#!/usr/bin/env python3
"""
inventaire_dossier.py
Génère un rapport complet d'un dossier : taille par type de fichier,
fichiers les plus lourds, répartition par date, arborescence.
Export optionnel en CSV et/ou HTML autonome.

Usage :
    python inventaire_dossier.py <dossier> [options]
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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

# ─── Catégories d'extensions ─────────────────────────────────────────────────

CATEGORIES = {
    "PDF":            {".pdf"},
    "Texte":          {".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".tex", ".rst", ".pages", ".wpd"},
    "Tableurs":       {".xls", ".xlsx", ".ods", ".csv", ".tsv", ".numbers", ".xlsm"},
    "Présentations":  {".ppt", ".pptx", ".odp", ".key"},
    "Images":         {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
                       ".heic", ".heif", ".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".svg"},
    "Audio":          {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".aiff"},
    "Vidéo":          {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"},
    "Archives":       {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".iso", ".dmg"},
    "Exécutables":    {".exe", ".msi", ".dmg", ".deb", ".rpm", ".apk", ".sh", ".bat", ".cmd"},
    "Code":           {".py", ".js", ".ts", ".html", ".css", ".php", ".rb", ".java",
                       ".c", ".cpp", ".go", ".rs", ".sql", ".sh", ".ps1"},
    "Données":        {".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log"},
    "Polices":        {".ttf", ".otf", ".woff", ".woff2"},
}

def categorie_extension(ext: str) -> str:
    ext_lower = ext.lower()
    for cat, extensions in CATEGORIES.items():
        if ext_lower in extensions:
            return cat
    return "Autres"

# ─── Formatage ────────────────────────────────────────────────────────────────

def fmt_taille(octets: int) -> str:
    for unite in ["o", "Ko", "Mo", "Go", "To"]:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} Po"

def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

# ─── Scan ─────────────────────────────────────────────────────────────────────

def scanner(racine: Path, recursif: bool = True) -> list:
    """Retourne la liste de tous les fichiers avec leurs métadonnées."""
    fichiers = []
    glob_fn = racine.rglob if recursif else racine.glob
    compteur = 0

    for chemin in glob_fn("*"):
        if not chemin.is_file() or chemin.is_symlink():
            continue
        try:
            stat = chemin.stat()
            dt   = datetime.fromtimestamp(stat.st_mtime)
            fichiers.append({
                "chemin":    chemin,
                "relatif":   chemin.relative_to(racine),
                "extension": chemin.suffix.lower() if chemin.suffix else "(aucune)",
                "categorie": categorie_extension(chemin.suffix),
                "taille":    stat.st_size,
                "mtime":     stat.st_mtime,
                "annee":     dt.year,
                "mois":      dt.month,
            })
            compteur += 1
            if compteur % 200 == 0:
                print(f"   {compteur} fichiers analysés...", end="\r")
        except (PermissionError, OSError):
            pass

    return fichiers

# ─── Analyses ─────────────────────────────────────────────────────────────────

def analyser_par_type(fichiers: list) -> dict:
    par_cat = defaultdict(lambda: {"count": 0, "taille": 0})
    for f in fichiers:
        par_cat[f["categorie"]]["count"]  += 1
        par_cat[f["categorie"]]["taille"] += f["taille"]
    return dict(sorted(par_cat.items(), key=lambda x: x[1]["taille"], reverse=True))

def top_fichiers(fichiers: list, n: int) -> list:
    return sorted(fichiers, key=lambda f: f["taille"], reverse=True)[:n]

def repartition_par_date(fichiers: list) -> dict:
    par_annee = defaultdict(lambda: {"count": 0, "taille": 0})
    for f in fichiers:
        par_annee[f["annee"]]["count"]  += 1
        par_annee[f["annee"]]["taille"] += f["taille"]
    return dict(sorted(par_annee.items(), reverse=True))

# ─── Affichage terminal ───────────────────────────────────────────────────────

def barre(valeur: int, total: int, largeur: int = 24) -> str:
    if total == 0:
        return "[" + "." * largeur + "]"
    plein = max(0, min(largeur, int(valeur / total * largeur)))
    return "[" + "#" * plein + "." * (largeur - plein) + "]"

def afficher_rapport(racine: Path, fichiers: list, top: int, silencieux: bool):
    total_taille  = sum(f["taille"] for f in fichiers)
    total_count   = len(fichiers)

    print()
    print(gras("=" * 65))
    print(gras(f"  INVENTAIRE : {racine.name}"))
    print(gras("=" * 65))
    print(f"  Chemin      : {racine}")
    print(f"  Fichiers    : {gras(str(total_count))}")
    print(f"  Taille tot. : {gras(fmt_taille(total_taille))}")
    if fichiers:
        dates = sorted(f["mtime"] for f in fichiers)
        print(f"  Période     : {fmt_date(dates[0])}  →  {fmt_date(dates[-1])}")
    print()

    # ── Par type ──────────────────────────────────────────────────────────────
    par_type = analyser_par_type(fichiers)
    print(gras("─── PAR TYPE " + "─" * 51))
    print(f"  {'Catégorie':<18}  {'Fichiers':>7}  {'Taille':>12}  {'Part':>5}  Proportion")
    print(f"  {'─'*18}  {'─'*7}  {'─'*12}  {'─'*5}  {'─'*26}")
    for cat, data in par_type.items():
        pct = data["taille"] / total_taille * 100 if total_taille else 0
        print(f"  {cat:<18}  {data['count']:>7}  {fmt_taille(data['taille']):>12}  "
              f"{pct:>4.1f}%  {barre(data['taille'], total_taille)}")
    print()

    if silencieux:
        return

    # ── Top fichiers ──────────────────────────────────────────────────────────
    tops = top_fichiers(fichiers, top)
    print(gras(f"─── TOP {top} FICHIERS LES PLUS LOURDS " + "─" * 28))
    for i, f in enumerate(tops, 1):
        print(f"  {i:>3}.  {fmt_taille(f['taille']):>12}  {f['relatif']}")
    print()

    # ── Répartition par date ──────────────────────────────────────────────────
    par_date = repartition_par_date(fichiers)
    print(gras("─── RÉPARTITION PAR ANNÉE " + "─" * 38))
    print(f"  {'Année':>5}  {'Fichiers':>8}  {'Taille':>12}  Proportion")
    print(f"  {'─'*5}  {'─'*8}  {'─'*12}  {'─'*26}")
    for annee, data in par_date.items():
        print(f"  {annee:>5}  {data['count']:>8}  {fmt_taille(data['taille']):>12}  "
              f"{barre(data['taille'], total_taille)}")
    print()

# ─── Export CSV ───────────────────────────────────────────────────────────────

def exporter_csv(racine: Path, fichiers: list, chemin_sortie: Path, top: int):
    total_taille = sum(f["taille"] for f in fichiers)

    with open(chemin_sortie, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")

        w.writerow(["# RÉSUMÉ"])
        w.writerow(["Dossier", str(racine)])
        w.writerow(["Fichiers", len(fichiers)])
        w.writerow(["Taille totale (o)", total_taille])
        w.writerow(["Taille totale", fmt_taille(total_taille)])
        w.writerow(["Généré le", datetime.now().strftime("%Y-%m-%d %H:%M")])
        w.writerow([])

        w.writerow(["# PAR TYPE"])
        w.writerow(["Catégorie", "Fichiers", "Taille (o)", "Taille lisible", "Part (%)"])
        for cat, data in analyser_par_type(fichiers).items():
            pct = data["taille"] / total_taille * 100 if total_taille else 0
            w.writerow([cat, data["count"], data["taille"], fmt_taille(data["taille"]), f"{pct:.1f}"])
        w.writerow([])

        w.writerow([f"# TOP {top} FICHIERS"])
        w.writerow(["Rang", "Taille (o)", "Taille lisible", "Chemin"])
        for i, f in enumerate(top_fichiers(fichiers, top), 1):
            w.writerow([i, f["taille"], fmt_taille(f["taille"]), str(f["relatif"])])
        w.writerow([])

        w.writerow(["# LISTE COMPLÈTE"])
        w.writerow(["Chemin", "Extension", "Catégorie", "Taille (o)", "Taille lisible", "Date modification"])
        for f in sorted(fichiers, key=lambda x: x["taille"], reverse=True):
            w.writerow([
                str(f["relatif"]), f["extension"], f["categorie"],
                f["taille"], fmt_taille(f["taille"]), fmt_date(f["mtime"]),
            ])

    print(vert(f"Export CSV : {chemin_sortie}"))

# ─── Export HTML ──────────────────────────────────────────────────────────────

CSS = """
body{font-family:monospace;background:#1e1e1e;color:#d4d4d4;margin:2em}
h1{color:#569cd6}h2{color:#4ec9b0;border-bottom:1px solid #333;padding-bottom:4px}
table{border-collapse:collapse;width:100%;margin-bottom:2em}
th{background:#252526;color:#9cdcfe;text-align:left;padding:6px 12px}
td{padding:4px 12px;border-bottom:1px solid #2d2d2d}
.num{text-align:right;color:#b5cea8}.path{color:#ce9178;font-size:.9em}
.summary{background:#252526;padding:1em;border-radius:4px;margin-bottom:2em}
.summary span{color:#4ec9b0;font-weight:bold}
.bar-wrap{background:#2d2d2d;border-radius:2px;overflow:hidden;height:12px;min-width:80px}
.bar-fill{background:#569cd6;height:12px}
tr:hover{background:#2a2d2e}
"""

def exporter_html(racine: Path, fichiers: list, chemin_sortie: Path, top: int):
    total_taille = sum(f["taille"] for f in fichiers)
    total_count  = len(fichiers)
    par_type = analyser_par_type(fichiers)
    tops     = top_fichiers(fichiers, top)
    par_date = repartition_par_date(fichiers)

    def pct_barre(valeur, total):
        p = valeur / total * 100 if total else 0
        return (f'<td class="num">{p:.1f}%</td>'
                f'<td><div class="bar-wrap"><div class="bar-fill" style="width:{int(p*2)}px"></div></div></td>')

    rows_type = "".join(
        f'<tr><td>{cat}</td><td class="num">{d["count"]}</td>'
        f'<td class="num">{fmt_taille(d["taille"])}</td>'
        f'{pct_barre(d["taille"], total_taille)}</tr>'
        for cat, d in par_type.items()
    )
    rows_top = "".join(
        f'<tr><td class="num">{i}</td><td class="num">{fmt_taille(f["taille"])}</td>'
        f'<td class="path">{f["relatif"]}</td></tr>'
        for i, f in enumerate(tops, 1)
    )
    rows_date = "".join(
        f'<tr><td>{annee}</td><td class="num">{d["count"]}</td>'
        f'<td class="num">{fmt_taille(d["taille"])}</td>'
        f'{pct_barre(d["taille"], total_taille)}</tr>'
        for annee, d in par_date.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Inventaire — {racine.name}</title>
<style>{CSS}</style></head>
<body>
<h1>Inventaire — {racine.name}</h1>
<div class="summary">
  Dossier : <span>{racine}</span><br>
  Fichiers : <span>{total_count}</span> &nbsp;|&nbsp;
  Taille : <span>{fmt_taille(total_taille)}</span><br>
  Généré le : <span>{datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
</div>

<h2>Par type de fichier</h2>
<table><tr><th>Catégorie</th><th>Fichiers</th><th>Taille</th><th>Part</th><th>Proportion</th></tr>
{rows_type}</table>

<h2>Top {top} fichiers les plus lourds</h2>
<table><tr><th>#</th><th>Taille</th><th>Chemin</th></tr>
{rows_top}</table>

<h2>Répartition par année</h2>
<table><tr><th>Année</th><th>Fichiers</th><th>Taille</th><th>Part</th><th>Proportion</th></tr>
{rows_date}</table>
</body></html>"""

    chemin_sortie.write_text(html, encoding="utf-8")
    print(vert(f"Export HTML : {chemin_sortie}"))

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Génère un rapport complet d'un dossier.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python inventaire_dossier.py ~/Documents
  python inventaire_dossier.py . --top 30 --html rapport.html
  python inventaire_dossier.py ~/Téléchargements --csv inv.csv --html inv.html
        """
    )
    parser.add_argument("dossier", nargs="?", default=".",
                        help="Dossier à analyser (défaut : dossier courant)")
    parser.add_argument("-t", "--top", type=int, default=20, metavar="N",
                        help="Nombre de fichiers les plus lourds à afficher (défaut : 20)")
    parser.add_argument("--csv",  metavar="FICHIER", help="Exporter le rapport en CSV")
    parser.add_argument("--html", metavar="FICHIER", help="Exporter le rapport en HTML autonome")
    parser.add_argument("-q", "--silencieux", action="store_true",
                        help="Affiche uniquement le tableau par type (pas le top ni les dates)")
    parser.add_argument("--sans-recursif", action="store_true",
                        help="Analyser uniquement la racine (non récursif)")
    return parser.parse_args()


def main():
    args = parse_args()

    racine = Path(args.dossier).resolve()
    if not racine.exists() or not racine.is_dir():
        print(rouge(f"Dossier introuvable : {racine}"))
        sys.exit(1)

    print(f"\nAnalyse de : {racine}")
    fichiers = scanner(racine, recursif=not args.sans_recursif)
    print(f"   {len(fichiers)} fichier(s) trouvé(s)       ")

    if not fichiers:
        print(jaune("Aucun fichier trouvé."))
        sys.exit(0)

    afficher_rapport(racine, fichiers, args.top, args.silencieux)

    if args.csv:
        exporter_csv(racine, fichiers, Path(args.csv), args.top)
    if args.html:
        exporter_html(racine, fichiers, Path(args.html), args.top)


if __name__ == "__main__":
    main()
