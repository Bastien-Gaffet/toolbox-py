# 🌍 geo_ip.py — Documentation

Géolocalise une ou plusieurs **adresses IP** ou **noms de domaine** : pays, ville,
coordonnées GPS, fuseau horaire, fournisseur d'accès (FAI), organisation, numéro AS,
et des **indices de sécurité** (proxy/VPN, hébergeur/datacenter, réseau mobile).

Remplace un utilitaire externe `.exe` par du Python intégré à la boîte à outils.

---

## 📦 Dépendances

```bash
pip install requests
```

Aucune clé API : les données viennent de **[ip-api.com](https://ip-api.com)**, gratuit
(~45 requêtes/minute, en HTTP).

---

## 🚀 Utilisation

```bash
# Ma propre IP publique (+ mode interactif ensuite)
python geo_ip.py

# Une IP
python geo_ip.py 8.8.8.8

# Un domaine (résolu automatiquement)
python geo_ip.py github.com

# Plusieurs cibles d'un coup (une seule requête /batch)
python geo_ip.py 8.8.8.8 1.1.1.1 92.184.0.1

# Depuis un fichier (une IP/domaine par ligne, # = commentaire)
python geo_ip.py --fichier ips.txt

# Sortie JSON brute (pour scripts)
python geo_ip.py 8.8.8.8 --json
```

---

## ⚙️ Options

| Option | Rôle |
|--------|------|
| `cibles` | IP ou domaines (vide → votre IP publique) |
| `--fichier FICHIER` | Lire les cibles depuis un fichier (1 par ligne, `#` ignoré) |
| `--json` | Afficher la réponse JSON brute au lieu de l'affichage formaté |

---

## 📋 Informations affichées

| Champ | Exemple |
|-------|---------|
| 🌍 Pays | USA 🇺🇸 (US) |
| 📍 Localité | Ashburn, Virginie (20149) |
| 🧭 Coordonnées | 39.03, -77.5 |
| 🗺 Carte | lien OpenStreetMap cliquable |
| 🕒 Fuseau | America/New_York |
| 🏢 FAI | Google LLC |
| 🏷 Organisation | Google Public DNS |
| 🔗 AS | AS15169 Google LLC |
| 🔁 Reverse DNS | dns.google |
| ⚠️ Indices | proxy/VPN, hébergeur/datacenter, réseau mobile |

Pour un **domaine**, l'affichage montre la résolution : `github.com → 20.26.156.215`.

---

## 🔎 À quoi servent les « indices de sécurité »

- **proxy/VPN** — l'IP appartient à un service de proxy ou VPN connu (l'utilisateur
  masque probablement sa vraie localisation).
- **hébergeur/datacenter** — l'IP est celle d'un serveur (cloud, hébergement), pas
  d'un particulier. Typique des bots, des DNS publics, des services web.
- **réseau mobile** — connexion via un opérateur mobile (4G/5G).

Utile pour identifier rapidement la nature d'une IP vue dans des logs.

---

## ⚠️ Notes

- **Batch** : au-delà d'une cible, tout part en **une seule** requête `/batch`
  (jusqu'à 100 cibles), ce qui ménage la limite de débit.
- ip-api.com gratuit est en **HTTP** (non chiffré) — convient à un usage personnel.
  Pour du HTTPS ou un débit supérieur, ip-api propose une offre payante.
- Respecter la limite d'environ **45 requêtes/minute** en usage gratuit.
