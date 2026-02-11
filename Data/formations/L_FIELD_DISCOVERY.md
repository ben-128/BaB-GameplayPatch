# L Field Discovery - Casting Behavior Control (2026-02-11)

## Status: ✅ MAJOR BREAKTHROUGH

**L field controls casting behavior!** After 7 failed spell bitfield attempts, we discovered that L=1 activates spell casting.

## Discovery Process

### Initial Observation
User reported: **Vanilla Shaman casts Sleep** (list 2 = Status), but **patched Shaman casts FireBullet** (list 0 = Offensive).

This suggested we had unknowingly changed which spell list monsters use.

### L Field Swap Tests (2026-02-11)

**Test 1: Goblin ↔ Shaman L swap**
- Goblin (slot 0): L=0 → L=1 (Shaman behavior)
- Shaman (slot 1): L=1 → L=0 (Goblin behavior)
- **Result**: Patch didn't apply (patcher bug)

**Test 2: Goblin with L=3 (Bat behavior)**
- Goblin: L=0 → L=3
- **Result**: Goblins FLY! ✅ Confirmed L controls movement/animation

**Test 3: Goblin with L=1 (Shaman behavior)**
- Goblin: L=0 → L=1
- **Result**: Goblins INVISIBLE and frozen ❌
- **Reason**: L=1 tries to load data not available for Goblin model

**Test 4: Bat with L=1 (Shaman behavior)** ← 🎯 **BREAKTHROUGH**
- Bat: L=3 → L=1
- **Result**: Bat STARTS CASTING A SPELL then CRASHES! 🔥
- **Reason**: Bat has MP=2 (too low), missing cast animations, or spell data issues

## Key Discovery

### L Field Controls Behavior Type

| L Value | Behavior Type | Characteristics |
|---------|---------------|-----------------|
| L=0 | Melee | Walks, physical attacks only (Goblin) |
| L=1 | **Caster** | Walks, **CASTS SPELLS** (Shaman) ✅ |
| L=3 | Flying | Flies, physical attacks (Bat) |

**Confirmed**: L=1 activates spell-casting AI behavior!

### Requirements for Casting

For a monster to successfully cast with L=1:
1. ✅ L=1 (casting behavior enabled)
2. ✅ Cast animations loaded for that model
3. ✅ Sufficient stat4_magic (MP pool)
4. ✅ entity+0x160 bitfield configured (which spells available)
5. ❓ entity+0x2B5 spell_list_index (which LIST to use: 0/1/2)

### What L Does NOT Control

❌ **L does NOT control WHICH spells** (Sleep vs FireBullet)
- Shaman with L=1 casts FireBullet (list 0)
- Vanilla Shaman with L=1 cast Sleep (list 2)
- Same L value, different spell lists!

## The Remaining Mystery: spell_list_index

**entity+0x2B5 = spell_list_index** determines WHICH spell list:
- 0 = Offensive (FireBullet, Blaze, etc.)
- 1 = Support (Heal, Cure, etc.)
- 2 = Status (Sleep, Slow, etc.)

**Problem**: We found 0 writes to entity+0x2B5 in EXE or overlay code!

**Hypothesis**: spell_list_index might be derived from another field?

### Candidates

**Assignment entry structure** (8 bytes):
```
[0] = model_slot
[1] = L (AI behavior) ← Controls casting ON/OFF
[2] = tex_variant
[3] = 0x00
[4] = unique_slot
[5] = R (unknown) ← Could this control spell_list_index?
[6] = 0x00
[7] = 0x40
```

**Current R values in Cavern F1**:
- Goblin (slot 0): R=**2** ← list 2 = Status = Sleep?
- Shaman (slot 1): R=**3**
- Bat (slot 2): R=**4**

## 🧪 Test to Perform

**Hypothesis**: R field controls spell_list_index

**Test**: Change Shaman R from 3 → 2
- If R controls spell_list: Shaman should cast **Sleep** (list 2) instead of FireBullet!
- If R doesn't: Shaman continues casting FireBullet (list 0)

**How to test**:
1. Edit `Data/formations/cavern_of_death/floor_1_area_1.json`
2. Change Shaman (slot 1) R from 3 → 2
3. Run `py -3 Data/formations/patch_assignment_entries.py`
4. Run `py -3 patch_blaze_all.py`
5. Test in-game: Does Shaman cast Sleep now?

## Technical Notes

### Patcher Bug Fixed

The main formation patcher (`patch_formations.py`) does NOT patch assignment_entries!

**Solution**: Created `patch_assignment_entries.py` to patch L/R values.

**Build integration**: Add to step 6 in `build_gameplay_patch.bat`:
```batch
py -3 Data\formations\patch_assignment_entries.py
```

### Search Results

**Searches performed**:
- entity+0x2B5 writes in BLAZE.ALL: 2 matches (data zone, not code)
- entity+0x2B5 writes in overlay code: 0 matches
- entity+0x2B5 writes in EXE: 0 matches

**Conclusion**: spell_list_index is NOT written explicitly. Either:
1. Defaults to 0 (memset/init)
2. Derived from another field (L, R, or other)
3. Copied from a structure/table we haven't found

## Impact on Previous Research

### Spell Bitfield Attempts (v1-v6, A1)

All 7 attempts tried to control entity+0x160 (bitfield = WHICH spells in the list).

**We were patching the WRONG thing!**

The real issue was:
- entity+0x2B5 (spell_list_index) = controls WHICH LIST
- entity+0x160 (bitfield) = controls WHICH SPELLS in that list

### Why Tier Threshold Failed (A1)

Tier threshold table (EXE 0x8003C020) controls how many spells unlock per tier.

But if spell_list_index is wrong (0 instead of 2), you get the wrong spells regardless of tier!

## Next Steps

### Immediate (Priority 1)
1. ✅ Test R field hypothesis (change Shaman R=3 → R=2)
2. If works: Document R field as spell_list_index controller
3. If fails: Search for other mechanisms

### If R Works (Priority 2)
1. Create spell_list assignment config per monster
2. Update formation JSONs with correct R values
3. Integrate into build pipeline
4. Test all caster monsters

### If R Fails (Priority 3)
1. Dump vanilla BLAZE.ALL assignment entries
2. Compare vanilla vs patched R values
3. Search for spell_list tables in BLAZE.ALL data sections
4. Consider runtime debugging (PCSX-Redux)

## Files Created/Modified

**New files**:
- `Data/formations/patch_assignment_entries.py` - Patches L/R values
- `Data/test_spell_list_swap.py` - Analysis tool for spell_list writes
- `Data/formations/L_FIELD_DISCOVERY.md` - This document

**Modified**:
- `Data/formations/cavern_of_death/floor_1_area_1.json` - L/R test values

**To clean up**:
- `Data/test_spell_list_swap.py` - Move to WIP/ (analysis only)
- `Data/character_classes/patch_tier_thresholds.py` - DISABLED (doesn't work for monsters)
- `Data/character_classes/tier_thresholds_config.json` - DISABLED
- `Data/character_classes/TIER_THRESHOLDS.md` - Mark as FAILED for monsters

## History

- **2026-02-10**: Attempts v1-v6 (overlay bitfield) - all failed
- **2026-02-11**: Attempt A1 (tier thresholds) - failed
- **2026-02-11**: User reports vanilla Shaman = Sleep, patched = FireBullet
- **2026-02-11**: L field swap tests → **L=1 activates casting!**
- **2026-02-11**: R field hypothesis proposed → **TEST PENDING**

## See Also

- `Data/ai_behavior/FAILED_ATTEMPTS.md` - Exhaustive 7-attempt log
- `Data/character_classes/TIER_THRESHOLD_FAILURE.md` - A1 failure report
- `Data/spells/MONSTER_SPELLS.md` - Working spell stats system
- `WIP/spells/MONSTER_SPELL_RESEARCH.md` - Full spell system research
