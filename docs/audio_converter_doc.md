# 🎵 audio_converter.py — Documentation

Convertit des fichiers audio en batch en utilisant ffmpeg. Supporte MP3, FLAC, WAV, OGG, AAC, M4A et OPUS. Peut normaliser le volume et extraire l'audio de vidéos.

**Prérequis :** [ffmpeg](https://ffmpeg.org/download.html) doit être installé et dans le PATH.

---

## 🚀 Utilisation rapide

```bash
# Convertir tous les MP3 d'un dossier en FLAC
python audio_converter.py ./musique --format flac

# Convertir en MP3 à 320 kbps avec normalisation du volume
python audio_converter.py ./musique --format mp3 --debit 320k --normaliser

# Extraire l'audio d'une vidéo
python audio_converter.py video.mp4 --format mp3 --extraire-audio

# Convertir en OPUS (format moderne, très compact)
python audio_converter.py ./dossier --format opus --debit 128k --sortie ./opus

# Voir les conversions sans exécuter
python audio_converter.py ./musique --format flac --simulation
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `source` | positional | — | Fichier ou dossier à convertir |
| `--format FORMAT` | choix | **requis** | Format de sortie |
| `--debit DEBIT` | string | codec défaut | Débit audio (ex: `128k`, `192k`, `320k`) |
| `--normaliser` | flag | non | Normaliser le volume (EBU R128, -23 LUFS) |
| `--extraire-audio` | flag | non | Extraire la piste audio d'une vidéo |
| `-r / --recursif` | flag | non | Traiter les sous-dossiers |
| `--sortie DIR` | string | même dossier | Dossier de destination |
| `-t / --threads N` | int | 2 | Conversions simultanées |
| `-s / --simulation` | flag | non | Afficher sans convertir |

---

## 🎼 Formats supportés

| Format | Type | Codec | Débit défaut | Usage recommandé |
|--------|------|-------|-------------|-----------------|
| `mp3` | Lossy | libmp3lame | 192k | Distribution, compatibilité maximale |
| `flac` | Lossless | flac | — | Archivage, qualité maximale |
| `wav` | Lossless | pcm_s16le | — | Édition audio, DAW |
| `ogg` | Lossy | libvorbis | 192k | Alternative libre au MP3 |
| `aac` | Lossy | aac | 192k | Appareils Apple, streaming |
| `m4a` | Lossy | aac | 192k | iTunes, iPhone |
| `opus` | Lossy | libopus | 128k | Streaming moderne, très compact |

---

## 🔊 Normalisation du volume (`--normaliser`)

Applique le filtre `loudnorm` de ffmpeg selon la norme **EBU R128** :
- Cible : `-23 LUFS` (niveau standard pour la diffusion TV/streaming)
- True Peak maximum : `-2 dBTP`
- LRA (Loudness Range) : `11 LU`

**Quand l'utiliser ?**
- Collections hétérogènes d'albums avec des niveaux variables
- Préparer des fichiers pour une diffusion radio/podcast
- Equaliser des enregistrements bruts

---

## 📹 Extraction audio de vidéo (`--extraire-audio`)

Active les extensions vidéo en entrée (MP4, MKV, AVI, MOV, WebM...) et passe `-vn` à ffmpeg pour ignorer la piste vidéo.

```bash
# Extraire l'audio d'une interview en FLAC
python audio_converter.py interview.mp4 --format flac --extraire-audio

# Extraire l'audio de toutes les vidéos d'un dossier
python audio_converter.py ./videos --format mp3 --extraire-audio --sortie ./audio
```

---

## 🔧 Installation de ffmpeg

### Windows
1. Télécharger depuis [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) — version `ffmpeg-release-essentials.zip`
2. Extraire et copier `ffmpeg.exe`, `ffprobe.exe` dans `C:\Windows\System32\` (ou un dossier dans le PATH)
3. Vérifier : `ffmpeg -version`

### macOS
```bash
brew install ffmpeg
```

### Linux
```bash
sudo apt install ffmpeg        # Debian/Ubuntu
sudo dnf install ffmpeg        # Fedora
```

---

## 💡 Comparaison des formats

| Situation | Format recommandé |
|-----------|-----------------|
| Archivage sans perte de qualité | `flac` |
| Écoute quotidienne sur smartphone | `mp3 --debit 192k` |
| Streaming web moderne | `opus --debit 128k` |
| Compatibilité maximale (iTunes, Android, tout) | `mp3` ou `aac` |
| Envoi en pièce jointe | `mp3 --debit 128k` (taille réduite) |
| Édition dans un DAW (Audacity, Reaper) | `wav` ou `flac` |
