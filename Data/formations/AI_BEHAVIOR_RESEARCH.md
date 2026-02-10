# AI Behavior Block Research

## Summary

**UPDATE 2026-02-10: The root[L] blocks are NOT monster AI behavior.**

In-game testing of the Goblin block (Cavern F1) proved that modifying the uint16 fields
has **NO effect on monster AI**. The only confirmed effect is:
- **Offset 0x06 = CAMERA HEIGHT** (634=normal, 0=ground level)

The blocks pointed to by root[0..3] contain **ZONE/CAMERA configuration**, not per-monster AI.

## In-Game Test Results (2026-02-10, Cavern F1 Area1 Goblin)

All tests performed on the Goblin block at 0xF7AAD8 (root[0], L=0).
Build + inject + test in ePSXe for each change.

| Test | Field | Offset | Change | AI Effect | Other Effect |
|------|-------|--------|--------|-----------|-------------|
| A | timer_08 | 0x08 | 420 -> 50 | **NONE** | None visible |
| C | timer_0A | 0x0A | 634 -> 65535 | **NONE** | None visible |
| E | dist_0E | 0x0E | 2048 -> 8000 | **NONE** | None visible |
| F | timer_04 | 0x04 | 468 -> 0 | **NONE** | None visible |
| G | timer_06 | 0x06 | 634 -> 0 | **NONE** | **CAMERA dropped to ground level** |

### Methodology
- Tests A through G were first activated ALL at once -> camera changed, AI unchanged
- Then disabled all, re-enabled ONE at a time with rebuild between each
- Isolated test_G (offset 0x06) as the camera height control
- Other 4 fields (0x04, 0x08, 0x0A, 0x0E) had zero observable effect

### Conclusions
1. **ALL "timer/distance" hypotheses were WRONG** (attack speed, cooldown, detection range, wind-up)
2. **Offset 0x06 = camera height** (CONFIRMED)
3. **Other fields** (0x04, 0x08, 0x0A, 0x0E) may be zone rendering/lighting params (not tested further)
4. The block labels "timer_04", "timer_08", "dist_0E" etc. in dump_ai_blocks.py are **misleading**
5. **Real monster AI** is elsewhere - likely in the EXE state machine or bytecode programs at root[5+]

## Root Offset Table

At the start of each area's script area. Indexed by L value.
- `root[L] = 0` means NULL (monster uses EXE default behavior, no custom data)
- `root[L] = N` means data block at `script_start + N`

Example (Cavern F1 Area1, script_start = 0xF7AA9C):
```
root[0] = 0x003C  -> Zone/camera config block (NOT Goblin AI!)
root[1] = 0x0000  -> NULL (Shaman = no custom data)
root[2] = 0x0050  -> Zone config block 2
root[3] = 0x00F4  -> Zone config block 3 (NOT Giant-Bat AI!)
root[4] = 0x0198  -> config/model table
root[5+]          -> Bytecode offset tables (actual AI programs?)
```

**Root[0..3] = zone/camera config. Root[5+] = bytecode program tables.**

## Raw Data (for reference)

### Goblin block (0xF7AAD8) - 20 bytes (root[0] to root[2])
```
uint16: 0, 0, 468, 634, 420, 634, 0, 2048, 900, 0
offset: 00  02  04   06   08   0A   0C  0E    10   12
                     ^^^
                     CAMERA HEIGHT (confirmed)
```

### Harpy block (Castle F1, L=3) at 0x23FF368
```
uint16: 0, 0, 0, 0, 450, 580, 0, 2048, 900, 0, 0, 0, 900, 0, 0, 151
```

### Wolf block (Castle F1, L=4) at 0x23FF3AC
```
uint16: 5000, 0, 0, 0, 506, 65535, 65535, 65535, 1, 0, 0, 0, 4, 150, 60836, 0
```

### Giant-Bat block (Cavern F1, L=3) at 0xF7AB90
```
uint16: 0, 21, 2067, 64376, 102, 0, 3072, 0, 881, 65535, 65535, 65535, 3, 0, 0, 0
```

### Zombie block (Castle F1, L=2) - Offset table type
```
uint32: 1880, 1948, 2016, 2084, 2152, 2284, 2352, 2452
```
This is a table of bytecode program offsets (NOT parameter values).

### Blue-Slime block (Cavern F7, L=7) - Record list type
```
Repeating 32-byte records with identical bytes 12-31 across rows.
```

## Root[5+] Analysis (2026-02-10) - NOT Bytecode

**UPDATE: root[5+] offset tables do NOT contain bytecode program references.**

Dumped all root[5..11] entries for Cavern F1 Area1. Findings:

### Offset Table Structure (root[5..9])
- Format: uint32 LE arrays of script-relative offsets
- root[5]: 25 entries (offsets 0x1D74-0x219C + 4 header values + NULLs)
- root[6]: 17 entries (offsets 0x21D4-0x24D4, evenly spaced ~0x30-0x50 apart)
- root[7]: 33 entries (offsets 0x24F8-0x2B30, evenly spaced)
- root[8]: 33 entries (offsets 0x2B50-0x2E70)
- root[9]: 25 entries (mixed: area-specific 0x2E8F-0x2EDD + global shared pairs + small offsets)

### What root[5+] Actually Points To
The offsets resolve to **32-byte entity/spawn placement records** with:
- 3D coordinates (signed int16 LE: X, Y, Z)
- Direction/facing values
- FFFFFFFF group separators
- 0B command markers
- Reference indices

**This is NOT bytecode.** The data contains byte values (0xB4, 0xFE, 0x63, etc.) that are
far outside the valid opcode range (0x00-0x3E for 63 opcodes). The repeating 32-byte
record structure with coordinate patterns confirms these are spatial/spawn data tables.

### root[9] "Globally Shared Pairs" Explained
Entries 12-17 of root[9] are paired offsets:
```
[12]=0x0AD1  [13]=0x2294  (pair 1)
[14]=0x0AD6  [15]=0x2174  (pair 2)
[16]=0x0ADB  [17]=0x1184  (pair 3)
```
Both members of each pair point to spawn placement records, not bytecode.

### root[10..11] = 0B Command Records (confirmed)
- Contain [XX 0B YY 00] headers + coordinates + FFFFFFFF separators
- These are spawn/placement commands, same format as formation records

## Corrected Script Area Map
```
Root entry   | Data type                    | Status
-------------|------------------------------|--------
root[0..3]   | Zone/camera config           | CONFIRMED (camera height at +0x06)
root[4]      | Config/model table           | Identified
root[5..9]   | Entity placement tables      | CONFIRMED (NOT bytecode)
root[10..11] | 0B command records (spawns)   | CONFIRMED
```

**All root table entries are spatial/config data. None contain bytecode programs.**

## Where Is The Real Monster AI?

### Eliminated candidates:
- ~~root[0..3] blocks~~ = zone/camera config (IN-GAME TESTED)
- ~~root[5+] offset tables~~ = entity placement data (DUMP CONFIRMED 2026-02-10)
- ~~96-byte entries~~ = name + stats only (19 swap tests)
- ~~R field~~ = no effect (tested)
- ~~Type-8 bytecode region~~ = room scripts, crashes when zeroed

### Remaining candidates:

1. **EXE State Machine at 0x8003B324** (32 entries) - STRONGEST CANDIDATE
   - Dispatched by function at 0x80017B6C (2304-byte stack frame)
   - Entity struct fields: timer at $s2+0x8C6, flags at $s2+0x8C7
   - State handlers control per-frame AI: idle/chase/attack/cast
   - **AI timing/speed likely hardcoded in these EXE handlers**

2. **EXE Combat Actions at 0x8003C1B0** (55 entries)
   - Specific combat action implementations (0x800270B8-0x80029E80)
   - Entity type -> action handler index mapping

3. **Bytecode Interpreter at 0x8001A03C** (63 opcodes at 0x8003BDE0)
   - May run room scripts, NOT monster AI
   - Opcodes: 0x00=call_secondary, 0x01=GOTO, 0x18=add_spell, 0x19=remove_spell

4. **Secondary Function Table at 0x800BF184**
   - Called by opcode 0x00
   - Purpose unknown

### Key insight: AI is likely in EXE code, NOT data
The script area contains zone config, spawn placement, and room scripts.
Monster AI behavior appears to be primarily controlled by **EXE state machine handlers**
at 0x8003B324, with the L field determining which entity spawn config is loaded.
AI parameters (attack speed, detection range, cooldowns) are likely hardcoded
in the MIPS assembly of individual state handlers.

### What To Try Next
- **Disassemble EXE state handlers**: Focus on the 32 handlers at 0x8003B324 to find
  timer/speed constants. These are the most likely location of AI behavior code.
- **Savestate approach**: Compare savestates with monsters in different AI states
  (idle vs chasing vs attacking) to identify entity struct AI fields
- **Memory watch**: Use ePSXe debugger to watch entity struct changes during combat

## Tools

- `dump_ai_blocks.py` - Extracts zone/camera config blocks (mislabeled as "AI blocks")
- `ai_blocks_dump.json` - Machine-readable dump
- `analyze_bytecode_interpreter.py` - EXE bytecode interpreter disassembly
- `ai_behavior_config.json` - Test patches (all disabled, only camera height confirmed)
