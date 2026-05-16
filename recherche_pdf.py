#!/usr/bin/env python3
"""
recherche_pdf.py
Recherche un mot, une phrase ou une chaîne dans tous les PDF
d'un dossier et de ses sous-dossiers.

Dépendances : pip install pdfplumber colorama
"""

import os
import sys
import re
import argparse
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Module manquant. Installez-le avec : pip install pdfplumber")
    sys.exit(1)

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COULEURS = True
except ImportError:
    COULEURS = False


# ─── Helpers couleurs ────────────────────────────────────────────────────────

def rouge(t):    return (Fore.RED    + t + Style.RESET_ALL) if COULEURS else t
def vert(t):     return (Fore.GREEN  + t + Style.RESET_ALL) if COULEURS else t
def jaune(t):    return (Fore.YELLOW + t + Style.RESET_ALL) if COULEURS else t
def cyan(t):     return (Fore.CYAN   + t + Style.RESET_ALL) if COULEURS else t
def gras(t):     return (Style.BRIGHT + t + Style.RESET_ALL) if COULEURS else t


# ─── Extraction de texte ─────────────────────────────────────────────────────

def extraire_texte_page(page):
    """Extrait le texte d'une page pdfplumber (retourne '' si échec)."""
    try:
        texte = page.extract_text()
        return texte if texte else ""
    except Exception:
        return ""


# ─── Recherche dans un PDF ───────────────────────────────────────────────────

def chercher_dans_pdf(chemin_pdf: Path, motif: re.Pattern, contexte: int = 1):
    """
    Cherche le motif dans chaque page du PDF.
    Retourne une liste de dicts {page, ligne, extrait}.
    """
    resultats = []
    try:
        with pdfplumber.open(chemin_pdf) as pdf:
            for num_page, page in enumerate(pdf.pages, start=1):
                texte = extraire_texte_page(page)
                if not texte:
                    continue
                lignes = texte.splitlines()
                for num_ligne, ligne in enumerate(lignes, start=1):
                    if motif.search(ligne):
                        # Contexte : lignes avant/après
                        debut = max(0, num_ligne - 1 - contexte)
                        fin   = min(len(lignes), num_ligne + contexte)
                        extrait = "\n    ".join(lignes[debut:fin])
                        resultats.append({
                            "page":    num_page,
                            "ligne":   num_ligne,
                            "extrait": extrait,
                        })
    except Exception as e:
        resultats.append({"erreur": str(e)})
    return resultats


# ─── Parcours récursif ───────────────────────────────────────────────────────

def parcourir_dossier(racine: Path, motif: re.Pattern, contexte: int = 1):
    """
    Parcourt récursivement le dossier et recherche dans chaque PDF.
    Retourne (liste_resultats, nb_fichiers, nb_fichiers_avec_resultats).
    """
    tous_resultats = []
    nb_fichiers = 0
    nb_avec_resultats = 0

    pdfs = sorted(racine.rglob("*.pdf"))

    if not pdfs:
        print(jaune(f"\nAucun fichier PDF trouvé dans : {racine}"))
        return [], 0, 0

    for chemin_pdf in pdfs:
        nb_fichiers += 1
        resultats = chercher_dans_pdf(chemin_pdf, motif, contexte)

        # Cas erreur de lecture
        if resultats and "erreur" in resultats[0]:
            print(rouge(f"  Erreur lecture : {chemin_pdf.relative_to(racine)}"
                        f"  -> {resultats[0]['erreur']}"))
            continue

        if resultats:
            nb_avec_resultats += 1
            tous_resultats.append({
                "fichier":    chemin_pdf,
                "relatif":    chemin_pdf.relative_to(racine),
                "occurrences": resultats,
            })

    return tous_resultats, nb_fichiers, nb_avec_resultats


# ─── Affichage des résultats ─────────────────────────────────────────────────

def afficher_resultats(tous_resultats, motif: re.Pattern,
                       nb_fichiers: int, nb_avec_resultats: int,
                       verbose: bool = True):
    """Affiche les résultats de façon lisible dans le terminal."""

    print()
    print(gras("━" * 60))
    print(gras("  RÉSULTATS DE RECHERCHE"))
    print(gras("━" * 60))

    total_occurrences = 0

    for entree in tous_resultats:
        nb = len(entree["occurrences"])
        total_occurrences += nb
        print()
        print(vert(str(entree["relatif"])) + f"  [{nb} occurrence(s)]")

        if verbose:
            for occ in entree["occurrences"]:
                print(f"  - Page {cyan(str(occ['page']))}, "
                      f"ligne {cyan(str(occ['ligne']))} :")
                # Mise en évidence du terme trouvé
                extrait_mis_en_evidence = motif.sub(
                    lambda m: jaune(gras(m.group())), occ["extrait"]
                )
                print(f"    {extrait_mis_en_evidence}")

    print()
    print(gras("━" * 60))
    print(f"  Fichiers analysés      : {gras(str(nb_fichiers))}")
    print(f"  Fichiers avec résultats: {gras(str(nb_avec_resultats))}")
    print(f"  Occurrences totales    : {gras(str(total_occurrences))}")
    print(gras("━" * 60))
    print()


# ─── Export CSV optionnel ────────────────────────────────────────────────────

def exporter_csv(tous_resultats, chemin_sortie: Path):
    """Exporte les résultats dans un fichier CSV."""
    import csv
    with open(chemin_sortie, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Fichier", "Page", "Ligne", "Extrait"])
        for entree in tous_resultats:
            for occ in entree["occurrences"]:
                writer.writerow([
                    str(entree["relatif"]),
                    occ["page"],
                    occ["ligne"],
                    occ["extrait"].replace("\n", " | "),
                ])
    print(vert(f"Export CSV : {chemin_sortie}"))


# ─── Interface en ligne de commande ─────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Recherche une chaîne dans tous les PDF d'un dossier (et sous-dossiers).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python recherche_pdf.py /chemin/dossier "intelligence artificielle"
  python recherche_pdf.py . "SNT" --insensible
  python recherche_pdf.py ./cours "Pythagore" --contexte 2 --csv resultats.csv
  python recherche_pdf.py . "http[s]?://" --regex
        """
    )
    parser.add_argument("dossier",  help="Dossier racine à analyser")
    parser.add_argument("recherche", help="Texte ou expression à rechercher")
    parser.add_argument("-i", "--insensible",  action="store_true",
                        help="Recherche insensible à la casse")
    parser.add_argument("-r", "--regex",       action="store_true",
                        help="Interpréter la recherche comme une expression régulière")
    parser.add_argument("-c", "--contexte",    type=int, default=1, metavar="N",
                        help="Nombre de lignes de contexte autour du résultat (défaut : 1)")
    parser.add_argument("--csv",               metavar="FICHIER",
                        help="Exporter les résultats dans un fichier CSV")
    parser.add_argument("-q", "--silencieux",  action="store_true",
                        help="N'affiche que le résumé (pas le détail des extraits)")
    return parser.parse_args()


# ─── Point d'entrée ──────────────────────────────────────────────────────────

def main():
    args = parse_args()

    racine = Path(args.dossier).resolve()
    if not racine.exists():
        print(rouge(f"Dossier introuvable : {racine}"))
        sys.exit(1)

    # Construction du motif
    flags = re.IGNORECASE if args.insensible else 0
    chaine = args.recherche if args.regex else re.escape(args.recherche)
    try:
        motif = re.compile(chaine, flags)
    except re.error as e:
        print(rouge(f"Expression régulière invalide : {e}"))
        sys.exit(1)

    print()
    print(gras("Recherche : ") + jaune(f'"{args.recherche}"'))
    print(gras("Dossier   : ") + str(racine))
    mode = []
    if args.insensible: mode.append("insensible à la casse")
    if args.regex:      mode.append("regex")
    if mode: print(gras("Options   : ") + ", ".join(mode))
    print()

    tous_resultats, nb_fichiers, nb_avec_resultats = parcourir_dossier(
        racine, motif, args.contexte
    )

    if not tous_resultats:
        print(jaune("Aucun résultat trouvé."))
        print(f"  {nb_fichiers} fichier(s) PDF analysé(s).")
    else:
        afficher_resultats(
            tous_resultats, motif,
            nb_fichiers, nb_avec_resultats,
            verbose=not args.silencieux
        )
        if args.csv:
            exporter_csv(tous_resultats, Path(args.csv))


if __name__ == "__main__":
    main()
