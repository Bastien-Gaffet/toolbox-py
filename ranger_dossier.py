#!/usr/bin/env python3
"""
ranger_dossier.py
Organise les fichiers d'un dossier en sous-dossiers thématiques
selon leur extension. Fonctionne aussi pour les dossiers de téléchargements.

Usage :
    python ranger_dossier.py                  # range le dossier courant
    python ranger_dossier.py /chemin/dossier  # range un dossier spécifique
    python ranger_dossier.py --simulation     # aperçu sans déplacer
    python ranger_dossier.py --annuler        # annule le dernier rangement
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime


def _init_terminal():
    """Sortie UTF-8 (cadres, accents) + couleurs ANSI sous Windows."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if os.name == "nt":
        try:
            import ctypes
            noyau = ctypes.windll.kernel32
            for std in (-11, -12):
                handle = noyau.GetStdHandle(std)
                mode = ctypes.c_uint32()
                if noyau.GetConsoleMode(handle, ctypes.byref(mode)):
                    noyau.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


_init_terminal()

# ─── Catégories et extensions ────────────────────────────────────────────────

CATEGORIES = {

    "Documents/PDF": [
        ".pdf",
    ],

    "Documents/Texte": [
        ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".markdown",
        ".tex", ".rst", ".wpd", ".pages", ".wps", ".abw", ".fodt",
    ],

    "Documents/Tableurs": [
        ".xls", ".xlsx", ".ods", ".csv", ".tsv", ".numbers",
        ".xlsm", ".xlsb", ".xltx", ".fods",
    ],

    "Documents/Présentations": [
        ".ppt", ".pptx", ".odp", ".key", ".fodp", ".pps", ".ppsx",
    ],

    "Documents/Notes & Données": [
        ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".conf", ".log", ".nfo", ".info",
    ],

    "Images/Photos": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
        ".webp", ".heic", ".heif", ".raw", ".cr2", ".cr3", ".nef",
        ".arw", ".dng", ".orf", ".rw2", ".pef",
    ],

    "Images/Graphisme & Vectoriel": [
        ".svg", ".ai", ".eps", ".psd", ".psb", ".xcf", ".cdr",
        ".afphoto", ".afdesign", ".sketch", ".fig", ".xd",
        ".indd", ".pub",
    ],

    "Audio": [
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
        ".opus", ".aiff", ".aif", ".ape", ".mka", ".mid", ".midi",
        ".amr", ".au", ".ra",
    ],

    "Vidéo": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp", ".3g2", ".ts", ".mts",
        ".m2ts", ".vob", ".ogv", ".rm", ".rmvb", ".divx", ".f4v",
    ],

    "Archives & Compression": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz", ".lz", ".lzma",
        ".zst", ".cab", ".iso", ".dmg", ".img", ".z", ".lzh",
        ".ace", ".arj",
    ],

    "Exécutables & Installateurs": [
        ".exe", ".msi", ".msix", ".appx",            # Windows
        ".dmg", ".pkg", ".app",                       # macOS
        ".deb", ".rpm", ".flatpak", ".snap", ".appimage",  # Linux
        ".apk", ".ipa",                               # Mobile
        ".run", ".bin", ".sh",                        # Scripts/Linux
        ".arm", ".arm64", ".aarch64",                 # ARM
        ".com", ".bat", ".cmd", ".ps1",               # Windows scripts
    ],

    "Code Source": [
        ".py", ".pyw", ".ipynb",                      # Python
        ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", # JavaScript/TS
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".php", ".rb", ".java", ".kt", ".swift",
        ".c", ".h", ".cpp", ".hpp", ".cc", ".cs",
        ".go", ".rs", ".dart", ".lua", ".pl", ".r",
        ".vb", ".vbs", ".asm", ".s",
        ".sql", ".db", ".sqlite", ".sqlite3",
        ".m", ".mat",                                 # MATLAB
        ".f", ".f90", ".for",                         # Fortran
    ],

    "Web & Raccourcis": [
        ".html", ".htm", ".url", ".webloc", ".lnk", ".desktop",
        ".mhtml", ".maff",
    ],

    "Polices": [
        ".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon", ".pfb",
        ".pfm", ".afm",
    ],

    "Paquets & Dépendances": [
        ".whl", ".egg",                               # Python
        ".jar", ".war", ".ear",                       # Java
        ".nupkg", ".vsix",                            # .NET / VSCode
        ".gem",                                       # Ruby
        ".npm",                                       # Node
    ],

    "Sécurité & Certificats": [
        ".pem", ".crt", ".cer", ".key", ".p12", ".pfx", ".p7b",
        ".gpg", ".asc", ".sig",
    ],

    "Impression & Mise en page": [
        ".ps", ".prn", ".xps", ".oxps",
    ],

    "Fichiers Système & Divers": [
        ".dll", ".sys", ".drv", ".ocx",               # Windows système
        ".so", ".dylib",                               # Linux/macOS libs
        ".bak", ".tmp", ".temp", ".swp", ".swo",      # Temporaires
        ".dat", ".bin",                                # Données binaires
        ".torrent",                                    # BitTorrent
        ".vhd", ".vhdx", ".vmdk", ".ova", ".ovf",    # Machines virtuelles
        ".crdownload", ".part",                        # Téléchargements incomplets
    ],
}

# Dossier de repli pour les extensions inconnues
DOSSIER_DIVERS = "Divers"

# Extensions à ne jamais déplacer (fichiers système invisibles, etc.)
EXTENSIONS_IGNOREES = {".ds_store", ".localized"}
NOMS_IGNORES = {"desktop.ini", "thumbs.db", ".gitignore", ".gitkeep"}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def construire_index_extensions(categories: dict) -> dict:
    """Construit un dictionnaire {extension: catégorie}."""
    index = {}
    for categorie, extensions in categories.items():
        for ext in extensions:
            # Ne pas écraser si déjà mappé (priorité à la première catégorie)
            if ext not in index:
                index[ext] = categorie
    return index


def trouver_categorie(fichier: Path, index: dict) -> str:
    """Retourne la catégorie d'un fichier selon son extension."""
    # Cas spécial : .tar.gz, .tar.bz2, etc.
    nom = fichier.name.lower()
    for ext_composee in [".tar.gz", ".tar.bz2", ".tar.xz"]:
        if nom.endswith(ext_composee):
            return index.get(ext_composee, DOSSIER_DIVERS)

    ext = fichier.suffix.lower()
    return index.get(ext, DOSSIER_DIVERS)


def destination_unique(dest: Path) -> Path:
    """Retourne un chemin sans collision (ajoute _2, _3… si nécessaire)."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffixe = dest.suffix
    parent = dest.parent
    compteur = 2
    while True:
        nouveau = parent / f"{stem}_{compteur}{suffixe}"
        if not nouveau.exists():
            return nouveau
        compteur += 1


# ─── Coeur du rangement ──────────────────────────────────────────────────────

def analyser_dossier(racine: Path, index: dict, recursif: bool = False) -> list:
    """
    Analyse les fichiers du dossier racine et retourne la liste des
    déplacements prévus : [(source, destination), …].

    Par défaut : 1 niveau (fichiers directement dans racine).
    Avec recursif=True : parcourt tous les sous-dossiers et range les fichiers
    dans des catégories au niveau de racine, en ignorant ceux déjà classés
    (déjà sous un dossier de catégorie).
    """
    mouvements = []
    # Racines de catégorie ("Images", "Documents", "Vidéo", …, "Divers") :
    # en récursif, on ne re-range pas ce qui est déjà dedans.
    cat_roots = {cle.split("/")[0] for cle in CATEGORIES} | {DOSSIER_DIVERS}

    entrees = racine.rglob("*") if recursif else racine.iterdir()
    for entree in sorted(entrees):
        # Ignorer les dossiers et les fichiers système
        if entree.is_dir():
            continue
        if entree.name.lower() in NOMS_IGNORES:
            continue
        if entree.suffix.lower() in EXTENSIONS_IGNOREES:
            continue
        if entree.name == Path(__file__).name:
            continue
        if entree.name.startswith(".rangement_"):   # journaux d'annulation
            continue
        # En récursif : ignorer ce qui est déjà dans un dossier de catégorie
        if recursif:
            rel = entree.relative_to(racine)
            if rel.parts and rel.parts[0] in cat_roots:
                continue

        categorie = trouver_categorie(entree, index)
        dossier_dest = racine / categorie
        dest = destination_unique(dossier_dest / entree.name)
        mouvements.append((entree, dest))

    return mouvements


def afficher_apercu(mouvements: list, racine: Path):
    """Affiche un tableau des déplacements prévus."""
    if not mouvements:
        print("  Aucun fichier à déplacer.")
        return

    # Regrouper par catégorie pour un affichage lisible
    par_categorie: dict = {}
    for src, dst in mouvements:
        cat = dst.parent.relative_to(racine)
        par_categorie.setdefault(str(cat), []).append(src.name)

    print(f"\n  {'─'*56}")
    print(f"  {'CATÉGORIE':<40} {'FICHIERS':>6}")
    print(f"  {'─'*56}")
    total = 0
    for cat, fichiers in sorted(par_categorie.items()):
        print(f"  {cat:<40} {len(fichiers):>6}")
        total += len(fichiers)
    print(f"  {'─'*56}")
    print(f"  {'TOTAL':<40} {total:>6}")
    print(f"  {'─'*56}\n")


def executer_mouvements(mouvements: list) -> list:
    """
    Déplace les fichiers. Retourne le journal des actions effectuées.
    """
    journal = []
    erreurs = 0

    for src, dst in mouvements:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            journal.append({"src": str(src), "dst": str(dst), "ok": True})
            print(f"  OK  {src.name:<45} -> {dst.parent.name}")
        except Exception as e:
            journal.append({"src": str(src), "dst": str(dst), "ok": False, "erreur": str(e)})
            print(f"  ERR {src.name:<45} -> ERREUR : {e}")
            erreurs += 1

    return journal


def sauvegarder_journal(racine: Path, journal: list) -> Path:
    """Sauvegarde le journal JSON pour pouvoir annuler."""
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = racine / f".rangement_{horodatage}.json"
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)
    return chemin


def annuler_dernier_rangement(racine: Path):
    """Annule le dernier rangement en utilisant le journal JSON."""
    journaux = sorted(racine.glob(".rangement_*.json"), reverse=True)
    if not journaux:
        print("  [!] Aucun journal de rangement trouvé dans ce dossier.")
        return

    dernier = journaux[0]
    print(f"  Journal utilisé : {dernier.name}\n")

    with open(dernier, encoding="utf-8") as f:
        journal = json.load(f)

    annules = 0
    for entree in reversed(journal):
        if not entree.get("ok"):
            continue
        src = Path(entree["dst"])
        dst = Path(entree["src"])
        if src.exists():
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"  <- {src.name}")
                annules += 1
            except Exception as e:
                print(f"  ERR {src.name} -> {e}")

    # Supprimer les dossiers vides créés lors du rangement
    for entree in journal:
        dossier = Path(entree["dst"]).parent
        try:
            if dossier.exists() and not any(dossier.iterdir()):
                dossier.rmdir()
        except Exception:
            pass

    dernier.unlink()
    print(f"\n  {annules} fichier(s) remis en place.")


# ─── Interface CLI ────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Range les fichiers d'un dossier par catégorie.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python ranger_dossier.py                        # range le dossier courant
  python ranger_dossier.py ~/Téléchargements      # range les téléchargements
  python ranger_dossier.py . --simulation         # aperçu sans déplacer
  python ranger_dossier.py . --annuler            # annule le dernier rangement
        """
    )
    parser.add_argument(
        "dossier", nargs="?", default=".",
        help="Dossier à ranger (défaut : dossier courant)"
    )
    parser.add_argument(
        "-s", "--simulation", action="store_true",
        help="Affiche ce qui serait fait sans déplacer aucun fichier"
    )
    parser.add_argument(
        "-r", "--recursif", action="store_true",
        help="Parcourt les sous-dossiers et range tout au niveau du dossier cible"
    )
    parser.add_argument(
        "-a", "--annuler", action="store_true",
        help="Annule le dernier rangement effectué (utilise le journal)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Affiche le détail de chaque fichier en mode simulation"
    )
    return parser.parse_args()


# ─── Point d'entrée ──────────────────────────────────────────────────────────

def main():
    args = parse_args()

    racine = Path(args.dossier).resolve()
    if not racine.exists() or not racine.is_dir():
        print(f"Dossier introuvable : {racine}")
        sys.exit(1)

    print(f"\nDossier cible : {racine}\n")

    # Mode annulation
    if args.annuler:
        print("Annulation du dernier rangement...\n")
        annuler_dernier_rangement(racine)
        return

    # Analyse
    index = construire_index_extensions(CATEGORIES)
    mouvements = analyser_dossier(racine, index, recursif=args.recursif)

    if not mouvements:
        if args.recursif:
            print("Aucun fichier à ranger (déjà classé, ou dossier vide).")
        else:
            print("Le dossier est déjà vide ou ne contient que des dossiers.")
            print("Astuce : ajoutez -r/--recursif pour ranger aussi les sous-dossiers.")
        return

    afficher_apercu(mouvements, racine)

    # Mode simulation
    if args.simulation:
        print("MODE SIMULATION — aucun fichier déplacé.\n")
        if args.verbose:
            for src, dst in mouvements:
                cat = dst.parent.relative_to(racine)
                print(f"  {src.name:<50} -> {cat}")
        return

    # Confirmation
    reponse = input(f"  Déplacer {len(mouvements)} fichier(s) ? [o/N] : ").strip().lower()
    if reponse not in ("o", "oui", "y", "yes"):
        print("  Annulé.")
        return

    print()
    journal = executer_mouvements(mouvements)
    chemin_journal = sauvegarder_journal(racine, journal)

    ok      = sum(1 for e in journal if e.get("ok"))
    echecs  = len(journal) - ok
    print(f"\n  {ok} fichier(s) déplacé(s)", end="")
    if echecs:
        print(f"  |  {echecs} erreur(s)", end="")
    print(f"\n  Journal sauvegardé : {chemin_journal.name}")
    print(f"  Pour annuler : python ranger_dossier.py {args.dossier} --annuler\n")


if __name__ == "__main__":
    main()
