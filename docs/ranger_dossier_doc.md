# 📁 ranger_dossier.py — Documentation

Script Python d'organisation automatique de fichiers par catégorie.  
Idéal pour ranger un dossier de téléchargements ou tout dossier encombré.

---

## 📦 Dépendances

Aucune installation requise — le script utilise uniquement des modules de la **bibliothèque standard Python** (`os`, `shutil`, `pathlib`, `json`, `argparse`).

---

## 🚀 Utilisation de base

```bash
python ranger_dossier.py                        # range le dossier courant
python ranger_dossier.py /chemin/vers/dossier   # range un dossier spécifique
python ranger_dossier.py ~/Téléchargements      # exemple : dossier Téléchargements
```

Le script analyse tous les fichiers présents **à la racine** du dossier cible (non récursif par défaut), les classe par extension, puis demande une **confirmation** avant de déplacer quoi que ce soit. Ajoutez `-r/--recursif` pour parcourir aussi les sous-dossiers.

---

## ⚙️ Arguments disponibles

### Argument optionnel de position

| Argument | Description | Défaut |
|----------|-------------|--------|
| `dossier` | Chemin du dossier à ranger | `.` (dossier courant) |

---

### Options

#### `-r` ou `--recursif` — Ranger aussi les sous-dossiers

Par défaut, seul le premier niveau est traité. Avec `-r`, le script parcourt **toute
l'arborescence** et regroupe les fichiers dans des catégories **au niveau du dossier
cible** — parfait pour un dossier de rassemblement contenant plusieurs sous-dossiers
sources (téléphone, cloud…).

```bash
python ranger_dossier.py "D:\Rassemblement" --recursif --simulation
python ranger_dossier.py "D:\Rassemblement" --recursif
```

Les fichiers **déjà classés** (déjà sous un dossier de catégorie) sont ignorés, donc
relancer la commande est sans risque. L'annulation (`--annuler`) remet chaque fichier à
son emplacement d'origine.

---

#### `-s` ou `--simulation` — Aperçu sans déplacer

Analyse le dossier et affiche le résumé des déplacements **sans toucher aux fichiers**.

```bash
python ranger_dossier.py . --simulation
```

Affiche le nombre de fichiers par catégorie. Combiner avec `--verbose` pour voir chaque fichier individuellement :

```bash
python ranger_dossier.py ~/Téléchargements --simulation --verbose
```

> ⭐ **Recommandé** avant le premier lancement sur un dossier important.

---

#### `-a` ou `--annuler` — Annuler le dernier rangement

Remet tous les fichiers **exactement à leur emplacement d'origine**, dans l'ordre inverse du rangement.

```bash
python ranger_dossier.py . --annuler
python ranger_dossier.py ~/Téléchargements --annuler
```

> Fonctionne grâce au journal JSON automatiquement sauvegardé lors du rangement (voir section [Journal & Annulation](#-journal--annulation)).  
> ⚠️ Seul le **dernier** rangement peut être annulé.

---

#### `-v` ou `--verbose` — Détail fichier par fichier

En mode simulation, affiche chaque fichier avec sa destination prévue.

```bash
python ranger_dossier.py . --simulation --verbose
```

---

## 📂 Dossiers et sous-dossiers créés

Le script organise les fichiers dans une arborescence à **deux niveaux** :  
un dossier thématique principal, et un sous-dossier de précision quand c'est utile.

---

### 📄 Documents/

#### `Documents/PDF`
Tous les fichiers PDF, quelle que soit leur nature.

| Extension | Description |
|-----------|-------------|
| `.pdf` | Portable Document Format |

---

#### `Documents/Texte`
Tous les formats de traitement de texte et fichiers texte brut.

| Extension | Description |
|-----------|-------------|
| `.doc`, `.docx` | Microsoft Word |
| `.odt`, `.fodt` | LibreOffice Writer |
| `.rtf` | Rich Text Format |
| `.txt` | Texte brut |
| `.md`, `.markdown` | Markdown |
| `.tex` | LaTeX |
| `.rst` | reStructuredText |
| `.pages` | Apple Pages |
| `.wpd`, `.wps`, `.abw` | WordPerfect, Works, AbiWord |

---

#### `Documents/Tableurs`
Tous les formats de feuilles de calcul.

| Extension | Description |
|-----------|-------------|
| `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.xltx` | Microsoft Excel |
| `.ods`, `.fods` | LibreOffice Calc |
| `.csv`, `.tsv` | Données séparées par virgule / tabulation |
| `.numbers` | Apple Numbers |

---

#### `Documents/Présentations`
Diaporamas et présentations.

| Extension | Description |
|-----------|-------------|
| `.ppt`, `.pptx`, `.pps`, `.ppsx` | Microsoft PowerPoint |
| `.odp`, `.fodp` | LibreOffice Impress |
| `.key` | Apple Keynote |

---

#### `Documents/Notes & Données`
Fichiers de configuration, de données structurées et journaux.

| Extension | Description |
|-----------|-------------|
| `.json` | JSON |
| `.xml` | XML |
| `.yaml`, `.yml` | YAML |
| `.toml` | TOML |
| `.ini`, `.cfg`, `.conf` | Fichiers de configuration |
| `.log` | Journaux |
| `.nfo`, `.info` | Informations |

---

### 🖼️ Images/

#### `Images/Photos`
Photos et images numériques, formats courants et formats RAW des appareils photo.

| Extension | Description |
|-----------|-------------|
| `.jpg`, `.jpeg` | JPEG |
| `.png` | PNG |
| `.gif` | GIF |
| `.bmp` | Bitmap |
| `.tiff`, `.tif` | TIFF |
| `.webp` | WebP |
| `.heic`, `.heif` | Format Apple (iPhone) |
| `.raw`, `.cr2`, `.cr3` | RAW Canon |
| `.nef` | RAW Nikon |
| `.arw` | RAW Sony |
| `.dng` | RAW Adobe DNG |
| `.orf`, `.rw2`, `.pef` | RAW Olympus, Panasonic, Pentax |

---

#### `Images/Graphisme & Vectoriel`
Fichiers de création graphique, retouche et design.

| Extension | Description |
|-----------|-------------|
| `.svg` | Vecteur SVG |
| `.ai` | Adobe Illustrator |
| `.eps` | Encapsulated PostScript |
| `.psd`, `.psb` | Adobe Photoshop |
| `.xcf` | GIMP |
| `.cdr` | CorelDRAW |
| `.afphoto`, `.afdesign` | Affinity Photo / Designer |
| `.sketch`, `.fig`, `.xd` | Sketch, Figma, Adobe XD |
| `.indd` | Adobe InDesign |
| `.pub` | Microsoft Publisher |

---

### 🎵 `Audio`
Tous les formats audio.

| Extension | Description |
|-----------|-------------|
| `.mp3` | MP3 |
| `.wav` | WAV non compressé |
| `.flac` | FLAC sans perte |
| `.aac`, `.m4a` | AAC (Apple) |
| `.ogg`, `.opus` | Ogg Vorbis / Opus |
| `.wma` | Windows Media Audio |
| `.aiff`, `.aif` | AIFF (Apple) |
| `.ape` | Monkey's Audio |
| `.mka` | Matroska Audio |
| `.mid`, `.midi` | MIDI |
| `.amr`, `.au`, `.ra` | Formats mobiles / anciens |

---

### 🎬 `Vidéo`
Tous les formats vidéo.

| Extension | Description |
|-----------|-------------|
| `.mp4`, `.m4v` | MPEG-4 |
| `.mkv`, `.mka` | Matroska |
| `.avi` | AVI |
| `.mov` | QuickTime (Apple) |
| `.wmv` | Windows Media Video |
| `.flv`, `.f4v` | Flash Video |
| `.webm` | WebM |
| `.mpg`, `.mpeg` | MPEG |
| `.3gp`, `.3g2` | Vidéo mobile |
| `.ts`, `.mts`, `.m2ts` | Transport Stream (Blu-ray, TV) |
| `.vob` | DVD Video Object |
| `.ogv` | Ogg Video |
| `.rm`, `.rmvb` | RealMedia |
| `.divx` | DivX |

---

### 🗜️ `Archives & Compression`
Fichiers compressés, archives et images disque.

| Extension | Description |
|-----------|-------------|
| `.zip` | ZIP |
| `.rar` | RAR |
| `.7z` | 7-Zip |
| `.tar`, `.tgz` | Tar |
| `.tar.gz`, `.gz` | Tar + Gzip |
| `.tar.bz2`, `.bz2` | Tar + Bzip2 |
| `.tar.xz`, `.xz` | Tar + XZ |
| `.zst` | Zstandard |
| `.lz`, `.lzma`, `.lzh` | Lempel-Ziv |
| `.cab` | Cabinet Windows |
| `.iso`, `.img` | Image disque |
| `.dmg` | Image disque macOS |
| `.z`, `.ace`, `.arj` | Formats anciens |

---

### 💾 `Exécutables & Installateurs`
Programmes, installateurs et scripts exécutables, toutes plateformes.

| Extension | Plateforme | Description |
|-----------|------------|-------------|
| `.exe`, `.msi`, `.msix`, `.appx` | Windows | Exécutables et installateurs |
| `.bat`, `.cmd`, `.ps1`, `.com` | Windows | Scripts Windows |
| `.dmg`, `.pkg`, `.app` | macOS | Installateurs et applications |
| `.deb` | Linux (Debian/Ubuntu) | Paquet Debian |
| `.rpm` | Linux (Fedora/RHEL) | Paquet RPM |
| `.flatpak`, `.snap`, `.appimage` | Linux universel | Formats modernes |
| `.apk` | Android | Paquet Android |
| `.ipa` | iOS | Application iPhone/iPad |
| `.run`, `.bin` | Linux | Installateurs binaires |
| `.sh` | Linux/macOS | Script shell |
| `.arm`, `.arm64`, `.aarch64` | ARM | Binaires architecture ARM |

---

### 💻 `Code Source`
Fichiers de code source, tous langages.

| Extension | Langage |
|-----------|---------|
| `.py`, `.pyw`, `.ipynb` | Python / Jupyter |
| `.js`, `.mjs`, `.ts`, `.jsx`, `.tsx` | JavaScript / TypeScript |
| `.html`, `.htm`, `.css`, `.scss` | Web |
| `.php`, `.rb`, `.java`, `.kt` | PHP, Ruby, Java, Kotlin |
| `.swift`, `.dart` | Swift, Dart |
| `.c`, `.h`, `.cpp`, `.hpp`, `.cc` | C / C++ |
| `.cs` | C# |
| `.go`, `.rs` | Go, Rust |
| `.sql`, `.db`, `.sqlite` | Bases de données |
| `.lua`, `.pl`, `.r` | Lua, Perl, R |
| `.vb`, `.vbs` | Visual Basic |
| `.asm`, `.s` | Assembleur |
| `.m`, `.mat` | MATLAB |
| `.f`, `.f90`, `.for` | Fortran |

---

### 🔤 `Polices`
Fichiers de polices de caractères.

| Extension | Description |
|-----------|-------------|
| `.ttf` | TrueType Font |
| `.otf` | OpenType Font |
| `.woff`, `.woff2` | Web Open Font Format |
| `.eot` | Embedded OpenType |
| `.fon`, `.pfb`, `.pfm`, `.afm` | Formats anciens |

---

### 📦 `Paquets & Dépendances`
Archives de distribution de logiciels et bibliothèques.

| Extension | Écosystème |
|-----------|------------|
| `.whl`, `.egg` | Python (pip) |
| `.jar`, `.war`, `.ear` | Java |
| `.nupkg`, `.vsix` | .NET / Extensions VSCode |
| `.gem` | Ruby |

---

### 🔐 `Sécurité & Certificats`
Clés, certificats et signatures numériques.

| Extension | Description |
|-----------|-------------|
| `.pem`, `.crt`, `.cer` | Certificats SSL/TLS |
| `.key` | Clé privée |
| `.p12`, `.pfx`, `.p7b` | Certificats avec clé |
| `.gpg`, `.asc`, `.sig` | Signatures GPG |

---

### 🖨️ `Impression & Mise en page`

| Extension | Description |
|-----------|-------------|
| `.ps` | PostScript |
| `.prn` | Fichier d'impression |
| `.xps`, `.oxps` | XML Paper Specification (Windows) |

---

### 💾 `Fichiers Système & Divers`
Fichiers système, bibliothèques, temporaires et machines virtuelles.

| Extension | Description |
|-----------|-------------|
| `.dll`, `.sys`, `.drv`, `.ocx` | Librairies système Windows |
| `.so`, `.dylib` | Librairies Linux / macOS |
| `.bak`, `.tmp`, `.temp`, `.swp` | Fichiers temporaires / sauvegardes |
| `.dat`, `.bin` | Données binaires génériques |
| `.torrent` | Fichiers BitTorrent |
| `.vhd`, `.vhdx`, `.vmdk`, `.ova` | Images de machines virtuelles |
| `.crdownload`, `.part` | Téléchargements incomplets (Chrome, Firefox) |

---

### 🗂️ `Divers`
Tout fichier dont l'extension **n'est reconnue dans aucune autre catégorie** est placé ici.  
Cela permet de ne jamais perdre un fichier, même exotique.

---

## 🔁 Gestion des doublons de nom

Si un fichier du même nom existe **déjà dans le dossier de destination**, le script ne l'écrase pas et ne plante pas. Il renomme automatiquement le fichier entrant en ajoutant un suffixe numérique :

```
rapport.pdf        →  rapport.pdf        (premier fichier, pas de conflit)
rapport.pdf        →  rapport_2.pdf      (deuxième fichier du même nom)
rapport.pdf        →  rapport_3.pdf      (troisième fichier du même nom)
```

La numérotation s'incrémente jusqu'à trouver un nom disponible.  
**Aucune donnée n'est jamais écrasée ou perdue.**

---

## 💾 Journal & Annulation

À chaque rangement, un fichier journal caché est créé dans le dossier rangé :

```
.rangement_20250516_143022.json
```

Il contient la liste complète des déplacements effectués (source → destination).  
Il est utilisé par l'option `--annuler` pour **remettre chaque fichier exactement où il était**.

> Les dossiers créés vides après l'annulation sont automatiquement supprimés.  
> ⚠️ Le journal du rangement annulé est effacé — seul le dernier rangement est annulable.

---

## ⚠️ Comportements importants

- Le script est **non récursif** : seuls les fichiers à la **racine** du dossier cible sont traités. Les sous-dossiers existants ne sont pas touchés.
- Le script **ne se déplace pas lui-même** : `ranger_dossier.py` est ignoré même s'il se trouve dans le dossier cible.
- Les fichiers suivants sont **ignorés** : `desktop.ini`, `thumbs.db`, `.gitignore`, `.ds_store`
- Une **confirmation est demandée** avant tout déplacement.
- En cas d'erreur sur un fichier, le script continue et signale l'erreur sans s'arrêter.

---

## 💡 Exemples complets

```bash
# Voir ce qui va être fait, sans toucher aux fichiers
python ranger_dossier.py ~/Téléchargements --simulation

# Voir le détail fichier par fichier
python ranger_dossier.py ~/Téléchargements --simulation --verbose

# Ranger le dossier Téléchargements
python ranger_dossier.py ~/Téléchargements

# Annuler si le résultat ne convient pas
python ranger_dossier.py ~/Téléchargements --annuler

# Ranger le dossier courant
python ranger_dossier.py
```
