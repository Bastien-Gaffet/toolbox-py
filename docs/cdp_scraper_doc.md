# 📚 cdp_scraper.py — Documentation

Scraper dédié à [cahier-de-prepa.fr](https://cahier-de-prepa.fr) : connexion depuis le terminal, découverte automatique de tous les documents d'une classe, téléchargement organisé par section.

---

## 🚀 Utilisation rapide

```bash
# Télécharger tous les documents d'une classe
python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe --login moi --mdp motdepasse

# Mode simulation (voir ce qui serait téléchargé sans télécharger)
python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe --simulation

# Exporter la liste des URLs (pour telechargeur_batch.py) sans télécharger
python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe --liste urls.txt

# Sauvegarder les cookies pour une utilisation ultérieure
python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe --cookie-sortie cookies.txt
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `--url URL` | string | **requis** | URL de la classe (ex: `https://cahier-de-prepa.fr/ma-classe`) |
| `--login NOM` | string | — | Identifiant de connexion (demandé interactivement si absent) |
| `--mdp MDP` | string | — | Mot de passe (demandé de façon sécurisée si absent) |
| `-s / --sortie DIR` | string | `./cdp_docs` | Dossier de destination des téléchargements |
| `--liste FICHIER` | string | — | Exporter les URLs trouvées (compatible telechargeur_batch.py) |
| `--simulation` | flag | non | Lister les documents sans télécharger |
| `--profondeur N` | int | 3 | Profondeur maximale de crawl |
| `--cookie-sortie` | string | — | Sauvegarder les cookies de session dans un fichier |

---

## 🔐 Connexion

La connexion se fait via POST sur le formulaire d'authentification de cahier-de-prepa.fr. Les champs utilisés sont `login` et `mdp` (conformément au code source du site).

**Si `--login` ou `--mdp` ne sont pas fournis**, le script les demande interactivement :
- Le login s'affiche en clair
- Le mot de passe est masqué (saisie sécurisée via `getpass`)

**Vérification de la connexion** : le script vérifie que la réponse ne contient plus le champ mot de passe, ce qui indique une authentification réussie.

---

## 🗂️ Organisation des téléchargements

Les documents sont organisés automatiquement par section dans le dossier de sortie :

```
cdp_docs/
├── Mathematiques/
│   ├── cours_algebre.pdf
│   └── td_matrices.pdf
├── Physique/
│   ├── cours_mecanique.pdf
│   └── exercices_optique.pdf
└── Informatique/
    └── cours_python.pdf
```

La section est déduite du titre de la rubrique parente dans la page HTML de la classe.

---

## 🔗 Compatibilité avec telechargeur_batch.py

Le flag `--liste` génère un fichier d'URLs au format compris par `telechargeur_batch.py`. Cela permet de séparer la découverte du téléchargement, ou de reprendre un téléchargement interrompu :

```bash
# Étape 1 : découvrir et exporter les URLs + cookies
python cdp_scraper.py --url https://cahier-de-prepa.fr/ma-classe --liste urls.txt --cookie-sortie cookies.txt

# Étape 2 : télécharger avec le téléchargeur batch (4 threads)
python telechargeur_batch.py urls.txt --cookie-fichier cookies.txt -t 4 -s ./cours
```

---

## 🕷️ Fonctionnement du crawl

1. **Connexion** : authentification POST sur le endpoint de connexion de la classe
2. **Page principale** : récupération des liens internes à la classe
3. **Crawl récursif** : exploration des pages jusqu'à la profondeur `--profondeur`
4. **Extraction des liens** : détection des URLs de type `download?id=X` via BeautifulSoup4 + regex
5. **Téléchargement** : requêtes séquentielles avec délai de politesse (0,2 s entre pages crawlées)

Un ensemble `visited` évite de revisiter les mêmes pages. Les liens hors du domaine de la classe sont ignorés.

---

## 📋 Mode simulation

Avec `--simulation`, aucun fichier n'est écrit. Le script affiche à la place la liste de tous les documents qu'il aurait téléchargés :

```
[SIMULATION] 23 documents trouvés :
  Mathematiques/cours_algebre.pdf     (https://cahier-de-prepa.fr/ma-classe/download?id=12)
  Mathematiques/td_matrices.pdf       (https://cahier-de-prepa.fr/ma-classe/download?id=13)
  Physique/cours_mecanique.pdf        (https://cahier-de-prepa.fr/ma-classe/download?id=21)
  ...
```

---

## 🧩 Dépendances

| Bibliothèque | Rôle | Obligatoire |
|---|---|---|
| `requests` | Requêtes HTTP, gestion des cookies | ✅ oui |
| `beautifulsoup4` | Parsing HTML pour l'extraction des liens | non (fallback regex) |
| `colorama` | Couleurs terminal | non |

Sans `beautifulsoup4`, le script utilise des expressions régulières pour extraire les liens — moins robuste mais fonctionnel dans la majorité des cas.

---

## 💡 Conseils d'utilisation

- **Premier lancement** : utiliser `--simulation` pour vérifier ce que le script trouve avant de télécharger
- **Gros volume** : exporter avec `--liste` puis télécharger avec `telechargeur_batch.py --threads 4`
- **Usage régulier** : sauvegarder les cookies (`--cookie-sortie`) pour relancer rapidement sans re-saisir les identifiants
- **Profondeur** : augmenter `--profondeur` si certaines sous-pages ne sont pas crawlées (défaut 3 convient à la plupart des classes)
