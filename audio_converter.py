#!/usr/bin/env python3
"""
audio_converter.py
Convertit des fichiers audio en batch via ffmpeg.
Supporte MP3, FLAC, WAV, OGG, AAC, M4A, OPUS.
Peut normaliser le volume et extraire l'audio d'une video.

Prérequis : ffmpeg doit etre installe et accessible dans le PATH.
            Telecharger : https://ffmpeg.org/download.html

Usage :
    python audio_converter.py ./musique --format mp3
    python audio_converter.py ./musique --format flac --normaliser
    python audio_converter.py video.mp4 --format mp3 --extraire-audio
    python audio_converter.py ./dossier --format opus --debit 128k --sortie ./converti
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

EXT_AUDIO = {".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".opus",
             ".wma", ".aiff", ".ape", ".alac"}
EXT_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".ts", ".m4v", ".flv"}

_verrou = threading.Lock()

# ─── Verification ffmpeg ──────────────────────────────────────────────────────

def verifier_ffmpeg() -> str:
    """Retourne le chemin de ffmpeg ou quitte si absent."""
    chemin = shutil.which("ffmpeg")
    if not chemin:
        print(rouge("ffmpeg introuvable dans le PATH."))
        print(dim("  Telecharger : https://ffmpeg.org/download.html"))
        print(dim("  Windows : https://www.gyan.dev/ffmpeg/builds/ (ffmpeg-release-essentials.zip)"))
        sys.exit(1)
    return chemin

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def taille_lisible(n: int) -> str:
    for u in ("o", "Ko", "Mo", "Go"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} To"


def duree_audio(chemin: Path) -> str:
    """Retourne la duree via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(chemin)],
            capture_output=True, text=True, timeout=10
        )
        sec = float(result.stdout.strip())
        h, sec = divmod(int(sec), 3600)
        m, s   = divmod(sec, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    except Exception:
        return "??:??"

# ─── Construction de la commande ffmpeg ───────────────────────────────────────

CODECS = {
    "mp3":  {"codec": "libmp3lame",   "debit_defaut": "192k", "lossless": False},
    "flac": {"codec": "flac",         "debit_defaut": None,   "lossless": True},
    "wav":  {"codec": "pcm_s16le",    "debit_defaut": None,   "lossless": True},
    "ogg":  {"codec": "libvorbis",    "debit_defaut": "192k", "lossless": False},
    "aac":  {"codec": "aac",          "debit_defaut": "192k", "lossless": False},
    "m4a":  {"codec": "aac",          "debit_defaut": "192k", "lossless": False},
    "opus": {"codec": "libopus",      "debit_defaut": "128k", "lossless": False},
}


def construire_cmd(ffmpeg: str, source: Path, dest: Path,
                   format_sortie: str, debit: str | None,
                   normaliser: bool, extraire_audio: bool) -> list[str]:
    info = CODECS.get(format_sortie, CODECS["mp3"])
    cmd = [ffmpeg, "-i", str(source), "-y"]

    if extraire_audio:
        cmd += ["-vn"]          # Ignorer la piste video

    cmd += ["-acodec", info["codec"]]

    if not info["lossless"] and debit:
        cmd += ["-ab", debit]
    elif not info["lossless"] and info["debit_defaut"]:
        cmd += ["-ab", info["debit_defaut"]]

    if normaliser:
        # loudnorm : normalisation EBU R128 (-23 LUFS)
        cmd += ["-af", "loudnorm=I=-23:TP=-2:LRA=11"]

    cmd.append(str(dest))
    return cmd

# ─── Conversion d'un fichier ──────────────────────────────────────────────────

def convertir_fichier(ffmpeg: str, chemin: Path, args,
                       dossier_sortie: Path | None) -> tuple[bool, str]:
    format_sortie = args.format
    ext_sortie = "." + format_sortie

    if dossier_sortie:
        dest = dossier_sortie / (chemin.stem + ext_sortie)
    else:
        dest = chemin.with_suffix(ext_sortie)

    if dest == chemin:
        dest = chemin.with_stem(chemin.stem + "_converti").with_suffix(ext_sortie)

    if args.simulation:
        with _verrou:
            print(f"  {cyan(chemin.name):<45} -> {dest.name}")
        return True, str(dest)

    cmd = construire_cmd(
        ffmpeg, chemin, dest, format_sortie,
        args.debit, args.normaliser, args.extraire_audio
    )

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            erreur = result.stderr.splitlines()[-1] if result.stderr else "Erreur inconnue"
            with _verrou:
                print(rouge(f"  ERR {chemin.name} : {erreur[:80]}"))
            return False, ""

        taille = dest.stat().st_size
        with _verrou:
            print(f"  {vert('OK')}  {chemin.name:<40} -> {dest.name} ({taille_lisible(taille)})")
        return True, str(dest)

    except subprocess.TimeoutExpired:
        with _verrou:
            print(rouge(f"  TIMEOUT {chemin.name}"))
        return False, ""
    except Exception as e:
        with _verrou:
            print(rouge(f"  ERR {chemin.name} : {e}"))
        return False, ""

# ─── Collecte des fichiers ────────────────────────────────────────────────────

def collecter(source: Path, recursif: bool, extraire_audio: bool) -> list[Path]:
    ext_valides = EXT_AUDIO | (EXT_VIDEO if extraire_audio else set())

    if source.is_file():
        return [source] if source.suffix.lower() in ext_valides else []

    motif = "**/*" if recursif else "*"
    return sorted(p for p in source.glob(motif)
                  if p.is_file() and p.suffix.lower() in ext_valides)

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Convertit des fichiers audio en batch via ffmpeg.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Formats supportes : mp3, flac, wav, ogg, aac, m4a, opus
Prérequis : ffmpeg installe (https://ffmpeg.org/download.html)

Exemples :
  python audio_converter.py ./musique --format flac
  python audio_converter.py ./musique --format mp3 --debit 320k --normaliser
  python audio_converter.py video.mp4 --format mp3 --extraire-audio
  python audio_converter.py ./dossier --format opus --debit 128k -r --sortie ./opus
        """
    )
    parser.add_argument("source", help="Fichier ou dossier a convertir")
    parser.add_argument("--format",
                        choices=list(CODECS.keys()), required=True,
                        help="Format audio de sortie")
    parser.add_argument("--debit", metavar="DEBIT",
                        help="Debit audio (ex: 128k, 192k, 320k) — formats lossy uniquement")
    parser.add_argument("--normaliser", action="store_true",
                        help="Normaliser le volume (EBU R128, -23 LUFS)")
    parser.add_argument("--extraire-audio", action="store_true",
                        help="Extraire la piste audio d'un fichier video")
    parser.add_argument("-r", "--recursif", action="store_true",
                        help="Traiter les sous-dossiers recursivement")
    parser.add_argument("--sortie", metavar="DIR",
                        help="Dossier de destination")
    parser.add_argument("-t", "--threads", type=int, default=2, metavar="N",
                        help="Conversions simultanees (defaut : 2)")
    parser.add_argument("-s", "--simulation", action="store_true",
                        help="Lister les conversions sans les executer")
    return parser.parse_args()


def main():
    args = parse_args()
    ffmpeg = verifier_ffmpeg()

    source = Path(args.source)
    if not source.exists():
        print(rouge(f"Source introuvable : {source}"))
        sys.exit(1)

    dossier_sortie = None
    if args.sortie:
        dossier_sortie = Path(args.sortie)
        if not args.simulation:
            dossier_sortie.mkdir(parents=True, exist_ok=True)

    fichiers = collecter(source, args.recursif, args.extraire_audio)
    if not fichiers:
        print(jaune("Aucun fichier audio/video compatible trouve."))
        sys.exit(0)

    info_codec = CODECS.get(args.format, {})
    print(f"\n{gras('=== Conversion audio batch ===')}")
    print(f"  Format  : {args.format}  ({info_codec.get('codec', '?')})")
    if args.debit and not info_codec.get("lossless"):
        print(f"  Debit   : {args.debit}")
    if args.normaliser:
        print(f"  Normalize : loudnorm EBU R128 -23 LUFS")
    print(f"  Fichiers : {len(fichiers)}")
    if args.simulation:
        print(jaune("  (simulation)\n"))

    ok = ko = 0
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {
            pool.submit(convertir_fichier, ffmpeg, f, args, dossier_sortie): f
            for f in fichiers
        }
        for future in as_completed(futures):
            succes, _ = future.result()
            if succes:
                ok += 1
            else:
                ko += 1

    print(f"\n  {vert(str(ok))} converti(s)"
          + (f"  /  {rouge(str(ko))} echec(s)" if ko else ""))


if __name__ == "__main__":
    main()
