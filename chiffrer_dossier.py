#!/usr/bin/env python3
"""
chiffrer_dossier.py
Chiffre ou dechiffre un dossier entier avec un mot de passe (AES-256-GCM + PBKDF2).
Cree une archive .enc autonome et portable.

IMPORTANT : si le mot de passe est perdu, les donnees sont inaccessibles.

Usage :
    python chiffrer_dossier.py ./documents
    python chiffrer_dossier.py ./documents --sortie archive.enc
    python chiffrer_dossier.py --dechiffrer archive.enc --sortie ./documents_restaures
"""

import os
import sys
import io
import zipfile
import getpass
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

# ─── Constantes du format ─────────────────────────────────────────────────────

MAGIC        = b"TBXENC01"   # Signature du format (8 octets)
SEL_LEN      = 32            # Longueur du sel PBKDF2
NONCE_LEN    = 12            # Longueur du nonce AES-GCM
PBKDF2_ITER  = 600_000       # Iterations PBKDF2 (recommandation NIST 2023)

# Format du fichier .enc :
#   MAGIC (8o) | SEL (32o) | NONCE (12o) | CHIFFRE+TAG (reste)

# ─── Crypto ───────────────────────────────────────────────────────────────────

def _verifier_cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # noqa
    except ImportError:
        print(rouge("La bibliotheque 'cryptography' est requise : pip install cryptography"))
        sys.exit(1)


def deriver_cle(mdp: str, sel: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=sel, iterations=PBKDF2_ITER)
    return kdf.derive(mdp.encode("utf-8"))


def chiffrer_bytes(mdp: str, donnees: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sel   = os.urandom(SEL_LEN)
    nonce = os.urandom(NONCE_LEN)
    cle   = deriver_cle(mdp, sel)
    chiffre = AESGCM(cle).encrypt(nonce, donnees, None)
    return MAGIC + sel + nonce + chiffre


def dechiffrer_bytes(mdp: str, blob: bytes) -> bytes:
    """Leve ValueError si le mot de passe est incorrect ou le fichier corrompu."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not blob.startswith(MAGIC):
        raise ValueError("Fichier non reconnu ou corrompu (mauvaise signature).")
    off     = len(MAGIC)
    sel     = blob[off:off + SEL_LEN]
    nonce   = blob[off + SEL_LEN:off + SEL_LEN + NONCE_LEN]
    chiffre = blob[off + SEL_LEN + NONCE_LEN:]
    cle     = deriver_cle(mdp, sel)
    try:
        return AESGCM(cle).decrypt(nonce, chiffre, None)
    except Exception:
        raise ValueError("Mot de passe incorrect ou fichier corrompu.")

# ─── ZIP ──────────────────────────────────────────────────────────────────────

def compresser(source: Path, niveau: int) -> tuple[bytes, int]:
    """Compresse source dans un ZIP en memoire. Retourne (donnees, nb_fichiers)."""
    buf = io.BytesIO()
    compression = zipfile.ZIP_DEFLATED if niveau > 0 else zipfile.ZIP_STORED
    nb = 0
    with zipfile.ZipFile(buf, "w", compression=compression, compresslevel=niveau) as zf:
        if source.is_file():
            zf.write(source, source.name)
            nb = 1
        else:
            for chemin in sorted(source.rglob("*")):
                if chemin.is_file():
                    zf.write(chemin, chemin.relative_to(source.parent))
                    nb += 1
    return buf.getvalue(), nb


def extraire(zip_data: bytes, destination: Path) -> int:
    """Extrait un ZIP vers destination. Retourne le nombre de fichiers."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        noms = zf.namelist()
        zf.extractall(destination)
    return len(noms)

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for unite in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.1f} {unite}"
        n /= 1024
    return f"{n:.1f} To"


def demander_mdp(confirmer: bool) -> str:
    mdp = getpass.getpass("Mot de passe : ")
    if not mdp:
        print(rouge("Le mot de passe ne peut pas etre vide."))
        sys.exit(1)
    if confirmer:
        confirmation = getpass.getpass("Confirmer     : ")
        if mdp != confirmation:
            print(rouge("Les mots de passe ne correspondent pas."))
            sys.exit(1)
    return mdp

# ─── Actions ──────────────────────────────────────────────────────────────────

def action_chiffrer(args):
    source = Path(args.source)
    if not source.exists():
        print(rouge(f"Source introuvable : {source}"))
        sys.exit(1)

    if args.sortie:
        dest = Path(args.sortie)
    elif source.is_file():
        dest = source.with_suffix(".enc")
    else:
        dest = Path(str(source).rstrip("/\\") + ".enc")

    if dest.exists() and not args.simulation:
        rep = input(f"Le fichier {dest} existe deja. Ecraser ? [o/N] : ").strip().lower()
        if rep != "o":
            print(jaune("Annule."))
            sys.exit(0)

    mdp = args.mdp or demander_mdp(confirmer=True)

    print(f"\n{gras('=== Chiffrement AES-256-GCM ===')}")
    print(f"  Source     : {source}")
    print(f"  Archive    : {dest}")
    print(f"  Iterations : {PBKDF2_ITER:,} (PBKDF2-HMAC-SHA256)")

    if args.simulation:
        print(jaune("\n(simulation : aucun fichier ne sera cree)"))
        return

    print("\n  Compression en cours...")
    zip_data, nb = compresser(source, args.compression)
    print(dim(f"  {nb} fichier(s) — ZIP : {taille_lisible(len(zip_data))}"))

    print("  Derivation de la cle (quelques secondes)...")
    blob = chiffrer_bytes(mdp, zip_data)
    del zip_data  # liberer la memoire

    dest.write_bytes(blob)
    print(vert(f"\n  Archive chiffree : {dest}"))
    print(dim(f"  Taille finale : {taille_lisible(len(blob))}"))


def action_dechiffrer(args):
    source = Path(args.source)
    if not source.exists():
        print(rouge(f"Archive introuvable : {source}"))
        sys.exit(1)

    if args.sortie:
        dest = Path(args.sortie)
    elif source.suffix == ".enc":
        dest = source.with_suffix("")
    else:
        dest = Path(str(source) + "_dechiffre")

    mdp = args.mdp or demander_mdp(confirmer=False)

    print(f"\n{gras('=== Dechiffrement AES-256-GCM ===')}")
    print(f"  Archive     : {source}")
    print(f"  Destination : {dest}")

    if args.simulation:
        print(jaune("\n(simulation : aucun fichier ne sera extrait)"))
        return

    print("\n  Derivation de la cle (quelques secondes)...")
    blob = source.read_bytes()

    try:
        zip_data = dechiffrer_bytes(mdp, blob)
    except ValueError as e:
        print(rouge(f"\n  Echec : {e}"))
        sys.exit(1)
    del blob

    print("  Extraction...")
    nb = extraire(zip_data, dest)
    print(vert(f"\n  {nb} fichier(s) restaure(s) dans : {dest}"))

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Chiffre/dechiffre un dossier entier avec AES-256-GCM + PBKDF2.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
IMPORTANT : si le mot de passe est perdu, les donnees sont definitivement inaccessibles.
Note : la totalite du dossier est chargee en memoire — deconseille pour les tres gros volumes (>2 Go).

Exemples :
  python chiffrer_dossier.py ./documents
  python chiffrer_dossier.py ./documents --sortie archive.enc
  python chiffrer_dossier.py --dechiffrer archive.enc
  python chiffrer_dossier.py --dechiffrer archive.enc --sortie ./restaure
        """
    )
    parser.add_argument("source",
                        help="Dossier (ou fichier) a chiffrer, ou archive .enc a dechiffrer")
    parser.add_argument("-d", "--dechiffrer", action="store_true",
                        help="Mode dechiffrement (source doit etre un fichier .enc)")
    parser.add_argument("-s", "--sortie", metavar="CHEMIN",
                        help="Fichier .enc de sortie, ou dossier de destination")
    parser.add_argument("--mdp", metavar="MDP",
                        help="Mot de passe (demande de facon securisee si absent)")
    parser.add_argument("--compression", type=int, default=6, metavar="N",
                        choices=range(10),
                        help="Niveau de compression ZIP 0-9 (defaut : 6)")
    parser.add_argument("--simulation", action="store_true",
                        help="Simuler sans ecrire de fichier")
    return parser.parse_args()


def main():
    args = parse_args()
    _verifier_cryptography()
    if args.dechiffrer:
        action_dechiffrer(args)
    else:
        action_chiffrer(args)


if __name__ == "__main__":
    main()
