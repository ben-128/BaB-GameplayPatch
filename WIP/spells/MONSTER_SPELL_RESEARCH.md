# Monster Spell System - Research Notes (2026-02-10)

## Problem
Goblin-Shaman still casts original spells (Fire Bullet, Magic Missile, Enchant Weapon, Stone Bullet)
despite patching both the spell SET table and the EXE spell_index.

## What We Patched (and why it doesn't work)

### Patch 1: Spell SET table (BLAZE.ALL)
- 16 entries x 16 bytes at 6 offsets in BLAZE.ALL
- We changed entry #6 content to match entry #8 (Blaze, Lightningbolt, Blizzard, Poison Cloud)
- All 6 copies correctly patched (verified)
- **RESULT: No effect on monster spells**

### Patch 2: EXE spell_index
- Changed byte at BIN offset 0x29601050 (SLES 0x1BE38, RAM 0x8002BE38)
- **FINDING: This code is CD-ROM DMA/transfer init, NOT spell assignment**
- The surrounding code stores 640, 240 (PS1 screen resolution) - it's graphics init
- **RESULT: No effect (wrong code patched)**

## Actual Monster Spell Architecture (DECODED)

### Entity fields involved
| Offset | Size | Purpose | Set by |
|--------|------|---------|--------|
| +0x150 | byte | Animation/attack phase counter (0-15, cycles) | Overlay code at 0x009870xx |
| +0x160 | 8 bytes | Spell availability bitfield (slot 0) | Overlay init at 0x0098A6A0 |
| +0x168 | 8 bytes | Spell availability bitfield (slot 1) | Overlay init |
| +0x2B0 | byte | Unknown (zeroed) | Overlay init at 0x0098A588 |
| +0x2B1 | byte | Set to 1 at init | Overlay init at 0x0098A59C |
| +0x2B2 | byte | Spell slot 2 (0xFF=none, active buff) | Overlay (class-dependent) |
| +0x2B3 | byte | Spell slot 3 (0xFF=none) | Overlay init |
| +0x2B4 | byte | Spell slot 4 (0xFF=none) | Overlay init |
| +0x2B5 | byte | **Spell list index** (into pointer_table) | Overlay at 0x0098A630 |
| +0x2B6 | byte | Secondary spell param | Overlay init |

### Spell list index initialization (0x0098A630 in BLAZE.ALL)
```
andi $v0, $v0, 0x0007        ; entity+0x150 & 7 = class (0-7)
lui $at, 0x8006
addu $at, $at, $v0
lbu $v0, -29904($at)         ; table[class] at RAM 0x80058B30
sb $v0, 0x2B5($v1)           ; store to entity+0x2B5
```

The 8-byte lookup table at **RAM 0x80058B30** (EXE offset 0x49330) is BSS.
It is **NEVER written to** by any code in the EXE or BLAZE.ALL.
Result: entity+0x2B5 = **always 0** for all entities.

### Spell casting code (EXE at 0x80024E14)
```
lbu $a1, 0x2B5($s3)          ; spell_list_index = 0
lw $v0, 0x490C($v0)          ; data_ptr from 0x8005490C
lw $v1, 156($v0)             ; pointer_table = data_ptr + 0x9C
sll $v0, $a0, 2              ; index * 4
lw $s5, 0($v1)               ; spell_list = pointer_table[0]
; ...
; Loop: iterate 48-byte entries, check entry+0x1D, cast first that passes
addiu $s5, $s5, 48           ; next 48-byte entry
```

### Overlay code reads (19 total in 3 clusters)
- 0x00927Dxx-0x009282xx (7 reads, $s1 = entity base)
- 0x0092DAxx-0x0092E8xx (7 reads, $s5 = entity base)
- 0x00932Dxx-0x00933Cxx (5 reads, $s1 or $s5 base)

The overlay code:
1. Reads entity+0x2B5 (=0)
2. Indexes pointer_table from data_ptr+0x9C
3. Also computes entity+0x160+(index*8) for per-type bitfield
4. Calls 0x80026A90 with entity+0x2B5 as $a1 (spell select function)

### Runtime data structures (BSS - populated by overlay loader)
| RAM address | Size | Purpose |
|-------------|------|---------|
| 0x80058B30 | 8 bytes | Class-to-spell-index table (always 0) |
| 0x8005490C | 4 bytes | data_ptr (global zone data pointer) |
| data_ptr+0x9C | 4 bytes | Pointer to spell pointer_table |
| 0x8003C020 | N*5 bytes | Spell count table (per spell_list_index) |

### Spell name/definition table (SINGLE COPY)
- Location: 0x908E68 in BLAZE.ALL
- Format: 48-byte entries, ~123 entries
- Contains: spell name (ASCII, null-terminated) + combat parameters
- Fields: +0x10=damage, +0x18=element, +0x1D=cast_probability, +0x24=range, +0x2A=target
- **NO COPIES exist anywhere in BLAZE.ALL** - this is the only instance
- Shared by players and monsters

### Spell SET table (6 COPIES - used for player spell learning?)
- Offsets: 0x9E8D8E, 0xA1755E, 0xA3555E, 0xA5155E, 0xA7BD66, 0xA9B55E
- 16 entries x 16 bytes each
- bytes[2-9] = offensive spell IDs, bytes[0-1,10-15] = support bytes
- **NOT used during monster spell casting** (patching has no effect)

## Key Conclusions

1. **Monster spells are NOT selected via the spell SET table**
   The 16-entry SET table is likely for player spell learning/availability,
   not for monster combat spell selection.

2. **All spell-casting entities use spell_list_index = 0**
   The class-to-index table at 0x80058B30 is never populated (BSS zeros).

3. **pointer_table[0] determines monster spells**
   This runtime pointer (from data_ptr+0x9C) points to 48-byte spell entries.
   The entries are the SAME 48-byte records at 0x908E68 (shared with players).

4. **The spell count determines how many entries are checked**
   From table at 0x8003C020, indexed by spell_list_index*5.

5. **The 48-byte entries at 0x908E68 are the actual combat data**
   Only 1 copy exists. Modifying these affects ALL casters (players + monsters).

## What's Still Unknown

- Where does data_ptr (0x8005490C) get set? Not by any visible store in EXE or overlay.
  Likely by the overlay LOADER via DMA/memcpy from BLAZE.ALL data section.

- What does pointer_table[0] actually point to? If it points into the 0x908E68
  table directly, which offset? This determines WHICH subset of spells the
  Shaman iterates through.

- How is the spell count at 0x8003C020 populated? Also BSS, loaded by overlay.

- The overlay's RAM base address is unknown (no internal JAL/J calls found in
  the overlay - all calls target EXE functions).

## Proposed Next Steps

### Option A: Nuclear test
Modify the 48-byte spell entries at 0x908E68 directly:
- Swap Fire Bullet (#0) params with Blaze (#10) params
- If Shaman casts Blaze effects, confirms the name table IS the combat source
- Downside: affects ALL Fire Bullet casters (players too)

### Option B: Find pointer_table via savestate
Use ePSXe savestate to dump RAM and find:
- Value at 0x8005490C (data_ptr)
- Value at data_ptr+0x9C (pointer_table address)
- Value at pointer_table[0] (spell list start)
- Compare with known BLAZE.ALL offsets to find the file mapping

### Option C: Disable current spell patches
Remove the non-functional spell SET table and EXE patches to reduce
build complexity. They have no effect on monster spells.
