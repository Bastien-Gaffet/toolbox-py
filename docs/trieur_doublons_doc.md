# 🔁 trieur_doublons.py — Documentation

Détecte les fichiers **strictement identiques** (même contenu) dans toute une
arborescence, **tous types confondus**. Complète `photos_manager.py` (qui, lui, ne
traite que les photos/vidéos) en couvrant documents, archives, musiques, etc.

Méthode en trois filtres, du plus rapide au plus sûr : pré-filtre par **taille**, puis
**hash partiel** (64 Ko de tête) pour écarter vite les fichiers différents, puis **hash
SHA-256 complet** uniquement sur les fichiers dont le début coïncide déjà. Résultat :
fiable même sur un disque entier, et bien plus rapide sur les grosses vidéos (on ne lit
pas des Go pour rien).

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
| `--pixels` | Comparer les **images par pixels décodés** (voir ci-dessous ; nécessite `pillow`) |
| `--similaires` | Comparer les **images par hachage perceptuel** (voir ci-dessous ; nécessite `pillow`) |
| `--seuil N` | Distance de Hamming max pour `--similaires` (défaut 4, 0 = empreintes identiques) |
| `--deplacer DOSSIER` | Déplacer les doublons vers ce dossier |
| `--supprimer` | Supprimer les doublons (garde 1 exemplaire) |
| `--oui` | Agir sans demander de confirmation (scripts) |
| `--json FICHIER` | Exporter le rapport des groupes en JSON |

## 🖼️ Mode `--pixels` (photos aux métadonnées réécrites)

Certains services (pCloud, Google…) réécrivent l'en-tête EXIF au téléversement :
la photo est identique **pixel par pixel** mais ses octets diffèrent — le hash
classique ne peut pas la voir. Le mode `--pixels` compare les **images décodées**,
en trois passes parallélisées (tous les cœurs), de la plus rapide à la plus sûre :

1. **Dimensions + mode couleur** (lecture d'en-tête seule) ;
2. **Pixels à 1/8ᵉ de résolution** (décodage JPEG « draft », ~10× plus rapide) ;
3. **Décodage complet** uniquement sur les groupes qui coïncident encore.

Seules les images aux pixels strictement identiques sont déclarées doublons.
Ne traite que les images (`jpg, png, webp, bmp, tiff, gif`) ; dépend de `pillow`.

## 👁️ Mode `--similaires` (copies recompressées / redimensionnées)

Une photo passée par WhatsApp, un réseau social ou un téléchargement est
**ré-encodée** : mêmes images à l'œil, pixels différents — invisible pour
`--pixels`. Le mode `--similaires` calcule un **dHash 64 bits** (gradient
horizontal d'une réduction 9×8 en niveaux de gris), insensible à la
recompression et au redimensionnement, puis regroupe les empreintes dont la
distance de Hamming est ≤ `--seuil` (union-find).

⚠️ **Semblable n'est pas identique** : des photos prises en rafale peuvent se
ressembler assez pour être regroupées. **Toujours relire le rapport** (ou le
`--json`) avant `--supprimer`/`--deplacer`. Dans ce mode, l'exemplaire gardé
est le **plus gros fichier** (meilleure qualité présumée), et le cache
`.krino/` est ignoré. `--pixels` et `--similaires` sont exclusifs.

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
