#!/usr/bin/env python3
"""
telechargeur_batch.py
Télécharge une liste d'URLs depuis un fichier texte.
Supporte la reprise en cas d'interruption, le renommage automatique,
la vérification d'intégrité par hash et l'authentification par cookie.

Format du fichier d'URLs (une entrée par ligne) :
    # Commentaire
    https://example.com/fichier.pdf
    https://example.com/cours.pdf  cours_ch1.pdf
    https://example.com/data.zip   data.zip   sha256:abc123...

Usage :
    python telechargeur_batch.py liste.txt --sortie ./downloads
    python telechargeur_batch.py liste.txt --cookie "SESSION=abc123"
    python telechargeur_batch.py liste.txt --cookie-fichier cookies.txt
"""

import os
import sys
import csv
import time
import hashlib
import argparse
import threading
from pathlib import Path
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Module manquant. Installez-le avec : pip install requests")
    sys.exit(1)

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

# ─── Verrou pour l'affichage concurrent ──────────────────────────────────────

_verrou_print = threading.Lock()

def afficher(msg: str):
    with _verrou_print:
        print(msg)

# ─── Formatage ────────────────────────────────────────────────────────────────

def fmt_taille(octets: int) -> str:
    for unite in ["o", "Ko", "Mo", "Go"]:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} To"

def fmt_vitesse(octets_par_sec: float) -> str:
    return fmt_taille(int(octets_par_sec)) + "/s"

def fmt_eta(secondes: float) -> str:
    if secondes < 0 or secondes > 86400:
        return "?"
    if secondes < 60:
        return f"{int(secondes)}s"
    if secondes < 3600:
        return f"{int(secondes // 60)}m{int(secondes % 60):02d}s"
    return f"{int(secondes // 3600)}h{int((secondes % 3600) // 60):02d}m"

# ─── Parsing du fichier d'URLs ────────────────────────────────────────────────

def parser_liste(chemin: Path) -> list[dict]:
    """
    Parse le fichier d'URLs. Format par ligne :
      URL [nom_fichier] [sha256:hash | md5:hash]

    Lignes vides et lignes commençant par # sont ignorées.
    """
    entrees = []
    with open(chemin, encoding="utf-8") as f:
        for num, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue

            parties = ligne.split()
            url = parties[0]

            if not url.startswith(("http://", "https://")):
                print(jaune(f"  Ligne {num} ignorée (pas une URL) : {url[:60]}"))
                continue

            nom = None
            hash_attendu = None
            hash_algo    = None

            for partie in parties[1:]:
                if partie.startswith(("sha256:", "sha1:", "md5:")):
                    algo, val = partie.split(":", 1)
                    hash_algo    = algo
                    hash_attendu = val
                elif not nom:
                    nom = partie

            entrees.append({
                "url":          url,
                "nom_force":    nom,
                "hash_attendu": hash_attendu,
                "hash_algo":    hash_algo,
            })

    return entrees

# ─── Nom de fichier depuis une réponse HTTP ──────────────────────────────────

def nom_depuis_reponse(resp: requests.Response, url: str) -> str:
    """Détermine le nom de fichier depuis Content-Disposition ou l'URL."""
    import re

    cd = resp.headers.get("Content-Disposition", "")
    if cd:
        # Chercher filename*=UTF-8''nom ou filename="nom"
        match = re.search(
            r"filename\*?\s*=\s*(?:UTF-8''|\"?)([^\";\r\n]+)",
            cd, re.IGNORECASE
        )
        if match:
            return unquote(match.group(1).strip().strip('"'))

    # Fallback : dernier segment de l'URL
    parsed = urlparse(url)
    nom = unquote(parsed.path.split("/")[-1])
    if not nom or "." not in nom:
        # URL sans extension lisible (ex: download?id=42)
        nom = "fichier_" + str(abs(hash(url)) % 100000)

    return nom

# ─── Hash d'un fichier ────────────────────────────────────────────────────────

def hash_fichier(chemin: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(chemin, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# ─── Barre de progression ─────────────────────────────────────────────────────

def barre_progression(telecharge: int, total: int, largeur: int = 25) -> str:
    if total <= 0:
        return "[" + "?" * largeur + "]"
    pct  = min(1.0, telecharge / total)
    plein = int(pct * largeur)
    return "[" + "=" * plein + ">" * min(1, largeur - plein) + "." * max(0, largeur - plein - 1) + "]"

# ─── Téléchargement d'un fichier ─────────────────────────────────────────────

def telecharger(entree: dict, session: requests.Session,
                dossier: Path, retries: int, timeout: int) -> dict:
    """
    Télécharge un fichier avec reprise automatique.
    Retourne un dict de résultat {url, nom, statut, taille, erreur}.
    """
    url     = entree["url"]
    nom_req = entree.get("nom_force")

    # ── Première requête HEAD pour obtenir le nom et la taille ──────────────
    try:
        head = session.head(url, timeout=timeout, allow_redirects=True)
        if nom_req:
            nom = nom_req
        else:
            nom = nom_depuis_reponse(head, url)
        taille_totale = int(head.headers.get("Content-Length", 0))
        supporte_range = "bytes" in head.headers.get("Accept-Ranges", "")
    except Exception as e:
        # HEAD non supporté par certains serveurs — on ira directement en GET
        nom           = nom_req or nom_depuis_reponse(
            type("R", (), {"headers": {}})(), url
        )
        taille_totale = 0
        supporte_range = True  # On tente quand même

    chemin_final = dossier / nom
    chemin_part  = dossier / (nom + ".part")

    # ── Vérifier si déjà téléchargé ─────────────────────────────────────────
    if chemin_final.exists() and not entree.get("hash_attendu"):
        afficher(dim(f"  [EXISTE]  {nom}"))
        return {"url": url, "nom": nom, "statut": "existe", "taille": chemin_final.stat().st_size}

    # ── Reprendre depuis .part si possible ───────────────────────────────────
    octets_depart = 0
    if chemin_part.exists() and supporte_range:
        octets_depart = chemin_part.stat().st_size
        if taille_totale and octets_depart >= taille_totale:
            # Fichier .part complet — renommer
            chemin_part.rename(chemin_final)
            octets_depart = 0

    headers = {}
    if octets_depart > 0:
        headers["Range"] = f"bytes={octets_depart}-"

    # ── Tentatives de téléchargement ─────────────────────────────────────────
    for tentative in range(1, retries + 2):
        try:
            resp = session.get(url, headers=headers, stream=True,
                               timeout=timeout, allow_redirects=True)

            if resp.status_code == 416:
                # Range not satisfiable — le fichier est peut-être complet
                chemin_part.rename(chemin_final)
                afficher(vert(f"  [OK]      {nom}  (reprise complète)"))
                return {"url": url, "nom": nom, "statut": "ok", "taille": chemin_final.stat().st_size}

            resp.raise_for_status()

            # Nom depuis la réponse GET si on ne l'avait pas encore
            if not nom_req and nom.startswith("fichier_"):
                nom_get = nom_depuis_reponse(resp, url)
                if nom_get and nom_get != nom:
                    nom = nom_get
                    chemin_final = dossier / nom
                    chemin_part  = dossier / (nom + ".part")

            taille_reelle = int(resp.headers.get("Content-Length", taille_totale or 0))
            taille_totale_dl = (octets_depart + taille_reelle) if taille_reelle else 0

            mode   = "ab" if octets_depart > 0 else "wb"
            telecharge = octets_depart
            debut  = time.time()

            with open(chemin_part, mode) as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        telecharge += len(chunk)

                        # Affichage de la progression
                        ecoule = time.time() - debut + 0.001
                        vitesse = (telecharge - octets_depart) / ecoule
                        barre = barre_progression(telecharge, taille_totale_dl)
                        eta   = fmt_eta((taille_totale_dl - telecharge) / vitesse) if vitesse and taille_totale_dl else "?"

                        with _verrou_print:
                            print(f"  {barre}  {fmt_taille(telecharge):>10}"
                                  f"  {fmt_vitesse(vitesse):>12}  ETA {eta:>5}  {nom[:40]}",
                                  end="\r", flush=True)

            print()  # Fin de la ligne de progression

            # Renommer .part en fichier final
            if chemin_final.exists():
                chemin_final.unlink()
            chemin_part.rename(chemin_final)

            # Vérification hash
            if entree.get("hash_attendu"):
                algo   = entree.get("hash_algo", "sha256")
                calcule = hash_fichier(chemin_final, algo)
                if calcule != entree["hash_attendu"]:
                    chemin_final.unlink()
                    msg = rouge(f"  [HASH KO] {nom}  ({algo} ne correspond pas)")
                    afficher(msg)
                    return {"url": url, "nom": nom, "statut": "hash_erreur",
                            "erreur": f"{algo} incorrect"}
                afficher(vert(f"  [OK]      {nom}  ({algo} verifie)"))
            else:
                afficher(vert(f"  [OK]      {nom}  ({fmt_taille(chemin_final.stat().st_size)})"))

            return {"url": url, "nom": nom, "statut": "ok", "taille": chemin_final.stat().st_size}

        except requests.RequestException as e:
            if tentative <= retries:
                delai = 2 ** tentative
                afficher(jaune(f"  [RETRY {tentative}] {nom}  -> {delai}s ({e})"))
                time.sleep(delai)
            else:
                # Supprimer le .part corrompu si trop petit
                if chemin_part.exists() and chemin_part.stat().st_size < 1024:
                    chemin_part.unlink()
                afficher(rouge(f"  [ECHEC]   {url[:60]}  -> {e}"))
                return {"url": url, "nom": nom, "statut": "echec", "erreur": str(e)}

    return {"url": url, "nom": nom, "statut": "echec", "erreur": "retries épuisés"}

# ─── Construction de la session HTTP ─────────────────────────────────────────

def creer_session(cookie_str: str = "", cookie_fichier: str = "") -> requests.Session:
    """Crée une session requests avec cookies et retry automatique."""
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Cookies via chaîne de caractères
    if cookie_str:
        for paire in cookie_str.split(";"):
            paire = paire.strip()
            if "=" in paire:
                nom, val = paire.split("=", 1)
                session.cookies.set(nom.strip(), val.strip())

    # Cookies via fichier (format "nom=valeur" une paire par ligne)
    if cookie_fichier:
        try:
            with open(cookie_fichier, encoding="utf-8") as f:
                for ligne in f:
                    ligne = ligne.strip()
                    if ligne and not ligne.startswith("#") and "=" in ligne:
                        nom, val = ligne.split("=", 1)
                        session.cookies.set(nom.strip(), val.strip())
        except FileNotFoundError:
            print(rouge(f"Fichier de cookies introuvable : {cookie_fichier}"))

    return session

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Télécharge une liste d'URLs avec reprise et vérification d'intégrité.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Format du fichier d'URLs :
  # Commentaire
  https://example.com/fichier.pdf
  https://example.com/cours.pdf   cours_chapitre1.pdf
  https://example.com/data.zip    data.zip   sha256:abc123...

Exemples :
  python telechargeur_batch.py liste.txt
  python telechargeur_batch.py liste.txt --sortie ~/Téléchargements
  python telechargeur_batch.py liste.txt --cookie "SESSION=abc; user=john"
  python telechargeur_batch.py liste.txt --cookie-fichier cookies.txt --threads 5
        """
    )
    parser.add_argument("fichier", help="Fichier texte contenant les URLs")
    parser.add_argument("-s", "--sortie", default=".", metavar="DOSSIER",
                        help="Dossier de destination (défaut : dossier courant)")
    parser.add_argument("--cookie", metavar="\"NOM=VAL; NOM2=VAL2\"",
                        help="Cookie(s) à envoyer avec chaque requête")
    parser.add_argument("--cookie-fichier", metavar="FICHIER",
                        help="Fichier de cookies (format : NOM=VALEUR, une paire par ligne)")
    parser.add_argument("-t", "--threads", type=int, default=3, metavar="N",
                        help="Téléchargements simultanés (défaut : 3)")
    parser.add_argument("-r", "--retries", type=int, default=3, metavar="N",
                        help="Nombre de tentatives en cas d'échec (défaut : 3)")
    parser.add_argument("--timeout", type=int, default=30, metavar="SEC",
                        help="Timeout de connexion en secondes (défaut : 30)")
    parser.add_argument("--csv", metavar="FICHIER",
                        help="Exporter le rapport de téléchargement en CSV")
    return parser.parse_args()


def main():
    args = parse_args()

    fichier_liste = Path(args.fichier)
    if not fichier_liste.exists():
        print(rouge(f"Fichier introuvable : {fichier_liste}"))
        sys.exit(1)

    dossier = Path(args.sortie)
    dossier.mkdir(parents=True, exist_ok=True)

    entrees = parser_liste(fichier_liste)
    if not entrees:
        print(jaune("Aucune URL valide trouvée dans le fichier."))
        sys.exit(0)

    session = creer_session(
        cookie_str    = args.cookie    or "",
        cookie_fichier = args.cookie_fichier or "",
    )

    print(f"\n{gras('Telechargeur batch')}")
    print(f"  URLs       : {len(entrees)}")
    print(f"  Destination: {dossier.resolve()}")
    print(f"  Threads    : {args.threads}")
    print()

    resultats = []

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {
            pool.submit(telecharger, e, session, dossier, args.retries, args.timeout): e
            for e in entrees
        }
        for future in as_completed(futures):
            resultats.append(future.result())

    # ── Résumé ───────────────────────────────────────────────────────────────
    ok      = sum(1 for r in resultats if r["statut"] in ("ok", "existe"))
    echecs  = sum(1 for r in resultats if r["statut"] == "echec")
    hash_ko = sum(1 for r in resultats if r["statut"] == "hash_erreur")

    print()
    print(gras("─── RÉSUMÉ " + "─" * 54))
    print(f"  Reussis  : {vert(str(ok))}")
    if echecs:
        print(f"  Echecs   : {rouge(str(echecs))}")
    if hash_ko:
        print(f"  Hash KO  : {rouge(str(hash_ko))}")
    print()

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["URL", "Nom fichier", "Statut", "Taille", "Erreur"])
            for r in resultats:
                w.writerow([
                    r["url"], r.get("nom", ""), r["statut"],
                    r.get("taille", ""), r.get("erreur", ""),
                ])
        print(vert(f"Rapport CSV : {args.csv}"))


if __name__ == "__main__":
    main()
