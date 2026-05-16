# 🔄 comparateur_dossiers.py — Documentation

Script Python de comparaison de deux dossiers : identifie les fichiers identiques, modifiés ou manquants dans l'un ou l'autre.  
Idéal pour **vérifier l'intégrité d'une sauvegarde**, détecter des divergences entre deux emplacements de stockage, ou auditer une synchronisation.

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
python comparateur_dossiers.py <dossier_a> <dossier_b>
```

**Dossier A** est la référence (source), **dossier B** est l'élément à comparer (sauvegarde, copie, etc.).  
La distinction A/B n'a d'importance que pour les catégories "seulement dans A" et "seulement dans B".

```bash
python comparateur_dossiers.py ~/Documents ~/Backup/Documents
python comparateur_dossiers.py . /media/disque_externe/sauvegarde
```

---

## ⚙️ Arguments disponibles

### Arguments de position

| Argument | Description |
|----------|-------------|
| `dossier_a` | Premier dossier — référence A |
| `dossier_b` | Second dossier — référence B |

---

### Options

#### `--rapide` — Comparaison par taille (sans hash)

Par défaut, le script calcule un **hash SHA-256** de chaque fichier pour une comparaison exacte du contenu.  
Avec `--rapide`, il compare uniquement la **taille en octets**, ce qui est beaucoup plus rapide mais peut produire de faux positifs (deux fichiers différents mais de même taille seraient classés "identiques").

| Mode | Méthode | Vitesse | Précision |
|------|---------|---------|-----------|
| Défaut | SHA-256 | Plus lent | Exacte — détecte même 1 bit modifié |
| `--rapide` | Taille seule | Très rapide | Approximative |

```bash
# Mode précis (défaut) — recommandé pour les sauvegardes importantes
python comparateur_dossiers.py ~/Documents ~/Backup

# Mode rapide — pour les grands volumes ou une vérification rapide
python comparateur_dossiers.py ~/Documents ~/Backup --rapide
```

> **Conseil** : utiliser `--rapide` pour un premier tri sur de gros volumes, puis relancer sans `--rapide` sur les dossiers suspects.

---

#### `--csv FICHIER` — Export CSV

Génère un fichier CSV avec :

1. **En-tête** — chemins des deux dossiers, date de génération
2. **Résumé** — nombre de fichiers par catégorie
3. **Détail** — une ligne par fichier avec statut, chemin, taille A, taille B, date A, date B

```bash
python comparateur_dossiers.py A B --csv rapport_diff.csv
```

---

#### `--html FICHIER` — Export HTML

Génère un fichier HTML **autonome** (CSS intégré, thème sombre) avec :

- Résumé des 4 catégories
- Tableau des fichiers modifiés (avec tailles et dates des deux versions)
- Tableau des fichiers seulement dans A
- Tableau des fichiers seulement dans B

```bash
python comparateur_dossiers.py A B --html diff.html
```

---

#### `-q` ou `--silencieux` — Résumé uniquement

N'affiche que le tableau de résumé (nombre de fichiers par catégorie), sans lister chaque fichier individuellement dans le terminal.  
Les exports CSV et HTML restent complets même en mode silencieux.

```bash
python comparateur_dossiers.py A B -q
```

---

#### `-e PATTERN [PATTERN...]` ou `--exclure` — Patterns d'exclusion

Exclut les fichiers et dossiers dont le chemin correspond aux patterns indiqués.  
Supporte la syntaxe **glob** (`*`, `?`, `[...]`).

```bash
# Exclure le dossier .git et les fichiers temporaires
python comparateur_dossiers.py A B -e .git __pycache__ *.tmp

# Exclure les fichiers .log et le dossier node_modules
python comparateur_dossiers.py A B -e *.log node_modules
```

Le pattern est testé contre chaque **partie du chemin relatif** (nom de dossier ou de fichier).

---

## 📋 Catégories de résultat

| Catégorie | Couleur | Signification |
|-----------|---------|---------------|
| **Identiques** | Vert | Même chemin relatif, même contenu (ou même taille en mode `--rapide`) |
| **Modifiés** | Jaune | Même chemin relatif, mais contenu différent |
| **Seulement dans A** | Rouge | Fichier présent dans A, absent dans B — potentiellement manquant dans la sauvegarde |
| **Seulement dans B** | Cyan | Fichier présent dans B, absent dans A — potentiellement supprimé de la source |

### Exemple de sortie

```
RÉSULTAT DE LA COMPARAISON
=================================================================
A : /home/user/Documents
B : /media/backup/Documents

Identiques         : 1 024
Modifiés           :    18
Seulement dans A   :     5
Seulement dans B   :    12
───────────────────────────────────
Total              : 1 059

─── MODIFIÉS (18) ──────────────────────────────────────────────
M  Projets/rapport_2025.docx
   A : 245.0 Ko — 2025-03-10 14:22
   B : 241.0 Ko — 2025-02-28 09:15  (-4.0 Ko)
...

─── SEULEMENT DANS A (5) ───────────────────────────────────────
-  Nouveau_dossier/fichier.pdf
...

─── SEULEMENT DANS B (12) ──────────────────────────────────────
+  Anciens/archive_2022.zip
...
```

---

## 🔬 Fonctionnement interne

### Construction de l'index

Pour chaque dossier, le script construit un index :

```
{
  "chemin/relatif/fichier.pdf": {
    "empreinte": "sha256...",   # ou taille en mode --rapide
    "taille":    1048576,
    "mtime":     1712345678.0
  },
  ...
}
```

### Comparaison des index

Les deux index sont comparés par leurs clés (chemins relatifs) :

```
Clés communes → comparer les empreintes
  Empreinte identique → Identiques
  Empreinte différente → Modifiés

Clés dans A seulement → Seulement dans A
Clés dans B seulement → Seulement dans B
```

### Chemin de comparaison

La comparaison est basée sur les **chemins relatifs** depuis chaque racine.  
Un fichier `Documents/rapport.pdf` dans A sera comparé à `rapport.pdf` dans B si B pointe déjà vers le sous-dossier `Documents` :

```bash
# Correct : on compare le contenu de Documents avec sa sauvegarde
python comparateur_dossiers.py ~/Documents ~/Backup/Documents

# Incorrect : B contient Documents comme sous-dossier, les chemins ne correspondent pas
python comparateur_dossiers.py ~/Documents ~/Backup
```

---

## 💡 Exemples complets

```bash
# Vérification de sauvegarde complète
python comparateur_dossiers.py ~/Documents ~/Backup/Documents

# Vérification rapide d'un disque externe (sans hash, par taille)
python comparateur_dossiers.py ~/Photos /media/usb/Photos --rapide

# Comparaison silencieuse avec export HTML
python comparateur_dossiers.py A B -q --html diff.html

# Exclure les fichiers cachés et temporaires, double export
python comparateur_dossiers.py ~/Projets ~/Backup/Projets \
  -e .git __pycache__ *.tmp *.log \
  --csv diff.csv --html diff.html

# Comparer deux versions d'un projet
python comparateur_dossiers.py projet_v1/ projet_v2/ --html changements.html
```

---

## ⚠️ Comportements importants

- Les **liens symboliques** sont ignorés dans les deux dossiers.
- Les fichiers **sans permission de lecture** sont silencieusement ignorés.
- En cas d'**erreur de lecture** lors du hash, le fichier est classé en "Modifié" par précaution.
- En mode **précis** (hash SHA-256), la vitesse dépend entièrement du débit disque : prévoir quelques minutes pour des dossiers de plusieurs Go.
- Le mode `--rapide` peut produire des **faux positifs** : deux fichiers de même taille mais de contenu différent (ex. métadonnées changées mais pas le contenu) seront classés "identiques".
- La comparaison est **case-sensitive** sur Linux/macOS et peut être **case-insensitive** sur Windows selon le système de fichiers.
