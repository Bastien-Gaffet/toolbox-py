#!/usr/bin/env python3
"""
video_downloader.py
Telecharge des videos (ou l'audio seul) depuis YouTube et ~1000 autres sites,
via yt-dlp. Choix de la qualite, extraction MP3, playlists, mode simulation.

Deux façons de l'utiliser :

  1. Mode interactif (le plus simple) — lancez sans rien :
         python video_downloader.py
     Le script demande l'URL, la qualite, le dossier de sortie.

  2. Mode arguments :
         python video_downloader.py "https://youtu.be/xxxx"
         python video_downloader.py "https://youtu.be/xxxx" -q 1080 -s ./videos
         python video_downloader.py "https://youtu.be/xxxx" --audio
         python video_downloader.py "https://.../playlist" --playlist

Prerequis :
    pip install yt-dlp
    ffmpeg dans le PATH  (pour fusionner video+audio HD et extraire le MP3)
        Windows : https://www.gyan.dev/ffmpeg/builds/
"""

import os
import sys
import shutil
import argparse
from pathlib import Path


def _init_terminal():
    """Sortie UTF-8 (emojis, accents) + activation des couleurs ANSI sous Windows."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if os.name == "nt":
        try:
            import ctypes
            noyau = ctypes.windll.kernel32
            for std in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
                handle = noyau.GetStdHandle(std)
                mode = ctypes.c_uint32()
                if noyau.GetConsoleMode(handle, ctypes.byref(mode)):
                    # 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    noyau.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


_init_terminal()

# ─── Couleurs terminal (colorama optionnel) ──────────────────────────────────
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

# ─── Dependance yt-dlp ───────────────────────────────────────────────────────
try:
    import yt_dlp
except ImportError:
    print(rouge("yt-dlp est requis : ") + "pip install yt-dlp")
    sys.exit(1)


QUALITES = {
    "best": None,          # meilleure disponible
    "2160": 2160,          # 4K
    "1440": 1440,          # 2K
    "1080": 1080,
    "720":  720,
    "480":  480,
    "360":  360,
}


def ffmpeg_present() -> bool:
    return shutil.which("ffmpeg") is not None


def formater_taille(octets) -> str:
    if not octets:
        return "?"
    o = float(octets)
    for unite in ["o", "Ko", "Mo", "Go"]:
        if o < 1024:
            return f"{o:.1f} {unite}"
        o /= 1024
    return f"{o:.1f} To"


# ═══════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DES OPTIONS yt-dlp
# ═══════════════════════════════════════════════════════════════════════════

def _hook_progression(d: dict):
    """Affiche la progression sur une seule ligne."""
    statut = d.get("status")
    if statut == "downloading":
        pct = (d.get("_percent_str") or "").strip()
        vitesse = (d.get("_speed_str") or "").strip()
        eta = (d.get("_eta_str") or "").strip()
        nom = Path(d.get("filename", "")).name
        nom = nom[:40] + "…" if len(nom) > 40 else nom
        print(f"\r  {cyan(pct):>6}  {nom:<42} {vitesse:>10}  ETA {eta:>6}",
              end="", flush=True)
    elif statut == "finished":
        print("\r" + " " * 78 + "\r", end="")
        print(f"  {vert('✓')} {Path(d.get('filename','')).name}")


def construire_options(dossier: Path, qualite: str, audio: bool,
                       playlist: bool, simulation: bool) -> dict:
    opts = {
        "outtmpl": str(dossier / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": not playlist,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,           # supprime la barre interne : on garde notre hook
        "progress_hooks": [_hook_progression],
        "restrictfilenames": False,
        "windowsfilenames": True,     # noms compatibles Windows
    }

    if audio:
        # Extraction audio → MP3 (necessite ffmpeg)
        opts["format"] = "ba/b"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        hauteur = QUALITES.get(qualite)
        if not ffmpeg_present():
            # Sans ffmpeg : un seul flux deja muxe (souvent <=720p)
            opts["format"] = (f"b[height<={hauteur}]/b" if hauteur else "b")
        elif hauteur:
            opts["format"] = (f"bv*[height<={hauteur}]+ba/"
                              f"b[height<={hauteur}]/bv*+ba/b")
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bv*+ba/b"
            opts["merge_output_format"] = "mp4"

    return opts


# ═══════════════════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

def lister(url: str, playlist: bool):
    """Mode simulation : liste ce qui serait telecharge, sans rien recuperer."""
    opts = {"quiet": True, "no_warnings": True, "noplaylist": not playlist,
            "ignoreerrors": True, "extract_flat": "in_playlist"}
    print(gras("\n🔎 Analyse (aucun téléchargement)...\n"))
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        print(rouge(f"  Impossible d'analyser l'URL : {e}"))
        return

    if info is None:
        print(rouge("  Rien trouvé à cette URL."))
        return

    entrees = info.get("entries")
    if entrees:  # playlist
        entrees = [e for e in entrees if e]
        print(f"  Playlist : {gras(info.get('title', '?'))}  "
              f"({len(entrees)} vidéo(s))\n")
        for i, e in enumerate(entrees, 1):
            print(f"    {i:>3}. {e.get('title', '?')}")
    else:        # video unique
        dur = info.get("duration")
        duree = f"{dur // 60}:{dur % 60:02d}" if dur else "?"
        print(f"  Titre    : {gras(info.get('title', '?'))}")
        print(f"  Auteur   : {info.get('uploader', '?')}")
        print(f"  Durée    : {duree}")
        print(f"  Site     : {info.get('extractor_key', '?')}")
    print(dim("\n  → Relancez sans --simulation pour télécharger.\n"))


def telecharger(url: str, dossier: Path, qualite: str, audio: bool,
                playlist: bool) -> int:
    """Telecharge et retourne le code de sortie yt-dlp (0 = succes)."""
    if audio and not ffmpeg_present():
        print(rouge("\n❌ L'extraction MP3 nécessite ffmpeg (absent du PATH)."))
        print(dim("   Windows : https://www.gyan.dev/ffmpeg/builds/\n"))
        return 1

    if not audio and not ffmpeg_present():
        print(jaune("\n⚠️  ffmpeg absent : qualité limitée au meilleur flux déjà "
                    "fusionné (souvent ≤720p), pas de fusion HD."))
        print(dim("   Installer ffmpeg pour la HD : https://www.gyan.dev/ffmpeg/builds/"))

    dossier.mkdir(parents=True, exist_ok=True)
    opts = construire_options(dossier, qualite, audio, playlist, simulation=False)

    cible = "🎵 Audio MP3" if audio else f"🎬 Vidéo ({qualite})"
    print(gras(f"\n{cible}  →  {dossier}"))
    print(dim(f"  Source : {url}\n"))

    with yt_dlp.YoutubeDL(opts) as ydl:
        code = ydl.download([url])

    if code == 0:
        print(vert(f"\n✅ Terminé. Fichiers dans : {dossier}\n"))
    else:
        print(jaune(f"\n⚠️  Terminé avec des erreurs (voir ci-dessus).\n"))
    return code


# ═══════════════════════════════════════════════════════════════════════════
# MODE INTERACTIF
# ═══════════════════════════════════════════════════════════════════════════

def demander(question: str, defaut: str = "") -> str:
    suffixe = f" [{defaut}]" if defaut else ""
    rep = input(f"{question}{suffixe} : ").strip()
    return rep or defaut


def mode_interactif() -> dict:
    print(gras(cyan("\n═══════ Téléchargeur vidéo (yt-dlp) ═══════\n")))
    url = demander("URL de la vidéo ou playlist")
    while not url:
        print(jaune("  (URL obligatoire)"))
        url = demander("URL de la vidéo ou playlist")

    rep_audio = demander("Audio seul en MP3 ? (o/N)", "n").lower()
    audio = rep_audio in ("o", "oui", "y", "yes")

    qualite = "best"
    if not audio:
        print(dim("  Qualités : best, 2160, 1440, 1080, 720, 480, 360"))
        qualite = demander("Qualité", "best")
        if qualite not in QUALITES:
            print(jaune(f"  Qualité inconnue '{qualite}', utilisation de 'best'."))
            qualite = "best"

    playlist = False
    if "list=" in url or "playlist" in url.lower():
        playlist = demander("Télécharger toute la playlist ? (o/N)", "n").lower() \
                   in ("o", "oui", "y", "yes")

    sortie = demander("Dossier de sortie", "telechargements_video")
    return {"url": url, "audio": audio, "qualite": qualite,
            "playlist": playlist, "sortie": sortie, "simulation": False}


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="🎬 Télécharge des vidéos/audio depuis YouTube et ~1000 sites (yt-dlp).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python video_downloader.py                              (mode interactif)
  python video_downloader.py "https://youtu.be/xxxx"
  python video_downloader.py "https://youtu.be/xxxx" -q 1080 -s ./videos
  python video_downloader.py "https://youtu.be/xxxx" --audio
  python video_downloader.py "https://.../playlist" --playlist
  python video_downloader.py "https://youtu.be/xxxx" --simulation
""",
    )
    p.add_argument("url", nargs="?", default=None,
                   help="URL de la vidéo/playlist (mode interactif si absente)")
    p.add_argument("-s", "--sortie", default="telechargements_video",
                   metavar="DOSSIER", help="Dossier de destination")
    p.add_argument("-q", "--qualite", default="best", choices=list(QUALITES),
                   metavar="QUALITE",
                   help="best (défaut), 2160, 1440, 1080, 720, 480, 360")
    p.add_argument("--audio", action="store_true",
                   help="Extraire uniquement l'audio en MP3 (nécessite ffmpeg)")
    p.add_argument("--playlist", action="store_true",
                   help="Télécharger toute la playlist (sinon : vidéo seule)")
    p.add_argument("--simulation", action="store_true",
                   help="Lister sans rien télécharger")
    return p.parse_args()


def main():
    args = parse_args()

    if args.url is None:
        params = mode_interactif()
    else:
        params = {"url": args.url, "audio": args.audio, "qualite": args.qualite,
                  "playlist": args.playlist, "sortie": args.sortie,
                  "simulation": args.simulation}

    if params["simulation"]:
        lister(params["url"], params["playlist"])
        return

    code = telecharger(
        url=params["url"],
        dossier=Path(params["sortie"]).resolve(),
        qualite=params["qualite"],
        audio=params["audio"],
        playlist=params["playlist"],
    )
    sys.exit(code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(jaune("\nInterrompu par l'utilisateur."))
        sys.exit(130)
