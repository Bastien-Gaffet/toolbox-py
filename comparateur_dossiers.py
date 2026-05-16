#!/usr/bin/env python3
"""
comparateur_dossiers.py
Compare deux dossiers et identifie les fichiers identiques, modifiés
ou manquants dans l'un ou l'autre. Utile pour vérifier une sauvegarde.

Deux modes :
  - Précis (défaut) : comparaison par hash SHA-256 — fiable mais plus lent
  - Rapide          : comparaison par taille seule  — rapide mais moins précis

Usage :
    python comparateur_dossiers.py <dossier_a> <dossier_b> [options]
"""

import sys
import csv
import hashlib
import fnmatch
import argparse
from pathlib import Path
from datetime import datetime

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
    for unite in ["o", "Ko", "Mo", "Go", "To"]:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} Po"

def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

# ─── Hachage ─────────────────────────────────────────────────────────────────

def hash_fichier(chemin: Path, bloc: int = 65536) -> str:
    sha = hashlib.sha256()
    try:
        with open(chemin, "rb") as f:
            while True:
                data = f.read(bloc)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()
    except (IOError, OSError):
        return ""

# ─── Scan ─────────────────────────────────────────────────────────────────────

def est_exclu(relatif: Path, patterns: list) -> bool:
    """Retourne True si le chemin correspond à l'un des patterns d'exclusion."""
    for pat in patterns:
        for partie in relatif.parts:
            if fnmatch.fnmatch(partie, pat):
                return True
        if fnmatch.fnmatch(str(relatif), pat):
            return True
    return False

def scanner(racine: Path, rapide: bool, exclure: list, label: str) -> dict:
    """
    Retourne un dict {chemin_relatif: {"empreinte": str, "taille": int, "mtime": float}}.
    empreinte = hash SHA-256 (précis) ou taille en octets (rapide).
    """
    index = {}
    compteur = 0

    for chemin in sorted(racine.rglob("*")):
        if not chemin.is_file() or chemin.is_symlink():
            continue

        relatif = chemin.relative_to(racine)
        if exclure and est_exclu(relatif, exclure):
            continue

        try:
            stat = chemin.stat()
            if rapide:
                empreinte = str(stat.st_size)
            else:
                empreinte = hash_fichier(chemin)

            index[str(relatif)] = {
                "empreinte": empreinte,
                "taille":    stat.st_size,
                "mtime":     stat.st_mtime,
            }
            compteur += 1
            if compteur % 100 == 0:
                print(f"   [{label}] {compteur} fichiers scannés...", end="\r")
        except (PermissionError, OSError):
            pass

    return index

# ─── Comparaison ──────────────────────────────────────────────────────────────

def comparer(index_a: dict, index_b: dict) -> dict:
    cles_a = set(index_a)
    cles_b = set(index_b)
    communs = cles_a & cles_b

    identiques = []
    modifies   = []

    for cle in sorted(communs):
        emp_a = index_a[cle]["empreinte"]
        emp_b = index_b[cle]["empreinte"]
        if emp_a and emp_b and emp_a == emp_b:
            identiques.append(cle)
        else:
            modifies.append({
                "chemin":   cle,
                "taille_a": index_a[cle]["taille"],
                "taille_b": index_b[cle]["taille"],
                "mtime_a":  index_a[cle]["mtime"],
                "mtime_b":  index_b[cle]["mtime"],
                "erreur":   not (emp_a and emp_b),
            })

    return {
        "identiques":  identiques,
        "modifies":    modifies,
        "seulement_a": sorted(cles_a - cles_b),
        "seulement_b": sorted(cles_b - cles_a),
    }

# ─── Affichage ────────────────────────────────────────────────────────────────

def afficher(resultats: dict, nom_a: str, nom_b: str, verbose: bool):
    nb_id  = len(resultats["identiques"])
    nb_mod = len(resultats["modifies"])
    nb_a   = len(resultats["seulement_a"])
    nb_b   = len(resultats["seulement_b"])
    total  = nb_id + nb_mod + nb_a + nb_b

    print()
    print(gras("=" * 65))
    print(gras("  RÉSULTAT DE LA COMPARAISON"))
    print(gras("=" * 65))
    print(f"  A : {nom_a}")
    print(f"  B : {nom_b}")
    print()
    print(f"  {vert(f'Identiques         : {nb_id:>5}')}")
    print(f"  {jaune(f'Modifiés           : {nb_mod:>5}')}")
    print(f"  {rouge(f'Seulement dans A   : {nb_a:>5}')}")
    print(f"  {cyan(f'Seulement dans B   : {nb_b:>5}')}")
    print(f"  {'─'*35}")
    print(f"  Total              : {total:>5}")
    print()

    if nb_id > 0 and nb_mod == 0 and nb_a == 0 and nb_b == 0:
        print(vert("  Les deux dossiers sont identiques."))
        print()
        return

    if not verbose:
        return

    if resultats["modifies"]:
        print(gras(f"─── MODIFIÉS ({nb_mod}) " + "─" * 48))
        for item in resultats["modifies"]:
            if item["erreur"]:
                print(f"  {jaune('[?]')} {item['chemin']}  (erreur de lecture)")
            else:
                delta = item["taille_b"] - item["taille_a"]
                signe = "+" if delta >= 0 else ""
                print(f"  {jaune('M')}  {item['chemin']}")
                print(dim(f"     A : {fmt_taille(item['taille_a'])} — {fmt_date(item['mtime_a'])}"))
                print(dim(f"     B : {fmt_taille(item['taille_b'])} — {fmt_date(item['mtime_b'])}"
                          f"  ({signe}{fmt_taille(abs(delta))})"))
        print()

    if resultats["seulement_a"]:
        print(gras(f"─── SEULEMENT DANS A ({nb_a}) " + "─" * 40))
        for chemin in resultats["seulement_a"]:
            print(f"  {rouge('-')}  {chemin}")
        print()

    if resultats["seulement_b"]:
        print(gras(f"─── SEULEMENT DANS B ({nb_b}) " + "─" * 40))
        for chemin in resultats["seulement_b"]:
            print(f"  {cyan('+')  }  {chemin}")
        print()

# ─── Export CSV ───────────────────────────────────────────────────────────────

def exporter_csv(resultats: dict, chemin_sortie: Path, nom_a: str, nom_b: str):
    with open(chemin_sortie, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")

        w.writerow(["# COMPARAISON DE DOSSIERS"])
        w.writerow(["Dossier A", nom_a])
        w.writerow(["Dossier B", nom_b])
        w.writerow(["Généré le", datetime.now().strftime("%Y-%m-%d %H:%M")])
        w.writerow([])
        w.writerow(["# RÉSUMÉ"])
        w.writerow(["Catégorie", "Fichiers"])
        w.writerow(["Identiques",        len(resultats["identiques"])])
        w.writerow(["Modifiés",          len(resultats["modifies"])])
        w.writerow(["Seulement dans A",  len(resultats["seulement_a"])])
        w.writerow(["Seulement dans B",  len(resultats["seulement_b"])])
        w.writerow([])

        w.writerow(["# DÉTAIL"])
        w.writerow(["Statut", "Chemin", "Taille A", "Taille B", "Date A", "Date B"])

        for c in resultats["identiques"]:
            w.writerow(["Identique", c, "", "", "", ""])

        for item in resultats["modifies"]:
            w.writerow([
                "Modifié", item["chemin"],
                fmt_taille(item.get("taille_a", 0)),
                fmt_taille(item.get("taille_b", 0)),
                fmt_date(item.get("mtime_a", 0)) if not item["erreur"] else "",
                fmt_date(item.get("mtime_b", 0)) if not item["erreur"] else "",
            ])

        for c in resultats["seulement_a"]:
            w.writerow(["Seulement dans A", c, "", "", "", ""])

        for c in resultats["seulement_b"]:
            w.writerow(["Seulement dans B", c, "", "", "", ""])

    print(vert(f"Export CSV : {chemin_sortie}"))

# ─── Export HTML ──────────────────────────────────────────────────────────────

CSS = """
body{font-family:monospace;background:#1e1e1e;color:#d4d4d4;margin:2em}
h1{color:#569cd6}h2{color:#4ec9b0;border-bottom:1px solid #333;padding-bottom:4px}
table{border-collapse:collapse;width:100%;margin-bottom:2em}
th{background:#252526;color:#9cdcfe;text-align:left;padding:6px 12px}
td{padding:4px 12px;border-bottom:1px solid #2d2d2d;font-size:.9em}
.identique{color:#4ec9b0}.modifie{color:#dcdcaa}
.seulement-a{color:#f44747}.seulement-b{color:#569cd6}
.summary{background:#252526;padding:1em;border-radius:4px;margin-bottom:2em}
.summary span{color:#4ec9b0;font-weight:bold}
.num{text-align:right;color:#b5cea8}
tr:hover{background:#2a2d2e}
"""

def exporter_html(resultats: dict, chemin_sortie: Path, nom_a: str, nom_b: str):
    nb_id  = len(resultats["identiques"])
    nb_mod = len(resultats["modifies"])
    nb_a   = len(resultats["seulement_a"])
    nb_b   = len(resultats["seulement_b"])

    def lignes_modifies():
        html = ""
        for item in resultats["modifies"]:
            if item["erreur"]:
                html += f'<tr><td class="modifie">{item["chemin"]}</td><td colspan="4">Erreur de lecture</td></tr>\n'
            else:
                html += (f'<tr><td class="modifie">{item["chemin"]}</td>'
                         f'<td class="num">{fmt_taille(item["taille_a"])}</td>'
                         f'<td class="num">{fmt_taille(item["taille_b"])}</td>'
                         f'<td class="num">{fmt_date(item["mtime_a"])}</td>'
                         f'<td class="num">{fmt_date(item["mtime_b"])}</td></tr>\n')
        return html

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Comparaison de dossiers</title>
<style>{CSS}</style></head>
<body>
<h1>Comparaison de dossiers</h1>
<div class="summary">
  A : <span>{nom_a}</span><br>
  B : <span>{nom_b}</span><br>
  Généré le : <span>{datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
</div>
<h2>Résumé</h2>
<table>
  <tr><th>Catégorie</th><th>Fichiers</th></tr>
  <tr><td class="identique">Identiques</td><td class="num">{nb_id}</td></tr>
  <tr><td class="modifie">Modifiés</td><td class="num">{nb_mod}</td></tr>
  <tr><td class="seulement-a">Seulement dans A</td><td class="num">{nb_a}</td></tr>
  <tr><td class="seulement-b">Seulement dans B</td><td class="num">{nb_b}</td></tr>
</table>
<h2>Fichiers modifiés</h2>
<table>
  <tr><th>Chemin</th><th>Taille A</th><th>Taille B</th><th>Date A</th><th>Date B</th></tr>
  {lignes_modifies()}
</table>
<h2>Seulement dans A</h2>
<table><tr><th>Chemin</th></tr>
{"".join(f'<tr><td class="seulement-a">{c}</td></tr>' for c in resultats["seulement_a"])}
</table>
<h2>Seulement dans B</h2>
<table><tr><th>Chemin</th></tr>
{"".join(f'<tr><td class="seulement-b">{c}</td></tr>' for c in resultats["seulement_b"])}
</table>
</body></html>"""

    chemin_sortie.write_text(html, encoding="utf-8")
    print(vert(f"Export HTML : {chemin_sortie}"))

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare deux dossiers et identifie les différences.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python comparateur_dossiers.py ~/Documents ~/Backup/Documents
  python comparateur_dossiers.py . /media/disque/sauvegarde --rapide
  python comparateur_dossiers.py A B --html diff.html --csv diff.csv
  python comparateur_dossiers.py A B -e .git __pycache__ *.tmp
        """
    )
    parser.add_argument("dossier_a", help="Premier dossier (référence A)")
    parser.add_argument("dossier_b", help="Second dossier (référence B)")
    parser.add_argument("--rapide", action="store_true",
                        help="Comparaison par taille uniquement (sans hash SHA-256 — plus rapide, moins précis)")
    parser.add_argument("--csv",  metavar="FICHIER", help="Exporter le rapport en CSV")
    parser.add_argument("--html", metavar="FICHIER", help="Exporter le rapport en HTML autonome")
    parser.add_argument("-q", "--silencieux", action="store_true",
                        help="Afficher uniquement le résumé (sans le détail par fichier)")
    parser.add_argument("-e", "--exclure", nargs="+", default=[], metavar="PATTERN",
                        help="Exclure les fichiers/dossiers correspondant aux patterns (ex: .git *.tmp)")
    return parser.parse_args()


def main():
    args = parse_args()

    racine_a = Path(args.dossier_a).resolve()
    racine_b = Path(args.dossier_b).resolve()

    for chemin, label in [(racine_a, "A"), (racine_b, "B")]:
        if not chemin.exists() or not chemin.is_dir():
            print(rouge(f"Dossier {label} introuvable : {chemin}"))
            sys.exit(1)

    mode = "taille uniquement (rapide)" if args.rapide else "hash SHA-256 (précis)"
    print(f"\nMode de comparaison : {mode}")
    print(f"  A : {racine_a}")
    print(f"  B : {racine_b}")
    if args.exclure:
        print(f"  Exclusions : {', '.join(args.exclure)}")
    print()

    print("Scan du dossier A...")
    index_a = scanner(racine_a, args.rapide, args.exclure, "A")
    print(f"   {len(index_a)} fichier(s) indexé(s)          ")

    print("Scan du dossier B...")
    index_b = scanner(racine_b, args.rapide, args.exclure, "B")
    print(f"   {len(index_b)} fichier(s) indexé(s)          ")

    resultats = comparer(index_a, index_b)
    afficher(resultats, str(racine_a), str(racine_b), verbose=not args.silencieux)

    if args.csv:
        exporter_csv(resultats, Path(args.csv), str(racine_a), str(racine_b))
    if args.html:
        exporter_html(resultats, Path(args.html), str(racine_a), str(racine_b))


if __name__ == "__main__":
    main()
