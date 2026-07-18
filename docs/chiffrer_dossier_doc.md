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
| `--compression N` | int 0-9 | 0 | Niveau de compression ZIP avant chiffrement (0 = stockage, idéal pour photos/vidéos) |
| `--simulation` | flag | non | Simuler sans écrire de fichier |

---

## 🔒 Fonctionnement technique

Le chiffrement se fait **en flux**, par morceaux de 4 Mo, écrits directement sur le
disque — **aucun pic mémoire**, adapté aux gros dossiers :

```
Dossier source
    ↓ archivage ZIP → fichier temporaire sur disque
    ↓ PBKDF2-HMAC-SHA256 (600 000 itérations) → clé AES-256   [une seule fois, en RAM]
    ↓ lecture par morceaux de 4 Mo → AES-256-GCM par morceau
Archive chiffrée (.enc)         [le ZIP temporaire est ensuite supprimé]
```

> Les 600 000 itérations PBKDF2 sont un **calcul CPU fait une seule fois** pour dériver
> la clé — elles n'écrivent rien sur le disque et ne l'usent pas.

### Format du fichier `.enc` (TBXENC02)

```
[TBXENC02] [SEL 32o] [NONCE_BASE 12o] [ morceaux... ]
   morceau : [LONGUEUR 4o] [CHIFFRÉ + TAG 16o]
```

| Champ | Taille | Description |
|-------|--------|-------------|
| Signature | 8 octets | `TBXENC02` — format en flux |
| Sel | 32 octets | Aléatoire, unique à chaque chiffrement |
| Nonce de base | 12 octets | Aléatoire ; le nonce du morceau _i_ = base + _i_ |
| Morceaux | reste | Chacun : longueur + données AES-256-GCM (tag 16 o inclus) |

Chaque morceau est authentifié avec, en données associées (AAD), son **numéro** et un
**drapeau « dernier morceau »**. Cela détecte non seulement toute modification, mais
aussi la **réorganisation** et la **troncature** (retirer un morceau final invalide la
vérification).

> Les archives de l'ancien format monobloc `TBXENC01` restent **déchiffrables**
> (rétrocompatibilité automatique).

### Propriétés de sécurité

- **AES-256-GCM** — chiffrement authentifié : détecte toute modification du fichier
- **PBKDF2 600 000 itérations** — ralentit les attaques par force brute (~1 s/tentative)
- **Sel unique** — deux chiffrements du même dossier avec le même mot de passe produisent des archives différentes
- **Nonce par morceau + AAD numérotée** — mot de passe incorrect, corruption, réorganisation ou troncature → erreur immédiate, aucune donnée corrompue extraite

---

## 🗜️ Niveaux de compression

| Niveau | Description | Vitesse | Taille |
|--------|-------------|---------|--------|
| 0 (défaut) | Aucune compression | Très rapide | Identique à la source |
| 1-3 | Légère | Rapide | Réduction modérée |
| 6 | Standard | Moyen | Bon équilibre |
| 9 | Maximum | Lent | Taille minimale |

La compression est appliquée avant le chiffrement. Le défaut est **0** car les photos et
vidéos (JPEG, HEIC, MP4…) sont déjà compressées : compresser ne gagne rien et coûte du
temps. Pour un dossier de **texte/documents**, monter à `--compression 6`.

---

## ⚠️ Limites

- Traitement **en flux** : pas de limite de taille pratique (un ZIP temporaire est créé
  sur le même disque, il faut donc l'espace libre équivalent le temps de l'opération)
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
