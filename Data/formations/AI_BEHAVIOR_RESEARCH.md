# AI Behavior Block Research

## Summary

Each monster type with a non-NULL L value has a behavior block in the script area of BLAZE.ALL.
These blocks are indexed by the ROOT offset table at the start of the script area.

**Key finding: block structure is NOT uniform across monster types.**
Some blocks contain parameter-like uint16 values, others contain uint32 offset tables (bytecode refs),
and others contain repeating 32-byte records. Field meanings are UNCONFIRMED without in-game testing.

## Root Offset Table

At the start of each area's script area. Indexed by L value.
- `root[L] = 0` means NULL (monster uses EXE default behavior, no custom data)
- `root[L] = N` means behavior block at `script_start + N`

Example (Cavern F1 Area1, script_start = 0xF7AA9C):
```
root[0] = 0x003C  -> Goblin (valid block)
root[1] = 0x0000  -> Shaman (NULL = default behavior)
root[2] = 0x0050  -> (valid)
root[3] = 0x00F4  -> Giant-Bat (valid block)
```

## Raw Data Comparison (32 bytes each)

### Ground Melee Monsters

**Goblin (Cavern F1, L=0)** at 0xF7AAD8:
```
uint16: 0, 0, 468, 634, 420, 634, 0, 2048, 900, 0, 0, 2048, 900, 0, 0, 0
hex:    00 00 00 00 d4 01 7a 02 a4 01 7a 02 00 00 00 08 84 03 00 00 00 00 00 08 84 03 00 00 00 00 00 00
```

**Harpy (Castle F1, L=3)** at 0x23FF368:
```
uint16: 0, 0, 0, 0, 450, 580, 0, 2048, 900, 0, 0, 0, 900, 0, 0, 151
hex:    00 00 00 00 00 00 00 00 c2 01 44 02 00 00 00 08 84 03 00 00 00 00 00 00 84 03 00 00 00 00 97 00
```

Shared values: 2048 (0x0800) at offset 0x0E, 900 (0x0384) at offsets 0x10 and 0x18.

### Fast/Aggressive Monsters

**Wolf (Castle F1, L=4)** at 0x23FF3AC:
```
uint16: 5000, 0, 0, 0, 506, 65535, 65535, 65535, 1, 0, 0, 0, 4, 150, 60836, 0
hex:    88 13 00 00 00 00 00 00 fa 01 ff ff ff ff ff ff 01 00 00 00 00 00 00 00 04 00 96 00 a4 ed 00 00
```

FFFF cluster at offsets 0x0A-0x0F (possibly special flags or disabled fields).

### Flying Monsters

**Giant-Bat (Cavern F1, L=3)** at 0xF7AB90:
```
uint16: 0, 21, 2067, 64376, 102, 0, 3072, 0, 881, 65535, 65535, 65535, 3, 0, 0, 0
hex:    00 00 15 00 13 08 78 fb 66 00 00 00 00 0c 00 00 71 03 ff ff ff ff ff ff 03 00 00 00 00 00 00 00
```

Unique: flags_02 = 21 (only flying monster with non-zero here). FFFF at 0x12-0x16.

### Offset Table Type (NOT parameters!)

**Zombie (Castle F1, L=2)** at 0x23FF324:
```
uint32: 1880, 1948, 2016, 2084, 2152, 2284, 2352, 2452
hex:    58 07 00 00 9c 07 00 00 e0 07 00 00 24 08 00 00 68 08 00 00 ec 08 00 00 30 09 00 00 94 09 00 00
```

This is clearly **NOT a parameter header** - it's a table of uint32 offsets
(increasing values: 1880, 1948, 2016, ...). Likely bytecode program references.

### Repeating Record Type

**Blue-Slime (Cavern F7, L=7)** at 0xF8EFD4:
```
row1: d4 ef 84 03 c8 00 00 00 00 00 00 00 57 01 de 02 ff ff ff ff 00 00 01 00 00 00 00 00 01 0b 18 00
row2: e9 ee 90 01 fa 04 00 00 00 00 00 00 57 01 e4 02 ff ff ff ff 00 00 01 00 00 00 00 00 01 0b 18 00
```

Bytes 12-31 are nearly identical across rows = repeating 32-byte record structure, not header.

## Observations

### Likely Parameter Fields (Goblin/Harpy pattern)
- Offset 0x0E: value 2048 shared between ground melee types
- Offset 0x10, 0x18: value 900 shared
- Offsets 0x04-0x0A: vary between monsters, could be timers or ranges

### FFFF Patterns
- Ground melee (Goblin, Harpy): no FFFF values
- Aggressive (Wolf): FFFF at 0x0A-0x0E
- Flying (Bat): FFFF at 0x12-0x16
- Passive (Slime, Spirit-Ball): FFFF at 0x10-0x12
- Likely means "disabled" or "use default" for that parameter

### Block Type Varies by Monster
| Monster | Block Type | Evidence |
|---|---|---|
| Goblin, Harpy | Parameter header | Shared uint16 values, reasonable ranges |
| Wolf | Parameter header | Similar structure with FFFF flags |
| Giant-Bat | Parameter header | Different layout, flying flags |
| Zombie | Offset table | Monotonically increasing uint32 values |
| Blue-Slime | Record list | Repeating 32-byte patterns |
| Spirit-Ball | Record list | Same pattern as Blue-Slime |

## What Would Be Needed to Modify AI

1. **Per-field testing**: Change one uint16 at a time in Goblin's block, observe in-game
2. **Bytecode decoding**: 63 opcodes, only 0x18/0x19 (spell list add/remove) decoded
3. **EXE tracing**: See how spawn init (0x80021C70) reads these blocks to confirm field layout
4. **Test candidates**: Start with Goblin offsets 0x04, 0x08, 0x0A, 0x0E (most likely to be timers/ranges)

## Tools

- `dump_ai_blocks.py` - Extracts and compares behavior blocks across areas
- `ai_blocks_dump.json` - Machine-readable dump of all analyzed blocks
