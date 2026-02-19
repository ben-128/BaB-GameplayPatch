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

## Files Modified

- `add_elite_slot_cavern_f1a1.py` — Complete rewrite using in-place approach
- `floor_1_area_1.json` — Updated offsets for 4-monster layout
- `output/BLAZE.ALL` — In-place area rewrite + 6 overlay data table patches

## Testing Checklist

1. Build completes without errors
2. Entering Cavern F1 Area 1 loads correctly (no infinite loading)
3. Vanilla formations work (Goblin, Shaman with Sleep, Bat)
4. E-Shaman appears in custom formations using slot 3
5. E-Shaman uses correct model (Shaman) with enhanced stats
6. E-Shaman uses Tower Shaman spell set (slot_type 03000000 = Sleep + Heal)
