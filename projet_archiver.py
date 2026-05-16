#!/usr/bin/env python3
"""
projet_archiver.py
Archive un projet dans un ZIP date en excluant les fichiers inutiles
(node_modules, __pycache__, .git, .env, dist, build, venv...).
Peut lire les regles d'un .gitignore existant.

Usage :
    python projet_archiver.py
    python projet_archiver.py ./mon_projet
    python projet_archiver.py ./mon_projet --sortie ../archives --simulation
    python projet_archiver.py ./mon_projet --exclure "*.log" "tmp/"
"""

import os
import sys
import zipfile
import fnmatch
import argparse
from pathlib import Path
from datetime import datetime

# ─── Couleurs terminal ────────────────────────────────────────────────────────

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

# ─── Exclusions par defaut ────────────────────────────────────────────────────

EXCLUSIONS_DEFAUT = {
    # Controle de version
    ".git", ".svn", ".hg",
    # Dependances
    "node_modules", "bower_components",
    "vendor",        # Go, PHP Composer
    ".venv", "venv", "env", ".env",
    # Build
    "__pycache__", "*.pyc", "*.pyo", "*.pyd",
    "dist", "build", ".next", ".nuxt", "out",
    "target",        # Rust / Java Maven
    "*.egg-info", ".eggs",
    # IDE
    ".idea", ".vscode", "*.suo", "*.user",
    # Secrets
    ".env", ".env.*", "*.pem", "*.key", "*.p12",
    # Temp / logs
    "*.log", "*.tmp", "*.temp",
    "Thumbs.db", ".DS_Store",
    # Coverage / tests artifacts
    ".coverage", "htmlcov", ".pytest_cache",
    ".mypy_cache", ".ruff_cache",
}

# ─── Lecture du .gitignore ────────────────────────────────────────────────────

def lire_gitignore(dossier: Path) -> set[str]:
    """Lit les patterns du .gitignore du projet."""
    motifs = set()
    gitignore = dossier / ".gitignore"
    if not gitignore.exists():
        return motifs
    for ligne in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and not ligne.startswith("!"):
            motifs.add(ligne.rstrip("/"))
    return motifs

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} To"


def est_exclu(chemin_relatif: Path, motifs: set[str]) -> bool:
    """Retourne True si le chemin (ou l'un de ses parents) correspond a un motif d'exclusion."""
    parties = chemin_relatif.parts
    for motif in motifs:
        # Tester chaque composant du chemin
        for partie in parties:
            if fnmatch.fnmatch(partie, motif):
                return True
        # Tester le chemin complet
        if fnmatch.fnmatch(str(chemin_relatif), motif):
            return True
        if fnmatch.fnmatch(str(chemin_relatif).replace("\\", "/"), motif):
            return True
    return False

# ─── Collecte des fichiers ────────────────────────────────────────────────────

def collecter_fichiers(source: Path, motifs: set[str]) -> list[tuple[Path, Path]]:
    """Retourne la liste des (chemin_absolu, chemin_relatif_dans_zip)."""
    resultat = []
    for chemin in sorted(source.rglob("*")):
        if not chemin.is_file():
            continue
        relatif = chemin.relative_to(source.parent)
        if est_exclu(relatif, motifs):
            continue
        resultat.append((chemin, relatif))
    return resultat

# ─── Archive ──────────────────────────────────────────────────────────────────

def creer_archive(fichiers: list[tuple[Path, Path]], dest: Path,
                  niveau: int, simulation: bool) -> tuple[int, int]:
    """Cree le ZIP. Retourne (nb_fichiers, taille_totale)."""
    taille_totale = sum(f.stat().st_size for f, _ in fichiers)

    if simulation:
        return len(fichiers), taille_totale

    with zipfile.ZipFile(dest, "w",
                         compression=zipfile.ZIP_DEFLATED,
                         compresslevel=niveau) as zf:
        for chemin, relatif in fichiers:
            zf.write(chemin, relatif)

    return len(fichiers), taille_totale

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Archive un projet dans un ZIP date en excluant les fichiers inutiles.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python projet_archiver.py
  python projet_archiver.py ./mon_projet
  python projet_archiver.py ./mon_projet --sortie ../archives
  python projet_archiver.py . --exclure "data/" "*.csv" --simulation
  python projet_archiver.py . --sans-gitignore --compression 9
        """
    )
    parser.add_argument("source", nargs="?", default=".",
                        help="Dossier du projet a archiver (defaut : dossier courant)")
    parser.add_argument("--sortie", metavar="DIR",
                        help="Dossier de destination du ZIP (defaut : parent du projet)")
    parser.add_argument("--nom", metavar="NOM",
                        help="Nom de l'archive sans extension (defaut : nom_projet_date)")
    parser.add_argument("--exclure", nargs="+", metavar="MOTIF",
                        help="Motifs supplementaires a exclure (en plus des defauts)")
    parser.add_argument("--sans-gitignore", action="store_true",
                        help="Ignorer le fichier .gitignore du projet")
    parser.add_argument("--sans-defauts", action="store_true",
                        help="Ne pas appliquer les exclusions par defaut")
    parser.add_argument("--compression", type=int, default=6, metavar="N",
                        choices=range(10),
                        help="Niveau de compression 0-9 (defaut : 6)")
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Lister les fichiers sans creer l'archive")
    return parser.parse_args()


def main():
    args = parse_args()
    source = Path(args.source).resolve()

    if not source.is_dir():
        print(rouge(f"Dossier introuvable : {source}"))
        sys.exit(1)

    # Construire les motifs d'exclusion
    motifs: set[str] = set()
    if not args.sans_defauts:
        motifs |= EXCLUSIONS_DEFAUT
    if not args.sans_gitignore:
        gitignore_motifs = lire_gitignore(source)
        if gitignore_motifs:
            motifs |= gitignore_motifs
    if args.exclure:
        motifs |= set(args.exclure)

    # Nom et chemin de l'archive
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    nom_archive = args.nom or f"{source.name}_{date_str}"
    if not nom_archive.endswith(".zip"):
        nom_archive += ".zip"

    if args.sortie:
        dossier_sortie = Path(args.sortie)
        dossier_sortie.mkdir(parents=True, exist_ok=True)
    else:
        dossier_sortie = source.parent

    dest = dossier_sortie / nom_archive

    print(f"\n{gras('=== Archivage de projet ===')}")
    print(f"  Source    : {source}")
    print(f"  Archive   : {dest}")
    print(f"  Exclusions: {len(motifs)} motifs actifs")
    if args.simulation:
        print(jaune("  (simulation : aucun fichier ne sera cree)"))

    # Collecte
    print("\n  Analyse du projet...")
    fichiers = collecter_fichiers(source, motifs)

    if not fichiers:
        print(jaune("  Aucun fichier a archiver."))
        sys.exit(0)

    nb, taille = creer_archive(fichiers, dest, args.compression, args.simulation)

    print(f"  {nb} fichier(s) — {taille_lisible(taille)} non compresse(s)")

    if args.simulation:
        print(f"\n  Apercu des {min(20, nb)} premiers fichiers :")
        for _, rel in fichiers[:20]:
            print(dim(f"    {rel}"))
        if nb > 20:
            print(dim(f"    ... et {nb - 20} autres"))
    else:
        taille_zip = dest.stat().st_size
        ratio = (1 - taille_zip / max(taille, 1)) * 100
        print(vert(f"\n  Archive creee : {dest}"))
        print(dim(f"  {taille_lisible(taille)} -> {taille_lisible(taille_zip)} ({ratio:.0f}% de compression)"))


if __name__ == "__main__":
    main()
