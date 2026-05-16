# 📝 sous_titres_toolkit.py — Documentation

Couteau suisse pour fichiers de sous-titres `.srt` et `.vtt`. 7 commandes indépendantes pour corriger la synchronisation, fusionner des pistes, changer de format et nettoyer les balises.

---

## 🚀 Utilisation rapide

```bash
# Décaler de 5 secondes en avant
python sous_titres_toolkit.py decaler film.srt +5000

# Synchronisation précise à 2 points
python sous_titres_toolkit.py sync film.srt "00:01:23,456" "00:01:20,000" "00:45:00,000" "00:44:55,000"

# Fusionner français + anglais
python sous_titres_toolkit.py fusionner fr.srt en.srt --sortie bilingue.srt

# Convertir SRT → VTT
python sous_titres_toolkit.py convertir film.srt

# Nettoyer les balises HTML et SSA
python sous_titres_toolkit.py nettoyer film.srt

# Statistiques
python sous_titres_toolkit.py stats film.srt

# Chercher/remplacer
python sous_titres_toolkit.py chercher film.srt "l'" "l'" --regex -i
```

---

## 📐 Formats supportés

### SRT (SubRip Text)

Format le plus courant. Chaque cue est séparé par une ligne vide :

```
1
00:00:01,000 --> 00:00:04,500
Bonjour et bienvenue !

2
00:00:05,200 --> 00:00:08,000
Voici le deuxième sous-titre
sur deux lignes.
```

- Horodatages : `HH:MM:SS,mmm` (virgule pour les millisecondes)
- Encodage attendu : UTF-8 (ou UTF-8 avec BOM)

### VTT (WebVTT)

Format web HTML5. Similaire à SRT avec quelques différences :

```
WEBVTT

1
00:00:01.000 --> 00:00:04.500
Bonjour et bienvenue !

2
00:00:05.200 --> 00:00:08.000
Deuxième sous-titre
```

- Horodatages : `HH:MM:SS.mmm` (point pour les millisecondes)
- En-tête obligatoire : `WEBVTT` sur la première ligne
- Peut contenir des blocs `NOTE` (commentaires) et `STYLE` (CSS) — ignorés à la lecture

---

## 🔧 Commandes détaillées

---

### `decaler` — Décalage temporel simple

Décale **tous** les horodatages d'un delta fixe, en millisecondes.

```bash
python sous_titres_toolkit.py decaler film.srt +5000          # +5 secondes
python sous_titres_toolkit.py decaler film.srt -3000          # -3 secondes
python sous_titres_toolkit.py decaler film.srt +500 --simulation
python sous_titres_toolkit.py decaler film.srt +2000 --sortie film_sync.srt
```

**Quand l'utiliser ?** Le film démarre avec un délai fixe (publicités, intro non comptée). Tous les sous-titres sont décalés du même montant.

**Limite :** ne fonctionne que si le décalage est **uniforme**. Si les sous-titres dérivent progressivement (s'écartent au fil du film), utiliser `sync` à 2 points.

---

### `sync` — Synchronisation à 2 points

Corrige à la fois l'**offset** (décalage de départ) et la **dérive** (les sous-titres s'accélèrent ou ralentissent par rapport à la vidéo). Nécessite deux points de référence connus.

```bash
python sous_titres_toolkit.py sync film.srt \
    "00:01:23,456" "00:01:20,000" \
    "00:45:00,000" "00:44:55,000"
```

**Arguments :**
| Argument | Description |
|----------|-------------|
| `t1_src` | Horodatage **actuel** du 1er cue de référence dans le fichier .srt |
| `t1_dest` | Horodatage **correct** de ce même cue (moment où il devrait apparaître) |
| `t2_src` | Horodatage **actuel** du 2ème cue de référence |
| `t2_dest` | Horodatage **correct** de ce même cue |

**Comment trouver les 2 points de référence ?**

1. Ouvrir le film dans un lecteur (VLC, MPC-HC)
2. Repérer un cue facilement identifiable vers le **début** du film (ex: premier dialogue)
3. Lire le temps affiché par le lecteur au moment où le personnage parle → c'est `t1_dest`
4. Lire le temps du cue dans le fichier .srt → c'est `t1_src`
5. Faire de même vers la **fin** du film pour obtenir `t2_src` / `t2_dest`

**Formule appliquée :**

```
t_nouveau = t_actuel × échelle + offset

échelle = (t2_dest - t1_dest) / (t2_src - t1_src)
offset  = t1_dest - échelle × t1_src
```

Le script affiche l'échelle et l'offset calculés :
```
  Echelle : 0.999852  (derive : -14.8 ms / 100s)
  Offset  : +4200 ms  (+4.200s)
```

---

### `fusionner` — Fusionner deux pistes

Mélange deux fichiers de sous-titres en un seul, triés par horodatage de début.

```bash
python sous_titres_toolkit.py fusionner fr.srt en.srt --sortie bilingue.srt
python sous_titres_toolkit.py fusionner commentaire.srt original.srt
```

**Cas d'usage :**
- Sous-titres bilingues (français + anglais simultanément)
- Ajouter une piste de description audio à des sous-titres existants
- Combiner les sous-titres de deux épisodes concaténés

**Note :** les cues sont fusionnés et triés par `debut`. Si deux cues se chevauchent exactement au même instant, l'ordre de priorité correspond à l'ordre des fichiers passés en argument.

---

### `convertir` — Conversion SRT ↔ VTT

```bash
python sous_titres_toolkit.py convertir film.srt           # → film.vtt
python sous_titres_toolkit.py convertir film.vtt           # → film.srt
python sous_titres_toolkit.py convertir film.srt --sortie sous-titres.vtt
```

**Ce qui est converti :**
- Horodatages : virgule (`,`) ↔ point (`.`)
- En-tête `WEBVTT` ajouté ou retiré
- Les blocs `NOTE` et `STYLE` VTT sont ignorés (non conservés)

---

### `nettoyer` — Suppression des balises

Retire les balises de formatage qui peuvent apparaître dans les fichiers téléchargés :

```bash
python sous_titres_toolkit.py nettoyer film.srt
python sous_titres_toolkit.py nettoyer film.srt --sortie film_clean.srt
python sous_titres_toolkit.py nettoyer film.srt --simulation
```

**Balises supprimées :**

| Type | Exemples | Format |
|------|----------|--------|
| HTML | `<i>`, `</i>`, `<b>`, `<u>`, `<font color="yellow">` | Courant dans les SRT téléchargés |
| SSA/ASS | `{\i1}`, `{\i0}`, `{\an8}`, `{\pos(320,240)}`, `{\c&H0000FF&}` | Fichiers d'origine Aegisub |
| VTT inline | `<00:01:23.456>`, `<c>`, `</c>` | Cue timestamps et Ruby text |

**Avant / après :**
```
Avant : {\an8}<i>Voix off</i> : Bienvenue sur <b>Mars</b>.
Après : Voix off : Bienvenue sur Mars.
```

---

### `stats` — Statistiques

Analyse le fichier et affiche des métriques utiles.

```bash
python sous_titres_toolkit.py stats film.srt
```

**Exemple de sortie :**
```
=== Statistiques ===  film.srt

  Cues            : 1247
  Debut           : 00:00:42,000
  Fin             : 01:52:35,800
  Duree totale    : 1h52m
  Duree affichage : 1h18m     (durée effective où les sous-titres sont visibles)
  Duree moyenne   : 3785 ms / cue
  Mots            : 9423
  Mots/minute     : 83.7

  Top 5 cues les plus longs (texte) :
    #423   00:45:12,000  Les règles de la cité interdite stipulent...
    ...

  3 cues les plus courts (durée) :
    #12    120 ms  Ah !
    ...
```

**Mots/minute :** indicateur de densité de sous-titres. Un film standard est à 80–120 mpm. Au-delà de 180 mpm, les sous-titres sont difficilement lisibles.

---

### `chercher` — Rechercher et remplacer

```bash
# Remplacement simple
python sous_titres_toolkit.py chercher film.srt "OK" "D'accord"

# Suppression de tous les "- " en début de ligne
python sous_titres_toolkit.py chercher film.srt "^- " "" --regex

# Aperçu sans modifier
python sous_titres_toolkit.py chercher film.srt "couleur" --apercu

# Insensible à la casse
python sous_titres_toolkit.py chercher film.srt "bonjour" "Bonjour" -i
```

**Arguments :**

| Argument | Description |
|----------|-------------|
| `motif` | Texte ou expression régulière à rechercher |
| `remplacement` | Texte de substitution (défaut : suppression) |
| `--regex` | Interpréter le motif comme une regex Python |
| `-i / --insensible` | Recherche insensible à la casse |
| `--apercu` | Afficher les modifications sans écrire le fichier |

**Regex utiles :**

| Regex | Effet |
|-------|-------|
| `^\-\s*` | Supprimer les tirets de dialogue en début de réplique |
| `\s+` | Normaliser les espaces multiples |
| `\.{3}` | Remplacer `...` par `…` (ellipse typographique) |
| `<[^>]+>` | Supprimer toutes les balises HTML (alternative à `nettoyer`) |

---

## 💡 Workflows typiques

### Sous-titres téléchargés décalés

```bash
# 1. Voir les stats pour confirmer le problème
python sous_titres_toolkit.py stats film.srt

# 2. Nettoyer les balises parasites d'abord
python sous_titres_toolkit.py nettoyer film.srt --sortie film_clean.srt

# 3. Décaler si offset uniforme
python sous_titres_toolkit.py decaler film_clean.srt +3500 --sortie film_sync.srt

# 4. Ou synchro 2 points si derive
python sous_titres_toolkit.py sync film_clean.srt "00:01:10,000" "00:01:07,500" "01:20:00,000" "01:19:54,000"
```

### Créer des sous-titres bilingues

```bash
# Fusionner et nettoyer
python sous_titres_toolkit.py fusionner fr.srt en.srt --sortie tmp.srt
python sous_titres_toolkit.py nettoyer tmp.srt --sortie bilingue.srt

# Convertir pour lecteur web
python sous_titres_toolkit.py convertir bilingue.srt --sortie bilingue.vtt
```

---

## 📦 Dépendances

Aucune bibliothèque externe — stdlib Python uniquement (`re`, `dataclasses`, `pathlib`).
