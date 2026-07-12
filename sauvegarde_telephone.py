#!/usr/bin/env python3
"""
sauvegarde_telephone.py
Copie les photos et vidéos d'un téléphone vers un disque dur.

Deux méthodes de connexion :
  Mode classique : téléphone monté comme lecteur (chemin accessible)
  Mode ADB       : connexion USB directe via Android Debug Bridge (--adb)

Deux modes de destination :
  --mode miroir  : reproduit exactement l'arborescence du téléphone
  --mode trier   : regroupe tout dans Photos/ et Videos/ à plat

Usage :
    python sauvegarde_telephone.py <destination> --adb [options]
    python sauvegarde_telephone.py <source> <destination> [options]
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# ── Couleurs terminal ─────────────────────────────────────────────────────────
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    def rouge(t):  return Fore.RED     + t + Style.RESET_ALL
    def vert(t):   return Fore.GREEN   + t + Style.RESET_ALL
    def jaune(t):  return Fore.YELLOW  + t + Style.RESET_ALL
    def cyan(t):   return Fore.CYAN    + t + Style.RESET_ALL
    def gras(t):   return Style.BRIGHT + t + Style.RESET_ALL
except ImportError:
    def rouge(t):  return t
    def vert(t):   return t
    def jaune(t):  return t
    def cyan(t):   return t
    def gras(t):   return t

# ═══════════════════════════════════════════════════════════════════════════════
# BARRE DE PROGRESSION (stdlib pure, aucune dépendance)
# ═══════════════════════════════════════════════════════════════════════════════

def barre_progression(actuel: int, total: int, largeur: int = 35,
                      label: str = "", suffixe: str = "") -> str:
    """
    Retourne une barre de progression textuelle.
    Ex : [==========>          ] 12/50  24%  label  suffixe
    """
    if total == 0:
        pct = 0.0
    else:
        pct = actuel / total
    rempli = int(largeur * pct)
    vide   = largeur - rempli - 1
    fleche = ">" if actuel < total else "="
    barre  = "=" * rempli + fleche + " " * max(0, vide)
    pct_str = f"{pct*100:5.1f}%"
    label_str = f"  {label}" if label else ""
    suffixe_str = f"  {suffixe}" if suffixe else ""
    return f"  [{barre}] {actuel}/{total}  {pct_str}{label_str}{suffixe_str}"


def afficher_barre(actuel: int, total: int, label: str = "",
                   suffixe: str = "", fin: bool = False):
    """Affiche ou met a jour la barre de progression sur la meme ligne."""
    ligne = barre_progression(actuel, total, label=label, suffixe=suffixe)
    if fin:
        print("\r" + ligne)
    else:
        print("\r" + ligne, end="", flush=True)


# ── Extensions media ──────────────────────────────────────────────────────────
EXT_PHOTOS = {
    # Standards courants
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".webp",

    # Formats modernes
    ".heic", ".heif",           # Apple iPhone (iOS 11+)
    ".avif",                    # AV1 Image (Android 12+, Pixel)
    ".jxl",                     # JPEG XL (Pixel 9+, futur standard)

    # RAW — constructeurs grands publics
    ".raw",                     # Générique
    ".dng",                     # Adobe DNG (Pixel, Lightroom, DJI)
    ".cr2", ".cr3",             # Canon
    ".nef", ".nrw",             # Nikon (reflex / compact)
    ".arw", ".srf", ".sr2",     # Sony
    ".orf",                     # Olympus / OM System
    ".rw2",                     # Panasonic / Leica
    ".pef", ".ptx",             # Pentax
    ".srw",                     # Samsung
    ".raf",                     # Fujifilm
    ".3fr", ".fff",             # Hasselblad
    ".iiq", ".cap",             # Phase One
    ".x3f",                     # Sigma
    ".erf",                     # Epson
    ".kdc", ".k25",             # Kodak
    ".mef",                     # Mamiya
    ".mos",                     # Leaf / Mamiya
    ".bay",                     # Casio
    ".rwl",                     # Leica (RAW)
    ".rwz",                     # Rawzor
    ".gpr",                     # GoPro RAW

    # Formats spéciaux / téléphones
    ".mp",                      # Google Motion Photo (Pixel)
    ".mvimg",                   # Google Motion Photo (ancien)
    ".live",                    # Samsung Live Photo
    ".lsa", ".lsav",            # Samsung Live Shot (données audio des Live Photos)
    ".mpo",                     # Photo 3D (Nintendo 3DS, certains APN)
    ".insp",                    # Insta360 photo
}

EXT_VIDEOS = {
    # Standards courants
    ".mp4", ".m4v",
    ".mkv",
    ".avi",
    ".mov",                     # QuickTime (Apple, DJI, GoPro)
    ".wmv",
    ".flv", ".f4v",
    ".webm",
    ".mpg", ".mpeg",
    ".3gp", ".3g2",             # Vidéo mobile (Android ancien)

    # Broadcast / caméscope
    ".ts", ".mts", ".m2ts",     # Transport Stream (Blu-ray, caméscopes)
    ".vob",                     # DVD
    ".ogv",                     # Ogg Video
    ".rm", ".rmvb",             # RealMedia
    ".divx",                    # DivX
    ".asf",                     # Windows Media (ancien)

    # Action cam / drone
    ".lrv",                     # GoPro Low Res Video (proxy)
    ".insv",                    # Insta360 vidéo 360°
    ".360",                     # Vidéo 360° générique

    # Apple
    ".m4v",                     # iTunes Video
}
EXT_MEDIA = EXT_PHOTOS | EXT_VIDEOS

# Dossiers système à ignorer sur le téléphone
# IMPORTANT : "android" retiré — trop large, bloquerait
# Seuls les dossiers PUREMENT système sans aucun média utilisateur sont ignorés.
# On ne code JAMAIS de chemins d'applications en dur (WhatsApp, Instagram, etc.)
# car il existe des centaines d'apps inconnues qui stockent des médias.
# Règle : si c'est une photo ou une vidéo, on la copie — peu importe d'où elle vient.
DOSSIERS_IGNORES = {
    ".thumbnails",      # miniatures générées automatiquement (pas les originaux)
    "thumbnails",
    ".trash",           # corbeille Android
    "lost.dir",         # fichiers récupérés par fsck (généralement corrompus)
    ".android_secure",  # dossier système chiffré inaccessible
}


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE ADB — Connexion USB directe
# ═══════════════════════════════════════════════════════════════════════════════

def adb(commande: list, capture: bool = True) -> subprocess.CompletedProcess:
    """Lance une commande adb et retourne le résultat."""
    return subprocess.run(
        ["adb"] + commande,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def verifier_adb() -> bool:
    """Vérifie qu'adb est installé et accessible dans le PATH."""
    try:
        r = adb(["version"])
        return r.returncode == 0
    except FileNotFoundError:
        return False


def verifier_appareil_connecte() -> tuple[bool, str]:
    """
    Vérifie qu'un appareil Android est connecté et autorisé.
    Retourne (ok, message).
    """
    r = adb(["devices"])
    if r.returncode != 0:
        return False, "adb ne répond pas."

    lignes = [l.strip() for l in r.stdout.splitlines()
              if l.strip() and not l.startswith("List of")]

    if not lignes:
        return False, "Aucun appareil détecté."

    for ligne in lignes:
        if "unauthorized" in ligne:
            return False, (
                "Appareil détecté mais non autorisé.\n"
                "   → Déverrouillez votre téléphone et appuyez sur\n"
                "     'Autoriser' dans la popup 'Autoriser le débogage USB'."
            )
        if "offline" in ligne:
            return False, "Appareil détecté mais hors ligne. Débranchez et rebranchez."
        if "device" in ligne:
            nom = ligne.split()[0]
            return True, nom

    return False, "État inconnu. Vérifiez la connexion USB."


def adb_scanner_complet(dossier_source: str = "/sdcard") -> dict:
    """
    Scanne le téléphone et retourne un rapport complet :
    {
      "dossier_reel": str,
      "methode": str,              # printf / find+stat / ls-R
      "tous": list,                # tous les fichiers trouvés
      "medias": dict,              # {chemin: taille} — fichiers media valides
      "ignores_dossier": list,     # ignorés car dossier système
      "ignores_ext": list,         # ignorés car extension non media
      "taille_totale": int,
    }
    Utilisé aussi bien par la sauvegarde que par --diagnostic.
    """
    rapport = {
        "dossier_reel": dossier_source,
        "methode": "?",
        "tous": [],
        "medias": {},
        "ignores_dossier": [],
        "ignores_ext": [],
        "taille_totale": 0,
    }

    # ── Résoudre le chemin réel ───────────────────────────────────────────────
    r_resolve = adb(["shell", f"readlink -f {dossier_source}"])
    dossier_reel = r_resolve.stdout.strip() if (
        r_resolve.returncode == 0 and r_resolve.stdout.strip()
    ) else dossier_source
    rapport["dossier_reel"] = dossier_reel

    # ── Récupérer tous les fichiers + tailles ─────────────────────────────────
    fichiers_avec_tailles = {}  # {chemin: taille}

    # Méthode A : find -printf (chemin|taille en une passe — idéal)
    r = adb(["shell", f"find {dossier_reel} -type f -printf '%p|%s\n' 2>/dev/null"])
    if r.returncode == 0 and r.stdout.strip() and "|" in r.stdout:
        rapport["methode"] = "find -printf"
        for ligne in r.stdout.splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("find:") or "|" not in ligne:
                continue
            idx = ligne.rfind("|")
            chemin = ligne[:idx]
            try:
                taille = int(ligne[idx+1:])
            except ValueError:
                taille = 0
            if chemin:
                fichiers_avec_tailles[chemin] = taille
    else:
        # Méthode B : find simple puis stat -c "%n %s" fichier par fichier
        r2 = adb(["shell", f"find {dossier_reel} -type f 2>/dev/null"])
        if r2.returncode == 0 and r2.stdout.strip():
            rapport["methode"] = "find + stat"
            tous_brut = [l.strip() for l in r2.stdout.splitlines()
                         if l.strip() and not l.startswith("find:")]

            # stat par lots de 50 (plus petit = plus fiable sur Android)
            for lot in _decouper_lots(tous_brut, 50):
                # Écrire les chemins dans un fichier tmp sur le téléphone
                # puis stat en une fois — évite les problèmes de longueur de commande
                liste_chemins = "\n".join(lot)
                # stat -c "%n|%s" sur chaque fichier individuellement via xargs
                chemins_echappes = " ".join(f"\"{c}\"" for c in lot)
                r3 = adb(["shell", f"stat -c '%n|%s' {chemins_echappes} 2>/dev/null"])
                for ligne in r3.stdout.splitlines():
                    ligne = ligne.strip()
                    if not ligne or "|" not in ligne:
                        continue
                    idx = ligne.rfind("|")
                    chemin = ligne[:idx].strip().strip('"')
                    try:
                        taille = int(ligne[idx+1:].strip())
                    except ValueError:
                        taille = 0
                    if chemin:
                        fichiers_avec_tailles[chemin] = taille

            # Si stat a échoué, garder les chemins avec taille 0
            for f in tous_brut:
                if f not in fichiers_avec_tailles:
                    fichiers_avec_tailles[f] = 0
        else:
            # Méthode C : ls -R (dernier recours)
            rapport["methode"] = "ls -R (fallback)"
            r4 = adb(["shell", f"ls -R {dossier_reel} 2>/dev/null"])
            for f in _parser_ls_recursif(r4.stdout, dossier_reel):
                fichiers_avec_tailles[f] = 0

    rapport["tous"] = list(fichiers_avec_tailles.keys())

    # ── Classifier chaque fichier — extension + dossiers système stricts uniquement
    for chemin, taille in fichiers_avec_tailles.items():
        parties = chemin.lower().replace("\\", "/").split("/")
        ignore_dossier = any(p in DOSSIERS_IGNORES for p in parties)
        ext = os.path.splitext(chemin)[1].lower()

        if ignore_dossier:
            rapport["ignores_dossier"].append(chemin)
        elif ext not in EXT_MEDIA:
            rapport["ignores_ext"].append((chemin, ext))
        else:
            rapport["medias"][chemin] = taille
            rapport["taille_totale"] += taille

    return rapport


def adb_lister_fichiers_avec_tailles(dossier_source: str = "/sdcard") -> dict:
    """Wrapper de compatibilité — retourne uniquement {chemin: taille} des médias."""
    rapport = adb_scanner_complet(dossier_source)
    return rapport["medias"]


def _est_media_valide(chemin: str) -> bool:
    """
    Retourne True si le fichier est un média (photo/vidéo).
    Filtre uniquement par extension + dossiers système stricts.
    On ne filtre JAMAIS par chemin d'application.
    """
    parties = chemin.lower().replace("\\", "/").split("/")
    if any(p in DOSSIERS_IGNORES for p in parties):
        return False
    ext = os.path.splitext(chemin)[1].lower()
    return ext in EXT_MEDIA

def _decouper_lots(liste: list, taille: int) -> list:
    """Decoupe une liste en lots de taille fixe."""
    return [liste[i:i+taille] for i in range(0, len(liste), taille)]


def _parser_ls_recursif(sortie: str, racine: str) -> list[str]:
    """Parse la sortie de 'ls -R' pour reconstruire les chemins complets."""
    fichiers = []
    dossier_courant = racine
    for ligne in sortie.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        if ligne.endswith(":"):
            dossier_courant = ligne.rstrip(":")
        elif "/" not in ligne and "." in ligne:
            fichiers.append(f"{dossier_courant}/{ligne}")
    return fichiers


def adb_lister_fichiers_media(dossier_source: str = "/sdcard") -> list[str]:
    """Wrapper pour compatibilite — retourne juste la liste des chemins."""
    return sorted(adb_lister_fichiers_avec_tailles(dossier_source).keys())


def adb_taille_fichier(chemin_telephone: str) -> int:
    """Retourne la taille d'un fichier (utilise le cache si disponible)."""
    if chemin_telephone in _CACHE_TAILLES:
        return _CACHE_TAILLES[chemin_telephone]
    r = adb(["shell", f"stat -c %s '{chemin_telephone}'"])
    try:
        return int(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0


# Cache global des tailles — rempli par adb_lister_fichiers_avec_tailles
_CACHE_TAILLES: dict = {}


def adb_copier_fichier(chemin_telephone: str, chemin_local: Path) -> bool:
    """
    Copie un fichier du téléphone vers le disque local via adb pull.
    Retourne True si succès.
    """
    chemin_local.parent.mkdir(parents=True, exist_ok=True)
    r = adb(["pull", chemin_telephone, str(chemin_local)], capture=True)
    return r.returncode == 0


def adb_infos_appareil() -> dict:
    """Récupère les infos de base de l'appareil (marque, modèle, Android)."""
    def prop(p):
        r = adb(["shell", f"getprop {p}"])
        return r.stdout.strip() if r.returncode == 0 else "?"

    return {
        "marque":   prop("ro.product.brand"),
        "modele":   prop("ro.product.model"),
        "android":  prop("ro.build.version.release"),
        "stockage": prop("ro.product.name"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES LOCAUX
# ═══════════════════════════════════════════════════════════════════════════════

def hash_fichier(chemin: Path, bloc: int = 65536) -> str:
    """Hash SHA-256 d'un fichier pour comparer le contenu."""
    sha = hashlib.sha256()
    with open(chemin, "rb") as f:
        while True:
            data = f.read(bloc)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()


def fichiers_identiques_local(src: Path, dst: Path) -> bool:
    """Vérifie si deux fichiers locaux sont identiques (taille puis hash)."""
    if src.stat().st_size != dst.stat().st_size:
        return False
    return hash_fichier(src) == hash_fichier(dst)


def fichiers_identiques_adb(chemin_telephone: str, dst: Path) -> bool:
    """
    Vérifie si un fichier sur le téléphone est identique à un fichier local.
    Comparaison par taille uniquement (rapide, évite de copier pour rien).
    """
    if not dst.exists():
        return False
    taille_tel = adb_taille_fichier(chemin_telephone)
    taille_loc = dst.stat().st_size
    return taille_tel == taille_loc and taille_tel > 0


def destination_unique(dest: Path) -> Path:
    """Retourne un chemin sans collision en ajoutant _2, _3… si nécessaire."""
    if not dest.exists():
        return dest
    compteur = 2
    while True:
        nouveau = dest.parent / f"{dest.stem}_{compteur}{dest.suffix}"
        if not nouveau.exists():
            return nouveau
        compteur += 1


def formater_taille(octets: int) -> str:
    """Formate une taille en octets en unité lisible."""
    for unite in ["o", "Ko", "Mo", "Go", "To"]:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} Po"


# ═══════════════════════════════════════════════════════════════════════════════
# CALCUL DES DESTINATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def calculer_destination(chemin_src: str | Path, source_racine: str | Path,
                         destination: Path, mode: str,
                         noms_utilises: dict) -> Path:
    """
    Calcule le chemin de destination selon le mode choisi.
    Fonctionne avec des chemins locaux (Path) ou des chemins ADB (str).
    """
    nom_fichier = Path(chemin_src).name
    ext = Path(chemin_src).suffix.lower()

    if mode == "miroir":
        # Reproduire le chemin relatif depuis la racine source
        if isinstance(chemin_src, Path):
            relatif = chemin_src.relative_to(source_racine)
        else:
            # Chemin ADB : construire le relatif manuellement
            racine_str = str(source_racine).rstrip("/")
            chemin_str = str(chemin_src)
            relatif = Path(chemin_str[len(racine_str):].lstrip("/"))
        dest = destination / relatif

    else:  # trier
        sous_dossier = "Photos" if ext in EXT_PHOTOS else "Videos"
        dest_initiale = destination / sous_dossier / nom_fichier
        cle = str(dest_initiale)
        if cle in noms_utilises:
            dest = destination_unique(dest_initiale)
        else:
            dest = dest_initiale
        noms_utilises[cle] = True

    return dest


# ═══════════════════════════════════════════════════════════════════════════════
# SAUVEGARDE — MODE CLASSIQUE (source locale)
# ═══════════════════════════════════════════════════════════════════════════════

def collecter_fichiers_local(source: Path) -> list[Path]:
    """Parcourt récursivement la source locale et retourne les fichiers média."""
    fichiers = []
    for f in source.rglob("*"):
        if not f.is_file():
            continue
        parties = {p.lower() for p in f.parts}
        if parties & DOSSIERS_IGNORES:
            continue
        if f.suffix.lower() in EXT_MEDIA:
            fichiers.append(f)
    return sorted(fichiers)


def sauvegarder_local(source: Path, destination: Path, mode: str,
                      incremental: bool, simulation: bool) -> list:
    """Sauvegarde depuis un chemin local (téléphone monté, carte SD…)."""
    print(gras("\n🔍 Analyse de la source..."))
    fichiers = collecter_fichiers_local(source)
    nb_photos = sum(1 for f in fichiers if f.suffix.lower() in EXT_PHOTOS)
    nb_videos = sum(1 for f in fichiers if f.suffix.lower() in EXT_VIDEOS)
    print(f"   {len(fichiers)} fichier(s) média  "
          f"({nb_photos} photo(s), {nb_videos} vidéo(s))")

    if not fichiers:
        print(jaune("   Aucun fichier média trouvé."))
        return []

    # Planification
    a_copier, deja_la, conflits = [], [], []
    noms_utilises: dict = {}

    for f in fichiers:
        dest = calculer_destination(f, source, destination, mode, noms_utilises)
        if dest.exists():
            if incremental and fichiers_identiques_local(f, dest):
                deja_la.append((f, dest))
            else:
                conflits.append((f, dest))
        else:
            a_copier.append((f, dest))

    _afficher_resume_plan(a_copier, deja_la, conflits, source, destination, mode)

    if not a_copier and not conflits:
        print(vert("✅ Sauvegarde déjà à jour."))
        return []

    if not simulation:
        reponse = input(
            f"  Lancer ({len(a_copier) + len(conflits)} fichier(s)) ? [o/N] : "
        ).strip().lower()
        if reponse not in ("o", "oui", "y", "yes"):
            print("  ⛔ Annulé.")
            return []
        print()

    journal = []
    tout = a_copier + [(src, destination_unique(dst)) for src, dst in conflits]
    for i, (src, dst) in enumerate(tout, 1):
        taille = src.stat().st_size
        print(f"  [{i}/{len(tout)}] {src.name:<45} {formater_taille(taille):>8}", end="")
        if not simulation:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  {vert('✅')}")
                journal.append({"src": str(src), "dst": str(dst), "ok": True})
            except Exception as e:
                print(f"  {rouge('❌')}  {e}")
                journal.append({"src": str(src), "dst": str(dst),
                                 "erreur": str(e), "ok": False})
        else:
            print(f"  {cyan('◌  [simulation]')}")
            journal.append({"src": str(src), "dst": str(dst), "simulation": True})

    return journal


# ═══════════════════════════════════════════════════════════════════════════════
# SAUVEGARDE — MODE ADB
# ═══════════════════════════════════════════════════════════════════════════════

def sauvegarder_adb(destination: Path, mode: str, source_adb: str,
                    incremental: bool, simulation: bool) -> list:
    """Sauvegarde via ADB (connexion USB directe)."""

    # ── Vérifications préalables ─────────────────────────────────────────────
    if not verifier_adb():
        print(rouge("\n❌ 'adb' introuvable dans le PATH."))
        print(jaune(AIDE_INSTALLATION_ADB))
        sys.exit(1)

    ok, msg = verifier_appareil_connecte()
    if not ok:
        print(rouge(f"\n❌ Appareil non disponible : {msg}"))
        sys.exit(1)

    # ── Infos appareil ───────────────────────────────────────────────────────
    infos = adb_infos_appareil()
    print(f"\n   📱 {infos['marque']} {infos['modele']}  "
          f"(Android {infos['android']})")

    # ── Listage des fichiers + tailles en une seule passe ───────────────────
    print(gras("\n🔍 Listage des fichiers sur le téléphone..."))
    print(f"   Source ADB : {source_adb}")

    # Spinner pendant le scan (appel bloquant unique)
    import threading, itertools, time as _time
    _stop_spinner = threading.Event()
    def _spinner():
        for c in itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]):
            if _stop_spinner.is_set():
                break
            print(f"\r   {c}  Scan du téléphone en cours...", end="", flush=True)
            _time.sleep(0.1)
    t = threading.Thread(target=_spinner, daemon=True)
    t.start()

    global _CACHE_TAILLES
    _rapport = adb_scanner_complet(source_adb)
    _CACHE_TAILLES = _rapport["medias"]

    _stop_spinner.set()
    t.join()

    fichiers = sorted(_CACHE_TAILLES.keys())
    nb_photos = sum(1 for f in fichiers if Path(f).suffix.lower() in EXT_PHOTOS)
    nb_videos = sum(1 for f in fichiers if Path(f).suffix.lower() in EXT_VIDEOS)
    taille_totale_tel = _rapport["taille_totale"]

    # Rapport détaillé du scan
    print(f"\r   ✅ Scan terminé (méthode : {_rapport['methode']})" + " " * 20)
    print(f"   {'─'*56}")
    print(f"   Fichiers totaux sur le téléphone : {len(_rapport['tous'])}")
    print(f"   Médias retenus    : {vert(str(len(fichiers)))} "
          f"({nb_photos} photo(s), {nb_videos} vidéo(s))"
          f"  —  {formater_taille(taille_totale_tel)}")
    print(f"   Ignorés (système) : {len(_rapport['ignores_dossier'])}"
          f"  (dossiers système Android)")
    print(f"   Ignorés (ext.)    : {len(_rapport['ignores_ext'])}"
          f"  (PDF, MP3, documents…)")
    print(f"   {'─'*56}")

    if not fichiers:
        print(jaune("   Aucun fichier média trouvé."))
        return []

    # ── Planification (comparaison locale uniquement, pas d'appel ADB) ───────
    print(gras("\n🗂  Planification des copies..."))
    a_copier, deja_la, conflits = [], [], []
    noms_utilises: dict = {}

    nb_total = len(fichiers)
    for i, f in enumerate(fichiers, 1):
        nom_court = Path(f).name[:30] + "…" if len(Path(f).name) > 30 else Path(f).name
        afficher_barre(i, nb_total, label=nom_court)
        dest = calculer_destination(f, source_adb, destination, mode, noms_utilises)
        if dest.exists() and incremental:
            taille_tel = _CACHE_TAILLES.get(f, 0)
            taille_loc = dest.stat().st_size
            if taille_tel == taille_loc and taille_tel > 0:
                deja_la.append((f, dest))
            else:
                conflits.append((f, dest))
        else:
            a_copier.append((f, dest))
    afficher_barre(nb_total, nb_total, label="Terminé", fin=True)

    _afficher_resume_plan(a_copier, deja_la, conflits,
                          Path(source_adb), destination, mode, adb_mode=True)

    if not a_copier and not conflits:
        print(vert("✅ Sauvegarde déjà à jour."))
        return []

    if not simulation:
        reponse = input(
            f"  Lancer ({len(a_copier) + len(conflits)} fichier(s)) ? [o/N] : "
        ).strip().lower()
        if reponse not in ("o", "oui", "y", "yes"):
            print("  ⛔ Annulé.")
            return []
        print()

    # ── Copie ────────────────────────────────────────────────────────────────
    journal = []
    tout = a_copier + [(src, destination_unique(dst)) for src, dst in conflits]
    total = len(tout)
    taille_copiee = 0

    erreurs = []
    for i, (src, dst) in enumerate(tout, 1):
        taille = _CACHE_TAILLES.get(src, adb_taille_fichier(src))
        nom_court = Path(src).name[:28] + "…" if len(Path(src).name) > 28 else Path(src).name
        suffixe_barre = formater_taille(taille_copiee) + " copiés" if taille_copiee else ""

        # Barre de progression — mise à jour sur place, pas de spam
        afficher_barre(i, total, label=nom_court, suffixe=suffixe_barre)

        if not simulation:
            ok = adb_copier_fichier(src, dst)
            if ok:
                taille_copiee += taille
                journal.append({"src": src, "dst": str(dst), "ok": True})
            else:
                # Erreur : mémoriser pour afficher après la barre
                erreurs.append(Path(src).name)
                journal.append({"src": src, "dst": str(dst), "ok": False})
        else:
            journal.append({"src": src, "dst": str(dst), "simulation": True})

    # Ligne de résumé finale (sur une nouvelle ligne après la barre)
    suffixe_final = formater_taille(taille_copiee) + " copiés" if not simulation else "[SIMULATION]"
    afficher_barre(total, total, label="Terminé", suffixe=suffixe_final, fin=True)
    print(f"  {'─'*60}")
    print(f"  {'✅' if not simulation else '◌ '} {total} fichier(s)  —  {suffixe_final}")
    if erreurs:
        print(rouge(f"  ❌ {len(erreurs)} erreur(s) :"))
        for nom in erreurs:
            print(rouge(f"     • {nom}"))
    print(f"  {'─'*60}")

    return journal


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSION DE MODE
# ═══════════════════════════════════════════════════════════════════════════════

def convertir_mode(dossier: Path, vers: str, simulation: bool = False):
    """Réorganise une sauvegarde existante vers un autre mode."""
    if vers == "miroir":
        print(jaune(
            "  ⚠️  La conversion vers le mode miroir nécessite le téléphone\n"
            "     (la structure d'origine n'est pas conservée en mode trié).\n"
            "     Relancez avec --adb --mode miroir en connectant le téléphone."
        ))
        return

    print(gras("\n🔄 Conversion vers le mode Trié (Photos/ + Videos/)...\n"))
    fichiers = [f for f in dossier.rglob("*")
                if f.is_file() and f.suffix.lower() in EXT_MEDIA
                and f.parent.name not in ("Photos", "Videos")]

    if not fichiers:
        print("  Aucun fichier à déplacer.")
        return

    deplacés = 0
    for fichier in sorted(fichiers):
        sous_dossier = "Photos" if fichier.suffix.lower() in EXT_PHOTOS else "Videos"
        dest = destination_unique(dossier / sous_dossier / fichier.name)
        print(f"  {fichier.relative_to(dossier):<60} → {dest.relative_to(dossier)}")
        if not simulation:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fichier), str(dest))
                deplacés += 1
            except Exception as e:
                print(rouge(f"    ❌ {e}"))

    if not simulation:
        for d in sorted(dossier.rglob("*"), reverse=True):
            if d.is_dir() and d.name not in ("Photos", "Videos"):
                try:
                    if not any(d.iterdir()):
                        d.rmdir()
                except Exception:
                    pass
        print(f"\n  ✅ {deplacés} fichier(s) réorganisé(s).")
    else:
        print(cyan(f"\n  [SIMULATION] {len(fichiers)} fichier(s) seraient déplacés."))


# ═══════════════════════════════════════════════════════════════════════════════
# AFFICHAGE & JOURNAL
# ═══════════════════════════════════════════════════════════════════════════════

def _afficher_resume_plan(a_copier, deja_la, conflits,
                          source, destination, mode, adb_mode=False):
    """Affiche le résumé du plan de copie."""
    nb_photos = sum(1 for s, _ in a_copier
                    if Path(s).suffix.lower() in EXT_PHOTOS)
    nb_videos = sum(1 for s, _ in a_copier
                    if Path(s).suffix.lower() in EXT_VIDEOS)

    print(f"\n  {'─'*58}")
    print(f"  Source      : {'ADB — ' if adb_mode else ''}{source}")
    print(f"  Destination : {destination}")
    print(f"  Mode        : {gras(mode)}")
    print(f"  {'─'*58}")
    print(f"  À copier    : {gras(str(len(a_copier)))} fichier(s)"
          f"  ({nb_photos} photo(s), {nb_videos} vidéo(s))")
    print(f"  Déjà à jour : {len(deja_la)} fichier(s)  ← ignorés")
    if conflits:
        print(rouge(f"  Conflits    : {len(conflits)} fichier(s) (même nom, taille différente)"))
        print(jaune("  → Renommés automatiquement à destination"))
    print(f"  {'─'*58}\n")


def sauvegarder_journal(destination: Path, journal: list, mode: str,
                        source: str, adb_mode: bool = False):
    """Sauvegarde un journal JSON horodaté."""
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = destination / f".sauvegarde_{horodatage}.json"
    données = {
        "date":        horodatage,
        "methode":     "adb" if adb_mode else "local",
        "source":      source,
        "destination": str(destination),
        "mode":        mode,
        "operations":  journal,
    }
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(données, f, ensure_ascii=False, indent=2)
    print(vert(f"\n  💾 Journal : {chemin.name}"))


# ═══════════════════════════════════════════════════════════════════════════════
# AIDE INSTALLATION ADB
# ═══════════════════════════════════════════════════════════════════════════════

AIDE_INSTALLATION_ADB = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  COMMENT INSTALLER ADB (Android Debug Bridge)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  WINDOWS
  ───────
  1. Télécharger "SDK Platform Tools" sur :
     https://developer.android.com/tools/releases/platform-tools
  2. Extraire le ZIP (ex: C:\\platform-tools\\)
  3. Ajouter au PATH :
     Panneau de config → Système → Variables d'environnement
     → PATH → Ajouter : C:\\platform-tools
  4. Redémarrer le terminal et tester : adb version

  macOS
  ─────
  brew install android-platform-tools

  Linux (Ubuntu/Debian)
  ─────────────────────
  sudo apt install adb

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ACTIVER LE DÉBOGAGE USB SUR LE TÉLÉPHONE (une seule fois)
  ─────────────────────────────────────────────────────────
  1. Paramètres → À propos du téléphone
  2. Appuyer 7 fois sur "Numéro de build"
     → "Vous êtes maintenant développeur !"
  3. Paramètres → Options pour les développeurs
  4. Activer "Débogage USB"
  5. Brancher le téléphone en USB
  6. Sur le téléphone : appuyer sur "Autoriser" dans la popup
  7. Tester : adb devices  (doit afficher votre appareil)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="📱 Sauvegarde photos/vidéos d'un téléphone vers un disque dur.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :

  ── Via ADB (USB direct, recommandé pour Redmi/Android) ──────────────────────
  python sauvegarde_telephone.py "D:\\Sauvegarde" --adb --mode miroir --simulation
  python sauvegarde_telephone.py "D:\\Sauvegarde" --adb --mode miroir
  python sauvegarde_telephone.py "D:\\Sauvegarde" --adb --mode trier

  ── Via chemin local (téléphone monté) ───────────────────────────────────────
  python sauvegarde_telephone.py "Z:\\" "D:\\Sauvegarde" --mode miroir

  ── Conversion d'une sauvegarde existante ────────────────────────────────────
  python sauvegarde_telephone.py "D:\\Sauvegarde" --convertir trier

  ── Infos & diagnostic ADB ───────────────────────────────────────────────────
  python sauvegarde_telephone.py --aide-adb
  python sauvegarde_telephone.py --verifier-adb
        """
    )

    parser.add_argument("source_ou_destination", nargs="?", default=None,
                        help="En mode ADB    : dossier de DESTINATION\n"
                             "En mode local  : dossier SOURCE (téléphone monté)\n"
                             "En mode convert: dossier à réorganiser\n"
                             "(optionnel avec --diagnostic, --verifier-adb, --aide-adb)")

    parser.add_argument("destination_locale", nargs="?",
                        help="Dossier de destination (mode local uniquement)")

    # ── Actions spéciales ──
    parser.add_argument("--adb", action="store_true",
                        help="Utiliser ADB pour accéder au téléphone via USB")
    parser.add_argument("--convertir", choices=["trier", "miroir"],
                        metavar="MODE",
                        help="Réorganiser une sauvegarde existante")
    parser.add_argument("--aide-adb", action="store_true",
                        help="Afficher les instructions d'installation d'ADB")
    parser.add_argument("--verifier-adb", action="store_true",
                        help="Vérifier la connexion ADB et afficher les infos appareil")
    parser.add_argument("--diagnostic", action="store_true",
                        help="Lister tous les fichiers trouvés ET ignorés sur le téléphone\n"
                             "Utile pour déboguer des fichiers manquants")

    # ── Options ──
    parser.add_argument("--mode", choices=["miroir", "trier"], default="miroir",
                        help="miroir : reproduit l'arborescence (défaut)\n"
                             "trier  : regroupe dans Photos/ et Videos/")
    parser.add_argument("--source-adb", default="/sdcard",
                        metavar="CHEMIN",
                        help="Dossier racine sur le téléphone (défaut : /sdcard)")
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Aperçu sans copier aucun fichier")
    parser.add_argument("-f", "--forcer", action="store_true",
                        help="Recopier même les fichiers déjà à jour")

    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    # ── Aide ADB ──────────────────────────────────────────────────────────────
    if args.aide_adb:
        print(AIDE_INSTALLATION_ADB)
        return

    # Vérifier que source_ou_destination est fourni pour les modes qui en ont besoin
    if not args.source_ou_destination and not any([
        args.aide_adb, args.verifier_adb, args.diagnostic
    ]):
        print(rouge("❌ Argument <destination> requis."))
        print(jaune("   Usage : python sauvegarde_telephone.py <destination> --adb"))
        print(jaune("   Aide  : python sauvegarde_telephone.py --help"))
        sys.exit(1)

    # ── Vérification ADB ─────────────────────────────────────────────────────
    if args.verifier_adb:
        print(gras("\n🔌 Vérification ADB...\n"))
        if not verifier_adb():
            print(rouge("  ❌ ADB non trouvé."))
            print(jaune("  Lancez : python sauvegarde_telephone.py --aide-adb"))
            sys.exit(1)
        r = adb(["version"])
        print(vert(f"  ✅ {r.stdout.splitlines()[0]}"))

        ok, msg = verifier_appareil_connecte()
        if not ok:
            print(rouge(f"  ❌ Appareil : {msg}"))
            sys.exit(1)

        print(vert(f"  ✅ Appareil connecté : {msg}"))
        infos = adb_infos_appareil()
        print(f"     {infos['marque']} {infos['modele']} — Android {infos['android']}")
        return

    # ── Mode diagnostic ───────────────────────────────────────────────────────
    if args.diagnostic:
        print(gras("\n🔬 Mode diagnostic — analyse complète du stockage\n"))
        if not verifier_adb():
            print(rouge("❌ ADB non trouvé."))
            sys.exit(1)
        ok, msg = verifier_appareil_connecte()
        if not ok:
            print(rouge(f"❌ {msg}"))
            sys.exit(1)

        # Spinner — même implémentation que la sauvegarde
        import threading, itertools, time as _time
        _stop_diag = threading.Event()
        def _spinner_diag():
            for c in itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]):
                if _stop_diag.is_set():
                    break
                print(f"\r   {c}  Scan en cours...", end="", flush=True)
                _time.sleep(0.1)
        t_diag = threading.Thread(target=_spinner_diag, daemon=True)
        t_diag.start()

        # Même fonction que la sauvegarde → résultats strictement cohérents
        source_diag = args.source_adb if hasattr(args, "source_adb") else "/sdcard"
        rapport = adb_scanner_complet(source_diag)

        _stop_diag.set()
        t_diag.join()

        medias    = list(rapport["medias"].keys())
        nb_photos = sum(1 for f in medias if Path(f).suffix.lower() in EXT_PHOTOS)
        nb_videos = sum(1 for f in medias if Path(f).suffix.lower() in EXT_VIDEOS)

        print(f"\r   ✅ Scan terminé  (méthode : {rapport['methode']})" + " "*20)
        print(f"\n  {'─'*60}")
        print(f"  Chemin scanné              : {rapport['dossier_reel']}")
        print(f"  {'─'*60}")
        print(f"  Fichiers totaux trouvés    : {len(rapport['tous'])}")
        print(f"  Médias retenus             : {vert(str(len(medias)))}  "
              f"({nb_photos} photo(s), {nb_videos} vidéo(s))"
              f"  —  {formater_taille(rapport['taille_totale'])}")
        print(f"  Ignorés (dossiers système) : {len(rapport['ignores_dossier'])}"
              f"  (/Android/data, cache, .thumbnails…)")
        print(f"  Ignorés (ext. non-média)   : {jaune(str(len(rapport['ignores_ext'])))}"
              f"  (PDF, MP3, documents…)")
        print(f"  {'─'*60}\n")

        if rapport["ignores_ext"]:
            from collections import Counter
            compteur = Counter(ext for _, ext in rapport["ignores_ext"])
            print(gras("  Extensions hors scope (pas des photos/vidéos) :"))
            for ext_val, nb in compteur.most_common(25):
                label = ext_val if ext_val else "(sans extension)"
                print(f"    {label:<22} {nb:>6} fichier(s)")
            print()
            print(jaune("  → Ces fichiers ne sont PAS copiés — ils ne sont pas des médias."))
            print(jaune("    Si une extension vous semble manquer, elle peut être ajoutée."))
        return

    dossier_principal = Path(args.source_ou_destination).resolve() if args.source_ou_destination else Path('.')
    mode_str = rouge(" [SIMULATION]") if args.simulation else ""
    print(f"\n{gras('📱 sauvegarde_telephone.py')}{mode_str}\n")

    # ── Mode conversion ───────────────────────────────────────────────────────
    if args.convertir:
        if not dossier_principal.exists():
            print(rouge(f"❌ Dossier introuvable : {dossier_principal}"))
            sys.exit(1)
        convertir_mode(dossier_principal, vers=args.convertir,
                       simulation=args.simulation)
        return

    # ── Mode ADB ──────────────────────────────────────────────────────────────
    if args.adb:
        destination = dossier_principal
        journal = sauvegarder_adb(
            destination=destination,
            mode=args.mode,
            source_adb=args.source_adb,
            incremental=not args.forcer,
            simulation=args.simulation,
        )
        if not args.simulation and journal:
            sauvegarder_journal(destination, journal, args.mode,
                                args.source_adb, adb_mode=True)

    # ── Mode local ────────────────────────────────────────────────────────────
    else:
        source = dossier_principal
        if not args.destination_locale:
            print(rouge("❌ <destination> requise en mode local."))
            sys.exit(1)
        destination = Path(args.destination_locale).resolve()

        if not source.exists():
            print(rouge(f"❌ Source introuvable : {source}"))
            print(jaune("   Vérifiez que le téléphone est bien monté."))
            sys.exit(1)

        journal = sauvegarder_local(
            source=source,
            destination=destination,
            mode=args.mode,
            incremental=not args.forcer,
            simulation=args.simulation,
        )
        if not args.simulation and journal:
            sauvegarder_journal(destination, journal, args.mode, str(source))

    if journal:
        ok     = sum(1 for e in journal if e.get("ok"))
        echecs = sum(1 for e in journal if not e.get("ok")
                     and not e.get("simulation"))
        print(f"\n{gras('✅ Terminé.')}  {ok} copie(s) réussie(s)"
              + (f"  |  {rouge(str(echecs) + ' erreur(s)')}" if echecs else "")
              + "\n")


if __name__ == "__main__":
    main()