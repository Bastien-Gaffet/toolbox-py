#!/usr/bin/env python3
"""
geo_ip.py
Géolocalise une ou plusieurs adresses IP (ou noms de domaine) et affiche
pays, ville, coordonnées, fuseau horaire, fournisseur d'accès, organisation,
et des indices de sécurité (proxy/VPN, hébergeur, mobile).

Données : API publique gratuite ip-api.com (sans clé, ~45 requêtes/min).

Deux façons de l'utiliser :

  1. Mode interactif — lancez sans rien :
         python geo_ip.py
     (affiche votre propre IP publique, puis vous pouvez en saisir d'autres)

  2. Mode arguments :
         python geo_ip.py                    # ma propre IP publique
         python geo_ip.py 8.8.8.8
         python geo_ip.py google.com         # résout le domaine
         python geo_ip.py 8.8.8.8 1.1.1.1    # plusieurs d'un coup
         python geo_ip.py --fichier ips.txt  # une IP/domaine par ligne
         python geo_ip.py 8.8.8.8 --json     # sortie JSON brute

Prérequis :
    pip install requests
"""

import os
import sys
import json
import argparse
from pathlib import Path


def _init_terminal():
    """Sortie UTF-8 (emojis, accents) + couleurs ANSI sous Windows."""
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

# ─── Dépendance requests ─────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    print(rouge("requests est requis : ") + "pip install requests")
    sys.exit(1)


API = "http://ip-api.com"
# Champs demandés à l'API (voir https://ip-api.com/docs/api:json)
CHAMPS = ("status,message,query,country,countryCode,regionName,city,zip,"
          "lat,lon,timezone,isp,org,as,reverse,mobile,proxy,hosting")


def drapeau(code_pays: str) -> str:
    """Convertit un code pays ISO (FR) en emoji drapeau (🇫🇷)."""
    if not code_pays or len(code_pays) != 2:
        return ""
    try:
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code_pays.upper())
    except (TypeError, ValueError):
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# REQUÊTES API
# ═══════════════════════════════════════════════════════════════════════════

def interroger_une(query: str) -> dict:
    """Géolocalise une seule cible (query vide = IP publique de l'appelant)."""
    url = f"{API}/json/{query}" if query else f"{API}/json/"
    r = requests.get(url, params={"fields": CHAMPS, "lang": "fr"}, timeout=15)
    r.raise_for_status()
    return r.json()


def interroger_lot(queries: list) -> list:
    """Géolocalise plusieurs cibles en une requête (endpoint /batch, max 100)."""
    corps = [{"query": q, "fields": CHAMPS, "lang": "fr"} for q in queries]
    r = requests.post(f"{API}/batch", json=corps, timeout=20)
    r.raise_for_status()
    return r.json()


# ═══════════════════════════════════════════════════════════════════════════
# AFFICHAGE
# ═══════════════════════════════════════════════════════════════════════════

def afficher(res: dict, cible_demandee: str = ""):
    """Affiche joliment un résultat de géolocalisation."""
    demande = cible_demandee or res.get("query", "?")

    if res.get("status") != "success":
        msg = res.get("message", "échec")
        print(f"\n  {rouge('✗')} {gras(demande)} — {rouge(msg)}")
        return

    ip = res.get("query", "?")
    pays = res.get("country", "?")
    cc = res.get("countryCode", "")
    ville = res.get("city", "")
    region = res.get("regionName", "")
    zip_ = res.get("zip", "")
    lat, lon = res.get("lat"), res.get("lon")

    localite = ", ".join(x for x in (ville, region) if x)
    if zip_:
        localite += f" ({zip_})" if localite else zip_

    entete = f"{gras(ip)}"
    if demande != ip:                     # domaine résolu → montrer les deux
        entete = f"{gras(demande)}  →  {ip}"

    print(f"\n  {cyan('┌─')} {entete}")
    print(f"  {cyan('│')}  🌍 Pays      : {pays} {drapeau(cc)} {dim('(' + cc + ')') if cc else ''}")
    if localite:
        print(f"  {cyan('│')}  📍 Localité  : {localite}")
    if lat is not None and lon is not None:
        print(f"  {cyan('│')}  🧭 Coord.    : {lat}, {lon}")
        print(f"  {cyan('│')}  🗺  Carte     : {dim(f'https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=11/{lat}/{lon}')}")
    if res.get("timezone"):
        print(f"  {cyan('│')}  🕒 Fuseau    : {res['timezone']}")
    if res.get("isp"):
        print(f"  {cyan('│')}  🏢 FAI       : {res['isp']}")
    if res.get("org") and res.get("org") != res.get("isp"):
        print(f"  {cyan('│')}  🏷  Org.      : {res['org']}")
    if res.get("as"):
        print(f"  {cyan('│')}  🔗 AS        : {res['as']}")
    if res.get("reverse"):
        print(f"  {cyan('│')}  🔁 Reverse   : {res['reverse']}")

    # Indices de sécurité
    marqueurs = []
    if res.get("proxy"):
        marqueurs.append(jaune("proxy/VPN"))
    if res.get("hosting"):
        marqueurs.append(jaune("hébergeur/datacenter"))
    if res.get("mobile"):
        marqueurs.append(cyan("réseau mobile"))
    if marqueurs:
        print(f"  {cyan('│')}  ⚠️  Indices   : {', '.join(marqueurs)}")
    print(f"  {cyan('└─')}")


# ═══════════════════════════════════════════════════════════════════════════
# COLLECTE DES CIBLES
# ═══════════════════════════════════════════════════════════════════════════

def lire_fichier(chemin: str) -> list:
    p = Path(chemin)
    if not p.exists():
        print(rouge(f"Fichier introuvable : {chemin}"))
        sys.exit(1)
    cibles = []
    for ligne in p.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if ligne:
            cibles.append(ligne)
    return cibles


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="🌍 Géolocalise des adresses IP ou domaines (ip-api.com).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python geo_ip.py                    (ma propre IP publique)
  python geo_ip.py 8.8.8.8
  python geo_ip.py google.com
  python geo_ip.py 8.8.8.8 1.1.1.1
  python geo_ip.py --fichier ips.txt
  python geo_ip.py 8.8.8.8 --json
""",
    )
    p.add_argument("cibles", nargs="*", metavar="IP|DOMAINE",
                   help="Adresses IP ou domaines (vide = votre IP publique)")
    p.add_argument("--fichier", metavar="FICHIER",
                   help="Lire les cibles depuis un fichier (une par ligne)")
    p.add_argument("--json", action="store_true",
                   help="Afficher la réponse JSON brute")
    return p.parse_args()


def main():
    args = parse_args()

    cibles = list(args.cibles)
    if args.fichier:
        cibles += lire_fichier(args.fichier)

    # Aucune cible → sa propre IP publique
    interactif = not cibles and not args.fichier
    propre_ip = not cibles

    try:
        if propre_ip:
            print(gras(cyan("\n🌍 Géolocalisation IP")))
            resultats = [interroger_une("")]
            demandes = [""]
        elif len(cibles) == 1:
            resultats = [interroger_une(cibles[0])]
            demandes = cibles
        else:
            resultats = interroger_lot(cibles)
            demandes = cibles
    except requests.RequestException as e:
        print(rouge(f"\n❌ Erreur réseau : {e}"))
        sys.exit(1)

    if args.json:
        print(json.dumps(resultats if len(resultats) > 1 else resultats[0],
                         ensure_ascii=False, indent=2))
    else:
        for demande, res in zip(demandes, resultats):
            afficher(res, demande)
        print()

    # Mode interactif : proposer d'autres recherches
    if interactif:
        print(dim("  Entrez une IP/domaine (vide pour quitter) :"))
        while True:
            try:
                q = input("  › ").strip()
            except EOFError:
                break
            if not q:
                break
            try:
                afficher(interroger_une(q), q)
            except requests.RequestException as e:
                print(rouge(f"  ❌ {e}"))
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(jaune("\nInterrompu."))
        sys.exit(130)
