# 🔍 metadata_cleaner.py — Documentation

Nettoie les métadonnées sensibles de photos, PDF et documents Word avant de les partager : coordonnées GPS, fabricant d'appareil, auteur du document, date de création, etc.

---

## 🚀 Utilisation rapide

```bash
# Inspecter une photo sans modifier
python metadata_cleaner.py photo.jpg --simulation

# Nettoyer une photo (crée photo_clean.jpg)
python metadata_cleaner.py photo.jpg

# Nettoyer en place (modifie l'original)
python metadata_cleaner.py photo.jpg --forcer

# Nettoyer tout un dossier récursivement
python metadata_cleaner.py ./photos --recursif --sortie ./photos_propres

# Nettoyer un PDF
python metadata_cleaner.py rapport.pdf --simulation
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `cible` | positional | — | Fichier ou dossier à nettoyer |
| `-r / --recursif` | flag | non | Traiter les sous-dossiers récursivement |
| `-s / --simulation` | flag | non | Afficher les métadonnées sans modifier les fichiers |
| `--forcer` | flag | non | Modifier les fichiers originaux en place |
| `--sortie DIR` | string | — | Dossier de destination pour les fichiers nettoyés |

Par défaut (sans `--forcer` ni `--sortie`), le fichier nettoyé est créé avec le suffixe `_clean` dans le même dossier : `photo.jpg` → `photo_clean.jpg`.

---

## 📂 Types de fichiers supportés

| Extension | Format | Méthode de nettoyage |
|-----------|--------|----------------------|
| `.jpg`, `.jpeg` | JPEG | `piexif.remove()` — suppression EXIF **sans ré-encodage** (qualité préservée) |
| `.png`, `.tiff`, `.tif`, `.webp`, `.bmp` | Images | Pillow re-save sans métadonnées |
| `.pdf` | PDF | pypdf — réécriture avec métadonnées vides |
| `.docx` | Word | python-docx — effacement des propriétés du document |

---

## 🔐 Métadonnées supprimées

### Photos (EXIF)
- **GPS** — coordonnées géographiques (latitude, longitude, altitude)
- **Fabricant appareil** — marque et modèle de l'appareil photo
- **Logiciel** — application ayant créé/modifié le fichier
- **Date de prise de vue**
- **Artiste / Copyright**
- **Commentaires utilisateur**

### PDF
- Titre, Auteur, Sujet, Mots-clés
- Créateur (logiciel de création), Producteur
- Dates de création et modification

### DOCX (Word)
- Auteur, Dernière modification par
- Titre, Sujet, Catégorie, Mots-clés
- Description, Commentaires, Statut du contenu

---

## 💡 Pourquoi utiliser ce script ?

| Situation | Risque sans nettoyage |
|-----------|----------------------|
| Partager une photo sur les réseaux sociaux | Localisation GPS révèle où vous habitez |
| Envoyer un CV en PDF | L'auteur peut révéler votre vrai nom ou pseudo |
| Partager un document Word d'entreprise | Métadonnées révèlent l'auteur, les révisions, l'entreprise |
| Publier des photos de reportage | GPS révèle la position de la source |

---

## 📦 Dépendances

| Bibliothèque | Usage | Obligatoire |
|---|---|---|
| `Pillow` | Lecture/écriture images | ✅ pour images |
| `piexif` | Suppression EXIF JPEG sans ré-encodage | ✅ pour JPEG |
| `pypdf` | Lecture/réécriture PDF | ✅ pour PDF |
| `python-docx` | Modification propriétés Word | ✅ pour DOCX |
| `colorama` | Couleurs terminal | non |

Si une bibliothèque est absente, le script signale l'erreur et passe au fichier suivant — les autres types restent traités.

---

## 📋 Exemple de rapport (simulation)

```
=== Nettoyage de metadonnees ===
Mode     : SIMULATION
Fichiers : 3
(simulation : aucun fichier ne sera modifie)

  photo_vacances.jpg
    GPS                          coordonnees GPS presentes
    Fabricant appareil           Apple
    Modele appareil              iPhone 15 Pro
    Logiciel                     17.4.1
    Date de prise de vue         2026:03:15 14:32:11

  rapport.pdf
    Author                       Jean Dupont
    Creator                      Microsoft Word
    CreationDate                 D:20260310120000

  compte_rendu.docx
    author                       jean.dupont@entreprise.fr
    last_modified_by             Marie Martin
    title                        Réunion stratégique Q1

---
  3/3 fichier(s) traite(s)
  3 fichier(s) contenaient des metadonnees sensibles
```
