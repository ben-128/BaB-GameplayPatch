# Trap Damage Research - Notes

## Date: 2026-02-10

### Research Summary

**Objective**: Find and modify trap/environmental damage values in Blaze & Blade.

**Known traps**: Cavern of Death (falling rocks), Tower of Illusion (toxic zones), Castle of Devil (crushing walls).

---

### Phase 1: Deep Entity Region Analysis

**Result**: DEAD END for trap data.

The "deep entity region" (script+0x900 to +0x1DC0) was investigated but:
- Most zones have script areas **under 0x900 bytes** - no deep region exists
- Only 3 zones have [XX FF 00 00] marker records (Cavern F7 A1: 288, Sealed Cave A8: 38, Tower A10: 4)
- These records are **zone spawn monster positions**, NOT trap data
- Cavern F1 Area 1 (where falling rocks are known) has only 1048 bytes of script data

**Files created**:
- `dump_deep_region.py` - Dumps deep entity region for all 70 zones
- `dumps/deep_region_summary.txt` - Summary of records per zone
- `dumps/deep_region_detail.txt` - Full hex dump of all regions

### Phase 2: EXE/Overlay Code Analysis

**Result**: FOUND the stat modifier function and damage callers.

#### Key Discovery: Function 0x8008A3E4

This is a **stat modification function** in overlay code:
```
call: 0x8008A3E4(entity_ptr, delta_a1, delta_a2, delta_a3)
```

- Called **58 times** from overlay code region (BLAZE.ALL 0x0091-0x0096)
- Takes 3 signed int16 arguments ($a1, $a2, $a3) = stat deltas
- **Negative values = damage/debuff**, positive = heal/buff
- After the call, code often reads entity+0x9A and entity+0x5C, subtracts

#### Related Function Family

All near 0x8008A3E4 in RAM:
| Function     | Callers | Notes                      |
|-------------|---------|----------------------------|
| 0x8008A1C4  | 25      | stat mod variant           |
| 0x8008A39C  | 25      | stat mod variant           |
| 0x8008A3BC  | 28      | stat mod variant           |
| 0x8008A3E4  | 58      | main stat modifier         |

#### Damage Values Found (32 callers with negative args)

Unique damage value triplets (a1, a2, a3):
- (-5, -5, -5) x3 - light traps
- (-7, -7, +50) x1 - mixed effect (damage + buff?)
- (-8, -8, -8) x1
- (-8, -8, -6) x1
- (-10, -10, -10) x7 - most common, likely standard trap
- (-10, -10, -3) x1
- (-10, -20, -20) x1
- (-13, -13, -13) x1
- (-15, -15, -15) x2
- (-15, -10, -15) x1
- (-20, -20, -20) x5
- (-25, -25, -25) x1
- (-30, -30, -30) x1
- (-30, -30, +70) x1 - mixed effect
- (-30, -30, +40) x1 - mixed effect
- (-50, -50, -50) x1 - heaviest damage
- Plus callers with only partial negative args

#### Overlay Location Problem

The overlay code (0x0091-0x0096 in BLAZE.ALL) is NOT stored near zone formation data (0xF7+ for Cavern). Cannot map callers to specific dungeon floors by offset proximity. The overlays are loaded dynamically into RAM per dungeon.

**What we know**: All 58 callers are in the same overlay region, which corresponds to Cavern of Death overlays (confirmed by proximity to other known Cavern data structures).

### Phase 3: Test Configuration

#### Test Script

`test_trap_modify.py` supports:
- `--mode nop` - NOP all damage JAL calls (zero damage test)
- `--mode multiply --factor N` - Multiply all damage by N

#### Test Results

**PENDING**: Needs in-game testing to confirm:
1. Do the NOPed calls disable trap damage?
2. Do they also disable monster damage? (If so, the calls are generic combat, not trap-specific)
3. Can we isolate trap-specific callers by testing individual patches?

### Phase 4: Patcher Integration

#### Files Created
- `Data/trap_damage/trap_damage_config.json` - Configuration (mode, multiplier)
- `Data/trap_damage/patch_trap_damage.py` - Dynamic patcher (finds callers automatically)

#### Build Pipeline
- Added as **step 7d** in `build_gameplay_patch.bat` (after AI behavior, before BIN creation)
- Patches `output/BLAZE.ALL` overlay code

#### How the Patcher Works
1. Scans BLAZE.ALL overlay code (0x00900000-0x02D00000) for `jal 0x8008A3E4`
2. For each JAL, extracts the immediate arguments from surrounding instructions
3. Filters for callers with negative $a1/$a2/$a3 values (damage callers)
4. Applies modification based on config:
   - `mode: "multiply"` - multiplies negative values by `damage_multiplier`
   - `mode: "nop"` - replaces JAL with NOP (disables the call entirely)

### Next Steps

1. **In-game test**: Build and test with NOP mode to confirm these are damage calls
2. **Isolate trap callers**: If some callers are monster abilities (not traps), need to identify which are which. Could test by NOPing one at a time.
3. **Three stat interpretation**: The 3 args may be HP/MP/SP damage, or attack/defense/speed modifiers. Need to observe in-game which stats change.
4. **Cross-dungeon expansion**: Currently only found callers in Cavern overlay. Tower/Castle overlays may use different function addresses or the same function loaded at different BLAZE.ALL offsets.

### Architecture Summary

```
Game Flow:
  PSX EXE (SLES_008.45) loads overlay code from BLAZE.ALL into RAM
  Overlay code handles per-dungeon gameplay (monster AI, traps, items)
  Trap collision -> calls 0x8008A3E4(entity, dmg1, dmg2, dmg3)
  Function modifies entity stats (HP, MP, or other stats)

BLAZE.ALL layout:
  0x0091xxxx - 0x0096xxxx : Dungeon overlay code (includes trap logic)
  0x00F7xxxx - 0x00F9xxxx : Cavern of Death zone data (monsters, formations)
  These are separate regions loaded independently by the engine.
```
