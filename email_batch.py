#!/usr/bin/env python3
"""
email_batch.py
Envoie des emails personnalises en masse depuis un fichier CSV.
Supporte les templates HTML, les pieces jointes et un mode test.

CSV attendu : colonnes "email" (obligatoire) + variables pour le template.
Template : fichier texte/HTML avec {{variable}} pour la substitution.

Usage :
    python email_batch.py contacts.csv --sujet "Bonjour {{nom}}" --template corps.html
    python email_batch.py contacts.csv --sujet "Réunion" --template corps.txt --test
    python email_batch.py contacts.csv --sujet "Info" --corps "Bonjour {{nom}} !" --pj doc.pdf
"""

import os
import sys
import csv
import re
import time
import getpass
import smtplib
import argparse
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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

# ─── Template ─────────────────────────────────────────────────────────────────

def rendre_template(template: str, variables: dict) -> str:
    """Remplace {{variable}} par les valeurs du dictionnaire."""
    def remplacer(m):
        cle = m.group(1).strip()
        return str(variables.get(cle, m.group(0)))  # Laisser intact si absent
    return re.sub(r"\{\{(.+?)\}\}", remplacer, template)


def est_html(contenu: str) -> bool:
    return bool(re.search(r"<(?:html|body|p|br|div|span|h[1-6]|table)\b", contenu, re.IGNORECASE))

# ─── Lecture CSV ──────────────────────────────────────────────────────────────

def lire_csv(chemin: Path, separateur: str) -> list[dict]:
    destinataires = []
    try:
        with open(chemin, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=separateur)
            if "email" not in (reader.fieldnames or []):
                print(rouge(f"Colonne 'email' manquante dans {chemin}."))
                print(dim(f"  Colonnes trouvees : {reader.fieldnames}"))
                sys.exit(1)
            for ligne in reader:
                email = ligne.get("email", "").strip()
                if email and "@" in email:
                    destinataires.append(dict(ligne))
                else:
                    print(jaune(f"  Ignore (email invalide) : {ligne}"))
    except OSError as e:
        print(rouge(f"Erreur lecture CSV : {e}"))
        sys.exit(1)
    return destinataires

# ─── Construction du message ──────────────────────────────────────────────────

def construire_message(expediteur: str, destinataire: dict,
                        sujet_template: str, corps_template: str,
                        pieces_jointes: list[Path]) -> MIMEMultipart:
    variables = dict(destinataire)
    sujet = rendre_template(sujet_template, variables)
    corps = rendre_template(corps_template, variables)

    msg = MIMEMultipart("alternative" if est_html(corps) else "mixed")
    msg["From"]    = expediteur
    msg["To"]      = destinataire["email"]
    msg["Subject"] = sujet

    if est_html(corps):
        msg.attach(MIMEText(corps, "html", "utf-8"))
    else:
        msg.attach(MIMEText(corps, "plain", "utf-8"))

    for pj in pieces_jointes:
        try:
            with open(pj, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition", "attachment", filename=pj.name
            )
            msg.attach(attachment)
        except OSError as e:
            print(jaune(f"  PJ ignoree ({pj.name}) : {e}"))

    return msg

# ─── Mode test ────────────────────────────────────────────────────────────────

def afficher_apercu(msg: MIMEMultipart, variables: dict):
    print(f"  {cyan('To')}      : {msg['To']}")
    print(f"  {cyan('Sujet')}   : {msg['Subject']}")
    corps = ""
    for part in msg.walk():
        if part.get_content_type() in ("text/plain", "text/html"):
            corps = part.get_payload(decode=True).decode("utf-8", errors="replace")
            break
    lignes = corps.strip().splitlines()
    apercu = "\n    ".join(lignes[:5])
    if len(lignes) > 5:
        apercu += f"\n    ... ({len(lignes) - 5} lignes de plus)"
    print(f"  {cyan('Corps')}   :\n    {apercu}")
    print()

# ─── Envoi ────────────────────────────────────────────────────────────────────

def envoyer(smtp: smtplib.SMTP, msg: MIMEMultipart) -> bool:
    try:
        smtp.send_message(msg)
        return True
    except Exception as e:
        print(rouge(f"  ERR {msg['To']} : {e}"))
        return False


def creer_connexion_smtp(host: str, port: int, login: str, mdp: str) -> smtplib.SMTP:
    try:
        if port == 465:
            smtp = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            smtp = smtplib.SMTP(host, port, timeout=15)
            smtp.ehlo()
            smtp.starttls()
        smtp.login(login, mdp)
        return smtp
    except smtplib.SMTPAuthenticationError:
        print(rouge("Authentification SMTP echouee. Verifiez votre login/mot de passe."))
        print(dim("  Gmail : utilisez un 'Mot de passe d'application' (2FA requis)."))
        sys.exit(1)
    except Exception as e:
        print(rouge(f"Connexion SMTP echouee ({host}:{port}) : {e}"))
        sys.exit(1)

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Envoi d'emails personalises en masse depuis un CSV.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Format CSV (separateur ; ou ,) :
  email;nom;prenom;variable1;variable2
  alice@example.com;Alice;Dupont;valeur1;valeur2

Template (fichier .txt ou .html) :
  Bonjour {{nom}} {{prenom}},
  Votre code est : {{variable1}}

Serveurs SMTP courants :
  Gmail   : smtp.gmail.com:587  (mot de passe d'application requis)
  Outlook : smtp.office365.com:587
  Mailtrap (test) : sandbox.smtp.mailtrap.io:587

Variables d'environnement : SMTP_HOST, SMTP_PORT, SMTP_LOGIN, SMTP_MDP, SMTP_FROM

Exemples :
  python email_batch.py contacts.csv --sujet "Bonjour {{nom}}" --template corps.html --test
  python email_batch.py contacts.csv --sujet "Info" --corps "Salut {{nom}} !" --smtp smtp.gmail.com --port 587
        """
    )
    parser.add_argument("csv", help="Fichier CSV des destinataires")
    parser.add_argument("--sujet", required=True,
                        help="Sujet de l'email (supporte {{variable}})")

    grp_corps = parser.add_mutually_exclusive_group(required=True)
    grp_corps.add_argument("--template", metavar="FICHIER",
                           help="Fichier template (.txt ou .html)")
    grp_corps.add_argument("--corps", metavar="TEXTE",
                           help="Corps du message inline (texte court)")

    parser.add_argument("--pj", nargs="+", metavar="FICHIER",
                        help="Piece(s) jointe(s) globale(s)")
    parser.add_argument("--sep", default=";", metavar="SEP",
                        help="Separateur CSV (defaut : ;)")
    parser.add_argument("--de", metavar="EMAIL",
                        help="Adresse expediteur (defaut : login SMTP)")

    grp_smtp = parser.add_argument_group("Configuration SMTP")
    grp_smtp.add_argument("--smtp", default=os.environ.get("SMTP_HOST", ""),
                          metavar="HOST", help="Serveur SMTP")
    grp_smtp.add_argument("--port", type=int,
                          default=int(os.environ.get("SMTP_PORT", "587")),
                          metavar="PORT", help="Port SMTP (defaut : 587)")
    grp_smtp.add_argument("--login", default=os.environ.get("SMTP_LOGIN", ""),
                          metavar="LOGIN", help="Login SMTP")
    grp_smtp.add_argument("--mdp", default=os.environ.get("SMTP_MDP", ""),
                          metavar="MDP",
                          help="Mot de passe SMTP (demande si absent)")

    grp_ctrl = parser.add_argument_group("Controle")
    grp_ctrl.add_argument("--test", action="store_true",
                           help="Afficher un apercu sans envoyer")
    grp_ctrl.add_argument("--delai", type=float, default=1.0, metavar="S",
                           help="Delai entre chaque envoi en secondes (defaut : 1)")
    grp_ctrl.add_argument("--limite", type=int, metavar="N",
                           help="Envoyer seulement les N premiers emails")

    return parser.parse_args()


def main():
    args = parse_args()

    # Charger le template
    if args.template:
        template_path = Path(args.template)
        if not template_path.exists():
            print(rouge(f"Template introuvable : {template_path}"))
            sys.exit(1)
        corps_template = template_path.read_text(encoding="utf-8")
    else:
        corps_template = args.corps

    # Lire le CSV
    destinataires = lire_csv(Path(args.csv), args.sep)
    if not destinataires:
        print(jaune("Aucun destinataire valide dans le CSV."))
        sys.exit(0)

    if args.limite:
        destinataires = destinataires[:args.limite]

    # Pieces jointes
    pieces_jointes = []
    if args.pj:
        for pj_path in args.pj:
            p = Path(pj_path)
            if p.exists():
                pieces_jointes.append(p)
            else:
                print(jaune(f"PJ introuvable : {pj_path}"))

    print(f"\n{gras('=== Email batch ===')}")
    print(f"  CSV          : {args.csv}  ({len(destinataires)} destinataire(s))")
    print(f"  Sujet        : {args.sujet}")
    if pieces_jointes:
        print(f"  PJ           : {', '.join(p.name for p in pieces_jointes)}")

    if args.test:
        print(jaune("\n  MODE TEST — apercu des 3 premiers emails :\n"))
        expediteur = args.de or args.login or "test@example.com"
        for dest in destinataires[:3]:
            msg = construire_message(expediteur, dest, args.sujet,
                                     corps_template, pieces_jointes)
            afficher_apercu(msg, dest)
        print(jaune(f"  {len(destinataires)} email(s) auraient ete envoyes."))
        return

    # Configuration SMTP
    if not args.smtp:
        print(rouge("--smtp requis (ex: smtp.gmail.com)"))
        sys.exit(1)

    mdp = args.mdp or getpass.getpass("Mot de passe SMTP : ")
    if not mdp:
        print(rouge("Mot de passe vide."))
        sys.exit(1)

    expediteur = args.de or args.login
    print(f"  Serveur      : {args.smtp}:{args.port}")
    print(f"  Expediteur   : {expediteur}")
    print(f"  Delai        : {args.delai}s entre envois\n")

    # Confirmation
    print(rouge(f"Envoyer {len(destinataires)} email(s) ? [o/N] : "), end="")
    if input().strip().lower() != "o":
        print(jaune("Annule."))
        sys.exit(0)

    smtp = creer_connexion_smtp(args.smtp, args.port, args.login, mdp)
    ok = ko = 0

    try:
        for i, dest in enumerate(destinataires):
            msg = construire_message(expediteur, dest, args.sujet,
                                     corps_template, pieces_jointes)
            if envoyer(smtp, msg):
                print(vert(f"  [{i+1}/{len(destinataires)}] {dest['email']}"))
                ok += 1
            else:
                ko += 1
            if i < len(destinataires) - 1:
                time.sleep(args.delai)
    finally:
        smtp.quit()

    print(f"\n  {vert(str(ok))} envoye(s)  /  {(rouge(str(ko)) if ko else str(ko))} echec(s)")


if __name__ == "__main__":
    main()
