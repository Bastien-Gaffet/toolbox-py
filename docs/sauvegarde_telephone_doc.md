# 📱 sauvegarde_telephone.py — Documentation

Script Python de sauvegarde des photos et vidéos d'un téléphone Android vers un disque dur ou un dossier local, via **connexion USB directe (ADB)**.

---

## 📦 Dépendances Python

```bash
pip install colorama
```

> `colorama` est optionnel (couleurs dans le terminal). Le script fonctionne sans.

---

## 🔌 Étape 1 — Installer ADB sur le PC (une seule fois)

ADB (Android Debug Bridge) est l'outil officiel Google qui permet de communiquer avec un téléphone Android en USB, sans lettre de lecteur Windows.

### Windows

1. Télécharger **SDK Platform Tools** :
   ```
   https://developer.android.com/tools/releases/platform-tools
   ```
2. Extraire le ZIP dans un dossier permanent, par exemple :
   ```
   C:\platform-tools\
   ```
3. Ajouter ce dossier au PATH Windows :
   ```
   Panneau de configuration
   → Système → Paramètres système avancés
   → Variables d'environnement
   → Variable "Path" → Modifier → Nouveau
   → Entrer : C:\platform-tools
   → OK partout
   ```
4. **Fermer et rouvrir** le terminal, puis tester :
   ```
   adb version
   ```
   Résultat attendu : `Android Debug Bridge version 35.x.x`

### macOS
```bash
brew install android-platform-tools
```

### Linux
```bash
sudo apt install adb
```

---

## 📲 Étape 2 — Activer le débogage USB sur le téléphone (une seule fois)

> Sur un **Redmi Note 13**, voici la procédure exacte :

```
1. Paramètres → À propos du téléphone → Toutes les spécifications
2. Appuyer 7 fois de suite sur "Version MIUI" ou "Numéro de build"
   → Le téléphone affiche : "Vous êtes maintenant développeur !"

3. Retour dans Paramètres → Paramètres supplémentaires
   → Options pour les développeurs
4. Activer "Débogage USB"

5. Brancher le téléphone au PC avec un câble USB
6. Sur l'écran du téléphone : appuyer "Autoriser" dans la popup
   "Autoriser le débogage USB depuis cet ordinateur ?"
   → Cocher "Toujours autoriser depuis cet ordinateur"
   (pour ne plus avoir à confirmer à chaque branchement)
```

### Vérifier que le téléphone est bien reconnu

Dans un terminal Windows :
```
adb devices
```

Résultat attendu :
```
List of devices attached
23124RA7EO      device
```

| Résultat | Signification |
|---|---|
| `device` | ✅ Tout est bon |
| `unauthorized` | La popup n'a pas été acceptée sur le téléphone |
| *(vide)* | Câble non branché, ou mode USB incorrect |

> Si le téléphone demande le mode USB : choisir **"Transfert de fichiers (MTP)"**.

---

## 🚀 Étape 3 — Lancer le script

### Commandes pour ton installation

Le script est dans `C:\Users\basti\Documents\toolbox-py\` et la destination est `C:\Users\basti\Documents\transfert`.

**Toujours commencer par une simulation :**
```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode miroir --simulation
```

**Lancement réel — mode miroir** (structure du téléphone préservée) :
```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode miroir
```

**Lancement réel — mode trié** (Photos/ + Videos/ à plat) :
```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode trier
```

> 💡 **Astuce** : déplacer le script dans un dossier sans espaces (ex: `C:\scripts\`) évite les guillemets :
> ```
> python C:\scripts\sauvegarde_telephone.py "C:\Users\basti\Documents\transfert" --adb --mode miroir
> ```

---

## ⚙️ Arguments et options

### Structure de la commande

```
python sauvegarde_telephone.py <destination> --adb [--mode miroir|trier] [options]
```

> ⚠️ En mode ADB, le **premier argument est toujours la destination** (pas la source — la source c'est le téléphone branché).

---

### `--adb` — Connexion USB directe *(obligatoire pour Android sans lettre de lecteur)*

```
python sauvegarde_telephone.py "C:\Users\basti\Documents\transfert" --adb
```

---

### `--mode` — Mode de rangement à destination

| Valeur | Résultat | Usage |
|--------|----------|-------|
| `miroir` *(défaut)* | Reproduit l'arborescence du téléphone | Conserver l'organisation d'origine |
| `trier` | Regroupe dans `Photos\` et `Videos\` | Préparer un tri par date avec `photos_manager.py` |

```
... --mode miroir
... --mode trier
```

---

### `--source-adb` — Dossier racine sur le téléphone

Par défaut `/sdcard` (tout le stockage interne). Peut être restreint à un sous-dossier :

```
# Sauvegarder uniquement les photos de l'appareil photo
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --source-adb /sdcard/DCIM

# Sauvegarder tout (défaut)
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --source-adb /sdcard
```

Le script scanne récursivement tout ce qui est sous ce chemin : DCIM, WhatsApp, Telegram, Screenshots, etc.

---

### `-s` ou `--simulation` — Aperçu sans copier

Affiche la liste complète de ce qui serait copié **sans toucher à aucun fichier**.

```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode miroir --simulation
```

> ⭐ Toujours recommandé avant le premier lancement.

---

### `-f` ou `--forcer` — Recopier tous les fichiers

Par défaut les fichiers déjà présents et de taille identique sont ignorés (mode incrémental).
Avec `--forcer`, tout est recopié même si déjà à jour.

```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --forcer
```

---

### `--convertir trier` — Réorganiser une sauvegarde existante

Convertit une sauvegarde miroir déjà effectuée en mode trié, **sans rebrancher le téléphone**.

```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --convertir trier --simulation
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --convertir trier
```

---

### `--verifier-adb` — Diagnostic de connexion

Vérifie qu'ADB est installé et que le téléphone est bien reconnu.

```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" --verifier-adb
```

Résultat attendu :
```
✅ Android Debug Bridge version 35.0.2
✅ Appareil connecté : 23124RA7EO
   Redmi Redmi Note 13 — Android 15
```

---

### `--diagnostic` — Lister tout ce qui est trouvé ET ignoré

Scanne le téléphone et affiche le détail complet : fichiers médias retenus, fichiers ignorés parce que leur **extension** n'est pas un format média, et fichiers ignorés parce qu'ils sont dans un **dossier système**. Aucun fichier n'est copié.

```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --diagnostic
```

> 🔍 À utiliser quand une photo semble **manquer** dans la sauvegarde : le diagnostic dit précisément pourquoi un fichier a été retenu ou écarté.

---

### `--aide-adb` — Afficher le guide d'installation ADB dans le terminal

```
python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" --aide-adb
```

---

## 📂 Les deux modes de rangement

### Mode `miroir`

Reproduit exactement la structure de dossiers du téléphone.

```
Téléphone /sdcard/                   C:\Users\basti\Documents\transfert\
├── DCIM\                        →   ├── DCIM\
│   ├── Camera\                  →   │   ├── Camera\
│   │   ├── IMG_20240615_001.jpg →   │   │   ├── IMG_20240615_001.jpg
│   │   └── VID_20240615_001.mp4 →   │   │   └── VID_20240615_001.mp4
│   └── Screenshots\             →   │   └── Screenshots\
├── WhatsApp\Media\Images\       →   ├── WhatsApp\Media\Images\
└── Telegram\                    →   └── Telegram\
```

---

### Mode `trier`

Regroupe tout dans deux dossiers à plat.

```
Téléphone /sdcard/                   C:\Users\basti\Documents\transfert\
├── DCIM\Camera\IMG_001.jpg      →   ├── Photos\
├── WhatsApp\Media\photo.jpg     →   │   ├── IMG_001.jpg
└── DCIM\Camera\VID_001.mp4      →   │   └── photo.jpg
                                     └── Videos\
                                         └── VID_001.mp4
```

> Compatible directement avec `photos_manager.py --classer` pour trier par année/mois.

---

## ⚡ Mode incrémental (comportement par défaut)

À chaque sauvegarde, le script **ne recopie que les nouveaux fichiers**.

Il compare la taille des fichiers déjà présents à destination avec la taille sur le téléphone.
Si identique → ignoré. Si différent ou absent → copié.

Cela permet de relancer la sauvegarde chaque semaine en ne copiant que les photos prises depuis la dernière fois.

**Performances :** toutes les tailles sont récupérées en **un seul appel ADB** (`find -printf`), puis la comparaison se fait en mémoire — aucun aller-retour USB supplémentaire pendant la planification.

---

## 🔁 Gestion des conflits de noms

Si un fichier de même nom existe déjà à destination avec une taille différente, il est renommé automatiquement :

```
IMG_001.jpg      ← déjà présent, conservé intact
IMG_001_2.jpg    ← nouveau fichier en conflit, renommé
```

---

## 💾 Journal des opérations

Après chaque sauvegarde réelle (hors simulation), un fichier journal JSON est créé dans la destination :

```
C:\Users\basti\Documents\transfert\.sauvegarde_20240615_143022.json
```

Il contient la date, la méthode, le mode, et le détail de chaque fichier copié.

---

## 💡 Workflow complet recommandé

```
── Étape 1 : première utilisation ──────────────────────────────────────────────

  Installer ADB → Activer débogage USB → Vérifier :
  python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" --verifier-adb


── Étape 2 : simulation avant la première sauvegarde ───────────────────────────

  python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode miroir --simulation


── Étape 3 : première sauvegarde complète ──────────────────────────────────────

  python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode miroir


── Étape 4 : sauvegardes suivantes (rapides, incrémentales) ────────────────────

  python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --adb --mode miroir


── Étape 5 (optionnel) : convertir pour trier par date ─────────────────────────

  python "C:\Users\basti\Documents\toolbox-py\sauvegarde_telephone.py" "C:\Users\basti\Documents\transfert" --convertir trier
  python "C:\Users\basti\Documents\toolbox-py\photos_manager.py" "C:\Users\basti\Documents\transfert\Photos" --classer
```

---

## 📋 Formats de fichiers pris en charge

### 🖼️ Photos — 46 formats

#### Standards courants
| Extension | Format |
|-----------|--------|
| `.jpg` `.jpeg` | JPEG |
| `.png` | PNG |
| `.gif` | GIF |
| `.bmp` | Bitmap |
| `.tiff` `.tif` | TIFF |
| `.webp` | WebP (Android, navigateurs modernes) |

#### Formats modernes
| Extension | Format | Appareils |
|-----------|--------|-----------|
| `.heic` `.heif` | High Efficiency Image | Apple iPhone (iOS 11+) |
| `.avif` | AV1 Image Format | Android 12+, Google Pixel |
| `.jxl` | JPEG XL | Google Pixel 9+, futur standard |

#### RAW — Appareils photo & smartphones
| Extension | Constructeur |
|-----------|-------------|
| `.raw` | Générique |
| `.dng` | Adobe DNG — Google Pixel, DJI, Lightroom, Samsung Pro |
| `.cr2` `.cr3` | Canon |
| `.nef` `.nrw` | Nikon (reflex / compact) |
| `.arw` `.srf` `.sr2` | Sony |
| `.orf` | Olympus / OM System |
| `.rw2` | Panasonic / Leica |
| `.pef` `.ptx` | Pentax |
| `.srw` | Samsung |
| `.raf` | Fujifilm |
| `.3fr` `.fff` | Hasselblad |
| `.iiq` `.cap` | Phase One |
| `.x3f` | Sigma |
| `.erf` | Epson |
| `.kdc` `.k25` | Kodak |
| `.mef` | Mamiya |
| `.mos` | Leaf / Mamiya |
| `.bay` | Casio |
| `.rwl` | Leica RAW |
| `.rwz` | Rawzor |
| `.gpr` | GoPro RAW |

#### Formats spéciaux / téléphones
| Extension | Format | Appareils |
|-----------|--------|-----------|
| `.mp` | Google Motion Photo | Google Pixel |
| `.mvimg` | Google Motion Photo (ancien format) | Google Pixel (anciens) |
| `.live` | Live Photo | Samsung |
| `.mpo` | Photo 3D stéréoscopique | Nintendo 3DS, certains APN |
| `.insp` | Photo sphérique | Insta360 |

---

### 🎬 Vidéos — 25 formats

#### Standards courants
| Extension | Format |
|-----------|--------|
| `.mp4` `.m4v` | MPEG-4 |
| `.mkv` | Matroska |
| `.avi` | AVI |
| `.mov` | QuickTime — Apple, DJI, GoPro |
| `.wmv` | Windows Media Video |
| `.flv` `.f4v` | Flash Video |
| `.webm` | WebM |
| `.mpg` `.mpeg` | MPEG-1/2 |
| `.3gp` `.3g2` | Vidéo mobile (anciens Android) |

#### Broadcast / caméscope
| Extension | Format |
|-----------|--------|
| `.ts` `.mts` `.m2ts` | Transport Stream — Blu-ray, caméscopes HD |
| `.vob` | DVD Video Object |
| `.ogv` | Ogg Video |
| `.rm` `.rmvb` | RealMedia |
| `.divx` | DivX |
| `.asf` | Windows Media (ancien) |

#### Action cam / drone / 360°
| Extension | Format | Appareils |
|-----------|--------|-----------|
| `.lrv` | Low Resolution Video | GoPro (fichier proxy) |
| `.insv` | Vidéo sphérique | Insta360 |
| `.360` | Vidéo 360° générique | Caméras 360° |

---

## ⚠️ Points importants

- Le script copie uniquement les **photos et vidéos** — aucun autre fichier n'est touché.
- **Non destructif** — aucun fichier sur le téléphone n'est jamais modifié ou supprimé.
- `adb pull` préserve les **dates de modification originales** des fichiers.
- La carte SD externe (si présente) est souvent accessible via `--source-adb /sdcard/external_sd` ou `/storage/extSdCard` selon le constructeur.
- Le nom du fichier `.py` **ne doit pas contenir d'espace ni de parenthèses**.

---

## 🎯 Principe de filtrage — quels fichiers sont copiés ?

Le script suit une règle volontairement simple : **si c'est une photo ou une vidéo, on la copie — peu importe d'où elle vient.**

Concrètement, un fichier est retenu s'il remplit **les deux conditions** suivantes :

1. Son **extension** figure dans la liste des formats médias pris en charge (voir plus bas : 46 formats photo + 25 formats vidéo).
2. Il ne se trouve **pas** dans un des rares dossiers **purement système** ci-dessous.

### Les seuls dossiers ignorés

| Dossier | Raison |
|---------|--------|
| `.thumbnails` / `thumbnails` | Miniatures régénérées automatiquement (pas les originaux) |
| `.trash` | Corbeille Android |
| `lost.dir` | Fichiers récupérés par `fsck`, généralement corrompus |
| `.android_secure` | Dossier système chiffré, inaccessible |

### Ce qui a changé (important)

> ⚠️ Aucun chemin d'application n'est codé en dur. Le script **ne filtre jamais** par nom d'app.

Les médias rangés dans `WhatsApp`, `Instagram`, `Telegram`, `Snapchat`, `/Android/media/…`, `/Android/data/…` ou n'importe quelle app inconnue **sont donc copiés**. Les anciens dossiers autrefois exclus (`cache`, `obb`, `data`, `.nomedia`…) ne sont **plus** écartés en bloc : seul le filtre par extension décide s'ils contiennent un média utile.

> 💡 Le compromis : quelques miniatures ou images d'interface d'apps peuvent être copiées si elles portent une extension image. En contrepartie, **aucune vraie photo n'est jamais oubliée**, même venant d'une app non prévue. En cas de doute sur un fichier retenu ou écarté, lancer `--diagnostic`.
