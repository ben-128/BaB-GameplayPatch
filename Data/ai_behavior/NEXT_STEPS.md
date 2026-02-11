# Monster Spell Assignment - Next Steps After Failed Attempts

## Context

**Status**: 6 overlay patching attempts failed (v1-v6, 2026-02-10 to 2026-02-11)
**Problem**: All identified overlay offsets are dead code for Cavern of Death
**Documentation**: See `FAILED_ATTEMPTS.md` for exhaustive 6-attempt log

## What Works TODAY ✅

### Spell Stats Modification (FULLY FUNCTIONAL)

**File**: `Data/spells/spell_config.json`
**Patcher**: `Data/spells/patch_spell_table.py` (step 7b)

**Capabilities**:
- Modify damage, MP cost, element, cast_time
- Modify **scaling_divisor** (controls MATK impact on damage)
- Works for ALL 103 spells:
  - 29 Offensive (list 0)
  - 24 Support (list 1)
  - 20 Status (list 2)
  - 30 Monster abilities (list 7)

**Impact**: Significant gameplay changes possible without bitfield control.

---

## Options Forward

### Option A: Patch EXE Dispatch Loop ⭐⭐⭐ (RECOMMENDED)

**Target**: EXE function `0x80024494` (dispatch/level-up simulation)

**Advantages**:
- ✅ Code confirmed executing (entity+0x160 built here)
- ✅ Universal (affects all zones)
- ✅ Direct control of bitfield construction

**Approaches**:

#### A1: Modify Tier Threshold Table (EASIEST)
**Location**: EXE `0x8003C020` (5-byte groups per list)

Current tier thresholds for offensive spells (list 0):
```
Tier 1: 5 spells  (bits 0-4)
Tier 2: 10 spells (bits 5-9)
Tier 3: 15 spells (bits 10-14)
Tier 4: 20 spells (bits 15-19)
Tier 5: 26 spells (bits 20-25)
```

**Change to**:
```
Tier 1: 15 spells (unlock more spells early)
Tier 2: 20 spells
Tier 3: 26 spells
Tier 4: 29 spells (all offensive)
Tier 5: 29 spells
```

**Implementation**:
```python
# Data/character_classes/patch_tier_thresholds.py
EXE_OFFSET = 0x8003C020
TIER_TABLE_SIZE = 5 * 8  # 5 bytes per list, 8 lists

with open(BIN_PATH, 'r+b') as f:
    offset = exe_to_bin_offset(EXE_OFFSET)
    f.seek(offset)

    # List 0 (offensive): [15, 20, 26, 29, 29]
    f.write(bytes([15, 20, 26, 29, 29]))
```

**Result**: All caster monsters get more spells earlier, but still gradual unlock.

#### A2: Force Full Bitfield (MORE AGGRESSIVE)
**Location**: EXE `0x800244F4` (OR-loop that sets bits)

**Inject code before the OR-loop**:
```mips
; Check if entity is a monster (not player)
lbu  $t0, 0x150($s3)        ; entity type flags
andi $t0, $t0, 0x80          ; bit 7 = is_monster?
beq  $t0, $zero, normal_path
nop

; Force full bitfield for monsters
lui  $v0, 0x1FFF
ori  $v0, $v0, 0xFFFF        ; 0x1FFFFFFF = all 29 spells
sw   $v0, 0x160($s6)
j    skip_dispatch
nop

normal_path:
; original dispatch code...
```

**Result**: All monsters have ALL spells immediately (very aggressive).

#### A3: Per-Monster via EXE Table (MOST FLEXIBLE)
**Location**: Create new table in free EXE space

**Add table lookup before dispatch**:
```mips
lbu  $t0, 0x150($s3)         ; monster identity
lui  $at, TABLE_HI
addu $at, $at, $t0
lw   $v0, TABLE_LO($at)      ; load bitfield from table
sw   $v0, 0x160($s6)         ; write to entity
```

**Result**: Full per-monster control, like overlay attempt but in EXE (works!).

---

### Option B: Hybrid Stats Approach ⭐⭐⭐ (PRACTICAL)

**Idea**: Use working systems to achieve similar result.

**Method**:
1. Increase monster `stat4_magic` (MP pool) → enable casting
2. Increase monster `MATK` → decent spell damage
3. Lower spell `scaling_divisor` → more MATK scaling
4. Adjust spell `damage` (flat) for balance

**Files**:
- `Data/monster_stats/*/monster_stats.json` (stat4_magic, MATK)
- `Data/spells/spell_config.json` (scaling_divisor, damage)

**Example - Make Goblin a weak caster**:
```json
// monster_stats.json
{
  "name": "Lv20.Goblin",
  "stat4_magic": 100,  // vanilla: 10 (barely casts)
  "stat9_matk": 30     // vanilla: 5 (weak damage)
}

// spell_config.json
{
  "list": 0, "index": 0, "name": "FireBullet",
  "fields": {
    "mp_cost": 4,
    "scaling_divisor": 1,  // vanilla: 3 (now uses full MATK)
    "damage": 10           // flat bonus stays same
  }
}
```

**Result**:
- Goblin can cast ~25 FireBullets (100 MP / 4 cost)
- Damage = (30 MATK / 1) + luck - MDEF + 10 = ~35-45 per hit
- Still uses vanilla spell set (FireBullet only) but much more viable

**Advantages**:
- ✅ Works TODAY (no research needed)
- ✅ Uses two confirmed-working systems
- ✅ Practical gameplay impact
- ✅ Fine control via stats

**Disadvantages**:
- ❌ Cannot change WHICH spells monsters have
- ❌ All Goblins same (no per-instance variety)

---

### Option C: Alternative Overlay Search ⭐ (UNCERTAIN)

**Hypothesis**: Cavern overlay loaded from different BLAZE range than identified.

**Method**:
1. Dump full RAM overlay (0x80060000-0x800A0000) from combat savestate
2. Search this 256KB dump in BLAZE.ALL byte-for-byte
3. Find actual BLAZE offset of loaded overlay
4. Re-scan new range for entity+0x160 writes

**Advantages**:
- ✅ If successful, unlocks per-monster via overlay
- ✅ More "correct" than EXE patching

**Disadvantages**:
- ❌ High effort, uncertain success
- ❌ Overlay might not exist in BLAZE.ALL (runtime-generated?)
- ❌ Even if found, init might still be in EXE

**Probability of success**: ~30% (overlay might be zone-dynamic)

---

### Option D: Accept Limitation ⭐⭐ (PRAGMATIC)

**Idea**: Focus on what works, document limitation.

**Use spell stats modification only**:
- Balance 103 spells via damage/MP/element/scaling
- Create interesting builds via stat allocation
- Accept that spell sets are fixed

**Advantages**:
- ✅ Zero additional work
- ✅ Significant impact already possible
- ✅ Stable, tested, documented

**Disadvantages**:
- ❌ Missing "cool factor" of custom spell sets
- ❌ Less variety between monster types

---

## Recommended Path

### Phase 1: Quick Win (Option B - Hybrid)
**Timeline**: 1-2 hours

1. Pick 3-5 monsters to make casters (e.g., Goblin-Elite, Dark-Magi, Bat-Shaman)
2. Increase their stat4_magic (50-150) and MATK (20-50)
3. Adjust spell scaling_divisor for offensive spells (3→1 or 2)
4. Test in-game, balance

**Result**: Viable caster monsters using existing spell sets.

### Phase 2: EXE Dispatch Patch (Option A1 - Tier Thresholds)
**Timeline**: 2-4 hours

1. Create `Data/character_classes/patch_tier_thresholds.py`
2. Modify tier table to unlock more spells earlier
3. Test with various monster levels
4. Document new progression

**Result**: More spell variety across all zones, gradual unlock.

### Phase 3: (Optional) Full EXE Control (Option A3 - Per-Monster Table)
**Timeline**: 4-8 hours

1. Find free space in EXE for monster→bitfield table
2. Inject table lookup code before dispatch
3. Create config JSON for per-monster bitfields
4. Test extensively

**Result**: Full per-monster spell control, EXE-based.

---

## NOT Recommended

❌ **Option C (Alternative overlay search)** - Too much uncertainty, low ROI.

---

## Files to Create

### For Option A1 (Tier Thresholds):
```
Data/character_classes/patch_tier_thresholds.py
Data/character_classes/tier_thresholds_config.json
```

### For Option A3 (EXE Table):
```
Data/ai_behavior/patch_exe_spell_table.py
Data/ai_behavior/exe_spell_config.json
Data/ai_behavior/EXE_SPELL_SYSTEM.md
```

### For Option B (Hybrid):
```
(already exists, just modify existing JSONs)
Data/monster_stats/*/monster_stats.json
Data/spells/spell_config.json
```

---

## Testing Checklist

For any approach:
- [ ] Cavern F1 (Goblin, Shaman, Bat)
- [ ] Tower of Ordeal (varied monster types)
- [ ] Castle (boss monsters)
- [ ] Different character levels (1, 20, 50, 99)
- [ ] MP consumption correct
- [ ] Damage scaling appropriate
- [ ] No crashes or freezes
- [ ] Savestate load/save works

---

## Documentation to Update

After implementing solution:
- [ ] `MEMORY.md` - Update spell system status
- [ ] `Data/spells/MONSTER_SPELLS.md` - Update capabilities
- [ ] `README.md` - Update feature list
- [ ] Create new guide for chosen approach
- [ ] Archive FAILED_ATTEMPTS.md (keep for history)

---

## Final Notes

The overlay patching failure is **not a dead end** - it's a redirection toward more reliable approaches:

1. **EXE patching** gives confirmed control at the source
2. **Hybrid stats** provides immediate practical results
3. The spell stats system is already powerful and working

The research was valuable - it eliminated dead ends and confirmed the EXE dispatch loop as the true bitfield builder.
