#!/usr/bin/env python3
"""
extracteur_archives.py
Décompresse en masse les archives d'un dossier, chacune dans son propre
sous-dossier nommé d'après l'archive.

Formats natifs (aucune dépendance) :
    .zip
    .tar, .tar.gz/.tgz, .tar.bz2/.tbz2, .tar.xz/.txz
    .gz  (fichier unique compressé)
Formats optionnels :
    .7z   → pip install py7zr
    .rar  → pip install rarfile  (+ outil unrar/7z dans le PATH)

Usage :
    python extracteur_archives.py                 # dossier courant
    python extracteur_archives.py ./telechargements
    python extracteur_archives.py archive.zip     # une archive précise
    python extracteur_archives.py ./dl --simulation
    python extracteur_archives.py ./dl --recursif
    python extracteur_archives.py ./dl --supprimer
"""

import os
import sys
import gzip
import shutil
import tarfile
import zipfile
import argparse
from pathlib import Path


def _init_terminal():
    """Sortie UTF-8 (emojis, accents) + couleurs ANSI sous Windows."""
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

# ─── Couleurs terminal (colorama optionnel) ──────────────────────────────────
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    def rouge(t): return Fore.RED     + t + Style.RESET_ALL
    def vert(t):  return Fore.GREEN   + t + Style.RESET_ALL
    def jaune(t): return Fore.YELLOW  + t + Style.RESET_ALL
    def cyan(t):  return Fore.CYAN    + t + Style.RESET_ALL
    def gras(t):  return Style.BRIGHT + t + Style.RESET_ALL
    def dim(t):   return Style.DIM    + t + Style.RESET_ALL
except ImportError:
    def rouge(t): return t
    def vert(t):  return t
    def jaune(t): return t
    def cyan(t):  return t
    def gras(t):  return t
    def dim(t):   return t


# Suffixes composés (à retirer en entier pour nommer le dossier cible)
SUFFIXES_TAR = (".tar.gz", ".tar.bz2", ".tar.xz")
EXT_TAR = SUFFIXES_TAR + (".tgz", ".tbz2", ".tbz", ".txz", ".tar")
EXT_ZIP = (".zip",)
EXT_7Z = (".7z",)
EXT_RAR = (".rar",)


def type_archive(chemin: Path) -> str | None:
    """Retourne 'zip' / 'tar' / 'gz' / '7z' / 'rar' selon l'extension, sinon None."""
    nom = chemin.name.lower()
    if nom.endswith(EXT_ZIP):
        return "zip"
    if nom.endswith(EXT_TAR):
        return "tar"
    if nom.endswith(EXT_7Z):
        return "7z"
    if nom.endswith(EXT_RAR):
        return "rar"
    if nom.endswith(".gz"):          # .gz simple (pas .tar.gz, déjà traité)
        return "gz"
    return None


def nom_cible(chemin: Path) -> str:
    """Nom du sous-dossier de destination (retire l'extension, même composée)."""
    nom = chemin.name
    bas = nom.lower()
    for suf in SUFFIXES_TAR:
        if bas.endswith(suf):
            return nom[: -len(suf)]
    if bas.endswith(".gz"):          # fichier.txt.gz → fichier.txt
        return nom[: -3]
    return chemin.stem


def dossier_unique(base: Path) -> Path:
    """Retourne un chemin de dossier sans collision (_2, _3…)."""
    if not base.exists():
        return base
    i = 2
    while True:
        cand = base.parent / f"{base.name}_{i}"
        if not cand.exists():
            return cand
        i += 1


def fichier_unique(base: Path) -> Path:
    """Retourne un chemin de fichier sans collision (_2, _3…)."""
    if not base.exists():
        return base
    i = 2
    while True:
        cand = base.parent / f"{base.stem}_{i}{base.suffix}"
        if not cand.exists():
            return cand
        i += 1


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTION PAR FORMAT
# ═══════════════════════════════════════════════════════════════════════════

def extraire_zip(src: Path, dest: Path):
    with zipfile.ZipFile(src) as z:
        z.extractall(dest)          # extractall assainit les noms (pas de chemin absolu)


def extraire_tar(src: Path, dest: Path):
    with tarfile.open(src) as t:
        # filter='data' (Python 3.12+) bloque les chemins dangereux (../, absolus)
        try:
            t.extractall(dest, filter="data")
        except TypeError:
            t.extractall(dest)


def extraire_gz(src: Path, cible: Path):
    """Fichier .gz unique → décompresse directement vers le fichier `cible`."""
    cible.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(src, "rb") as f_in, open(cible, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def extraire_7z(src: Path, dest: Path):
    try:
        import py7zr
    except ImportError:
        raise RuntimeError("format .7z non supporté (pip install py7zr)")
    with py7zr.SevenZipFile(src, mode="r") as z:
        z.extractall(dest)


def extraire_rar(src: Path, dest: Path):
    try:
        import rarfile
    except ImportError:
        raise RuntimeError("format .rar non supporté (pip install rarfile + outil unrar)")
    with rarfile.RarFile(src) as r:
        r.extractall(dest)


# Formats « multi-fichiers » → extraits dans un sous-dossier dédié.
# Le .gz simple est traité à part (fichier unique, pas de sous-dossier).
EXTRACTEURS = {
    "zip": extraire_zip,
    "tar": extraire_tar,
    "7z":  extraire_7z,
    "rar": extraire_rar,
}


# ═══════════════════════════════════════════════════════════════════════════
# COLLECTE
# ═══════════════════════════════════════════════════════════════════════════

def collecter(source: Path, recursif: bool) -> list:
    """Retourne la liste des archives trouvées (fichier unique ou dossier)."""
    if source.is_file():
        return [source] if type_archive(source) else []
    motif = source.rglob("*") if recursif else source.glob("*")
    return sorted(f for f in motif if f.is_file() and type_archive(f))


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="📦 Décompresse en masse les archives d'un dossier.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python extracteur_archives.py                 (dossier courant)
  python extracteur_archives.py ./telechargements
  python extracteur_archives.py archive.zip
  python extracteur_archives.py ./dl --simulation
  python extracteur_archives.py ./dl --recursif --supprimer
""",
    )
    p.add_argument("source", nargs="?", default=".",
                   help="Dossier à parcourir ou archive unique (défaut : dossier courant)")
    p.add_argument("-o", "--sortie", metavar="DOSSIER",
                   help="Dossier de base pour les extractions (défaut : à côté de l'archive)")
    p.add_argument("-r", "--recursif", action="store_true",
                   help="Chercher aussi dans les sous-dossiers")
    p.add_argument("-s", "--simulation", action="store_true",
                   help="Aperçu sans rien extraire")
    p.add_argument("--supprimer", action="store_true",
                   help="Supprimer l'archive après extraction réussie")
    return p.parse_args()


def main():
    args = parse_args()
    source = Path(args.source).resolve()

    if not source.exists():
        print(rouge(f"❌ Introuvable : {source}"))
        sys.exit(1)

    archives = collecter(source, args.recursif)
    mode = rouge(" [SIMULATION]") if args.simulation else ""
    print(f"\n{gras('📦 extracteur_archives.py')}{mode}\n")

    if not archives:
        print(jaune("  Aucune archive trouvée."))
        return

    print(f"  {len(archives)} archive(s) trouvée(s) :\n")

    base_sortie = Path(args.sortie).resolve() if args.sortie else None
    compteurs = {"ok": 0, "ignore": 0, "erreur": 0}

    for arc in archives:
        typ = type_archive(arc)
        parent = base_sortie if base_sortie else arc.parent

        # Cible : un fichier pour .gz simple, un sous-dossier pour le reste.
        if typ == "gz":
            cible = fichier_unique(parent / arc.name[:-3])
            etiquette = f"{arc.name}  →  {cible.name}"
        else:
            cible = dossier_unique(parent / nom_cible(arc))
            etiquette = f"{arc.name}  →  {cible.name}{os.sep}"

        if args.simulation:
            print(f"  {cyan('◌')} {etiquette}  {dim('[' + typ + ']')}")
            continue

        try:
            if typ == "gz":
                extraire_gz(arc, cible)
            else:
                cible.mkdir(parents=True, exist_ok=True)
                EXTRACTEURS[typ](arc, cible)
            print(f"  {vert('✓')} {etiquette}")
            compteurs["ok"] += 1
            if args.supprimer:
                arc.unlink()
                print(f"      {dim('archive supprimée')}")
        except RuntimeError as e:          # format optionnel non installé
            if typ != "gz" and cible.exists() and not any(cible.iterdir()):
                cible.rmdir()
            print(f"  {jaune('⊘')} {arc.name}  {dim('— ' + str(e))}")
            compteurs["ignore"] += 1
        except Exception as e:
            print(f"  {rouge('✗')} {arc.name}  {rouge('— ' + str(e))}")
            compteurs["erreur"] += 1

    ok, ignore, erreur = compteurs["ok"], compteurs["ignore"], compteurs["erreur"]
    if not args.simulation:
        print(f"\n  {'─'*50}")
        resume = f"  {vert(str(ok) + ' extraite(s)')}"
        if ignore:
            resume += f"  |  {jaune(str(ignore) + ' ignorée(s)')}"
        if erreur:
            resume += f"  |  {rouge(str(erreur) + ' erreur(s)')}"
        print(resume + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(jaune("\nInterrompu."))
        sys.exit(130)
