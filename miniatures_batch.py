#!/usr/bin/env python3
"""
miniatures_batch.py
Genere des miniatures ou redimensionne des images en masse.
Modes : ajuster (conserver ratio), remplir (rogner), etirer (exact).
Options : qualite, format de sortie, filigrane texte ou image.

Usage :
    python miniatures_batch.py ./photos --largeur 800
    python miniatures_batch.py ./photos --largeur 1280 --hauteur 720 --mode remplir
    python miniatures_batch.py ./photos --largeur 200 --hauteur 200 --sortie ./thumbs
    python miniatures_batch.py ./photos --filigrane "© 2026 Mon Nom" --qualite 90
"""

import sys
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Pillow est requis : pip install Pillow")
    sys.exit(1)

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

EXT_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for u in ("o", "Ko", "Mo"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} Go"

# ─── Redimensionnement ────────────────────────────────────────────────────────

def redimensionner(img: Image.Image, largeur: int | None, hauteur: int | None,
                   mode: str) -> Image.Image:
    """Redimensionne selon le mode : ajuster / remplir / etirer."""
    w_orig, h_orig = img.size
    w_cible = largeur or w_orig
    h_cible = hauteur or h_orig

    if mode == "etirer":
        return img.resize((w_cible, h_cible), Image.LANCZOS)

    if mode == "ajuster":
        img_copy = img.copy()
        img_copy.thumbnail((w_cible, h_cible), Image.LANCZOS)
        return img_copy

    if mode == "remplir":
        # Calculer le ratio pour couvrir entierement les dimensions cibles
        ratio = max(w_cible / w_orig, h_cible / h_orig)
        w_new = round(w_orig * ratio)
        h_new = round(h_orig * ratio)
        img = img.resize((w_new, h_new), Image.LANCZOS)
        # Rogner au centre
        left = (w_new - w_cible) // 2
        top  = (h_new - h_cible) // 2
        return img.crop((left, top, left + w_cible, top + h_cible))

    return img

# ─── Filigrane texte ──────────────────────────────────────────────────────────

def appliquer_filigrane_texte(img: Image.Image, texte: str,
                               position: str, opacite: int) -> Image.Image:
    """Ajoute un filigrane texte semi-transparent."""
    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGBA")

    # Creer un calque transparent
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw   = ImageDraw.Draw(calque)

    # Essayer de charger une police systeme, sinon utiliser la police par defaut
    taille_police = max(12, img.size[0] // 30)
    police = None
    for nom_police in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            police = ImageFont.truetype(nom_police, taille_police)
            break
        except (OSError, IOError):
            continue
    if police is None:
        police = ImageFont.load_default()

    # Calculer la taille du texte
    bbox = draw.textbbox((0, 0), texte, font=police)
    w_txt = bbox[2] - bbox[0]
    h_txt = bbox[3] - bbox[1]
    marge = 10

    pos_map = {
        "bas-droite":  (img.size[0] - w_txt - marge, img.size[1] - h_txt - marge),
        "bas-gauche":  (marge, img.size[1] - h_txt - marge),
        "haut-droite": (img.size[0] - w_txt - marge, marge),
        "haut-gauche": (marge, marge),
        "centre":      ((img.size[0] - w_txt) // 2, (img.size[1] - h_txt) // 2),
    }
    x, y = pos_map.get(position, pos_map["bas-droite"])

    # Ombre portee pour lisibilite
    alpha = int(opacite * 2.55)
    draw.text((x + 1, y + 1), texte, font=police, fill=(0, 0, 0, alpha // 2))
    draw.text((x, y), texte, font=police, fill=(255, 255, 255, alpha))

    if img.mode == "RGBA":
        return Image.alpha_composite(img, calque)
    return Image.alpha_composite(img.convert("RGBA"), calque).convert("RGB")


def appliquer_filigrane_image(img: Image.Image, filigrane_img: Image.Image,
                               position: str, opacite: int) -> Image.Image:
    """Composite un filigrane image semi-transparent."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    fw = filigrane_img.convert("RGBA")

    # Appliquer l'opacite
    r, g, b, a = fw.split()
    a = a.point(lambda x: int(x * opacite / 100))
    fw = Image.merge("RGBA", (r, g, b, a))

    marge = 10
    pos_map = {
        "bas-droite":  (img.size[0] - fw.size[0] - marge, img.size[1] - fw.size[1] - marge),
        "bas-gauche":  (marge, img.size[1] - fw.size[1] - marge),
        "haut-droite": (img.size[0] - fw.size[0] - marge, marge),
        "haut-gauche": (marge, marge),
        "centre":      ((img.size[0] - fw.size[0]) // 2, (img.size[1] - fw.size[1]) // 2),
    }
    x, y = pos_map.get(position, pos_map["bas-droite"])

    resultat = img.copy()
    resultat.paste(fw, (x, y), fw)
    return resultat

# ─── Traitement d'une image ───────────────────────────────────────────────────

def traiter_image(chemin: Path, args, dossier_sortie: Path | None,
                  fw_img: Image.Image | None) -> bool:
    try:
        img = Image.open(chemin)
        # Convertir RGBA -> RGB si sortie JPEG
        format_sortie = (args.format or chemin.suffix.lstrip(".")).upper()
        if format_sortie in ("JPG", "JPEG") and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if args.largeur or args.hauteur:
            img = redimensionner(img, args.largeur, args.hauteur, args.mode)

        if args.filigrane:
            img = appliquer_filigrane_texte(img, args.filigrane,
                                             args.position, args.opacite)
        elif fw_img:
            img = appliquer_filigrane_image(img, fw_img, args.position, args.opacite)

        # Determiner le chemin de sortie
        ext_sortie = "." + (args.format or chemin.suffix.lstrip(".")).lower()
        if ext_sortie == ".jpg":
            ext_sortie = ".jpeg"

        if dossier_sortie:
            chemin_sortie = dossier_sortie / (chemin.stem + args.suffixe + ext_sortie)
        elif args.suffixe or args.format:
            chemin_sortie = chemin.with_stem(chemin.stem + args.suffixe).with_suffix(ext_sortie)
        else:
            chemin_sortie = chemin.with_stem(chemin.stem + "_mini").with_suffix(ext_sortie)

        # Parametres de sauvegarde
        params: dict = {}
        if format_sortie in ("JPG", "JPEG", "JPEG"):
            params["quality"] = args.qualite
            params["optimize"] = True
        elif format_sortie == "PNG":
            params["optimize"] = True
        elif format_sortie == "WEBP":
            params["quality"] = args.qualite

        if img.mode == "RGBA" and format_sortie in ("JPEG", "JPG"):
            img = img.convert("RGB")

        img.save(chemin_sortie, **params)
        taille_out = chemin_sortie.stat().st_size
        print(f"  {vert('OK')}  {chemin.name:<40} -> {chemin_sortie.name} ({taille_lisible(taille_out)})")
        return True

    except Exception as e:
        print(rouge(f"  ERR {chemin.name} : {e}"))
        return False

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Redimensionne ou genere des miniatures d'images en masse.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Modes de redimensionnement :
  ajuster   Respecte le ratio, l'image tient dans les dimensions (defaut)
  remplir   Remplit exactement les dimensions en rognant les bords
  etirer    Etire aux dimensions exactes (peut deformer)

Exemples :
  python miniatures_batch.py ./photos --largeur 800
  python miniatures_batch.py ./photos --largeur 1920 --hauteur 1080 --mode remplir
  python miniatures_batch.py ./photos --largeur 200 --sortie ./thumbs --format webp
  python miniatures_batch.py ./photos --filigrane "© 2026" --position bas-droite --opacite 70
  python miniatures_batch.py ./photos --filigrane-image logo.png --opacite 50
        """
    )
    parser.add_argument("source", help="Dossier ou fichier image source")

    grp_dim = parser.add_argument_group("Dimensions")
    grp_dim.add_argument("--largeur", type=int, metavar="W",
                         help="Largeur cible en pixels")
    grp_dim.add_argument("--hauteur", type=int, metavar="H",
                         help="Hauteur cible en pixels")
    grp_dim.add_argument("--mode", choices=["ajuster", "remplir", "etirer"],
                         default="ajuster",
                         help="Mode de redimensionnement (defaut : ajuster)")

    grp_fmt = parser.add_argument_group("Format de sortie")
    grp_fmt.add_argument("--format", choices=["jpg", "jpeg", "png", "webp", "bmp"],
                         help="Format de sortie (defaut : meme format que l'entree)")
    grp_fmt.add_argument("--qualite", type=int, default=85, metavar="N",
                         help="Qualite JPEG/WebP 1-95 (defaut : 85)")
    grp_fmt.add_argument("--suffixe", default="",
                         help="Suffixe a ajouter au nom du fichier de sortie")
    grp_fmt.add_argument("--sortie", metavar="DIR",
                         help="Dossier de destination (defaut : meme que la source)")

    grp_fw = parser.add_argument_group("Filigrane")
    grp_fw.add_argument("--filigrane", metavar="TEXTE",
                        help="Texte du filigrane")
    grp_fw.add_argument("--filigrane-image", metavar="FICHIER",
                        help="Image du filigrane (PNG avec transparence recommande)")
    grp_fw.add_argument("--position",
                        choices=["bas-droite", "bas-gauche", "haut-droite",
                                 "haut-gauche", "centre"],
                        default="bas-droite",
                        help="Position du filigrane (defaut : bas-droite)")
    grp_fw.add_argument("--opacite", type=int, default=60, metavar="N",
                        help="Opacite du filigrane 0-100 (defaut : 60)")

    grp_ctrl = parser.add_argument_group("Controle")
    grp_ctrl.add_argument("-r", "--recursif", action="store_true",
                          help="Traiter les sous-dossiers recursivement")
    grp_ctrl.add_argument("-s", "--simulation", action="store_true",
                          help="Lister les fichiers sans traiter")

    return parser.parse_args()


def main():
    args = parse_args()
    source = Path(args.source)

    if not source.exists():
        print(rouge(f"Source introuvable : {source}"))
        sys.exit(1)

    # Charger le filigrane image si specifie
    fw_img = None
    if args.filigrane_image:
        try:
            fw_img = Image.open(args.filigrane_image)
        except Exception as e:
            print(rouge(f"Filigrane image invalide : {e}"))
            sys.exit(1)

    # Collecter les fichiers
    if source.is_file():
        fichiers = [source] if source.suffix.lower() in EXT_IMAGES else []
    else:
        motif = "**/*" if args.recursif else "*"
        fichiers = [p for p in source.glob(motif)
                    if p.is_file() and p.suffix.lower() in EXT_IMAGES]
    fichiers.sort()

    if not fichiers:
        print(jaune("Aucune image trouvee."))
        sys.exit(0)

    # Dossier de sortie
    dossier_sortie = None
    if args.sortie:
        dossier_sortie = Path(args.sortie)
        if not args.simulation:
            dossier_sortie.mkdir(parents=True, exist_ok=True)

    print(f"\n{gras('=== Traitement en masse ===')}  {len(fichiers)} image(s)")
    if args.largeur or args.hauteur:
        dim = f"{args.largeur or '?'}x{args.hauteur or '?'}  mode={args.mode}"
        print(f"  Dimensions : {dim}")
    if args.filigrane:
        print(f"  Filigrane  : \"{args.filigrane}\"  opacite={args.opacite}%")
    if args.simulation:
        print(jaune("  (simulation : aucun fichier ne sera cree)\n"))
        for f in fichiers:
            print(dim(f"  {f.name}"))
        return
    print()

    ok = ko = 0
    for f in fichiers:
        if traiter_image(f, args, dossier_sortie, fw_img):
            ok += 1
        else:
            ko += 1

    print(f"\n  {vert(str(ok))} image(s) traitee(s)"
          + (f"  /  {rouge(str(ko))} echec(s)" if ko else ""))


if __name__ == "__main__":
    main()
