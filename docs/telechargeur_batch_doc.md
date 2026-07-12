# 📥 telechargeur_batch.py — Documentation

Télécharge en parallèle une liste d'URLs depuis un fichier texte, avec reprise après interruption, vérification d'intégrité SHA-256 et support des cookies de session.

---

## 🚀 Utilisation rapide

```bash
# Télécharger une liste d'URLs
python telechargeur_batch.py liste.txt

# Avec dossier de sortie et cookies
python telechargeur_batch.py liste.txt -s ./telechargements --cookie "session=abc123"

# Avec fichier de cookies (format Netscape ou clé=valeur)
python telechargeur_batch.py liste.txt --cookie-fichier cookies.txt

# 4 téléchargements simultanés, rapport CSV
python telechargeur_batch.py liste.txt -t 4 --csv rapport.csv
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `fichier` | positional | — | Fichier texte contenant les URLs à télécharger |
| `-s / --sortie DIR` | string | `./telechargements` | Dossier de destination |
| `--cookie "N=V; ..."` | string | — | Cookies à envoyer (format HTTP : `Nom=Valeur; Nom2=Valeur2`) |
| `--cookie-fichier` | string | — | Fichier de cookies (format Netscape/texte ligne par ligne) |
| `-t / --threads N` | int | 3 | Téléchargements simultanés |
| `-r / --retries N` | int | 3 | Tentatives en cas d'échec |
| `--timeout S` | int | 30 | Timeout de connexion en secondes |
| `--csv FICHIER` | string | — | Exporter le rapport de téléchargement en CSV |

---

## 📄 Format du fichier d'URLs

Chaque ligne du fichier texte suit ce format :

```
URL [nom_fichier] [sha256:empreinte]
```

| Champ | Obligatoire | Description |
|-------|-------------|-------------|
| `URL` | ✅ oui | L'URL complète à télécharger |
| `nom_fichier` | non | Nom de fichier souhaité (sinon déduit automatiquement) |
| `sha256:HASH` | non | Empreinte SHA-256 pour vérifier l'intégrité |

Les lignes vides et commençant par `#` sont ignorées.

**Exemples :**

```
# Cours de maths
https://cahier-de-prepa.fr/ma-classe/download?id=42 cours_maths.pdf
https://cahier-de-prepa.fr/ma-classe/download?id=43 sha256:a1b2c3d4e5f6...
https://example.com/fichier.zip
```

---

## 🔄 Reprise après interruption

Si un téléchargement est interrompu, le fichier partiel est conservé avec l'extension `.part`. Au prochain lancement, le script reprend automatiquement depuis là où il s'était arrêté grâce à l'en-tête HTTP `Range`.

Le serveur doit supporter les téléchargements par morceaux (`Accept-Ranges: bytes`). Sinon, le fichier est retéléchargé depuis le début.

---

## 🔐 Support des cookies

Les cookies permettent de télécharger des fichiers derrière une authentification.

**Via ligne de commande :**
```bash
python telechargeur_batch.py liste.txt --cookie "CDP_SESSION_PERM=abc123; autre=val"
```

**Via fichier texte** (format Netscape ou simplifié) :
```
# Netscape HTTP Cookie File
.exemple.fr	TRUE	/	FALSE	0	SESSION	abc123
```

---

## 📊 Affichage en cours de téléchargement

```
[=>.........]  4,5 Mo / 10,0 Mo  (1,2 Mo/s)  ETA: 4s   cours_maths.pdf
[==========>]  8,2 Mo / 8,2 Mo   (2,1 Mo/s)  OK        exercices.pdf
[ERR] connexion_refused           timeout     erreur.pdf
```

Les téléchargements en parallèle s'affichent ligne par ligne sans se mélanger (verrou de thread).

---

## ✅ Vérification d'intégrité

Si une empreinte SHA-256 est fournie dans le fichier d'URLs, le script la compare après téléchargement. En cas de non-concordance, le fichier est supprimé et le téléchargement est signalé comme échoué.

```
[SHA256 OK]  cours_maths.pdf
[SHA256 ERR] exercices.pdf — fichier corrompu ou modifié
```

---

## 📤 Rapport CSV

Avec `--csv rapport.csv`, un rapport est généré avec les colonnes :

```
URL ; Fichier ; Statut ; Taille ; Durée (s) ; Erreur
```

Statuts possibles : `OK`, `ERREUR`, `SHA256_INVALIDE`, `IGNORE`

---

## 💡 Cas d'usage

- **Archives** : télécharger une liste de fichiers volumineux en parallèle avec reprise
- **Sauvegardes** : récupérer des fichiers depuis un serveur avec vérification d'intégrité
- **Ressources pédagogiques** : Moodle, ENT, portails universitaires avec cookies exportés
