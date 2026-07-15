# 📦 extracteur_archives.py — Documentation

Décompresse **en masse** toutes les archives d'un dossier, chacune dans son propre
sous-dossier nommé d'après l'archive. Idéal pour un dossier `Téléchargements` rempli
de `.zip`, `.tar.gz`, etc.

---

## 📦 Dépendances

Les formats les plus courants marchent **sans rien installer** (bibliothèque standard) :

| Format | Support |
|--------|---------|
| `.zip` | ✅ natif |
| `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`/`.tbz2`, `.tar.xz`/`.txz` | ✅ natif |
| `.gz` (fichier unique) | ✅ natif |
| `.7z` | `pip install py7zr` |
| `.rar` | `pip install rarfile` + un outil `unrar`/`7z` dans le PATH |

---

## 🚀 Utilisation

```bash
# Toutes les archives du dossier courant
python extracteur_archives.py

# Un dossier précis
python extracteur_archives.py ./telechargements

# Une seule archive
python extracteur_archives.py archive.zip

# Aperçu (rien n'est extrait)
python extracteur_archives.py ./dl --simulation

# Chercher aussi dans les sous-dossiers
python extracteur_archives.py ./dl --recursif

# Supprimer chaque archive après extraction réussie
python extracteur_archives.py ./dl --supprimer

# Extraire vers un autre dossier de base
python extracteur_archives.py ./dl --sortie ./extrait
```

---

## ⚙️ Options

| Option | Rôle |
|--------|------|
| `source` | Dossier à parcourir ou archive unique (défaut : dossier courant) |
| `-o`, `--sortie DOSSIER` | Dossier de base des extractions (défaut : à côté de l'archive) |
| `-r`, `--recursif` | Chercher aussi dans les sous-dossiers |
| `-s`, `--simulation` | Aperçu sans rien extraire |
| `--supprimer` | Supprimer l'archive après une extraction réussie |

---

## 📂 Où atterrissent les fichiers

| Archive | Résultat |
|---------|----------|
| `cours.zip` | `cours/…` (sous-dossier) |
| `backup.tar.gz` | `backup/…` (sous-dossier) |
| `notes.txt.gz` | `notes.txt` (fichier unique — pas de sous-dossier) |

En cas de nom déjà pris, un suffixe `_2`, `_3`… est ajouté (rien n'est écrasé).

---

## ✅ Résumé & sécurité

- Chaque ligne indique le résultat : `✓` extraite, `⊘` ignorée (format optionnel non
  installé), `✗` erreur — avec un total en fin d'exécution.
- Les archives `.tar` sont extraites avec le filtre `data` (Python 3.12+), qui bloque
  les chemins dangereux (`../`, chemins absolus). `zipfile` assainit aussi les noms.
- **Non destructif par défaut** : les archives ne sont supprimées qu'avec `--supprimer`.
