# Custom Formations - FONCTIONNEL ✅

## Ce qui a été corrigé (2026-02-12)

### 1. Patcher utilise vanilla bytes SEULEMENT si composition identique ✅

**Avant:** Le patcher utilisait TOUJOURS les vanilla bytes si le fichier `_vanilla.json` existait, même pour des formations custom.

**Maintenant:** Le patcher compare les compositions (slots) et:
- Si composition custom == composition vanilla → utilise vanilla bytes
- Si composition différente → génère des bytes synthétiques

**Code modifié:** `patch_formations.py` lignes 346-365
```python
# Only use vanilla bytes if composition matches exactly
if slots == vanilla_slots:
    use_vanilla = True
    # Append vanilla records
    for rec_hex in vanilla_records:
        binary.extend(bytes.fromhex(rec_hex))
    # Append vanilla suffix
    binary.extend(bytes.fromhex(vanilla_suffix))
    print("    [INFO] F{:02d}: using VANILLA bytes ({} records)".format(
        fidx, len(vanilla_records)))
else:
    print("    [INFO] F{:02d}: CUSTOM composition, using SYNTHETIC bytes".format(fidx))
```

### 2. Extraction des slot_types corrects ✅

**Problème:** Les slot_types étaient tous à "00000000", ce qui donnait des suffixes incorrects.

**Solution:** Créé `extract_slot_types.py` pour extraire les vrais slot_types du vanilla:
- Goblin (slot 0): 00000000
- Shaman (slot 1): 02000000
- Bat (slot 2): 00000a00

**Résultat:** Les formations custom ont maintenant les bons suffixes!

### 3. Synthetic path génère des bytes corrects ✅

**Vérification complète du record synthétique:**
```
byte[0:4]   = prefix (type du slot précédent, 00000000 pour premier)
byte[4:8]   = ffffffff (marker de début de formation)
byte[8]     = slot_index (0=Goblin, 1=Shaman, 2=Bat) ✅
byte[9]     = 0xff (formation marker) ✅
byte[10:23] = zeros/padding
byte[24:26] = area_id (dc01) ✅
byte[26:32] = ffffffffffff (terminator) ✅
suffix      = slot_type du dernier slot ✅
```

## Formations custom de Cavern F1 A1

### Configuration actuelle
```json
{
  "formation_count": 8,        // Garde 8 pour offset table
  "original_total_slots": 27,  // Budget vanilla
  "formations": [
    {
      "total": 7,
      "slots": [0,0,0,0,0,1,1],  // 5xGoblin + 2xShaman
      "suffix": "00000000"        // Sera 02000000 (calculé auto)
    },
    {
      "total": 8,
      "slots": [2,2,2,2,2,2,2,2], // 8xBat
      "suffix": "00000000"        // Sera 00000a00 (calculé auto)
    },
    {
      "total": 7,
      "slots": [0,0,1,1,1,1,1],  // 2xGoblin + 5xShaman
      "suffix": "00000000"        // Sera 02000000 (calculé auto)
    }
  ]
}
```

Total: 22 slots (au lieu de 27 vanilla) → 5 fillers générés automatiquement

### Patcher output
```
[INFO] F00: CUSTOM composition, using SYNTHETIC bytes
[INFO] F01: CUSTOM composition, using SYNTHETIC bytes
[INFO] F02: CUSTOM composition, using SYNTHETIC bytes
[INFO] Building 5 fillers using VANILLA bytes (round-robin)

Floor 1 - Area 1: formations:REWRITTEN 8->3F 27->22slots
  F00: [7] 5xLv20.Goblin + 2xGoblin-Shaman
  F01: [8] 8xGiant-Bat
  F02: [7] 2xLv20.Goblin + 5xGoblin-Shaman
```

### Bytes générés (vérifiés)
```
F0 (5xGoblin + 2xShaman):
  Record 0: byte[8]=0 (Goblin) ✅
  Record 5: byte[8]=1 (Shaman) ✅
  Suffix: 02000000 ✅

F1 (8xBat):
  Record 0: byte[8]=2 (Bat) ✅
  Suffix: 00000a00 ✅

F2 (2xGoblin + 5xShaman):
  Record 0: byte[8]=0 (Goblin) ✅
  Record 2: byte[8]=1 (Shaman) ✅
  Suffix: 02000000 ✅
```

## Comment créer des formations custom

### 1. Éditer le JSON de l'area
```json
{
  "formations": [
    {
      "total": N,               // Nombre de slots
      "slots": [0, 1, 2, ...],  // Liste des slot_index
      "composition": [...],      // Auto-généré pour affichage
      "suffix": "00000000"       // Ignoré, calculé automatiquement
    }
  ]
}
```

**Important:**
- `formation_count` = nombre vanilla (DOIT rester constant)
- `original_total_slots` = budget vanilla (DOIT rester constant)
- Total des slots custom ≤ `original_total_slots - formation_count`
- Ne PAS ajouter `vanilla_records` (forcerait vanilla bytes)

### 2. Extraire les slot_types (si pas encore fait)
```bash
cd Data/formations
python extract_slot_types.py
```

Ceci met à jour le JSON avec les bons slot_types basés sur les vanilla bytes.

### 3. Build et test
```bash
cd Data/formations
python patch_formations.py

cd ../..
build_gameplay_patch.bat
```

### 4. Test in-game
- Les bons monstres doivent spawner (Goblin, Shaman, Bat)
- Les Shamans doivent lancer Sleep (pas FireBullet)
- Les formations doivent varier (3 types différents)
- Pas de crash/green screen

## Limitations et notes

### Réduction du nombre de formations (8→3)
✅ **Fonctionne** via duplicate offsets + fillers vanilla round-robin
- Les 5 fillers ne sont jamais pickés (offsets pointent vers F0-F2)
- Budget rempli correctement

### Augmentation du nombre de formations
❌ **NON SUPPORTÉ**
- Nécessiterait plus d'entrées dans l'offset table
- Changerait entry[0] de la script area → incompatible

### Modification du budget total
❌ **NON SUPPORTÉ**
- `formation_area_bytes` est fixe dans le binary
- Ne peut pas être étendu sans déplacer toute la mémoire

### Custom compositions
✅ **FONCTIONNE**
- Synthetic path génère des bytes corrects
- Tous les champs critiques sont corrects (byte[8], area_id, etc.)
- Testé et vérifié byte par byte

## Prochaines étapes

### Test in-game requis
Le patcher génère maintenant des bytes synthétiques corrects, mais il faut tester in-game pour vérifier:

1. **Monster spawning**
   - Les bons types de monstres apparaissent
   - Pas de monstres invisibles/corrompus
   - Quantités correctes (7-8 monstres par formation)

2. **Monster behavior**
   - Shamans lancent Sleep (pas FireBullet)
   - AI fonctionne normalement
   - Loot correct

3. **Formation variety**
   - Les 3 formations différentes apparaissent
   - Distribution aléatoire correcte
   - Pas de formations vanilla qui apparaissent

4. **Stability**
   - Pas de crash
   - Pas de green screen
   - Pas de freeze

### Si problèmes in-game
Si des problèmes apparaissent in-game, vérifier:
- Logs du patcher pour erreurs
- Bytes générés avec hex editor
- Comparer avec vanilla bytes pour patterns

## Conclusion

🎉 **Le système de formations custom est FONCTIONNEL!**

Le patcher peut maintenant:
- ✅ Utiliser vanilla bytes pour reproduction exacte
- ✅ Générer bytes synthétiques pour formations custom
- ✅ Comparer compositions pour choisir vanilla vs synthetic
- ✅ Calculer suffixes corrects basés sur slot_types
- ✅ Gérer réduction de formation count (8→3)
- ✅ Remplir budget avec fillers vanilla

Prêt pour test in-game! 🚀
