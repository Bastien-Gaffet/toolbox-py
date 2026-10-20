#!/usr/bin/env python3
"""
importer_nouveautes.py
Importe UNIQUEMENT les nouvelles photos/vidéos d'une source (pCloud Drive,
dossier de téléchargement, carte SD...) vers un dossier de tri, sans jamais
reprendre ce qui a déjà été trié, dédoublonné ou supprimé.

Principe : un registre permanent (SQLite, dans le dossier de tri) mémorise
l'empreinte SHA-256 de tout ce qui a déjà été vu. Le registre ne fait que
grandir : supprimer une photo du disque ne l'en retire pas, donc elle ne
sera jamais réimportée.

Usage :
    python importer_nouveautes.py            ← assistant interactif (recommandé)
    python importer_nouveautes.py indexer  <racine> [dossier ...] [--avant AAAA-MM-JJ]
    python importer_nouveautes.py importer <racine> <source> [--simulation]
    python importer_nouveautes.py statut   <racine>

Avec rclone (ex. pCloud), la comparaison se fait sur les empreintes SHA-256
fournies par le cloud : seules les vraies nouveautés sont téléchargées.
"""

import os
import sys
import csv
import json
import shutil
import sqlite3
import getpass
import hashlib
import argparse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# ─── Extensions supportées ────────────────────────────────────────────────────

EXT_PHOTOS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".heic", ".heif", ".raw", ".cr2", ".cr3", ".nef",
    ".arw", ".dng", ".orf", ".rw2", ".pef",
}

EXT_VIDEOS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".3gp", ".ts", ".mts", ".m2ts",
    ".vob", ".ogv", ".rm", ".rmvb", ".divx",
}

EXT_MEDIA = EXT_PHOTOS | EXT_VIDEOS

NOM_REGISTRE = ".import_registre.sqlite"
DOSSIER_IMPORT = "_A_TRIER"

# Dossiers jamais parcourus (les miniatures krino sont aussi exclues, mais pas
# sa corbeille : voir indexer)
DOSSIERS_IGNORES = {".git", "__pycache__"}


# ─── Couleurs terminal ────────────────────────────────────────────────────────

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    def rouge(t):  return Fore.RED    + t + Style.RESET_ALL
    def vert(t):   return Fore.GREEN  + t + Style.RESET_ALL
    def jaune(t):  return Fore.YELLOW + t + Style.RESET_ALL
    def cyan(t):   return Fore.CYAN   + t + Style.RESET_ALL
    def gras(t):   return Style.BRIGHT + t + Style.RESET_ALL
except ImportError:
    def rouge(t):  return t
    def vert(t):   return t
    def jaune(t):  return t
    def cyan(t):   return t
    def gras(t):   return t


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRE
# ═══════════════════════════════════════════════════════════════════════════════
#
# Deux tables :
#   connus(hash)  → contenus déjà vus (sur le disque, importés, ou supprimés depuis)
#   vus(cle)      → fichiers source identifiés par nom|taille|mtime, qu'on sait
#                   déjà traités : on les saute SANS les relire (évite de
#                   retélécharger tout pCloud à chaque passage)
#   cache(cle)    → hash déjà calculé pour un fichier nom|taille|mtime
#                   (un fichier déplacé par krino ou un tri n'est pas rehashé)

def ouvrir_registre(racine: Path) -> sqlite3.Connection:
    db = sqlite3.connect(racine / NOM_REGISTRE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS connus (
            hash    TEXT PRIMARY KEY,
            origine TEXT NOT NULL,
            chemin  TEXT,
            date    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vus (
            cle     TEXT PRIMARY KEY,
            origine TEXT NOT NULL,
            date    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cache (
            cle  TEXT PRIMARY KEY,
            hash TEXT NOT NULL
        );
    """)
    return db


def cle_fichier(chemin: Path, st: os.stat_result) -> str:
    """Identité rapide d'un fichier, stable si on le déplace ou le copie avec copy2."""
    return f"{chemin.name.lower()}|{st.st_size}|{int(st.st_mtime)}"


def hash_fichier(chemin: Path, bloc: int = 1 << 20) -> str:
    """Calcule le hash SHA-256 d'un fichier par blocs."""
    sha = hashlib.sha256()
    with open(chemin, "rb") as f:
        while True:
            data = f.read(bloc)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()


def hash_avec_cache(db: sqlite3.Connection, chemin: Path, cle: str) -> str:
    ligne = db.execute("SELECT hash FROM cache WHERE cle = ?", (cle,)).fetchone()
    if ligne:
        return ligne[0]
    h = hash_fichier(chemin)
    db.execute("INSERT OR REPLACE INTO cache (cle, hash) VALUES (?, ?)", (cle, h))
    return h


def maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def lister_medias(dossier: Path, tout: bool = False, exclure: Path | None = None):
    """Itère (chemin, stat) sur les médias d'un dossier, récursivement."""
    for base, dirs, fichiers in os.walk(dossier):
        base_p = Path(base)
        dirs[:] = [d for d in dirs if d not in DOSSIERS_IGNORES
                   and not (base_p.name == ".krino" and d == "miniatures")]
        if exclure and (base_p == exclure or exclure in base_p.parents):
            dirs[:] = []
            continue
        for nom in fichiers:
            p = base_p / nom
            if not tout and p.suffix.lower() not in EXT_MEDIA:
                continue
            try:
                yield p, p.stat()
            except OSError as e:
                print(rouge(f"   ⚠ illisible : {p} ({e})"))


def afficher_progression(i: int, total: int | None = None):
    if i % 250 == 0:
        suffixe = f"/{total}" if total else ""
        print(f"   ... {i}{suffixe} fichiers", end="\r", flush=True)


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDE : indexer
# ═══════════════════════════════════════════════════════════════════════════════

def indexer(racine: Path, dossiers: list[Path], avant: datetime | None,
            tout: bool) -> None:
    db = ouvrir_registre(racine)
    date = maintenant()

    for dossier in dossiers:
        if not dossier.is_dir():
            print(rouge(f"✗ Dossier introuvable : {dossier}"))
            continue

        if avant:
            # Marque l'ancien contenu comme déjà vu, sans le lire
            print(gras(f"\nMarquage comme « déjà vu » (avant {avant:%Y-%m-%d}) : {dossier}"))
            n_vus = n_ignores = 0
            seuil = avant.timestamp()
            for i, (p, st) in enumerate(lister_medias(dossier, tout), 1):
                afficher_progression(i)
                if st.st_mtime < seuil:
                    db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)",
                               (cle_fichier(p, st), f"avant:{dossier}", date))
                    n_vus += 1
                else:
                    n_ignores += 1
            db.commit()
            print(f"   {vert(str(n_vus))} marqué(s) déjà vu(s), "
                  f"{n_ignores} plus récent(s) laissé(s) pour l'import")
            continue

        # Indexation par contenu (inclut la corbeille krino : ce qui y est
        # passé a été rejeté et ne doit pas revenir, même après vidage)
        print(gras(f"\nIndexation par contenu : {dossier}"))
        n_nouveaux = n_total = 0
        for i, (p, st) in enumerate(lister_medias(dossier, tout), 1):
            afficher_progression(i)
            cle = cle_fichier(p, st)
            try:
                h = hash_avec_cache(db, p, cle)
            except OSError as e:
                print(rouge(f"   ⚠ lecture impossible : {p} ({e})"))
                continue
            cur = db.execute("INSERT OR IGNORE INTO connus VALUES (?, ?, ?, ?)",
                             (h, "disque", str(p), date))
            n_nouveaux += cur.rowcount
            n_total += 1
            if i % 500 == 0:
                db.commit()
        db.commit()
        print(f"   {n_total} fichier(s) indexé(s), "
              f"{vert(str(n_nouveaux))} nouveau(x) contenu(s) mémorisé(s)")

    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDE : importer
# ═══════════════════════════════════════════════════════════════════════════════

def chemin_libre(cible: Path) -> Path:
    """Évite d'écraser un fichier existant : nom (2).jpg, nom (3).jpg..."""
    if not cible.exists():
        return cible
    n = 2
    while True:
        alt = cible.with_name(f"{cible.stem} ({n}){cible.suffix}")
        if not alt.exists():
            return alt
        n += 1


def importer(racine: Path, source: Path, vers: str | None,
             simulation: bool, tout: bool, sans_reindex: bool) -> None:
    if not source.is_dir():
        print(rouge(f"✗ Source introuvable : {source}"))
        sys.exit(1)

    dest = racine / DOSSIER_IMPORT / (vers or f"import_{datetime.now():%Y-%m-%d_%H%M}")

    # Rafraîchit d'abord l'index du disque (photos ajoutées à la main depuis la
    # dernière fois). Rapide : le cache évite de relire les fichiers connus.
    if not sans_reindex:
        indexer(racine, [racine], None, tout)

    db = ouvrir_registre(racine)
    date = maintenant()

    print(gras(f"\nAnalyse de la source : {source}"))
    if simulation:
        print(jaune("   [SIMULATION] aucun fichier ne sera copié"))

    stats = {"deja_vu": 0, "deja_sur_disque": 0, "doublon_source": 0,
             "importe": 0, "erreur": 0, "octets": 0}
    journal = []
    hash_session = set()

    for i, (p, st) in enumerate(lister_medias(source, tout, exclure=racine), 1):
        afficher_progression(i)
        cle = cle_fichier(p, st)

        if db.execute("SELECT 1 FROM vus WHERE cle = ?", (cle,)).fetchone():
            stats["deja_vu"] += 1
            continue

        try:
            h = hash_avec_cache(db, p, cle)
        except OSError as e:
            print(rouge(f"   ⚠ lecture impossible : {p} ({e})"))
            stats["erreur"] += 1
            continue

        if db.execute("SELECT 1 FROM connus WHERE hash = ?", (h,)).fetchone():
            stats["deja_sur_disque"] += 1
            if not simulation:
                db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)",
                           (cle, "connu", date))
            continue

        if h in hash_session:
            stats["doublon_source"] += 1
            if not simulation:
                db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)",
                           (cle, "doublon", date))
            continue
        hash_session.add(h)

        cible = chemin_libre(dest / p.relative_to(source))
        journal.append((str(p), str(cible), st.st_size, h))
        stats["importe"] += 1
        stats["octets"] += st.st_size

        if simulation:
            continue

        try:
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, cible)
            if cible.stat().st_size != st.st_size:
                raise OSError("taille différente après copie")
        except OSError as e:
            print(rouge(f"   ✗ échec copie : {p} ({e})"))
            stats["erreur"] += 1
            stats["importe"] -= 1
            journal.pop()
            continue

        # Enregistré seulement après une copie réussie
        db.execute("INSERT OR IGNORE INTO connus VALUES (?, ?, ?, ?)",
                   (h, "import", str(p), date))
        db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)",
                   (cle, "import", date))
        db.execute("INSERT OR IGNORE INTO cache VALUES (?, ?)",
                   (cle_fichier(cible, cible.stat()), h))
        if stats["importe"] % 100 == 0:
            db.commit()

    db.commit()
    db.close()

    # ── Rapport ──
    print(" " * 40)
    print(gras("\nRésultat"))
    print(f"   Déjà vus (sautés sans lecture)     : {stats['deja_vu']}")
    print(f"   Déjà sur le disque / déjà triés    : {stats['deja_sur_disque']}")
    print(f"   Doublons à l'intérieur de la source : {stats['doublon_source']}")
    if stats["erreur"]:
        print(rouge(f"   Erreurs                            : {stats['erreur']}"))
    verbe = "à importer" if simulation else "importé(s)"
    print(gras(vert(f"   Nouveaux {verbe:<26}: {stats['importe']} "
                    f"({stats['octets'] / 1e9:.2f} Go)")))

    if journal:
        if simulation:
            print(cyan(f"\n   Destination prévue : {dest}"))
            for src, _, _, _ in journal[:15]:
                print(f"     + {src}")
            if len(journal) > 15:
                print(f"     ... et {len(journal) - 15} autre(s)")
        else:
            fichier_journal = dest / "_journal_import.csv"
            with open(fichier_journal, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["source", "destination", "taille", "sha256"])
                w.writerows(journal)
            print(cyan(f"\n   Copiés dans : {dest}"))
            print(cyan(f"   Journal     : {fichier_journal}"))


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDE : statut
# ═══════════════════════════════════════════════════════════════════════════════

def statut(racine: Path) -> None:
    if not (racine / NOM_REGISTRE).exists():
        print(jaune(f"Aucun registre dans {racine}. Lance d'abord : indexer {racine}"))
        return
    db = ouvrir_registre(racine)
    print(gras(f"\nRegistre : {racine / NOM_REGISTRE}"))
    print(gras("   Contenus connus (par empreinte) :"))
    for origine, n in db.execute("SELECT origine, COUNT(*) FROM connus GROUP BY origine"):
        print(f"     {origine:<10} {n}")
    print(gras("   Fichiers source déjà vus :"))
    for origine, n in db.execute(
            "SELECT CASE WHEN origine LIKE 'avant:%' THEN 'avant-date' ELSE origine END o,"
            " COUNT(*) FROM vus GROUP BY o"):
        print(f"     {origine:<10} {n}")
    dernier = db.execute("SELECT MAX(date) FROM connus WHERE origine = 'import'").fetchone()[0]
    print(f"   Dernier import : {dernier or 'jamais'}")
    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE RCLONE (pCloud, Google Drive...)
# ═══════════════════════════════════════════════════════════════════════════════

EMPLACEMENTS_RCLONE = [
    r"D:\logiciel_exe\rclone-v1.74.4-windows-amd64\rclone.exe",
    str(Path.home() / "rclone-v1.74.4-windows-amd64" / "rclone.exe"),
]


def trouver_rclone(prefere: str | None = None) -> str | None:
    for candidat in [prefere, shutil.which("rclone"), *EMPLACEMENTS_RCLONE]:
        if candidat and Path(candidat).is_file():
            return candidat
    return None


def env_rclone(mot_de_passe: str | None) -> dict:
    env = dict(os.environ)
    if mot_de_passe:
        env["RCLONE_CONFIG_PASS"] = mot_de_passe
    return env


def rclone_sortie(rclone: str, args: list[str], mot_de_passe: str | None) -> str:
    res = subprocess.run([rclone, *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace",
                         env=env_rclone(mot_de_passe), stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or f"rclone a échoué ({res.returncode})")
    return res.stdout


def config_rclone_chiffree(rclone: str) -> bool:
    try:
        sortie = rclone_sortie(rclone, ["config", "file"], None)
        chemin = Path(sortie.strip().splitlines()[-1].strip())
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return "Encrypted rclone configuration" in f.readline()
    except (OSError, RuntimeError, IndexError):
        return False


def lister_rclone(rclone: str, distant: str, mot_de_passe: str | None,
                  tout: bool) -> list[dict]:
    """Liste récursive d'un dossier distant (sans empreintes : très rapide)."""
    sortie = rclone_sortie(rclone, ["lsjson", "-R", "--files-only", distant], mot_de_passe)
    fichiers = []
    for f in json.loads(sortie or "[]"):
        if not tout and Path(f["Name"]).suffix.lower() not in EXT_MEDIA:
            continue
        mtime = datetime.fromisoformat(f["ModTime"].replace("Z", "+00:00")).timestamp()
        fichiers.append({
            "chemin": f["Path"],
            "taille": f["Size"],
            "mtime": mtime,
            "cle": f"{f['Name'].lower()}|{f['Size']}|{int(mtime)}",
            "hash": None,
        })
    return fichiers


def empreintes_rclone(rclone: str, distant: str, fichiers: list[dict],
                      mot_de_passe: str | None) -> None:
    """Récupère le SHA-256 calculé par le cloud, sans télécharger les fichiers.
    Interrogés en parallèle, et seulement pour les fichiers donnés (lsjson --hash
    les interroge un par un : beaucoup trop lent sur pCloud)."""
    if not fichiers:
        return
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write("\n".join(f["chemin"] for f in fichiers))
    try:
        sortie = rclone_sortie(rclone, ["hashsum", "sha256", distant,
                                        "--files-from-raw", tmp.name,
                                        "--checkers", "16"], mot_de_passe)
    finally:
        os.unlink(tmp.name)
    par_chemin = {}
    for ligne in sortie.splitlines():
        h, _, chemin = ligne.partition("  ")
        if len(h) == 64 and chemin:
            par_chemin[chemin] = h
    for f in fichiers:
        f["hash"] = par_chemin.get(f["chemin"])


def marquer_avant_rclone(racine: Path, fichiers: list[dict], distant: str,
                         avant: datetime) -> tuple[int, int]:
    """Mémorise l'ancien contenu distant (avant la date) sans le télécharger."""
    db = ouvrir_registre(racine)
    date, seuil = maintenant(), avant.timestamp()
    n_vus = n_recents = 0
    for f in fichiers:
        if f["mtime"] >= seuil:
            n_recents += 1
            continue
        db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)",
                   (f["cle"], f"avant:{distant}", date))
        n_vus += 1
    db.commit()
    db.close()
    return n_vus, n_recents


def trier_rclone(racine: Path, rclone: str, distant: str, fichiers: list[dict],
                 mot_de_passe: str | None) -> dict:
    """Classe les fichiers distants : déjà vus / déjà connus / doublons / nouveaux."""
    db = ouvrir_registre(racine)
    res = {"deja_vu": 0, "deja_sur_disque": 0, "doublon_source": 0, "nouveaux": []}
    candidats = []
    for f in fichiers:
        if db.execute("SELECT 1 FROM vus WHERE cle = ?", (f["cle"],)).fetchone():
            res["deja_vu"] += 1
        else:
            candidats.append(f)
    if candidats:
        print(f"   Empreintes de {len(candidats)} fichier(s) non encore vus ...", flush=True)
        empreintes_rclone(rclone, distant, candidats, mot_de_passe)

    hash_session = set()
    for f in candidats:
        if f["hash"] and db.execute("SELECT 1 FROM connus WHERE hash = ?",
                                      (f["hash"],)).fetchone():
            res["deja_sur_disque"] += 1
            # Inutile de redemander son empreinte la prochaine fois
            db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)",
                       (f["cle"], "connu", maintenant()))
        elif f["hash"] and f["hash"] in hash_session:
            res["doublon_source"] += 1
        else:
            if f["hash"]:
                hash_session.add(f["hash"])
            res["nouveaux"].append(f)
    db.commit()
    db.close()
    return res


def telecharger_rclone(racine: Path, rclone: str, distant: str, nouveaux: list[dict],
                       dest: Path, mot_de_passe: str | None) -> int:
    """Télécharge les nouveautés avec rclone puis les enregistre dans le registre."""
    dest.mkdir(parents=True, exist_ok=True)
    liste = dest / "_liste_rclone.txt"
    liste.write_text("\n".join(f["chemin"] for f in nouveaux), encoding="utf-8")

    # rclone vérifie lui-même l'empreinte après chaque téléchargement
    subprocess.run([rclone, "copy", distant, str(dest), "--files-from-raw", str(liste),
                    "--progress", "--transfers", "8", "--retries", "3"],
                   env=env_rclone(mot_de_passe))
    liste.unlink(missing_ok=True)

    db = ouvrir_registre(racine)
    date = maintenant()
    journal, n_ok = [], 0
    for f in nouveaux:
        local = dest / f["chemin"]
        if not local.is_file() or local.stat().st_size != f["taille"]:
            print(rouge(f"   ✗ manquant après téléchargement : {f['chemin']}"))
            continue
        st = local.stat()
        h = f["hash"] or hash_fichier(local)
        if not f["hash"] and db.execute("SELECT 1 FROM connus WHERE hash = ?",
                                        (h,)).fetchone():
            local.unlink()  # sans empreinte distante : c'était en fait déjà connu
        else:
            db.execute("INSERT OR IGNORE INTO connus VALUES (?, ?, ?, ?)",
                       (h, "import", f"{distant}/{f['chemin']}", date))
            journal.append((f"{distant}/{f['chemin']}", str(local), f["taille"], h))
            n_ok += 1
        db.execute("INSERT OR IGNORE INTO vus VALUES (?, ?, ?)", (f["cle"], "import", date))
        db.execute("INSERT OR IGNORE INTO cache VALUES (?, ?)", (cle_fichier(local, st), h))
    db.commit()
    db.close()

    with open(dest / "_journal_import.csv", "w", newline="", encoding="utf-8") as fj:
        w = csv.writer(fj, delimiter=";")
        w.writerow(["source", "destination", "taille", "sha256"])
        w.writerows(journal)
    return n_ok


# ═══════════════════════════════════════════════════════════════════════════════
# SAUVEGARDE (robocopy)
# ═══════════════════════════════════════════════════════════════════════════════

def sauvegarder(racine: Path, cible: Path) -> bool:
    """Miroir du dossier de tri vers la sauvegarde (robocopy /MIR)."""
    cible.mkdir(parents=True, exist_ok=True)
    journal = cible.parent / f"{cible.name}_sauvegarde.log"
    print(cyan(f"\n   {racine}  →  {cible}"))
    res = subprocess.run(["robocopy", str(racine), str(cible), "/MIR",
                          "/COPY:DAT", "/DCOPY:DAT", "/MT:16", "/R:1", "/W:1",
                          "/NP", "/NFL", "/NDL", f"/LOG:{journal}", "/TEE"])
    # robocopy : 0-7 = succès, 8+ = erreurs
    ok = res.returncode < 8
    print((vert("   ✓ Sauvegarde terminée") if ok else
           rouge(f"   ✗ Erreurs pendant la sauvegarde, voir {journal}")))
    return ok


# ═══════════════════════════════════════════════════════════════════════════════
# ASSISTANT INTERACTIF
# ═══════════════════════════════════════════════════════════════════════════════

FICHIER_PREFS = Path.home() / ".importer_nouveautes.json"

PREFS_DEFAUT = {
    "racine": r"E:\Bastien\main_tri",
    "sauvegarde": r"D:\Sauvegardes\main_tri",
    "rclone": None,
    "distants": ["pcloud:Automatic Upload"],
}


def charger_prefs() -> dict:
    prefs = dict(PREFS_DEFAUT)
    try:
        prefs.update(json.loads(FICHIER_PREFS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return prefs


def enregistrer_prefs(prefs: dict) -> None:
    FICHIER_PREFS.write_text(json.dumps(prefs, indent=2, ensure_ascii=False),
                             encoding="utf-8")


def demander(question: str, defaut: str | None = None) -> str:
    suffixe = f" [{defaut}]" if defaut else ""
    while True:
        rep = input(f"{question}{suffixe} : ").strip().strip('"')
        if rep or defaut:
            return rep or defaut
        print(jaune("   (réponse requise)"))


def confirmer(question: str, defaut: bool = False) -> bool:
    rep = input(f"{question} [{'O/n' if defaut else 'o/N'}] : ").strip().lower()
    return defaut if not rep else rep in ("o", "oui", "y", "yes")


def demander_date(question: str, defaut: str | None = None) -> datetime:
    while True:
        try:
            return datetime.strptime(demander(question, defaut), "%Y-%m-%d")
        except ValueError:
            print(jaune("   Format attendu : AAAA-MM-JJ (ex. 2026-07-10)"))


def choisir(titre: str, options: list[str]) -> int:
    print(gras(f"\n{titre}"))
    for i, opt in enumerate(options, 1):
        print(f"  {cyan(str(i))}) {opt}")
    while True:
        rep = input("Choix : ").strip()
        if rep.isdigit() and 1 <= int(rep) <= len(options):
            return int(rep) - 1
        print(jaune(f"   Tape un numéro entre 1 et {len(options)}"))


class Session:
    """État de l'assistant : préférences + rclone + mot de passe (en mémoire seulement)."""

    def __init__(self):
        self.prefs = charger_prefs()
        self.mot_de_passe = None
        self.rclone = None

    def racine(self) -> Path:
        while True:
            r = Path(demander("Dossier de tri", self.prefs["racine"]))
            if r.is_dir():
                self.prefs["racine"] = str(r)
                return r
            print(rouge(f"   ✗ Introuvable : {r}"))

    def preparer_rclone(self) -> bool:
        if self.rclone:
            return True
        self.rclone = trouver_rclone(self.prefs.get("rclone"))
        while not self.rclone:
            chemin = demander("Chemin de rclone.exe (vide = annuler)", "-")
            if chemin == "-":
                return False
            self.rclone = trouver_rclone(chemin)
        self.prefs["rclone"] = self.rclone
        if config_rclone_chiffree(self.rclone):
            self.mot_de_passe = getpass.getpass("Mot de passe de la config rclone : ")
        return True

    def choisir_distants(self) -> list[str]:
        """Propose les dossiers distants (mémorisés ou à choisir dans le cloud)."""
        actuels = self.prefs.get("distants") or []
        if actuels:
            print(f"\nDossiers cloud surveillés : {cyan(', '.join(actuels))}")
            if confirmer("Utiliser ces dossiers ?", defaut=True):
                return actuels

        remotes = rclone_sortie(self.rclone, ["listremotes"], self.mot_de_passe).split()
        if not remotes:
            print(rouge("   ✗ Aucun remote rclone configuré (lance : rclone config)"))
            return []
        remote = remotes[choisir("Quel cloud ?", remotes)] if len(remotes) > 1 else remotes[0]
        print(f"\nDossiers à la racine de {remote}")
        sortie = rclone_sortie(self.rclone, ["lsf", "--dirs-only", remote], self.mot_de_passe)
        dossiers = [d.rstrip("/") for d in sortie.splitlines() if d.strip()]
        for i, d in enumerate(dossiers, 1):
            print(f"  {cyan(str(i))}) {d}")
        while True:
            rep = input("Numéros à surveiller (ex. 1,3) : ").replace(" ", "")
            try:
                choix = [dossiers[int(x) - 1] for x in rep.split(",") if x]
                if choix:
                    break
            except (ValueError, IndexError):
                pass
            print(jaune("   Sélection invalide"))
        self.prefs["distants"] = [f"{remote}{d}" for d in choix]
        return self.prefs["distants"]

    def lister(self, distant: str) -> list[dict]:
        print(f"   Lecture de {cyan(distant)} ...", flush=True)
        fichiers = lister_rclone(self.rclone, distant, self.mot_de_passe, tout=False)
        print(f"   {len(fichiers)} photo(s)/vidéo(s)")
        return fichiers


def flux_mise_en_place(s: Session) -> None:
    print(gras("\n═══ Mise en place du registre ═══"))
    print("Le registre mémorise tout ce qui a déjà été vu, pour ne jamais le réimporter.")
    racine = s.racine()

    if confirmer("\n1/2  Indexer le contenu actuel du dossier de tri (corbeille krino "
                 "comprise) ?\n     La 1re fois, compter ~10 min pour 60 Go", defaut=True):
        indexer(racine, [racine], None, tout=False)

    if not confirmer("\n2/2  As-tu déjà importé ce cloud par le passé (photos triées "
                     "et parfois supprimées depuis) ?", defaut=True):
        return
    if not s.preparer_rclone():
        return
    avant = demander_date("     Date de ton dernier import (garde de la marge, AAAA-MM-JJ)")
    print(jaune("     Tout ce qui est antérieur sera considéré comme déjà trié."))
    for distant in s.choisir_distants():
        fichiers = s.lister(distant)
        n_vus, n_recents = marquer_avant_rclone(racine, fichiers, distant, avant)
        print(f"   {vert(str(n_vus))} marqué(s) déjà vu(s), "
              f"{n_recents} postérieur(s) laissé(s) pour l'import")
    enregistrer_prefs(s.prefs)
    print(vert("\n✓ Mise en place terminée. Utilise maintenant « Importer les nouveautés »."))


def flux_import_cloud(s: Session) -> None:
    print(gras("\n═══ Importer les nouveautés du cloud ═══"))
    racine = s.racine()
    if not (racine / NOM_REGISTRE).exists():
        print(jaune("Pas encore de registre : fais d'abord la mise en place."))
        if confirmer("La lancer maintenant ?", defaut=True):
            flux_mise_en_place(s)
        return
    if not s.preparer_rclone():
        return
    distants = s.choisir_distants()
    enregistrer_prefs(s.prefs)

    # Photos ajoutées à la main depuis la dernière fois (rapide grâce au cache)
    indexer(racine, [racine], None, tout=False)

    print(gras("\nComparaison avec le registre (rien n'est téléchargé)"))
    a_importer = []
    for distant in distants:
        tri = trier_rclone(racine, s.rclone, distant, s.lister(distant), s.mot_de_passe)
        taille = sum(f["taille"] for f in tri["nouveaux"])
        print(f"     déjà vus {tri['deja_vu']}, déjà triés {tri['deja_sur_disque']}, "
              f"doublons {tri['doublon_source']}  →  "
              + gras(vert(f"{len(tri['nouveaux'])} nouveau(x) ({taille / 1e9:.2f} Go)")))
        if tri["nouveaux"]:
            a_importer.append((distant, tri["nouveaux"]))

    if not a_importer:
        print(vert("\n✓ Rien de nouveau, tout est déjà trié."))
        return

    for distant, nouveaux in a_importer:
        print(cyan(f"\n   {distant}"))
        for f in sorted(nouveaux, key=lambda f: f["mtime"])[-10:]:
            print(f"     + {datetime.fromtimestamp(f['mtime']):%Y-%m-%d}  {f['chemin']}")
        if len(nouveaux) > 10:
            print(f"     ... ({len(nouveaux) - 10} autre(s) plus ancien(s))")

    total = sum(len(n) for _, n in a_importer)
    nom = f"import_{datetime.now():%Y-%m-%d_%H%M}"
    if not confirmer(f"\nTélécharger ces {total} fichier(s) dans "
                     f"{DOSSIER_IMPORT}\\{nom} ?", defaut=True):
        print("Annulé, rien n'a été téléchargé.")
        return

    n_total = 0
    for distant, nouveaux in a_importer:
        sous = distant.split(":", 1)[-1].replace("/", "_") or "racine"
        dest = racine / DOSSIER_IMPORT / nom / sous
        print(gras(f"\nTéléchargement depuis {distant}"))
        n_total += telecharger_rclone(racine, s.rclone, distant, nouveaux, dest,
                                      s.mot_de_passe)

    print(gras(vert(f"\n✓ {n_total} nouveau(x) fichier(s) importé(s) dans "
                    f"{racine / DOSSIER_IMPORT / nom}")))
    print("  Trie-les avec krino : ce que tu supprimeras ne reviendra plus.")
    if confirmer("\nMettre à jour la sauvegarde maintenant ?", defaut=True):
        flux_sauvegarde(s, racine)


def flux_import_local(s: Session) -> None:
    print(gras("\n═══ Importer depuis un dossier local ═══"))
    racine = s.racine()
    source = Path(demander("Dossier source (carte SD, téléchargements...)"))
    importer(racine, source, None, simulation=True, tout=False, sans_reindex=False)
    if confirmer("\nCopier ces fichiers pour de vrai ?", defaut=True):
        importer(racine, source, None, simulation=False, tout=False, sans_reindex=True)


def flux_sauvegarde(s: Session, racine: Path | None = None) -> None:
    print(gras("\n═══ Sauvegarde du dossier de tri ═══"))
    racine = racine or s.racine()
    cible = Path(demander("Dossier de sauvegarde", s.prefs["sauvegarde"]))
    print(jaune("   Miroir : ce qui a été supprimé du tri le sera aussi de la sauvegarde."))
    if confirmer("   Lancer ?", defaut=True):
        s.prefs["sauvegarde"] = str(cible)
        enregistrer_prefs(s.prefs)
        sauvegarder(racine, cible)


def assistant() -> None:
    s = Session()
    print(gras(cyan("\n📥 Importer les nouveautés — assistant")))
    actions = [
        ("Importer les nouveautés du cloud (pCloud...)", flux_import_cloud),
        ("Importer depuis un dossier local", flux_import_local),
        ("Mise en place du registre (1re fois)", flux_mise_en_place),
        ("Sauvegarder le dossier de tri", flux_sauvegarde),
        ("Voir le registre", lambda s: statut(s.racine())),
        ("Quitter", None),
    ]
    while True:
        i = choisir("Que veux-tu faire ?", [a for a, _ in actions])
        fonction = actions[i][1]
        if fonction is None:
            return
        try:
            fonction(s)
        except RuntimeError as e:
            print(rouge(f"\n✗ {e}"))


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Importe seulement les nouvelles photos d'une source, "
                    "sans reprendre ce qui a déjà été trié ou supprimé.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Première fois :\n"
            "  python importer_nouveautes.py indexer  E:\\Photos\n"
            "  python importer_nouveautes.py indexer  E:\\Photos P:\\Photos --avant 2026-07-18\n"
            "Ensuite, à chaque fois :\n"
            "  python importer_nouveautes.py importer E:\\Photos P:\\Photos --simulation\n"
            "  python importer_nouveautes.py importer E:\\Photos P:\\Photos\n"
        ),
    )
    sous = parser.add_subparsers(dest="commande")

    p_idx = sous.add_parser("indexer", help="Mémorise le contenu existant comme « déjà vu »")
    p_idx.add_argument("racine", help="Dossier de tri (le registre y est stocké)")
    p_idx.add_argument("dossiers", nargs="*",
                       help="Dossiers à indexer (défaut : la racine elle-même)")
    p_idx.add_argument("--avant", metavar="AAAA-MM-JJ",
                       help="Marque comme déjà vus les fichiers modifiés avant cette date,\n"
                            "SANS les lire (pour l'ancien contenu d'une source déjà importée)")
    p_idx.add_argument("--tout", action="store_true",
                       help="Tous les fichiers, pas seulement photos/vidéos")

    p_imp = sous.add_parser("importer", help="Copie les nouveautés de la source vers le tri")
    p_imp.add_argument("racine", help="Dossier de tri (contient le registre)")
    p_imp.add_argument("source", help="Dossier source (pCloud Drive, téléchargements...)")
    p_imp.add_argument("-s", "--simulation", action="store_true",
                       help="Affiche ce qui serait importé sans rien copier")
    p_imp.add_argument("--vers", metavar="NOM",
                       help=f"Sous-dossier de {DOSSIER_IMPORT}/ (défaut : import_<date>)")
    p_imp.add_argument("--tout", action="store_true",
                       help="Tous les fichiers, pas seulement photos/vidéos")
    p_imp.add_argument("--sans-reindex", action="store_true",
                       help="Ne pas réindexer le dossier de tri avant l'import")

    p_st = sous.add_parser("statut", help="Affiche le contenu du registre")
    p_st.add_argument("racine", help="Dossier de tri")

    return parser.parse_args()


def main():
    # Console Windows : évite un plantage sur les symboles ✗ ⚠ « »
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = parse_args()
    if args.commande is None:
        assistant()
        return

    racine = Path(args.racine).resolve()
    if not racine.is_dir():
        print(rouge(f"✗ Dossier de tri introuvable : {racine}"))
        sys.exit(1)

    if args.commande == "indexer":
        avant = None
        if args.avant:
            try:
                avant = datetime.strptime(args.avant, "%Y-%m-%d")
            except ValueError:
                print(rouge("✗ Date invalide, format attendu : AAAA-MM-JJ"))
                sys.exit(1)
        dossiers = [Path(d).resolve() for d in args.dossiers] or [racine]
        indexer(racine, dossiers, avant, args.tout)
    elif args.commande == "importer":
        importer(racine, Path(args.source).resolve(), args.vers,
                 args.simulation, args.tout, args.sans_reindex)
    elif args.commande == "statut":
        statut(racine)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(jaune("\nInterrompu — le registre garde ce qui a déjà été enregistré."))
        sys.exit(130)
