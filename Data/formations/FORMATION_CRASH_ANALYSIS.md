# Formation Crash Analysis

## Problem

Changing formation **sizes** (redistributing slots between formations) causes invisible monsters.
Changing formation **composition** (which monster in each slot) while keeping original sizes works.

## Root cause: CONFIRMED

### Offset table in script area

The script area (between 96-byte monster entries and formation templates) starts with a **uint32 LE
offset table**. This table contains offsets from an implied base address to each spawn point group
AND each formation template.

Structure:
```
[entry0, 0, SP_offset_0, SP_offset_1, ..., FM_offset_0, FM_offset_1, ..., FM_offset_N, 0, 0]
```

When formation sizes change, the patcher rewrites the formation templates correctly, but the offset
table still points to the OLD formation positions. The engine reads the stale offset, jumps to the
wrong byte position, and reads garbled data -> invisible monsters.

**Confirmed on 33/41 areas (80%).** The 8 unmatched areas either have no offset table (4) or only
1 formation (4, where diffs can't be verified but no update is needed).

### Verification: Cavern of Death Floor 1 Area 1

```
Script area:  0xF7AA9C - 0xF7AFFC (1376 bytes)
Offset table: [60, 0, 80, 244, 408, 508, 608, 676, 808, 940, 1040, 1172, 0]
                        ^--SP--^  ^---------8 FM entries-----------------^
Implied base: 0xF7AE64

Entry  Value  Abs address  Target
[2]    80     0xF7AEB4     = spawn_points_area_start  (EXACT)
[4]    408    0xF7AFFC     = formation_area_start     (EXACT)
[5]    508    0xF7B060     = F01 start                (EXACT)
[6]    608    0xF7B0C4     = F02 start                (EXACT)
...
[11]   1172   0xF7B2F8     = F07 start                (EXACT)

FM diffs:              100, 100, 68, 132, 132, 100, 132
Formation byte sizes:  100, 100, 68, 132, 132, 100, 132, 132  <- PERFECT MATCH
(byte size = num_slots * 32 + 4)
```

### Fix implemented

`patch_formations.py` now calls `update_offset_table()` BEFORE writing new formation data.
It parses original formation sizes from the binary, locates the FM entries in the offset table
by matching consecutive diffs, then recalculates and writes new offset values.

## Ruled-out hypotheses

### H3: Suffix bytes encode formation size or behavior (RULED OUT)

Analysis of all 159 formations across 41 areas confirmed:
- Suffix = `slot_types[last_slot]` in **100% of cases** (verified against binary)
- **No correlation** with formation size: same suffix value appears with sizes 1 through 8
- The patcher already recalculates suffixes correctly when composition changes
- Only 6 unique suffix values exist across the entire game:
  `00000000`, `00000100`, `00000a00`, `00000b00`, `02000000`, `03000000`

### Padding content (RULED OUT)

Null-byte or 0xFF padding between formations was tested. Did not fix the issue. The engine doesn't
parse padding - it jumps directly to offsets from the table.

### Formation size limits (RULED OUT)

Zone spawns have groups of 10-15 monsters. The engine handles large groups fine.

### Offset table = direct formation index (RULED OUT)

The offset table has MORE entries than formations in every area. It indexes both spawn point groups
AND formation templates, not just formations. The table structure is:
`[header, 0, SP_offsets..., FM_offsets..., 0, 0]`

### Formation count stored in 96-byte monster entries (NOT INVESTIGATED)

No evidence found. The offset table approach works without this.

### Formation count in SLES executable (NOT INVESTIGATED)

No evidence found. The offset table approach works without this.

## Formation count decrease — WORKING

Reducing the number of formations (e.g. 8 -> 4) is now supported via **duplicate offsets + filler barriers**:

1. User formations are written first, followed by filler formations (1-record each with FFFFFFFF markers)
2. The offset table keeps the original entry count — unused entries duplicate user formation offsets (round-robin)
3. The engine picks from all 8 table entries but always lands on one of the 4 real formations
4. Filler binary data acts as termination barriers (FFFFFFFF prevents reads from bleeding into garbage)
5. Non-monotonic offsets are accepted by the engine (e.g. `[408, 572, 800, 1028, 408, 572, 800, 1028]`)

**What does NOT work:**
- 0-record empty formations → GREEN SCREEN CRASH (engine can't handle them)
- 1-record filler formations without duplicate offsets → spawn in-game as 1-monster encounters
- Duplicate offsets without filler barriers (zero padding only) → CRASH at spawn
- Formation count **increase** is not supported (would need more table entries)

**Max user slots** when decreasing count: `num_user_formations + original_total_slots - original_count`

## Remaining limitations

- **Formation count increase** (e.g. 3 -> 5) not supported — would need more offset table entries.
- **4 areas with no offset table** (Cavern F5 A1, Fire Mountain A1, Hall of Demons A7/A8): offset
  table update is skipped. Resizing formations in these areas may still cause issues.

## Test Case: Cavern of Death Floor 1 Area 1

### Original formations (clean BLAZE.ALL)

```
F00: 3 slots [3xGoblin]                          suffix=00000000  @0xF7AFFC  byte_size=100
F01: 3 slots [2xGoblin + 1xShaman]               suffix=02000000  @0xF7B060  byte_size=100
F02: 2 slots [2xShaman]                           suffix=02000000  @0xF7B0C4  byte_size=68
F03: 4 slots [4xBat]                              suffix=00000a00  @0xF7B108  byte_size=132
F04: 4 slots [2xGoblin + 2xBat]                   suffix=00000a00  @0xF7B18C  byte_size=132
F05: 3 slots [3xShaman]                           suffix=02000000  @0xF7B210  byte_size=100
F06: 4 slots [2xGoblin + 2xShaman]               suffix=02000000  @0xF7B274  byte_size=132
F07: 4 slots [2xGoblin + 1xShaman + 1xBat]       suffix=00000a00  @0xF7B2F8  byte_size=132
```

- 8 formations, 27 total slots, 896 bytes
- Budget: 27 * 32 + 8 * 4 = 896 (exact fill)
