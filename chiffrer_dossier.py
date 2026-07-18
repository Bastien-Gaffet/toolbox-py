#!/usr/bin/env python3
"""
chiffrer_dossier.py
Chiffre ou dechiffre un dossier entier avec un mot de passe (AES-256-GCM + PBKDF2).
Cree une archive .enc autonome et portable.

Chiffrement EN FLUX : l'archive est traitee par morceaux de 4 Mo, ecrite
directement sur le disque — pas de pic memoire, adapte aux gros dossiers.

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
import tempfile
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

MAGIC        = b"TBXENC02"   # Signature du format en flux (8 octets)
MAGIC_LEGACY = b"TBXENC01"   # Ancien format monobloc (lecture seule, retrocompat)
SEL_LEN      = 32            # Longueur du sel PBKDF2
NONCE_LEN    = 12            # Longueur du nonce de base AES-GCM
PBKDF2_ITER  = 600_000       # Iterations PBKDF2 (recommandation NIST 2023)
CHUNK        = 4 * 1024 * 1024   # Taille d'un morceau chiffre (4 Mo)

# Format .enc (TBXENC02) :
#   MAGIC(8o) | SEL(32o) | NONCE_BASE(12o) | [ morceaux... ]
#   morceau : LONGUEUR(4o, big-endian) | CHIFFRE+TAG(LONGUEUR octets)
#   - nonce du morceau i = (NONCE_BASE + i) mod 2^96
#   - donnees associees (AAD) du morceau i = i(8o) + drapeau(1o : 0x01 = dernier)
#     -> empeche la reorganisation ET la troncature (le dernier morceau est signe
#        comme tel ; toute coupure est detectee a la verification GCM).

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


def _nonce_pour(base: bytes, compteur: int) -> bytes:
    """Nonce unique du morceau : (base + compteur) mod 2^96, sur 12 octets."""
    return ((int.from_bytes(base, "big") + compteur) % (1 << 96)).to_bytes(12, "big")


def _aad(compteur: int, dernier: bool) -> bytes:
    return compteur.to_bytes(8, "big") + (b"\x01" if dernier else b"\x00")


def chiffrer_flux(mdp: str, source_claire: Path, dest_enc: Path,
                  progresse=None) -> None:
    """Chiffre `source_claire` (fichier) vers `dest_enc`, morceau par morceau."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sel   = os.urandom(SEL_LEN)
    base  = os.urandom(NONCE_LEN)
    aes   = AESGCM(deriver_cle(mdp, sel))

    total = source_claire.stat().st_size
    fait  = 0
    with open(source_claire, "rb") as fin, open(dest_enc, "wb") as fout:
        fout.write(MAGIC + sel + base)
        compteur = 0
        prec = fin.read(CHUNK)          # on lit un morceau d'avance pour marquer le dernier
        while True:
            suiv = fin.read(CHUNK)
            dernier = (suiv == b"")
            chiffre = aes.encrypt(_nonce_pour(base, compteur), prec, _aad(compteur, dernier))
            fout.write(len(chiffre).to_bytes(4, "big"))
            fout.write(chiffre)
            fait += len(prec)
            if progresse and total:
                progresse(fait, total)
            compteur += 1
            if dernier:
                break
            prec = suiv


def dechiffrer_flux(mdp: str, source_enc: Path, dest_claire: Path,
                    progresse=None) -> None:
    """Dechiffre une archive TBXENC02 vers `dest_claire` (fichier)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    total = source_enc.stat().st_size
    fait  = 0
    with open(source_enc, "rb") as fin, open(dest_claire, "wb") as fout:
        entete = fin.read(len(MAGIC) + SEL_LEN + NONCE_LEN)
        if not entete.startswith(MAGIC):
            raise ValueError("Fichier non reconnu (mauvaise signature).")
        sel  = entete[len(MAGIC):len(MAGIC) + SEL_LEN]
        base = entete[len(MAGIC) + SEL_LEN:]
        aes  = AESGCM(deriver_cle(mdp, sel))

        compteur = 0
        lb = fin.read(4)
        while lb:
            if len(lb) < 4:
                raise ValueError("Archive tronquee ou corrompue.")
            longueur = int.from_bytes(lb, "big")
            chiffre = fin.read(longueur)
            if len(chiffre) < longueur:
                raise ValueError("Archive tronquee ou corrompue.")
            suiv = fin.read(4)
            dernier = (suiv == b"")
            try:
                clair = aes.decrypt(_nonce_pour(base, compteur), chiffre, _aad(compteur, dernier))
            except Exception:
                raise ValueError("Mot de passe incorrect ou archive corrompue/tronquee.")
            fout.write(clair)
            fait += longueur
            if progresse and total:
                progresse(fait, total)
            compteur += 1
            lb = suiv


def dechiffrer_legacy(mdp: str, source_enc: Path, dest_claire: Path) -> None:
    """Dechiffre une ancienne archive monobloc TBXENC01 (chargee en memoire)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    blob = source_enc.read_bytes()
    off     = len(MAGIC_LEGACY)
    sel     = blob[off:off + SEL_LEN]
    nonce   = blob[off + SEL_LEN:off + SEL_LEN + NONCE_LEN]
    chiffre = blob[off + SEL_LEN + NONCE_LEN:]
    aes     = AESGCM(deriver_cle(mdp, sel))
    try:
        clair = aes.decrypt(nonce, chiffre, None)
    except Exception:
        raise ValueError("Mot de passe incorrect ou fichier corrompu.")
    dest_claire.write_bytes(clair)

# ─── ZIP (ecrit / lu sur disque, pas en memoire) ──────────────────────────────

def compresser_vers(source: Path, dest_zip: Path, niveau: int,
                    progresse=None) -> int:
    """Cree un ZIP sur disque a partir de `source`. Retourne le nb de fichiers."""
    compression = zipfile.ZIP_DEFLATED if niveau > 0 else zipfile.ZIP_STORED
    fichiers = [source] if source.is_file() else \
        [p for p in sorted(source.rglob("*")) if p.is_file()]
    total = len(fichiers)
    with zipfile.ZipFile(dest_zip, "w", compression=compression,
                         compresslevel=niveau if niveau > 0 else None) as zf:
        for i, chemin in enumerate(fichiers, 1):
            arc = chemin.name if source.is_file() else chemin.relative_to(source.parent)
            zf.write(chemin, arc)
            if progresse:
                progresse(i, total)
    return total


def extraire_zip(zip_path: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        noms = zf.namelist()
        zf.extractall(destination)
    return len(noms)

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: float) -> str:
    for unite in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.1f} {unite}"
        n /= 1024
    return f"{n:.1f} To"


def _barre(actuel: int, total: int, label: str):
    pct = actuel / total if total else 1.0
    largeur = 28
    rempli = int(largeur * pct)
    barre = "=" * rempli + ">" + " " * (largeur - rempli)
    print(f"\r  {label} [{barre}] {pct*100:5.1f}%", end="", flush=True)


def _tmp_sibling(ref: Path, suffixe: str) -> Path:
    """Cree un fichier temporaire sur le MEME disque que `ref` (evite les copies inter-disques)."""
    fd, nom = tempfile.mkstemp(prefix=".enc_tmp_", suffix=suffixe, dir=str(ref.parent))
    os.close(fd)
    return Path(nom)


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

    print(f"\n{gras('=== Chiffrement AES-256-GCM (en flux) ===')}")
    print(f"  Source     : {source}")
    print(f"  Archive    : {dest}")
    print(f"  Iterations : {PBKDF2_ITER:,} (PBKDF2-HMAC-SHA256)")
    print(f"  Compression: {args.compression}" +
          (dim("  (0 = stockage, ideal pour photos/videos deja compressees)")
           if args.compression == 0 else ""))

    if args.simulation:
        print(jaune("\n(simulation : aucun fichier ne sera cree)"))
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = _tmp_sibling(dest, ".zip")
    try:
        nb = compresser_vers(source, tmp_zip, args.compression,
                             progresse=lambda a, t: _barre(a, t, "Archivage  "))
        print(f"\r  Archivage    {nb} fichier(s) — {taille_lisible(tmp_zip.stat().st_size)}" + " " * 20)

        chiffrer_flux(mdp, tmp_zip, dest,
                      progresse=lambda a, t: _barre(a, t, "Chiffrement"))
        print(f"\r  Chiffrement  termine" + " " * 40)
    finally:
        tmp_zip.unlink(missing_ok=True)

    print(vert(f"\n  Archive chiffree : {dest}"))
    print(dim(f"  Taille finale : {taille_lisible(dest.stat().st_size)}"))


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

    with open(source, "rb") as f:
        signature = f.read(len(MAGIC))
    if signature not in (MAGIC, MAGIC_LEGACY):
        print(rouge("\n  Echec : fichier non reconnu (mauvaise signature)."))
        sys.exit(1)

    mdp = args.mdp or demander_mdp(confirmer=False)

    print(f"\n{gras('=== Dechiffrement AES-256-GCM ===')}")
    print(f"  Archive     : {source}")
    print(f"  Destination : {dest}")

    if args.simulation:
        print(jaune("\n(simulation : aucun fichier ne sera extrait)"))
        return

    dest.mkdir(parents=True, exist_ok=True)
    tmp_zip = _tmp_sibling(source, ".zip")
    try:
        if signature == MAGIC:
            dechiffrer_flux(mdp, source, tmp_zip,
                            progresse=lambda a, t: _barre(a, t, "Dechiffrement"))
            print(f"\r  Dechiffrement termine" + " " * 30)
        else:
            print("  Ancien format detecte (lecture en memoire)...")
            dechiffrer_legacy(mdp, source, tmp_zip)

        print("  Extraction...")
        nb = extraire_zip(tmp_zip, dest)
    except ValueError as e:
        print(rouge(f"\n  Echec : {e}"))
        sys.exit(1)
    finally:
        tmp_zip.unlink(missing_ok=True)

    print(vert(f"\n  {nb} fichier(s) restaure(s) dans : {dest}"))

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Chiffre/dechiffre un dossier entier avec AES-256-GCM + PBKDF2 (en flux).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
IMPORTANT : si le mot de passe est perdu, les donnees sont definitivement inaccessibles.
Le traitement se fait en flux (par morceaux de 4 Mo) : adapte aux gros dossiers, sans pic memoire.

Exemples :
  python chiffrer_dossier.py ./documents
  python chiffrer_dossier.py ./photos --sortie archive.enc            (compression 0 par defaut)
  python chiffrer_dossier.py ./textes --compression 6                 (utile pour du compressible)
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
    parser.add_argument("--compression", type=int, default=0, metavar="N",
                        choices=range(10),
                        help="Niveau de compression ZIP 0-9 (defaut : 0 = stockage,\n"
                             "ideal pour photos/videos ; monter a 6 pour du texte)")
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
