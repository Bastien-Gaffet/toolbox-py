# 🔍 env_checker.py — Documentation

Vérifie que l'environnement de développement est correctement configuré : versions des outils, variables d'environnement manquantes, paquets Python installés vs `requirements.txt`. Utile avant de démarrer un projet ou après un clone de dépôt.

---

## 🚀 Utilisation rapide

```bash
# Vérification de base (Python, pip, git, node, npm)
python env_checker.py

# Avec requirements.txt et .env.example
python env_checker.py --requirements requirements.txt --env-exemple .env.example

# Ajouter des outils personnalisés
python env_checker.py --outils docker make ffmpeg --python-min 3.11
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `--requirements FICHIER` | string | `requirements.txt` | Fichier de dépendances à vérifier |
| `--env-exemple FICHIER` | string | — | Fichier `.env.example` listant les variables attendues |
| `--outils OUTIL...` | strings | — | Outils supplémentaires à vérifier |
| `--python-min VERSION` | string | `3.10` | Version Python minimale requise |
| `--node-min VERSION` | string | — | Version Node.js minimale requise |

---

## 📋 Sections vérifiées

### Outils installés (par défaut)
- `python` — version + minimum requis
- `pip` — version
- `git` — version
- `node` — version Node.js
- `npm` — version

### Environnement virtuel
Détecte automatiquement : venv actif (`VIRTUAL_ENV`), conda (`CONDA_DEFAULT_ENV`), ou `sys.prefix != sys.base_prefix`.

### Paquets Python (`requirements.txt`)
Pour chaque ligne du fichier requirements.txt, vérifie si le paquet est installé via `importlib.metadata`. Affiche la version installée si présente.

### Variables d'environnement (`.env.example`)
Compare les variables listées dans `.env.example` avec celles de l'environnement courant. Format attendu du fichier :

```bash
# Variables obligatoires
DATABASE_URL=postgresql://...
SECRET_KEY=

# Variable optionnelle (préfixée #)
# SENTRY_DSN=https://...
```

---

## 📋 Exemple de sortie

```
=== Verificateur d'environnement ===

  venv actif : D:\projets\mon_projet\.venv

Outils
  ─────────────────────────────────────────────────────────────
  [OK ]  python               3.13.2
  [OK ]  pip                  25.3
  [OK ]  git                  2.48.1
  [OK ]  node                 22.14.0
  [ERR]  docker               non installe
  [ERR]  ffmpeg               non installe

Paquets Python (requirements.txt)
  ─────────────────────────────────────────────────────────────
  [OK ]  requests                       2.32.3
  [OK ]  Pillow                         12.1.0
  [ERR]  some-package                   non installe              >=1.0.0

Variables d'environnement (.env.example)
  ─────────────────────────────────────────────────────────────
  [OK ]  DATABASE_URL                        definie
  [ERR]  SECRET_KEY                          MANQUANTE
  [AVT]  SENTRY_DSN                          absente (optionnelle)

────────────────────────────────────────────────────────────────
  2 erreur(s) critique(s)
  1 avertissement(s)
```

**Code de sortie :** 0 si aucune erreur, 1 sinon — utilisable dans un script CI.

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Premier lancement d'un projet cloné | `python env_checker.py --requirements requirements.txt --env-exemple .env.example` |
| Vérifier avant déploiement | `python env_checker.py --outils docker make --python-min 3.11` |
| Check CI minimal | `python env_checker.py` (exit 1 si Python/pip/git manquants) |
