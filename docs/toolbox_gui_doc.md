# 🖥️ toolbox_gui.py — Documentation

Interface **graphique** (PySide6) de la boîte à outils. Liste tous les outils,
permet de saisir les arguments et affiche la sortie du programme en direct.

Partage le même socle [`toolbox_core.py`](../toolbox_core.py) que le lanceur en
terminal `toolbox.py` : même découverte des outils, mêmes dépendances, même exécution.

---

## 📦 Dépendances

```bash
pip install PySide6
```

---

## 🚀 Lancement

```bash
python toolbox_gui.py
```

Contrairement au lanceur terminal, la GUI fonctionne partout (y compris depuis Git Bash).

---

## 🧭 Interface

```
┌─ 🧰 toolbox-py · 24 outils ──────┬─ nom_de_l_outil ───────────────────┐
│ 🔎 Filtrer…                      │ description de l'outil             │
│ ▾ 🗂️ Fichiers & Dossiers  (6)    │ [ Arguments…        ] ▶ Lancer ❔ ⏹ │
│    ranger_dossier.py             │ ┌─ sortie du programme ─────────┐  │
│    nettoyer_dossier.py           │ │ $ python ranger_dossier.py …  │  │
│ ▸ 🌐 Réseau & Web  (4)           │ │ …                             │  │
│ …                                │ └───────────────────────────────┘  │
│                                  │ [ ↳ répondre au programme… ] Envoyer│
└──────────────────────────────────┴─────────────────────────────────────┘
```

- **Gauche** — champ de filtre + arbre des outils groupés par catégorie
  (celles du README). Double-clic sur un outil = le lancer directement.
- **Droite** — nom + description de l'outil sélectionné, ligne d'**arguments**,
  boutons **Lancer / Aide (--help) / Arrêter**, puis la **sortie en direct**.
- **Bas** — une ligne pour **répondre au programme** quand il pose une question
  (invites type `[o/N]`, saisie interactive…). Tape la réponse, Entrée.

---

## ⚙️ Comment ça marche

- Chaque outil est lancé dans un **QProcess** séparé (`python <script> <args>`),
  sans modifier les scripts. La sortie standard et d'erreur sont fusionnées et
  affichées au fil de l'eau.
- L'environnement force l'UTF-8 (`PYTHONUTF8=1`) pour les accents et emojis.
- **Arrêter** tue le processus en cours ; les boutons se réactivent à la fin.
- Si des **dépendances manquent** (lues dans `requirements.txt`), un bandeau
  jaune s'affiche en haut avec un bouton **Installer** (lance `pip install`).

---

## 🧩 Architecture partagée

```
toolbox_core.py   ← découverte (README), dépendances, exécution   (stdlib pure)
   ├── toolbox.py       ← interface terminal (Rich + questionary)
   └── toolbox_gui.py   ← interface graphique (PySide6)
```

Ajouter un outil au README (et déposer son `.py`) le fait apparaître
**automatiquement** dans les deux interfaces — rien à coder dans le socle.

---

## ⚠️ Notes

- Les outils pilotés par **arguments** (la plupart, avec `--simulation`, options…)
  sont idéaux pour la GUI. Les scripts **purement interactifs** restent utilisables
  grâce à la ligne « répondre au programme », mais un script qui teste `isatty()`
  peut se comporter différemment (il se sait non lancé depuis un vrai terminal).
- Pour empaqueter la GUI en `.exe` autonome plus tard : PyInstaller
  (`pyinstaller --noconsole --onefile toolbox_gui.py`).
