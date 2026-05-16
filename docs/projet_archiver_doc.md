# 📦 projet_archiver.py — Documentation

Archive un dossier de projet dans un fichier ZIP daté, en excluant automatiquement les dossiers inutiles (`node_modules`, `__pycache__`, `.git`, `.env`...). Peut lire le `.gitignore` du projet pour affiner les exclusions.

---

## 🚀 Utilisation rapide

```bash
# Archiver le dossier courant
python projet_archiver.py

# Archiver un projet spécifique
python projet_archiver.py ./mon_projet

# Choisir le dossier de destination
python projet_archiver.py ./mon_projet --sortie ~/archives

# Voir ce qui serait inclus sans créer l'archive
python projet_archiver.py ./mon_projet --simulation

# Exclure des dossiers supplémentaires
python projet_archiver.py . --exclure "data/" "*.csv" "rapports/"
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `source` | positional | `.` | Dossier du projet à archiver |
| `--sortie DIR` | string | parent du projet | Dossier de destination du ZIP |
| `--nom NOM` | string | `projet_AAAA-MM-JJ_HHMMSS` | Nom de l'archive (sans extension) |
| `--exclure MOTIF...` | strings | — | Motifs glob supplémentaires à exclure |
| `--sans-gitignore` | flag | non | Ignorer le `.gitignore` du projet |
| `--sans-defauts` | flag | non | Désactiver les exclusions par défaut |
| `--compression N` | int 0-9 | 6 | Niveau de compression ZIP |
| `-s / --simulation` | flag | non | Lister sans créer l'archive |

---

## 🚫 Exclusions par défaut

| Catégorie | Dossiers/fichiers exclus |
|-----------|-------------------------|
| Contrôle de version | `.git`, `.svn`, `.hg` |
| Dépendances | `node_modules`, `vendor`, `.venv`, `venv`, `env` |
| Build | `__pycache__`, `*.pyc`, `*.pyo`, `dist`, `build`, `.next`, `target`, `*.egg-info` |
| IDE | `.idea`, `.vscode`, `*.suo`, `*.user` |
| Secrets | `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12` |
| Temp | `*.log`, `*.tmp`, `Thumbs.db`, `.DS_Store` |
| Tests | `.coverage`, `htmlcov`, `.pytest_cache`, `.mypy_cache` |

Si un `.gitignore` est présent dans le projet, ses patterns sont **également appliqués** (sauf avec `--sans-gitignore`).

---

## 📋 Exemple de sortie

```
=== Archivage de projet ===
  Source    : D:\projets\mon_projet
  Archive   : D:\projets\mon_projet_2026-05-16_143022.zip
  Exclusions: 41 motifs actifs

  Analyse du projet...
  847 fichier(s) — 12.4 Mo non compressés

  Archive créée : D:\projets\mon_projet_2026-05-16_143022.zip
  12.4 Mo -> 4.8 Mo (61% de compression)
```

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Sauvegarder avant une refactorisation risquée | `python projet_archiver.py .` |
| Partager le code source sans les node_modules | Comportement par défaut |
| Archive pour un client (sans .git, .env) | `python projet_archiver.py . --sortie ~/bureau` |
| Voir exactement ce qui sera inclus | `--simulation` |
