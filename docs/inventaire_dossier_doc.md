# 📊 inventaire_dossier.py — Documentation

Script Python d'analyse complète d'un dossier : taille par type de fichier, fichiers les plus lourds, répartition par date.  
Export optionnel en CSV et en HTML autonome (dark theme, ouvrable dans n'importe quel navigateur).

---

## 📦 Dépendances

| Dépendance | Rôle | Obligatoire |
|------------|------|-------------|
| `colorama` | Couleurs dans le terminal | Non — fonctionne sans, affichage en noir et blanc |

```bash
pip install colorama
```

Ou via le fichier global :

```bash
pip install -r requirements.txt
```

---

## 🚀 Utilisation de base

```bash
python inventaire_dossier.py                        # analyse le dossier courant
python inventaire_dossier.py /chemin/vers/dossier   # analyse un dossier spécifique
python inventaire_dossier.py ~/Téléchargements      # exemple : dossier Téléchargements
```

Le script scanne récursivement tous les fichiers du dossier et affiche un rapport structuré en plusieurs sections.

---

## ⚙️ Arguments disponibles

### Argument de position

| Argument | Description | Défaut |
|----------|-------------|--------|
| `dossier` | Chemin du dossier à analyser | `.` (dossier courant) |

---

### Options

#### `-t N` ou `--top N` — Nombre de fichiers à afficher

Détermine combien de fichiers apparaissent dans la section "Top fichiers les plus lourds".

```bash
python inventaire_dossier.py . --top 50
```

> Défaut : **20**

---

#### `--csv FICHIER` — Export CSV

Génère un fichier CSV structuré en 4 sections :

1. **Résumé** — dossier analysé, nombre de fichiers, taille totale, date de génération
2. **Par type** — une ligne par catégorie avec nombre de fichiers, taille en octets, taille lisible et part en pourcentage
3. **Top N fichiers** — rang, taille, chemin relatif
4. **Liste complète** — tous les fichiers triés par taille décroissante avec extension, catégorie, taille, date de modification

```bash
python inventaire_dossier.py ~/Documents --csv inventaire.csv
```

Le séparateur utilisé est le **point-virgule** (`;`) pour une compatibilité optimale avec LibreOffice Calc et Excel.

---

#### `--html FICHIER` — Export HTML

Génère un fichier HTML **autonome** (CSS intégré, aucune dépendance externe) en thème sombre.  
Ouvrable directement dans un navigateur web, sans serveur.

Contenu du fichier HTML :
- En-tête avec chemin analysé, nombre de fichiers, taille totale, date de génération
- Tableau "Par type" avec barres de proportion visuelles
- Tableau "Top N fichiers les plus lourds"
- Tableau "Répartition par année"

```bash
python inventaire_dossier.py ~/Documents --html rapport.html
```

> **Astuce** : combiner `--csv` et `--html` pour avoir les deux formats en une seule passe.

```bash
python inventaire_dossier.py . --csv inv.csv --html inv.html
```

---

#### `-q` ou `--silencieux` — Résumé uniquement

Affiche uniquement le tableau "Par type de fichier" dans le terminal, sans le top fichiers ni la répartition par date.  
Utile pour un aperçu rapide.

```bash
python inventaire_dossier.py ~/Documents -q
```

---

#### `--sans-recursif` — Non récursif

Analyse uniquement les fichiers directement à la racine du dossier (sans descendre dans les sous-dossiers).

```bash
python inventaire_dossier.py ~/Documents --sans-recursif
```

---

## 📂 Sections du rapport

### 1. En-tête

Informations générales sur le dossier analysé :

```
INVENTAIRE : Documents
=================================================================
Chemin      : /home/user/Documents
Fichiers    : 1 247
Taille tot. : 4.2 Go
Période     : 2019-03-12  →  2026-04-30
```

---

### 2. Par type de fichier

Tableau récapitulatif par catégorie avec barres de proportion :

```
Catégorie           Fichiers       Taille    Part  Proportion
──────────────────  ───────  ────────────  ─────  ──────────────────────────
PDF                     312       2.1 Go   50.0%  [############............]
Images                  487       1.3 Go   30.9%  [########................]
Vidéo                    28       0.5 Go   11.9%  [###.....................]
Texte                   215      80.4 Mo    1.9%  [........................]
...
```

#### Catégories reconnues

| Catégorie | Extensions principales |
|-----------|------------------------|
| PDF | `.pdf` |
| Texte | `.doc`, `.docx`, `.odt`, `.txt`, `.md`, `.tex`, `.rtf`, `.pages`… |
| Tableurs | `.xls`, `.xlsx`, `.ods`, `.csv`, `.numbers`… |
| Présentations | `.ppt`, `.pptx`, `.odp`, `.key` |
| Images | `.jpg`, `.png`, `.gif`, `.webp`, `.heic`, `.raw`, `.cr2`, `.svg`… |
| Audio | `.mp3`, `.flac`, `.wav`, `.aac`, `.ogg`, `.m4a`… |
| Vidéo | `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.mpg`… |
| Archives | `.zip`, `.rar`, `.7z`, `.tar.gz`, `.iso`, `.dmg`… |
| Exécutables | `.exe`, `.msi`, `.deb`, `.rpm`, `.apk`, `.sh`… |
| Code | `.py`, `.js`, `.ts`, `.html`, `.css`, `.java`, `.go`, `.rs`… |
| Données | `.json`, `.xml`, `.yaml`, `.ini`, `.log`… |
| Polices | `.ttf`, `.otf`, `.woff`, `.woff2` |
| **Autres** | Toute extension non reconnue |

---

### 3. Top N fichiers les plus lourds

```
TOP 20 FICHIERS LES PLUS LOURDS
─────────────────────────────────────────────────────────────────
    1.      1.8 Go  Vidéo/formation_python.mp4
    2.    450.3 Mo  Archives/backup_2024.zip
    3.    210.0 Mo  Images/panorama_raw.cr2
  ...
```

---

### 4. Répartition par année

Basée sur la **date de dernière modification** de chaque fichier :

```
RÉPARTITION PAR ANNÉE
─────────────────────────────────────────────────────────────────
Année  Fichiers       Taille  Part  Proportion
─────  ────────  ──────────  ─────  ──────────────────────────
 2025       412    2.0 Go   47.6%  [############............]
 2024       318    1.5 Go   35.7%  [#########...............]
 2023       201    0.5 Go   11.9%  [###.....................]
 2022       316    0.2 Go    4.8%  [#.......................]
```

---

## 💡 Exemples complets

```bash
# Aperçu rapide du dossier courant
python inventaire_dossier.py -q

# Rapport complet avec export HTML
python inventaire_dossier.py ~/Téléchargements --html tele.html

# Top 50 fichiers + export CSV pour analyse dans un tableur
python inventaire_dossier.py ~/Documents --top 50 --csv doc.csv

# Analyser un seul niveau sans sous-dossiers, export HTML
python inventaire_dossier.py ~/Photos --sans-recursif --html photos.html

# Double export en une passe
python inventaire_dossier.py . --top 30 --csv inv.csv --html inv.html
```

---

## ⚠️ Comportements importants

- Les **liens symboliques** sont ignorés (pour éviter les boucles infinies).
- Les fichiers **sans permission de lecture** sont ignorés silencieusement.
- La **date utilisée** pour la répartition est la date de **dernière modification** du fichier, pas la date de création.
- L'export HTML est **entièrement autonome** : il n'y a aucun lien externe, aucun CDN — le fichier reste lisible sans connexion.
