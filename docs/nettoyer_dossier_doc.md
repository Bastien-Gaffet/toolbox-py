# 🧹 nettoyer_dossier.py — Documentation

Analyse un dossier et supprime les fichiers inutiles : fichiers système (Thumbs.db, .DS_Store), fichiers temporaires (*.tmp, ~$*), dossiers vides et copies dupliquées (_copie, (1), - Copie...).

**Mode simulation par défaut** — utiliser `--forcer` pour supprimer réellement.

---

## 🚀 Utilisation rapide

```bash
# Voir ce qui serait supprimé (simulation, sans danger)
python nettoyer_dossier.py ./Téléchargements

# Nettoyer réellement
python nettoyer_dossier.py ./Téléchargements --forcer

# Inclure les dossiers vides et les copies dupliquées
python nettoyer_dossier.py ./docs --forcer --dossiers-vides --duplic

# Nettoyer récursivement
python nettoyer_dossier.py ./projets --forcer --recursif
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `dossier` | positional | — | Dossier à analyser et nettoyer |
| `-r / --recursif` | flag | non | Analyser les sous-dossiers |
| `--duplic` | flag | non | Inclure les fichiers dont le nom suggère une copie |
| `--logs` | flag | non | Inclure les fichiers `.log` |
| `--dossiers-vides` | flag | non | Supprimer les dossiers vides |
| `-s / --simulation` | flag | actif | Mode simulation (par défaut, sans `--forcer`) |
| `-f / --forcer` | flag | non | Supprimer réellement (désactive la simulation) |

---

## 📋 Fichiers détectés

### Fichiers système (toujours inclus)

| Fichier | Système | Description |
|---------|---------|-------------|
| `Thumbs.db`, `ehthumbs.db` | Windows | Cache des miniatures |
| `.DS_Store`, `._.DS_Store` | macOS | Attributs de dossier |
| `desktop.ini` | Windows | Paramètres d'affichage |
| `._*` | macOS | Fork de ressources (sur partitions non-macOS) |

### Fichiers temporaires (toujours inclus)

| Extension | Usage |
|-----------|-------|
| `.tmp`, `.temp` | Fichiers temporaires généraux |
| `.bak`, `.old`, `.orig` | Sauvegardes automatiques |
| `.swp`, `.swo` | Fichiers de sauvegarde Vim |
| `.pyc`, `.pyo` | Bytecode Python compilé |
| `~$*` | Fichiers temporaires Microsoft Office |

### Copies dupliquées (`--duplic`)

Fichiers dont le nom correspond à l'un de ces patterns :

| Pattern | Exemple |
|---------|---------|
| `fichier (N).ext` | `rapport (1).pdf`, `photo (2).jpg` |
| `fichier_copie.ext` | `notes_copie.txt` |
| `fichier - Copie.ext` | `document - Copie.docx` |
| `fichier copy.ext` | `image copy.png` |

---

## 📋 Exemple de rapport

```
=== Nettoyage de dossier ===
  Dossier : D:\Téléchargements
  Mode : SIMULATION (utilisez --forcer pour supprimer reellement)

  Fichiers systeme (4) — 45.2 Ko :
    - Thumbs.db                                              34.0 Ko
    - .DS_Store                                               6.1 Ko
    - desktop.ini                                             0.5 Ko
    - .DS_Store                                               4.6 Ko

  Fichiers temporaires (12) — 8.3 Mo :
    - ~$rapport_stage.docx                                    1.2 Ko
    - document_backup.bak                                     2.4 Mo
    - install.tmp                                             5.9 Mo
    ... et 9 autres

  Copies dupliquees (3) — 24.6 Mo :
    - cours (1).pdf                                          12.3 Mo
    - photo - Copie.jpg                                       4.1 Mo
    - notes_copie.txt                                         8.2 Ko

---
  Total : 19 fichier(s) — 33.0 Mo

(simulation : aucun fichier n'a ete supprime)
  Relancez avec --forcer pour effectuer le nettoyage.
```

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Nettoyer le dossier Téléchargements | `--forcer --duplic --dossiers-vides` |
| Préparer un dossier à sauvegarder | `--forcer --recursif` |
| Supprimer le bytecode Python compilé | `--forcer -r` (détecte `.pyc`) |
| Vérifier avant de partager un dossier | simulation seule (sans `--forcer`) |
