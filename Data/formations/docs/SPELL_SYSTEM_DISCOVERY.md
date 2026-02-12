# Monster Spell System - Discovery & Patching Guide

## Discovery: slot_types Control Monster Spells

**Date:** 2026-02-12

### Root Cause of FireBullet Bug

The Shaman FireBullet bug was caused by incorrect **byte[0:4] prefix** values in synthetic formation records.

#### The Bug Mechanism

**OLD synthetic generator (commit 8ad1717):**
```python
def build_record(slot_index, is_formation_start, area_id_bytes):
    rec = bytearray(RECORD_SIZE)
    # byte[0:4] = flags (zeros)  <- HARDCODED TO ZEROS!
    # (no rec[0:4] assignment, stays as zeros)
    rec[8] = slot_index  # Correct slot_index
    # ...
```

**Result for Cavern F1 A1 Shamans:**
```
Generated record:
  byte[0:4] = 00000000  <- Goblin prefix (WRONG!)
  byte[8]   = 0x01      <- Shaman slot_index (correct)

Game engine interpretation:
  "This is entity type Shaman (byte[8]=0x01)
   BUT with Goblin spell flags (byte[0:4]=00000000)"

In-game result:
  ✓ Shaman visual (byte[8] controls 3D model)
  ✓ Shaman stats (byte[8] controls combat stats)
  ✓ Shaman AI (byte[8] controls behavior)
  ✗ Modified spell list (byte[0:4] modifies available spells)
     → FireBullet appeared instead of Sleep
```

**Why the confusion:**
- byte[8] controls the **base entity type** (visual, stats, AI)
- byte[0:4] prefix/suffix **modifies** the entity (including spell list)
- This is a two-layer system: entity + modifiers

#### Cavern F1 A1 slot_types

From `floor_1_area_1.json`:
```json
"slot_types": [
  "00000000",  // Slot 0: Lv20.Goblin
  "02000000",  // Slot 1: Goblin-Shaman
  "00000a00"   // Slot 2: Giant-Bat
]
```

**What old patcher did:**
- Set byte[0:4] = `00000000` for ALL records (including Shamans)
- This gave Shamans the "Goblin spell modifier"
- Result: Shaman base entity with Goblin-influenced spell list

**What fixed patcher does:**
- Uses correct slot_types as prefix values
- Shaman gets byte[0:4] = `02000000` (Shaman spell modifier)
- Result: Shaman base entity with correct Shaman spell list

---

## slot_types System Architecture

### Record Format (32 bytes)

```
byte[0:4]   = prefix (slot_types of PREVIOUS monster in formation)
byte[4:8]   = FFFFFFFF marker (formation start) or 00000000 (continuation)
byte[8]     = slot_index (which entity: 0=Goblin, 1=Shaman, 2=Bat)
byte[9]     = 0xFF (formation marker) or 0x0B (direct spawn)
byte[10-23] = ALL ZEROS (no spell/stat data here)
byte[24-25] = area_id (e.g., dc01 for Cavern F1 A1)
byte[26-31] = FFFFFFFFFFFF (terminator)

After formation: 4-byte suffix (slot_types of LAST monster)
```

### Two-Layer Entity System

**Layer 1: Base Entity (byte[8])**
- Determines: 3D model, animations, textures, base stats, AI behavior
- Example: byte[8]=0x01 → Goblin-Shaman entity

**Layer 2: Modifier Flags (byte[0:4] prefix/suffix)**
- Modifies: spell list, possibly other attributes
- Example: byte[0:4]=02000000 → Shaman spell modifier
- Example: byte[0:4]=00000000 → Goblin spell modifier

**Combined:**
```
byte[8]=0x01 + byte[0:4]=02000000 → Full Shaman (Sleep spell)
byte[8]=0x01 + byte[0:4]=00000000 → Shaman with Goblin spell modifier (FireBullet)
byte[8]=0x01 + byte[0:4]=00000a00 → Shaman with Bat spell modifier (unknown spells)
```

---

## How to Patch Monster Spells

### Method 1: Test slot_types Combinations (Recommended)

**Goal:** Map slot_types values to spell lists

**Process:**
1. Use `test_slot_types_spells.py` to experiment with different prefixes
2. Test each combination in-game
3. Document which slot_types unlock which spells
4. Create a spell modifier table

**Example test sequence:**
```bash
# Test 1: Shaman with Goblin prefix
py -3 Data/formations/test_slot_types_spells.py
# Select option 1 (Goblin prefix)
# Build, inject, test in-game → record spell list

# Test 2: Shaman with Bat prefix
py -3 Data/formations/test_slot_types_spells.py
# Select option 2 (Bat prefix)
# Build, inject, test in-game → record spell list

# Test 3: Restore vanilla
py -3 Data/formations/test_slot_types_spells.py
# Select option 3 (Shaman prefix)
# Verify vanilla behavior
```

**Expected findings:**
- Each slot_types value maps to a specific spell modifier
- Different prefixes give access to different spell pools
- Can mix entity types (byte[8]) with spell modifiers (byte[0:4])

### Method 2: Analyze All slot_types (Comprehensive)

**Goal:** Extract all slot_types across all 41 areas to find patterns

**Data sources:**
- `extract_slot_types.py` has already extracted slot_types for all areas
- Check `Data/formations/*/floor_*_area_*.json` for `slot_types` arrays
- Look for rare/unique slot_types values that might unlock special spells

**Analysis:**
```bash
# Find all unique slot_types values
cd Data/formations
grep -r "\"slot_types\":" --include="*.json" | \
  grep -v "_vanilla" | \
  sed 's/.*\[\(.*\)\].*/\1/' | \
  tr ',' '\n' | \
  sort -u
```

**Look for:**
- spell caster monsters (Dark-Magi, Trent, Dark-Angel, etc.)
- boss monsters (might have special slot_types)
- flying monsters (0x0a flag in slot_types)

### Method 3: Direct Formation Editing (Production)

**Goal:** Create custom formations with specific spell modifiers

**Process:**
1. Edit area JSON `formations[N]["slots"]` array
2. **DELETE** `vanilla_records` field (forces synthetic generation)
3. **KEEP** `suffix` field (will be calculated from last slot's slot_types)
4. Run `extract_slot_types.py` to ensure slot_types are correct
5. Build and test

**Example: Give Goblin the Shaman spell list**
```json
{
  "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
  "slot_types": ["00000000", "02000000", "00000a00"],
  "formations": [
    {
      "total": 3,
      "slots": [0, 0, 0],  // 3 Goblins (slot_index = 0)
      "composition": [{"count": 3, "slot": 0, "monster": "Lv20.Goblin"}]
      // NO vanilla_records field (forces synthetic generation)
    }
  ]
}
```

**Then modify patcher to use custom prefix:**
- In `patch_formations.py`, add logic to override prefix values
- Instead of `prefix = slot_types.get(prev_slot, default_type)`
- Use `prefix = custom_spell_modifier_table[desired_spell_set]`

**Warning:** This requires modifying the patcher code.

---

## slot_types Values Catalog

### Known Values (Cavern F1 A1)

| slot_types | Vanilla Monster | Spell Behavior (vanilla)  | **Test Result**                    |
|------------|-----------------|---------------------------|------------------------------------|
| 00000000   | Lv20.Goblin     | Melee-focused, no spells  | -                                  |
| 02000000   | Goblin-Shaman   | Sleep spell               | Sleep ✅ (control)                 |
| 00000a00   | Giant-Bat       | FireBullet spell          | **FireBullet ✅ (on Shaman byte[8]=0x01)** |

### Confirmed Spell Modifiers (2026-02-12)

**When applied to Shaman entity (byte[8]=0x01):**
- `02000000` → Sleep (vanilla Shaman spell)
- `00000a00` → FireBullet (Bat spell transferred to Shaman!)

**Implication:** slot_types prefix can TRANSFER spells between entity types!

### Hypothesis

The slot_types format might be:
```
byte[0] = spell modifier flags (0x00=melee?, 0x02=magic?)
byte[1] = ?
byte[2] = movement flags (0x0a = flying?)
byte[3] = ?
```

**Pattern observed:**
- Goblin (00000000): No spells, melee only
- Shaman (02000000): Magic spell (Sleep)
- Bat (00000a00): Magic spell (FireBullet) + flying

**Next tests needed:**
1. Test 00000000 (Goblin) on Shaman → does it remove spells?
2. Test other spell casters' slot_types on Shaman
3. Map all unique slot_types across 41 areas

---

## IN-GAME TEST RESULTS — CONFIRMED! ✅

### Test 1: Bat Prefix on Shamans (2026-02-12)

**Configuration:**
- Location: Cavern F1 A1, Formation 0
- Modified: Shaman records with byte[0:4] = 00000a00 (Bat prefix)
- Control: Other formations in same area kept vanilla bytes

**Results:**
- ✅ **Formation 0 (patched):** Shamans cast **FireBullet** instead of Sleep
- ✅ **Other formations (vanilla):** Shamans still cast **Sleep**
- ✅ Visual/stats/AI unchanged (Shaman entity preserved)

**CRITICAL DISCOVERY:**
The spell modifier works on a **PER-FORMATION basis**, not globally!
- Same monster type (Shaman) in different formations can have different spells
- The engine reads byte[0:4] from each formation record individually
- This is a per-instance modifier system

**Proof:**
```
Formation 0 (patched):
  byte[0:4] = 00000a00 (Bat modifier)
  byte[8]   = 0x01 (Shaman entity)
  → Result: Shaman with FireBullet

Formation X (vanilla, same area):
  byte[0:4] = 02000000 (Shaman modifier)
  byte[8]   = 0x01 (Shaman entity)
  → Result: Shaman with Sleep
```

**Spell Modifier Mapping (Confirmed):**
| slot_types | Applied to Shaman | Spell Result |
|------------|-------------------|--------------|
| 00000a00   | byte[8]=0x01      | FireBullet   |
| 02000000   | byte[8]=0x01      | Sleep        |

---

## Testing Protocol

### For Each Test:

1. **Backup current BLAZE.ALL:**
   ```bash
   copy output\BLAZE.ALL output\BLAZE.ALL.backup
   ```

2. **Apply test patch:**
   ```bash
   py -3 Data/formations/test_slot_types_spells.py
   ```

3. **Build and inject:**
   ```bash
   build_gameplay_patch.bat
   # (only steps 10-11 needed)
   ```

4. **Test in-game:**
   - Load Cavern of Death, Floor 1, Area 1
   - Trigger formation with Shamans
   - Enter combat
   - Check Shaman's available spells in spell menu
   - Note which spells appear vs. vanilla

5. **Document results:**
   - Record slot_types value tested
   - List all spells available
   - Compare with vanilla spell list
   - Note any visual/AI changes (should be none if byte[8] unchanged)

6. **Restore backup if needed:**
   ```bash
   copy output\BLAZE.ALL.backup output\BLAZE.ALL
   ```

---

## Next Steps

### Immediate (Testing Phase):

1. Run test script with Goblin prefix → document spell list
2. Run test script with Bat prefix → document spell list
3. Run test script with Shaman prefix → verify vanilla behavior
4. Create spell modifier table from results

### Short-term (Mapping Phase):

1. Extract slot_types for all spell-casting monsters across all areas
2. Test rare/unique slot_types values
3. Build comprehensive spell modifier catalog
4. Identify patterns in slot_types format

### Long-term (Production Phase):

1. Design spell modifier system
2. Create custom formation templates with desired spell sets
3. Build spell mod patcher (extension of formation patcher)
4. Document spell modding workflow for users

---

## References

- Formation patcher fix: commit 07c094a (2026-02-12)
- Original buggy patcher: commit 8ad1717
- Test script: `Data/formations/test_slot_types_spells.py`
- Slot types extractor: `Data/formations/Scripts/extract_slot_types.py`
- Memory notes: `memory/MEMORY.md` (Formation Patcher section)
