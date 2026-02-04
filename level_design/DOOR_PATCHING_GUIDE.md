# Guide de Modification des Portes

## 🎯 Objectif

Modifier l'état des portes dans le jeu (ouvrir, changer clés, rediriger) et réinjecter dans le BIN.

---

## 🚀 Quick Start

### Option 1: Utiliser un Preset (Recommandé)

```bash
# 1. Générer les presets
py -3 patch_doors.py

# 2. Copier un preset
copy door_presets\unlock_all_doors.json door_modifications.json

# 3. Appliquer
py -3 patch_doors.py

# 4. Réinjecter dans le BIN
cd ..
py -3 patch_blaze_all.py
```

### Option 2: Configuration Personnalisée

```bash
# 1. Créer config par défaut
py -3 patch_doors.py

# 2. Éditer door_modifications.json
# 3. Relancer
py -3 patch_doors.py

# 4. Réinjecter
cd ..
py -3 patch_blaze_all.py
```

---

## 📖 Format de Configuration

### Structure du Fichier

**door_modifications.json:**
```json
{
  "modifications": [
    {
      "name": "Description de la modification",
      "offset": "0x100000",
      "current_type": 1,
      "new_type": 0,
      "new_key_id": 0,
      "new_dest_id": null,
      "comment": "Explications",
      "enabled": true
    }
  ]
}
```

### Paramètres

| Paramètre | Type | Description |
|-----------|------|-------------|
| **name** | string | Nom de la modification (pour log) |
| **offset** | string | Offset hex de la porte (depuis door_analysis.json) |
| **current_type** | int | Type actuel (optionnel, pour référence) |
| **new_type** | int/null | Nouveau type de porte (null = pas de changement) |
| **new_key_id** | int/null | Nouveau ID de clé (null = pas de changement) |
| **new_dest_id** | int/null | Nouvelle destination (null = pas de changement) |
| **comment** | string | Commentaire (ignoré) |
| **enabled** | bool | true = appliquer, false = ignorer |

### Types de Portes

```json
{
  "UNLOCKED": 0,         // Toujours ouverte
  "KEY_LOCKED": 1,       // Nécessite clé
  "MAGIC_LOCKED": 2,     // Nécessite sort magique
  "DEMON_ENGRAVED": 3,   // Nécessite item démon
  "GHOST_ENGRAVED": 4,   // Nécessite item fantôme
  "EVENT_LOCKED": 5,     // Nécessite événement (boss)
  "BOSS_DOOR": 6,        // Porte de boss
  "ONE_WAY": 7           // Sens unique
}
```

---

## 📝 Exemples de Modifications

### 1. Débloquer une Porte

**But:** Rendre une porte accessible sans clé

```json
{
  "name": "Unlock Castle Entrance",
  "offset": "0x100000",
  "new_type": 0,
  "new_key_id": 0,
  "new_dest_id": null,
  "enabled": true
}
```

### 2. Retirer Besoin de Clé (Garder Type)

**But:** Enlever la clé mais garder l'aspect locked

```json
{
  "name": "Remove Key from Magic Door",
  "offset": "0x100010",
  "new_type": null,
  "new_key_id": 0,
  "new_dest_id": null,
  "enabled": true
}
```

### 3. Changer de Clé

**But:** Utiliser une autre clé

```json
{
  "name": "Use Different Key",
  "offset": "0x100020",
  "new_type": null,
  "new_key_id": 5,
  "new_dest_id": null,
  "enabled": true
}
```

### 4. Rediriger une Porte

**But:** Changer la destination

```json
{
  "name": "Shortcut to Boss",
  "offset": "0x100030",
  "new_type": null,
  "new_key_id": null,
  "new_dest_id": 10,
  "comment": "Direct to boss level",
  "enabled": true
}
```

### 5. Convertir en Portal

**But:** Transformer une porte en portal

```json
{
  "name": "Convert to Portal",
  "offset": "0x100040",
  "new_type": 0,
  "new_key_id": 0,
  "new_dest_id": 1,
  "comment": "Portal to 1st Floor",
  "enabled": true
}
```

---

## 🎮 Presets Disponibles

### unlock_all_doors.json

**Description:** Débloque toutes les portes trouvées

**Effet:** Type = 0 (UNLOCKED), Key = 0

**Usage:**
```bash
copy door_presets\unlock_all_doors.json door_modifications.json
py -3 patch_doors.py
```

### remove_key_requirements.json

**Description:** Enlève toutes les clés mais garde les types

**Effet:** Key = 0, Types inchangés

**Usage:**
```bash
copy door_presets\remove_key_requirements.json door_modifications.json
py -3 patch_doors.py
```

---

## 🔍 Trouver les Offsets

### Méthode 1: Depuis door_analysis.json

```json
{
  "door_structures": [
    {
      "offset": "0x100000",
      "position": {"x": 768, "y": 384, "z": 1536},
      "type": 1,
      "type_description": "Key Locked",
      "key_id": 12,
      "destination_id": 5
    }
  ]
}
```

**Copier l'offset** → Utiliser dans configuration

### Méthode 2: Depuis door_positions.csv

```csv
offset,x,y,z,type,type_desc,key_id,dest_id,flags
0x100000,768,384,1536,1,Key Locked,12,5,0x0001
```

**Première colonne** = Offset à utiliser

### Méthode 3: Depuis Unity

1. Visualiser dans Unity
2. Sélectionner une porte
3. Noter sa position (x, y, z)
4. Chercher dans door_positions.csv
5. Récupérer l'offset

---

## 🛠️ Workflow Complet

### 1. Identifier les Portes

**Méthode A: Unity**
```
1. Visualiser avec CompleteVisualization.cs
2. Repérer les portes à modifier
3. Noter positions ou noms
```

**Méthode B: JSON**
```
1. Ouvrir door_analysis.json
2. Chercher par type ou position
3. Noter offsets
```

### 2. Créer Configuration

**Option A: Preset**
```bash
py -3 patch_doors.py  # Génère presets
copy door_presets\unlock_all_doors.json door_modifications.json
```

**Option B: Manuel**
```bash
py -3 patch_doors.py  # Génère template
# Éditer door_modifications.json
```

### 3. Appliquer Modifications

```bash
py -3 patch_doors.py
```

**Vérifier output:**
```
Modifications applied: 5
  - Unlock Castle Entrance
  - Remove Key from Magic Door
  - ...
```

### 4. Réinjecter dans BIN

```bash
cd ..
py -3 patch_blaze_all.py
```

### 5. Tester

```
1. Lancer émulateur PS1
2. Charger "Blaze & Blade - Patched.bin"
3. Aller aux portes modifiées
4. Vérifier changements
```

---

## ⚠️ Précautions

### Backup Automatique

Le script crée automatiquement:
```
work/BLAZE.ALL.backup
```

**Restaurer si problème:**
```bash
cd work
copy BLAZE.ALL.backup BLAZE.ALL
```

### Tester Progressivement

**Ne pas tout débloquer d'un coup!**

1. Commencer par 1-2 portes
2. Tester in-game
3. Si OK, continuer

### Valeurs Sûres

**Types:**
- 0 (UNLOCKED) = Toujours safe
- 1 (KEY_LOCKED) = Safe avec key_id=0

**Key IDs:**
- 0 = Pas de clé (safe)
- 1-20 = IDs probablement valides

**Destinations:**
- 0 = Même niveau
- 1-50 = Probablement valides
- >50 = Risque de crash

### Offsets Suspects

**Ignorer les offsets avec:**
- Position (0, 0, 0)
- Type = 0 et Key = 0 et Dest = 0
- Beaucoup de padding

---

## 🐛 Troubleshooting

### Problème: "Invalid offset"

**Cause:** Offset hors limites

**Solution:**
- Vérifier format: "0x100000" (avec 0x)
- Vérifier que offset < taille fichier
- Utiliser offsets depuis door_analysis.json

### Problème: Porte toujours locked in-game

**Causes possibles:**
1. **Type pas changé** → Set new_type = 0
2. **Clé toujours requise** → Set new_key_id = 0
3. **Flags pas modifiés** → (Flags pas supportés actuellement)
4. **Cache pas cleared** → Restart émulateur

**Solutions:**
```json
{
  "new_type": 0,
  "new_key_id": 0,
  "new_dest_id": null
}
```

### Problème: Crash au passage

**Cause:** Destination invalide

**Solution:**
- Retirer new_dest_id (laisser null)
- Ou utiliser dest_id connu valide (1-10)

### Problème: Modifications pas appliquées

**Cause:** enabled = false

**Solution:**
```json
{
  "enabled": true  // Vérifier!
}
```

---

## 📊 Exemples Avancés

### Débloquer Tout un Niveau

```json
{
  "modifications": [
    {"name": "Door 1", "offset": "0x100000", "new_type": 0, "enabled": true},
    {"name": "Door 2", "offset": "0x100010", "new_type": 0, "enabled": true},
    {"name": "Door 3", "offset": "0x100020", "new_type": 0, "enabled": true},
    {"name": "Door 4", "offset": "0x100030", "new_type": 0, "enabled": true}
  ]
}
```

### Créer des Shortcuts

```json
{
  "modifications": [
    {
      "name": "Shortcut to Boss",
      "offset": "0x100000",
      "new_type": 0,
      "new_key_id": 0,
      "new_dest_id": 10,
      "comment": "From entrance to boss",
      "enabled": true
    },
    {
      "name": "Quick Return",
      "offset": "0x100010",
      "new_type": 0,
      "new_key_id": 0,
      "new_dest_id": 1,
      "comment": "From boss to entrance",
      "enabled": true
    }
  ]
}
```

### Mode "Easy Access"

**Débloquer + Enlever clés:**
```json
{
  "modifications": [
    {
      "name": "Easy Mode - Door 1",
      "offset": "0x100000",
      "new_type": 0,
      "new_key_id": 0,
      "new_dest_id": null,
      "enabled": true
    }
  ]
}
```

---

## 🎯 Use Cases

### 1. Speedrun Setup

**But:** Accès direct aux boss

```
Débloquer toutes portes
+ Shortcuts vers boss rooms
+ Portals de retour rapide
```

### 2. Exploration Mode

**But:** Visiter tous les niveaux librement

```
Type = UNLOCKED partout
Pas de clés requises
```

### 3. Challenge Mode

**But:** Changer ordre de progression

```
Bloquer portes faciles
Débloquer portes difficiles
Rediriger pour nouveau chemin
```

### 4. Debug Mode

**But:** Tester rapidement

```
Toutes portes unlocked
Destinations vers zones test
```

---

## ✅ Checklist

### Avant Modification
- [ ] Backup exists (auto-créé par script)
- [ ] door_analysis.json disponible
- [ ] Offsets identifiés
- [ ] Configuration créée

### Application
- [ ] py -3 patch_doors.py exécuté
- [ ] Modifications logged (voir console)
- [ ] Aucune erreur

### Réinjection
- [ ] py -3 patch_blaze_all.py exécuté
- [ ] BIN patché créé
- [ ] Taille fichier OK

### Test In-Game
- [ ] Émulateur lancé
- [ ] BIN patché chargé
- [ ] Portes modifiées testées
- [ ] Pas de crash

---

## 📋 Templates

### Template Vide

```json
{
  "modifications": [
    {
      "name": "",
      "offset": "0x",
      "new_type": null,
      "new_key_id": null,
      "new_dest_id": null,
      "comment": "",
      "enabled": false
    }
  ]
}
```

### Template Quick Unlock

```json
{
  "modifications": [
    {
      "name": "Quick Unlock",
      "offset": "0x",
      "new_type": 0,
      "new_key_id": 0,
      "enabled": true
    }
  ]
}
```

---

**Prêt à modifier les portes! 🚪✨**

**Commencer:** `py -3 patch_doors.py`
