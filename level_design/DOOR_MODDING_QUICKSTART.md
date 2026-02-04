# 🚪 Modification des Portes - Quick Start

## ✅ Système Complet Créé!

Vous pouvez maintenant **modifier les portes** et réinjecter dans le jeu:
- ✅ Débloquer des portes
- ✅ Retirer les clés requises
- ✅ Changer les destinations
- ✅ Créer des shortcuts

---

## 🚀 Utilisation (5 minutes)

### Option 1: Débloquer Toutes les Portes

```bash
# 1. Copier le preset
copy door_presets\unlock_all_doors.json door_modifications.json

# 2. Appliquer
py -3 patch_doors.py

# 3. Réinjecter dans le BIN
cd ..
py -3 patch_blaze_all.py

# 4. Tester dans l'émulateur!
```

**Résultat:** Toutes les portes seront ouvertes (UNLOCKED)

---

### Option 2: Enlever les Clés

```bash
# 1. Copier le preset
copy door_presets\remove_key_requirements.json door_modifications.json

# 2. Appliquer
py -3 patch_doors.py

# 3. Réinjecter
cd ..
py -3 patch_blaze_all.py
```

**Résultat:** Les portes gardent leur apparence mais ne nécessitent plus de clé

---

### Option 3: Modification Personnalisée

```bash
# 1. Éditer la configuration
notepad door_modifications.json

# 2. Modifier selon besoin (voir exemples ci-dessous)

# 3. Appliquer
py -3 patch_doors.py

# 4. Réinjecter
cd ..
py -3 patch_blaze_all.py
```

---

## 📝 Exemples Rapides

### Débloquer une Porte Spécifique

**Éditer door_modifications.json:**
```json
{
  "modifications": [
    {
      "name": "Unlock Castle Door",
      "offset": "0x100000",
      "new_type": 0,
      "new_key_id": 0,
      "enabled": true
    }
  ]
}
```

### Créer un Shortcut

```json
{
  "modifications": [
    {
      "name": "Shortcut to Boss",
      "offset": "0x100010",
      "new_type": 0,
      "new_dest_id": 10,
      "enabled": true
    }
  ]
}
```

### Changer de Clé

```json
{
  "modifications": [
    {
      "name": "Use Different Key",
      "offset": "0x100020",
      "new_key_id": 5,
      "enabled": true
    }
  ]
}
```

---

## 🎮 Types de Portes

```
0 = UNLOCKED         (Toujours ouverte)
1 = KEY_LOCKED       (Nécessite clé)
2 = MAGIC_LOCKED     (Sort magique)
3 = DEMON_ENGRAVED   (Item démon)
4 = GHOST_ENGRAVED   (Item fantôme)
5 = EVENT_LOCKED     (Boss battu)
6 = BOSS_DOOR        (Porte de boss)
7 = ONE_WAY          (Sens unique)
```

---

## 🔍 Trouver les Offsets

### Méthode 1: Unity

1. Visualiser avec CompleteVisualization.cs
2. Cliquer sur une porte
3. Noter la position
4. Chercher dans door_positions.csv
5. Récupérer l'offset

### Méthode 2: CSV Direct

**Ouvrir:** `door_positions.csv`
```csv
offset,x,y,z,type,type_desc,key_id,dest_id,flags
0x100000,768,384,1536,1,Key Locked,12,5,0x0001
```

**Colonne 1** = Offset à utiliser

### Méthode 3: JSON

**Ouvrir:** `door_analysis.json`
```json
{
  "offset": "0x100000",
  "type_description": "Key Locked",
  "key_id": 12
}
```

---

## 📁 Fichiers Créés

```
level_design/
├── patch_doors.py                   ⭐ Script de patching
├── door_modifications.json          ⭐ Configuration (à éditer)
├── door_presets/
│   ├── unlock_all_doors.json        ⭐ Preset: tout débloquer
│   └── remove_key_requirements.json ⭐ Preset: enlever clés
├── DOOR_PATCHING_GUIDE.md           📖 Guide complet
└── DOOR_MODDING_QUICKSTART.md       📖 Ce fichier
```

---

## ⚠️ Sécurité

### Backup Automatique

Le script crée automatiquement:
```
work/BLAZE.ALL.backup
```

### Restaurer si Problème

```bash
cd work
copy BLAZE.ALL.backup BLAZE.ALL
```

---

## 🎯 Workflow Complet

```
1. Identifier portes (Unity ou CSV)
   |
2. Créer/éditer configuration
   |
3. py -3 patch_doors.py
   |
4. cd .. && py -3 patch_blaze_all.py
   |
5. Tester dans émulateur
   |
6. Si OK: Garder
   Si KO: Restaurer backup
```

---

## 💡 Use Cases

### Speedrun
```bash
copy door_presets\unlock_all_doors.json door_modifications.json
py -3 patch_doors.py
```
→ Accès direct aux boss

### Exploration
```bash
copy door_presets\unlock_all_doors.json door_modifications.json
py -3 patch_doors.py
```
→ Visiter tous les niveaux

### Debug/Test
```
Débloquer zones spécifiques
+ Shortcuts vers zones test
```

---

## 📊 Statistiques

**Portes Trouvées:** 50 structures
**Presets Disponibles:** 2
**Types Supportés:** 8 (0-7)

---

## ✅ Checklist

### Installation
- [x] patch_doors.py créé
- [x] door_modifications.json créé
- [x] Presets générés
- [x] Guide disponible

### Utilisation
- [ ] Configuration choisie (preset ou manuel)
- [ ] Script exécuté (patch_doors.py)
- [ ] BLAZE.ALL patché
- [ ] BIN réinjecté (patch_blaze_all.py)
- [ ] Testé in-game

---

## 🐛 Troubleshooting Rapide

**Modifications pas appliquées?**
→ Vérifier `"enabled": true`

**Porte toujours locked?**
→ Set `"new_type": 0` ET `"new_key_id": 0`

**Crash au passage?**
→ Enlever `"new_dest_id"` (mettre `null`)

**Erreur "Invalid offset"?**
→ Vérifier format: `"0x100000"` (avec 0x)

---

## 📖 Documentation Complète

**Guide détaillé:** `DOOR_PATCHING_GUIDE.md`

Contient:
- Tous les exemples
- Formats détaillés
- Troubleshooting complet
- Templates

---

**Prêt à modifier! 🚪✨**

**Commencer:**
```bash
# Débloquer tout
copy door_presets\unlock_all_doors.json door_modifications.json
py -3 patch_doors.py

# Ou manuel
notepad door_modifications.json
```
