#!/usr/bin/env python3
"""
photos_manager.py
Gestion complète d'un dossier de photos et vidéos :
  1. Détection et suppression des vrais doublons (hash + taille)
  2. Renommage normalisé avec détection screenshots
  3. Classement par année/mois

Dépendances :
    pip install Pillow piexif

Usage :
    python photos_manager.py <dossier> [options]
"""

import os
import sys
import re
import json
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

# ── Pillow + piexif (EXIF) ────────────────────────────────────────────────────
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

try:
    import piexif
    PIEXIF_OK = True
except ImportError:
    PIEXIF_OK = False

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

# ── Mots-clés indiquant un screenshot dans le nom de fichier ─────────────────
PATTERNS_SCREENSHOT = [
    r"screenshot", r"screen.?shot", r"capture", r"captura",
    r"bildschirmfoto", r"prise.?d.?[eé]cran",
    r"^sc_", r"^screen_",
]
REGEX_SCREENSHOT = re.compile(
    "|".join(PATTERNS_SCREENSHOT), re.IGNORECASE
)

# ── Résolutions typiques d'écrans (indice parmi d'autres, non décisif seul) ──
RESOLUTIONS_ECRANS = {
    (1080, 1920), (1080, 2340), (1080, 2400), (1080, 2460),
    (1170, 2532), (1179, 2556), (1284, 2778), (1290, 2796),
    (1440, 2560), (1440, 3040), (1440, 3200),
    (2160, 3840),                              # 4K
    (1080, 1080),                              # carré Instagram
    (750, 1334), (828, 1792), (1125, 2436),    # anciens iPhone
    (1366, 768), (1920, 1080), (2560, 1440),   # PC landscape
    (768, 1366), (1080, 1920), (1440, 2560),   # PC portrait
}

# ── Tags EXIF caractéristiques d'un vrai appareil photo ──────────────────────
# Leur présence est un contre-indice fort (= vraie photo, pas screenshot)
TAGS_APPAREIL_PHOTO = {"Make", "Model", "LensModel", "LensMake"}
TAGS_OPTIQUES       = {"FocalLength", "ExposureTime", "FNumber",
                       "ISOSpeedRatings", "ShutterSpeedValue", "ApertureValue"}

# ── Seuil de score pour classifier comme screenshot ───────────────────────────
# Score >= SEUIL_SCREENSHOT → tagué _screenshot
SEUIL_SCREENSHOT = 2


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
# MODULE 1 — DÉTECTION ET SUPPRESSION DES DOUBLONS
# ═══════════════════════════════════════════════════════════════════════════════

def hash_fichier(chemin: Path, bloc: int = 65536) -> str:
    """Calcule le hash SHA-256 d'un fichier par blocs (efficace sur gros fichiers)."""
    sha = hashlib.sha256()
    with open(chemin, "rb") as f:
        while True:
            data = f.read(bloc)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()


def trouver_doublons(racine: Path, recursif: bool = True) -> dict:
    """
    Parcourt le dossier et groupe les fichiers par (taille, hash).
    Retourne un dict {hash: [liste de chemins]} pour les groupes de 2+ fichiers.
    Stratégie : d'abord grouper par taille (rapide), puis hasher les candidats.
    """
    print(gras("\nAnalyse des doublons..."))

    # Étape 1 : grouper par taille (filtre rapide)
    par_taille: dict = {}
    glob = racine.rglob("*") if recursif else racine.glob("*")
    tous = [f for f in glob if f.is_file() and f.suffix.lower() in EXT_MEDIA]

    print(f"   {len(tous)} fichier(s) média trouvé(s)")

    for fichier in tous:
        taille = fichier.stat().st_size
        par_taille.setdefault(taille, []).append(fichier)

    # Ne garder que les groupes avec au moins 2 fichiers de même taille
    candidats = [groupe for groupe in par_taille.values() if len(groupe) > 1]
    nb_candidats = sum(len(g) for g in candidats)
    print(f"   {nb_candidats} fichier(s) à hasher (même taille)")

    if not candidats:
        return {}

    # Étape 2 : hasher les candidats seulement
    par_hash: dict = {}
    for groupe in candidats:
        for fichier in groupe:
            try:
                h = hash_fichier(fichier)
                par_hash.setdefault(h, []).append(fichier)
            except (IOError, OSError) as e:
                print(rouge(f"   Impossible de lire {fichier.name} : {e}"))

    # Ne garder que les vrais doublons
    doublons = {h: chemins for h, chemins in par_hash.items() if len(chemins) > 1}
    return doublons


def choisir_fichier_a_garder(groupe: list) -> Path:
    """
    Parmi un groupe de doublons, choisit le fichier à conserver :
    - Priorité au nom le plus court (original probable)
    - En cas d'égalité : le plus ancien (date de modification)
    """
    return sorted(groupe, key=lambda f: (len(f.name), f.stat().st_mtime))[0]


def supprimer_doublons(doublons: dict, simulation: bool = True,
                       corbeille: bool = False, racine: Path = None) -> list:
    """
    Supprime (ou déplace vers _DOUBLONS) les fichiers en double.
    Retourne le journal des suppressions.
    """
    journal = []
    total_libere = 0

    if not doublons:
        print(vert("   Aucun doublon trouvé."))
        return journal

    nb_groupes = len(doublons)
    nb_a_suppr = sum(len(v) - 1 for v in doublons.values())
    print(f"\n   {nb_groupes} groupe(s) de doublons — {nb_a_suppr} fichier(s) à supprimer")
    print()

    dossier_corbeille = (racine / "_DOUBLONS_SUPPRIMES") if corbeille and racine else None

    for i, (hash_val, groupe) in enumerate(doublons.items(), 1):
        garder = choisir_fichier_a_garder(groupe)
        supprimer = [f for f in groupe if f != garder]

        print(f"  Groupe {i}/{nb_groupes} — {gras(garder.name)}")
        print(f"   Conservé  : {garder}")
        for f in supprimer:
            taille = f.stat().st_size
            total_libere += taille
            print(f"   Doublon  : {f}  ({taille // 1024} Ko)")
            if not simulation:
                try:
                    if corbeille and dossier_corbeille:
                        dossier_corbeille.mkdir(exist_ok=True)
                        dest = dossier_corbeille / f.name
                        # Éviter collision dans la corbeille
                        compteur = 2
                        while dest.exists():
                            dest = dossier_corbeille / f"{f.stem}_{compteur}{f.suffix}"
                            compteur += 1
                        shutil.move(str(f), str(dest))
                    else:
                        f.unlink()
                    journal.append({"fichier": str(f), "conserve": str(garder), "ok": True})
                except Exception as e:
                    print(rouge(f"      Erreur : {e}"))
                    journal.append({"fichier": str(f), "erreur": str(e), "ok": False})
            else:
                journal.append({"fichier": str(f), "conserve": str(garder), "simulation": True})
        print()

    mode = "serait libéré" if simulation else "libéré"
    print(f"   Espace {mode} : {total_libere / (1024*1024):.1f} Mo")
    if corbeille and dossier_corbeille and not simulation:
        print(f"   Doublons déplacés vers : {dossier_corbeille}")

    return journal


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — LECTURE EXIF ET DÉTECTION SCREENSHOT
# ═══════════════════════════════════════════════════════════════════════════════

def lire_date_exif(chemin: Path) -> datetime | None:
    """
    Lit la date de prise de vue depuis les métadonnées EXIF.
    Retourne un objet datetime ou None si non disponible.
    """
    if not PILLOW_OK:
        return None
    try:
        img = Image.open(chemin)
        exif_data = img._getexif()
        if not exif_data:
            return None
        for tag_id, valeur in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                # Format EXIF : "YYYY:MM:DD HH:MM:SS"
                return datetime.strptime(str(valeur), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def lire_date_fichier(chemin: Path) -> datetime:
    """Retourne la date de modification du fichier comme fallback."""
    return datetime.fromtimestamp(chemin.stat().st_mtime)


def obtenir_date_media(chemin: Path) -> tuple[datetime, str]:
    """
    Retourne (date, source) où source est 'exif' ou 'fichier'.
    Priorité : EXIF > date de modification.
    """
    if chemin.suffix.lower() in EXT_PHOTOS:
        date_exif = lire_date_exif(chemin)
        if date_exif:
            return date_exif, "exif"
    return lire_date_fichier(chemin), "fichier"


def lire_exif_brut(chemin: Path) -> dict:
    """
    Retourne un dict {nom_tag: valeur} des tags EXIF présents dans l'image.
    Retourne {} si Pillow non disponible ou lecture impossible.
    """
    if not PILLOW_OK:
        return {}
    try:
        img = Image.open(chemin)
        exif_raw = img._getexif()
        if not exif_raw:
            return {}
        return {TAGS.get(tid, tid): val for tid, val in exif_raw.items()}
    except Exception:
        return {}


def score_screenshot(chemin: Path) -> tuple[int, list]:
    """
    Calcule un score de probabilité « screenshot » pour un fichier image.
    Retourne (score, liste_des_indices_détectés).

    Système de points :
      +2  Nom du fichier contient un mot-clé screenshot
      +1  Dimensions correspondent à une résolution d'écran connue
      +1  Aucun tag Make/Model/Lens (pas d'appareil photo identifié)
      +1  Aucune donnée optique (focale, exposition, ISO...)
      -2  Tag Make OU Model présent          -> vraie photo, fort contre-indice
      -1  Données optiques présentes         -> vraie photo, contre-indice

    Seuil de classification : score >= SEUIL_SCREENSHOT (= 2)
    """
    score = 0
    indices = []

    # ── Indice 1 : nom de fichier (+2 si positif — très fiable) ──────────────
    if REGEX_SCREENSHOT.search(chemin.stem):
        score += 2
        indices.append("nom_suspect(+2)")

    # ── Indices EXIF (nécessitent Pillow) ────────────────────────────────────
    if PILLOW_OK and chemin.suffix.lower() in EXT_PHOTOS:

        exif = lire_exif_brut(chemin)

        # Indice 2 : dimensions d'écran (+1 si correspond, mais non décisif seul)
        try:
            with Image.open(chemin) as img:
                w, h = img.size
            if (w, h) in RESOLUTIONS_ECRANS or (h, w) in RESOLUTIONS_ECRANS:
                score += 1
                indices.append(f"dimensions_ecran({w}x{h})(+1)")
        except Exception:
            pass

        # Indice 3 : absence de Make/Model (-2 si présent, +1 si absent)
        tags_appareil_presents = TAGS_APPAREIL_PHOTO & set(exif.keys())
        if tags_appareil_presents:
            score -= 2
            indices.append(f"appareil_photo_identifie({','.join(tags_appareil_presents)})(-2)")
        else:
            score += 1
            indices.append("pas_de_make_model(+1)")

        # Indice 4 : absence de données optiques (-1 si présentes, +1 si absentes)
        tags_optiques_presents = TAGS_OPTIQUES & set(exif.keys())
        if tags_optiques_presents:
            score -= 1
            indices.append("donnees_optiques_presentes(-1)")
        else:
            score += 1
            indices.append("pas_de_donnees_optiques(+1)")

    return score, indices


def est_screenshot(chemin: Path) -> bool:
    """
    Retourne True si le fichier est très probablement un screenshot.
    Utilise un système de score multi-indices pour éviter les faux positifs
    (ex : photo portrait smartphone avec la même résolution qu'un écran).
    """
    score, _ = score_screenshot(chemin)
    return score >= SEUIL_SCREENSHOT


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3 — RENOMMAGE NORMALISÉ
# ═══════════════════════════════════════════════════════════════════════════════

def construire_nom(chemin: Path, format_date: str = "AAAA-MM-JJ",
                   compteur: int = 0) -> str:
    """
    Construit le nouveau nom normalisé du fichier.
    Format :
      - Photo   : AAAA-MM-JJ_HH-MM-SS.ext  ou  AAAAMMJJ_HHMMSS.ext
      - Screenshot : AAAA-MM-JJ_HH-MM-SS_screenshot.ext
      - Vidéo   : AAAA-MM-JJ_HH-MM-SS_video.ext
    """
    date, _ = obtenir_date_media(chemin)
    ext = chemin.suffix.lower()
    est_video = ext in EXT_VIDEOS
    screenshot = est_screenshot(chemin) and not est_video

    if format_date == "AAAA-MM-JJ":
        partie_date = date.strftime("%Y-%m-%d_%H-%M-%S")
    else:
        partie_date = date.strftime("%Y%m%d_%H%M%S")

    suffixe = ""
    if screenshot:
        suffixe = "_screenshot"
    elif est_video:
        suffixe = "_video"

    nom_base = f"{partie_date}{suffixe}"
    if compteur > 0:
        nom_base += f"_{compteur:02d}"

    return nom_base + ext


def renommer_fichiers(racine: Path, format_date: str = "AAAA-MM-JJ",
                      recursif: bool = True, simulation: bool = True) -> list:
    """Renomme tous les fichiers média selon la convention choisie."""
    print(gras("\nRenommage des fichiers..."))

    glob = racine.rglob("*") if recursif else racine.glob("*")
    fichiers = sorted([f for f in glob if f.is_file()
                       and f.suffix.lower() in EXT_MEDIA])

    if not fichiers:
        print("   Aucun fichier média trouvé.")
        return []

    journal = []
    # Suivi des noms déjà utilisés dans chaque dossier pour éviter les collisions
    noms_utilises: dict = {}

    for fichier in fichiers:
        dossier = fichier.parent
        compteur = 0
        nom_cible = construire_nom(fichier, format_date, compteur)

        # Incrémenter si collision
        while True:
            cle = (dossier, nom_cible)
            cible = dossier / nom_cible
            if cle not in noms_utilises and (cible == fichier or not cible.exists()):
                break
            compteur += 1
            nom_cible = construire_nom(fichier, format_date, compteur)

        noms_utilises[(dossier, nom_cible)] = True
        cible = dossier / nom_cible

        if fichier.name == nom_cible:
            continue  # Déjà au bon format

        type_label = ""
        if "_screenshot" in nom_cible:
            _, indices = score_screenshot(fichier)
            detail = ", ".join(indices) if indices else ""
            type_label = cyan(f" [screenshot — {detail}]")
        elif "_video" in nom_cible:
            type_label = jaune(" [video]")

        print(f"   {fichier.name:<50} -> {vert(nom_cible)}{type_label}")

        if not simulation:
            try:
                fichier.rename(cible)
                journal.append({"ancien": str(fichier), "nouveau": str(cible), "ok": True})
            except Exception as e:
                print(rouge(f"      {e}"))
                journal.append({"ancien": str(fichier), "erreur": str(e), "ok": False})
        else:
            journal.append({"ancien": str(fichier), "nouveau": str(cible), "simulation": True})

    ok = sum(1 for e in journal if e.get("ok") or e.get("simulation"))
    print(f"\n   {ok} fichier(s) renommé(s)" + (" [SIMULATION]" if simulation else ""))
    return journal


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4 — CLASSEMENT PAR ANNÉE / MOIS
# ═══════════════════════════════════════════════════════════════════════════════

NOMS_MOIS = [
    "", "01_Janvier", "02_Février", "03_Mars", "04_Avril",
    "05_Mai", "06_Juin", "07_Juillet", "08_Août",
    "09_Septembre", "10_Octobre", "11_Novembre", "12_Décembre",
]


def classer_par_date(racine: Path, par_mois: bool = True,
                     recursif: bool = False, simulation: bool = True) -> list:
    """
    Déplace les fichiers dans une arborescence Année/Mois (ou Année seule).
    Structure créée :
        racine/
          2023/
            01_Janvier/
            06_Juin/
          2024/
            ...
    """
    print(gras("\nClassement par date..."))

    # On prend uniquement les fichiers à la racine (non récursif par défaut)
    glob = racine.rglob("*") if recursif else racine.glob("*")
    fichiers = sorted([f for f in glob if f.is_file()
                       and f.suffix.lower() in EXT_MEDIA])

    if not fichiers:
        print("   Aucun fichier média à classer.")
        return []

    journal = []

    for fichier in fichiers:
        date, _ = obtenir_date_media(fichier)
        annee = str(date.year)
        mois = NOMS_MOIS[date.month]

        if par_mois:
            dossier_dest = racine / annee / mois
        else:
            dossier_dest = racine / annee

        # Gérer les doublons de nom à destination
        dest = dossier_dest / fichier.name
        compteur = 2
        while dest.exists() and dest != fichier:
            dest = dossier_dest / f"{fichier.stem}_{compteur:02d}{fichier.suffix}"
            compteur += 1

        label_dest = dest.relative_to(racine)
        print(f"   {fichier.name:<50} -> {vert(str(label_dest))}")

        if not simulation:
            try:
                dossier_dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fichier), str(dest))
                journal.append({"src": str(fichier), "dst": str(dest), "ok": True})
            except Exception as e:
                print(rouge(f"      {e}"))
                journal.append({"src": str(fichier), "erreur": str(e), "ok": False})
        else:
            journal.append({"src": str(fichier), "dst": str(dest), "simulation": True})

    ok = sum(1 for e in journal if e.get("ok") or e.get("simulation"))
    print(f"\n   {ok} fichier(s) classé(s)" + (" [SIMULATION]" if simulation else ""))
    return journal


# ─── Journal global ───────────────────────────────────────────────────────────

def sauvegarder_journal(racine: Path, données: dict):
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = racine / f".photos_manager_{horodatage}.json"
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(données, f, ensure_ascii=False, indent=2)
    print(vert(f"\n   Journal : {chemin.name}"))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Gestionnaire de photos et vidéos — doublons, renommage, classement",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  # Supprimer les doublons (simulation d'abord)
  python photos_manager.py ~/Photos --doublons --simulation

  # Supprimer les doublons réellement (déplacer vers dossier sécurisé)
  python photos_manager.py ~/Photos --doublons --corbeille

  # Renommer avec format court
  python photos_manager.py ~/Photos --renommer --format court

  # Classer par année et mois
  python photos_manager.py ~/Photos --classer

  # Classer par année uniquement
  python photos_manager.py ~/Photos --classer --sans-mois

  # Tout faire d'un coup (simulation)
  python photos_manager.py ~/Photos --doublons --renommer --classer --simulation

  # Tout faire pour de vrai
  python photos_manager.py ~/Photos --doublons --renommer --classer
        """
    )

    parser.add_argument("dossier", nargs="?", default=".",
                        help="Dossier à traiter (défaut : dossier courant)")

    # ── Actions ──
    actions = parser.add_argument_group("Actions (au moins une requise)")
    actions.add_argument("--doublons",  action="store_true",
                         help="Détecter et supprimer les doublons")
    actions.add_argument("--renommer",  action="store_true",
                         help="Renommer les fichiers en format normalisé")
    actions.add_argument("--classer",   action="store_true",
                         help="Classer les fichiers par année/mois")

    # ── Options doublons ──
    opt_dup = parser.add_argument_group("Options doublons")
    opt_dup.add_argument("--corbeille", action="store_true",
                         help="Déplacer les doublons dans _DOUBLONS_SUPPRIMES/ au lieu de supprimer")

    # ── Options renommage ──
    opt_ren = parser.add_argument_group("Options renommage")
    opt_ren.add_argument("--format", choices=["long", "court"], default="long",
                         help="Format de date : long=AAAA-MM-JJ (défaut), court=AAAAMMJJ")

    # ── Options classement ──
    opt_cls = parser.add_argument_group("Options classement")
    opt_cls.add_argument("--sans-mois", action="store_true",
                         help="Classer par année seulement (sans sous-dossier mois)")
    opt_cls.add_argument("--recursif-classer", action="store_true",
                         help="Chercher les fichiers dans les sous-dossiers pour le classement")

    # ── Global ──
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Aperçu sans modifier aucun fichier")
    parser.add_argument("-r", "--recursif", action="store_true",
                        help="Traiter aussi les sous-dossiers (doublons et renommage)")

    return parser.parse_args()


# ─── Point d'entrée ──────────────────────────────────────────────────────────

def main():
    args = parse_args()

    if not any([args.doublons, args.renommer, args.classer]):
        print(jaune("Aucune action demandée. Utilisez --doublons, --renommer et/ou --classer."))
        print("   Ajoutez --help pour l'aide complète.")
        sys.exit(0)

    racine = Path(args.dossier).resolve()
    if not racine.exists() or not racine.is_dir():
        print(rouge(f"Dossier introuvable : {racine}"))
        sys.exit(1)

    if not PILLOW_OK:
        print(jaune("Pillow non installé — EXIF et détection screenshot par dimensions désactivés."))
        print("   Installez avec : pip install Pillow piexif\n")

    mode_str = jaune(" [SIMULATION — aucun fichier modifié]") if args.simulation else ""
    print(f"\n{gras('photos_manager.py')}{mode_str}")
    print(f"   Dossier : {racine}\n")

    journal_global = {}
    fmt = "AAAA-MM-JJ" if args.format == "long" else "AAAAMMJJ"

    # ── 1. Doublons ──────────────────────────────────────────────────────────
    if args.doublons:
        print(gras("=" * 60))
        print(gras("  ÉTAPE 1 — Suppression des doublons"))
        print(gras("=" * 60))
        doublons = trouver_doublons(racine, recursif=args.recursif)
        journal_dup = supprimer_doublons(
            doublons,
            simulation=args.simulation,
            corbeille=args.corbeille,
            racine=racine,
        )
        journal_global["doublons"] = journal_dup

    # ── 2. Renommage ─────────────────────────────────────────────────────────
    if args.renommer:
        print(gras("=" * 60))
        print(gras("  ÉTAPE 2 — Renommage normalisé"))
        print(gras("=" * 60))
        journal_ren = renommer_fichiers(
            racine,
            format_date=fmt,
            recursif=args.recursif,
            simulation=args.simulation,
        )
        journal_global["renommage"] = journal_ren

    # ── 3. Classement ────────────────────────────────────────────────────────
    if args.classer:
        print(gras("=" * 60))
        print(gras("  ÉTAPE 3 — Classement par date"))
        print(gras("=" * 60))
        journal_cls = classer_par_date(
            racine,
            par_mois=not args.sans_mois,
            recursif=args.recursif_classer,
            simulation=args.simulation,
        )
        journal_global["classement"] = journal_cls

    # ── Journal ──────────────────────────────────────────────────────────────
    if not args.simulation and journal_global:
        sauvegarder_journal(racine, journal_global)

    print(f"\n{gras('Terminé.')}\n")


if __name__ == "__main__":
    main()
