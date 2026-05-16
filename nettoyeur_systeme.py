#!/usr/bin/env python3
"""
nettoyeur_systeme.py
Vide les caches navigateurs, dossiers temporaires, vieux logs et fichiers de crash.
Affiche l'espace recuperable avant d'agir.

Usage :
    python nettoyeur_systeme.py                  # simulation
    python nettoyeur_systeme.py --forcer         # nettoyage reel
    python nettoyeur_systeme.py --forcer --logs  # inclure les logs
"""

import os
import sys
import re
import time
import shutil
import platform
import argparse
from pathlib import Path
from datetime import datetime, timedelta

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


def taille_dossier(chemin: Path) -> int:
    """Calcule la taille totale d'un dossier recursivement."""
    total = 0
    try:
        for f in chemin.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def nb_fichiers(chemin: Path) -> int:
    try:
        return sum(1 for f in chemin.rglob("*") if f.is_file())
    except OSError:
        return 0


def trouver_fichiers_par_pattern(dossier: Path, motifs: list[str],
                                  age_min_jours: int = 0) -> list[Path]:
    """Retourne les fichiers correspondant aux motifs (glob), optionnellement filtre par age."""
    resultat = []
    seuil = datetime.now() - timedelta(days=age_min_jours) if age_min_jours else None
    for motif in motifs:
        try:
            for f in dossier.glob(motif):
                if not f.is_file():
                    continue
                if seuil:
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime > seuil:
                            continue
                    except OSError:
                        continue
                resultat.append(f)
        except OSError:
            pass
    return resultat

# ─── Definition des cibles ────────────────────────────────────────────────────

def construire_cibles(args) -> list[dict]:
    """Retourne la liste des cibles a nettoyer selon l'OS et les options."""
    systeme = platform.system().lower()
    cibles = []

    if systeme == "windows":
        local  = Path(os.environ.get("LOCALAPPDATA", ""))
        temp   = Path(os.environ.get("TEMP", ""))
        appdata = Path(os.environ.get("APPDATA", ""))

        # Dossiers temporaires
        cibles.append({
            "label": "Dossier TEMP utilisateur",
            "type":  "dossier",
            "chemin": temp,
        })

        # Cache Windows (miniatures)
        thumb_dir = local / "Microsoft" / "Windows" / "Explorer"
        if thumb_dir.exists():
            cibles.append({
                "label": "Cache miniatures Windows",
                "type":  "fichiers",
                "dossier": thumb_dir,
                "motifs":  ["thumbcache_*.db", "iconcache_*.db"],
            })

        # Cache internet Windows
        inet_cache = local / "Microsoft" / "Windows" / "INetCache"
        if inet_cache.exists():
            cibles.append({
                "label": "Cache Internet Explorer / Windows",
                "type":  "dossier",
                "chemin": inet_cache,
            })

        # Crash dumps
        crash = local / "CrashDumps"
        if crash.exists():
            cibles.append({
                "label": "Rapports de crash",
                "type":  "dossier",
                "chemin": crash,
            })

        # Chrome cache
        chrome_cache = local / "Google" / "Chrome" / "User Data" / "Default" / "Cache" / "Cache_Data"
        if chrome_cache.exists():
            cibles.append({
                "label": "Cache Google Chrome",
                "type":  "dossier",
                "chemin": chrome_cache,
            })

        # Edge cache
        edge_cache = local / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache" / "Cache_Data"
        if edge_cache.exists():
            cibles.append({
                "label": "Cache Microsoft Edge",
                "type":  "dossier",
                "chemin": edge_cache,
            })

        # Firefox cache (parcourir les profils)
        ff_profiles = appdata / "Mozilla" / "Firefox" / "Profiles"
        if ff_profiles.exists():
            for profil in ff_profiles.iterdir():
                if profil.is_dir():
                    ff_cache = profil / "cache2"
                    if ff_cache.exists():
                        cibles.append({
                            "label": f"Cache Firefox ({profil.name[:30]})",
                            "type":  "dossier",
                            "chemin": ff_cache,
                        })

        # Logs anciens (optionnel)
        if args.logs:
            logs_dossiers = [
                local / "Temp",
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Logs",
            ]
            for d in logs_dossiers:
                if d.exists():
                    cibles.append({
                        "label": f"Logs anciens ({d})",
                        "type":  "fichiers",
                        "dossier": d,
                        "motifs":  ["*.log", "*.dmp"],
                        "age_jours": args.age_logs,
                    })

    elif systeme in ("linux", "darwin"):
        temp = Path("/tmp")
        cibles.append({
            "label": "Dossier /tmp",
            "type":  "dossier",
            "chemin": temp,
        })

        home = Path.home()
        cache = home / ".cache"
        if cache.exists():
            for navigateur in ("google-chrome", "chromium", "mozilla", "BraveSoftware"):
                nav_cache = cache / navigateur
                if nav_cache.exists():
                    cibles.append({
                        "label": f"Cache {navigateur}",
                        "type":  "dossier",
                        "chemin": nav_cache,
                    })

        if args.logs:
            cibles.append({
                "label": "Logs anciens (/var/log)",
                "type":  "fichiers",
                "dossier": Path("/var/log"),
                "motifs":  ["*.gz", "*.1", "*.old"],
                "age_jours": args.age_logs,
            })

    return [c for c in cibles if _cible_accessible(c)]


def _cible_accessible(c: dict) -> bool:
    if c["type"] == "dossier":
        return c["chemin"].exists()
    if c["type"] == "fichiers":
        return c.get("dossier", Path(".")).exists()
    return False

# ─── Analyse ──────────────────────────────────────────────────────────────────

def analyser_cible(c: dict) -> dict:
    """Retourne {taille, nb} pour une cible."""
    if c["type"] == "dossier":
        chemin = c["chemin"]
        return {
            "taille": taille_dossier(chemin),
            "nb":     nb_fichiers(chemin),
        }
    if c["type"] == "fichiers":
        fichiers = trouver_fichiers_par_pattern(
            c["dossier"], c["motifs"], c.get("age_jours", 0)
        )
        c["_fichiers"] = fichiers
        taille = sum(f.stat().st_size for f in fichiers if f.exists())
        return {"taille": taille, "nb": len(fichiers)}
    return {"taille": 0, "nb": 0}

# ─── Nettoyage ────────────────────────────────────────────────────────────────

def nettoyer_cible(c: dict) -> tuple[int, int]:
    """Supprime le contenu. Retourne (octets_liberes, nb_erreurs)."""
    libere = 0
    erreurs = 0

    if c["type"] == "dossier":
        chemin = c["chemin"]
        for item in chemin.iterdir():
            try:
                taille = item.stat().st_size if item.is_file() else taille_dossier(item)
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
                libere += taille
            except OSError:
                erreurs += 1

    elif c["type"] == "fichiers":
        for f in c.get("_fichiers", []):
            try:
                taille = f.stat().st_size
                f.unlink()
                libere += taille
            except OSError:
                erreurs += 1

    return libere, erreurs

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Nettoie les caches, temp et vieux fichiers systeme.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Cibles nettoyees par defaut :
  Windows : TEMP, cache miniatures, INetCache, crash dumps,
            caches Chrome / Edge / Firefox
  Linux   : /tmp, caches navigateurs dans ~/.cache

Exemples :
  python nettoyeur_systeme.py                   # simulation (aucune suppression)
  python nettoyeur_systeme.py --forcer          # nettoyage reel
  python nettoyeur_systeme.py --forcer --logs   # inclure les anciens fichiers .log
        """
    )
    parser.add_argument("-f", "--forcer", action="store_true",
                        help="Nettoyer reellement (sans --forcer : simulation uniquement)")
    parser.add_argument("--logs", action="store_true",
                        help="Inclure les fichiers de log anciens")
    parser.add_argument("--age-logs", type=int, default=30, metavar="JOURS",
                        help="Age minimum des logs a supprimer en jours (defaut : 30)")
    return parser.parse_args()


def main():
    args = parse_args()
    simulation = not args.forcer

    print(f"\n{gras('=== Nettoyeur systeme ===')} — {platform.system()}")
    if simulation:
        print(jaune("  Mode : SIMULATION (utilisez --forcer pour nettoyer reellement)"))
    else:
        print(rouge("  Mode : NETTOYAGE REEL"))
    print()

    cibles = construire_cibles(args)
    if not cibles:
        print(jaune("Aucune cible trouvee sur ce systeme."))
        sys.exit(0)

    # Analyse
    print("  Analyse en cours...")
    total_taille = 0
    total_nb     = 0
    resultats    = []

    for c in cibles:
        stats = analyser_cible(c)
        c["_stats"] = stats
        total_taille += stats["taille"]
        total_nb     += stats["nb"]
        resultats.append(c)

    # Affichage du rapport
    print()
    print(f"  {'Cible':<42} {'Fichiers':>8}  {'Taille':>10}")
    print(dim("  " + "-" * 64))
    for c in resultats:
        stats = c["_stats"]
        if stats["nb"] == 0:
            couleur_label = dim
        elif stats["taille"] > 100 * 1024 * 1024:  # > 100 Mo
            couleur_label = rouge
        elif stats["taille"] > 10 * 1024 * 1024:   # > 10 Mo
            couleur_label = jaune
        else:
            couleur_label = vert
        print(f"  {couleur_label(c['label']):<52} {stats['nb']:>8}  "
              f"{taille_lisible(stats['taille']):>10}")

    print(dim("  " + "-" * 64))
    print(f"  {'Total':<42} {total_nb:>8}  {taille_lisible(total_taille):>10}")
    print()

    if total_nb == 0:
        print(vert("  Rien a nettoyer. Le systeme est deja propre."))
        return

    if simulation:
        print(jaune(f"  Espace recuperable : {taille_lisible(total_taille)}"))
        print(dim("  Relancez avec --forcer pour effectuer le nettoyage."))
        return

    # Confirmation
    print(rouge(f"  Supprimer {total_nb} fichier(s) ({taille_lisible(total_taille)}) ? [o/N] : "), end="")
    if input().strip().lower() != "o":
        print(jaune("Annule."))
        sys.exit(0)

    # Nettoyage
    print()
    total_libere = 0
    total_erreurs = 0
    for c in resultats:
        if c["_stats"]["nb"] == 0:
            continue
        print(f"  Nettoyage : {c['label']}...", end=" ", flush=True)
        libere, erreurs = nettoyer_cible(c)
        total_libere  += libere
        total_erreurs += erreurs
        print(vert(f"OK — {taille_lisible(libere)} liberes"))

    print()
    print(gras(f"  Espace libere : {taille_lisible(total_libere)}"))
    if total_erreurs:
        print(jaune(f"  {total_erreurs} element(s) n'ont pas pu etre supprimes (permissions)"))


if __name__ == "__main__":
    main()
