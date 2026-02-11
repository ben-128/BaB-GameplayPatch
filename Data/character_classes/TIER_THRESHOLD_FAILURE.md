# Tier Threshold Patching - FAILURE REPORT

## Status: ❌ FAILED (2026-02-11)

**Approach A1 (tier threshold table patching) does NOT work for monsters.**

## What Was Attempted

### Theory
The EXE dispatch loop (0x80024494) reads tier thresholds from table at 0x8003C020 to build entity+0x160 spell bitfield. By modifying this table, we should give monsters access to more spells.

### Implementation
- **Patcher**: `Data/character_classes/patch_tier_thresholds.py`
- **Config**: `Data/character_classes/tier_thresholds_config.json`
- **Target**: EXE offset 0x8003C020 (40 bytes, 8 lists × 5 tiers)
- **Modification**: Changed offensive list from [5,10,15,20,26] to [29,29,29,29,29]
- **Sector handling**: Correctly implemented sector-aware BIN patching

### Test Setup (Ultra-Boost)
To make the difference OBVIOUS:
- **Tier thresholds**: ALL 29 spells from tier 1 (vs vanilla 5)
- **Goblin-Shaman MP**: 999 (vs vanilla 70)
- **Goblin-Shaman MATK**: 300 (vs vanilla 10)
- **Expected**: Shaman uses 29 varied spells with massive damage

### Test Procedure
1. Built patched BIN with all modifications
2. Verified patches applied:
   - Tier thresholds: ✅ Patched (Tier 1: 10→29 spells confirmed)
   - Goblin-Shaman stats: ✅ Patched (7 occurrences)
3. Loaded in emulator
4. Fought Goblin-Shaman in Cavern of Death F1

### Result: ❌ NO EFFECT

**Observation**: Goblin-Shaman still casts the SAME 5 spells as vanilla.

- ❌ No increase in spell variety
- ❌ No access to higher-tier spells
- ✅ Stat changes DID apply (damage/HP different)

**Conclusion**: Tier threshold table is NOT used for monsters, or is overridden by another mechanism.

## Why It Failed

### Hypothesis 1: Overlay Bitfield Override (Most Likely)
The overlay init code writes a **hardcoded bitfield** (0x01 = FireBullet only) that OVERRIDES the tier threshold calculation.

**Evidence**:
- Overlay code at 0x0098A69C writes `li $v0, 0x01` (confirmed in research)
- This happens AFTER dispatch loop runs
- Final bitfield = overlay value, not dispatch result

**Flow**:
```
1. EXE dispatch reads tier table → builds bitfield from thresholds
2. Overlay init runs → writes hardcoded 0x01 (FireBullet only)
3. Monster spawns with bitfield = 0x01 (overlay wins)
```

### Hypothesis 2: Monster vs Player Detection
The dispatch loop may check entity type and use tier table ONLY for players, not monsters.

**Evidence**:
- Tier table is in character class section (player-focused)
- Monsters may use completely different spell unlock system
- No documentation found of tier table affecting monsters

### Hypothesis 3: Level-Based Addition Only
Tier table may control initial unlock, but monsters get **additions** based on level, not full replacement.

**Evidence**:
- Comments in code mention "level-up simulation ADDS more bits"
- Base bitfield = 0x01 (overlay), then level adds more
- Tier table may only affect which bits get ADDED, not the base

## Technical Verification

### Patcher Confirmed Working
```
[OK] Read 40 bytes
  Current:  [10, 15, 20, 26, 29]
  Modified: [29, 29, 29, 29, 29]
    Tier 1: 10 → 29 spells
[OK] Tier thresholds patched successfully
```

### Stats Patcher Confirmed Working
```
Goblin-Shaman: patched 7 occurrences
```

### BIN File Modified
- File: `output/Blaze & Blade - Patched.bin`
- Size: 703MB
- Timestamp: 2026-02-11 13:19
- EXE offset 0x8003C020: Verified contains [29,29,29,29,29]

### In-Game Behavior
- Shaman stats: CHANGED (HP/damage different)
- Shaman spells: UNCHANGED (same 5 spells as vanilla)
- Shaman MP: CHANGED (casts more frequently, doesn't run out)
- Shaman damage: CHANGED (higher spell damage)

**Conclusion**: Stats patches work, tier threshold patch does not affect monster spells.

## Attempts Summary

This is the **7th failed attempt** to modify monster spell sets:

| # | Method | Target | Result |
|---|--------|--------|--------|
| v1 | Table lookup | Overlay 0x0098A69C | ❌ No effect |
| v2 | Sentinel trick | Overlay 0x0098A69C | ❌ No effect |
| v3 | Hardcoded 0x03FFFFFF | Overlay 0x0098A69C | ❌ No effect |
| v4 | Freeze test | Overlay 0x0098A69C | ❌ No crash (dead code) |
| v5 | Pattern refinement | Multiple overlays | ❌ No effect |
| v6 | Freeze test v2 | Overlay 0x0092BF74 | ❌ No crash (dead code) |
| **A1** | **Tier threshold table** | **EXE 0x8003C020** | **❌ No effect on monsters** |

## Why A1 Seemed Promising

- ✅ Code confirmed executing (dispatch loop runs)
- ✅ Data modification only (no code injection)
- ✅ Table confirmed being read by EXE
- ✅ Universal approach (affects all entities)
- ❌ BUT: Doesn't actually control monster spells

**Predicted success**: 95%
**Actual success**: 0%

The tier table IS used by the game, but NOT for controlling monster spell sets. It may only affect player spell unlocks, or be overridden by overlay code for monsters.

## Next Steps

### Remaining Options

#### Option A2: Force Full Bitfield in Dispatch Loop ⭐⭐
Inject code at 0x800244F4 (before OR-loop) to force bitfield = 0x1FFFFFFF for monsters.

**Advantages**:
- Code confirmed executing
- Would run BEFORE overlay init
- Could check entity type (monster vs player)

**Disadvantages**:
- Requires code injection (not just data)
- Need to find free space in EXE
- More complex than A1

**Effort**: 4-8 hours
**Success chance**: 70% (depends on overlay override timing)

#### Option A3: Per-Monster Table in EXE ⭐
Create monster→bitfield table in EXE, look up before dispatch.

**Advantages**:
- Full per-monster control
- Runs in EXE (confirmed execution)

**Disadvantages**:
- Requires code injection + table
- Complex implementation
- Still may be overridden by overlay

**Effort**: 8-16 hours
**Success chance**: 50% (overlay may still override)

#### Option B: Hybrid Stats Only ⭐⭐⭐ (WORKING TODAY)
Accept that spell SETS cannot be changed, focus on making existing spells better.

**Method**:
1. ✅ Increase monster MP (stat4_magic) - WORKING
2. ✅ Increase monster MATK (stat22_magic_atk) - WORKING
3. ✅ Adjust spell damage/cost (spell_config.json) - WORKING

**Advantages**:
- Already proven working (stats DO apply)
- No research needed
- Immediate results

**Disadvantages**:
- Cannot change WHICH spells monsters have
- Limited to 5-spell variety per monster type

**Effort**: 0 hours (already implemented)
**Success chance**: 100% (confirmed working)

#### Option C: Accept Limitation ⭐⭐
Focus on spell stats modification only, document limitation.

**Advantages**:
- Spell stats system fully working
- Significant gameplay impact possible
- Stable and tested

**Disadvantages**:
- No spell variety for monsters
- Original goal not achieved

**Effort**: 0 hours
**Success chance**: N/A (not trying to change spells)

## Recommendation

### SHORT TERM: Option B (Hybrid Stats)
The stat changes ARE working (confirmed in-game). Continue with:
- Boosted MP for caster monsters
- Boosted MATK for damage
- Spell stats tuning

This gives practical results TODAY.

### LONG TERM: Consider A2/A3 or Accept Limitation
- A2 (force bitfield) requires code injection but may work
- A3 (per-monster table) is complex but flexible
- OR accept that monster spell sets are fixed

**Realistically**: After 7 failed attempts, the overlay bitfield system may be fundamentally un-patchable without reverse-engineering the full overlay loading system.

## Files to Update

- ❌ `Data/character_classes/TIER_THRESHOLDS.md` - Mark as FAILED for monsters
- ❌ `Data/character_classes/patch_tier_thresholds.py` - Add warning
- ❌ `Data/character_classes/tier_thresholds_config.json` - Disable or remove
- 📝 `Data/ai_behavior/FAILED_ATTEMPTS.md` - Add A1 attempt
- 📝 `Data/ai_behavior/NEXT_STEPS.md` - Update with A1 failure
- 📝 `Data/ai_behavior/README.md` - Remove A1 success claim
- 📝 `MEMORY.md` - Document A1 failure

## Lessons Learned

1. **Data modification alone is insufficient** if code overrides it
2. **EXE changes don't guarantee monster behavior** (overlay has priority)
3. **Tier table is player-focused**, not monster-focused
4. **In-game testing is essential** - don't trust theory alone
5. **Stats patches work, spell set patches don't** (different systems)

## History

- **2026-02-10**: v1-v4 overlay attempts failed
- **2026-02-11**: v5-v6 freeze tests confirmed dead code
- **2026-02-11**: A1 implemented, predicted 95% success
- **2026-02-11**: A1 tested in-game, **0% success** - FAILED
- **Status**: 7 attempts, 7 failures. Spell set modification may be impossible.

## See Also

- `Data/ai_behavior/FAILED_ATTEMPTS.md` - Full v1-v6 overlay attempt log
- `Data/ai_behavior/NEXT_STEPS.md` - Alternative approaches
- `Data/spells/MONSTER_SPELLS.md` - Working spell stats system
- `WIP/spells/MONSTER_SPELL_RESEARCH.md` - Full spell system research
