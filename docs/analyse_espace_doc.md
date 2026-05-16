# 📈 analyse_espace.py — Documentation

Script Python d'analyse de l'utilisation de l'espace disque d'un dossier.  
Affiche les sous-dossiers classés par taille décroissante avec **barres de progression ASCII colorées**.  
Inspiré de l'outil `ncdu` (NCurses Disk Usage), entièrement en Python, sans interface interactive.

---

## 📦 Dépendances

| Dépendance | Rôle | Obligatoire |
|------------|------|-------------|
| `colorama` | Couleurs dans le terminal | Non — fonctionne sans, affichage en noir et blanc |

```bash
pip install colorama
```

---

## 🚀 Utilisation de base

```bash
python analyse_espace.py                    # analyse le dossier courant
python analyse_espace.py /chemin/dossier    # analyse un dossier spécifique
python analyse_espace.py ~/Documents        # exemple
```

Le script scanne récursivement tout le dossier, calcule la taille cumulée de chaque sous-dossier, puis affiche le classement trié par taille décroissante.

---

## ⚙️ Arguments disponibles

### Argument de position

| Argument | Description | Défaut |
|----------|-------------|--------|
| `dossier` | Chemin du dossier à analyser | `.` (dossier courant) |

---

### Options

#### `-n N` ou `--top N` — Nombre d'entrées à afficher

Limite le classement aux N dossiers les plus lourds.

```bash
python analyse_espace.py ~/Documents -n 30
```

> Défaut : **20**

---

#### `-p N` ou `--profondeur N` — Profondeur d'analyse

Contrôle jusqu'à quel niveau de sous-dossiers le script descend pour créer des entrées dans le classement.

| Profondeur | Dossiers indexés |
|------------|-----------------|
| `1` | Uniquement les sous-dossiers directs de la racine |
| `2` | Sous-dossiers et sous-sous-dossiers (défaut) |
| `3` | Trois niveaux de profondeur |

> Quelle que soit la profondeur, **tous les fichiers** sont comptabilisés pour calculer les tailles (le scan reste toujours récursif jusqu'au fond). Seule l'affichage dans le tableau est limité.

```bash
# Vue rapide : seulement les dossiers directs
python analyse_espace.py ~/Documents -p 1

# Vue détaillée : 3 niveaux
python analyse_espace.py ~/Documents -p 3 -n 50
```

> Défaut : **2**

---

#### `-f` ou `--fichiers` — Inclure les fichiers individuels

Par défaut, seuls les **dossiers** apparaissent dans le classement.  
Avec `--fichiers`, les gros fichiers individuels sont aussi inclus dans la liste triée.

```bash
python analyse_espace.py ~/Documents --fichiers
```

Utile pour repérer les fichiers isolés qui prennent beaucoup de place (archives, images lourdes, vidéos).

> Chaque entrée est préfixée de `D` (dossier) ou `F` (fichier) pour les distinguer.

---

#### `-w N` ou `--largeur N` — Largeur de la barre de progression

Ajuste le nombre de caractères de la barre ASCII.

```bash
python analyse_espace.py . -w 50
```

> Défaut : **30** caractères

---

## 📊 Lecture du tableau

### Exemple de sortie

```
ANALYSE ESPACE : Documents
=========================================================================
Chemin   : /home/user/Documents
Total    : 4.2 Go  (1 247 fichier(s))
Barre    : 100% = 4.2 Go

    Taille    Part  Fichiers  Proportion                      Chemin
──────────  ──────  ────────  ──────────────────────────────  ──────────────────
   2.1 Go   50.0%      312  [###############...............]  D  Vidéo
   1.3 Go   30.9%      487  [#########.....................]  D  Photos
 480.0 Mo   11.2%       28  [###...........................]  D  Archives
  84.0 Mo    2.0%      215  [#.............................]  D  Cours
    ...
```

### Colonnes

| Colonne | Description |
|---------|-------------|
| **Taille** | Taille cumulée du dossier (tous ses fichiers, récursivement) |
| **Part** | Pourcentage de la taille totale |
| **Fichiers** | Nombre de fichiers dans ce dossier (récursivement) |
| **Proportion** | Barre ASCII visuelle proportionnelle à la taille |
| **Chemin** | Chemin relatif depuis la racine analysée, précédé de `D` (dossier) ou `F` (fichier) |

---

## 🎨 Code couleur

| Couleur | Seuil | Signification |
|---------|-------|---------------|
| **Rouge** | ≥ 30% du total | Dossier très volumineux — premier candidat à l'attention |
| **Jaune** | ≥ 10% du total | Dossier significatif |
| **Vert** | ≥ 1% du total | Dossier de taille modérée |
| **Grisé** | < 1% du total | Dossier marginal |

---

## 📌 Résumé affiché en bas

Après le tableau, le script affiche une ligne de synthèse :

```
Les 3 plus gros éléments représentent 3.9 Go (92.8% du total)
```

Cela permet de savoir rapidement si l'espace est concentré dans quelques gros dossiers ou réparti uniformément.

---

## 💡 Exemples complets

```bash
# Vue rapide du dossier courant
python analyse_espace.py

# Analyser les Téléchargements, afficher 30 dossiers
python analyse_espace.py ~/Téléchargements -n 30

# Vue à 3 niveaux de profondeur
python analyse_espace.py ~/Documents -p 3 -n 40

# Inclure les gros fichiers dans le classement
python analyse_espace.py ~/Photos --fichiers

# Barre plus large pour un grand terminal
python analyse_espace.py . -w 50 -n 25

# Analyser un disque entier (profondeur 1 — rapide)
python analyse_espace.py C:/ -p 1 -n 30

# Vue complète : profondeur 3, 50 entrées, fichiers inclus
python analyse_espace.py ~/Documents -p 3 -n 50 --fichiers
```

---

## ⚠️ Comportements importants

- Les **liens symboliques** sont ignorés (pour éviter les boucles et les doubles comptages).
- Les dossiers **sans permission de lecture** sont ignorés silencieusement — leur taille peut donc être sous-estimée.
- La **taille affichée** est la taille réelle des fichiers en octets, **pas la taille sur disque** (qui dépend de la taille des clusters du système de fichiers et peut être légèrement différente).
- La profondeur contrôle uniquement **l'affichage** dans le tableau — le scan reste toujours complet. Une profondeur de 1 est donc aussi lente qu'une profondeur de 3, mais affiche moins d'entrées.
- Sur de **très gros dossiers** (> 100 000 fichiers), le scan peut prendre plusieurs secondes à quelques minutes selon le débit disque. Un compteur s'affiche toutes les 500 entrées.
- Les **fichiers à la racine** analysée (pas dans des sous-dossiers) sont comptabilisés dans le total mais n'apparaissent pas comme entrée séparée dans le tableau — à moins d'utiliser `--fichiers`.
