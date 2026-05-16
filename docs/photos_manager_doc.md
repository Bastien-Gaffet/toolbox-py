# 📷 photos_manager.py — Documentation

Script Python de gestion complète d'un dossier de photos et vidéos.  
Trois fonctions indépendantes et combinables :

1. 🔍 **Suppression des vrais doublons** (hash SHA-256 + taille)
2. ✏️ **Renommage normalisé** avec détection automatique des screenshots
3. 📅 **Classement par année et par mois**

---

## 📦 Installation des dépendances

```bash
pip install Pillow piexif colorama
```

| Bibliothèque | Rôle | Obligatoire |
|---|---|---|
| `Pillow` | Lecture des données EXIF, détection dimensions | Recommandé |
| `piexif` | Lecture avancée des métadonnées EXIF | Recommandé |
| `colorama` | Mise en couleur du terminal | Optionnel |

> Sans `Pillow`, le script fonctionne mais utilise uniquement la **date de modification du fichier** (moins précise) et la **détection par nom** pour les screenshots.

---

## 🚀 Utilisation de base

```bash
python photos_manager.py <dossier> <action(s)> [options]
```

> ⭐ **Toujours commencer par `--simulation`** pour voir ce qui va être fait sans toucher aux fichiers.

```bash
# Aperçu complet sans rien modifier
python photos_manager.py ~/Photos --doublons --renommer --classer --simulation

# Puis exécuter pour de vrai
python photos_manager.py ~/Photos --doublons --renommer --classer
```

---

## ⚙️ Arguments et options

### Argument de position

| Argument | Description | Défaut |
|----------|-------------|--------|
| `dossier` | Chemin du dossier à traiter | `.` (dossier courant) |

---

### Actions (combinables)

#### `--doublons` — Supprimer les vrais doublons

Détecte et supprime les fichiers dont le **contenu est strictement identique**.  
Voir la section [Comment fonctionne la détection des doublons](#-comment-fonctionne-la-détection-des-doublons) pour le détail.

```bash
python photos_manager.py ~/Photos --doublons
```

---

#### `--renommer` — Renommer en format normalisé

Renomme chaque fichier selon une convention de date standardisée.  
Voir la section [Convention de nommage](#️-convention-de-nommage) pour le détail.

```bash
python photos_manager.py ~/Photos --renommer
```

---

#### `--classer` — Classer par année et mois

Déplace les fichiers dans une arborescence `Année/Mois/`.  
Voir la section [Arborescence créée](#-arborescence-créée) pour le détail.

```bash
python photos_manager.py ~/Photos --classer
```

---

### Options globales

#### `-s` ou `--simulation` — Aperçu sans modification

Affiche exactement ce qui serait fait **sans déplacer, renommer ou supprimer** quoi que ce soit.

```bash
python photos_manager.py ~/Photos --doublons --renommer --classer --simulation
```

> ⭐ Fortement recommandé avant le premier lancement sur un dossier important.

---

#### `-r` ou `--recursif` — Traiter les sous-dossiers

Applique les actions **doublons** et **renommage** aux fichiers dans les sous-dossiers également.  
Par défaut, seuls les fichiers à la racine du dossier cible sont traités.

```bash
python photos_manager.py ~/Photos --doublons --recursif
```

---

### Options spécifiques aux doublons

#### `--corbeille` — Déplacement sécurisé au lieu de suppression

Au lieu de supprimer définitivement les doublons, les déplace dans un sous-dossier `_DOUBLONS_SUPPRIMES/`.  
Permet de vérifier avant de supprimer manuellement.

```bash
python photos_manager.py ~/Photos --doublons --corbeille
```

> Sans `--corbeille`, la suppression est **définitive**. Utiliser `--simulation` d'abord.

---

### Options spécifiques au renommage

#### `--format long` ou `--format court`

Choisit le format de la date dans le nom du fichier.

| Option | Format | Exemple |
|--------|--------|---------|
| `--format long` *(défaut)* | `AAAA-MM-JJ_HH-MM-SS` | `2024-06-15_14-32-01.jpg` |
| `--format court` | `AAAAMMJJ_HHMMSS` | `20240615_143201.jpg` |

```bash
python photos_manager.py ~/Photos --renommer --format court
```

---

### Options spécifiques au classement

#### `--sans-mois` — Classer par année uniquement

Crée une arborescence à un seul niveau (`Année/`) sans sous-dossier par mois.

```bash
python photos_manager.py ~/Photos --classer --sans-mois
```

| Sans l'option | Avec `--sans-mois` |
|---|---|
| `2024/06_Juin/photo.jpg` | `2024/photo.jpg` |

---

#### `--recursif-classer` — Chercher dans les sous-dossiers pour le classement

Cherche les fichiers à classer dans tous les sous-dossiers, pas seulement à la racine.

```bash
python photos_manager.py ~/Photos --classer --recursif-classer
```

---

## 🔍 Comment fonctionne la détection des doublons

La détection repose sur **deux étapes successives** pour être à la fois fiable et rapide :

### Étape 1 — Filtre par taille (rapide)

Tous les fichiers sont d'abord regroupés par **taille en octets**.  
Deux fichiers de tailles différentes ne peuvent pas être identiques : ils sont éliminés immédiatement sans calcul coûteux.

### Étape 2 — Hash SHA-256 (fiable)

Seuls les fichiers de **même taille** sont hashés. Le hash SHA-256 est une empreinte numérique unique du contenu : deux fichiers avec le même hash ont un contenu **bit pour bit identique**, quelle que soit leur date, leur nom ou leur emplacement.

```
IMG_0042.jpg  (3,2 Mo)  ──┐
IMG_0042_copie.jpg (3,2 Mo) ──┤── même taille → hash calculé → identiques → doublon détecté
photo_backup.jpg (3,2 Mo) ──┘
```

### Quel doublon est conservé ?

Parmi un groupe de doublons, le fichier conservé est celui avec :
1. Le **nom le plus court** (présumé être l'original)
2. En cas d'égalité : le **plus ancien** (date de modification)

Les autres sont supprimés ou déplacés selon l'option `--corbeille`.

> ✅ **Aucun fichier unique n'est jamais touché.** Seuls les fichiers dont le contenu est strictement identique à un autre sont concernés.

---

## ✏️ Convention de nommage

### Format général

```
AAAA-MM-JJ_HH-MM-SS[_type][_N].ext
```

| Partie | Description | Exemple |
|--------|-------------|---------|
| `AAAA-MM-JJ` | Date (année-mois-jour) | `2024-06-15` |
| `HH-MM-SS` | Heure (heures-minutes-secondes) | `14-32-01` |
| `_type` | Optionnel : `_screenshot` ou `_video` | `_screenshot` |
| `_N` | Optionnel : numéro si collision de nom | `_02` |
| `.ext` | Extension d'origine conservée | `.jpg` |

### Exemples de noms produits

| Fichier original | Nouveau nom |
|---|---|
| `IMG_4872.jpg` | `2024-06-15_14-32-01.jpg` |
| `Screenshot_20240615.png` | `2024-06-15_09-15-44_screenshot.png` |
| `VID_0023.mp4` | `2024-06-15_18-05-12_video.mp4` |
| Deux photos identiques au même moment | `2024-06-15_14-32-01.jpg` + `2024-06-15_14-32-01_02.jpg` |

### Source de la date

La date est lue dans cet ordre de priorité :

1. **Métadonnées EXIF** (`DateTimeOriginal`) — date réelle de prise de vue, même si le fichier a été copié ou modifié depuis *(nécessite Pillow)*
2. **Date de modification du fichier** — utilisée en fallback si pas d'EXIF (vidéos, PNG, fichiers sans métadonnées)

---

## 📸 Détection des screenshots — Système de score

Un fichier est identifié comme screenshot grâce à un **système de score multi-indices** qui croise plusieurs informations pour éviter les faux positifs.

> ⚠️ **Problème de la détection par dimensions seules** : une photo portrait prise avec un smartphone peut avoir exactement la même résolution qu'un screenshot (ex : `1080×1920`). Se fier uniquement aux dimensions produirait des faux positifs — de vraies photos taguées `_screenshot` par erreur.

### Principe : score ≥ 2 = screenshot

Chaque indice ajoute ou retire des points. Un fichier est classé screenshot uniquement si son **score total atteint 2 ou plus**.

### Tableau des indices

| Indice | Points | Explication |
|--------|--------|-------------|
| Nom contient un mot-clé screenshot | **+2** | `Screenshot_`, `Capture`, `screen_`, `bildschirmfoto`… Les OS nomment systématiquement leurs captures ainsi — indice très fiable |
| Dimensions = résolution d'écran connue | **+1** | Seul, cet indice ne suffit pas. Combiné aux autres, il confirme |
| Aucun tag `Make` / `Model` d'appareil photo | **+1** | Un vrai appareil photo (Canon, Nikon, iPhone en mode photo…) inscrit toujours sa marque dans l'EXIF |
| Aucune donnée optique (focale, exposition, ISO…) | **+1** | Les screenshots n'ont pas de données d'objectif ; une vraie photo en a presque toujours |
| Tag `Make` ou `Model` **présent** | **−2** | Contre-indice fort : l'image vient d'un vrai appareil photo identifié |
| Données optiques **présentes** | **−1** | Contre-indice : présence de focale, vitesse d'obturation, ouverture… |

### Exemples de calcul

**Screenshot Android typique** → score 5 ✅
```
Nom "Screenshot_20240615.png"  → +2
Dimensions 1080×2340           → +1
Pas de Make/Model              → +1
Pas de données optiques        → +1
                          TOTAL = 5  ≥ 2 → screenshot
```

**Photo portrait smartphone (faux positif évité)** → score −1 ❌
```
Nom "IMG_4872.jpg"             →  0
Dimensions 1080×1920           → +1
Make=Apple, Model=iPhone 15    → −2
FocalLength=26mm, ISO=50…      → −1
                          TOTAL = −1  < 2 → photo normale ✅
```

**PNG sans EXIF (capture web ambiguë)** → score 2 ✅
```
Nom "capture_ecran.png"        → +2
Dimensions 1920×1080           → +1
Pas de Make/Model (PNG)        → +1
Pas de données optiques (PNG)  → +1
                          TOTAL = 5  ≥ 2 → screenshot
```

### Indices visibles dans le terminal

Lors du renommage, le détail du score est affiché pour chaque screenshot détecté :
```
IMG_0042.png  →  2024-06-15_09-15-44_screenshot.png  [screenshot — nom_suspect(+2), dimensions_ecran(1080×1920)(+1), pas_de_make_model(+1), pas_de_données_optiques(+1)]
```

### Résolutions d'écrans reconnues *(indice +1)*

| Résolution | Appareils |
|---|---|
| 1080 × 1920, 1080 × 2340, 1080 × 2400… | Smartphones Android |
| 1170 × 2532, 1179 × 2556 | iPhone 13/14 Pro |
| 1284 × 2778, 1290 × 2796 | iPhone Pro Max |
| 750 × 1334, 828 × 1792, 1125 × 2436 | Anciens iPhone |
| 1366 × 768, 1920 × 1080, 2560 × 1440 | Écrans PC |
| 3840 × 2160 | Écrans 4K |

---

## 📅 Arborescence créée par le classement

### Avec `--classer` (défaut — par année et mois)

```
Photos/
├── 2022/
│   ├── 03_Mars/
│   ├── 07_Juillet/
│   └── 12_Décembre/
├── 2023/
│   ├── 01_Janvier/
│   ├── 06_Juin/
│   └── 11_Novembre/
└── 2024/
    ├── 01_Janvier/
    └── 06_Juin/
```

### Avec `--classer --sans-mois` (par année uniquement)

```
Photos/
├── 2022/
├── 2023/
└── 2024/
```

Les noms de mois sont préfixés par leur numéro (`01_Janvier`, `06_Juin`…) pour que le classement alphabétique reste dans l'ordre chronologique.

---

## 🔁 Gestion des collisions de nom

Si deux fichiers différents produiraient le **même nom de destination**, le script ne les écrase pas : il ajoute un suffixe numérique au second.

```
2024-06-15_14-32-01.jpg        ← premier fichier, aucune collision
2024-06-15_14-32-01_02.jpg     ← deuxième fichier au même moment
2024-06-15_14-32-01_03.jpg     ← troisième fichier au même moment
```

> Cela peut arriver avec des photos prises en rafale ou des fichiers copiés depuis plusieurs sources.

---

## 💾 Journal des opérations

À chaque exécution réelle (hors simulation), un fichier journal JSON est créé dans le dossier traité :

```
.photos_manager_20240615_143201.json
```

Il contient le détail de chaque action effectuée (anciens noms, nouveaux noms, sources, destinations). Utile pour tracer les modifications ou récupérer un nom original.

---

## 💡 Exemples complets

```bash
# ── Doublons ─────────────────────────────────────────────────────────────────

# Simulation : voir les doublons sans rien supprimer
python photos_manager.py ~/Photos --doublons --simulation

# Supprimer les doublons (définitif)
python photos_manager.py ~/Photos --doublons

# Déplacer les doublons dans un dossier sécurisé
python photos_manager.py ~/Photos --doublons --corbeille

# Chercher les doublons dans les sous-dossiers aussi
python photos_manager.py ~/Photos --doublons --recursif


# ── Renommage ─────────────────────────────────────────────────────────────────

# Aperçu du renommage
python photos_manager.py ~/Photos --renommer --simulation

# Renommer avec format long (défaut)
python photos_manager.py ~/Photos --renommer

# Renommer avec format court
python photos_manager.py ~/Photos --renommer --format court


# ── Classement ────────────────────────────────────────────────────────────────

# Aperçu du classement
python photos_manager.py ~/Photos --classer --simulation

# Classer par année et mois
python photos_manager.py ~/Photos --classer

# Classer par année uniquement
python photos_manager.py ~/Photos --classer --sans-mois


# ── Combinaisons ─────────────────────────────────────────────────────────────

# Tout faire en simulation
python photos_manager.py ~/Photos --doublons --renommer --classer --simulation

# Workflow complet recommandé (dans cet ordre)
python photos_manager.py ~/Photos --doublons --corbeille   # 1. sécuriser les doublons
python photos_manager.py ~/Photos --renommer               # 2. normaliser les noms
python photos_manager.py ~/Photos --classer                # 3. ranger par date
```

---

## ⚠️ Points importants

- Le script traite uniquement les fichiers **photo et vidéo** (`.jpg`, `.png`, `.mp4`, `.mov`, `.heic`… — liste complète dans le code).
- Sans `--recursif`, seuls les fichiers **à la racine** du dossier sont traités pour les doublons et le renommage.
- **L'ordre recommandé** si on fait tout : doublons → renommage → classement.
- Les doublons sans `--corbeille` sont **supprimés définitivement** — toujours faire `--simulation` d'abord.
- La détection screenshot utilise un **système de score multi-indices** (nom + EXIF + dimensions) — une photo portrait smartphone ne sera jamais taguée `_screenshot` si elle possède des métadonnées d'appareil photo (Make, Model, focale…).
- L'EXIF n'est disponible que sur les **JPEG et certains TIFF** — les PNG, vidéos et RAW utilisent la date de modification du fichier.

---

*Script basé sur [Pillow](https://python-pillow.org/) pour la lecture EXIF et la détection d'images.*
