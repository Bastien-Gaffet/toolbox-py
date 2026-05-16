# ✏️ renommer_batch.py — Documentation

Renomme en masse des fichiers avec des règles cumulables : chercher/remplacer, numérotation séquentielle, changement de casse, nettoyage des caractères spéciaux, ajout de préfixe/suffixe.

---

## 🚀 Utilisation rapide

```bash
# Remplacer "IMG_" par "Photo_"
python renommer_batch.py ./photos --chercher "IMG_" --remplacer "Photo_"

# Numéroter les fichiers et mettre en casse titre
python renommer_batch.py ./docs --numerot --casse titre

# Nettoyer les noms + ajouter préfixe date
python renommer_batch.py ./dl --nettoyer --prefixe "2026_"

# Voir l'aperçu sans renommer
python renommer_batch.py ./photos --chercher "IMG_" --remplacer "Photo_" --simulation
```

---

## ⚙️ Arguments

### Substitution

| Argument | Type | Description |
|----------|------|-------------|
| `--chercher MOTIF` | string | Texte ou regex à rechercher dans le nom |
| `--remplacer TEXTE` | string | Texte de remplacement (défaut : suppression) |
| `--regex` | flag | Interpréter `--chercher` comme une expression régulière |
| `-i / --insensible` | flag | Recherche insensible à la casse |

### Formatage

| Argument | Type | Description |
|----------|------|-------------|
| `--casse {haut,bas,titre}` | choix | Changer la casse du nom |
| `--casse-ext {haut,bas}` | choix | Changer la casse de l'extension |
| `--nettoyer` | flag | Supprimer caractères spéciaux, normaliser espaces/tirets |
| `--prefixe STR` | string | Ajouter un préfixe |
| `--suffixe STR` | string | Ajouter un suffixe (avant l'extension) |
| `--numerot [DEBUT]` | int? | Préfixer par numéro séquentiel (défaut début : 1) |
| `--sep-num SEP` | string | Séparateur entre numéro et nom (défaut : `_`) |
| `--extension EXT` | string | Remplacer l'extension |

### Filtres & Contrôle

| Argument | Type | Description |
|----------|------|-------------|
| `--motif GLOB` | string | Filtrer les fichiers (ex: `*.jpg`, défaut : `*`) |
| `-r / --recursif` | flag | Traiter les sous-dossiers |
| `-s / --simulation` | flag | Aperçu sans renommer |
| `-f / --forcer` | flag | Renommer sans confirmation |

---

## 🔢 Ordre des transformations

Les transformations sont appliquées dans cet ordre fixe :

1. `--nettoyer` — normalisation des caractères spéciaux
2. `--chercher / --remplacer` — substitution
3. `--casse` — changement de casse
4. `--prefixe` — ajout du préfixe
5. `--suffixe` — ajout du suffixe
6. `--numerot` — numérotation préfixe (appliquée après tout le reste)

---

## 📋 Exemples détaillés

### Chercher/remplacer simple

```bash
python renommer_batch.py ./photos --chercher "IMG_" --remplacer "Vacances_"
# IMG_0042.jpg  →  Vacances_0042.jpg
```

### Regex : remplacer les espaces par underscores

```bash
python renommer_batch.py ./docs --chercher "\s+" --remplacer "_" --regex
# Mon document important.pdf  →  Mon_document_important.pdf
```

### Numérotation avec préfixe personnalisé

```bash
python renommer_batch.py ./cours --numerot 10 --sep-num ". "
# algebre.pdf       →  10. algebre.pdf
# analyse.pdf       →  11. analyse.pdf
# geometrie.pdf     →  12. geometrie.pdf
```

### Nettoyage + mise en majuscule de l'extension

```bash
python renommer_batch.py ./dl --nettoyer --casse-ext haut --motif "*.jpeg"
# photo été (1).jpeg  →  photo ete (1).JPEG
```

### Pipeline complet

```bash
python renommer_batch.py ./photos --nettoyer --casse bas --numerot --prefixe "2026-"
# Vacances NICE (1).JPG  →  2026-001_vacances nice (1).jpg
```

---

## 🛡️ Détection de conflits

Avant tout renommage, le script vérifie que deux fichiers ne se retrouveraient pas avec le même nom. En cas de conflit, l'opération est annulée avec un message explicite.

```
3 conflit(s) detecte(s) :
  rapport.pdf
  rapport.pdf
Annule. Modifiez vos regles pour eviter les doublons.
```

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Uniformiser des imports appareil photo | `--chercher "IMG_" --remplacer "Photo_"` |
| Ordonner des cours avant impression | `--numerot` |
| Supprimer les espaces dans les noms | `--chercher " " --remplacer "_"` |
| Passer tout en minuscules | `--casse bas` |
| Changer extension `.jpeg` → `.jpg` | `--extension jpg --motif "*.jpeg"` |
