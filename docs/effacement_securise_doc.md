# 🗑️ effacement_securise.py — Documentation

Écrase le contenu d'un fichier plusieurs fois avec des données aléatoires ou des motifs fixes avant de le supprimer, rendant la récupération très difficile voire impossible.

**⚠️ Cette opération est irréversible. Aucune corbeille, aucun undo.**

---

## 🚀 Utilisation rapide

```bash
# Effacer un fichier (méthode DoD par défaut, confirmation requise)
python effacement_securise.py secret.pdf

# Voir ce qui serait effacé sans effacer
python effacement_securise.py ./dossier --recursif --simulation

# Effacer avec 7 passes et afficher chaque passe
python effacement_securise.py secret.pdf --methode dod7 --verbose

# Effacer plusieurs fichiers
python effacement_securise.py a.pdf b.docx c.jpg
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `cibles` | positional(s) | — | Fichier(s) ou dossier(s) à effacer |
| `-m / --methode` | choix | `dod` | Méthode d'effacement (voir tableau ci-dessous) |
| `-r / --recursif` | flag | non | Effacer tous les fichiers dans un dossier |
| `-s / --simulation` | flag | non | Lister sans effacer |
| `-v / --verbose` | flag | non | Afficher chaque passe d'écrasement |

---

## 🔄 Méthodes d'effacement

| Méthode | Passes | Description | Usage recommandé |
|---------|--------|-------------|-----------------|
| `simple` | 1 | Aléatoire | Suppression rapide, usage quotidien |
| `dod` | 3 | 0x00 → 0xFF → aléatoire (DoD 5220.22-M) | **Par défaut** — bon compromis |
| `dod7` | 7 | Variante DoD renforcée | Documents très sensibles, HDD |
| `gutmann` | 35 | Méthode Gutmann complète | Inutile sur SSD, overkill sur HDD moderne |

### Détail des passes DoD (3 passes)

| Passe | Données écrites |
|-------|----------------|
| 1 | Tous les bits à 0 (`0x00 0x00 0x00...`) |
| 2 | Tous les bits à 1 (`0xFF 0xFF 0xFF...`) |
| 3 | Données aléatoires (`os.urandom`) |

Après chaque passe : `flush()` + `fsync()` pour forcer l'écriture sur le disque.

---

## ⚠️ Note importante sur les SSD

L'écrasement multiple est **moins efficace sur les SSD, NVMe et clés USB** en raison du *wear-leveling* : le contrôleur du SSD peut écrire les nouvelles données sur des cellules différentes des originales, laissant les données sensibles potentiellement accessibles dans d'autres blocs physiques.

**Sur SSD, préférer :**
- Le **chiffrement intégral du disque** (BitLocker sur Windows, FileVault sur macOS, LUKS sur Linux)
- Ou `chiffrer_dossier.py` pour les archives sensibles avant suppression normale

Sur **HDD mécanique classique**, la méthode DoD (3 passes) est largement suffisante.

---

## 🔐 Processus de confirmation

Le script demande une confirmation explicite avant tout effacement réel :

```
=== Effacement securise ===
Methode  : dod  —  3 passes — DoD 5220.22-M
Fichiers : 2

ATTENTION : cette operation est IRREVERSIBLE.
Tapez 'oui' pour confirmer l'effacement de 2 fichier(s) : oui

  secret.pdf    EFFACE
  notes.txt     EFFACE

---
  2 efface(s)  /  0 echec(s)
```

Il faut taper exactement `oui` (pas `o`, pas `yes`) pour valider.

---

## 💡 Cas d'usage combinés

```bash
# Chiffrer d'abord, puis effacer les originaux
python chiffrer_dossier.py ./documents
python effacement_securise.py ./documents --recursif --methode dod

# Nettoyer un dossier de photos avant revente d'un disque
python effacement_securise.py ./photos --recursif

# Simulation pour voir l'ampleur avant d'agir
python effacement_securise.py ./confidentiel --recursif --simulation
```
