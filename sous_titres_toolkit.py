#!/usr/bin/env python3
"""
sous_titres_toolkit.py
Outils pour fichiers de sous-titres .srt et .vtt :
  decaler    Decale tous les horodatages de +/- N millisecondes
  sync       Synchronisation precise a 2 points (corrige derive + offset)
  fusionner  Fusionne deux pistes en une (bilingue)
  convertir  Convertit SRT <-> VTT
  nettoyer   Supprime les balises HTML et SSA/ASS
  stats      Statistiques : nombre de cues, duree, mots/min
  chercher   Recherche et remplacement dans le texte

Usage :
    python sous_titres_toolkit.py decaler film.srt +5000
    python sous_titres_toolkit.py sync film.srt "00:01:23,456" "00:01:20,000" "00:45:00,000" "00:44:55,000"
    python sous_titres_toolkit.py fusionner fr.srt en.srt --sortie bilingue.srt
    python sous_titres_toolkit.py convertir film.srt film.vtt
    python sous_titres_toolkit.py nettoyer film.srt --sortie film_clean.srt
    python sous_titres_toolkit.py stats film.srt
    python sous_titres_toolkit.py chercher film.srt "l'" "l'" --regex
"""

import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass

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

# ─── Modele de donnees ────────────────────────────────────────────────────────

@dataclass
class Cue:
    index: int
    debut: int   # millisecondes
    fin:   int   # millisecondes
    texte: str   # peut etre multiligne

# ─── Conversion d'horodatages ─────────────────────────────────────────────────

RE_TS_SRT = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
RE_TS_VTT = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")


def ts_vers_ms(ts: str) -> int:
    """Convertit un horodatage SRT ou VTT en millisecondes."""
    ts = ts.strip().replace(",", ".").replace(".", ":", 2)
    m = re.match(r"(\d+):(\d{2}):(\d{2})[,\.](\d{3})", ts.replace(":", ",", 2).replace(",", ":", 2))
    if not m:
        m = re.match(r"(\d+):(\d{2}):(\d{2})[,\.](\d{3})", ts)
    if not m:
        raise ValueError(f"Horodatage non reconnu : {ts!r}")
    h, mn, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return h * 3_600_000 + mn * 60_000 + s * 1_000 + ms


def ms_vers_ts(ms: int, virgule: bool = True) -> str:
    """Convertit des millisecondes en horodatage SRT (virgule=True) ou VTT (virgule=False)."""
    ms = max(0, int(ms))
    h    = ms // 3_600_000;  ms %= 3_600_000
    mn   = ms // 60_000;     ms %= 60_000
    s    = ms // 1_000;      ms %= 1_000
    sep  = "," if virgule else "."
    return f"{h:02d}:{mn:02d}:{s:02d}{sep}{ms:03d}"


def ms_vers_ts_lisible(ms: int) -> str:
    """Retourne un format lisible type 1h23m45s."""
    ms = max(0, int(ms))
    h  = ms // 3_600_000;  ms %= 3_600_000
    mn = ms // 60_000;     ms %= 60_000
    s  = ms // 1_000
    if h:
        return f"{h}h{mn:02d}m{s:02d}s"
    if mn:
        return f"{mn}m{s:02d}s"
    return f"{s}s"

# ─── Parsers ──────────────────────────────────────────────────────────────────

RE_FLECHE = re.compile(r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})")


def parse_srt(contenu: str) -> list[Cue]:
    cues = []
    blocs = re.split(r"\n{2,}", contenu.strip())
    for bloc in blocs:
        lignes = bloc.strip().splitlines()
        if len(lignes) < 2:
            continue
        # Chercher la ligne de timing
        timing_idx = None
        for i, ligne in enumerate(lignes):
            if RE_FLECHE.match(ligne.strip()):
                timing_idx = i
                break
        if timing_idx is None:
            continue
        m = RE_FLECHE.match(lignes[timing_idx].strip())
        try:
            debut = ts_vers_ms(m.group(1))
            fin   = ts_vers_ms(m.group(2))
        except ValueError:
            continue
        # L'index est la ligne avant le timing (s'il existe)
        try:
            index = int(lignes[timing_idx - 1].strip()) if timing_idx > 0 else len(cues) + 1
        except (ValueError, IndexError):
            index = len(cues) + 1
        texte = "\n".join(lignes[timing_idx + 1:]).strip()
        cues.append(Cue(index=index, debut=debut, fin=fin, texte=texte))
    return cues


def parse_vtt(contenu: str) -> list[Cue]:
    # Supprimer l'en-tete WEBVTT et les blocs NOTE/STYLE
    contenu = re.sub(r"^WEBVTT.*\n?", "", contenu, flags=re.MULTILINE)
    contenu = re.sub(r"^(NOTE|STYLE).*?(?=\n\n|\Z)", "", contenu,
                     flags=re.MULTILINE | re.DOTALL)
    # Supprimer les balises de cue inline VTT (<c>, <00:00:00.000>, etc.)
    contenu = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", contenu)
    contenu = re.sub(r"</?c(?:\.\w+)?>", "", contenu)
    return parse_srt(contenu)  # Meme logique apres nettoyage


def parse_auto(chemin: Path) -> list[Cue]:
    contenu = chemin.read_text(encoding="utf-8-sig", errors="replace")
    if chemin.suffix.lower() == ".vtt":
        return parse_vtt(contenu)
    return parse_srt(contenu)

# ─── Serialiseurs ─────────────────────────────────────────────────────────────

def vers_srt(cues: list[Cue]) -> str:
    blocs = []
    for i, cue in enumerate(cues, 1):
        blocs.append(
            f"{i}\n"
            f"{ms_vers_ts(cue.debut, virgule=True)} --> {ms_vers_ts(cue.fin, virgule=True)}\n"
            f"{cue.texte}"
        )
    return "\n\n".join(blocs) + "\n"


def vers_vtt(cues: list[Cue]) -> str:
    blocs = ["WEBVTT\n"]
    for i, cue in enumerate(cues, 1):
        blocs.append(
            f"{i}\n"
            f"{ms_vers_ts(cue.debut, virgule=False)} --> {ms_vers_ts(cue.fin, virgule=False)}\n"
            f"{cue.texte}"
        )
    return "\n\n".join(blocs) + "\n"


def ecrire(cues: list[Cue], chemin: Path):
    if chemin.suffix.lower() == ".vtt":
        chemin.write_text(vers_vtt(cues), encoding="utf-8")
    else:
        chemin.write_text(vers_srt(cues), encoding="utf-8")
    print(vert(f"  Ecrit : {chemin}  ({len(cues)} cue(s))"))

# ─── Destination par defaut ───────────────────────────────────────────────────

def dest_par_defaut(source: Path, suffixe: str, ext: str | None = None) -> Path:
    extension = ext or source.suffix
    return source.with_stem(source.stem + suffixe).with_suffix(extension)

# ─── Operations ───────────────────────────────────────────────────────────────

def op_decaler(args):
    source = Path(args.source)
    cues = parse_auto(source)
    if not cues:
        print(rouge("Aucun cue trouve."))
        sys.exit(1)

    try:
        delta = int(args.delta)
    except ValueError:
        print(rouge(f"Delta invalide : {args.delta!r}  (entier en ms, ex: +5000 ou -3000)"))
        sys.exit(1)

    for cue in cues:
        cue.debut = max(0, cue.debut + delta)
        cue.fin   = max(0, cue.fin   + delta)

    signe = "+" if delta >= 0 else ""
    print(f"\n  Decalage : {signe}{delta} ms  ({signe}{delta/1000:.3f}s)")
    print(f"  {len(cues)} cue(s) modifie(s)")

    sortie = Path(args.sortie) if args.sortie else dest_par_defaut(source, "_sync")
    if not args.simulation:
        ecrire(cues, sortie)
    else:
        print(jaune("  (simulation : fichier non ecrit)"))


def op_sync(args):
    """Synchronisation lineaire a 2 points : corrige derive et offset."""
    source = Path(args.source)
    cues = parse_auto(source)

    try:
        t1_src  = ts_vers_ms(args.t1_src)
        t1_dest = ts_vers_ms(args.t1_dest)
        t2_src  = ts_vers_ms(args.t2_src)
        t2_dest = ts_vers_ms(args.t2_dest)
    except ValueError as e:
        print(rouge(f"Horodatage invalide : {e}"))
        sys.exit(1)

    if t2_src == t1_src:
        print(rouge("Les deux points source sont identiques (division par zero)."))
        sys.exit(1)

    # Transformation lineaire : t_new = t * echelle + offset
    echelle = (t2_dest - t1_dest) / (t2_src - t1_src)
    offset  = t1_dest - echelle * t1_src

    for cue in cues:
        cue.debut = max(0, round(cue.debut * echelle + offset))
        cue.fin   = max(0, round(cue.fin   * echelle + offset))

    derive_ms = round((echelle - 1) * 100000) / 100  # derive par 100s en ms
    print(f"\n  Echelle : {echelle:.6f}  (derive : {derive_ms:+.1f} ms / 100s)")
    print(f"  Offset  : {offset:+.0f} ms  ({offset/1000:+.3f}s)")
    print(f"  {len(cues)} cue(s) recales")

    sortie = Path(args.sortie) if args.sortie else dest_par_defaut(source, "_sync2p")
    if not args.simulation:
        ecrire(cues, sortie)
    else:
        print(jaune("  (simulation : fichier non ecrit)"))


def op_fusionner(args):
    source1 = Path(args.source)
    source2 = Path(args.source2)
    cues1 = parse_auto(source1)
    cues2 = parse_auto(source2)

    # Fusionner et trier par debut
    tous = sorted(cues1 + cues2, key=lambda c: c.debut)

    # Re-numeroter
    for i, cue in enumerate(tous, 1):
        cue.index = i

    print(f"\n  Piste 1 : {len(cues1)} cue(s) — {source1.name}")
    print(f"  Piste 2 : {len(cues2)} cue(s) — {source2.name}")
    print(f"  Fusionnes : {len(tous)} cue(s)")

    sortie = Path(args.sortie) if args.sortie else dest_par_defaut(source1, "_bilingue")
    if not args.simulation:
        ecrire(tous, sortie)
    else:
        print(jaune("  (simulation : fichier non ecrit)"))


def op_convertir(args):
    source = Path(args.source)
    cues = parse_auto(source)

    if args.sortie:
        sortie = Path(args.sortie)
    else:
        ext_cible = ".vtt" if source.suffix.lower() == ".srt" else ".srt"
        sortie = source.with_suffix(ext_cible)

    print(f"\n  Conversion : {source.suffix.upper()} -> {sortie.suffix.upper()}")
    print(f"  {len(cues)} cue(s)")

    if not args.simulation:
        ecrire(cues, sortie)
    else:
        print(jaune("  (simulation : fichier non ecrit)"))


# Balises a supprimer
RE_BALISES_HTML = re.compile(
    r"</?(?:i|b|u|s|em|strong|font|span|c)[^>]*>",
    re.IGNORECASE
)
RE_BALISES_SSA = re.compile(
    r"\{[^}]*\}"         # {\\an8}, {\i1}, {\pos(x,y)}, etc.
)
RE_BALISES_VTT_INLINE = re.compile(
    r"<\d{2}:\d{2}:\d{2}\.\d{3}>"   # cue timestamps inline
)


def nettoyer_texte(texte: str) -> str:
    texte = RE_BALISES_SSA.sub("", texte)
    texte = RE_BALISES_VTT_INLINE.sub("", texte)
    texte = RE_BALISES_HTML.sub("", texte)
    # Normaliser les espaces
    lignes = [re.sub(r"  +", " ", l).strip() for l in texte.splitlines()]
    return "\n".join(l for l in lignes if l)


def op_nettoyer(args):
    source = Path(args.source)
    cues = parse_auto(source)
    balises_trouvees = 0

    for cue in cues:
        propre = nettoyer_texte(cue.texte)
        if propre != cue.texte:
            balises_trouvees += 1
        cue.texte = propre

    print(f"\n  {balises_trouvees} cue(s) contenaient des balises")

    sortie = Path(args.sortie) if args.sortie else dest_par_defaut(source, "_clean")
    if not args.simulation:
        ecrire(cues, sortie)
    else:
        print(jaune("  (simulation : fichier non ecrit)"))


def op_stats(args):
    source = Path(args.source)
    cues = parse_auto(source)

    if not cues:
        print(rouge("Aucun cue trouve."))
        sys.exit(1)

    nb_mots = sum(len(cue.texte.split()) for cue in cues)
    duree_totale = cues[-1].fin - cues[0].debut  # ms
    duree_affichee = sum(cue.fin - cue.debut for cue in cues)
    duree_moyenne = duree_affichee / len(cues)
    mpm = nb_mots / max(duree_totale / 60_000, 0.001)

    # Cues les plus longs en texte
    top_longs = sorted(cues, key=lambda c: len(c.texte), reverse=True)[:5]
    # Cues les plus courts en duree
    durees = [(cue.fin - cue.debut, cue) for cue in cues]
    durees.sort()

    print(f"\n{gras('=== Statistiques ===')}  {source.name}\n")
    print(f"  Cues            : {len(cues)}")
    print(f"  Debut           : {ms_vers_ts(cues[0].debut)}")
    print(f"  Fin             : {ms_vers_ts(cues[-1].fin)}")
    print(f"  Duree totale    : {ms_vers_ts_lisible(duree_totale)}")
    print(f"  Duree affichage : {ms_vers_ts_lisible(duree_affichee)}")
    print(f"  Duree moyenne   : {duree_moyenne:.0f} ms / cue")
    print(f"  Mots            : {nb_mots}")
    print(f"  Mots/minute     : {mpm:.1f}")

    print(f"\n  {dim('Top 5 cues les plus longs (texte) :')}")
    for cue in top_longs:
        preview = cue.texte.replace("\n", " ")[:60]
        print(f"    #{cue.index:<5} {dim(ms_vers_ts(cue.debut))}  {preview}")

    print(f"\n  {dim('3 cues les plus courts (duree) :')}")
    for duree_ms, cue in durees[:3]:
        print(f"    #{cue.index:<5} {duree_ms} ms  {cue.texte[:50].replace(chr(10), ' ')}")


def op_chercher(args):
    source = Path(args.source)
    cues = parse_auto(source)
    modifies = 0

    flags = re.IGNORECASE if args.insensible else 0
    remplacement = args.remplacement or ""

    for cue in cues:
        if args.regex:
            nouveau = re.sub(args.motif, remplacement, cue.texte, flags=flags)
        elif args.insensible:
            nouveau = re.sub(re.escape(args.motif), remplacement, cue.texte, flags=flags)
        else:
            nouveau = cue.texte.replace(args.motif, remplacement)

        if nouveau != cue.texte:
            if args.apercu:
                print(f"  #{cue.index}  {cyan(cue.texte[:60])} -> {vert(nouveau[:60])}")
            cue.texte = nouveau
            modifies += 1

    print(f"\n  {modifies} cue(s) modifie(s) sur {len(cues)}")

    if args.apercu or args.simulation:
        print(jaune("  (simulation : fichier non ecrit)"))
        return

    sortie = Path(args.sortie) if args.sortie else dest_par_defaut(source, "_modifie")
    ecrire(cues, sortie)

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Outils pour fichiers de sous-titres SRT et VTT.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="commande", required=True)

    # ── decaler
    p = sub.add_parser("decaler", help="Decaler tous les horodatages de +/- N ms")
    p.add_argument("source", help="Fichier .srt ou .vtt")
    p.add_argument("delta",  help="Decalage en millisecondes (ex: +5000 ou -3000)")
    p.add_argument("--sortie", metavar="FICHIER", help="Fichier de sortie")
    p.add_argument("-s", "--simulation", action="store_true")

    # ── sync (2 points)
    p = sub.add_parser("sync",
        help="Synchronisation a 2 points (corrige derive + offset)")
    p.add_argument("source",  help="Fichier .srt ou .vtt")
    p.add_argument("t1_src",  help="1er horodatage source   (ex: 00:01:23,456)")
    p.add_argument("t1_dest", help="1er horodatage cible    (ex: 00:01:20,000)")
    p.add_argument("t2_src",  help="2eme horodatage source  (ex: 00:45:00,000)")
    p.add_argument("t2_dest", help="2eme horodatage cible   (ex: 00:44:55,000)")
    p.add_argument("--sortie", metavar="FICHIER")
    p.add_argument("-s", "--simulation", action="store_true")

    # ── fusionner
    p = sub.add_parser("fusionner", help="Fusionner deux pistes en une")
    p.add_argument("source",  help="Premiere piste .srt / .vtt")
    p.add_argument("source2", help="Deuxieme piste .srt / .vtt")
    p.add_argument("--sortie", metavar="FICHIER")
    p.add_argument("-s", "--simulation", action="store_true")

    # ── convertir
    p = sub.add_parser("convertir", help="Convertir SRT <-> VTT")
    p.add_argument("source",  help="Fichier source .srt ou .vtt")
    p.add_argument("--sortie", metavar="FICHIER")
    p.add_argument("-s", "--simulation", action="store_true")

    # ── nettoyer
    p = sub.add_parser("nettoyer",
        help="Supprimer les balises HTML et SSA ({\\i1}, <b>, <font...>)")
    p.add_argument("source", help="Fichier .srt ou .vtt")
    p.add_argument("--sortie", metavar="FICHIER")
    p.add_argument("-s", "--simulation", action="store_true")

    # ── stats
    p = sub.add_parser("stats", help="Afficher les statistiques du fichier")
    p.add_argument("source", help="Fichier .srt ou .vtt")

    # ── chercher
    p = sub.add_parser("chercher", help="Rechercher et remplacer dans le texte")
    p.add_argument("source",       help="Fichier .srt ou .vtt")
    p.add_argument("motif",        help="Texte ou regex a rechercher")
    p.add_argument("remplacement", nargs="?", default="",
                   help="Texte de remplacement (defaut : suppression)")
    p.add_argument("--regex",      action="store_true",
                   help="Interpreter le motif comme une regex")
    p.add_argument("-i", "--insensible", action="store_true",
                   help="Recherche insensible a la casse")
    p.add_argument("--apercu",     action="store_true",
                   help="Afficher les modifications sans ecrire")
    p.add_argument("--sortie",     metavar="FICHIER")
    p.add_argument("-s", "--simulation", action="store_true")

    return parser.parse_args()


OPERATIONS = {
    "decaler":   op_decaler,
    "sync":      op_sync,
    "fusionner": op_fusionner,
    "convertir": op_convertir,
    "nettoyer":  op_nettoyer,
    "stats":     op_stats,
    "chercher":  op_chercher,
}


def main():
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        print(rouge(f"Fichier introuvable : {source}"))
        sys.exit(1)
    OPERATIONS[args.commande](args)


if __name__ == "__main__":
    main()
