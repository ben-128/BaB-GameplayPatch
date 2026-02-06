# Formation Crash Analysis

## Problem

Changing the number of formations in an area (e.g. from 8 to 3 in Cavern of Death Floor 1 Area 1)
causes the game to crash (screen flickering, broken rendering) when monsters are supposed to spawn.

Changing formation **composition** (which monsters, how many) while keeping the **same number of
formations** works fine.

## Test Case: Cavern of Death Floor 1 Area 1

### Original formations (clean BLAZE.ALL)

```
F00: 3 slots [3xGoblin]                          suffix=00000000  @0xF7AFFC
F01: 3 slots [2xGoblin + 1xShaman]               suffix=02000000  @0xF7B060
F02: 2 slots [2xShaman]                           suffix=02000000  @0xF7B0C4
F03: 4 slots [4xBat]                              suffix=00000a00  @0xF7B108
F04: 4 slots [2xGoblin + 2xBat]                   suffix=00000a00  @0xF7B18C
F05: 3 slots [3xShaman]                           suffix=02000000  @0xF7B210
F06: 4 slots [2xGoblin + 2xShaman]               suffix=02000000  @0xF7B274
F07: 4 slots [2xGoblin + 1xShaman + 1xBat]       suffix=00000a00  @0xF7B2F8
```

- 8 formations, 27 total slots
- Perfectly contiguous: 27 * 32 + 8 * 4 = **896 bytes** (exactly fills the budget)
- No padding in the original

### Modified formations (user edit, causes crash)

```
F00: 9 slots [3xGoblin + 3xShaman + 3xBat]       suffix=02000000
F01: 8 slots [8xBat]                              suffix=00000000
F02: 10 slots [5xGoblin + 5xShaman]               suffix=00000000
```

- 3 formations, 27 total slots
- 27 * 32 + 3 * 4 = 876 bytes, leaving 20 bytes of padding

## What was ruled out

### Padding content
The initial hypothesis was that null-byte padding (20 bytes of `\x00`) was being parsed as
monster records. We changed the padding to `\xFF` bytes and added filler-formation logic for
larger gaps. **This did not fix the crash.**

Since 20 bytes < 32 bytes (record size), the game can't even read a full record from the padding.
The padding content is not the issue.

### Formation size limits
Zone spawns in the same area have groups of 10-15 monsters, so the engine can handle large groups.
The crash is not caused by having too many monsters in a single formation.

### Build pipeline
The `build_gameplay_patch.bat` was failing at step 6 due to a moved script
(`WIP\level_design\patch_spawn_groups.py` -> `WIP\level_design\spawns\scripts\patch_spawn_groups.py`).
This was fixed but the crash persists after a successful build.

## Hypotheses (most likely first)

### H1: Formation count is stored/referenced elsewhere (MOST LIKELY)

The game probably stores the number of formations (or an index into formations) somewhere outside
the formation data area. Candidates:

1. **Script bytecode area** (1376 bytes between monster entries and formation templates, starting
   at `0xF7AA9C`). This area contains what appears to be an offset table at its start:
   ```
   +0:  0x3C (60)     +4:  0x00 (0)
   +8:  0x50 (80)     +12: 0xF4 (244)
   +16: 0x198 (408)   +20: 0x1FC (508)
   +24: 0x260 (608)   +28: 0x2A4 (676)
   +32: 0x328 (808)   +36: 0x3AC (940)
   +40: 0x410 (1040)  +44: 0x494 (1172)
   +48: 0x00           ...zeros...
   ```
   These are relative offsets (from script_start) pointing into the script area.
   The script bytecode likely contains commands like "pick random formation 0..N" where N is
   hardcoded.

2. **The 96-byte monster entries** at `group_offset` might contain a formation count field.

3. **The SLES executable** might contain per-area formation count tables.

If the game expects 8 formations and tries to read formation index 4 (for example), it would
compute the offset based on the old layout and land in the middle of a record or in the padding,
causing a crash.

### H2: Formation offsets are referenced by absolute position

Rather than reading formations sequentially, the game might jump to specific offsets for each
formation. The script bytecode might contain absolute offsets like:

```
spawn_formation(offset=0xF7B274)  // original F06
```

After rewriting the area, `0xF7B274` no longer contains a valid formation start. It contains data
from our larger formations at a different alignment. This would explain the crash.

**Evidence:** The original F06 was at `0xF7B274`, and the user's modified JSON still has
`"offset": "0xF7B274"` in F00 (from the original extraction). This suggests the extractor
captured each formation's original absolute offset.

### H3: The suffix bytes encode formation behavior

The original suffixes have specific patterns:
- `00000000` - used by F00 (3xGoblin only)
- `02000000` - used by formations with Shaman (F01, F02, F05, F06)
- `00000a00` - used by formations with Bat (F03, F04, F07)

These might encode spawn behavior (animation type, encounter trigger type, etc.).
Incorrect suffixes could cause rendering issues or crashes. The user's modified formations
used `00000000` for F01/F02, which might be wrong for their composition.

This alone probably wouldn't cause a crash, but combined with H1/H2 it could contribute.

## Recommended investigation

1. **Compare a working patched area vs this broken one** - check if any area where we changed
   the formation COUNT (not just composition) works in-game. If all count-changes crash, H1/H2
   is confirmed.

2. **Test with exactly 8 formations** - redistribute the 27 slots across 8 formations (matching
   the original count) and verify the crash goes away. This would confirm H1.

3. **Disassemble the MIPS bytecode** around formation spawn logic in SLES_008.45 to find where
   formation count / offsets are stored.

4. **Dump the script area bytecode** and look for patterns that reference formation indices or
   offsets.

## Practical workaround

Until the formation count/offset mechanism is fully understood, **always keep the same number
of formations as the original**. Redistribute slots across the original formation count.

For Cavern of Death Floor 1 Area 1: keep 8 formations, redistribute 27 slots as desired.
