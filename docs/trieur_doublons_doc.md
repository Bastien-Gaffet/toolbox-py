# 🔁 trieur_doublons.py — Documentation

Détecte les fichiers **strictement identiques** (même contenu) dans toute une
arborescence, **tous types confondus**. Complète `photos_manager.py` (qui, lui, ne
traite que les photos/vidéos) en couvrant documents, archives, musiques, etc.

Méthode : pré-filtre par **taille** (rapide), puis comparaison par **hash SHA-256**
uniquement des fichiers de même taille — fiable même sur un disque entier.

---

## 📦 Dépendances

Aucune (bibliothèque standard). `colorama` en option pour les couleurs.

---

## 🚀 Utilisation

```bash
# Rapport seul (rien n'est modifié) — comportement par défaut
python trieur_doublons.py "D:\Rassemblement"

# Ignorer les petits fichiers pour aller plus vite
python trieur_doublons.py "D:\Rassemblement" --min-taille 1M

# Déplacer les doublons dans un dossier (pour les vérifier avant de supprimer)
python trieur_doublons.py "D:\Rassemblement" --deplacer "D:\_doublons"

# Supprimer les doublons (garde 1 exemplaire par groupe)
python trieur_doublons.py "D:\Rassemblement" --supprimer

# Exporter la liste des doublons en JSON
python trieur_doublons.py "D:\Rassemblement" --json rapport.json
```

---

## ⚙️ Options

| Option | Rôle |
|--------|------|
| `dossier` | Dossier à analyser (récursif) |
| `--min-taille TAILLE` | Ignorer les fichiers plus petits (`1M`, `500K`, `2G`…) |
| `--inclure-vides` | Inclure les fichiers de 0 octet (ignorés par défaut) |
| `--deplacer DOSSIER` | Déplacer les doublons vers ce dossier |
| `--supprimer` | Supprimer les doublons (garde 1 exemplaire) |
| `--json FICHIER` | Exporter le rapport des groupes en JSON |

`--supprimer` et `--deplacer` sont **exclusifs**.

---

## 🧠 Quel exemplaire est conservé ?

Dans chaque groupe de fichiers identiques, l'outil garde le **plus ancien** (date de
modification), et à égalité **le chemin le plus court**. Les autres copies sont les
« doublons » — supprimés ou déplacés selon l'option. Le rapport indique clairement
lequel est `gardé` et lesquels sont `doublon`.

---

## 🛡️ Sécurité

- **Non destructif par défaut** : sans `--supprimer` ni `--deplacer`, l'outil ne fait
  qu'un rapport.
- Une **confirmation** `[o/N]` est demandée avant toute suppression/déplacement.
- Les **liens symboliques** sont ignorés (pas suivis).
- La détection par hash SHA-256 garantit qu'on ne supprime **que** des fichiers au
  contenu réellement identique (deux fichiers de même taille mais différents ne sont
  jamais confondus).

---

## 🔗 Complément au tri photos

Workflow recommandé pour un grand tri (voir aussi le projet de rassemblement photos) :

```bash
# 1. Dédoublonner TOUT (documents, archives, etc.)
python trieur_doublons.py "D:\Rassemblement" --deplacer "D:\_doublons"
# 2. Puis le tri fin des photos/vidéos par date
python photos_manager.py "D:\Rassemblement\Images\Photos"
```
