#!/usr/bin/env python3
"""
toolbox_core.py
Socle partagé par les interfaces de la boîte à outils (CLI `toolbox.py` et
GUI `toolbox_gui.py`).

Ne dépend que de la bibliothèque standard. Fournit :
  - la découverte des outils en lisant le tableau du README ;
  - la vérification des dépendances (requirements.txt) ;
  - le découpage d'une ligne d'arguments (compatible chemins Windows) ;
  - la construction de la commande d'exécution d'un outil.

Aucune interface ici : ni rich, ni questionary, ni PySide6.
"""

import re
import sys
import shlex
import importlib.metadata as md
from pathlib import Path

RACINE = Path(__file__).resolve().parent
README = RACINE / "README.md"
REQUIREMENTS = RACINE / "requirements.txt"

# Noms des fichiers d'interface, exclus de la liste des outils.
_INTERFACES = {"toolbox.py", "toolbox_core.py", "toolbox_gui.py"}


# ═══════════════════════════════════════════════════════════════════════════
# DÉCOUVERTE DES OUTILS (parse le README)
# ═══════════════════════════════════════════════════════════════════════════

RE_CATEGORIE = re.compile(r"^###\s+(.+?)\s*$")
# | [`script.py`](script.py) | Description |
RE_OUTIL = re.compile(r"^\|\s*\[`([^`]+\.py)`\]\([^)]+\)\s*\|\s*(.+?)\s*\|\s*$")


def charger_outils() -> dict:
    """
    Lit README.md et retourne {categorie: [(script, description), ...]}.
    Ne garde que les scripts réellement présents sur le disque
    (les entrées « à venir » sans fichier sont ainsi écartées).
    """
    if not README.exists():
        return {}

    outils: dict = {}
    categorie = None
    for ligne in README.read_text(encoding="utf-8").splitlines():
        m_cat = RE_CATEGORIE.match(ligne)
        if m_cat:
            categorie = m_cat.group(1)
            continue
        m_out = RE_OUTIL.match(ligne)
        if m_out and categorie:
            script, desc = m_out.group(1), m_out.group(2)
            desc = re.sub(r"\*\(.*?\)\*", "", desc).strip()
            if script in _INTERFACES:
                continue
            if (RACINE / script).exists():
                outils.setdefault(categorie, []).append((script, desc))

    return {cat: lst for cat, lst in outils.items() if lst}


# ═══════════════════════════════════════════════════════════════════════════
# DÉPENDANCES
# ═══════════════════════════════════════════════════════════════════════════

def paquets_requis() -> list:
    """Noms de paquets listés dans requirements.txt (sans versions ni commentaires)."""
    if not REQUIREMENTS.exists():
        return []
    noms = []
    for ligne in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if not ligne:
            continue
        nom = re.split(r"[<>=!~;\[\s]", ligne, maxsplit=1)[0].strip()
        if nom:
            noms.append(nom)
    return noms


def paquets_manquants() -> list:
    """Paquets de requirements.txt non installés (vérif par nom de distribution PyPI)."""
    manquants = []
    for nom in paquets_requis():
        try:
            md.version(nom)
        except md.PackageNotFoundError:
            manquants.append(nom)
    return manquants


def commande_pip_install(paquets: list) -> list:
    """Commande pip pour installer une liste de paquets."""
    return [sys.executable, "-m", "pip", "install", *paquets]


# ═══════════════════════════════════════════════════════════════════════════
# EXÉCUTION
# ═══════════════════════════════════════════════════════════════════════════

def decouper_args(chaine: str) -> list:
    """
    Découpe une ligne d'arguments en préservant les backslashes Windows
    (chemins D:\\dossier) et en retirant les guillemets englobants.
    """
    if not chaine or not chaine.strip():
        return []
    tokens = shlex.split(chaine, posix=False)
    nettoyes = []
    for t in tokens:
        if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
            t = t[1:-1]
        nettoyes.append(t)
    return nettoyes


def commande_pour(script: str, args: list) -> list:
    """Construit la commande d'exécution d'un outil : [python, chemin_script, *args]."""
    return [sys.executable, str(RACINE / script), *args]
