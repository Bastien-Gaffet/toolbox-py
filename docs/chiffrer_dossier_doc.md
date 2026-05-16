# 🔐 chiffrer_dossier.py — Documentation

Chiffre un dossier entier dans une archive `.enc` protégée par mot de passe, ou déchiffre une archive existante. Utilise AES-256-GCM avec dérivation de clé PBKDF2-HMAC-SHA256.

**⚠️ Important : si le mot de passe est perdu, les données sont définitivement inaccessibles.**

---

## 🚀 Utilisation rapide

```bash
# Chiffrer un dossier (crée documents.enc)
python chiffrer_dossier.py ./documents

# Chiffrer vers un fichier spécifique
python chiffrer_dossier.py ./documents --sortie archive_2026.enc

# Déchiffrer
python chiffrer_dossier.py --dechiffrer documents.enc

# Déchiffrer vers un dossier spécifique
python chiffrer_dossier.py --dechiffrer archive.enc --sortie ./restaure

# Simuler sans créer de fichier
python chiffrer_dossier.py ./documents --simulation
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `source` | positional | — | Dossier à chiffrer, ou archive `.enc` à déchiffrer |
| `-d / --dechiffrer` | flag | non | Mode déchiffrement |
| `-s / --sortie CHEMIN` | string | auto | Fichier `.enc` de sortie ou dossier de destination |
| `--mdp MDP` | string | — | Mot de passe (demandé de façon sécurisée si absent) |
| `--compression N` | int 0-9 | 6 | Niveau de compression ZIP avant chiffrement |
| `--simulation` | flag | non | Simuler sans écrire de fichier |

---

## 🔒 Fonctionnement technique

Le processus de chiffrement se déroule en 3 étapes :

```
Dossier source
    ↓ compression ZIP
Archive ZIP (en mémoire)
    ↓ PBKDF2-HMAC-SHA256 (600 000 itérations) → clé AES-256
    ↓ AES-256-GCM avec nonce aléatoire 12 octets
Archive chiffrée (.enc)
```

### Format du fichier `.enc`

```
[TBXENC01] [SEL 32o] [NONCE 12o] [DONNÉES CHIFFRÉES + TAG 16o]
```

| Champ | Taille | Description |
|-------|--------|-------------|
| Signature | 8 octets | `TBXENC01` — identifie le format |
| Sel | 32 octets | Aléatoire, unique à chaque chiffrement |
| Nonce | 12 octets | Aléatoire, unique à chaque chiffrement |
| Données | reste | ZIP chiffré AES-256-GCM + tag d'authenticité 16 octets |

### Propriétés de sécurité

- **AES-256-GCM** — chiffrement authentifié : détecte toute modification du fichier
- **PBKDF2 600 000 itérations** — ralentit les attaques par force brute (~1 s/tentative)
- **Sel unique** — deux chiffrements du même dossier avec le même mot de passe produisent des archives différentes
- **Tag GCM** — mot de passe incorrect → erreur immédiate, aucune donnée corrompue extraite

---

## 🗜️ Niveaux de compression

| Niveau | Description | Vitesse | Taille |
|--------|-------------|---------|--------|
| 0 | Aucune compression | Très rapide | Identique à la source |
| 1-3 | Légère | Rapide | Réduction modérée |
| 6 (défaut) | Standard | Moyen | Bon équilibre |
| 9 | Maximum | Lent | Taille minimale |

La compression est appliquée avant le chiffrement. Pour des archives déjà compressées (ZIP, MP4, JPEG), le niveau 0 est préférable.

---

## ⚠️ Limites

- Le dossier entier est chargé en mémoire (via ZIP) avant chiffrement — **déconseillé pour les volumes > 2 Go**
- La dérivation PBKDF2 prend quelques secondes (c'est voulu — c'est une protection)
- Dépendance : `cryptography` (`pip install cryptography`)

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Archiver des documents fiscaux | `python chiffrer_dossier.py ./impots_2026` |
| Sauvegarder des mots de passe ou clés | `python chiffrer_dossier.py ./secrets --compression 0` |
| Transférer des fichiers sensibles | Chiffrer → envoyer `.enc` → déchiffrer à destination |
| Archiver avant suppression | `python chiffrer_dossier.py ./projet` puis `python effacement_securise.py ./projet --recursif` |
