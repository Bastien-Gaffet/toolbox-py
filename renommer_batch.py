#!/usr/bin/env python3
"""
renommer_batch.py
Renommage en masse de fichiers : chercher/remplacer, numerotation, casse,
nettoyage des caracteres speciaux, prefixe/suffixe.

Usage :
    python renommer_batch.py ./dossier --chercher "IMG_" --remplacer "Photo_"
    python renommer_batch.py ./dossier --numerot --casse titre
    python renommer_batch.py ./dossier --nettoyer --prefixe "2026_"
"""

import os
import re
import sys
import argparse
import unicodedata
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

# ─── Transformations ──────────────────────────────────────────────────────────

def appliquer_nettoyer(nom: str) -> str:
    """Supprime les caracteres speciaux, normalise les espaces et tirets."""
    # Normaliser les caracteres accentues (conserver les lettres, remplacer le reste)
    nom = unicodedata.normalize("NFC", nom)
    # Remplacer les caracteres interdits dans les noms de fichiers
    nom = re.sub(r'[\\/*?:"<>|]', "_", nom)
    # Remplacer les espaces multiples et tirets redondants
    nom = re.sub(r"[ \t]+", " ", nom).strip()
    nom = re.sub(r"[-_]{2,}", "_", nom)
    return nom


def appliquer_casse(nom: str, mode: str) -> str:
    if mode == "haut":
        return nom.upper()
    if mode == "bas":
        return nom.lower()
    if mode == "titre":
        return nom.title()
    return nom


def appliquer_chercher_remplacer(nom: str, chercher: str, remplacer: str,
                                  regex: bool, insensible: bool) -> str:
    if not chercher:
        return nom
    flags = re.IGNORECASE if insensible else 0
    if regex:
        return re.sub(chercher, remplacer, nom, flags=flags)
    if insensible:
        return re.sub(re.escape(chercher), remplacer, nom, flags=flags)
    return nom.replace(chercher, remplacer)


def construire_nom(nom_base: str, args, index: int, total: int) -> str:
    """Applique toutes les transformations au nom de base (sans extension)."""
    nom = nom_base

    if args.nettoyer:
        nom = appliquer_nettoyer(nom)

    if args.chercher is not None:
        nom = appliquer_chercher_remplacer(
            nom, args.chercher, args.remplacer or "",
            args.regex, args.insensible
        )

    if args.casse:
        nom = appliquer_casse(nom, args.casse)

    if args.prefixe:
        nom = args.prefixe + nom

    if args.suffixe:
        nom = nom + args.suffixe

    if args.numerot is not None:
        debut = args.numerot
        largeur = len(str(total + debut - 1))
        num = str(index + debut - 1).zfill(largeur)
        sep = args.sep_num
        nom = f"{num}{sep}{nom}"

    return nom

# ─── Collecte et validation ───────────────────────────────────────────────────

def collecter(dossier: Path, recursif: bool, glob_motif: str) -> list[Path]:
    motif = f"**/{glob_motif}" if recursif else glob_motif
    return sorted(p for p in dossier.glob(motif) if p.is_file())


def calculer_renames(fichiers: list[Path], args) -> list[tuple[Path, Path]]:
    """Retourne la liste des (chemin_source, chemin_destination) a renommer."""
    renames = []
    total = len(fichiers)

    for i, chemin in enumerate(fichiers, 1):
        stem = chemin.stem
        ext  = chemin.suffix

        if args.extension:
            ext_cible = ("." + args.extension.lstrip(".")) if args.extension else ext
        else:
            ext_cible = ext

        nouveau_stem = construire_nom(stem, args, i, total)

        if args.casse_ext:
            ext_cible = appliquer_casse(ext_cible, args.casse_ext)

        nouveau_nom = nouveau_stem + ext_cible
        destination = chemin.parent / nouveau_nom

        if destination != chemin:
            renames.append((chemin, destination))

    return renames


def detecter_conflits(renames: list[tuple[Path, Path]]) -> list[Path]:
    """Retourne les destinations en conflit (doublons ou fichier existant)."""
    destinations = [d for _, d in renames]
    conflits = []
    vus = set()
    for dest in destinations:
        if dest in vus:
            conflits.append(dest)
        vus.add(dest)
        if dest.exists() and not any(src == dest for src, _ in renames):
            conflits.append(dest)
    return list(set(conflits))

# ─── Affichage ────────────────────────────────────────────────────────────────

def afficher_apercu(renames: list[tuple[Path, Path]], max_lignes: int = 30):
    print()
    for i, (src, dst) in enumerate(renames):
        if i >= max_lignes:
            print(dim(f"  ... et {len(renames) - max_lignes} autres"))
            break
        print(f"  {cyan(src.name)}")
        print(f"  {vert('-> ' + dst.name)}")
        print()

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Renommage en masse de fichiers avec regles cumulables.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Les transformations sont appliquees dans cet ordre :
  1. --nettoyer   2. --chercher/--remplacer   3. --casse
  4. --prefixe    5. --suffixe                6. --numerot (ajoute avant tout)

Exemples :
  python renommer_batch.py ./photos --chercher "IMG_" --remplacer "Photo_"
  python renommer_batch.py ./docs --numerot --casse titre
  python renommer_batch.py ./dl --nettoyer --prefixe "2026_" --simulation
  python renommer_batch.py ./dossier --chercher "\\s+" --remplacer "_" --regex
        """
    )
    parser.add_argument("dossier", help="Dossier contenant les fichiers a renommer")

    grp_sub = parser.add_argument_group("Substitution")
    grp_sub.add_argument("--chercher", metavar="MOTIF",
                         help="Texte (ou regex avec --regex) a rechercher dans le nom")
    grp_sub.add_argument("--remplacer", metavar="TEXTE", default="",
                         help="Texte de remplacement (defaut : suppression)")
    grp_sub.add_argument("--regex", action="store_true",
                         help="Interpreter --chercher comme une expression reguliere")
    grp_sub.add_argument("-i", "--insensible", action="store_true",
                         help="Recherche insensible a la casse")

    grp_fmt = parser.add_argument_group("Formatage")
    grp_fmt.add_argument("--casse", choices=["haut", "bas", "titre"],
                         help="Changer la casse du nom")
    grp_fmt.add_argument("--casse-ext", choices=["haut", "bas"],
                         help="Changer la casse de l'extension")
    grp_fmt.add_argument("--nettoyer", action="store_true",
                         help="Supprimer les caracteres speciaux, normaliser espaces/tirets")
    grp_fmt.add_argument("--prefixe", metavar="STR",
                         help="Ajouter un prefixe au nom")
    grp_fmt.add_argument("--suffixe", metavar="STR",
                         help="Ajouter un suffixe au nom (avant l'extension)")
    grp_fmt.add_argument("--numerot", type=int, nargs="?", const=1, metavar="DEBUT",
                         help="Prefixer par un numero sequentiel (debut : 1 par defaut)")
    grp_fmt.add_argument("--sep-num", metavar="SEP", default="_",
                         help="Separateur entre numero et nom (defaut : '_')")
    grp_fmt.add_argument("--extension", metavar="EXT",
                         help="Remplacer l'extension (ex: jpg)")

    grp_filt = parser.add_argument_group("Filtres")
    grp_filt.add_argument("--motif", metavar="GLOB", default="*",
                          help="Motif glob pour filtrer les fichiers (defaut : *)")
    grp_filt.add_argument("-r", "--recursif", action="store_true",
                          help="Traiter les sous-dossiers recursivement")

    grp_ctrl = parser.add_argument_group("Controle")
    grp_ctrl.add_argument("-s", "--simulation", action="store_true",
                          help="Afficher les renames sans les executer")
    grp_ctrl.add_argument("-f", "--forcer", action="store_true",
                          help="Renommer sans demander de confirmation")

    return parser.parse_args()


def main():
    args = parse_args()

    # Verifier qu'au moins une transformation est demandee
    aucune_action = not any([
        args.chercher is not None, args.casse, args.casse_ext,
        args.nettoyer, args.prefixe, args.suffixe,
        args.numerot is not None, args.extension,
    ])
    if aucune_action:
        print(rouge("Aucune transformation specifiee. Ajoutez --chercher, --casse, --numerot, etc."))
        sys.exit(1)

    dossier = Path(args.dossier)
    if not dossier.is_dir():
        print(rouge(f"Dossier introuvable : {dossier}"))
        sys.exit(1)

    fichiers = collecter(dossier, args.recursif, args.motif)
    if not fichiers:
        print(jaune("Aucun fichier trouve."))
        sys.exit(0)

    renames = calculer_renames(fichiers, args)

    if not renames:
        print(jaune(f"Aucun fichier a renommer ({len(fichiers)} inchange(s))."))
        sys.exit(0)

    conflits = detecter_conflits(renames)
    if conflits:
        print(rouge(f"\n{len(conflits)} conflit(s) detecte(s) :"))
        for c in conflits:
            print(rouge(f"  {c.name}"))
        print(rouge("Annule. Modifiez vos regles pour eviter les doublons."))
        sys.exit(1)

    print(f"\n{gras('=== Renommage en masse ===')}")
    print(f"  {len(renames)} fichier(s) a renommer sur {len(fichiers)}")
    afficher_apercu(renames)

    if args.simulation:
        print(jaune("(simulation : aucun fichier ne sera renomme)"))
        return

    if not args.forcer:
        rep = input(f"Renommer {len(renames)} fichier(s) ? [o/N] : ").strip().lower()
        if rep != "o":
            print(jaune("Annule."))
            sys.exit(0)

    ok = ko = 0
    for src, dst in renames:
        try:
            src.rename(dst)
            ok += 1
        except OSError as e:
            print(rouge(f"  ERR {src.name} : {e}"))
            ko += 1

    print(f"\n  {vert(str(ok))} renomme(s)  /  {(rouge(str(ko)) if ko else str(ko))} echec(s)")


if __name__ == "__main__":
    main()
