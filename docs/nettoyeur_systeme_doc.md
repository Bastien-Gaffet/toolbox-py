# 🧽 nettoyeur_systeme.py — Documentation

Identifie et supprime les fichiers qui s'accumulent au fil du temps : caches des navigateurs, dossiers temporaires Windows, miniatures, rapports de crash, logs anciens. Affiche l'espace récupérable avant d'agir.

**Mode simulation par défaut** — utiliser `--forcer` pour nettoyer réellement.

---

## 🚀 Utilisation rapide

```bash
# Voir l'espace récupérable (simulation, sans danger)
python nettoyeur_systeme.py

# Nettoyer réellement
python nettoyeur_systeme.py --forcer

# Inclure les fichiers .log de plus de 30 jours
python nettoyeur_systeme.py --forcer --logs

# Logs de plus de 7 jours
python nettoyeur_systeme.py --forcer --logs --age-logs 7
```

---

## ⚙️ Arguments

| Argument | Type | Défaut | Description |
|----------|------|--------|-------------|
| `-f / --forcer` | flag | non | Nettoyer réellement (sans ce flag : simulation uniquement) |
| `--logs` | flag | non | Inclure les fichiers `.log` et `.dmp` anciens |
| `--age-logs JOURS` | int | 30 | Âge minimum des logs à supprimer |

---

## 🗂️ Cibles nettoyées sur Windows

| Cible | Chemin | Description |
|-------|--------|-------------|
| TEMP utilisateur | `%TEMP%` | Fichiers temporaires de session |
| Cache miniatures | `%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db` | Base de données des aperçus |
| Cache Internet | `%LOCALAPPDATA%\Microsoft\Windows\INetCache` | Cache IE / Windows |
| Rapports de crash | `%LOCALAPPDATA%\CrashDumps` | Fichiers `.dmp` de plantage |
| Cache Chrome | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache\Cache_Data` | Cache Google Chrome |
| Cache Edge | `%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache\Cache_Data` | Cache Microsoft Edge |
| Cache Firefox | `%APPDATA%\Mozilla\Firefox\Profiles\*.default*\cache2` | Cache Mozilla Firefox |
| Logs (optionnel) | `%LOCALAPPDATA%\Temp`, `%WINDIR%\Logs` | Logs `.log` et `.dmp` |

Les caches navigateurs qui n'existent pas (navigateur non installé) sont automatiquement ignorés.

---

## 🐧 Sur Linux / macOS

| Cible | Chemin |
|-------|--------|
| Temp | `/tmp` |
| Cache Chrome | `~/.cache/google-chrome` |
| Cache Chromium | `~/.cache/chromium` |
| Cache Firefox | `~/.cache/mozilla` |
| Logs (optionnel) | `/var/log` (fichiers `.gz`, `.1`, `.old`) |

---

## 📋 Exemple de rapport (simulation)

```
=== Nettoyeur systeme === — Windows

  Mode : SIMULATION (utilisez --forcer pour nettoyer reellement)

  Analyse en cours...

  Cible                                      Fichiers       Taille
  ----------------------------------------------------------------
  Dossier TEMP utilisateur                       1247      412.3 Mo
  Cache miniatures Windows                          8       14.2 Mo
  Cache Internet Explorer / Windows               892      156.8 Mo
  Rapports de crash                                 3       45.0 Mo
  Cache Google Chrome                            5821      832.4 Mo
  Cache Microsoft Edge                           1204      123.5 Mo
  Cache Firefox (default-release)                2341      298.6 Mo
  ----------------------------------------------------------------
  Total                                         11516        1.9 Go

  Espace recuperable : 1.9 Go
  Relancez avec --forcer pour effectuer le nettoyage.
```

---

## ⚠️ Ce que le script ne fait pas

- Ne touche pas aux fichiers de profil des navigateurs (favoris, mots de passe, historique)
- Ne supprime pas les fichiers en cours d'utilisation (les erreurs sont signalées et ignorées)
- Ne vide pas la corbeille
- Pas d'accès aux dossiers système protégés (Prefetch, WinSxS) sans droits administrateur

---

## 💡 Fréquence recommandée

| Fréquence | Situation |
|-----------|-----------|
| Mensuelle | Usage normal |
| Hebdomadaire | Navigation intensive, nombreux téléchargements |
| Avant une sauvegarde | Réduire la taille de la sauvegarde |
| Avant une réinstallation | Libérer de l'espace sur C:\ |
