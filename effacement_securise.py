#!/usr/bin/env python3
"""
effacement_securise.py
Ecrase un fichier plusieurs fois avant suppression pour le rendre irrecuperable.
Methodes : simple (1 passe), dod (3 passes), dod7 (7 passes), gutmann (35 passes).

Avertissement SSD / cle USB : le sur-ecrasement est moins efficace sur les supports flash
en raison du wear-leveling. Preferer le chiffrement integral du disque dans ce cas.

Usage :
    python effacement_securise.py fichier.txt
    python effacement_securise.py ./dossier --recursif --methode dod
    python effacement_securise.py secret.pdf --simulation
"""

import os
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

# ─── Definition des methodes ──────────────────────────────────────────────────

# Chaque passe est ("fixe", octet_bytes) ou ("aleatoire", None)
METHODES: dict[str, list[tuple[str, bytes | None]]] = {
    "simple": [
        ("aleatoire", None),
    ],
    "dod": [
        ("fixe", b"\x00"),
        ("fixe", b"\xFF"),
        ("aleatoire", None),
    ],
    "dod7": [
        ("fixe", b"\x00"), ("fixe", b"\xFF"), ("aleatoire", None),
        ("fixe", b"\x00"), ("fixe", b"\xFF"), ("aleatoire", None),
        ("aleatoire", None),
    ],
    # Gutmann simplifie : 35 passes (4 aleatoires + 27 valeurs + 4 aleatoires)
    "gutmann": (
        [("aleatoire", None)] * 4 +
        [("fixe", bytes([v])) for v in [
            0x55, 0xAA, 0x92, 0x49, 0x24, 0x49, 0x92, 0x24,
            0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
            0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF,
            0x92, 0x49, 0x24,
        ]] +
        [("aleatoire", None)] * 4
    ),
}

DESCRIPTIONS = {
    "simple":  "1 passe aleatoire (rapide)",
    "dod":     "3 passes — DoD 5220.22-M (0x00 / 0xFF / aleatoire)",
    "dod7":    "7 passes — variante DoD renforcee",
    "gutmann": "35 passes — methode Gutmann (HDD uniquement, inutile sur SSD)",
}

BLOC = 65536  # 64 Ko par ecriture

# ─── Effacement ───────────────────────────────────────────────────────────────

def ecraser_passe(f, taille: int, type_passe: str, valeur: bytes | None,
                  verbose: bool, num: int, total: int):
    f.seek(0)
    ecrit = 0
    while ecrit < taille:
        n = min(BLOC, taille - ecrit)
        if type_passe == "aleatoire":
            f.write(os.urandom(n))
        else:
            f.write((valeur * n)[:n])
        ecrit += n
    f.flush()
    try:
        os.fsync(f.fileno())
    except OSError:
        pass
    if verbose:
        label = "aleatoire" if type_passe == "aleatoire" else f"0x{valeur[0]:02X}"
        print(dim(f"    Passe {num}/{total} ({label})"))


def effacer_fichier(chemin: Path, methode: str, simulation: bool, verbose: bool) -> bool:
    passes = METHODES[methode]
    try:
        taille = chemin.stat().st_size
    except OSError as e:
        print(rouge(f"  [ERR] {chemin.name} : {e}"))
        return False

    taille_str = f"{taille:,} o"
    if simulation:
        print(f"  {cyan(chemin.name):<50} {taille_str}  {len(passes)} passe(s)")
        return True

    print(f"  {cyan(chemin.name)}", end="", flush=True)

    try:
        if taille > 0:
            with open(chemin, "r+b") as f:
                for i, (type_passe, valeur) in enumerate(passes, 1):
                    ecraser_passe(f, taille, type_passe, valeur, verbose, i, len(passes))
        chemin.unlink()
        print("  " + vert("EFFACE"))
        return True
    except PermissionError:
        print("  " + rouge("ACCES REFUSE"))
        return False
    except OSError as e:
        print("  " + rouge(f"ERREUR : {e}"))
        return False

# ─── Collecte ─────────────────────────────────────────────────────────────────

def collecter(cibles: list[str], recursif: bool) -> list[Path]:
    fichiers = []
    for c in cibles:
        p = Path(c)
        if not p.exists():
            print(rouge(f"Introuvable : {c}"))
            continue
        if p.is_file():
            fichiers.append(p)
        elif p.is_dir():
            if recursif:
                fichiers.extend(f for f in sorted(p.rglob("*")) if f.is_file())
            else:
                fichiers.extend(f for f in sorted(p.iterdir()) if f.is_file())
        else:
            print(jaune(f"Ignore (ni fichier ni dossier) : {c}"))
    return fichiers

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Efface des fichiers de facon securisee (sur-ecrasement avant suppression).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Methodes :
  simple    1 passe aleatoire (rapide)
  dod       3 passes : 0x00 / 0xFF / aleatoire — DoD 5220.22-M (defaut)
  dod7      7 passes — variante DoD renforcee
  gutmann   35 passes — methode Gutmann (HDD uniquement)

Note SSD : le wear-leveling des SSD et cles USB reduit l'efficacite du sur-ecrasement.
Pour les SSD, preferer le chiffrement integral du disque (VeraCrypt, BitLocker).

Exemples :
  python effacement_securise.py fichier.txt
  python effacement_securise.py secret.pdf --methode dod7 --verbose
  python effacement_securise.py ./dossier --recursif --simulation
  python effacement_securise.py a.pdf b.pdf c.pdf --methode simple
        """
    )
    parser.add_argument("cibles", nargs="+", help="Fichier(s) ou dossier(s) a effacer")
    parser.add_argument("-m", "--methode", choices=list(METHODES), default="dod",
                        help="Methode d'effacement (defaut : dod)")
    parser.add_argument("-r", "--recursif", action="store_true",
                        help="Effacer tous les fichiers dans un dossier recursivement")
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Lister ce qui serait efface sans effacer")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Afficher chaque passe d'ecrasement")
    return parser.parse_args()


def main():
    args = parse_args()
    methode = args.methode
    passes  = METHODES[methode]

    fichiers = collecter(args.cibles, args.recursif)
    if not fichiers:
        print(jaune("Aucun fichier a effacer."))
        sys.exit(0)

    print(f"\n{gras('=== Effacement securise ===')}")
    print(f"Methode  : {gras(methode)}  —  {DESCRIPTIONS[methode]}")
    print(f"Fichiers : {len(fichiers)}\n")

    if args.simulation:
        print(jaune("(simulation : aucun fichier ne sera efface)\n"))
        ok = ko = 0
        for f in fichiers:
            if effacer_fichier(f, methode, True, args.verbose):
                ok += 1
            else:
                ko += 1
    else:
        print(rouge("ATTENTION : cette operation est IRREVERSIBLE."))
        print(f"Tapez 'oui' pour confirmer l'effacement de {len(fichiers)} fichier(s) : ", end="")
        confirmation = input().strip().lower()
        if confirmation != "oui":
            print(jaune("Annule."))
            sys.exit(0)
        print()
        ok = ko = 0
        for f in fichiers:
            if effacer_fichier(f, methode, False, args.verbose):
                ok += 1
            else:
                ko += 1

    print(f"\n{gras('---')}")
    if args.simulation:
        print(f"  {ok} fichier(s) auraient ete effaces")
    else:
        print(f"  {vert(str(ok))} efface(s)  /  {(rouge(str(ko)) if ko else str(ko))} echec(s)")


if __name__ == "__main__":
    main()
