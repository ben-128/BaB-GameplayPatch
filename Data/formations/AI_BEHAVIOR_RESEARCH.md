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

## Where Is The Real Monster AI?

### Candidates (from SPAWN_MODDING_RESEARCH.md):

1. **EXE State Machine at 0x8003B324** (32 entries)
   - Handles: idle, move, attack, cast states per frame
   - Dispatched by function at 0x80017F2C
   - This is likely where attack timing, detection range, etc. are coded

2. **EXE Combat Actions at 0x8003C1B0** (55 entries)
   - Specific combat action implementations (0x800270B8-0x80029E80)
   - Entity type -> action handler index mapping

3. **Bytecode Programs at root[5+]** (per-area + global shared)
   - Offset tables with values 0x1000-0x4FF0
   - Interpreted by 0x8001A03C with 63 opcodes
   - Only 5/63 opcodes decoded (0x00, 0x01, 0x02, 0x18, 0x19, 0xFF)

4. **Secondary Function Table at 0x800BF184**
   - Called by opcode 0x00
   - Purpose unknown

### What To Try Next
- **Savestate approach**: Make 2 savestates (idle vs attacking), diff RAM to find AI state variables
- **EXE state machine tracing**: Disassemble handlers at 0x8003B324 to find timer/speed logic
- **Bytecode opcode decoding**: Decode more of the 63 opcodes to understand AI programs
- **Memory watch**: Use ePSXe debugger to watch which RAM addresses change when Goblin attacks

## Tools

- `dump_ai_blocks.py` - Extracts zone/camera config blocks (mislabeled as "AI blocks")
- `ai_blocks_dump.json` - Machine-readable dump
- `analyze_bytecode_interpreter.py` - EXE bytecode interpreter disassembly
- `ai_behavior_config.json` - Test patches (all disabled, only camera height confirmed)
