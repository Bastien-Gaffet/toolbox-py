#!/usr/bin/env python3
"""
scan_reseau.py
Scanne le réseau local : liste les appareils connectés (IP, nom, MAC,
fabricant), détecte les ports ouverts sur chaque hôte actif.

Usage :
    python scan_reseau.py
    python scan_reseau.py --reseau 192.168.0.0/24
    python scan_reseau.py --ports --csv resultats.csv
"""

import os
import sys
import csv
import time
import socket
import platform
import argparse
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Couleurs terminal ────────────────────────────────────────────────────────

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    def rouge(t):  return Fore.RED     + t + Style.RESET_ALL
    def vert(t):   return Fore.GREEN   + t + Style.RESET_ALL
    def jaune(t):  return Fore.YELLOW  + t + Style.RESET_ALL
    def cyan(t):   return Fore.CYAN    + t + Style.RESET_ALL
    def gras(t):   return Style.BRIGHT + t + Style.RESET_ALL
    def dim(t):    return Style.DIM    + t + Style.RESET_ALL
except ImportError:
    def rouge(t):  return t
    def vert(t):   return t
    def jaune(t):  return t
    def cyan(t):   return t
    def gras(t):   return t
    def dim(t):    return t

# ─── Ports courants à scanner ─────────────────────────────────────────────────

PORTS_COURANTS = {
    21:   "FTP",
    22:   "SSH",
    23:   "Telnet",
    25:   "SMTP",
    53:   "DNS",
    80:   "HTTP",
    110:  "POP3",
    139:  "NetBIOS",
    143:  "IMAP",
    443:  "HTTPS",
    445:  "SMB",
    548:  "AFP",
    993:  "IMAPS",
    995:  "POP3S",
    1883: "MQTT",
    3306: "MySQL",
    3389: "RDP",
    5900: "VNC",
    8080: "HTTP-alt",
    8443: "HTTPS-alt",
    9100: "Imprimante",
}

# ─── Détection du réseau local ────────────────────────────────────────────────

def ip_locale() -> str:
    """Retourne l'IP locale principale (celle par laquelle on sort)."""
    try:
        # Connexion UDP fictive pour trouver l'IP sortante sans envoyer de paquets
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def reseau_depuis_ip(ip: str) -> tuple[str, list[str]]:
    """Retourne le préfixe réseau et la liste des IPs à scanner (/24)."""
    parties = ip.split(".")
    prefixe  = ".".join(parties[:3])
    ips      = [f"{prefixe}.{i}" for i in range(1, 255)]
    return prefixe + ".0/24", ips


def parser_reseau(cidr: str) -> tuple[str, list[str]]:
    """Parse un CIDR /24 fourni par l'utilisateur."""
    base = cidr.split("/")[0]
    parties = base.split(".")
    prefixe = ".".join(parties[:3])
    ips = [f"{prefixe}.{i}" for i in range(1, 255)]
    return cidr, ips

# ─── Ping ─────────────────────────────────────────────────────────────────────

def ping(ip: str, timeout_ms: int = 800) -> bool:
    """Retourne True si l'IP répond au ping."""
    systeme = platform.system().lower()
    if systeme == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    else:
        timeout_s = max(1, timeout_ms // 1000)
        cmd = ["ping", "-c", "1", "-W", str(timeout_s), ip]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_ms / 1000 + 1,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

# ─── Résolution DNS ───────────────────────────────────────────────────────────

def nom_hote(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except socket.herror:
        return ""

# ─── Table ARP ────────────────────────────────────────────────────────────────

def lire_arp() -> dict[str, str]:
    """Lit la table ARP du système. Retourne {ip: mac}."""
    macs = {}
    systeme = platform.system().lower()

    try:
        if systeme == "windows":
            resultat = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            for ligne in resultat.stdout.splitlines():
                parties = ligne.split()
                # Format Windows : "  192.168.1.1    00-11-22-33-44-55    dynamic"
                if len(parties) >= 2 and "-" in parties[1]:
                    ip  = parties[0].strip()
                    mac = parties[1].strip().replace("-", ":").upper()
                    macs[ip] = mac
        else:
            # Linux : "ip neigh" ou "arp -n"
            for cmd in [["ip", "neigh"], ["arp", "-n"]]:
                try:
                    resultat = subprocess.run(cmd, capture_output=True, text=True)
                    for ligne in resultat.stdout.splitlines():
                        parties = ligne.split()
                        if not parties:
                            continue
                        ip = parties[0]
                        # Chercher une MAC (format XX:XX:XX:XX:XX:XX)
                        for partie in parties:
                            if len(partie) == 17 and partie.count(":") == 5:
                                macs[ip] = partie.upper()
                                break
                    if macs:
                        break
                except FileNotFoundError:
                    continue
    except Exception:
        pass

    return macs

# ─── Fabricant via API macvendors.com ─────────────────────────────────────────

_cache_vendeurs: dict[str, str] = {}

def fabricant_mac(mac: str) -> str:
    """Retourne le fabricant du matériel via les 3 premiers octets de la MAC."""
    if not mac or mac in ("FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"):
        return ""

    oui = mac[:8]  # "AA:BB:CC"
    if oui in _cache_vendeurs:
        return _cache_vendeurs[oui]

    try:
        import urllib.request
        url = f"https://api.macvendors.com/{oui}"
        req = urllib.request.Request(url, headers={"User-Agent": "scan_reseau/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            vendeur = resp.read().decode("utf-8", errors="replace").strip()
            _cache_vendeurs[oui] = vendeur
            time.sleep(0.8)  # Respect du rate limit (1 req/s max)
            return vendeur
    except Exception:
        _cache_vendeurs[oui] = ""
        return ""

# ─── Scan de ports ────────────────────────────────────────────────────────────

def scanner_ports(ip: str, ports: dict, timeout: float = 0.5) -> list[tuple[int, str]]:
    """Retourne la liste des ports ouverts [(port, service), ...]."""
    ouverts = []
    for port, service in ports.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                ouverts.append((port, service))
            s.close()
        except OSError:
            pass
    return ouverts

# ─── Scan principal ───────────────────────────────────────────────────────────

def scanner_hote(ip: str, avec_dns: bool, timeout_ms: int) -> dict | None:
    """Scanne un hôte. Retourne ses infos ou None s'il ne répond pas."""
    if not ping(ip, timeout_ms):
        return None
    nom = nom_hote(ip) if avec_dns else ""
    return {"ip": ip, "nom": nom}


def scanner_reseau(ips: list[str], threads: int, timeout_ms: int,
                   avec_dns: bool, avec_ports: bool,
                   avec_vendeur: bool) -> list[dict]:
    """Scanne toutes les IPs en parallèle et retourne les hôtes actifs."""
    actifs = []
    total  = len(ips)
    fait   = [0]

    print(f"\nScan de {total} adresses ({threads} threads simultanés)...\n")

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {pool.submit(scanner_hote, ip, avec_dns, timeout_ms): ip for ip in ips}
        for future in as_completed(futures):
            fait[0] += 1
            print(f"  Progression : {fait[0]}/{total}", end="\r")
            resultat = future.result()
            if resultat:
                actifs.append(resultat)

    print(f"  {len(actifs)} hôte(s) actif(s) trouvé(s)           \n")

    if not actifs:
        return []

    # Trier par dernier octet de l'IP
    actifs.sort(key=lambda h: int(h["ip"].split(".")[-1]))

    # Lire la table ARP une seule fois pour tous les hôtes
    macs = lire_arp()

    for hote in actifs:
        hote["mac"]     = macs.get(hote["ip"], "")
        hote["vendeur"] = ""
        hote["ports"]   = []

        if avec_vendeur and hote["mac"]:
            hote["vendeur"] = fabricant_mac(hote["mac"])

        if avec_ports:
            hote["ports"] = scanner_ports(hote["ip"], PORTS_COURANTS)

    return actifs

# ─── Affichage ────────────────────────────────────────────────────────────────

def afficher(actifs: list[dict], reseau: str, avec_ports: bool):
    print()
    print(gras("=" * 70))
    print(gras(f"  RÉSEAU LOCAL : {reseau}"))
    print(gras("=" * 70))
    print(f"  Hôtes actifs : {gras(str(len(actifs)))}   —   "
          f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    for hote in actifs:
        ip      = hote["ip"]
        nom     = hote.get("nom", "")
        mac     = hote.get("mac", "")
        vendeur = hote.get("vendeur", "")
        ports   = hote.get("ports", [])

        label = vert(f"  {ip:<18}")
        if nom:
            label += cyan(f"  {nom}")
        print(label)

        if mac:
            print(dim(f"    MAC     : {mac}") +
                  (f"  ({vendeur})" if vendeur else ""))
        if ports:
            ports_str = ", ".join(f"{p}/{s}" for p, s in ports)
            print(dim(f"    Ports   : ") + jaune(ports_str))
        elif avec_ports:
            print(dim("    Ports   : aucun port courant ouvert"))

    print()

# ─── Export CSV ───────────────────────────────────────────────────────────────

def exporter_csv(actifs: list[dict], chemin_sortie: str):
    with open(chemin_sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["IP", "Nom", "MAC", "Fabricant", "Ports ouverts"])
        for hote in actifs:
            ports_str = " | ".join(f"{p}/{s}" for p, s in hote.get("ports", []))
            w.writerow([
                hote["ip"],
                hote.get("nom", ""),
                hote.get("mac", ""),
                hote.get("vendeur", ""),
                ports_str,
            ])
    print(vert(f"Export CSV : {chemin_sortie}"))

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scanne le réseau local et liste les appareils connectés.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python scan_reseau.py
  python scan_reseau.py --reseau 192.168.0.0/24
  python scan_reseau.py --ports --vendeur
  python scan_reseau.py --ports --csv scan.csv
        """
    )
    parser.add_argument("--reseau", metavar="CIDR",
                        help="Réseau à scanner en notation CIDR (ex: 192.168.1.0/24)\n"
                             "Défaut : détection automatique")
    parser.add_argument("--ports", action="store_true",
                        help="Scanner les ports courants sur chaque hôte actif")
    parser.add_argument("--vendeur", action="store_true",
                        help="Récupérer le fabricant via l'adresse MAC (nécessite internet)")
    parser.add_argument("--sans-dns", action="store_true",
                        help="Ne pas résoudre les noms d'hôtes (plus rapide)")
    parser.add_argument("--threads", type=int, default=100, metavar="N",
                        help="Nombre de threads pour le ping sweep (défaut : 100)")
    parser.add_argument("--timeout", type=int, default=800, metavar="MS",
                        help="Timeout du ping en millisecondes (défaut : 800)")
    parser.add_argument("--csv", metavar="FICHIER",
                        help="Exporter les résultats en CSV")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.reseau:
        reseau, ips = parser_reseau(args.reseau)
    else:
        ip_loc = ip_locale()
        reseau, ips = reseau_depuis_ip(ip_loc)
        print(f"\nIP locale détectée : {ip_loc}")
        print(f"Réseau cible       : {reseau}")

    actifs = scanner_reseau(
        ips        = ips,
        threads    = args.threads,
        timeout_ms = args.timeout,
        avec_dns   = not args.sans_dns,
        avec_ports = args.ports,
        avec_vendeur = args.vendeur,
    )

    if not actifs:
        print(jaune("Aucun hôte actif trouvé."))
        sys.exit(0)

    afficher(actifs, reseau, avec_ports=args.ports)

    if args.csv:
        exporter_csv(actifs, args.csv)


if __name__ == "__main__":
    main()
