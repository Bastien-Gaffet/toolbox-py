#!/usr/bin/env python3
"""
nettoyer_dossier.py
Supprime les fichiers inutiles : temporaires, systeme (.DS_Store, Thumbs.db),
dossiers vides, et fichiers dupliques par le nom (_copie, (1), - Copie...).

Usage :
    python nettoyer_dossier.py ./dossier --simulation
    python nettoyer_dossier.py ./dossier --forcer
    python nettoyer_dossier.py ./dossier --forcer --dossiers-vides
"""

import os
import re
import sys
import argparse
from pathlib import Path

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

# ─── Categories de fichiers inutiles ──────────────────────────────────────────

# Noms exacts a supprimer
NOMS_SYSTEME = {
    "Thumbs.db", "thumbs.db", "ehthumbs.db",
    ".DS_Store", "._.DS_Store",
    "desktop.ini", "Desktop.ini",
    ".Spotlight-V100", ".Trashes",
    "RECYCLER", "$RECYCLE.BIN",
}

# Extensions de fichiers temporaires
EXT_TEMP = {
    ".tmp", ".temp", ".bak", ".old", ".orig",
    ".swp", ".swo",    # vim
    ".pyc", ".pyo",    # Python bytecode
    ".log",            # logs (optionnel, voir --logs)
}

# Prefixes de fichiers temporaires (Windows Office)
PREFIXES_TEMP = ("~$",)

# Regex pour detecter les noms dupliques typiques
# Exemples : "fichier (1).pdf", "fichier_copie.pdf", "fichier - Copie.pdf",
#            "fichier copy.pdf", "fichier (2).pdf", "fichier_1.pdf" (si numerique seul)
RE_DUPLIC = re.compile(
    r"(.+?)"                              # nom de base
    r"(?:"
    r"\s*\(\d+\)"                         # (1), (2), ...
    r"|[ _-]+[Cc]opie\d*"                 # _copie, _Copie2, - copie
    r"|[ _-]+[Cc]opy\d*"                  # _copy, - Copy
    r"|[ _-]+\d{1,3}$"                    # _1, _02 (seulement si suffix numerique pur)
    r")"
    r"(\.\w+)?$"                          # extension
)

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} To"


def est_nom_systeme(chemin: Path) -> bool:
    return chemin.name in NOMS_SYSTEME or chemin.name.startswith("._")


def est_temp(chemin: Path) -> bool:
    if chemin.suffix.lower() in EXT_TEMP:
        return True
    return any(chemin.name.startswith(p) for p in PREFIXES_TEMP)


def est_duplic(chemin: Path) -> bool:
    """Detecte si le nom suggere une copie (ex: fichier (1).pdf)."""
    return bool(RE_DUPLIC.match(chemin.stem))

# ─── Analyse ──────────────────────────────────────────────────────────────────

def analyser(dossier: Path, recursif: bool, inclure_logs: bool,
             inclure_duplic: bool) -> dict[str, list]:
    """Retourne les fichiers classes par categorie."""
    resultats = {
        "systeme": [],
        "temp":    [],
        "duplic":  [],
    }

    motif = "**/*" if recursif else "*"
    for chemin in dossier.glob(motif):
        if not chemin.is_file():
            continue
        if est_nom_systeme(chemin):
            resultats["systeme"].append(chemin)
        elif est_temp(chemin):
            if chemin.suffix.lower() == ".log" and not inclure_logs:
                continue
            resultats["temp"].append(chemin)
        elif inclure_duplic and est_duplic(chemin):
            resultats["duplic"].append(chemin)

    return resultats


def trouver_dossiers_vides(dossier: Path) -> list[Path]:
    """Retourne les dossiers vides dans l'ordre inverse (feuilles en premier)."""
    vides = []
    for chemin in sorted(dossier.rglob("*"), reverse=True):
        if chemin.is_dir() and not any(chemin.iterdir()):
            vides.append(chemin)
    return vides

# ─── Affichage ────────────────────────────────────────────────────────────────

def afficher_categorie(label: str, fichiers: list[Path], max_lignes: int = 15):
    if not fichiers:
        return
    total_taille = sum(f.stat().st_size for f in fichiers if f.exists())
    print(f"\n  {label} ({len(fichiers)}) — {taille_lisible(total_taille)} :")
    for f in fichiers[:max_lignes]:
        try:
            taille = taille_lisible(f.stat().st_size)
        except OSError:
            taille = "?"
        print(f"    {rouge('-')} {f.name:<50} {dim(taille)}")
    if len(fichiers) > max_lignes:
        print(dim(f"    ... et {len(fichiers) - max_lignes} autres"))


def taille_totale(fichiers: list[Path]) -> int:
    total = 0
    for f in fichiers:
        try:
            total += f.stat().st_size
        except OSError:
            pass
    return total

# ─── Suppression ──────────────────────────────────────────────────────────────

def supprimer_fichiers(fichiers: list[Path]) -> tuple[int, int]:
    ok = ko = 0
    for f in fichiers:
        try:
            f.unlink()
            ok += 1
        except OSError as e:
            print(rouge(f"  ERR {f.name} : {e}"))
            ko += 1
    return ok, ko


def supprimer_dossiers_vides(dossiers: list[Path]) -> tuple[int, int]:
    ok = ko = 0
    for d in dossiers:
        try:
            d.rmdir()
            ok += 1
        except OSError as e:
            print(rouge(f"  ERR {d.name} : {e}"))
            ko += 1
    return ok, ko

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Supprime les fichiers inutiles d'un dossier.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Fichiers cibles par defaut :
  - Systeme  : Thumbs.db, .DS_Store, desktop.ini, fichiers ._ ...
  - Temp     : *.tmp, *.temp, *.bak, *.old, *.orig, *.swp, ~$*
  - (option) Copies : fichier (1).pdf, fichier_copie.pdf, fichier - Copie.pdf

Exemples :
  python nettoyer_dossier.py ./Téléchargements --simulation
  python nettoyer_dossier.py ./docs --forcer --dossiers-vides
  python nettoyer_dossier.py ./photos --forcer --duplic --logs -r
        """
    )
    parser.add_argument("dossier", help="Dossier a nettoyer")
    parser.add_argument("-r", "--recursif", action="store_true",
                        help="Traiter les sous-dossiers recursivement")
    parser.add_argument("--duplic", action="store_true",
                        help="Inclure les fichiers dupliques par le nom (_copie, (1), etc.)")
    parser.add_argument("--logs", action="store_true",
                        help="Inclure les fichiers .log")
    parser.add_argument("--dossiers-vides", action="store_true",
                        help="Supprimer les dossiers vides")
    parser.add_argument("-s", "--simulation", action="store_true", default=True,
                        help="Simuler sans supprimer (actif par defaut)")
    parser.add_argument("-f", "--forcer", action="store_true",
                        help="Supprimer reellement les fichiers (desactive la simulation)")
    return parser.parse_args()


def main():
    args = parse_args()
    simulation = not args.forcer  # --forcer desactive la simulation

    dossier = Path(args.dossier)
    if not dossier.is_dir():
        print(rouge(f"Dossier introuvable : {dossier}"))
        sys.exit(1)

    print(f"\n{gras('=== Nettoyage de dossier ===')}")
    print(f"  Dossier : {dossier}")
    if simulation:
        print(jaune("  Mode : SIMULATION (utilisez --forcer pour supprimer reellement)"))
    else:
        print(rouge("  Mode : SUPPRESSION REELLE"))

    resultats = analyser(dossier, args.recursif, args.logs, args.duplic)

    dossiers_vides = []
    if args.dossiers_vides:
        dossiers_vides = trouver_dossiers_vides(dossier)

    tous_fichiers = (resultats["systeme"] + resultats["temp"] + resultats["duplic"])
    taille_totale_bytes = taille_totale(tous_fichiers)

    if not tous_fichiers and not dossiers_vides:
        print(vert("\n  Aucun fichier inutile trouve. Le dossier est propre."))
        return

    afficher_categorie("Fichiers systeme", resultats["systeme"])
    afficher_categorie("Fichiers temporaires", resultats["temp"])
    afficher_categorie("Copies dupliquees", resultats["duplic"])

    if dossiers_vides:
        print(f"\n  Dossiers vides ({len(dossiers_vides)}) :")
        for d in dossiers_vides[:10]:
            print(f"    {rouge('-')} {d}")
        if len(dossiers_vides) > 10:
            print(dim(f"    ... et {len(dossiers_vides) - 10} autres"))

    print(f"\n{gras('---')}")
    print(f"  Total : {len(tous_fichiers)} fichier(s) — {taille_lisible(taille_totale_bytes)}")
    if dossiers_vides:
        print(f"          {len(dossiers_vides)} dossier(s) vide(s)")

    if simulation:
        print(jaune("\n(simulation : aucun fichier n'a ete supprime)"))
        print(dim("  Relancez avec --forcer pour effectuer le nettoyage."))
        return

    # Confirmation
    print(f"\nSupprimer {len(tous_fichiers)} fichier(s)"
          + (f" et {len(dossiers_vides)} dossier(s) vide(s)" if dossiers_vides else "")
          + f" ? [o/N] : ", end="")
    if input().strip().lower() != "o":
        print(jaune("Annule."))
        sys.exit(0)

    total_ok = total_ko = 0
    for categorie in ("systeme", "temp", "duplic"):
        if resultats[categorie]:
            ok, ko = supprimer_fichiers(resultats[categorie])
            total_ok += ok
            total_ko += ko

    if dossiers_vides:
        ok, ko = supprimer_dossiers_vides(dossiers_vides)
        print(f"  {ok} dossier(s) vide(s) supprime(s)")

    print(f"\n  {vert(str(total_ok))} fichier(s) supprime(s)"
          + (f"  /  {rouge(str(total_ko))} echec(s)" if total_ko else ""))
    print(f"  Espace recupere : {taille_lisible(taille_totale_bytes)}")


if __name__ == "__main__":
    main()
