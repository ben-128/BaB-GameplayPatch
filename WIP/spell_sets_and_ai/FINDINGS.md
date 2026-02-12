# Spell Sets & AI System - Current Findings

## Date: 2026-02-12

### Slot Types - What We Know

**Confirmed slot_type values (from 41 areas):**
- `00000000` - Base (Trent/Wisp cast with this - NOT "no spells")
- `02000000` - Shaman vanilla (Sleep / Magic Missile / Stone Bullet)
- `03000000` - Tower variant (Sleep / Magic Missile / Heal)
- `00000a00` - Bat/Flying (FireBullet / Magic Missile / Stone Bullet)
- `00000100` - Rare variant (Arch-Magi, some Bats)

**In-game confirmed:**
- Shaman + 02000000 → Sleep
- Shaman + 03000000 → Heal
- Shaman + 00000a00 → FireBullet

**Occurrences in BLAZE.ALL:**
- 02000000: 29,398 occurrences
- 03000000: 29,962 occurrences
- 00000a00: 4,953 occurrences
- 00000100: 73,877 occurrences

Most occurrences are in formation records themselves (0x200000+ region = overlays/level data).

### Combat Dispatch System (From combat_dispatch_ref.md)

**entity+0x160** = 32-bit bitmask that gates spell availability
- One bitmask per creature_type (stride 8 bytes)
- creature_type at entity+0x2B5 = always 0 for all monsters
- Type 0 = 28 Mage spells (array at BLAZE 0x908E68, RAM 0x800DE714)

**Bitmask initialization:**
- Level-up simulation loop at 0x800244F4
- Iterates from level 0 to entity+0x144 (current level)
- OR-accumulates spell bits into entity+0x160
- Sentinel value 0x270F (9999) at entity+0x146 exits loop

**The Missing Link:**
WHERE are slot_types (byte[0:4] from formation records) used to initialize entity+0x160?

## AI System - What We Know

### L Field (flag 0x00) = AI Behavior Index

From `WIP/level_design/docs/SPAWN_MODDING_RESEARCH.md`:

**Location:** Assignment entries, 8 bytes before 96-byte group
```
[slot, L_val, 00, 00]  <- L entry (flag 0x00)
[slot, R_val, 00, 40]  <- R entry (flag 0x40) - unknown purpose
```

**Cavern F1 A1 example:**
```
Slot 0 (Goblin):  L=0
Slot 1 (Shaman):  L=1
Slot 2 (Bat):     L=3  (NOT self-referencing!)
```

**Confirmed effects:**
- L controls which AI behavior the monster uses
- Changing L changes AI behavior + animation expectations
- L beyond valid range → monster stands still
- L to incompatible AI → visual glitches
  - Example: Goblin with L=1 (Shaman AI) → tries to cast, disappears (no cast animations)

**NOT self-referencing:**
- Giant-Bat at slot 2 has L=3
- Goblin-Leader at slot 3 has L=2
- L is an index into an AI behavior handler table

### R Field (flag 0x40)

**Purpose:** UNKNOWN
- Tested with no visible effect on visuals or AI
- Value pattern: often slot+2 in Cavern (R=2,3,4 for slots 0,1,2)

### The Problem: Making Non-Casters Cast

**Approach A: Change L to caster AI**
- Problem: Animation incompatibility
- Goblin (melee animations) + Shaman AI (expects cast animations) = glitches/disappears

**Approach B: Give melee monsters cast bitmask without changing L**
- Modify entity+0x160 to include spell bits
- Keep L=0 (melee AI)
- Problem: Will melee AI ever decide to cast? Probably not.

**Approach C: Find hybrid AI**
- Some monsters (Trent? Wisp?) do melee + cast with L=?
- If we find their L value, we could apply it to other monsters
- Need: Catalog all L values across all 41 areas

## Next Research Steps

### Priority 1: Find where slot_types initialize entity+0x160

**Method:**
1. Find formation spawn code (probably in overlay at 0x200000+)
2. Search for code that:
   - Reads formation records (byte[0:4])
   - Performs lookup or calculation
   - Writes to entity+0x160

**Tools needed:**
- MIPS disassembler for overlay region
- Pattern search for entity+0x160 write operations (sw $reg, 0x160($base))
- Trace backwards from writes to find source data

**Hypothesis:**
```c
// Pseudo-code of what we're looking for
void spawn_formation_monster(formation_record* rec, entity* e) {
    uint32_t slot_type = rec->prefix;  // byte[0:4]
    uint32_t base_bitmask = slot_type_table[slot_type];  // THE TABLE WE NEED
    e->spell_bitmask = base_bitmask;  // Write to entity+0x160

    // Then level-up sim loop OR-accumulates more bits
    for (int lvl = 0; lvl < e->level; lvl++) {
        e->spell_bitmask |= get_spell_for_level(lvl);
    }
}
```

### Priority 2: Catalog all L values

**Script to create:**
```python
# catalog_L_values.py
# Extract all assignment entries from all 41 areas
# Output: CSV with columns: area, slot, monster_name, L, R
# Identify patterns:
#   - Which L values exist?
#   - Which monsters have which L?
#   - Are there hybrid AI values (melee+cast)?
```

### Priority 3: Test custom slot_types

**Experiment:**
```python
# test_custom_slot_types.py
# Try non-vanilla values: 01000000, 04000000, 05000000, FF000000
# Observe:
#   - Crash?
#   - Different spells?
#   - No effect?
# Goal: Reverse engineer the slot_type → bitmask mapping empirically
```

### Priority 4: Find monsters that naturally melee+cast

**Check:**
- Trent (casts with 00000000 according to notes)
- Wisp (casts with 00000000)
- Wraith, Ghost (flying types that might have hybrid AI)
- Mini-bosses (likely have complex AI)

Extract their L values and test on other monsters.

## Technical Constraints

### Why This Is Hard

1. **Code is in overlays, not EXE**
   - Formation spawn code loads dynamically
   - Not in the 2MB EXE that's always in RAM
   - Must identify which overlay handles formations

2. **No debug symbols**
   - Must reverse engineer assembly
   - Pattern matching and hypothesis testing

3. **Animation coupling**
   - Can't just change AI without animation support
   - Need either:
     - Hybrid AI that works with existing animations
     - OR modify bitmask without changing AI (may not trigger casting)

4. **Entity initialization is complex**
   - Multiple data structures (L/R, 96-byte, script area)
   - Initialization happens across multiple functions
   - Hard to find THE spot where slot_types are read

## Potential Solutions

### Solution 1: Find and modify the slot_type table

If we find the table that maps `slot_type → base_bitmask`, we could:
- Add new slot_types with custom spell combinations
- Modify existing slot_types to change spell sets
- Create a "Goblin caster" slot_type with both melee + cast bits

### Solution 2: Patch entity initialization directly

Find the formation spawn code and patch it to:
- Force specific entity+0x160 values based on slot index
- Bypass the slot_type lookup entirely
- Example: "If slot 0, force bitmask 0x000001FF (all tier 0-1 spells)"

### Solution 3: Use existing hybrid monsters

If we find a monster that already melee+casts:
- Copy its L value to Goblin
- Copy its animations if needed (complex)
- Or just use that monster visually modded

## Files to Monitor

- `combat_dispatch_ref.md` - Combat system reference
- `WIP/level_design/docs/SPAWN_MODDING_RESEARCH.md` - Monster data structures
- `Data/formations/*.json` - Formation data with slot_types
- `memory/MEMORY.md` - General findings

## Questions to Answer

1. Which overlay contains formation spawn code?
2. Where in that overlay is entity+0x160 initialized?
3. Is there a slot_type → bitmask lookup table, or is it calculated?
4. What L values exist across all areas?
5. Which monsters have hybrid melee+cast AI (if any)?
6. Can we modify the level-up sim loop to use custom bitmasks?

## Success Criteria

**Milestone 1:** Find where slot_types are read and used
**Milestone 2:** Find the bitmask initialization code
**Milestone 3:** Create a custom slot_type that gives Goblin cast ability
**Milestone 4:** Test Goblin casting in-game (even if animations glitch)
**Milestone 5:** Find or create hybrid AI that works with melee animations

---

This is a complex reverse engineering task. The slot_type system works (we've proven that in-game), but finding WHERE it's implemented in the binary will require:
- MIPS disassembly
- Pattern matching
- Trial and error with patches
- In-game testing of hypotheses

The good news: We know the system EXISTS and WORKS. We just need to find it.
