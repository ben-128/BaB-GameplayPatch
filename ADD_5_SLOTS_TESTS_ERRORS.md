# Add 5 Monster Slots - Tests & Errors

## Objectif
Ajouter 2 slots de monstres à Cavern F1 A1 (3 → 5):
- Slot 3: Goblin-Leader (level 63)
- Slot 4: Big-Viper (level 5)

## Structure Requise
Pour 5 slots fonctionnels:
- 5 animation tables
- 5 animation records
- 5 assignments
- 5 stats
- header_count = 5
- middle_count = 5

## Tests Effectués

### Test 1: 5 slots avec animations dupliquées (Goblin/Shaman)
**Script:** `add_5_slots_with_anim_tables.py`

**Configuration:**
- 5 animation tables (slots 3-4 dupliquent 0-1)
- 5 animation records (slots 3-4 dupliquent 0-1)
- 5 assignments
- 5 stats
- header_count = 5
- middle_count = 5
- Total shift: +240 bytes

**Résultat:** ❌ CRASH
```
[   17.9928] E(ReadBlockInstructions): Instruction read failed at PC=0x00000874
[   17.9936] E(CompileOrRevalidateBlock): Failed to read block at 0x00000874
[   18.0096] W(ProcessDataSector): Interrupt not processed in time, missed 1 sectors
```

**Analyse:**
- Crash à PC=0x00000874 (adresse très basse)
- Pointeur corrompu ou saut vers mauvaise adresse
- Se produit ~18 secondes après démarrage (pendant chargement area)

---

### Test 2: 5 slots avec animations extraites de Floor 2
**Script:** `add_5_slots_real_animations.py`

**Configuration:**
- 5 animation tables (slots 3-4 extraites de Floor 2 Area 1)
- Big-Viper table: `28 00 ce 00 00 0a 00 00`
- Goblin-Leader table: `00 00 00 00 00 04 00 00`
- 5 animation records (tous extraits Floor 2)
- 5 assignments
- 5 stats
- header_count = 5
- middle_count = 5

**Résultat:** ❌ CRASH (identique Test 1)
```
[   19.9951] E(ReadBlockInstructions): Instruction read failed at PC=0x00000874
```

**Analyse:**
- Même crash que Test 1
- Problème PAS lié aux données d'animation spécifiques
- Note: Extraction Floor 2 possiblement incorrecte (header montrait "haman" en ASCII)

---

### Test 3: 3 anim tables, 5 stats (header=3, middle=5)
**Script:** `test_3_anims_5_stats.py`

**Configuration:**
- 3 animation tables (vanilla)
- 3 animation records (vanilla)
- 5 assignments (slots 3-4 réutilisent anims 0-1)
- 5 stats
- header_count = 3 (unchanged)
- middle_count = 5
- Total shift: +208 bytes

**Résultat:** ❌ CD SEEK ERROR
```
[   21.4488] E(ExecuteCommand): Invalid/out of range seek to D4:11:50
```

**Analyse:**
- Erreur différente des Tests 1-2
- CD seek invalide → données script/formation corrompues ou offsets incorrects
- Confirme que le problème n'est PAS uniquement header_count=5
- Problème dans la copie/décalage des données

---

## Problèmes Identifiés

### 1. CD Seek Errors
L'erreur `D4:11:50` indique que le jeu essaie de lire des données CD qui n'existent pas ou à une mauvaise position.

**Causes possibles:**
- Formation offsets incorrects
- Script offsets incorrects
- Données copiées incorrectement
- File size pas multiple de 2048 (vérifié OK: 46206976 = 22562 × 2048)

### 2. Crash PC=0x00000874
Adresse très basse → pointeur corrompu.

**Causes possibles:**
- Offset table dans script area pas mise à jour
- Autre référence au nombre de slots qu'on n'a pas trouvée
- Code calcule dynamiquement un offset basé sur header_count
- Animation tables pointent vers données corrompues

### 3. Formation Offset Table
Documentation précédente mentionne une "offset table" dans script area:
```
Script area starts with uint32 LE table:
[entry0, 0, SP_offsets..., FM_offsets..., 0, 0]
```

Cette table contient des offsets relatifs pour chaque formation. Si on ajoute des slots, cette table doit être mise à jour.

**Status:** Pas vérifiée dans nos tests

### 4. Script Offset Calculation
Le jeu calcule possiblement:
```c
script_offset = stats_start + (header_count × 96)
```

- Si header_count=3 mais 5 stats → lit 192 bytes trop tôt (garbage)
- Si header_count=5 avec 5 stats → calcul correct, mais crash ailleurs

---

## Scripts Créés

1. `add_5_slots_complete.py` - Version initiale (header=3, middle=5)
2. `add_5_slots_with_anim_tables.py` - Ajoute 5 anim tables (header=5)
3. `add_5_slots_real_animations.py` - Utilise animations Floor 2
4. `extract_floor2_animations.py` - Extrait animations de Floor 2 Area 1
5. `test_3_anims_5_stats.py` - Test diagnostic
6. `manually_update_offset_table.py` - Debug offset table
7. `test_header5_for_debug.py` - Version debug infinite loading
8. `patch_header5_infinite_loop.py` - Tentative patch boucle
9. `patch_loop_limit.py` - Recherche v1=5 load

---

## Données Extraites

### Floor 2 Area 1 Structure
- Group offset: `0xF819A0`
- Monsters: Goblin-Shaman, Giant-Bat, Big-Viper, Goblin-Leader
- 4 slots avec header_count=4

**Animations extraites (possiblement incorrectes):**
```
Big-Viper (Slot 2):
  Table:  28 00 ce 00 00 0a 00 00
  Record: 00 00 00 00 00 00 00 00

Goblin-Leader (Slot 3):
  Table:  00 00 00 00 00 04 00 00
  Record: 00 00 00 00 00 00 00 00
```

Note: Records tous à zéro suspect. Extraction peut-être au mauvais offset.

---

## Prochaines Étapes

### Option A: Fixer les Offsets
1. Vérifier la formation offset table dans script area
2. S'assurer que TOUS les offsets sont correctement mis à jour
3. Vérifier le calcul du script offset par le jeu

### Option B: Patcher le Code
1. Déboguer avec DuckStation pour trouver où ça crashe exactement
2. Identifier le code qui cause le crash
3. Patcher le code pour accepter 5 slots

### Option C: Approche Alternative
1. Utiliser la formation patcher existante (patch_formations.py)
2. Modifier les formations JSON pour ajouter des slots
3. Laisser le patcher gérer les offsets automatiquement

---

## Conclusion

**L'ajout de 5 monster slots échoue pour des raisons structurelles:**

1. ❌ header_count=5 → Crash PC=0x00000874
2. ❌ header_count=3 + 5 stats → CD seek error D4:11:50
3. ❌ Les deux approches causent des crashs différents

**Le problème n'est PAS:**
- Les données d'animation spécifiques
- La taille du fichier (vérifié OK)

**Le problème EST:**
- Offset table pas mise à jour correctement
- Copie des données script/formation cassée
- Structure interne plus complexe que prévu

**Recommendation:** Utiliser le formation patcher existant qui gère déjà correctement les offsets et la structure, plutôt que d'essayer de manipuler directement les bytes.
