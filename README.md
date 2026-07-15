# 🧰 toolbox-py

> Collection de scripts Python utilitaires pour automatiser les tâches du quotidien — gestion de fichiers, photos, PDF, réseau, système et plus.

---

## 📦 Scripts disponibles

### 🗂️ Fichiers & Dossiers

| Script | Description |
|--------|-------------|
| [`ranger_dossier.py`](ranger_dossier.py) | Range un dossier par catégorie de fichiers (documents, images, vidéos, archives, exécutables…) avec annulation possible |
| [`recherche_pdf.py`](recherche_pdf.py) | Recherche un mot, une phrase ou une regex dans tous les PDF d'une arborescence |
| [`photos_manager.py`](photos_manager.py) | Supprime les doublons de photos/vidéos, renomme en format normalisé, détecte les screenshots, classe par année/mois |
| [`renommer_batch.py`](renommer_batch.py) | Renommage en masse : chercher/remplacer, numérotation, casse, nettoyage, préfixe/suffixe |
| [`sync_dossiers.py`](sync_dossiers.py) | Synchronisation unidirectionnelle entre deux dossiers — rapport avant action, détection nouveaux/modifiés/supprimés |
| [`nettoyer_dossier.py`](nettoyer_dossier.py) | Supprime fichiers temporaires, .DS_Store, Thumbs.db, dossiers vides, copies dupliquées (_copie, (1)…) |

### 📊 Analyse & Rapports

| Script | Description |
|--------|-------------|
| [`inventaire_dossier.py`](inventaire_dossier.py) | Rapport complet d'un dossier : taille par type, fichiers les plus lourds, répartition par date, export CSV/HTML |
| [`comparateur_dossiers.py`](comparateur_dossiers.py) | Compare deux dossiers : identiques, modifiés, manquants — utile pour vérifier une sauvegarde, export CSV/HTML |
| [`analyse_espace.py`](analyse_espace.py) | Visualise les dossiers qui prennent le plus de place avec barres de progression ASCII, style ncdu |

### 🌐 Réseau & Web

| Script | Description |
|--------|-------------|
| [`scan_reseau.py`](scan_reseau.py) | Scanne le réseau local : liste les appareils connectés (IP, nom, MAC, fabricant), détecte les ports ouverts |
| [`telechargeur_batch.py`](telechargeur_batch.py) | Télécharge une liste d'URLs en parallèle avec reprise, vérification SHA-256 et support des cookies |
| [`video_downloader.py`](video_downloader.py) | Télécharge des vidéos/audio depuis YouTube et ~1000 sites (yt-dlp) : choix de qualité, extraction MP3, playlists, simulation |

### 🔒 Sécurité & Confidentialité

| Script | Description |
|--------|-------------|
| [`metadata_cleaner.py`](metadata_cleaner.py) | Nettoie les métadonnées sensibles (EXIF, GPS, auteur) de photos, PDF et DOCX avant partage |
| [`chiffrer_dossier.py`](chiffrer_dossier.py) | Chiffre/déchiffre un dossier entier avec mot de passe (AES-256-GCM + PBKDF2) en archive .enc |
| [`effacement_securise.py`](effacement_securise.py) | Écrase un fichier plusieurs fois avant suppression (DoD, Gutmann) pour le rendre irrécupérable |

### 💻 Système & Performance

| Script | Description |
|--------|-------------|
| [`nettoyeur_systeme.py`](nettoyeur_systeme.py) | Vide caches navigateurs, dossiers temporaires, vieux logs et fichiers de crash — estimation avant action |

### 🔧 Développement & Déploiement

| Script | Description |
|--------|-------------|
| [`env_checker.py`](env_checker.py) | Vérifie l'environnement de développement : Python, pip, git, Node, variables d'env, dépendances vs requirements.txt |
| [`projet_archiver.py`](projet_archiver.py) | Archive un projet dans un ZIP daté en excluant node_modules, __pycache__, .git, .env et autres fichiers inutiles |

### 📨 Communication

| Script | Description |
|--------|-------------|
| [`email_batch.py`](email_batch.py) | Envoie des emails personnalisés en masse depuis un CSV avec template HTML, pièces jointes et mode test |

### 🎵 Multimédia

| Script | Description |
|--------|-------------|
| [`audio_converter.py`](audio_converter.py) | Convertit des fichiers audio en batch (MP3, FLAC, WAV, OGG, OPUS…), normalise le volume, extrait l'audio de vidéos |
| [`sous_titres_toolkit.py`](sous_titres_toolkit.py) | Outils SRT/VTT : recalage temporel, synchronisation 2 points, fusion bilingue, conversion de format, nettoyage balises |
| [`miniatures_batch.py`](miniatures_batch.py) | Redimensionne des images en masse (ajuster/remplir/étirer), génère des miniatures avec filigrane texte ou image |
| [`sauvegarde_telephone.py`](sauvegarde_telephone.py) | Sauvegarde les photos/vidéos d'un téléphone Android vers un disque (USB/ADB), modes miroir ou trié, incrémental |

### 📄 PDF

| Script | Description |
|--------|-------------|
| [`compresser_pdf.py`](compresser_pdf.py) | Compresse des PDF avec plusieurs niveaux (léger → maximum), traitement batch, rapport taille avant/après *(à venir)* |
| [`pdf_toolkit.py`](pdf_toolkit.py) | Fusionner, découper, pivoter, filigrane, numérotation *(à venir)* |

---

## 🚀 Installation

**Prérequis :** Python 3.10+

```bash
git clone https://github.com/ton-utilisateur/toolbox-py.git
cd toolbox-py
pip install -r requirements.txt
```

### Dépendances par script

| Script | Dépendances |
|--------|-------------|
| `ranger_dossier.py` | aucune (stdlib uniquement) |
| `recherche_pdf.py` | `pdfplumber`, `colorama` |
| `photos_manager.py` | `Pillow`, `piexif`, `colorama` |
| `inventaire_dossier.py` | `colorama` (optionnel) |
| `comparateur_dossiers.py` | `colorama` (optionnel) |
| `analyse_espace.py` | `colorama` (optionnel) |
| `renommer_batch.py` | `colorama` (optionnel) |
| `sync_dossiers.py` | `colorama` (optionnel) |
| `nettoyer_dossier.py` | `colorama` (optionnel) |
| `scan_reseau.py` | `colorama` (optionnel) |
| `telechargeur_batch.py` | `requests`, `colorama` (optionnel) |
| `video_downloader.py` | `yt-dlp`, `ffmpeg` (externe, pour HD/MP3), `colorama` (optionnel) |
| `metadata_cleaner.py` | `Pillow`, `piexif`, `pypdf`, `python-docx`, `colorama` (optionnel) |
| `chiffrer_dossier.py` | `cryptography`, `colorama` (optionnel) |
| `effacement_securise.py` | `colorama` (optionnel) |
| `nettoyeur_systeme.py` | `colorama` (optionnel) |
| `env_checker.py` | aucune (stdlib uniquement) |
| `projet_archiver.py` | aucune (stdlib uniquement) |
| `email_batch.py` | aucune (stdlib uniquement) |
| `audio_converter.py` | `ffmpeg` (outil externe, non-Python) |
| `sous_titres_toolkit.py` | aucune (stdlib uniquement) |
| `miniatures_batch.py` | `Pillow`, `colorama` (optionnel) |
| `sauvegarde_telephone.py` | `adb` (outil externe, non-Python), `colorama` (optionnel) |
| `toolbox.py` (lanceur) | `rich`, `questionary` |

---

## 📖 Utilisation rapide

### 🧰 Lanceur interactif (le plus simple)

Un menu à flèches qui découvre tous les outils et les lance pour toi — aucun argument à retenir :

```bash
python toolbox.py
```

Il regroupe les scripts par catégorie (en lisant ce README), affiche leur description, et
te laisse taper les arguments. Pour un usage direct en ligne de commande, voir ci-dessous.

### Ligne de commande directe

```bash
# Ranger le dossier Téléchargements
python ranger_dossier.py ~/Téléchargements --simulation
python ranger_dossier.py ~/Téléchargements

# Rechercher dans des PDFs
python recherche_pdf.py ./cours "photosynthèse" -i

# Gérer les photos
python photos_manager.py ~/Photos --doublons --simulation
python photos_manager.py ~/Photos --doublons --renommer --classer

# Renommer en masse
python renommer_batch.py ./photos --chercher "IMG_" --remplacer "Photo_" --numerot

# Synchroniser un dossier vers une sauvegarde
python sync_dossiers.py ./documents ./backup --simulation
python sync_dossiers.py ./documents ./backup --supprimer

# Nettoyer les fichiers temporaires
python nettoyer_dossier.py ./Téléchargements --simulation
python nettoyer_dossier.py ./Téléchargements --forcer --dossiers-vides

# Nettoyer les métadonnées d'une photo
python metadata_cleaner.py photo.jpg --simulation
python metadata_cleaner.py ./dossier --recursif --forcer

# Chiffrer un dossier sensible
python chiffrer_dossier.py ./documents
python chiffrer_dossier.py --dechiffrer documents.enc --sortie ./restaure

# Effacer un fichier de façon sécurisée
python effacement_securise.py secret.pdf --methode dod

# Scanner le réseau local
python scan_reseau.py --ports --vendeur

# Télécharger une vidéo (ou l'audio en MP3)
python video_downloader.py "https://youtu.be/xxxx" -q 1080
python video_downloader.py "https://youtu.be/xxxx" --audio

# Nettoyer les caches système
python nettoyeur_systeme.py --forcer

# Vérifier l'environnement de dev
python env_checker.py --requirements requirements.txt --env-exemple .env.example

# Archiver un projet proprement
python projet_archiver.py . --sortie ~/archives --simulation
python projet_archiver.py .

# Envoyer des emails en masse
python email_batch.py contacts.csv --sujet "Bonjour {{nom}}" --template corps.html --test

# Convertir des fichiers audio
python audio_converter.py ./musique --format flac --normaliser

# Recaler des sous-titres
python sous_titres_toolkit.py decaler film.srt --ms 2500
python sous_titres_toolkit.py sync2pts film.srt --src 100 500 --dest 2600 3000

# Redimensionner des images en masse
python miniatures_batch.py ./photos --largeur 800 --format webp --sortie ./web
```

Chaque script dispose de sa propre documentation détaillée dans le dossier [`docs/`](docs/).

---

## 📁 Structure du dépôt

```
toolbox-py/
├── toolbox.py                  ← lanceur interactif
├── ranger_dossier.py
├── recherche_pdf.py
├── photos_manager.py
├── renommer_batch.py
├── sync_dossiers.py
├── nettoyer_dossier.py
├── inventaire_dossier.py
├── comparateur_dossiers.py
├── analyse_espace.py
├── scan_reseau.py
├── telechargeur_batch.py
├── video_downloader.py
├── metadata_cleaner.py
├── chiffrer_dossier.py
├── effacement_securise.py
├── nettoyeur_systeme.py
├── env_checker.py
├── projet_archiver.py
├── email_batch.py
├── audio_converter.py
├── sous_titres_toolkit.py
├── miniatures_batch.py
├── sauvegarde_telephone.py
├── docs/
│   ├── ranger_dossier_doc.md
│   ├── recherche_pdf_doc.md
│   ├── photos_manager_doc.md
│   ├── renommer_batch_doc.md
│   ├── sync_dossiers_doc.md
│   ├── nettoyer_dossier_doc.md
│   ├── inventaire_dossier_doc.md
│   ├── comparateur_dossiers_doc.md
│   ├── analyse_espace_doc.md
│   ├── scan_reseau_doc.md
│   ├── telechargeur_batch_doc.md
│   ├── video_downloader_doc.md
│   ├── metadata_cleaner_doc.md
│   ├── chiffrer_dossier_doc.md
│   ├── effacement_securise_doc.md
│   ├── nettoyeur_systeme_doc.md
│   ├── env_checker_doc.md
│   ├── projet_archiver_doc.md
│   ├── email_batch_doc.md
│   ├── audio_converter_doc.md
│   ├── sous_titres_toolkit_doc.md
│   ├── miniatures_batch_doc.md
│   ├── sauvegarde_telephone_doc.md
│   └── toolbox_doc.md
├── requirements.txt
└── README.md
```

---

## ⚙️ Philosophie

- **Sécurité d'abord** — chaque script propose un mode `--simulation` avant d'agir
- **Aucune donnée dans le cloud** — tout fonctionne localement
- **Stdlib prioritaire** — dépendances externes réduites au minimum
- **Lisible et modifiable** — code commenté en français, facile à adapter

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de distribution.
