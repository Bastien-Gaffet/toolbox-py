# 🖼️ miniatures_batch.py — Documentation

Redimensionne des images en masse et génère des miniatures. Trois modes de redimensionnement, choix du format de sortie, qualité configurable et ajout optionnel d'un filigrane texte ou image.

---

## 🚀 Utilisation rapide

```bash
# Miniatures 800px de large (ratio préservé)
python miniatures_batch.py ./photos --largeur 800

# Vignettes carrées 200×200 (rogner au centre)
python miniatures_batch.py ./photos --largeur 200 --hauteur 200 --mode remplir --sortie ./thumbs

# Convertir en WebP haute qualité
python miniatures_batch.py ./photos --format webp --qualite 90

# Filigrane texte
python miniatures_batch.py ./photos --filigrane "© 2026 Mon Nom" --opacite 70

# Filigrane image (logo PNG avec transparence)
python miniatures_batch.py ./photos --filigrane-image logo.png --position bas-droite

# Voir sans traiter
python miniatures_batch.py ./photos --largeur 800 --simulation
```

---

## ⚙️ Arguments

### Dimensions

| Argument | Description |
|----------|-------------|
| `--largeur W` | Largeur cible en pixels |
| `--hauteur H` | Hauteur cible en pixels |
| `--mode {ajuster,remplir,etirer}` | Mode de redimensionnement (défaut : `ajuster`) |

### Format de sortie

| Argument | Description |
|----------|-------------|
| `--format {jpg,png,webp,bmp}` | Format de sortie (défaut : même que l'entrée) |
| `--qualite N` | Qualité JPEG/WebP 1-95 (défaut : 85) |
| `--suffixe STR` | Suffixe à ajouter au nom du fichier |
| `--sortie DIR` | Dossier de destination |

### Filigrane

| Argument | Description |
|----------|-------------|
| `--filigrane TEXTE` | Texte du filigrane |
| `--filigrane-image FICHIER` | Image du filigrane (PNG avec transparence) |
| `--position` | Position : `bas-droite`, `bas-gauche`, `haut-droite`, `haut-gauche`, `centre` |
| `--opacite N` | Opacité 0-100 (défaut : 60) |

### Contrôle

| Argument | Description |
|----------|-------------|
| `-r / --recursif` | Traiter les sous-dossiers |
| `-s / --simulation` | Lister sans traiter |

---

## 🔲 Modes de redimensionnement

### `ajuster` (défaut)
Réduit l'image pour qu'elle **tienne** dans les dimensions données, en conservant le ratio. L'image ne sera jamais déformée ni rognée, mais peut être plus petite que les dimensions spécifiées sur un axe.

```
Original : 4000×3000  →  --largeur 800  →  800×600  ✓
Original : 4000×3000  →  --largeur 800 --hauteur 400  →  533×400  ✓
```

### `remplir`
Remplit **exactement** les dimensions spécifiées en rognant les bords. L'image est d'abord agrandie/réduite pour couvrir la zone, puis rognée au centre. Idéal pour les miniatures carrées.

```
Original : 4000×3000  →  --largeur 400 --hauteur 400  →  400×400 (rognée)
```

### `etirer`
Étire l'image aux dimensions exactes **sans préserver le ratio**. Peut déformer l'image. Usage rare.

---

## 🎨 Filigrane

### Texte
Le texte est rendu avec une ombre portée pour la lisibilité sur toutes les couleurs de fond.

```bash
python miniatures_batch.py ./photos --filigrane "© 2026 Bastien" --opacite 70 --position bas-droite
```

La taille de la police est calculée automatiquement selon la largeur de l'image (environ 1/30ème de la largeur).

### Image (logo)
Pour un meilleur résultat, utiliser un PNG avec canal alpha (transparence).

```bash
python miniatures_batch.py ./photos --filigrane-image logo.png --opacite 50 --position bas-gauche
```

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Miniatures pour un site web | `--largeur 400 --hauteur 300 --mode remplir --format webp --qualite 80 --sortie ./web` |
| Réduire des photos avant envoi | `--largeur 1920 --qualite 85 --format jpg` |
| Vignettes carrées pour galerie | `--largeur 200 --hauteur 200 --mode remplir --sortie ./thumbs` |
| Ajouter un copyright | `--filigrane "© 2026 Mon Nom" --position bas-droite` |
| Convertir toutes les PNG en WebP | `--format webp --motif "*.png"` (via `--recursif`) |

---

## 📦 Dépendances

| Bibliothèque | Obligatoire | Installation |
|---|---|---|
| `Pillow` | ✅ oui | `pip install Pillow` (déjà installé) |
| `colorama` | non | `pip install colorama` |
