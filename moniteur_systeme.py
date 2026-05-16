#!/usr/bin/env python3
"""
moniteur_systeme.py
Tableau de bord terminal : CPU, RAM, disque, reseau, processus gourmands.
Rafraichi en temps reel. Ctrl+C pour quitter.

Usage :
    python moniteur_systeme.py
    python moniteur_systeme.py --intervalle 5 --top 15
    python moniteur_systeme.py --une-fois
"""

import sys
import time
import argparse
import platform

# ─── Verification psutil ──────────────────────────────────────────────────────

try:
    import psutil
except ImportError:
    print("La bibliotheque 'psutil' est requise : pip install psutil")
    sys.exit(1)

# ─── Couleurs terminal ────────────────────────────────────────────────────────

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    def rouge(t):  return Fore.RED     + t + Style.RESET_ALL
    def vert(t):   return Fore.GREEN   + t + Style.RESET_ALL
    def jaune(t):  return Fore.YELLOW  + t + Style.RESET_ALL
    def cyan(t):   return Fore.CYAN    + t + Style.RESET_ALL
    def blanc(t):  return Fore.WHITE   + t + Style.RESET_ALL
    def gras(t):   return Style.BRIGHT + t + Style.RESET_ALL
    def dim(t):    return Style.DIM    + t + Style.RESET_ALL
except ImportError:
    def rouge(t):  return t
    def vert(t):   return t
    def jaune(t):  return t
    def cyan(t):   return t
    def blanc(t):  return t
    def gras(t):   return t
    def dim(t):    return t

LARGEUR_BARRE = 22

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for u in ("o", "Ko", "Mo", "Go", "To"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} Po"


def barre(pct: float, largeur: int = LARGEUR_BARRE) -> str:
    pct = max(0.0, min(100.0, pct))
    rempli = int(largeur * pct / 100)
    b = "[" + "=" * rempli + "." * (largeur - rempli) + "]"
    if pct >= 80:
        return rouge(b)
    if pct >= 50:
        return jaune(b)
    return vert(b)


def couleur_pct(pct: float) -> str:
    s = f"{pct:5.1f}%"
    if pct >= 80:
        return rouge(s)
    if pct >= 50:
        return jaune(s)
    return vert(s)


def effacer_ecran():
    print("\033[2J\033[H", end="", flush=True)

# ─── Collecte des donnees ─────────────────────────────────────────────────────

class SnapshotReseau:
    """Garde le dernier snapshot reseau pour calculer les debits."""
    def __init__(self):
        self.temps = time.time()
        c = psutil.net_io_counters()
        self.envoye = c.bytes_sent
        self.recu   = c.bytes_recv

    def debits(self) -> tuple[float, float]:
        """Retourne (envoye_par_s, recu_par_s) depuis le dernier snapshot."""
        maintenant = time.time()
        delta = max(maintenant - self.temps, 0.1)
        c = psutil.net_io_counters()
        envoye_s = (c.bytes_sent - self.envoye) / delta
        recu_s   = (c.bytes_recv - self.recu)   / delta
        self.temps  = maintenant
        self.envoye = c.bytes_sent
        self.recu   = c.bytes_recv
        return envoye_s, recu_s

# ─── Affichage ────────────────────────────────────────────────────────────────

def afficher_cpu(avec_cores: bool):
    total = psutil.cpu_percent()
    print(f"  CPU total : {barre(total)} {couleur_pct(total)}"
          f"  —  {psutil.cpu_count(logical=True)} coeur(s) logique(s)")

    if avec_cores:
        cores = psutil.cpu_percent(percpu=True)
        for i, pct in enumerate(cores):
            print(f"    Core {i:<2} : {barre(pct, 16)} {couleur_pct(pct)}")

    try:
        freq = psutil.cpu_freq()
        if freq:
            print(dim(f"    {freq.current:.0f} MHz (max {freq.max:.0f} MHz)"))
    except Exception:
        pass


def afficher_ram():
    ram = psutil.virtual_memory()
    print(f"  RAM       : {barre(ram.percent)} {couleur_pct(ram.percent)}"
          f"  {taille_lisible(ram.used)} / {taille_lisible(ram.total)}")
    try:
        swap = psutil.swap_memory()
        if swap.total > 0:
            print(f"  Swap      : {barre(swap.percent)} {couleur_pct(swap.percent)}"
                  f"  {taille_lisible(swap.used)} / {taille_lisible(swap.total)}")
    except Exception:
        pass


def afficher_disques():
    print(f"  Disques :")
    try:
        partitions = psutil.disk_partitions()
    except Exception:
        return
    for p in partitions:
        if "cdrom" in p.opts or not p.mountpoint:
            continue
        try:
            usage = psutil.disk_usage(p.mountpoint)
        except (PermissionError, OSError):
            continue
        point = p.mountpoint[:12]
        print(f"    {point:<14} {barre(usage.percent, 18)} {couleur_pct(usage.percent)}"
              f"  {taille_lisible(usage.used)} / {taille_lisible(usage.total)}")


def afficher_reseau(snap: SnapshotReseau):
    envoye_s, recu_s = snap.debits()
    print(f"  Reseau    :  envoye {taille_lisible(int(envoye_s))}/s  "
          f"|  recu {taille_lisible(int(recu_s))}/s")


def afficher_temperatures():
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return
        print("  Temperatures :")
        for nom, entrees in list(temps.items())[:3]:
            for e in entrees[:2]:
                pct = (e.current / (e.high or 100)) * 100 if e.high else e.current
                print(f"    {nom:<20} {couleur_pct(pct)} ({e.current:.0f} degC)")
    except (AttributeError, Exception):
        pass


def afficher_processus(top: int, trier_par: str):
    print(f"  Processus (top {top} par {trier_par}) :")
    print(dim(f"  {'PID':<7} {'Nom':<26} {'CPU%':>6}  {'RAM':>8}"))

    attrs = ["pid", "name", "cpu_percent", "memory_info"]
    procs = []
    for p in psutil.process_iter(attrs):
        try:
            info = p.info
            if info["cpu_percent"] is None:
                continue
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    cle = "cpu_percent" if trier_par == "cpu" else (
        lambda x: x["memory_info"].rss if x["memory_info"] else 0
    )
    if trier_par == "ram":
        procs.sort(key=lambda x: x["memory_info"].rss if x["memory_info"] else 0, reverse=True)
    else:
        procs.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)

    for info in procs[:top]:
        pid  = info["pid"]
        nom  = (info["name"] or "?")[:25]
        cpu  = info["cpu_percent"] or 0
        ram  = info["memory_info"].rss if info["memory_info"] else 0
        ligne = f"  {pid:<7} {nom:<26} {couleur_pct(cpu)}  {taille_lisible(ram):>8}"
        print(ligne)


def afficher_tableau(args, snap: SnapshotReseau, iteration: int):
    effacer_ecran()
    maintenant = time.strftime("%Y-%m-%d %H:%M:%S")
    if args.une_fois:
        entete = f"=== Moniteur systeme — {maintenant} ==="
    else:
        entete = f"=== Moniteur systeme — {maintenant} — Refresh: {args.intervalle}s (Ctrl+C pour quitter) ==="
    print(gras(entete))
    print()

    afficher_cpu(args.cores)
    print()
    afficher_ram()
    print()
    afficher_disques()
    print()
    afficher_reseau(snap)

    if not args.sans_temp:
        afficher_temperatures()

    print()
    afficher_processus(args.top, args.trier)

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Tableau de bord terminal en temps reel (CPU, RAM, disque, processus).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python moniteur_systeme.py
  python moniteur_systeme.py --intervalle 5 --top 15
  python moniteur_systeme.py --une-fois --trier ram
  python moniteur_systeme.py --cores
        """
    )
    parser.add_argument("--intervalle", type=float, default=2.0, metavar="S",
                        help="Secondes entre chaque rafraichissement (defaut : 2)")
    parser.add_argument("--top", type=int, default=10, metavar="N",
                        help="Nombre de processus a afficher (defaut : 10)")
    parser.add_argument("--trier", choices=["cpu", "ram"], default="cpu",
                        help="Trier les processus par cpu ou ram (defaut : cpu)")
    parser.add_argument("--cores", action="store_true",
                        help="Afficher l'utilisation de chaque coeur CPU")
    parser.add_argument("--sans-temp", action="store_true",
                        help="Ne pas afficher les temperatures")
    parser.add_argument("--une-fois", action="store_true",
                        help="Afficher une seule fois sans boucle de rafraichissement")
    return parser.parse_args()


def main():
    args = parse_args()

    # Premier appel pour initialiser les compteurs CPU (valeur de reference)
    psutil.cpu_percent(percpu=True)
    snap = SnapshotReseau()

    if args.une_fois:
        time.sleep(max(args.intervalle, 1.0))
        afficher_tableau(args, snap, 1)
        return

    iteration = 0
    try:
        while True:
            time.sleep(args.intervalle)
            iteration += 1
            afficher_tableau(args, snap, iteration)
    except KeyboardInterrupt:
        print("\n\nMoniteur arrete.")


if __name__ == "__main__":
    main()
