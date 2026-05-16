#!/usr/bin/env python3
"""
env_checker.py
Verifie l'environnement de developpement : versions des outils, variables
d'environnement manquantes, paquets installes vs requirements.txt.

Usage :
    python env_checker.py
    python env_checker.py --requirements requirements.txt
    python env_checker.py --env-exemple .env.example --outils docker make
"""

import os
import re
import sys
import subprocess
import importlib.metadata
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

OK  = vert("OK ")
ERR = rouge("ERR")
AVT = jaune("AVT")

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def version_commande(cmd: str, flag: str = "--version") -> str | None:
    """Retourne la version d'une commande ou None si introuvable."""
    try:
        result = subprocess.run(
            [cmd, flag], capture_output=True, text=True, timeout=5
        )
        sortie = (result.stdout + result.stderr).strip()
        # Extraire le premier token ressemblant a une version
        m = re.search(r"\d+\.\d+[\.\d]*", sortie)
        return m.group(0) if m else (sortie[:30] or None)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def version_min_ok(version: str, minimum: str) -> bool:
    """Retourne True si version >= minimum (comparaison par tuple d'entiers)."""
    try:
        v = tuple(int(x) for x in re.split(r"[.\-]", version)[:3])
        m = tuple(int(x) for x in re.split(r"[.\-]", minimum)[:3])
        return v >= m
    except ValueError:
        return True


def parse_requirements(chemin: Path) -> list[tuple[str, str]]:
    """Retourne [(nom_paquet, specif_version)] depuis un fichier requirements.txt."""
    paquets = []
    try:
        for ligne in chemin.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or ligne.startswith("-"):
                continue
            # Supprimer les extras et les marqueurs d'environnement
            ligne = re.sub(r"\[.*?\]", "", ligne)
            ligne = re.split(r";", ligne)[0].strip()
            m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([>=<!~].+)?$", ligne)
            if m:
                nom    = m.group(1).lower().replace("-", "_").replace(".", "_")
                specif = (m.group(2) or "").strip()
                paquets.append((m.group(1), specif))
    except OSError:
        pass
    return paquets

# ─── Sections de verification ─────────────────────────────────────────────────

def verifier_outils(outils: list[tuple[str, str, str]]) -> list[tuple[str, str, str, bool]]:
    """
    outils : liste de (nom, flag_version, version_min)
    Retourne : liste de (nom, version, version_min, ok)
    """
    resultats = []
    for nom, flag, version_min in outils:
        version = version_commande(nom, flag)
        if version and version_min:
            ok = version_min_ok(version, version_min)
        else:
            ok = version is not None
        resultats.append((nom, version or "", version_min, ok))
    return resultats


def verifier_paquets(requirements: Path) -> list[tuple[str, str, str, bool]]:
    """Verifie les paquets Python installes vs requirements.txt."""
    paquets = parse_requirements(requirements)
    resultats = []
    for nom_original, specif in paquets:
        # Normaliser le nom pour importlib
        nom_norm = nom_original.lower().replace("-", "_").replace(".", "_")
        # Essayer plusieurs variantes du nom
        version_installee = None
        for candidat in [nom_original, nom_norm, nom_original.replace("_", "-")]:
            try:
                version_installee = importlib.metadata.version(candidat)
                break
            except importlib.metadata.PackageNotFoundError:
                continue
        ok = version_installee is not None
        resultats.append((nom_original, version_installee or "", specif, ok))
    return resultats


def verifier_env(env_exemple: Path) -> list[tuple[str, bool, bool]]:
    """
    Compare .env.example avec les variables d'environnement actuelles.
    Retourne : [(nom, existe_dans_env, optionnel)]
    """
    resultats = []
    try:
        for ligne in env_exemple.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            # Format : VAR=valeur ou VAR= ou #optionnel VAR=
            optionnel = False
            if ligne.startswith("#"):
                optionnel = True
                ligne = ligne[1:].strip()
            m = re.match(r"^([A-Z_][A-Z0-9_]*)[\s=]", ligne)
            if not m:
                m = re.match(r"^([A-Z_][A-Z0-9_]*)$", ligne)
            if m:
                nom = m.group(1)
                existe = nom in os.environ
                resultats.append((nom, existe, optionnel))
    except OSError:
        pass
    return resultats


def verifier_venv() -> str:
    """Detecte l'environnement virtuel actif."""
    if os.environ.get("VIRTUAL_ENV"):
        return f"venv actif : {os.environ['VIRTUAL_ENV']}"
    if os.environ.get("CONDA_DEFAULT_ENV"):
        return f"conda actif : {os.environ['CONDA_DEFAULT_ENV']}"
    if sys.prefix != sys.base_prefix:
        return f"venv actif : {sys.prefix}"
    return ""

# ─── Affichage ────────────────────────────────────────────────────────────────

def afficher_section(titre: str):
    print(f"\n{gras(titre)}")
    print(dim("  " + "─" * 60))


def afficher_outil(nom: str, version: str, version_min: str, ok: bool):
    statut = OK if ok else ERR
    v = vert(version) if ok else rouge("non installe")
    min_str = dim(f"  (min: {version_min})") if version_min and not ok else ""
    print(f"  [{statut}]  {nom:<20} {v}{min_str}")


def afficher_paquet(nom: str, version: str, specif: str, ok: bool):
    statut = OK if ok else ERR
    if ok:
        detail = vert(version)
    else:
        detail = rouge("non installe")
    specif_str = dim(f"  {specif}") if specif else ""
    print(f"  [{statut}]  {nom:<30} {detail}{specif_str}")


def afficher_var_env(nom: str, existe: bool, optionnel: bool):
    if existe:
        statut = OK
        detail = vert("definie")
    elif optionnel:
        statut = AVT
        detail = jaune("absente (optionnelle)")
    else:
        statut = ERR
        detail = rouge("MANQUANTE")
    print(f"  [{statut}]  {nom:<35} {detail}")

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Verifie l'environnement de developpement.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Exemples :
  python env_checker.py
  python env_checker.py --requirements requirements.txt
  python env_checker.py --env-exemple .env.example
  python env_checker.py --outils docker make ffmpeg --python-min 3.11
        """
    )
    parser.add_argument("--requirements", metavar="FICHIER", default="requirements.txt",
                        help="Fichier requirements.txt a verifier (defaut : requirements.txt)")
    parser.add_argument("--env-exemple", metavar="FICHIER",
                        help="Fichier .env.example listant les variables attendues")
    parser.add_argument("--outils", nargs="+", metavar="OUTIL",
                        help="Outils supplementaires a verifier (ex: docker make ffmpeg)")
    parser.add_argument("--python-min", metavar="VERSION", default="3.10",
                        help="Version Python minimale requise (defaut : 3.10)")
    parser.add_argument("--node-min", metavar="VERSION", default="",
                        help="Version Node.js minimale requise")
    return parser.parse_args()


def main():
    args = parse_args()
    erreurs = 0
    avertissements = 0

    print(f"\n{gras('=== Verificateur d\'environnement ===')}")

    # ── Venv
    venv = verifier_venv()
    if venv:
        print(f"\n  {vert(venv)}")
    else:
        print(f"\n  {jaune('Aucun environnement virtuel actif detecto')}")

    # ── Outils principaux
    outils_base = [
        ("python",  "--version", args.python_min),
        ("pip",     "--version", ""),
        ("git",     "--version", ""),
        ("node",    "--version", args.node_min),
        ("npm",     "--version", ""),
    ]
    if args.outils:
        for outil in args.outils:
            outils_base.append((outil, "--version", ""))

    afficher_section("Outils")
    for nom, version, version_min, ok in verifier_outils(outils_base):
        afficher_outil(nom, version, version_min, ok)
        if not ok and nom in ("python", "pip", "git"):
            erreurs += 1
        elif not ok:
            avertissements += 1

    # ── Paquets Python
    req_path = Path(args.requirements)
    if req_path.exists():
        afficher_section(f"Paquets Python ({req_path})")
        resultats = verifier_paquets(req_path)
        for nom, version, specif, ok in resultats:
            afficher_paquet(nom, version, specif, ok)
            if not ok:
                erreurs += 1
        if not resultats:
            print(dim("  (fichier vide ou aucun paquet reconnu)"))
    else:
        afficher_section("Paquets Python")
        print(jaune(f"  Fichier {req_path} introuvable."))

    # ── Variables d'environnement
    if args.env_exemple:
        env_path = Path(args.env_exemple)
        if env_path.exists():
            afficher_section(f"Variables d'environnement ({env_path})")
            resultats_env = verifier_env(env_path)
            for nom, existe, optionnel in resultats_env:
                afficher_var_env(nom, existe, optionnel)
                if not existe and not optionnel:
                    erreurs += 1
                elif not existe and optionnel:
                    avertissements += 1
            if not resultats_env:
                print(dim("  (aucune variable trouvee dans le fichier)"))
        else:
            print(jaune(f"\n  Fichier {env_path} introuvable."))

    # ── Resume
    print(f"\n{gras('─' * 64)}")
    if erreurs == 0 and avertissements == 0:
        print(vert(f"  Environnement valide — aucun probleme detecte."))
    else:
        if erreurs:
            print(rouge(f"  {erreurs} erreur(s) critique(s)"))
        if avertissements:
            print(jaune(f"  {avertissements} avertissement(s)"))

    sys.exit(0 if erreurs == 0 else 1)


if __name__ == "__main__":
    main()
