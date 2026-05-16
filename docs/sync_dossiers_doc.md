# 🔄 sync_dossiers.py — Documentation

Synchronise un dossier source vers une destination en détectant les fichiers nouveaux, modifiés et supprimés. Affiche un rapport complet avant d'agir.

---

## 🚀 Utilisation rapide

```bash
# Voir les différences sans modifier quoi que ce soit
python sync_dossiers.py ./source ./backup --simulation

# Synchroniser (copier nouveaux et modifiés)
python sync_dossiers.py ./source ./backup

# Synchronisation complète (y compris suppression des fichiers disparus)
python sync_dossiers.py ./source ./backup --supprimer

# Comparaison précise par contenu (SHA-256)
python sync_dossiers.py ./source ./backup --hash

# Exclure certains fichiers
python sync_dossiers.py ./source ./backup --exclure "*.tmp" ".git" "node_modules"
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `source` | positional | — | Dossier de référence |
| `destination` | positional | — | Dossier cible à mettre à jour |
| `--supprimer` | flag | non | Supprimer dans la destination les fichiers absents de la source |
| `--hash` | flag | non | Comparaison par SHA-256 (précis mais plus lent) |
| `-e / --exclure MOTIF...` | strings | — | Motifs glob à exclure |
| `-s / --simulation` | flag | non | Afficher le rapport sans modifier la destination |
| `--csv FICHIER` | string | — | Exporter le rapport en CSV |

---

## 🔍 Modes de comparaison

### Mode rapide (défaut) — taille + date de modification

Chaque fichier est identifié par sa taille en octets et son horodatage de modification (`mtime`). Très rapide, convient à la majorité des synchronisations.

**Limite :** un fichier modifié avec la même taille et le même horodatage (rare) ne serait pas détecté.

### Mode précis (`--hash`) — SHA-256

Calcule l'empreinte SHA-256 de chaque fichier. Détecte toute modification de contenu, même si la taille et la date sont identiques.

**Usage :** vérification de sauvegarde critique, migration de données.

---

## 📋 Catégories de différences

| Statut | Description | Action |
|--------|-------------|--------|
| **Nouveau** | Présent dans source, absent en destination | Copié |
| **Modifié** | Présent dans les deux, mais différent | Écrasé dans destination |
| **Absent de source** | Présent en destination, absent en source | Supprimé avec `--supprimer`, ignoré sinon |

---

## 📤 Export CSV

Avec `--csv rapport.csv`, génère un fichier contenant :

```
Statut ; Chemin ; Taille
NOUVEAU ; docs/cours.pdf ; 245760
MODIFIE ; docs/notes.txt ; 1024
SUPPRIME ; old/archive.zip ; 102400
```

---

## 📋 Exemple de rapport

```
=== Synchronisation dossiers ===
  Source      : D:\Documents
  Destination : E:\Backup\Documents
  Comparaison : taille+date

  Analyse de la source...
  1847 fichier(s) dans la source
  Analyse de la destination...
  1821 fichier(s) dans la destination

  Nouveaux (3) :
    + cours/algebre_ch5.pdf  (1.2 Mo)
    + notes/td_2026-05.txt   (12.4 Ko)
    + photos/sortie.jpg      (4.8 Mo)

  Modifies (2) :
    ~ notes/todo.txt         (3.1 Ko)
    ~ docs/rapport.docx      (248.0 Ko)

  Absents de la source (25) :
  (non supprimes — utiliser --supprimer pour les retirer)

Synchroniser 5 operation(s) ? [o/N] : o

  5 fichier(s) copie(s)  /  0 erreur(s)
  Synchro terminee le 2026-05-16 14:30
```

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Sauvegarde hebdomadaire vers disque externe | `python sync_dossiers.py ~/Documents /media/ext/Backup` |
| Vérifier qu'une sauvegarde est complète | `--hash --simulation` |
| Miroir exact (y compris suppressions) | `--supprimer` |
| Exclure les fichiers temporaires | `--exclure "*.tmp" "~$*" ".DS_Store"` |
