# 📡 scan_reseau.py — Documentation

Scanne le réseau local pour découvrir les appareils connectés, leurs adresses MAC, le fabricant du matériel et les ports ouverts.

---

## 🚀 Utilisation rapide

```bash
# Scan basique (détection automatique du réseau)
python scan_reseau.py

# Scan avec ports ouverts et fabricants
python scan_reseau.py --ports --vendeur

# Cibler un réseau spécifique et exporter
python scan_reseau.py --reseau 192.168.0.0/24 --ports --csv scan.csv
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `--reseau CIDR` | string | auto | Réseau à scanner en notation CIDR (ex: `192.168.1.0/24`) |
| `--ports` | flag | non | Scanner les ports courants sur chaque hôte actif |
| `--vendeur` | flag | non | Identifier le fabricant via l'adresse MAC (nécessite internet) |
| `--sans-dns` | flag | non | Ne pas résoudre les noms d'hôtes (plus rapide) |
| `--threads N` | int | 100 | Threads simultanés pour le ping sweep |
| `--timeout MS` | int | 800 | Timeout du ping en millisecondes |
| `--csv FICHIER` | string | — | Exporter les résultats dans un fichier CSV |

---

## 🔍 Ce que le script détecte

Pour chaque hôte actif, le script remonte :

| Information | Source | Toujours disponible |
|-------------|--------|---------------------|
| **Adresse IP** | ping sweep | ✅ oui |
| **Nom d'hôte** | résolution DNS inverse | selon le réseau |
| **Adresse MAC** | table ARP du système | après le ping |
| **Fabricant** | API macvendors.com | avec `--vendeur` + internet |
| **Ports ouverts** | connexion TCP | avec `--ports` |

---

## 🔌 Ports scannés avec `--ports`

| Port | Service | Port | Service |
|------|---------|------|---------|
| 21 | FTP | 445 | SMB |
| 22 | SSH | 548 | AFP |
| 23 | Telnet | 993 | IMAPS |
| 25 | SMTP | 995 | POP3S |
| 53 | DNS | 1883 | MQTT |
| 80 | HTTP | 3306 | MySQL |
| 110 | POP3 | 3389 | RDP |
| 139 | NetBIOS | 5900 | VNC |
| 143 | IMAP | 8080 | HTTP-alt |
| 443 | HTTPS | 9100 | Imprimante |

---

## 📤 Export CSV

Le fichier CSV généré avec `--csv` contient les colonnes :

```
IP ; Nom ; MAC ; Fabricant ; Ports ouverts
```

Exemple de ligne :
```
192.168.1.42 ; mon-pc ; AA:BB:CC:DD:EE:FF ; Dell Inc. ; 22/SSH | 80/HTTP | 3389/RDP
```

Compatible LibreOffice Calc et Excel (délimiteur `;`).

---

## 📋 Exemples de sortie terminal

```
IP locale détectée : 192.168.1.10
Réseau cible       : 192.168.1.0/24

Scan de 254 adresses (100 threads simultanés)...

  12 hôte(s) actif(s) trouvé(s)

======================================================================
  RÉSEAU LOCAL : 192.168.1.0/24
======================================================================
  Hôtes actifs : 12   —   Généré le 2026-05-16 14:30

  192.168.1.1         router.home
    MAC     : AA:BB:CC:11:22:33  (TP-Link Corporation Limited)
    Ports   : 80/HTTP | 443/HTTPS

  192.168.1.42        mon-pc
    MAC     : DD:EE:FF:44:55:66  (Dell Inc.)
    Ports   : 3389/RDP

  192.168.1.101
    MAC     : 11:22:33:AA:BB:CC  (Apple Inc.)
    Ports   : 5900/VNC
```

---

## ⚡ Performances

| Mode | Temps estimé (réseau /24) |
|------|--------------------------|
| Ping seul | 5–15 secondes |
| Ping + ports | 30–60 secondes |
| Ping + ports + vendeurs | 2–5 minutes (rate limit API) |

Le rate limit de l'API macvendors.com est de 1 requête/seconde — le script insère automatiquement un délai de 0,8 s entre chaque appel et met en cache les résultats pour éviter les doublons.

---

## 🖥️ Compatibilité

- Windows : utilise `ping -n 1 -w MS` et `arp -a`
- Linux / macOS : utilise `ping -c 1 -W S` et `ip neigh` (ou `arp -n`)
- Aucune bibliothèque externe requise (stdlib uniquement)
- `colorama` optionnel pour les couleurs terminal

---

## 💡 Cas d'usage

- **Inventaire réseau** : quels appareils sont connectés chez soi ?
- **Détection d'intrus** : un appareil inconnu est-il sur le réseau ?
- **Audit de services** : quels ports sont exposés sur chaque machine ?
- **NAS / imprimantes** : trouver l'IP d'un appareil sans écran
