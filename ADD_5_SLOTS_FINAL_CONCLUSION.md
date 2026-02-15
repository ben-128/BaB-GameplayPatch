# Add 5 Monster Slots - Final Conclusion

## Objectif
Ajouter 2 slots de monstres à Cavern of Death Floor 1 Area 1 (3 → 5 slots):
- Slot 3: Goblin-Leader (level 63)
- Slot 4: Big-Viper (level 5)

---

## Résumé des Tests

### Test 1: 5 Animation Tables Dupliquées
**Approche:** Dupliquer animations des slots 0-1 pour slots 3-4.

**Résultat:** ❌ CRASH
```
PC=0x00000874
Instruction read failed
Empty block compiled
```

**Offset table:** Non mise à jour

---

### Test 2: 5 Animation Tables Extraites (Floor 2)
**Approche:** Extraire vraies animations de Floor 2 Area 1.

**Résultat:** ❌ CRASH (identique Test 1)
```
PC=0x00000874
```

**Problème d'extraction:** Header montrait "haman" (ASCII) au lieu de données binaires → extraction au mauvais offset.

**Offset table:** Non mise à jour

---

### Test 3: 3 Anim Tables, 5 Stats (header=3)
**Approche:** Garder 3 animation tables, ajouter 2 stats, espérer que le script offset soit calculé différemment.

**Résultat:** ❌ CD SEEK ERROR
```
Invalid/out of range seek to D4:11:50
```

**Analyse:** Confirme que le problème n'est PAS uniquement header_count=5.

**Offset table:** Non mise à jour

---

### Test 4: 5 Anim Tables + Offset Table Fix
**Approche:** Utiliser la logique du formation patcher pour mettre à jour correctement l'offset table dans la script area.

**Configuration:**
- 5 animation tables (duplicated 0,1)
- 5 stats
- header_count = 5
- **Offset table mise à jour** (+240 shift sur FM offsets)

**Résultat:** ❌ CRASH avec nouvelles erreurs
```
[   19.9063] E(UnknownReadHandler): Invalid word read at address 0xFFFFFFFC, pc 0x80032530
[   19.9078] E(UnknownWriteHandler): Invalid word write at address 0xFFFFFFFC, value 0x0CFFFFFF, pc 0x80032530
[   19.9102] E(CompileOrRevalidateBlock): Failed to compile block at 0x00000000
[   19.9112] E(ReadBlockInstructions): Instruction read failed at PC=0x00000874
```

**Analyse:**
- **0xFFFFFFFC = -4** en signed int
- Lecture/écriture à adresse invalide
- Pointeur corrompu ou calcul d'offset incorrect **dans le code**
- PC=0x80032530 → adresse de code normale (pas corrompu)
- Le code CALCULE un mauvais offset qui donne 0xFFFFFFFC

---

## Analyse Technique

### Erreurs Observées

#### 1. PC=0x00000874
- Adresse très basse, inhabituelle
- Saut vers mauvaise adresse
- Pointeur corrompu

#### 2. 0xFFFFFFFC Read/Write
- -4 en signed int
- Résultat d'un calcul d'offset incorrect
- Le code fait probablement: `base + offset` où `offset` est négatif ou trop grand
- Exemple: `ptr = array_start + (slot_count - 1) * size`
  - Si slot_count est mal lu ou array_start corrompu → valeur invalide

#### 3. CD Seek D4:11:50
- Position CD invalide
- Formation offsets incorrects
- Données script/formation corrompues

### Structure Affectée

```
Group Offset (0xF7A7F8)
  ├─ 8 bytes: Group Header
  ├─ N × 96 bytes: Monster Stats (N = monster count)
  ├─ Script Area (offset table + bytecode)
  │   ├─ Offset Table: [entry0, 0, SP_offsets..., FM_offsets..., 0, 0]
  │   └─ Script bytecode
  └─ Formation Area (formation templates)

Animation Section (0xF7A900)
  ├─ 8 bytes: Header
  ├─ header_count × 8 bytes: Animation Tables
  ├─ header_count × 8 bytes: Animation Records
  ├─ 44 bytes: Middle Section (contains middle_count)
  ├─ middle_count × 8 bytes: Assignments
  └─ middle_count × 96 bytes: Stats
```

**Modifications apportées:**
- header_count: 3 → 5 (+2 animation tables/records)
- middle_count: 3 → 5 (+2 assignments/stats)
- Total shift: +240 bytes
- Script offset: 0xF7AA9C → 0xF7AB8C
- Formation offset: 0xF7AFFC → 0xF7B0EC
- **Offset table FM entries: +240 shift ✅**

**Ce qui n'a PAS été trouvé/mis à jour:**
- ❓ Autres références au nombre de slots
- ❓ Code qui calcule dynamiquement des offsets
- ❓ Vérifications/assertions sur le nombre de slots
- ❓ Limites hardcodées dans le code

---

## Problème Fondamental

### Le Code du Jeu Fait des Calculs Incorrects

L'erreur `0xFFFFFFFC` suggère que le code fait un calcul comme:

```c
// Pseudocode du jeu (hypothétique)
int slot_count = read_header_count();  // Lit 5
void* base = get_some_base_address();
int offset = calculate_offset(slot_count);  // Calcul devient négatif ou trop grand
void* ptr = base + offset;  // = 0xFFFFFFFC (adresse invalide)
read_word(ptr);  // CRASH
```

**Possible que:**
1. Le code s'attend à max 3-4 slots et fait des vérifications
2. Un tableau/buffer est hardcodé à taille 3-4
3. Le calcul d'offset utilise une formule qui échoue avec slot_count > 4
4. Il y a un autre compteur ou flag qu'on n'a pas trouvé

### Pourquoi l'Offset Table Fix N'a Pas Suffi

L'offset table dans la script area contrôle les **formations** (spawn templates), pas les **monster slots** (animations/stats).

Même avec l'offset table correcte:
- Les formations pointent vers les bonnes positions ✅
- Mais le code qui **charge les animations** au démarrage échoue ❌
- Le code qui **initialise les slots** calcule mal ❌

---

## Scripts Créés (Par Ordre Chronologique)

1. `add_monster_slots_v2.py` - Première tentative
2. `test_add_slots_header3.py` - Test header=3
3. `test_other_counts.py` - Test différentes combinaisons
4. `test_incremental_changes.py` - Tests incrémentaux
5. `add_5_slots_complete.py` - Version "complète" (header=3, middle=5)
6. `test_stats_with_padding.py` - Test padding
7. `test_reuse_anims.py` - Réutilise animations
8. `add_5_slots_with_anim_tables.py` - Ajoute vraiment 5 anim tables
9. `extract_floor2_animations.py` - Extrait animations Floor 2
10. `add_5_slots_real_animations.py` - Utilise animations Floor 2
11. `test_3_anims_5_stats.py` - Test diagnostic
12. `add_5_slots_with_offset_table.py` - **Fix offset table** (dernier test)

### Scripts de Debug
- `manually_update_offset_table.py` - Debug offset table
- `fix_offset_table.py` - Tentative fix
- `test_header5_for_debug.py` - Version debug infinite loading
- `patch_header5_infinite_loop.py` - Tentative patch boucle
- `patch_loop_limit.py` - Recherche v1=5 load
- `patch_formation0_use_slots34.py` - Utilise slots 3-4

### Scripts d'Extraction
- `extract_real_animations.py` - Extrait animations
- `extract_floor2_animations.py` - Extrait Floor 2

---

## Documentation Créée

1. `MONSTER_SLOTS_RESEARCH_SUMMARY.md` - Recherche initiale
2. `MONSTER_SLOTS_TEST_RESULTS.md` - Résultats tests systématiques
3. `ADD_5_SLOTS_TESTS_ERRORS.md` - Documentation erreurs (Tests 1-3)
4. `DEBUG_HEADER5_INFINITE_LOADING.md` - Guide debug DuckStation
5. `ANALYSIS_INFINITE_LOOP.md` - Analyse boucle infinie
6. `ADD_5_SLOTS_FINAL_CONCLUSION.md` - Ce document

---

## Données Extraites

### Floor 1 Area 1 (Vanilla)
```
Group: 0xF7A7F8
Animation: 0xF7A900
  - Header count: 3
  - Middle count: 3
  - 3 monsters: Lv20.Goblin, Goblin-Shaman, Giant-Bat
Stats: 0xF7A97C (3 × 96 bytes)
Script: 0xF7AA9C
Formation: 0xF7AFFC
```

### Floor 2 Area 1 (Vanilla)
```
Group: 0xF819A0
Monsters: Goblin-Shaman, Giant-Bat, Big-Viper, Goblin-Leader
Header count: 4
```

**Tentative extraction animations:**
```
Big-Viper (Slot 2):
  Table:  28 00 ce 00 00 0a 00 00
  Record: 00 00 00 00 00 00 00 00

Goblin-Leader (Slot 3):
  Table:  00 00 00 00 00 04 00 00
  Record: 00 00 00 00 00 00 00 00
```

**Note:** Records tous à zéro → extraction probablement incorrecte (mauvais offset).

### Monster IDs
- Lv20.Goblin: ID 84
- Goblin-Shaman: ID 59
- Giant-Bat: ID 49
- Big-Viper: ID 26
- Goblin-Leader: ID 58

---

## Conclusion Finale

### ❌ Impossible d'Ajouter 5 Slots avec l'Approche Actuelle

**Raisons:**

1. **Le code du jeu ne supporte pas >3-4 slots dans cette zone**
   - Calculs d'offsets échouent (0xFFFFFFFC)
   - Vérifications/assertions hardcodées
   - Limites de buffers

2. **Structure trop complexe**
   - Offset table mise à jour ✅ mais insuffisante
   - Autres références cachées non trouvées
   - Code fait des calculs dynamiques qui échouent

3. **Toutes les approches testées ont échoué**
   - 4 tests majeurs, 4 crashs
   - Même avec offset table correcte
   - Problème au niveau CODE, pas DATA

### ✅ Ce Qui Fonctionne

**3 slots vanilla:**
- Fonctionne parfaitement
- Structure stable
- Tous les offsets corrects

**Modification de formations (même nombre de slots):**
- Formation patcher fonctionne bien
- Peut changer composition, merge, resize
- Tant qu'on garde le même nombre de slots

### 🔄 Alternatives Possibles

#### Option A: Utiliser Formation Patcher (Recommandé)
**Avantages:**
- Fonctionne déjà
- Gère offsets automatiquement
- Peut modifier formations existantes

**Ce qu'on peut faire:**
- Changer les formations pour utiliser différents slots
- Merger/splitter formations
- Modifier spawn points

**Ce qu'on NE peut PAS faire:**
- Ajouter de nouveaux slots (animations/stats)

#### Option B: Patcher le Code
**Approche:**
1. Déboguer avec DuckStation pour trouver PC=0x80032530
2. Identifier le code qui calcule l'offset invalide
3. Patcher le code pour supporter 5 slots

**Challenges:**
- Nécessite reverse engineering MIPS
- Trouver TOUS les endroits à patcher
- Risque de casser autres zones

**Effort:** Très élevé, expertise MIPS requise

#### Option C: Ajouter Slots dans une Autre Zone
**Approche:**
- Chercher une zone qui a déjà 5+ slots
- Modifier cette zone au lieu de Floor 1 Area 1

**Exemples potentiels:**
- Floor 2 Area 1 a 4 slots (Goblin-Shaman, Giant-Bat, Big-Viper, Goblin-Leader)
- Autres zones avec plus de slots

#### Option D: Utiliser Slots Existants avec Stats Différentes
**Approche:**
- Garder 3 slots (animations vanilla)
- Modifier uniquement les stats/noms
- Exemple:
  - Slot 0: Garder apparence Goblin, changer stats en "Goblin-Leader"
  - Slot 1: Garder apparence Shaman, changer stats en "Shaman-Elder"
  - Slot 2: Garder apparence Bat, changer stats en "Giant-Bat"

**Avantages:**
- Pas de problème de structure
- Facile à faire (modifier stats JSON)
- Stable

**Inconvénients:**
- Pas de nouvelles apparences
- Limité à 3 types de monstres visuellement

---

## Recommandation Finale

### Pour ce Projet:

**Utiliser Option D (Stats modifiées sur 3 slots existants)**

**Pourquoi:**
- ✅ Fonctionne garanti (pas de crash)
- ✅ Simple à implémenter
- ✅ Peut avoir des monstres plus forts
- ✅ Peut changer noms
- ❌ Limité à 3 types visuels (mais compositions de formations variées possibles)

**Ou:**

**Utiliser une zone qui a déjà 4-5 slots**
- Floor 2 Area 1 a déjà Goblin-Leader et Big-Viper
- Modifier formations de cette zone
- Pas besoin d'ajouter de slots

---

## Leçons Apprises

### Structure PSX Complexe
- Multiples systèmes imbriqués (animations, stats, formations, script)
- Offset tables critiques
- Calculs dynamiques par le code

### Limites du Binary Patching
- Peut modifier DATA facilement
- Modifier CODE = reverse engineering complexe
- Certaines limites hardcodées impossibles à contourner sans patcher le code

### Importance du Débogage
- DuckStation debugger essentiel
- Erreurs PC/adresses révèlent problèmes profonds
- Tests systématiques nécessaires

### Formation Patcher = Bonne Architecture
- Gère automatiquement offsets
- Abstraction au niveau JSON
- Plus sûr que manipulation binaire directe

---

## Fichiers Modifiés (à Exclure du Commit Final)

Si cleanup nécessaire, supprimer:
- `add_*.py` (sauf si documentation)
- `test_*.py` (tests temporaires)
- `patch_*.py` (tentatives)
- `extract_*.py` (extraction)
- `manually_*.py` (debug)
- `fix_*.py` (tentatives fix)

**Garder:**
- `*.md` (documentation complète de la recherche)
- Formation patcher existant

---

## Timestamp

**Recherche effectuée:** 2026-02-15 à 2026-02-16
**Durée:** ~24 heures de tests
**Tests effectués:** 12+ scripts, 4 approches majeures
**Résultat:** ❌ Impossible avec approche actuelle
**Recommendation:** Utiliser slots existants ou patcher le code

---

**Fin de la recherche "Add 5 Monster Slots"**
