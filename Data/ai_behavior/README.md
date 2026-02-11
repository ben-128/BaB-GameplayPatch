# Monster AI & Spell System

## Current Status (2026-02-11)

### ✅ What Works

**Spell Stats Modification** - `Data/spells/spell_config.json`
- Modify damage, MP cost, element, cast_time, scaling_divisor
- Affects all 103 spells (offensive + support + status + monster abilities)
- Patcher: `Data/spells/patch_spell_table.py` (step 7b)
- **Status**: FULLY FUNCTIONAL ✅

### ❌ What Doesn't Work

**Monster Spell Bitfield Assignment** - `overlay_bitfield_config.json`
- Goal: Change which offensive spells monsters can cast
- Method: Patch entity+0x160 bitfield via overlay init
- **Status**: PERMANENTLY FAILED ❌

**6 patching attempts (v1-v6)** all failed:
- v1: Table lookup per-monster
- v2: Table + sentinel trick
- v3: Hardcoded constants (0x03FFFFFF)
- v4: Freeze test (infinite loop at spawn)
- v5: Pattern search refined
- v6: Freeze test v2 (infinite loop at combat init)

**Freeze test v6 result** (2026-02-11):
- Patched offset `0x0092BF74` with `beq $zero,$zero,-1`
- Loaded in emulator, triggered combat in Cavern F1
- **Result: NO CRASH** → Code never executes
- **Conclusion: DEFINITIVE - All overlay offsets are dead code**

## Why It Failed

The bitfield entity+0x160 is **built by the EXE dispatch loop** (0x800244F4), NOT by overlay init code.

All identified overlay offsets (0x0098A69C, 0x0092BF74, 0x00916C44) are either:
- Dead/legacy code
- For different dungeons (not Cavern)
- Executed before savestate capture
- Simply never reached

## Files in This Directory

### Working Files
- `patch_ai_behavior.py` - General AI behavior patcher (works, unrelated to spells)
- `ai_behavior_config.json` - AI behavior config (works)

### Failed Spell System Files
- ❌ `patch_monster_spells.py` - DISABLED, overlay bitfield patcher (doesn't work)
- ❌ `overlay_bitfield_config.json` - DISABLED, spell assignment config (doesn't work)
- ❌ `patch_spell_freeze_test.py` - Freeze test tool (diagnostic, used for v6)

### Documentation
- 📄 `FAILED_ATTEMPTS.md` - Exhaustive 6-attempt log with technical details
- 📄 `NEXT_STEPS.md` - Alternative solutions & recommended approaches
- 📄 `SPELL_FREEZE_TEST.md` - Freeze test v6 procedure & results
- 📄 `README.md` - This file

## Alternative Solutions

See `NEXT_STEPS.md` for detailed plans. Summary:

### Option A: Patch EXE Dispatch Loop ⭐⭐⭐ (Recommended)
- Modify tier threshold table (EXE 0x8003C020)
- OR inject code before OR-loop (0x800244F4)
- **Advantage**: Code confirmed executing, universal solution
- **Effort**: Medium (2-8 hours)

### Option B: Hybrid Stats Approach ⭐⭐⭐ (Practical)
- Increase monster stat4_magic (MP pool)
- Increase monster MATK (spell damage)
- Lower spell scaling_divisor (more MATK impact)
- **Advantage**: Works today, uses existing systems
- **Effort**: Low (1-2 hours)

### Option C: Accept Limitation ⭐⭐ (Pragmatic)
- Focus on spell stats only (already powerful)
- Document limitation
- Move on to other systems
- **Advantage**: Zero work, stable
- **Effort**: None

## For Developers

If you want to investigate further:

1. **DO NOT** try more overlay offsets - we've confirmed they don't execute
2. **DO** consider EXE dispatch patching (confirmed execution point)
3. **DO** read `FAILED_ATTEMPTS.md` to avoid repeating dead ends
4. **DO** check `NEXT_STEPS.md` for viable approaches

## Build Integration

The spell bitfield patcher is called at step 7e but immediately skips (disabled).

To remove from build:
1. Edit `build_gameplay_patch.bat`
2. Comment out step 7e (lines 267-280)
3. Or leave as-is - it skips gracefully

## Testing

To verify freeze test yourself:
```bash
# Quick test (30 seconds)
test_spell_freeze.bat

# Or via build
# Edit build_gameplay_patch.bat: set TEST_SPELL_FREEZE=1
build_gameplay_patch.bat
```

Then load in emulator, go to Cavern F1, trigger combat.
Expected: No freeze (game runs normally) = code dead.

## History

- **2026-02-10**: Attempts v1-v4, initial freeze tests
- **2026-02-11**: Attempts v5-v6, pattern search + definitive freeze test
- **2026-02-11**: Documentation complete, system marked as failed
- **Status**: Closed, alternative solutions proposed

## See Also

- `Data/spells/MONSTER_SPELLS.md` - Working spell stats system (user guide)
- `WIP/spells/MONSTER_SPELL_RESEARCH.md` - Full 40KB research log
- `MEMORY.md` - Updated with failed attempt notes
