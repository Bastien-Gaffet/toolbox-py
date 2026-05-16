#!/usr/bin/env python3
"""
analyse_espace.py
Analyse l'utilisation de l'espace disque d'un dossier.
Affiche les sous-dossiers par ordre de taille décroissante
avec barres de progression ASCII. Style ncdu en terminal Python.

Usage :
    python analyse_espace.py [dossier] [options]
"""

import sys
import shutil
import argparse
from pathlib import Path

# ─── Couleurs terminal ────────────────────────────────────────────────────────

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    def rouge(t):  return Fore.RED     + t + Style.RESET_ALL
    def vert(t):   return Fore.GREEN   + t + Style.RESET_ALL
    def jaune(t):  return Fore.YELLOW  + t + Style.RESET_ALL
    def cyan(t):   return Fore.CYAN    + t + Style.RESET_ALL
    def bleu(t):   return Fore.BLUE    + t + Style.RESET_ALL
    def gras(t):   return Style.BRIGHT + t + Style.RESET_ALL
    def dim(t):    return Style.DIM    + t + Style.RESET_ALL
except ImportError:
    def rouge(t):  return t
    def vert(t):   return t
    def jaune(t):  return t
    def cyan(t):   return t
    def bleu(t):   return t
    def gras(t):   return t
    def dim(t):    return t

# ─── Formatage ────────────────────────────────────────────────────────────────

def fmt_taille(octets: int) -> str:
    """Retourne la taille formatée, alignée sur 9 caractères."""
    for unite in [" o  ", " Ko ", " Mo ", " Go ", " To "]:
        if octets < 1024:
            return f"{octets:6.1f}{unite}"
        octets /= 1024
    return f"{octets:6.1f} Po "

# ─── Scan récursif ────────────────────────────────────────────────────────────

def calculer_tailles(racine: Path, profondeur_max: int) -> tuple[dict, list]:
    """
    Parcourt récursivement le dossier et calcule :
      - tailles_dossiers : {chemin: {"taille": int, "fichiers": int, "niveau": int}}
      - top_fichiers     : liste de {"chemin": Path, "taille": int} pour les fichiers directs
    """
    tailles_dossiers = {}
    tous_fichiers    = []
    compteur         = [0]

    def _scan(chemin: Path, niveau: int) -> tuple[int, int]:
        taille_locale   = 0
        fichiers_locaux = 0

        try:
            for entree in chemin.iterdir():
                if entree.is_symlink():
                    continue
                if entree.is_file():
                    try:
                        t = entree.stat().st_size
                        taille_locale   += t
                        fichiers_locaux += 1
                        tous_fichiers.append({"chemin": entree, "taille": t, "niveau": niveau})
                        compteur[0] += 1
                        if compteur[0] % 500 == 0:
                            print(f"   {compteur[0]} entrées scannées...", end="\r")
                    except OSError:
                        pass
                elif entree.is_dir():
                    sous_taille, sous_fichiers = _scan(entree, niveau + 1)
                    taille_locale   += sous_taille
                    fichiers_locaux += sous_fichiers

                    if niveau <= profondeur_max:
                        tailles_dossiers[entree] = {
                            "taille":   sous_taille,
                            "fichiers": sous_fichiers,
                            "niveau":   niveau,
                        }
        except PermissionError:
            pass

        return taille_locale, fichiers_locaux

    total_taille, total_fichiers = _scan(racine, 1)
    tailles_dossiers[racine] = {
        "taille":   total_taille,
        "fichiers": total_fichiers,
        "niveau":   0,
    }

    return tailles_dossiers, tous_fichiers

# ─── Affichage ────────────────────────────────────────────────────────────────

def couleur_taille(taille: int, total: int):
    """Couleur selon la proportion de la taille totale."""
    if total == 0:
        return dim
    pct = taille / total * 100
    if pct >= 30:
        return rouge
    elif pct >= 10:
        return jaune
    elif pct >= 1:
        return vert
    else:
        return dim

def barre_ascii(taille: int, total: int, largeur: int) -> str:
    if total == 0 or largeur <= 0:
        return "[" + "." * largeur + "]"
    plein = max(0, min(largeur, int(taille / total * largeur)))
    return "[" + "#" * plein + "." * (largeur - plein) + "]"

def afficher(racine: Path, tailles_dossiers: dict, tous_fichiers: list,
             top: int, largeur_barre: int, avec_fichiers: bool, profondeur_max: int):

    info_racine  = tailles_dossiers[racine]
    total_taille = info_racine["taille"]
    total_fich   = info_racine["fichiers"]

    terme_w = shutil.get_terminal_size((100, 40)).columns

    print()
    print(gras("=" * min(terme_w - 1, 75)))
    print(gras(f"  ANALYSE ESPACE : {racine.name}"))
    print(gras("=" * min(terme_w - 1, 75)))
    print(f"  Chemin   : {racine}")
    print(f"  Total    : {gras(fmt_taille(total_taille).strip())}  ({total_fich} fichier(s))")
    print(f"  Barre    : 100% = {fmt_taille(total_taille).strip()}")
    print()

    # Construire le classement des dossiers (sans la racine)
    entrees_dossiers = [
        {"chemin": ch, **data, "est_fichier": False}
        for ch, data in tailles_dossiers.items()
        if ch != racine
    ]

    if avec_fichiers:
        # Ajouter les gros fichiers individuels au classement
        for fic in tous_fichiers:
            entrees_dossiers.append({
                "chemin":    fic["chemin"],
                "taille":    fic["taille"],
                "fichiers":  1,
                "niveau":    fic["niveau"],
                "est_fichier": True,
            })

    classement = sorted(entrees_dossiers, key=lambda x: x["taille"], reverse=True)[:top]

    # En-tête du tableau
    col_taille = 10
    col_pct    = 6
    col_nb     = 8
    col_barre  = largeur_barre + 2
    print(f"  {'Taille':>{col_taille}}  {'Part':>{col_pct}}  {'Fichiers':>{col_nb}}  "
          f"{'Proportion':<{col_barre}}  Chemin")
    print(f"  {'─'*col_taille}  {'─'*col_pct}  {'─'*col_nb}  {'─'*col_barre}  {'─'*30}")

    for entree in classement:
        taille   = entree["taille"]
        fichiers = entree["fichiers"]
        niveau   = entree.get("niveau", 1)
        est_fich = entree.get("est_fichier", False)
        chemin   = entree["chemin"]

        pct   = taille / total_taille * 100 if total_taille else 0
        barre = barre_ascii(taille, total_taille, largeur_barre)

        try:
            nom = str(chemin.relative_to(racine))
        except ValueError:
            nom = str(chemin)

        # Indentation selon le niveau
        indent = "  " * max(0, niveau - 1)
        type_label = "F  " if est_fich else "D  "

        col = couleur_taille(taille, total_taille)

        taille_str  = fmt_taille(taille).rstrip()
        fichiers_str = str(fichiers) if not est_fich else ""

        print(f"  {col(f'{taille_str:>{col_taille}}')}  "
              f"{pct:>{col_pct-1}.1f}%  "
              f"{fichiers_str:>{col_nb}}  "
              f"{barre:<{col_barre}}  "
              f"{indent}{type_label}{nom}")

    nb_total_dossiers = len([k for k in tailles_dossiers if k != racine])
    nb_affiche = min(top, len(classement))

    print()
    if nb_total_dossiers > nb_affiche:
        print(dim(f"  ... {nb_total_dossiers - nb_affiche} dossier(s) supplémentaire(s) non affiché(s)"
                  f" (utilisez -n pour en voir plus)"))
        print()

    # Résumé des gros contributeurs
    if len(classement) > 0:
        top3 = classement[:3]
        cumulatif = sum(e["taille"] for e in top3)
        pct_top3  = cumulatif / total_taille * 100 if total_taille else 0
        print(dim(f"  Les {min(3, len(top3))} plus gros éléments représentent "
                  f"{fmt_taille(cumulatif).strip()} ({pct_top3:.1f}% du total)"))
        print()

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyse l'espace disque d'un dossier, style ncdu.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python analyse_espace.py
  python analyse_espace.py ~/Documents -n 30
  python analyse_espace.py ~/Documents -p 3
  python analyse_espace.py . -n 50 --fichiers
  python analyse_espace.py C:/Users -p 1 -n 20
        """
    )
    parser.add_argument("dossier", nargs="?", default=".",
                        help="Dossier à analyser (défaut : dossier courant)")
    parser.add_argument("-n", "--top", type=int, default=20, metavar="N",
                        help="Nombre d'entrées à afficher (défaut : 20)")
    parser.add_argument("-p", "--profondeur", type=int, default=2, metavar="N",
                        help="Profondeur maximale d'analyse (défaut : 2)")
    parser.add_argument("-f", "--fichiers", action="store_true",
                        help="Inclure les fichiers individuels dans le classement")
    parser.add_argument("-w", "--largeur", type=int, default=30, metavar="N",
                        help="Largeur de la barre de progression en caractères (défaut : 30)")
    return parser.parse_args()


def main():
    args = parse_args()

    racine = Path(args.dossier).resolve()
    if not racine.exists() or not racine.is_dir():
        print(rouge(f"Dossier introuvable : {racine}"))
        sys.exit(1)

    print(f"\nScan de : {racine}  (profondeur {args.profondeur})")
    tailles_dossiers, tous_fichiers = calculer_tailles(racine, args.profondeur)
    print(f"   {tailles_dossiers[racine]['fichiers']} fichier(s) trouvé(s)          ")

    afficher(
        racine        = racine,
        tailles_dossiers = tailles_dossiers,
        tous_fichiers = tous_fichiers,
        top           = args.top,
        largeur_barre = args.largeur,
        avec_fichiers = args.fichiers,
        profondeur_max = args.profondeur,
    )


if __name__ == "__main__":
    main()
