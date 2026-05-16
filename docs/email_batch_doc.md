# 📧 email_batch.py — Documentation

Envoie des emails personnalisés en masse depuis un fichier CSV. Supporte les templates HTML, les pièces jointes et un mode test pour prévisualiser sans envoyer.

---

## 🚀 Utilisation rapide

```bash
# Mode test — prévisualiser sans envoyer
python email_batch.py contacts.csv --sujet "Bonjour {{nom}}" --template corps.html --test

# Envoi réel
python email_batch.py contacts.csv \
    --sujet "Résultats {{annee}}" \
    --template corps.html \
    --smtp smtp.gmail.com --port 587 --login moi@gmail.com \
    --pj rapport.pdf

# Corps court en ligne
python email_batch.py contacts.csv --sujet "Info" --corps "Bonjour {{nom}} !" --test
```

---

## ⚙️ Arguments

### Contenu
| Argument | Description |
|----------|-------------|
| `csv` | Fichier CSV des destinataires |
| `--sujet TEXTE` | Sujet de l'email (supporte `{{variable}}`) |
| `--template FICHIER` | Fichier template `.txt` ou `.html` |
| `--corps TEXTE` | Corps du message court en ligne |
| `--pj FICHIER...` | Pièce(s) jointe(s) globale(s) |

### SMTP
| Argument | Variable d'env | Description |
|----------|---------------|-------------|
| `--smtp HOST` | `SMTP_HOST` | Serveur SMTP |
| `--port PORT` | `SMTP_PORT` | Port (défaut : 587) |
| `--login LOGIN` | `SMTP_LOGIN` | Identifiant SMTP |
| `--mdp MDP` | `SMTP_MDP` | Mot de passe (demandé si absent) |
| `--de EMAIL` | — | Adresse expéditeur (défaut : login) |

### Contrôle
| Argument | Description |
|----------|-------------|
| `--test` | Afficher un aperçu sans envoyer |
| `--delai S` | Délai entre envois en secondes (défaut : 1s) |
| `--limite N` | Envoyer seulement les N premiers |
| `--sep SEP` | Séparateur CSV (défaut : `;`) |

---

## 📄 Format du fichier CSV

La colonne `email` est obligatoire. Toutes les autres colonnes deviennent des variables disponibles dans le template.

```csv
email;nom;prenom;classe
alice@example.com;Dupont;Alice;MP2I
bob@example.com;Martin;Bob;MPSI
```

---

## ✏️ Système de template `{{variable}}`

Le template peut être un fichier `.txt` ou `.html`. Les variables sont substituées via `{{nom_colonne}}` :

**corps.html :**
```html
<html><body>
<p>Bonjour <b>{{prenom}} {{nom}}</b>,</p>
<p>Votre classe : <b>{{classe}}</b></p>
<p>Cordialement</p>
</body></html>
```

**Le sujet supporte aussi les variables :**
```
--sujet "Vos résultats — {{nom}} {{prenom}}"
```

Si une variable n'est pas trouvée dans le CSV, le placeholder `{{variable}}` est laissé tel quel (pas d'erreur).

---

## 🔐 Configuration SMTP

### Gmail
1. Activer la validation en 2 étapes
2. Générer un "Mot de passe d'application" (Compte Google → Sécurité → Mots de passe des applications)
3. Utiliser ce mot de passe (pas le mot de passe Gmail habituel)

```bash
python email_batch.py contacts.csv --smtp smtp.gmail.com --port 587 --login moi@gmail.com
```

### Variables d'environnement (recommandé)
Évitez de passer les credentials en ligne de commande :

```bash
# PowerShell
$env:SMTP_HOST = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SMTP_LOGIN = "moi@gmail.com"
$env:SMTP_MDP = "mot_de_passe_application"

python email_batch.py contacts.csv --sujet "Bonjour" --template corps.html --test
```

### Serveurs SMTP courants

| Fournisseur | Serveur | Port | Note |
|-------------|---------|------|------|
| Gmail | `smtp.gmail.com` | 587 | Mot de passe d'application requis |
| Outlook/Hotmail | `smtp.office365.com` | 587 | |
| Yahoo | `smtp.mail.yahoo.com` | 587 | |
| Mailtrap (tests) | `sandbox.smtp.mailtrap.io` | 587 | Pas d'envoi réel, boîte de test |
| OVH | `ssl0.ovh.net` | 587 | |

---

## 📋 Exemple de mode test

```
=== Email batch ===
  CSV          : contacts.csv  (3 destinataire(s))
  Sujet        : Vos résultats — Dupont Alice
  PJ           : rapport.pdf

  MODE TEST — apercu des 3 premiers emails :

  To      : alice@example.com
  Sujet   : Vos résultats — Dupont Alice
  Corps   :
    Bonjour Alice Dupont,
    Votre classe : MP2I
    Cordialement

  To      : bob@example.com
  ...

  3 email(s) auraient ete envoyes.
```

---

## ⚠️ Bonnes pratiques

- **Toujours tester avec `--test` avant d'envoyer** — prévisualise les 3 premiers emails
- **Utiliser `--limite 1` pour un premier envoi de test réel** vers une adresse de test
- **Respecter le délai `--delai`** pour ne pas être bloqué par les filtres anti-spam
- **Ne pas passer le mot de passe en argument** si la commande est dans l'historique shell — utiliser les variables d'environnement
