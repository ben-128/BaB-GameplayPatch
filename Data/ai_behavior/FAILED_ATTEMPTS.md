# Monster Spell Bitfield Assignment - Failed Attempts Log

## Objectif

Modifier quels sorts offensifs (list 0) les monstres peuvent utiliser en patchant le bitfield entity+0x160 qui contrôle la disponibilité des sorts.

## Contexte technique

- **entity+0x160** = 64-bit bitfield, chaque bit = un sort de la liste offensive
- **Bit 0** = FireBullet, **Bit 8** = MagicMissile, etc.
- **Valeur vanilla** : `0x00000001` (seul FireBullet activé au spawn)
- **Level-up simulation** : EXE dispatch loop (0x800244F4) ajoute plus de bits via OR
- **Overlay init** : Devrait écrire la valeur initiale avant le dispatch

## Recherche des offsets overlay

### Phase 1: Mapping RAM → BLAZE (2026-02-10)

**Méthode** : Analyse de savestate Cavern F1 + comparaison byte-à-byte
**Résultat** : Delta `BLAZE = RAM - 0x7F739758` vérifié 100% correct (20/20 tests)
**Range overlay Cavern** : BLAZE `0x009268A8`-`0x009668A8` (RAM `0x80060000`-`0x800A0000`)

### Phase 2: Identification des write sites (2026-02-10)

Recherche de tous les stores à entity+0x160 dans EXE et BLAZE.ALL :

| # | BLAZE | RAM | Type | Dans Cavern? |
|---|-------|-----|------|--------------|
| 1 | 0x0098A69C | 0x800C3DF4 | Spawn init (verbose 14-instr) | ❌ NON (au-dessus du range) |
| 2 | 0x0092BF74 | 0x800656CC | Combat init (compact ori+sb) | ✅ OUI (dans le range) |
| 3 | 0x00916C44 | 0x8005039C | Entity init (zeroing 4 bytes) | ❌ NON (en-dessous du range) |
| 4 | — | 0x800244F4 | EXE dispatch OR-loop | N/A (EXE, pas overlay) |

**Site #2 identifié comme candidat principal** : Dans le range Cavern, pattern correct, proximité avec autres inits.

---

## Tentative #1: Table lookup per-monster (v1) - 2026-02-10

**Approche** : Remplacer les 14 instructions d'init par un table lookup basé sur identity byte.

**Offsets patchés** :
- Site 1 (spawn) : BLAZE `0x0098A69C`
- Site 2 (combat) : BLAZE `0x0092BF74`

**Code généré** : 8 instructions + 6 table entries (14 slots total)
```mips
lui   $at, TABLE_HI
lbu   $v1, 0x10($v0)        ; identity byte from entity+0x10
nop
sll   $v1, $v1, 2           ; identity * 4
addu  $at, $at, $v1
lw    $v1, TABLE_LO($at)    ; bitfield = table[identity]
beq   $zero, $zero, +7      ; skip table data
sw    $v1, 0x160($v0)       ; DELAY SLOT: store bitfield
.word table[0]              ; identity 0
.word table[1]              ; identity 1
.word table[2]              ; Goblin (0x03FFFFFF = tier 1-5)
.word table[3]              ; Shaman (0x03FFFFFF)
.word table[4]              ; Bat (0x03FFFFFF)
.word table[5]              ; default (0x03FFFFFF)
```

**Config** : Tous monstres → `0x03FFFFFF` (26 sorts, tier 1-5)

**Test in-game** :
- Cavern F1, combat avec Goblin + Shaman + Bat
- **Résultat** : Comportement vanilla identique
- Shaman lance toujours FireBullet, MagicMissile, EnchantWeapon (sorts vanilla)
- Aucun nouveau sort observé (Explosion, Thunderbolt attendus avec bitfield complet)

**Conclusion** : Patches ignorés, code ne s'exécute pas.

---

## Tentative #2: Table lookup + Sentinel (v2) - 2026-02-10

**Hypothèse** : Le dispatch OR-loop écrase notre bitfield. Utilisons un sentinel pour skip la loop.

**Modification** : Ajout de `entity+0x146 = 9999` (sentinel qui fait exit la dispatch function)

**Code généré** : 8 instructions MIPS + sentinel write + 3 table entries (compact mode)
```mips
lui   $at, TABLE_HI
lbu   $v1, 0x10($v0)        ; identity byte
addiu $v1, $v1, -2          ; compact: index 0-2 for identities 2-4
nop
sll   $v1, $v1, 2
addu  $at, $at, $v1
lw    $v1, TABLE_LO($at)
sw    $v1, 0x160($v0)       ; store bitfield
lhu   $v0, 0x146($v0)       ; sentinel write (9999)
ori   $v0, $v0, 0x270F
sh    $v0, 0x146($v0)
```

**Test in-game** : Même résultat, comportement vanilla identique.

**Analyse post-échec** : Dispatch function analysis révèle :
- Sentinel 9999 cause `j 0x80024F04` (exit function), pas loop skip
- Timer entity+0x158 gate la loop (doit accumuler à ≥9999)
- Sur fresh combat (timer=0), la loop ne run jamais anyway
- **La loop n'était pas le problème** - elle n'écrase rien au premier call

**Conclusion** : Sentinel inutile, code overlay toujours pas exécuté.

---

## Tentative #3: Hardcoded constant (v3) - 2026-02-10

**Hypothèse** : L'identity byte est incorrect ou table lookup fail. Testons avec valeur hardcodée.

**Code** : Le plus simple possible, aucun lookup
```mips
; Spawn init (entity in $v0):
lui  $v1, 0x03FF
ori  $v1, $v1, 0xFFFF      ; $v1 = 0x03FFFFFF
sw   $v1, 0x160($v0)
nop x 11                    ; padding to 14 slots

; Combat init (entity in $s5):
lui  $v0, 0x03FF
ori  $v0, $v0, 0xFFFF
sw   $v0, 0x160($s5)
nop x 10
```

**Validation** :
- Patches vérifiés présents dans output/BLAZE.ALL (27 words diffèrent du clean)
- BIN injection confirmée (patch_blaze_all.py succès)
- Output BIN vérifié : bytes présents aux 2 LBA

**Test in-game** : **TOUJOURS comportement vanilla**.

**Conclusion** : Code à ces offsets n'est **jamais exécuté** pour Cavern F1. DÉFINITIF.

---

## Tentative #4: Freeze test infinite loop (v4) - 2026-02-10

**Hypothèse** : Pour être 100% certain que le code ne run pas, utilisons infinite loop.

**Code** :
```mips
0x0098A69C: beq $zero, $zero, -1    ; infinite loop
0x0092BF74: beq $zero, $zero, -1    ; infinite loop
```

**Test in-game** :
- Cavern F1, spawn + combat
- **Résultat** : **AUCUN FREEZE**, jeu fonctionne normalement

**Conclusion DÉFINITIVE** : Code à `0x0098A69C` et `0x0092BF74` n'est **jamais chargé/exécuté** pour Cavern of Death Floor 1.

---

## Tentative #5: Pattern search refined - 2026-02-11

**Méthode** : Scanner BLAZE.ALL entier pour patterns écriture entity+0x160

**Patterns recherchés** :
- A) Spawn init verbose (ori $v1,$zero,1 + sb $v1,0x160($v0))
- B) Combat init compact (ori + sb avec offset 0x160)
- C) Entity init zeroing (4x sb $zero,0x16X)

**Résultats** :
- Total : 5 patterns trouvés dans BLAZE.ALL
- **Dans range Cavern** (0x80060000-0x800A0000) : **2 candidats**
  - `0x0092BF78` détecté par patterns B (combat_init) ET C (entity_init)
  - Note : Offset légèrement différent de tentative #2 (0x0092BF74 vs 0x0092BF78)

**Analyse** :
```
0092BF74: ori $v0, $zero, 0x0001    ; value = 1
0092BF78: sb $v0, 0x160($s5)        ; entity+0x160 = 1
0092BF7C: sb $zero, 0x161($s5)      ; bytes 1-3 = 0
0092BF80: sb $zero, 0x162($s5)
0092BF84: sb $zero, 0x163($s5)
```
Pattern correct, entity dans `$s5`, RAM `0x800656D0` (dans range Cavern ✓).

---

## Tentative #6: Freeze test v2 - offset exact - 2026-02-11

**Méthode** : Freeze test sur offset exact identifié par pattern search

**Offset** : `0x0092BF74` (instruction `ori $v0,$zero,1` avant le `sb`)

**Code** :
```mips
0x0092BF74: beq $zero, $zero, -1    ; était: ori $v0, $zero, 0x0001
```

**Validation** :
- Script `test_spell_freeze.bat` créé
- Patch appliqué à BLAZE.ALL
- BLAZE injecté dans BIN
- BIN vérifié : bytes présents

**Test in-game** (2026-02-11) :
- Cavern of Death Floor 1
- Trigger combat
- **Résultat** : **AUCUN FREEZE**, jeu fonctionne normalement

**Conclusion DÉFINITIVE #2** : Code à `0x0092BF74` confirmé **dead/unused** pour Cavern F1.

---

## Analyse finale

### Pourquoi tous ces offsets sont dead code?

**Hypothèse 1 : Overlay mapping zone-spécifique**
- Le delta `0x7F739758` n'est valide que pour certaines zones
- Cavern F1 charge peut-être un overlay différent du range `0x0092xxxx`
- Les offsets identifiés appartiennent à un autre donjon (ex: Tower, Castle)

**Hypothèse 2 : Init code dans l'EXE, pas l'overlay**
- entity+0x160 pourrait être initialisé par l'EXE avant le chargement de l'overlay
- Les writes overlay seraient des no-ops ou des refreshes
- Le bitfield serait déjà set par l'EXE lors de l'entity creation

**Hypothèse 3 : Code d'init dynamique/indirect**
- L'init pourrait passer par function pointers (jalr) au lieu de direct calls
- Pattern search manque les indirect calls
- Code réel pourrait être dans une région non-recherchée

### Preuves accumulées

1. ✅ Mapping RAM→BLAZE vérifié 100% correct (20/20 cross-validations)
2. ✅ Site #2 confirmé dans range overlay Cavern (0x80060000-0x800A0000)
3. ✅ Pattern d'init correct (ori + sb + entity+0x160)
4. ✅ Patches présents dans output BLAZE.ALL et BIN
5. ❌ **Freeze tests confirment : code jamais exécuté**
6. ❌ Hardcoded values ignorées (pas d'effet in-game)
7. ❌ Sentinel trick ignoré (dispatch OR-loop pas le problème)

### Unique certitude

**Le bitfield entity+0x160 EST construit par le dispatch OR-loop dans l'EXE** (0x800244F4).
Tous les writes overlay identifiés sont soit :
- Pour d'autres zones (Tower, Castle, etc.)
- Dead code / legacy code
- Refreshes sans effet (écrasés immédiatement)

---

## Options restantes

### Option A : Chercher dans d'autres ranges BLAZE.ALL ⭐

L'overlay Cavern utilise peut-être un range complètement différent.

**Approche** :
1. Dump l'overlay RAM complet (0x80060000-0x800A0000) depuis savestate
2. Search ce dump dans BLAZE.ALL byte-à-byte
3. Trouver le vrai offset BLAZE pour l'overlay actif
4. Re-scanner dans ce nouveau range

**Probabilité** : Moyenne. Le mapping pourrait être zone-spécifique.

### Option B : Patcher l'EXE dispatch loop ⭐⭐⭐

Le seul endroit **confirmé** où entity+0x160 est modifié.

**Approche** :
1. Patcher le tier threshold table (EXE 0x8003C020)
2. OU modifier le OR-loop pour always set full bitfield
3. OU injecter code qui override le bitfield après dispatch

**Avantages** :
- Universel (tous les donjons)
- Code confirmé exécuté
- Pas de recherche overlay nécessaire

**Inconvénients** :
- Moins flexible (zone-wide, pas per-monster sans travail additionnel)
- Modification EXE (plus risqué que BLAZE.ALL)

### Option C : Patcher uniquement les stats de sorts ⭐⭐

Accepter la limitation bitfield, focus sur ce qui marche.

**Déjà fonctionnel** :
- Modification damage, MP cost, element
- scaling_divisor pour contrôle MATK
- 103 sorts modifiables (offensive + support + status + monster abilities)

**Avantages** :
- Fonctionne aujourd'hui (0 recherche nécessaire)
- Impact significatif sur gameplay
- Stable, testé, documenté

**Inconvénients** :
- Pas de contrôle sur QUELS sorts les monstres ont
- Tous les casters gardent leur spell set vanilla

### Option D : Hybrid approach ⭐⭐⭐

Combiner stats de sorts (fonctionnel) + modification des stats de monstres.

**Approche** :
1. Augmenter stat4_magic (MP) des melee monsters → les rendre casters
2. Augmenter MATK pour dégâts décents
3. Modifier stats des sorts pour équilibrer

**Résultat pratique** :
- Gobelins standard pourraient avoir assez de MP pour caster
- Avec MATK augmenté + scaling_divisor baissé = dégâts significatifs
- Pas de contrôle spell set mais monsters "upgradés" en casters

---

## Recommandation

**Priorité 1** : Option B (EXE dispatch loop) ⭐⭐⭐
- Plus haut taux de succès
- Code confirmé exécuté
- Impact universel

**Priorité 2** : Option D (hybrid stats) ⭐⭐⭐
- Fonctionne immédiatement
- Combine deux systèmes working
- Bon résultat pratique

**Priorité 3** : Option A (nouveau range search) ⭐
- Beaucoup de travail
- Taux de succès incertain
- Peut-être impossible si init est dans EXE

---

## Scripts créés (pour historique)

1. `find_cavern_overlay_offsets.py` - Pattern search dans BLAZE.ALL
2. `inspect_offset.py` - Disassembly context viewer
3. `test_freeze_exact_offset.py` - Freeze test standalone (OBSOLETE)
4. `patch_spell_freeze_test.py` - Freeze test pour build pipeline
5. `test_spell_freeze.bat` - Quick test script

## Documentation

1. `SPELL_FREEZE_TEST.md` - Test procedure et résultats
2. `FAILED_ATTEMPTS.md` - Ce document
3. `MONSTER_SPELL_RESEARCH.md` - Recherche exhaustive (40KB)
4. `Data/spells/MONSTER_SPELLS.md` - User documentation (stats de sorts)

## Date des tentatives

- **2026-02-10** : Tentatives #1-4 (v1 table lookup → v4 freeze test)
- **2026-02-11** : Tentative #5-6 (pattern search refined + freeze v2)

## Status final

**BLOQUÉ** - Tous les offsets overlay identifiés sont dead code pour Cavern F1.

**Prochaine étape recommandée** : Patcher l'EXE dispatch loop (Option B).
