#!/usr/bin/env python3
"""
cdp_scraper.py
Scraper pour cahier-de-prepa.fr — connexion depuis le terminal,
téléchargement automatique de tous les documents d'une classe.

Nécessite vos identifiants cahier-de-prepa (email + mot de passe).
Vos fichiers sont téléchargés dans le dossier de sortie, organisés
par section telle qu'elles apparaissent sur la page de votre classe.

Usage :
    python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe
    python cdp_scraper.py --url https://... --login email@example.com
    python cdp_scraper.py --url https://... --simulation
    python cdp_scraper.py --url https://... --liste urls.txt
"""

import os
import re
import sys
import time
import getpass
import hashlib
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

try:
    import requests
except ImportError:
    print("Module manquant. Installez-le avec : pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False
    # Fallback minimal avec re si bs4 absent
    print("[!] beautifulsoup4 non installe — parsing degrade.")
    print("    Installez avec : pip install beautifulsoup4")

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

# ─── Formatage ────────────────────────────────────────────────────────────────

def fmt_taille(octets: int) -> str:
    for unite in ["o", "Ko", "Mo", "Go"]:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} To"

def nom_fichier_sur(chemin: str) -> str:
    """Retourne un nom de fichier sûr (sans caractères interdits)."""
    nom = re.sub(r'[\\/*?:"<>|]', "_", chemin)
    return nom.strip(". ")[:200] or "document"

# ─── Connexion à cahier-de-prepa ─────────────────────────────────────────────

def creer_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    return session


def connexion(session: requests.Session, url_classe: str,
              login: str, mdp: str) -> bool:
    """
    Tente de se connecter à cahier-de-prepa.
    Essaie plusieurs endpoints possibles selon la structure du site.
    Retourne True si la connexion a réussi.
    """
    base = url_classe.rstrip("/")

    # Endpoints possibles pour la connexion
    endpoints = [
        f"{base}/connexion",
        base,
        "https://cahier-de-prepa.fr/connexion",
    ]

    # Champs du formulaire trouvés dans le code source
    payload = {
        "login": login,
        "mdp":   mdp,
    }

    for endpoint in endpoints:
        try:
            # Récupérer la page de connexion pour vérifier sa structure
            resp_get = session.get(endpoint, timeout=10)
            if resp_get.status_code != 200:
                continue

            # Tenter la connexion en POST
            resp = session.post(endpoint, data=payload, timeout=10, allow_redirects=True)

            # Vérifier si la connexion a réussi :
            # — On est redirigé vers la classe (pas vers la page de connexion)
            # — Ou la réponse ne contient plus le formulaire de login
            contenu = resp.text.lower()
            echec = (
                'type="password"' in contenu or
                'name="mdp"' in contenu or
                "identifiants incorrects" in contenu or
                "mot de passe incorrect" in contenu or
                "connexion" in resp.url.lower() and resp.url == endpoint
            )
            if not echec:
                # Vérifier qu'on peut accéder à la classe
                resp_classe = session.get(base, timeout=10)
                if resp_classe.status_code == 200 and 'name="mdp"' not in resp_classe.text.lower():
                    return True

        except requests.RequestException:
            continue

    return False


def sauvegarder_cookies(session: requests.Session, chemin: Path):
    """Sauvegarde les cookies de session dans un fichier pour telechargeur_batch.py."""
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("# Cookies de session cahier-de-prepa\n")
        f.write("# Utilisable avec : python telechargeur_batch.py ... --cookie-fichier {}\n\n".format(chemin))
        for cookie in session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")
    print(vert(f"Cookies sauvegardés : {chemin}"))

# ─── Scraping des documents ───────────────────────────────────────────────────

PATTERN_DOWNLOAD = re.compile(r"download\?id=(\d+)", re.IGNORECASE)
PATTERN_LIEN_INTERNE = re.compile(r"^(?!http|mailto|#|javascript)", re.IGNORECASE)


def extraire_liens_download(html: str, url_base: str) -> list[dict]:
    """
    Extrait tous les liens de téléchargement de la page.
    Retourne une liste de {"url": str, "nom": str, "section": str}.
    """
    documents = []

    if BS4_OK:
        soup = BeautifulSoup(html, "html.parser")

        # Chercher tous les liens contenant download?id=
        for tag in soup.find_all("a", href=PATTERN_DOWNLOAD):
            href = tag.get("href", "")
            url_doc = urljoin(url_base, href)
            nom = (tag.get_text(strip=True) or
                   href.split("id=")[-1] or
                   "document")

            # Remonter dans le DOM pour trouver la section
            section = ""
            parent = tag.parent
            for _ in range(6):
                if parent is None:
                    break
                titre = parent.find(re.compile(r"^h[1-4]$"))
                if titre:
                    section = titre.get_text(strip=True)
                    break
                parent = parent.parent

            documents.append({
                "url":     url_doc,
                "nom":     nom,
                "section": section,
                "id":      PATTERN_DOWNLOAD.search(href).group(1),
            })
    else:
        # Fallback regex si bs4 absent
        for m in PATTERN_DOWNLOAD.finditer(html):
            doc_id  = m.group(1)
            url_doc = urljoin(url_base, f"download?id={doc_id}")
            documents.append({
                "url":     url_doc,
                "nom":     f"document_{doc_id}",
                "section": "",
                "id":      doc_id,
            })

    return documents


def extraire_liens_internes(html: str, url_base: str) -> list[str]:
    """
    Extrait les liens internes à la même classe (pour explorer les sous-pages).
    """
    liens = []
    base_parsed = urlparse(url_base)

    if BS4_OK:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            url_abs = urljoin(url_base, href)
            parsed  = urlparse(url_abs)

            # Garder seulement les liens internes à la même classe
            if (parsed.netloc == base_parsed.netloc and
                    parsed.path.startswith(base_parsed.path) and
                    not PATTERN_DOWNLOAD.search(href) and
                    not href.startswith("#")):
                liens.append(url_abs.split("#")[0])
    else:
        for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
            href = m.group(1)
            if (not href.startswith(("http", "mailto", "#", "javascript")) and
                    not PATTERN_DOWNLOAD.search(href)):
                liens.append(urljoin(url_base, href).split("#")[0])

    return list(set(liens))


def crawler(session: requests.Session, url_classe: str,
            profondeur_max: int = 3) -> list[dict]:
    """
    Parcourt les pages de la classe pour trouver tous les documents téléchargeables.
    Retourne la liste dédupliquée des documents trouvés.
    """
    visites    = set()
    a_visiter  = [url_classe.rstrip("/") + "/"]
    documents  = {}  # {id: doc} pour dédupliquer

    profondeur = 0

    while a_visiter and profondeur <= profondeur_max:
        niveau_suivant = []

        for url in a_visiter:
            if url in visites:
                continue
            visites.add(url)

            try:
                resp = session.get(url, timeout=15)
                if resp.status_code != 200:
                    continue

                print(dim(f"  Scan : {url}"))

                # Extraire les documents de cette page
                docs_page = extraire_liens_download(resp.text, url)
                for doc in docs_page:
                    if doc["id"] not in documents:
                        documents[doc["id"]] = doc

                # Extraire les liens internes pour les pages suivantes
                if profondeur < profondeur_max:
                    liens = extraire_liens_internes(resp.text, url_classe)
                    niveau_suivant.extend(l for l in liens if l not in visites)

                time.sleep(0.2)  # Politesse envers le serveur

            except requests.RequestException as e:
                print(jaune(f"  [!] Erreur sur {url} : {e}"))

        a_visiter = list(set(niveau_suivant))
        profondeur += 1

    return list(documents.values())

# ─── Téléchargement des documents ────────────────────────────────────────────

def nom_depuis_reponse(resp: requests.Response, doc: dict) -> str:
    """Détermine le nom de fichier depuis Content-Disposition ou le nom scrapé."""
    cd = resp.headers.get("Content-Disposition", "")
    if cd:
        m = re.search(r'filename\*?\s*=\s*(?:UTF-8\'\'|"?)([^";\r\n]+)', cd, re.IGNORECASE)
        if m:
            return unquote(m.group(1).strip().strip('"'))

    # Utiliser le nom extrait du HTML
    nom = doc.get("nom", f"document_{doc['id']}")

    # Ajouter une extension si absente
    ctype = resp.headers.get("Content-Type", "")
    ext_map = {
        "application/pdf":  ".pdf",
        "image/jpeg":       ".jpg",
        "image/png":        ".png",
        "application/zip":  ".zip",
        "text/plain":       ".txt",
    }
    if "." not in nom:
        for mime, ext in ext_map.items():
            if mime in ctype:
                nom += ext
                break

    return nom


def telecharger_document(session: requests.Session, doc: dict,
                         dossier_base: Path, simulation: bool) -> dict:
    """Télécharge un document et le range dans son dossier de section."""
    # Créer le sous-dossier de section
    section = doc.get("section", "")
    if section:
        dossier_dest = dossier_base / nom_fichier_sur(section)
    else:
        dossier_dest = dossier_base

    if not simulation:
        dossier_dest.mkdir(parents=True, exist_ok=True)

    try:
        resp = session.get(doc["url"], timeout=30, stream=True)
        resp.raise_for_status()

        nom = nom_fichier_sur(nom_depuis_reponse(resp, doc))
        chemin = dossier_dest / nom

        if simulation:
            taille = int(resp.headers.get("Content-Length", 0))
            print(f"  [SIM]  {section + '/' if section else ''}{nom}  "
                  f"({fmt_taille(taille) if taille else '?'})")
            return {"url": doc["url"], "nom": nom, "section": section, "statut": "simulation"}

        if chemin.exists():
            print(dim(f"  [EXISTE]  {nom}"))
            return {"url": doc["url"], "nom": nom, "section": section, "statut": "existe"}

        taille = 0
        with open(chemin, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    taille += len(chunk)

        print(vert(f"  [OK]  {section + '/' if section else ''}{nom}  ({fmt_taille(taille)})"))
        return {"url": doc["url"], "nom": nom, "section": section,
                "statut": "ok", "taille": taille}

    except requests.RequestException as e:
        print(rouge(f"  [ERR]  {doc['url']}  -> {e}"))
        return {"url": doc["url"], "nom": "", "section": section,
                "statut": "echec", "erreur": str(e)}

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scraper pour cahier-de-prepa.fr — login terminal + telechargement automatique.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  # Télécharger tous les docs de votre classe (login interactif)
  python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe

  # Passer les identifiants en argument
  python cdp_scraper.py --url https://... --login email@lycee.fr --mdp monmotdepasse

  # Voir ce qui serait téléchargé sans rien télécharger
  python cdp_scraper.py --url https://... --simulation

  # Générer une liste d'URLs pour telechargeur_batch.py
  python cdp_scraper.py --url https://... --liste urls_cours.txt

  # Sauvegarder les cookies de session (pour les réutiliser)
  python cdp_scraper.py --url https://... --cookie-sortie session.txt
        """
    )
    parser.add_argument("--url", required=True, metavar="URL_CLASSE",
                        help="URL de votre classe (ex: https://cahier-de-prepa.fr/ma-classe)")
    parser.add_argument("--login", metavar="EMAIL",
                        help="Adresse email (demandée interactivement si absente)")
    parser.add_argument("--mdp", metavar="MOT_DE_PASSE",
                        help="Mot de passe (demandé interactivement si absent)")
    parser.add_argument("-s", "--sortie", default="cours_cdp", metavar="DOSSIER",
                        help="Dossier de destination (défaut : cours_cdp/)")
    parser.add_argument("--liste", metavar="FICHIER",
                        help="Exporter la liste des URLs au lieu de télécharger\n"
                             "(compatible avec telechargeur_batch.py)")
    parser.add_argument("--simulation", action="store_true",
                        help="Afficher ce qui serait téléchargé sans rien télécharger")
    parser.add_argument("--profondeur", type=int, default=3, metavar="N",
                        help="Profondeur de crawl des sous-pages (défaut : 3)")
    parser.add_argument("--cookie-sortie", metavar="FICHIER",
                        help="Sauvegarder les cookies de session dans un fichier\n"
                             "(réutilisable avec telechargeur_batch.py --cookie-fichier)")
    return parser.parse_args()


def main():
    args = parse_args()

    url_classe = args.url.rstrip("/")

    # ── Identifiants ─────────────────────────────────────────────────────────
    login = args.login or input("Email cahier-de-prepa : ").strip()
    mdp   = args.mdp   or getpass.getpass("Mot de passe : ")

    if not login or not mdp:
        print(rouge("Identifiants manquants."))
        sys.exit(1)

    # ── Connexion ─────────────────────────────────────────────────────────────
    print(f"\nConnexion à : {url_classe}")
    session = creer_session()

    if not connexion(session, url_classe, login, mdp):
        print(rouge("Connexion échouée. Vérifiez l'URL, l'email et le mot de passe."))
        print(jaune("Conseil : assurez-vous que l'URL pointe sur votre classe,"))
        print(jaune("ex : https://cahier-de-prepa.fr/mp2-monlycee"))
        sys.exit(1)

    print(vert("Connexion réussie."))

    if args.cookie_sortie:
        sauvegarder_cookies(session, Path(args.cookie_sortie))

    # ── Crawl ─────────────────────────────────────────────────────────────────
    print(f"\nRecherche des documents (profondeur {args.profondeur})...")
    documents = crawler(session, url_classe, args.profondeur)

    if not documents:
        print(jaune("\nAucun document téléchargeable trouvé."))
        print(jaune("Vérifiez que l'URL est celle de votre classe et que vous y avez accès."))
        sys.exit(0)

    print(f"\n{len(documents)} document(s) trouvé(s).\n")

    # ── Export liste uniquement ───────────────────────────────────────────────
    if args.liste:
        with open(args.liste, "w", encoding="utf-8") as f:
            f.write("# URLs de documents cahier-de-prepa\n")
            f.write(f"# Classe : {url_classe}\n")
            f.write("# Utilisable avec : python telechargeur_batch.py {} --cookie-fichier cookies.txt\n\n".format(args.liste))
            for doc in documents:
                section = doc.get("section", "")
                nom     = doc.get("nom", "")
                commentaire = f"  # {section} / {nom}" if section or nom else ""
                f.write(f"{doc['url']}{commentaire}\n")
        print(vert(f"Liste exportée : {args.liste}"))
        print(f"  Utilisez : python telechargeur_batch.py {args.liste} --cookie-fichier cookies.txt")
        sys.exit(0)

    # ── Téléchargement ────────────────────────────────────────────────────────
    dossier = Path(args.sortie)
    if not args.simulation:
        dossier.mkdir(parents=True, exist_ok=True)
        print(f"Dossier de destination : {dossier.resolve()}\n")

    resultats = []
    for doc in documents:
        res = telecharger_document(session, doc, dossier, simulation=args.simulation)
        resultats.append(res)

    # ── Résumé ────────────────────────────────────────────────────────────────
    ok     = sum(1 for r in resultats if r["statut"] == "ok")
    existe = sum(1 for r in resultats if r["statut"] == "existe")
    echecs = sum(1 for r in resultats if r["statut"] == "echec")

    print()
    print(gras("─── RÉSUMÉ " + "─" * 54))
    if args.simulation:
        print(f"  Documents à télécharger : {len(documents)}")
    else:
        print(f"  Téléchargés  : {vert(str(ok))}")
        if existe:
            print(f"  Déjà présents: {dim(str(existe))}")
        if echecs:
            print(f"  Echecs       : {rouge(str(echecs))}")
    print()


if __name__ == "__main__":
    main()
