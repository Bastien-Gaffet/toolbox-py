# 📥 importer_nouveautes.py — Documentation

Importe **uniquement les nouvelles** photos/vidéos d'une source (pCloud Drive, dossier téléchargé, carte SD…) vers un dossier de tri, **sans jamais reprendre** ce qui a déjà été trié, dédoublonné ou supprimé.

---

## 🧠 Le problème résolu

Les outils de comparaison classiques (`sync_dossiers.py`, `comparateur_dossiers.py`) comparent ce qui est **présent** sur le disque. Une photo supprimée pendant le tri n'est plus présente, donc elle revient à chaque synchronisation. Et comme `photos_manager.py --renommer` change les noms, on ne peut pas se fier aux noms non plus.

**Solution :** un registre permanent (`.import_registre.sqlite`, à la racine du dossier de tri) mémorise l'empreinte SHA-256 de tout ce qui a été vu. Il ne fait que grandir : supprimer une photo du disque **ne l'en retire pas**.

---

## 🧭 Assistant interactif (recommandé)

```bash
python importer_nouveautes.py
```

Sans argument, un menu pose les questions une par une (dossier de tri, dossiers cloud à surveiller, date du dernier import, confirmation…). Les réponses sont mémorisées dans `~/.importer_nouveautes.json` et proposées par défaut la fois suivante : on n'a plus qu'à appuyer sur Entrée.

| Menu | Rôle |
|---|---|
| Importer les nouveautés du cloud | Le flux habituel : compare, montre la liste, télécharge après confirmation, propose la sauvegarde |
| Importer depuis un dossier local | Carte SD, dossier téléchargé… (simulation puis confirmation) |
| Mise en place du registre | 1re fois : indexe le disque trié et marque l'ancien contenu du cloud comme déjà vu |
| Sauvegarder le dossier de tri | `robocopy` vers la sauvegarde (D:\Sauvegardes\main_tri par défaut). Ajout seulement par défaut : rien n'est supprimé de la sauvegarde ; miroir `/MIR` uniquement sur demande |
| Voir le registre | Résumé |

### Source cloud via rclone

Le cloud est lu avec [rclone](https://rclone.org) (remote déjà configuré par `rclone config`). Le flux :

1. `rclone lsjson` liste le cloud en ~2 s, **sans rien télécharger** ;
2. les fichiers déjà vus (nom + taille + date) sont écartés ;
3. pour les autres, l'empreinte SHA-256 est demandée **au cloud** (`rclone hashsum`, 16 en parallèle) et comparée au registre ;
4. seules les vraies nouveautés sont téléchargées (`rclone copy`, empreinte vérifiée par rclone).

### Changement de téléphone

Un nouveau téléphone réuploade souvent toutes les anciennes photos dans un nouveau dossier du cloud. Elles sont reconnues car :

- la mise en place mémorise l'**empreinte** de tout l'ancien contenu du cloud (pas seulement nom/date). C'est aussi la seule trace des photos rejetées puis supprimées définitivement du disque ;
- les copies d'un téléphone à l'autre sont identiques octet pour octet (vérifié sur pCloud : 203/204).

Filet de sécurité : un fichier inconnu mais daté d'avant la date de mise en place n'est pas importé en silence. L'assistant le liste et propose de l'importer à part (`_anciens_a_verifier`), de l'ignorer définitivement, ou de reporter la décision.

Si la config rclone est chiffrée, l'assistant demande son mot de passe (gardé en mémoire le temps de la session seulement).

---

## 🚀 Mise en place en ligne de commande (dossier local)

```bash
# 1. Mémoriser tout ce qui est déjà sur le disque trié (y compris la corbeille krino)
python importer_nouveautes.py indexer E:\Bastien\main_tri

# 2. Marquer l'ancien contenu de la source comme déjà vu, SANS le télécharger :
#    tout ce qui a été modifié avant la date du dernier import manuel
python importer_nouveautes.py indexer E:\Bastien\main_tri P:\Photos --avant 2026-07-18
```

L'étape 2 couvre les photos **déjà supprimées définitivement** : on ne peut plus calculer leur empreinte, donc on se base sur la date.

## 🔁 À chaque fois

```bash
python importer_nouveautes.py importer E:\Bastien\main_tri P:\Photos --simulation
python importer_nouveautes.py importer E:\Bastien\main_tri P:\Photos
```

Les nouveautés sont copiées dans `main_tri/_A_TRIER/import_<date>/` (arborescence de la source conservée), avec un `_journal_import.csv`. Il ne reste qu'à les trier (krino, `photos_manager.py`…) : ce qui sera supprimé ne reviendra plus.

```bash
python importer_nouveautes.py statut E:\Bastien\main_tri
```

---

## ⚙️ Arguments

| Commande | Argument / option | Description |
|---|---|---|
| `indexer` | `racine` | Dossier de tri (le registre y est stocké) |
| | `dossiers...` | Dossiers à indexer (défaut : la racine) |
| | `--avant AAAA-MM-JJ` | Marque comme vus les fichiers modifiés avant cette date, sans les lire |
| | `--tout` | Tous les fichiers, pas seulement photos/vidéos |
| `importer` | `racine source` | Dossier de tri, dossier source |
| | `-s / --simulation` | Affiche ce qui serait importé, ne copie rien |
| | `--vers NOM` | Nom du sous-dossier dans `_A_TRIER/` |
| | `--sans-reindex` | Ne pas réindexer le dossier de tri avant l'import |
| | `--tout` | Tous les fichiers |
| `statut` | `racine` | Résumé du registre |

---

## 🔍 Comment un fichier source est décidé

1. **Déjà vu** (nom + taille + date déjà rencontrés) → sauté **sans être lu**. C'est ce qui rend les passages suivants rapides sur pCloud Drive (pas de retéléchargement).
2. Sinon, calcul SHA-256 → **contenu déjà connu** (présent sur le disque, importé avant, ou supprimé depuis) → sauté.
3. **Doublon à l'intérieur de la source** → importé une seule fois.
4. Sinon → **copié** (`copy2`, taille vérifiée) puis enregistré dans le registre.

`importer` réindexe d'abord le dossier de tri pour prendre en compte les photos ajoutées à la main. Un cache évite de relire les fichiers déjà hashés, même s'ils ont été déplacés.

---

## 🛡️ Sécurité des données

- L'outil ne supprime **jamais** de fichier du disque ni du cloud : rclone copie dans un seul sens (cloud → disque). Vider le cloud ou en perdre l'accès ne touche pas au disque.
- Le registre conserve les empreintes de l'ancien contenu du cloud : il reste valable même si le cloud est vidé. **Faire la mise en place tant que le cloud est accessible.**

## ⚠️ Limites

- Une photo **modifiée** (recadrée, retouchée, EXIF nettoyé par `metadata_cleaner.py`) a une nouvelle empreinte : elle sera considérée comme nouvelle.
- `--avant` se base sur la date de modification des fichiers de la source. Elle est fiable sur pCloud Drive, mais pas sur un dossier téléchargé dont les dates n'ont pas été conservées.
- Ne supprime **jamais** le registre `.import_registre.sqlite` : c'est la mémoire du tri. Il est inclus dans la sauvegarde du dossier.
