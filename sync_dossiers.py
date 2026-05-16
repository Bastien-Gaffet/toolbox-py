#!/usr/bin/env python3
"""
sync_dossiers.py
Synchronisation unidirectionnelle source -> destination.
Detecte et copie les fichiers nouveaux et modifies.
Peut supprimer les fichiers absents de la source avec --supprimer.

Usage :
    python sync_dossiers.py ./source ./destination
    python sync_dossiers.py ./source ./backup --supprimer --simulation
    python sync_dossiers.py ./source ./dest --hash --exclure "*.tmp" "*.log"
"""

import os
import sys
import csv
import shutil
import hashlib
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

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} To"


def sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return h.hexdigest()


def empreinte(chemin: Path, mode_hash: bool) -> str:
    if mode_hash:
        return sha256(chemin)
    stat = chemin.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def est_exclu(chemin_relatif: Path, motifs: list[str]) -> bool:
    nom = chemin_relatif.name
    chemin_str = str(chemin_relatif)
    return any(fnmatch.fnmatch(nom, m) or fnmatch.fnmatch(chemin_str, m)
               for m in motifs)

# ─── Indexation ───────────────────────────────────────────────────────────────

def indexer(dossier: Path, motifs_exclusion: list[str],
            mode_hash: bool) -> dict[str, dict]:
    """Retourne {chemin_relatif_str: {empreinte, taille, chemin}}."""
    index = {}
    for chemin in dossier.rglob("*"):
        if not chemin.is_file():
            continue
        relatif = chemin.relative_to(dossier)
        if est_exclu(relatif, motifs_exclusion):
            continue
        try:
            index[str(relatif)] = {
                "empreinte": empreinte(chemin, mode_hash),
                "taille":    chemin.stat().st_size,
                "chemin":    chemin,
            }
        except OSError:
            pass
    return index

# ─── Comparaison ──────────────────────────────────────────────────────────────

def comparer(idx_src: dict, idx_dst: dict) -> dict:
    """Retourne les listes nouveaux, modifies, supprimes."""
    nouveaux   = []
    modifies   = []
    supprimes  = []

    for relatif, info in idx_src.items():
        if relatif not in idx_dst:
            nouveaux.append((relatif, info))
        elif info["empreinte"] != idx_dst[relatif]["empreinte"]:
            modifies.append((relatif, info, idx_dst[relatif]))

    for relatif, info in idx_dst.items():
        if relatif not in idx_src:
            supprimes.append((relatif, info))

    return {"nouveaux": nouveaux, "modifies": modifies, "supprimes": supprimes}

# ─── Rapport ──────────────────────────────────────────────────────────────────

def afficher_rapport(diff: dict, avec_suppr: bool):
    nouveaux  = diff["nouveaux"]
    modifies  = diff["modifies"]
    supprimes = diff["supprimes"]

    if nouveaux:
        print(f"\n  {vert('Nouveaux')} ({len(nouveaux)}) :")
        for rel, info in nouveaux[:20]:
            print(f"    + {rel}  ({taille_lisible(info['taille'])})")
        if len(nouveaux) > 20:
            print(dim(f"    ... et {len(nouveaux) - 20} autres"))

    if modifies:
        print(f"\n  {jaune('Modifies')} ({len(modifies)}) :")
        for rel, src_info, _ in modifies[:20]:
            print(f"    ~ {rel}  ({taille_lisible(src_info['taille'])})")
        if len(modifies) > 20:
            print(dim(f"    ... et {len(modifies) - 20} autres"))

    if supprimes and avec_suppr:
        print(f"\n  {rouge('A supprimer')} ({len(supprimes)}) :")
        for rel, info in supprimes[:20]:
            print(f"    - {rel}  ({taille_lisible(info['taille'])})")
        if len(supprimes) > 20:
            print(dim(f"    ... et {len(supprimes) - 20} autres"))
    elif supprimes and not avec_suppr:
        print(f"\n  {dim('Absents de la source')} ({len(supprimes)}) :")
        print(dim("  (non supprimes — utiliser --supprimer pour les retirer)"))

# ─── Synchronisation ──────────────────────────────────────────────────────────

def synchroniser(diff: dict, source: Path, destination: Path,
                 avec_suppr: bool, simulation: bool) -> tuple[int, int, int, int]:
    ok_copie = ok_suppr = err_copie = err_suppr = 0

    for rel, info in diff["nouveaux"] + [(r, s) for r, s, _ in diff["modifies"]]:
        src_p = source / rel
        dst_p = destination / rel
        if simulation:
            ok_copie += 1
            continue
        try:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_p, dst_p)
            ok_copie += 1
        except OSError as e:
            print(rouge(f"  ERR copie {rel} : {e}"))
            err_copie += 1

    if avec_suppr:
        for rel, info in diff["supprimes"]:
            dst_p = destination / rel
            if simulation:
                ok_suppr += 1
                continue
            try:
                dst_p.unlink()
                ok_suppr += 1
                # Supprimer les dossiers parents vides
                parent = dst_p.parent
                while parent != destination:
                    try:
                        parent.rmdir()
                        parent = parent.parent
                    except OSError:
                        break
            except OSError as e:
                print(rouge(f"  ERR suppr {rel} : {e}"))
                err_suppr += 1

    return ok_copie, ok_suppr, err_copie, err_suppr

# ─── Export CSV ───────────────────────────────────────────────────────────────

def exporter_csv(diff: dict, chemin: str):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Statut", "Chemin", "Taille"])
        for rel, info in diff["nouveaux"]:
            w.writerow(["NOUVEAU", rel, info["taille"]])
        for rel, info, _ in diff["modifies"]:
            w.writerow(["MODIFIE", rel, info["taille"]])
        for rel, info in diff["supprimes"]:
            w.writerow(["SUPPRIME", rel, info["taille"]])
    print(vert(f"Rapport CSV : {chemin}"))

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Synchronisation unidirectionnelle source -> destination.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python sync_dossiers.py ./source ./backup
  python sync_dossiers.py ./source ./backup --supprimer --simulation
  python sync_dossiers.py ./docs ./nas --hash --exclure "*.tmp" ".git"
  python sync_dossiers.py ./source ./dest --csv rapport.csv
        """
    )
    parser.add_argument("source",      help="Dossier source (reference)")
    parser.add_argument("destination", help="Dossier destination (cible a mettre a jour)")
    parser.add_argument("--supprimer", action="store_true",
                        help="Supprimer dans la destination les fichiers absents de la source")
    parser.add_argument("--hash", action="store_true",
                        help="Comparaison precise par SHA-256 (plus lent mais fiable)")
    parser.add_argument("-e", "--exclure", nargs="+", metavar="MOTIF", default=[],
                        help="Motifs glob a exclure (ex: '*.tmp' '.git')")
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Afficher les differences sans modifier la destination")
    parser.add_argument("--csv", metavar="FICHIER",
                        help="Exporter le rapport de differences en CSV")
    return parser.parse_args()


def main():
    args = parse_args()
    source      = Path(args.source)
    destination = Path(args.destination)

    for p, label in [(source, "source"), (destination, "destination")]:
        if not p.exists():
            if label == "source":
                print(rouge(f"Source introuvable : {p}"))
                sys.exit(1)
            # La destination peut ne pas encore exister
            destination.mkdir(parents=True, exist_ok=True)

    mode_cmp = "SHA-256" if args.hash else "taille+date"
    print(f"\n{gras('=== Synchronisation dossiers ===')}")
    print(f"  Source      : {source}")
    print(f"  Destination : {destination}")
    print(f"  Comparaison : {mode_cmp}")
    if args.exclure:
        print(f"  Exclusions  : {', '.join(args.exclure)}")

    print("\n  Analyse de la source...")
    idx_src = indexer(source, args.exclure, args.hash)
    print(f"  {len(idx_src)} fichier(s) dans la source")

    print("  Analyse de la destination...")
    idx_dst = indexer(destination, args.exclure, args.hash)
    print(f"  {len(idx_dst)} fichier(s) dans la destination")

    diff = comparer(idx_src, idx_dst)

    nb_total = (len(diff["nouveaux"]) + len(diff["modifies"]) +
                (len(diff["supprimes"]) if args.supprimer else 0))

    if nb_total == 0 and not diff["supprimes"]:
        print(vert("\n  Destination a jour. Aucune action necessaire."))
        if args.csv:
            exporter_csv(diff, args.csv)
        return

    afficher_rapport(diff, args.supprimer)

    if args.csv:
        exporter_csv(diff, args.csv)

    if args.simulation:
        print(jaune("\n(simulation : aucun fichier ne sera modifie)"))
        n = len(diff["nouveaux"]) + len(diff["modifies"])
        s = len(diff["supprimes"]) if args.supprimer else 0
        print(f"  {n} copie(s) prevue(s) / {s} suppression(s) prevue(s)")
        return

    if nb_total > 0:
        print(f"\nSynchroniser {nb_total} operation(s) ? [o/N] : ", end="")
        if input().strip().lower() != "o":
            print(jaune("Annule."))
            sys.exit(0)

    ok_c, ok_s, err_c, err_s = synchroniser(
        diff, source, destination, args.supprimer, simulation=False
    )

    print(f"\n{gras('---')}")
    print(f"  {vert(str(ok_c))} fichier(s) copie(s)  /  {(rouge(str(err_c)) if err_c else str(err_c))} erreur(s)")
    if args.supprimer:
        print(f"  {str(ok_s)} fichier(s) supprime(s)  /  {(rouge(str(err_s)) if err_s else str(err_s))} erreur(s)")
    print(f"  Synchro terminee le {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
