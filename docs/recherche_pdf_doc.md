# 🔍 recherche_pdf.py — Documentation

Script Python de recherche de texte dans une arborescence de fichiers PDF.

---

## 📦 Installation des dépendances

```bash
pip install pdfplumber colorama
```

> `pdfplumber` : extraction du texte des PDF  
> `colorama` : mise en couleur des résultats dans le terminal (optionnel mais recommandé)

---

## 🚀 Utilisation de base

```bash
python recherche_pdf.py <dossier> "<texte à rechercher>"
```

**Exemple minimal :**
```bash
python recherche_pdf.py ./cours "photosynthèse"
```

Le script parcourt **récursivement** tous les sous-dossiers et affiche chaque occurrence trouvée avec son fichier, sa page et un extrait du contexte.

---

## ⚙️ Arguments disponibles

### Arguments obligatoires

| Argument | Description |
|----------|-------------|
| `dossier` | Chemin du dossier racine à analyser |
| `recherche` | Mot, phrase ou expression à rechercher |

---

### Options facultatives

#### `-i` ou `--insensible` — Recherche insensible à la casse

Ignore la différence entre majuscules et minuscules.

```bash
python recherche_pdf.py . "SNT" -i
```
> Trouve : `SNT`, `snt`, `Snt`, `sNT`…

⭐ **Très utile** pour ne pas rater des occurrences selon la mise en forme du document.

---

#### `-r` ou `--regex` — Mode expression régulière

Interprète la chaîne de recherche comme une **expression régulière** (regex).

```bash
python recherche_pdf.py . "\d{2}/\d{2}/\d{4}" -r
```
> Trouve toutes les dates au format `jj/mm/aaaa`

Autres exemples utiles :

```bash
# Toutes les adresses e-mail
python recherche_pdf.py . "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" -r

# Les mots "évaluation" ou "contrôle"
python recherche_pdf.py . "évaluation|contrôle" -r -i

# Une URL (http ou https)
python recherche_pdf.py . "https?://[^\s]+" -r
```

---

#### `-c N` ou `--contexte N` — Lignes de contexte

Affiche **N lignes** avant et après chaque ligne contenant le résultat.  
Par défaut : `1` ligne de contexte.

```bash
python recherche_pdf.py . "conclusion" -c 3
```
> Affiche 3 lignes avant et après chaque occurrence — pratique pour comprendre le passage sans ouvrir le PDF.

| Valeur | Usage conseillé |
|--------|-----------------|
| `0` | Résultat brut uniquement |
| `1` | Par défaut, bon équilibre |
| `2–3` | Pour lire le passage en contexte |
| `5+` | Pour des phrases longues ou des tableaux |

---

#### `--csv <fichier>` — Export des résultats en CSV

Enregistre tous les résultats dans un fichier `.csv` (séparateur `;`).

```bash
python recherche_pdf.py ./docs "objectif" --csv resultats.csv
```

Le fichier CSV contient les colonnes :

| Fichier | Page | Ligne | Extrait |
|---------|------|-------|---------|
| cours/chap1.pdf | 3 | 12 | …texte extrait… |

> Ouvrable directement dans **Excel** ou **LibreOffice Calc** pour filtrer et trier les résultats.

---

#### `-q` ou `--silencieux` — Mode résumé

N'affiche **que le résumé final** (nombre de fichiers, occurrences) sans détailler chaque extrait.

```bash
python recherche_pdf.py . "évaluation" -q
```

> Utile quand on veut juste savoir **combien** de fichiers contiennent le terme, sans flood de texte dans le terminal.

---

## 🔗 Combinaisons utiles

```bash
# Recherche large insensible à la casse avec export CSV
python recherche_pdf.py ./cours "révision" -i --csv export.csv

# Recherche d'un mot avec beaucoup de contexte
python recherche_pdf.py . "introduction" -c 4 -i

# Recherche regex + export silencieux
python recherche_pdf.py . "\d{4}" -r -q --csv chiffres.csv

# Recherche dans le dossier courant, insensible, contexte 2 lignes
python recherche_pdf.py . "STI2D" -i -c 2
```

---

## 📋 Résumé des options

| Option | Raccourci | Valeur | Défaut | Rôle |
|--------|-----------|--------|--------|------|
| `--insensible` | `-i` | — | Non | Ignore maj/min |
| `--regex` | `-r` | — | Non | Active les expressions régulières |
| `--contexte` | `-c` | Entier | `1` | Nb de lignes de contexte |
| `--csv` | — | Nom de fichier | — | Export CSV des résultats |
| `--silencieux` | `-q` | — | Non | Affiche uniquement le résumé |

---

## ⚠️ Limites connues

- Les PDF **scannés** (images sans couche texte) ne sont **pas lisibles** sans OCR — le script retournera 0 résultat sur ces fichiers.
- Les PDF **protégés par mot de passe** ne peuvent pas être lus.
- La qualité de l'extraction dépend de la structure interne du PDF (certains fichiers exportés depuis Word sont mieux extraits que d'autres).

---

*Script basé sur la bibliothèque [pdfplumber](https://github.com/jsvine/pdfplumber)*
