#!/usr/bin/env python3
"""
toolbox.py
Lanceur interactif de toute la boite a outils.

Menu a fleches (Rich + questionary) qui decouvre automatiquement les scripts
en lisant le tableau du README.md, les regroupe par categorie, et lance
l'outil choisi via subprocess (aucune modification des scripts existants).

Ajouter un nouvel outil = l'ajouter au README + deposer son .py. Rien a coder ici.

Usage :
    python toolbox.py

Dependances :
    pip install rich questionary
"""

import re
import sys
import shlex
import subprocess
import importlib.metadata as md
from pathlib import Path

RACINE = Path(__file__).resolve().parent
README = RACINE / "README.md"
REQUIREMENTS = RACINE / "requirements.txt"

# ─── Dependances (message clair si absentes) ─────────────────────────────────
try:
    import questionary
    from questionary import Choice, Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except ImportError:
    print(
        "\nDependances manquantes pour le lanceur.\n"
        "  Installez-les avec :  pip install rich questionary\n"
    )
    sys.exit(1)

console = Console()

# Style questionary accorde a la charte terminal du projet
STYLE = Style([
    ("qmark",       "fg:#5fd7ff bold"),
    ("question",    "bold"),
    ("pointer",     "fg:#5fd7ff bold"),
    ("highlighted", "fg:#5fd7ff bold"),
    ("selected",    "fg:#5fff87"),
    ("answer",      "fg:#5fff87 bold"),
])


# ═══════════════════════════════════════════════════════════════════════════
# DECOUVERTE DES OUTILS (parse le README)
# ═══════════════════════════════════════════════════════════════════════════

RE_CATEGORIE = re.compile(r"^###\s+(.+?)\s*$")
# | [`script.py`](script.py) | Description |
RE_OUTIL = re.compile(r"^\|\s*\[`([^`]+\.py)`\]\([^)]+\)\s*\|\s*(.+?)\s*\|\s*$")


def charger_outils() -> dict:
    """
    Lit README.md et retourne {categorie: [(script, description), ...]}.
    Ne garde que les scripts reellement presents sur le disque
    (les entrees marquees « a venir » sont ainsi ecartees).
    """
    if not README.exists():
        console.print(f"[red]README.md introuvable a cote de toolbox.py[/red]")
        sys.exit(1)

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
            # Nettoyer les mentions type *(a venir)* et les liens markdown residuels
            desc = re.sub(r"\*\(.*?\)\*", "", desc).strip()
            if script == Path(__file__).name:
                continue
            if (RACINE / script).exists():
                outils.setdefault(categorie, []).append((script, desc))

    # Ne garder que les categories non vides
    return {cat: lst for cat, lst in outils.items() if lst}


# ═══════════════════════════════════════════════════════════════════════════
# DEPENDANCES (verifie requirements.txt, propose d'installer les manquantes)
# ═══════════════════════════════════════════════════════════════════════════

def paquets_requis() -> list:
    """Lit requirements.txt et retourne les noms de paquets (sans versions ni commentaires)."""
    if not REQUIREMENTS.exists():
        return []
    noms = []
    for ligne in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if not ligne:
            continue
        # Retire specificateurs de version/extras : Pillow>=10, paquet[extra], etc.
        nom = re.split(r"[<>=!~;\[\s]", ligne, maxsplit=1)[0].strip()
        if nom:
            noms.append(nom)
    return noms


def paquets_manquants() -> list:
    """Retourne les paquets de requirements.txt qui ne sont pas installes."""
    manquants = []
    for nom in paquets_requis():
        try:
            md.version(nom)          # verifie par nom de distribution PyPI
        except md.PackageNotFoundError:
            manquants.append(nom)
    return manquants


def installer(paquets: list) -> bool:
    """Installe une liste de paquets via pip. Retourne True si succes."""
    commande = [sys.executable, "-m", "pip", "install", *paquets]
    console.print(f"\n[dim]$ {' '.join(commande)}[/dim]\n")
    console.rule(style="cyan")
    code = subprocess.run(commande).returncode
    console.rule(style="cyan")
    if code == 0:
        console.print("[green]✓ Dépendances installées.[/green]\n")
        return True
    console.print("[red]✗ Échec de l'installation (voir le détail ci-dessus).[/red]\n")
    return False


def verifier_dependances():
    """Au demarrage : signale les paquets manquants et propose de les installer."""
    manquants = paquets_manquants()
    if not manquants:
        return
    console.print(Panel(
        "[yellow]Dépendances manquantes :[/yellow] "
        + ", ".join(f"[bold]{p}[/bold]" for p in manquants)
        + "\n[dim]Certains outils ne fonctionneront pas sans elles "
          "(ex. psutil pour moniteur_systeme).[/dim]",
        border_style="yellow", box=box.ROUNDED,
    ))
    rep = questionary.confirm(
        f"Installer maintenant ({len(manquants)}) avec pip ?",
        default=True, style=STYLE, qmark="»",
    ).ask()
    if rep:
        installer(manquants)
    else:
        console.print("[dim]Ignoré — installable plus tard : "
                      f"pip install {' '.join(manquants)}[/dim]\n")


# ═══════════════════════════════════════════════════════════════════════════
# AFFICHAGE
# ═══════════════════════════════════════════════════════════════════════════

def banniere(outils: dict):
    total = sum(len(v) for v in outils.values())
    console.print(Panel.fit(
        f"[bold cyan]🧰  toolbox-py[/bold cyan]\n"
        f"[dim]{total} outils · {len(outils)} categories[/dim]",
        box=box.ROUNDED, border_style="cyan",
    ))


def couper(texte: str, largeur: int) -> str:
    return texte if len(texte) <= largeur else texte[: largeur - 1] + "…"


# ═══════════════════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

def decouper_args(chaine: str) -> list:
    """
    Decoupe une ligne d'arguments en preservant les backslashes Windows
    (chemins D:\\dossier) et en retirant les guillemets englobants.
    """
    if not chaine.strip():
        return []
    tokens = shlex.split(chaine, posix=False)
    nettoyes = []
    for t in tokens:
        if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
            t = t[1:-1]
        nettoyes.append(t)
    return nettoyes


def lancer(script: str, args: list):
    """Lance `python <script> <args>` en heritant du terminal (scripts interactifs OK)."""
    commande = [sys.executable, str(RACINE / script), *args]
    console.print(f"\n[dim]$ python {script} {' '.join(args)}[/dim]\n")
    console.rule(style="cyan")
    try:
        code = subprocess.run(commande).returncode
    except KeyboardInterrupt:
        console.print("\n[yellow]Outil interrompu.[/yellow]")
        return
    console.rule(style="cyan")
    if code == 0:
        console.print(f"[green]✓ {script} termine.[/green]")
    else:
        console.print(f"[red]✗ {script} s'est termine avec le code {code}.[/red]")


def menu_outil(script: str, desc: str):
    """Sous-menu d'un outil : lancer, voir l'aide, ou revenir."""
    while True:
        console.print(Panel(
            f"[bold]{script}[/bold]\n[dim]{desc}[/dim]",
            border_style="cyan", box=box.ROUNDED,
        ))
        action = questionary.select(
            "Action :",
            choices=[
                Choice("▶  Lancer", "run"),
                Choice("❔  Voir l'aide (--help)", "help"),
                Choice("↩  Retour", "back"),
            ],
            style=STYLE, qmark="»",
        ).ask()

        if action in (None, "back"):
            return
        if action == "help":
            lancer(script, ["--help"])
            questionary.text("Entree pour continuer…", style=STYLE, qmark=" ").ask()
        elif action == "run":
            brut = questionary.text(
                "Arguments (vide = aucun, ex: \"D:\\Photos\" --simulation) :",
                style=STYLE, qmark="»",
            ).ask()
            if brut is None:
                return
            lancer(script, decouper_args(brut))
            questionary.text("Entree pour revenir au menu…", style=STYLE, qmark=" ").ask()
            return


def menu_categorie(categorie: str, liste: list):
    largeur = max(20, console.width - 40)
    while True:
        choices = [
            Choice(f"{script:<26} {couper(desc, largeur)}", value=(script, desc))
            for script, desc in liste
        ]
        choices.append(Choice("↩  Retour", value="back"))
        rep = questionary.select(
            f"{categorie} :", choices=choices, style=STYLE, qmark="»",
        ).ask()
        if rep in (None, "back"):
            return
        menu_outil(*rep)


def menu_principal(outils: dict):
    while True:
        choices = [
            Choice(f"{cat}  ({len(lst)})", value=cat)
            for cat, lst in outils.items()
        ]
        choices.append(Choice("✖  Quitter", value="quit"))
        cat = questionary.select(
            "Categorie :", choices=choices, style=STYLE, qmark="»",
        ).ask()
        if cat in (None, "quit"):
            console.print("\n[cyan]A bientot ![/cyan]\n")
            return
        menu_categorie(cat, outils[cat])


# ═══════════════════════════════════════════════════════════════════════════
# POINT D'ENTREE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    outils = charger_outils()
    if not outils:
        console.print("[yellow]Aucun outil detecte dans le README.[/yellow]")
        return
    console.clear()
    banniere(outils)
    try:
        verifier_dependances()
        menu_principal(outils)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompu.[/yellow]\n")
    except Exception as e:
        # Cas typique : terminal non compatible (Git Bash/MSYS, entree redirigee).
        if "console" in str(e).lower() or e.__class__.__name__ == "NoConsoleScreenBufferError":
            console.print(
                "\n[red]Terminal non compatible avec le menu interactif.[/red]\n"
                "[yellow]Lancez le lanceur dans PowerShell ou cmd.exe :[/yellow]\n"
                "    python toolbox.py\n"
                "[dim](Git Bash / MSYS et les entrees redirigees ne sont pas supportes "
                "par le menu a fleches.)[/dim]\n"
            )
        else:
            raise


if __name__ == "__main__":
    main()
