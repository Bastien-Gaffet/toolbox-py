# 📊 moniteur_systeme.py — Documentation

Tableau de bord terminal rafraîchi en temps réel : utilisation CPU, RAM, disques, débit réseau, et processus les plus gourmands. Nécessite `psutil`.

---

## 🚀 Utilisation rapide

```bash
# Lancer le tableau de bord (refresh toutes les 2 secondes)
python moniteur_systeme.py

# Refresh plus lent, plus de processus
python moniteur_systeme.py --intervalle 5 --top 20

# Afficher une seule fois et quitter
python moniteur_systeme.py --une-fois

# Afficher le détail par cœur CPU, trier par RAM
python moniteur_systeme.py --cores --trier ram
```

Appuyer sur **Ctrl+C** pour quitter.

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `--intervalle S` | float | 2.0 | Secondes entre chaque rafraîchissement |
| `--top N` | int | 10 | Nombre de processus à afficher |
| `--trier {cpu,ram}` | choix | `cpu` | Critère de tri des processus |
| `--cores` | flag | non | Afficher l'utilisation de chaque cœur CPU |
| `--sans-temp` | flag | non | Ne pas afficher les températures |
| `--une-fois` | flag | non | Afficher une seule fois sans boucle |

---

## 📺 Exemple d'affichage

```
=== Moniteur systeme — 2026-05-16 14:32:05 — Refresh: 2s (Ctrl+C pour quitter) ===

  CPU total : [===========>........] 57.3%  —  8 coeur(s) logique(s)
    2200 MHz (max 4800 MHz)

  RAM       : [=========>..........] 47.8%  7.6 Go / 16.0 Go
  Swap      : [>.....................]  2.1%  0.2 Go / 8.0 Go

  Disques :
    C:\            [===========>........] 58.6%  149.9 Go / 256.0 Go
    D:\            [=>..................]  4.2%   84.0 Go / 2000.0 Go

  Reseau    :  envoye 145.2 Ko/s  |  recu 1.2 Mo/s

  Processus (top 10 par CPU) :
  PID     Nom                        CPU%      RAM
  18432   chrome.exe                 12.4%   1.8 Go
   4512   python.exe                  8.1%  82.0 Mo
   9876   Code.exe                    3.2% 312.0 Mo
   1234   explorer.exe                1.0% 156.0 Mo
    ...
```

---

## 🎨 Code couleur

| Couleur | Seuil | Signification |
|---------|-------|---------------|
| Vert | < 50% | Utilisation normale |
| Jaune | 50–79% | Charge modérée |
| Rouge | ≥ 80% | Charge élevée — attention |

Les barres, pourcentages et lignes de processus adoptent automatiquement la couleur selon le niveau de charge.

---

## 📡 Métriques affichées

### CPU
- Pourcentage total
- Détail par cœur avec `--cores`
- Fréquence actuelle et maximale

### RAM & Swap
- Utilisation en octets et pourcentage
- Swap affiché si le système en utilise

### Disques
- Toutes les partitions montées (hors CD-ROM)
- Espace utilisé / total

### Réseau
- Débit en envoi et réception (Mo/s ou Ko/s)
- Calculé entre deux mesures consécutives

### Températures
- Si exposées par le système (Windows : WMI requis, Linux : fichiers `/sys`)
- Masquables avec `--sans-temp`

### Processus
- Triables par CPU (défaut) ou RAM
- Affiche PID, nom, CPU%, RAM

---

## 📦 Dépendances

| Bibliothèque | Obligatoire | Installation |
|---|---|---|
| `psutil` | ✅ oui | `pip install psutil` |
| `colorama` | non | `pip install colorama` |

---

## 💡 Cas d'usage

| Situation | Commande |
|-----------|----------|
| Trouver quel processus ralentit tout | `--top 20 --trier cpu` |
| Surveiller la RAM pendant une compilation | `--intervalle 1 --trier ram` |
| Snapshot ponctuel avant de quitter | `--une-fois` |
| Vérifier l'utilisation disque en temps réel | `python moniteur_systeme.py` (section Disques) |
