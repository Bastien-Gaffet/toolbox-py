#!/usr/bin/env python3
"""
metadata_cleaner.py
Nettoie les metadonnees sensibles (EXIF, GPS, auteur, etc.) de photos, PDF et
documents Word avant de les partager.

Usage :
    python metadata_cleaner.py photo.jpg
    python metadata_cleaner.py ./dossier --recursif --simulation
    python metadata_cleaner.py rapport.pdf --forcer
    python metadata_cleaner.py ./docs --sortie ./docs_propres
"""

import os
import sys
import shutil
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

# ─── Extensions supportees ────────────────────────────────────────────────────

EXT_JPEG   = {".jpg", ".jpeg"}
EXT_IMAGES = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp"}
EXT_PDF    = {".pdf"}
EXT_WORD   = {".docx"}
EXT_TOUT   = EXT_IMAGES | EXT_PDF | EXT_WORD

# ─── Inspection ───────────────────────────────────────────────────────────────

def inspecter_image(chemin: Path) -> dict:
    meta = {}
    try:
        from PIL import Image
        import piexif

        img = Image.open(chemin)
        exif_bytes = img.info.get("exif", b"")
        if not exif_bytes:
            return meta

        try:
            exif = piexif.load(exif_bytes)
        except Exception:
            meta["exif"] = "donnees EXIF presentes (format non parseable)"
            return meta

        etiquettes = {
            piexif.ImageIFD.Make:            "Fabricant appareil",
            piexif.ImageIFD.Model:           "Modele appareil",
            piexif.ImageIFD.Software:        "Logiciel",
            piexif.ImageIFD.Artist:          "Artiste",
            piexif.ImageIFD.Copyright:       "Copyright",
            piexif.ExifIFD.DateTimeOriginal: "Date de prise de vue",
            piexif.ExifIFD.UserComment:      "Commentaire utilisateur",
        }
        for ifd_name, ifd_data in exif.items():
            if ifd_name == "GPS" and ifd_data:
                meta["GPS"] = "coordonnees GPS presentes"
            elif isinstance(ifd_data, dict):
                for tag, val in ifd_data.items():
                    if tag in etiquettes and val:
                        v = val.decode("utf-8", errors="replace").strip() if isinstance(val, bytes) else str(val)
                        v = v.strip("\x00")
                        if v:
                            meta[etiquettes[tag]] = v[:80]
    except ImportError:
        meta["erreur"] = "Pillow / piexif manquant — pip install Pillow piexif"
    except Exception as e:
        meta["erreur"] = str(e)
    return meta


CHAMPS_PDF = ["Title", "Author", "Subject", "Keywords", "Creator",
              "Producer", "CreationDate", "ModDate"]


def inspecter_pdf(chemin: Path) -> dict:
    meta = {}
    try:
        from pypdf import PdfReader
        reader = PdfReader(chemin)
        info = reader.metadata or {}
        for champ in CHAMPS_PDF:
            val = info.get(f"/{champ}", "") or info.get(champ, "")
            if val:
                meta[champ] = str(val)[:80]
    except ImportError:
        meta["erreur"] = "pypdf manquant — pip install pypdf"
    except Exception as e:
        meta["erreur"] = str(e)
    return meta


CHAMPS_DOCX_STR = [
    "author", "last_modified_by", "title", "subject",
    "keywords", "description", "category", "comments",
    "content_status", "identifier", "language", "version",
]


def inspecter_docx(chemin: Path) -> dict:
    meta = {}
    try:
        from docx import Document
        props = Document(chemin).core_properties
        for champ in CHAMPS_DOCX_STR:
            val = getattr(props, champ, None)
            if val:
                meta[champ] = str(val)[:80]
    except ImportError:
        meta["erreur"] = "python-docx manquant — pip install python-docx"
    except Exception as e:
        meta["erreur"] = str(e)
    return meta


def inspecter(chemin: Path) -> dict:
    ext = chemin.suffix.lower()
    if ext in EXT_IMAGES:
        return inspecter_image(chemin)
    if ext in EXT_PDF:
        return inspecter_pdf(chemin)
    if ext in EXT_WORD:
        return inspecter_docx(chemin)
    return {}

# ─── Nettoyage ────────────────────────────────────────────────────────────────

def nettoyer_image(chemin: Path, sortie: Path) -> bool:
    ext = chemin.suffix.lower()
    try:
        if ext in EXT_JPEG:
            import piexif
            if sortie != chemin:
                shutil.copy2(chemin, sortie)
            try:
                piexif.remove(str(sortie))
            except Exception:
                pass
        else:
            from PIL import Image
            img = Image.open(chemin)
            fmt = img.format or ext.lstrip(".").upper()
            if fmt == "JPG":
                fmt = "JPEG"
            img.save(sortie, format=fmt)
        return True
    except ImportError:
        print(rouge("  Pillow / piexif manquant"))
        return False
    except Exception as e:
        print(rouge(f"  Erreur image : {e}"))
        return False


def nettoyer_pdf(chemin: Path, sortie: Path) -> bool:
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(chemin)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata({f"/{c}": "" for c in CHAMPS_PDF})
        with open(sortie, "wb") as f:
            writer.write(f)
        return True
    except ImportError:
        print(rouge("  pypdf manquant — pip install pypdf"))
        return False
    except Exception as e:
        print(rouge(f"  Erreur PDF : {e}"))
        return False


def nettoyer_docx(chemin: Path, sortie: Path) -> bool:
    try:
        from docx import Document
        if sortie != chemin:
            shutil.copy2(chemin, sortie)
        doc = Document(sortie)
        props = doc.core_properties
        for champ in CHAMPS_DOCX_STR:
            try:
                setattr(props, champ, "")
            except (AttributeError, TypeError):
                pass
        try:
            props.revision = 1
        except (AttributeError, TypeError):
            pass
        doc.save(sortie)
        return True
    except ImportError:
        print(rouge("  python-docx manquant — pip install python-docx"))
        return False
    except Exception as e:
        print(rouge(f"  Erreur DOCX : {e}"))
        return False


def nettoyer(chemin: Path, sortie: Path) -> bool:
    ext = chemin.suffix.lower()
    if ext in EXT_IMAGES:
        return nettoyer_image(chemin, sortie)
    if ext in EXT_PDF:
        return nettoyer_pdf(chemin, sortie)
    if ext in EXT_WORD:
        return nettoyer_docx(chemin, sortie)
    return False

# ─── Traitement ───────────────────────────────────────────────────────────────

def destination(chemin: Path, forcer: bool, dossier_sortie: Path | None) -> Path:
    if forcer:
        return chemin
    if dossier_sortie:
        return dossier_sortie / chemin.name
    return chemin.with_stem(chemin.stem + "_clean")


def traiter_fichier(chemin: Path, simulation: bool, forcer: bool,
                    dossier_sortie: Path | None) -> tuple[bool, bool]:
    """Retourne (traite_sans_erreur, avait_des_metadonnees)."""
    if chemin.suffix.lower() not in EXT_TOUT:
        return False, False

    meta = inspecter(chemin)
    print(f"\n  {cyan(str(chemin.name))}")

    if "erreur" in meta:
        print(rouge(f"    [ERR] {meta['erreur']}"))
        return False, False

    if not meta:
        print(dim("    Aucune metadonnee sensible trouvee."))
        return True, False

    for cle, val in meta.items():
        print(jaune(f"    {cle:<28} {val}"))

    if simulation:
        return True, True

    dest = destination(chemin, forcer, dossier_sortie)
    ok = nettoyer(chemin, dest)
    if ok:
        label = dest.name if dest != chemin else "(en place)"
        print(vert(f"    OK -> {label}"))
    return ok, True


def collecter(cible: Path, recursif: bool) -> list[Path]:
    if cible.is_file():
        return [cible]
    motif = "**/*" if recursif else "*"
    return [p for p in cible.glob(motif)
            if p.is_file() and p.suffix.lower() in EXT_TOUT]

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Nettoie les metadonnees sensibles de fichiers avant partage.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Types de fichiers supportes : JPEG, PNG, TIFF, WEBP, BMP, PDF, DOCX

Exemples :
  python metadata_cleaner.py photo.jpg
  python metadata_cleaner.py ./dossier --recursif --simulation
  python metadata_cleaner.py rapport.pdf --forcer
  python metadata_cleaner.py ./docs --sortie ./docs_propres -r
        """
    )
    parser.add_argument("cible", help="Fichier ou dossier a nettoyer")
    parser.add_argument("-r", "--recursif", action="store_true",
                        help="Traiter les sous-dossiers recursivement")
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Afficher les metadonnees sans modifier les fichiers")
    parser.add_argument("--forcer", action="store_true",
                        help="Modifier les fichiers originaux en place (sans copie)")
    parser.add_argument("--sortie", metavar="DIR",
                        help="Dossier de destination pour les fichiers nettoyes\n"
                             "(defaut : nom_clean.ext dans le meme dossier)")
    return parser.parse_args()


def main():
    args = parse_args()
    cible = Path(args.cible)

    if not cible.exists():
        print(rouge(f"Introuvable : {cible}"))
        sys.exit(1)

    dossier_sortie = None
    if args.sortie:
        dossier_sortie = Path(args.sortie)
        dossier_sortie.mkdir(parents=True, exist_ok=True)

    fichiers = collecter(cible, args.recursif)
    if not fichiers:
        print(jaune("Aucun fichier compatible trouve (JPEG, PNG, TIFF, WEBP, PDF, DOCX)."))
        sys.exit(0)

    if args.simulation:
        mode = "SIMULATION"
    elif args.forcer:
        mode = "MODIFICATION EN PLACE"
    else:
        mode = "COPIE NETTOYEE"

    print(f"\n{gras('=== Nettoyage de metadonnees ===')}")
    print(f"Mode     : {gras(mode)}")
    print(f"Fichiers : {len(fichiers)}")
    if args.simulation:
        print(jaune("(simulation : aucun fichier ne sera modifie)"))

    ok_count = nettoyage_count = 0
    for f in fichiers:
        succes, avait_meta = traiter_fichier(f, args.simulation, args.forcer, dossier_sortie)
        if succes:
            ok_count += 1
        if avait_meta:
            nettoyage_count += 1

    print(f"\n{gras('---')}")
    print(f"  {ok_count}/{len(fichiers)} fichier(s) traite(s)")
    print(f"  {nettoyage_count} fichier(s) contenaient des metadonnees sensibles")


if __name__ == "__main__":
    main()
