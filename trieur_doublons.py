#!/usr/bin/env python3
"""
trieur_doublons.py
Détecte les fichiers en double (contenu strictement identique) dans toute une
arborescence, tous types confondus. Pré-filtre par taille puis compare par
hash SHA-256 — fiable et rapide même sur un disque entier.

Par défaut : rapport seul (rien n'est supprimé). Pour agir :
    --supprimer         supprime les doublons (garde 1 exemplaire par groupe)
    --deplacer DOSSIER  déplace les doublons vers DOSSIER

L'exemplaire conservé est le plus ancien (date de modification), à égalité le
chemin le plus court — les autres copies sont considérées comme les doublons.

Usage :
    python trieur_doublons.py <dossier> [options]

Exemples :
    python trieur_doublons.py "D:\\Rassemblement"
    python trieur_doublons.py "D:\\Rassemblement" --min-taille 1M
    python trieur_doublons.py "D:\\Rassemblement" --deplacer "D:\\_doublons"
    python trieur_doublons.py "D:\\Rassemblement" --supprimer
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict


def _init_terminal():
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


# ═══════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════

def formater_taille(octets: float) -> str:
    o = float(octets)
    for unite in ["o", "Ko", "Mo", "Go", "To"]:
        if o < 1024:
            return f"{o:.1f} {unite}"
        o /= 1024
    return f"{o:.1f} Po"


def parser_taille(valeur: str) -> int:
    """Convertit '1M', '500K', '2G', '1024' en octets."""
    if not valeur:
        return 0
    v = valeur.strip().upper()
    facteurs = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    if v[-1] in facteurs:
        try:
            return int(float(v[:-1]) * facteurs[v[-1]])
        except ValueError:
            return 0
    try:
        return int(v)
    except ValueError:
        return 0


def hash_fichier(chemin: Path, bloc: int = 1 << 20, limite: int | None = None) -> str | None:
    """
    SHA-256 d'un fichier (par blocs de 1 Mo). None si illisible.
    Si `limite` est fournie, ne lit que les premiers `limite` octets
    (hash partiel — sert au pré-filtrage rapide des gros fichiers).
    """
    sha = hashlib.sha256()
    lu = 0
    try:
        with open(chemin, "rb") as f:
            while True:
                if limite is not None:
                    reste = limite - lu
                    if reste <= 0:
                        break
                    data = f.read(min(bloc, reste))
                else:
                    data = f.read(bloc)
                if not data:
                    break
                sha.update(data)
                lu += len(data)
    except OSError:
        return None
    return sha.hexdigest()


def barre(actuel: int, total: int, largeur: int = 30) -> str:
    pct = actuel / total if total else 1.0
    rempli = int(largeur * pct)
    return "[" + "=" * rempli + ">" + " " * (largeur - rempli) + f"] {actuel}/{total}"


# ═══════════════════════════════════════════════════════════════════════════
# DÉTECTION DES DOUBLONS
# ═══════════════════════════════════════════════════════════════════════════

def collecter(racine: Path, min_taille: int, inclure_vides: bool) -> dict:
    """Retourne {taille: [chemins]} pour tous les fichiers retenus."""
    par_taille: dict = defaultdict(list)
    for f in racine.rglob("*"):
        if not f.is_file() or f.is_symlink():
            continue
        try:
            taille = f.stat().st_size
        except OSError:
            continue
        if taille == 0 and not inclure_vides:
            continue
        if taille < min_taille:
            continue
        par_taille[taille].append(f)
    return par_taille


PARTIEL = 1 << 16   # 64 Ko lus pour le pré-filtre


def trouver_doublons(par_taille: dict) -> list:
    """
    Compare par hash les fichiers de même taille, en DEUX passes :
      1. hash PARTIEL (64 Ko de tête) — élimine vite les fichiers différents ;
      2. hash COMPLET seulement pour ceux dont le début coïncide déjà.
    Bien plus rapide sur les gros fichiers (vidéos) sans perte de fiabilité.

    Retourne une liste de groupes ; chaque groupe = liste de chemins identiques
    (≥ 2), triée : original d'abord (plus ancien, puis chemin le plus court).
    """
    # Seuls les groupes de taille avec >1 fichier valent la peine d'être hashés.
    a_hasher = [(t, chemins) for t, chemins in par_taille.items() if len(chemins) > 1]

    # ── Passe 1 : hash partiel, clé = (taille, hash des 64 premiers Ko) ──
    total1 = sum(len(c) for _, c in a_hasher)
    par_partiel: dict = defaultdict(list)
    fait = 0
    for taille, chemins in a_hasher:
        for chemin in chemins:
            fait += 1
            if total1:
                print("\r  Pré-filtre   " + barre(fait, total1), end="", flush=True)
            h = hash_fichier(chemin, limite=PARTIEL)
            if h is not None:
                par_partiel[(taille, h)].append(chemin)
    if total1:
        print("\r" + " " * 60 + "\r", end="")

    # ── Passe 2 : hash complet uniquement sur les groupes encore ambigus ──
    confirmes = []          # petits fichiers (≤ 64 Ko) : le partiel = le complet
    a_confirmer = []        # gros fichiers de même début : à confirmer en entier
    for (taille, _h), chemins in par_partiel.items():
        if len(chemins) < 2:
            continue
        (confirmes if taille <= PARTIEL else a_confirmer).append(chemins)

    total2 = sum(len(c) for c in a_confirmer)
    par_hash: dict = defaultdict(list)
    fait = 0
    for chemins in a_confirmer:
        for chemin in chemins:
            fait += 1
            if total2:
                print("\r  Comparaison  " + barre(fait, total2), end="", flush=True)
            h = hash_fichier(chemin)
            if h is not None:
                par_hash[h].append(chemin)
    if total2:
        print("\r" + " " * 60 + "\r", end="")

    groupes = [c for c in par_hash.values() if len(c) > 1] + confirmes
    for g in groupes:
        g.sort(key=lambda p: (_mtime(p), len(str(p)), str(p)))
    # Groupes les plus « coûteux » d'abord (taille × nb de doublons)
    groupes.sort(key=lambda g: g[0].stat().st_size * (len(g) - 1), reverse=True)
    return groupes


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return float("inf")


# ═══════════════════════════════════════════════════════════════════════════
# RAPPORT & ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

def afficher_rapport(groupes: list, racine: Path):
    nb_redondants = sum(len(g) - 1 for g in groupes)
    gaspille = sum(g[0].stat().st_size * (len(g) - 1) for g in groupes)

    if not groupes:
        print(vert("\n  ✅ Aucun doublon trouvé.\n"))
        return 0, 0

    print(f"\n  {gras(str(len(groupes)))} groupe(s) de doublons  —  "
          f"{gras(str(nb_redondants))} fichier(s) redondant(s)  —  "
          f"{gras(formater_taille(gaspille))} récupérable(s)\n")

    for i, g in enumerate(groupes, 1):
        taille = g[0].stat().st_size
        print(f"  {cyan(f'#{i}')}  {formater_taille(taille)} × {len(g)}")
        print(f"      {vert('gardé   ')} {_rel(g[0], racine)}")
        for doublon in g[1:]:
            print(f"      {jaune('doublon ')} {_rel(doublon, racine)}")
        print()
    return nb_redondants, gaspille


def _rel(p: Path, racine: Path) -> str:
    try:
        return str(p.relative_to(racine))
    except ValueError:
        return str(p)


def agir(groupes: list, supprimer: bool, deplacer: Path | None, racine: Path):
    """Supprime ou déplace les doublons (tout sauf le 1er de chaque groupe)."""
    redondants = [d for g in groupes for d in g[1:]]
    if not redondants:
        return

    action = "supprimer" if supprimer else f"déplacer vers {deplacer}"
    try:
        rep = input(f"  {jaune('⚠')}  {action} {len(redondants)} fichier(s) ? [o/N] : ").strip().lower()
    except EOFError:
        rep = ""
    if rep not in ("o", "oui", "y", "yes"):
        print("  ⛔ Annulé.\n")
        return

    faits = erreurs = 0
    for doublon in redondants:
        try:
            if supprimer:
                doublon.unlink()
            else:
                cible = deplacer / doublon.name
                c = cible
                n = 2
                while c.exists():
                    c = deplacer / f"{cible.stem}_{n}{cible.suffix}"
                    n += 1
                deplacer.mkdir(parents=True, exist_ok=True)
                shutil.move(str(doublon), str(c))
            faits += 1
        except OSError as e:
            print(rouge(f"    ✗ {doublon.name} : {e}"))
            erreurs += 1

    verbe = "supprimé(s)" if supprimer else "déplacé(s)"
    print(f"\n  {vert('✓')} {faits} doublon(s) {verbe}"
          + (f"  |  {rouge(str(erreurs) + ' erreur(s)')}" if erreurs else "") + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="🔁 Détecte (et supprime/déplace) les fichiers en double dans une arborescence.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python trieur_doublons.py "D:\\Rassemblement"
  python trieur_doublons.py "D:\\Rassemblement" --min-taille 1M
  python trieur_doublons.py "D:\\Rassemblement" --deplacer "D:\\_doublons"
  python trieur_doublons.py "D:\\Rassemblement" --supprimer --json rapport.json
""",
    )
    p.add_argument("dossier", help="Dossier à analyser (récursif)")
    p.add_argument("--min-taille", default="0", metavar="TAILLE",
                   help="Ignorer les fichiers plus petits (ex: 1M, 500K) — accélère")
    p.add_argument("--inclure-vides", action="store_true",
                   help="Inclure les fichiers de 0 octet (ignorés par défaut)")
    p.add_argument("--supprimer", action="store_true",
                   help="Supprimer les doublons (garde 1 exemplaire par groupe)")
    p.add_argument("--deplacer", metavar="DOSSIER",
                   help="Déplacer les doublons vers ce dossier au lieu de supprimer")
    p.add_argument("--json", metavar="FICHIER",
                   help="Exporter le rapport des groupes en JSON")
    return p.parse_args()


def main():
    args = parse_args()
    racine = Path(args.dossier).resolve()
    if not racine.is_dir():
        print(rouge(f"❌ Dossier introuvable : {racine}"))
        sys.exit(1)

    if args.supprimer and args.deplacer:
        print(rouge("❌ Choisissez --supprimer OU --deplacer, pas les deux."))
        sys.exit(1)

    print(f"\n{gras('🔁 trieur_doublons.py')}")
    print(f"  Dossier : {racine}")
    min_taille = parser_taille(args.min_taille)
    if min_taille:
        print(f"  Filtre  : ≥ {formater_taille(min_taille)}")

    print(gras("\n  Analyse des tailles..."))
    par_taille = collecter(racine, min_taille, args.inclure_vides)
    nb_fichiers = sum(len(v) for v in par_taille.values())
    candidats = sum(len(v) for v in par_taille.values() if len(v) > 1)
    print(f"  {nb_fichiers} fichier(s) — {candidats} candidat(s) de même taille à comparer")

    groupes = trouver_doublons(par_taille)
    nb_redondants, gaspille = afficher_rapport(groupes, racine)

    if args.json:
        donnees = [
            {"taille": g[0].stat().st_size,
             "garde": str(g[0]),
             "doublons": [str(d) for d in g[1:]]}
            for g in groupes
        ]
        Path(args.json).write_text(
            json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        print(vert(f"  💾 Rapport JSON : {args.json}\n"))

    if groupes and (args.supprimer or args.deplacer):
        deplacer = Path(args.deplacer).resolve() if args.deplacer else None
        agir(groupes, args.supprimer, deplacer, racine)
    elif groupes:
        print(dim("  (rapport seul — ajoutez --supprimer ou --deplacer pour agir)\n"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(jaune("\nInterrompu."))
        sys.exit(130)
