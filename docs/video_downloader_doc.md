# 🎬 video_downloader.py — Documentation

Télécharge des **vidéos** (ou l'**audio seul en MP3**) depuis YouTube et
~1000 autres sites, via [yt-dlp](https://github.com/yt-dlp/yt-dlp).
Choix de la qualité, playlists, mode simulation.

---

## 📦 Dépendances

```bash
pip install yt-dlp
```

- **ffmpeg** (outil externe, recommandé) — requis pour la **HD** (fusion vidéo+audio)
  et l'**extraction MP3**.
  - Windows : https://www.gyan.dev/ffmpeg/builds/ (`ffmpeg-release-essentials.zip`),
    puis ajouter le dossier `bin` au PATH.
  - macOS : `brew install ffmpeg` · Linux : `sudo apt install ffmpeg`
- Sans ffmpeg, le script bascule sur le meilleur flux déjà fusionné (souvent ≤720p)
  et l'extraction MP3 est indisponible.

---

## 🚀 Utilisation

### Mode interactif (le plus simple)

```bash
python video_downloader.py
```

Le script demande l'URL, si on veut l'audio seul, la qualité et le dossier de sortie.

### Mode arguments

```bash
# Vidéo, meilleure qualité disponible
python video_downloader.py "https://youtu.be/xxxx"

# Vidéo en 1080p dans un dossier précis
python video_downloader.py "https://youtu.be/xxxx" -q 1080 -s ./videos

# Audio seul en MP3
python video_downloader.py "https://youtu.be/xxxx" --audio

# Toute une playlist
python video_downloader.py "https://.../playlist?list=xxxx" --playlist

# Aperçu sans rien télécharger
python video_downloader.py "https://youtu.be/xxxx" --simulation
```

---

## ⚙️ Options

| Option | Rôle |
|--------|------|
| `url` | URL de la vidéo ou playlist (si absente → mode interactif) |
| `-s`, `--sortie DOSSIER` | Dossier de destination (défaut : `telechargements_video`) |
| `-q`, `--qualite QUALITE` | `best` (défaut), `2160`, `1440`, `1080`, `720`, `480`, `360` |
| `--audio` | Extraire uniquement l'audio en MP3 (nécessite ffmpeg) |
| `--playlist` | Télécharger toute la playlist (sinon : la vidéo seule) |
| `--simulation` | Lister le titre/auteur/durée sans rien télécharger |

---

## 📂 Nommage des fichiers

Les fichiers sont enregistrés sous la forme :

```
Titre de la vidéo [ID].ext
```

Le suffixe `[ID]` garantit l'unicité (deux vidéos de même titre ne s'écrasent pas).
Les noms sont assainis pour être compatibles Windows.

---

## 🎚️ Comment la qualité est choisie

- **Avec ffmpeg** : yt-dlp télécharge le meilleur flux vidéo **et** le meilleur flux
  audio séparément, puis les **fusionne** en MP4 — c'est ce qui permet le 1080p, 4K, etc.
- **Sans ffmpeg** : seul un flux déjà « muxé » (vidéo+audio dans un même fichier) est
  possible, souvent plafonné à 720p, parfois 360p.
- `-q 1080` prend « au plus 1080p » : si la vidéo n'existe qu'en 720p, elle est prise
  en 720p (pas d'échec).

---

## ⚠️ Notes

- **Playlists** : par défaut, une URL de playlist ne télécharge que la vidéo pointée.
  Ajouter `--playlist` pour tout récupérer.
- Le script ignore les erreurs individuelles dans une playlist (`ignoreerrors`) et
  continue avec les vidéos suivantes.
- Usage strictement personnel — respecter les droits d'auteur et les conditions
  d'utilisation des plateformes.
