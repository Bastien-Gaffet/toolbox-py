# 🧰 toolbox.py — Documentation

Lanceur interactif de toute la boîte à outils. Un menu à flèches (Rich + questionary)
qui découvre automatiquement les scripts, les regroupe par catégorie et lance celui
choisi — **sans avoir à retenir les commandes ni les arguments**.

---

## 📦 Dépendances

```bash
pip install rich questionary
```

---

## 🚀 Lancement

```bash
python toolbox.py
```

Aucun argument. Le lanceur est purement interactif.

---

## 📦 Vérification des dépendances au démarrage

Au lancement, `toolbox.py` lit `requirements.txt` et vérifie quels paquets sont
installés (via `importlib.metadata`, donc par nom de distribution PyPI — pas de souci
avec `Pillow`/`PIL` etc.). S'il en manque, il les liste et propose de **tout installer
en une fois** avec pip :

```
Dépendances manquantes : piexif, python-docx
» Installer maintenant (2) avec pip ?  (O/n)
```

- **Oui** → `pip install piexif python-docx` puis retour au menu.
- **Non** → on continue quand même ; la commande d'installation est rappelée.

Ainsi, plus besoin d'installer les dépendances à la main avant d'utiliser un outil
(ex. `piexif` pour `photos_manager.py`). Les outils externes non-Python (`ffmpeg`,
`adb`) ne sont **pas** gérés par pip et restent à installer séparément.

---

## 🧭 Fonctionnement

```
Catégorie  →  Outil  →  Action (Lancer / Voir l'aide / Retour)  →  Arguments  →  Exécution
```

1. **Catégorie** — les mêmes catégories que le README (Fichiers & Dossiers, Réseau, Sécurité…).
2. **Outil** — la liste des scripts de la catégorie, avec leur description.
3. **Action** :
   - **▶ Lancer** — demande la ligne d'arguments, puis exécute le script.
   - **❔ Voir l'aide** — affiche le `--help` du script.
   - **↩ Retour** — remonte d'un niveau.
4. **Arguments** — on tape la ligne comme en CLI, ex : `"D:\Photos" --simulation`.
   Les chemins Windows avec `\` et les guillemets sont gérés correctement.

Le script sélectionné tourne dans le même terminal (les scripts interactifs, barres de
progression, invites `[o/N]`… fonctionnent normalement). À la fin, on revient au menu.

---

## ⚙️ Découverte automatique des outils

Le lanceur **lit `README.md`** : chaque ligne de tableau
`| [`script.py`](script.py) | Description |` sous un titre `### Catégorie` devient une
entrée du menu.

Conséquences pratiques :

- **Ajouter un outil** = l'ajouter au tableau du README + déposer son `.py`. Rien à
  modifier dans `toolbox.py`.
- Les entrées marquées *(à venir)* dont le fichier `.py` n'existe pas encore sont
  **automatiquement ignorées**.
- `toolbox.py` ne se liste jamais lui-même.

---

## 🎨 Interface

- **Rich** — bannière, panneaux, filets colorés, rendu UTF-8 propre (émojis inclus).
- **questionary** — menus à flèches, filtrage en tapant, style accordé à la charte du projet.

---

## 🧩 Socle partagé

La découverte des outils, la vérification des dépendances et l'exécution vivent dans
[`toolbox_core.py`](toolbox_core.py) (stdlib pure). `toolbox.py` (ce lanceur terminal)
et [`toolbox_gui.py`](toolbox_gui.py) (interface graphique PySide6) s'appuient tous deux
dessus — voir [`toolbox_gui_doc.md`](toolbox_gui_doc.md).
