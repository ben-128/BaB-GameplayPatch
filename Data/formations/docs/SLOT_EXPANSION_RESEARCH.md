# Slot Expansion Research — Cavern F1 Area 1

## Summary

Investigation into why adding a 4th monster slot (E-Shaman) to Cavern F1 Area 1
caused an **infinite loading screen**. Three compounding bugs were found in the
original insertion-based approach. A corrected **in-place rewrite** approach was
designed and implemented.

## Original Approach (BROKEN — caused infinite loading)

The v1 script (`add_elite_slot_cavern_f1a1.py`) used binary **insertion**:
- Inserted +132 bytes into BLAZE.ALL at 0xF7AA9C
- Built a 160-byte middle section (was 124)
- Patched 4 "MIPS ADDIU references" at `0x18920CB, 0x1892133, 0x189234B, 0x18923B3`

### Bug 1: Binary insertion breaks ALL absolute references

Inserting +132 bytes shifts everything after 0xF7AA9C by 132 bytes. This breaks:
- The area TOC entry at `0x160E16F` pointing to MIDDLE_START (0xF7A900)
  → After insertion, this TOC entry no longer points to the correct area base
  → Engine reads garbage instead of area data → **infinite loading**
- Potentially hundreds of other absolute references throughout the binary

**Key finding**: Global search found that the engine navigates **structurally**:
- Only MIDDLE_START has 1 absolute reference (at 0x160E16F)
- Only FORMATION_START has 4 absolute references (in overlay data table)
- SCRIPT_START, SPAWN_POINTS, ZONE_SPAWNS, GROUP_OFFSET have **0 references**
  anywhere in the entire binary — the engine finds them by reading data structures

### Bug 2: False positive "MIPS references" were actually data table entries

The 4 references at `0x18920CB, 0x1892133, 0x189234B, 0x18923B3` were identified
as MIPS ADDIU instructions encoding the lower 16 bits of FORMATION_START. This was
**completely wrong**:

- All 4 are at byte alignment = 3 (offset % 4 = 3)
- MIPS instructions must be 4-byte aligned
- The `[FC, AF]` bytes SPAN TWO INSTRUCTIONS (byte[3] of one, byte[0] of next)
- Decoding at the proper 4-byte boundary gives opcode 0x3F (COP2/SPECIAL2)
- These are **GTE (Geometry Transformation Engine) instructions**
- Patching them corrupted the 3D rendering pipeline

**What they actually are**: Non-aligned uint32 entries in a **data table** within
the Cavern overlay region. Reading 4 bytes starting at each position yields
exactly `0x00F7AFFC` (the vanilla formation_start offset). These DO need patching,
but as uint32 data values, not as instruction immediates.

### Bug 3: Middle section 8 bytes too small

The v1 script built a 160-byte middle section for N=4 monsters. Cross-area
comparison with Area 2 (which naturally has N=4 monsters: Goblin, Shaman, Bat,
Goblin-Leader) revealed the correct size is **168 bytes**.

The difference is in the **data_block** (the section between anim_table and
pointer_table):

| Component      | N=3 (Area 1 vanilla) | N=4 (Area 2 reference) | N=4 (v1 WRONG) |
|---------------|---------------------|----------------------|----------------|
| header        | 12                  | 12                   | 12             |
| anim_table    | 3×8 = 24           | 4×8 = 32            | 4×8 = 32       |
| data_block    | 5×8 = 40           | **8×8 = 64**         | 7×8 = 56       |
| pointer_table | 6×4 = 24           | 7×4 = 28            | 7×4 = 28       |
| assignments   | 3×8 = 24           | 4×8 = 32            | 4×8 = 32       |
| **TOTAL**     | **124**             | **168**              | **160** (WRONG) |

The data_block has `N pointed entries + M unpointed entries`:
- N=3: 3 pointed + 2 unpointed = 5 entries
- N=4: 4 pointed + 4 unpointed = 8 entries

## Corrected Approach — In-place Rewrite

### Strategy

Instead of inserting bytes (which breaks absolute references), rewrite the area
data **in-place** within the fixed boundaries `[0xF7A900, 0xF7CA48)` (8520 bytes).

The space for expansion comes from truncating zone_spawns at the end:
- Zone_spawns: 5416 bytes → 5276 bytes (140 bytes truncated = ~4-5 records, 2.6% loss)
- This removes the last few zone_spawn records from the area
- The truncated records are far-corner bat/goblin spawns — minimal gameplay impact

### New Area Layout

```
Offset     Size    Section               Change from vanilla
─────────  ──────  ────────────────────  ──────────────────
0xF7A900   168     Middle section        +44 bytes (was 124)
0xF7A9A8   384     Stats (4 × 96)       +96 bytes (was 288)
0xF7AB28   varies  Script area           shifted +140, unchanged content
0xF7AF40   328     Spawn points          shifted +140, unchanged content
0xF7B088   896     Formations            shifted +140, unchanged content
0xF7B5AC   5276    Zone spawns           shifted +140, truncated 140 bytes
0xF7CA48   ---     Area end              UNCHANGED (same total size)
```

### 168-byte Middle Section Structure

```
Offset  Size  Section          Contents
──────  ────  ───────────────  ─────────────────────────────────
+0x00   12    Header           Copy vanilla (00000000 04000000 00000000)
+0x0C   32    Anim table       Slots 0,1,2 vanilla + Slot 3 = copy Shaman
+0x2C   64    Data block       4 pointed (3 vanilla + E-Shaman) + 4 unpointed
+0x6C   28    Pointer table    [0, 0, 0x2C, 0x34, 0x3C, 0x44, 0]
+0x88   32    Assignments      Slots 0,1,2 vanilla + Slot 3 E-Shaman
+0xA8   ---   END              = new group_offset
```

### Overlay References to Patch

6 non-aligned uint32 entries in the Cavern overlay data table:

| Offset in BLAZE | Old Value (vanilla) | New Value (expanded) | Type |
|-----------------|--------------------|--------------------|------|
| 0x18920CB       | 0x00F7AFFC         | 0x00F7B088          | formation_start |
| 0x1892133       | 0x00F7AFFC         | 0x00F7B088          | formation_start |
| 0x189234B       | 0x00F7AFFC         | 0x00F7B088          | formation_start |
| 0x18923B3       | 0x00F7AFFC         | 0x00F7B088          | formation_start |
| 0x18920DB       | 0x00F7B8FC         | 0x00F7B988          | zone_spawns ref |
| 0x189235B       | 0x00F7B8FC         | 0x00F7B988          | zone_spawns ref |

These are read/written as uint32 LE at the given (non-aligned) offset.
They are NOT MIPS instructions.

### How Engine Navigates Area Data

The engine uses a **structural navigation** approach:
1. TOC ref at `0x160E16F` → MIDDLE_START (0xF7A900) — **unchanged by in-place rewrite**
2. Middle section's pointer table tells engine how many monsters (N non-zero entries)
3. Assignments at end of middle section → 8 bytes per slot
4. Stats follow immediately after middle section → N × 96 bytes
5. Script area follows stats → `group_offset + N × 96`
6. Offset table in script area gives relative positions of spawn_points, formations
7. Formation_start has 4 absolute refs in overlay data table (must be patched)
8. Zone_spawns has 2 internal absolute refs in overlay data table (must be patched)

Only items 7 and 8 require explicit patching. Everything else adjusts automatically
because the engine reads the structure sequentially.

## Key Constants

```python
# Expansion amounts
MIDDLE_EXPANSION = 44       # 168 - 124
STATS_EXPANSION  = 96       # One new 96-byte stat block
TOTAL_EXPANSION  = 140      # = 0x8C

# New offsets (all = vanilla + appropriate shift)
NEW_GROUP_OFFSET        = 0xF7A9A8  # AREA_START + 168
NEW_STATS_END           = 0xF7AB28  # = new script_start
NEW_FORMATION_START     = 0xF7B088  # vanilla 0xF7AFFC + 140
NEW_SPAWN_POINTS_START  = 0xF7AF40  # vanilla 0xF7AEB4 + 140
NEW_ZONE_SPAWNS_START   = 0xF7B5AC  # vanilla 0xF7B520 + 140
NEW_ZONE_SPAWNS_BYTES   = 5276      # vanilla 5416 - 140
```

## In-Game Test Results (2026-02-19)

**Status: CRASH when entering Cavern F1 Area 1. Other levels work fine.**

| Build variant | Cavern F1 A1 | Other levels |
|---------------|-------------|-------------|
| No expansion (baseline) | OK | OK |
| Expansion, no overlay patches | CRASH | OK |
| Expansion + 6 overlay patches | CRASH | OK |

### Build Pipeline Bugs Found & Fixed

1. **Formation patcher corruption** — The formation patcher (`patch_formations.py`) was
   rewriting formation data even though the expansion script already placed it correctly.
   Fixed by adding `skip_formation_rewrite: true` and `skip_offset_table_update: true`
   flags in `floor_1_area_1.json`.

2. **Spawn groups overwrite** — `patch_spawn_groups.py` writes 96-byte stat blocks
   starting at `group_offset`. The spawn groups JSON still had the vanilla offset
   `0xF7A97C`, which in the expanded layout falls INSIDE the 168-byte middle section.
   This corrupted the pointer table and assignments. Fixed by updating the offset to
   `0xF7A9A8` in `cavern_of_death.json`.

3. **Assignment R values** — JSON had R=0 for vanilla slots, but binary has R=2,3,4.
   Fixed in both JSON and expansion script.

After fixing all pipeline bugs, binary verification shows **0 bytes different** between
expansion output and expected layout. All other areas unaffected.

### Root Cause Analysis — Why the Crash Persists

The crash is NOT caused by:
- ~~Overlay formation refs~~ (patched all 6, crash unchanged)
- ~~Build pipeline bugs~~ (all fixed, binary is structurally correct)
- ~~Other areas affected~~ (only Area 1 crashes)

The crash IS caused by the **middle section structure change** (124→168 bytes).

**Key discovery: Area 2 (natural N=4) has ZERO formation refs in the overlay data table.**
Area 1 (N=3) has 4 formation + 2 zone_spawn refs. This means the engine uses **different
code paths** for Area 1 vs Area 2. The overlay likely has area-specific parsing logic that
expects a fixed N=3 structure for Area 1.

Possible mechanisms:
1. Monster count N=3 hardcoded somewhere in overlay → reads wrong section boundaries
2. Middle section size (124) hardcoded → engine calculates wrong stats/script offset
3. Anim table entry count fixed → pointer table read at wrong offset
4. Per-area configuration in overlay data table encodes N indirectly

## Next Steps — Approaches to Solve the Crash

### Approach A: Find N=3 hardcoding in the Cavern overlay (HIGH EFFORT, HIGH REWARD)

The engine must know how many monster slots each area has. For Area 2 (N=4), it works
natively. For Area 1 (N=3), the number may be:
- Encoded in the overlay data table entries (the 4+2 refs unique to Area 1)
- Hardcoded in overlay MIPS code (e.g., `li $t0, 3` before a loop)
- Derived from other area metadata

**Steps:**
1. Disassemble the Cavern overlay code region (~0x1892000) with a MIPS disassembler
2. Search for instructions loading the value 3 (`addiu $reg, $zero, 3` = `03 00 XX 24`)
   near the 4 formation ref addresses
3. Compare with how Area 2 is handled — if Area 2 has no overlay refs, its N=4 must
   come from the data structures themselves (pointer table non-zero count)
4. If found: patch the N value from 3 to 4

### Approach B: Swap Area 1 and Area 2 data (MEDIUM EFFORT, GUARANTEED)

Since Area 2 already supports N=4 natively and has zero overlay hardcoding:
1. Put our expanded 4-monster data into Area 2's slot (which the engine handles as N=4)
2. Put vanilla Area 2 data into Area 1's slot (or duplicate Area 2's vanilla as Area 1)
3. Swap the overlay refs to match
4. This avoids fighting the N=3 hardcoding entirely

**Risk:** Area 1 and Area 2 have different zone_spawn layouts (spawn positions on the map).
Swapping data might place monsters in wrong positions. Need to verify what zone_spawns
actually encode.

### Approach C: Clone Area 2's binary structure for Area 1 (MEDIUM EFFORT, CLEAN)

Instead of expanding Area 1's middle section from 124→168, clone the EXACT binary
structure of Area 2 (which is naturally N=4) and adapt it for Area 1:
1. Extract Area 2's middle section (168 bytes) as template
2. Replace Area 2's animation/assignment values with Area 1's + the new E-Shaman slot
3. Keep stats, script, formations, zone_spawns from Area 1 (shifted +140)
4. The overlay refs might not need patching if the engine reads N from the data structure

**Why this might work:** If Area 2 has zero overlay refs, its N=4 comes from reading the
pointer table (which has 7 entries: `[0, ptr, ptr, ptr, ptr, ptr, 0]` with 4 non-zero).
The engine might do: "count non-zero entries in pointer table = N". If Area 1's expanded
middle section uses the same pointer table format, the engine would read N=4 from it.

**The crash then is NOT about N being hardcoded, but about the overlay data table refs
pointing to wrong offsets.** But we already patched those... so this may not help.

### Approach D: Use DuckStation debugger to trace the crash (HIGH EFFORT, DEFINITIVE)

Load the patched build in DuckStation with CPU debugger:
1. Set a read breakpoint on the middle section start address (RAM equivalent of 0xF7A900)
2. Enter Cavern F1 Area 1 and observe which instruction causes the crash
3. The crash PC (program counter) will reveal exactly which code path fails
4. Trace backwards to find the assumption being violated

**This is the most reliable approach** but requires familiarity with the DuckStation
debugger and MIPS assembly. See the trap damage research for a successful example of
this workflow.

### Approach E: Minimal expansion — use 3 slots + stat-only change (LOW EFFORT, FALLBACK)

If structural expansion proves too difficult, avoid expanding the middle section entirely:
1. Keep N=3 slots (Goblin, Shaman, Bat) — no middle section change
2. Modify Shaman's stats (96-byte block) to create an "Elite Shaman" variant
3. Use slot_types (suffix) to give it Tower Shaman spells (03000000 = Sleep + Heal)
4. Replace Bat (slot 2) with E-Shaman by copying Shaman's anim data to slot 2

**Limitations:** Only 3 visually distinct monster types per area (same as vanilla).
The E-Shaman would replace the Bat entirely rather than being a 4th type.

### Recommended Priority

1. **Approach D** (debugger trace) — understand exactly what crashes before trying fixes
2. **Approach A** (find N hardcoding) — if debugger reveals an N=3 constant, patch it
3. **Approach C** (clone Area 2 structure) — if the issue is subtler than a simple constant
4. **Approach E** (3-slot fallback) — if structural expansion is truly blocked by engine

## Files

- `Data/formations/Scripts/add_elite_slot_cavern_f1a1.py` — v2 expansion script (in-place + overlay patches)
- `Data/formations/cavern_of_death/floor_1_area_1.json` — 4-monster config with skip flags
- `WIP/level_design/spawns/data/spawn_groups/cavern_of_death.json` — expanded group_offset
- `Data/formations/Scripts/patch_formations.py` — skip_formation_rewrite check

## Testing Checklist

1. Build completes without errors ✅
2. Other levels load correctly ✅
3. Entering Cavern F1 Area 1 loads correctly — **CRASH** ✗
4. Vanilla formations work (Goblin, Shaman with Sleep, Bat) — blocked by #3
5. E-Shaman appears in custom formations using slot 3 — blocked by #3
6. E-Shaman uses correct model (Shaman) with enhanced stats — blocked by #3
7. E-Shaman uses Tower Shaman spell set (slot_type 03000000 = Sleep + Heal) — blocked by #3
