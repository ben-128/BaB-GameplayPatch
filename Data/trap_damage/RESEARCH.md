# Trap/Environmental Damage - Research Notes

## Damage Function (CONFIRMED)

**Address:** `0x80024F90` (EXE, never moves)
**JAL word:** `0x0C0093E4` (same for all overlays)

### Formula
```
damage = (maxHP * damage_param) / 100
```
- `damage_param` = percentage of max HP (e.g., 2 = 2%, 10 = 10%)
- Minimum damage = 1 (clamped)
- Death: HP set to 0, flag `0x40000000` set at entity+0x0140

### Disassembly (key part)
```
0x80024FE4: lh   $a1, 0x148($at)     ; load max_HP from player block
0x80024FEC: mult $a1, $a3            ; max_HP * damage_param
0x80024FF0: mflo $a1
0x80024FF4: lui  $v0, 0x51EB         ; magic constant for /100
0x80024FF8: ori  $v0, 0x851F
0x80024FFC: mult $a1, $v0
0x80025000: mfhi $t0
0x80025004: sra  $v1, $t0, 5         ; >> 5 completes /100
0x80025010-18: min damage = 1
0x8002501C: lhu  $v0, 0x14C($a0)     ; load current HP
0x80025024: subu $v0, $v0, $a1       ; HP -= damage
0x80025028: sh   $v0, 0x14C($a0)     ; store new HP
```

### Player Data Blocks
- Base: `0x800F0000 + player_index * 0x2000`
- Player index loaded via `lbu $a0, 8($entity)` then `sll $v1, $a0, 13`
- +0x0100 = name (ASCII), +0x0144 = level, +0x0148 = maxHP, +0x014C = curHP

---

## Three Damage Delivery Paths (CONFIRMED 2026-02-10)

### Path 1: Script Bytecode (per-area DATA)

Per-area script data contains damage commands as bytecode:
```
[0x1E] [damage%] [00/FF]
```
- Opcode 0x1E = damage command (handler 0x8001C558 in Table 1)
- byte[1] = damage percentage (e.g., 0x05 = 5%, 0x02 = 2%)
- byte[2] = 0x00 (continue) or 0xFF (script terminator)

**No confirmed instances in Cavern F1** (earlier matches were false positives).
Other dungeon areas may use this path — investigation needed.

### Path 2: Direct JAL callers (overlay code)

Overlay code calls `jal 0x80024F90` with `$a1` set to an immediate value.

| Count | Original % | Description |
|-------|-----------|-------------|
| 2 | 2% | Light environmental (fall damage) |
| 3 | 3% | Medium-light traps |
| 6 | 5% | Poison/periodic damage |
| 3 | 10% | Heavy traps |
| 1 | 20% | Very heavy trap |

**15 total** across 7+ overlay regions. Pattern:
```
addiu/ori $a1, $zero, N    ; $a1 = damage%
...
jal   0x80024F90           ; call damage function
```

### Path 3: Overlay code with register-passed damage% (168 sites)

Overlay functions receive damage% from a **per-entity data table at RAM 0x80054698**.
- 189 total `jal 0x80024F90` sites in overlay code
- ~15 use hardcoded immediates (caught by Path 2 / Pass 1)
- **168 use saved registers** with pattern: `sll $a1, $sN, 16; sra $a1, $a1, 16`
  (sign-extending a halfword from a register loaded from 0x80054698+offset)
- Table at 0x80054698 is in BSS (zero in EXE), filled from BLAZE.ALL entity init data
- **Falling rock 10% uses this path**: halfword at BLAZE 0x009ECE8A → RAM 0x80054698+N

---

### Cavern F1 Damage Sites — Complete Map

**Overlay code region ~0x0093xxxx** (3 sites with immediate $a1):
| BLAZE offset (jal) | BLAZE offset (ori) | Damage | Type |
|--------------------|--------------------|--------|------|
| 0x00936E60 | 0x00936E5C | 2% | Blade/spike trap |
| 0x00937C28 | 0x00937C24 | 2% | Blade/spike trap |
| 0x0093C004 | 0x0093C000 | 5% | Floor trap |

**Code overlay region 0x009E0000-0x00A00000** (6 sites with register $a1):
All 6 use saved registers. Damage % is a pass-through from EXE caller.
- Template A (3 sites): damage from 5th stack arg via $s7/$s3
- Template B (3 sites): damage from $a1 via $s6

**Falling rocks (10% damage) = LOCATION UNKNOWN:**
- Not in script bytecode (false positives)
- Not in immediate-argument jal sites (only 2% and 5% found)
- Not hardcoded in EXE (the "10" at 0x80025364 is an effect ID, not damage%)
- **NOT at BLAZE 0x009ECE8A** (in-game test 2026-02-10: changed collision/hitbox, not damage)
- Not in any of the 6 immediate-value-10 sites in overlay (all are state machine variables)
- Damage% reaches Template A/B via register arguments from an overlay-internal dispatch
- **See "Entity Descriptor System" section below for current understanding**

**Three other dungeons hardcode 10% as immediate** (jal 0x80024F90 with $a1=10):
| BLAZE offset | Context |
|-------------|---------|
| 0x01787E90 | distance < 50, element=9 |
| 0x028985FC | distance < 300, element=0 |
| 0x0296780C | distance < 300, element=0 |

**EXE effect ID system** (NOT damage%, confirmed):
- Function 0x80025308 dispatches to overlay stub 0x8006E044
- Bit 23 of entity+0x00 selects between paired IDs: (2,12), (3,13), ..., (10,20)
- These are action/effect type IDs, NOT damage percentages
- 0x8006E044 is NOP stub in EXE, filled from BLAZE.ALL at runtime

---

### Entity Init Data Block 0x009ECE8A — WRONG LEAD (2026-02-10)

**In-game test result:** Patching halfword at BLAZE 0x009ECE8A from 10 to 50:
- Collision/hitbox behavior **CHANGED** (harder to get hit by falling rock)
- Damage amount **UNCHANGED** (still 10% of max HP)
- **Conclusion:** data_block+0x06 controls collision radius or hitbox size, NOT damage%

#### Entity data block layout at 0x009ECE84

```
Offset  Value   Interpretation
+0x00   0x0000  (unknown)
+0x02   0x0003  (unknown, count?)
+0x04   0x0008  (unknown)
+0x06   0x000A  = 10 → COLLISION/HITBOX parameter (NOT damage%)
+0x08   0x0010  = 16 (unknown)
+0x0A   0x020C  = 524 (unknown, large value)
+0x0C   0x0003  (unknown)
+0x0E   0x0008  (unknown)
...
```

Only ONE byte with value 0x0A (10) exists in the entire data block (at +0x06).
The damage% (also 10) must come from elsewhere.

---

### Entity Descriptor System — DISCOVERED (2026-02-10)

The falling rock entity uses a **descriptor pointer** system:

#### How entity+0x3C gets its value (EXE at 0x80021E68)

```mips
lui   $v1, 0x8005
lw    $v1, 0x4914($v1)     ; v1 = *(0x80054914) = global struct
lbu   $v0, 0x0004($s0)     ; v0 = entity+0x04 (entity type byte)
lw    $v1, 0x0038($v1)     ; v1 = global+0x38 (template array base)
sll   $v0, $v0, 2          ; v0 = type_index * 4
addu  $v0, $v0, $v1        ; v0 = &template_array[type_index]
lw    $v0, 0x0000($v0)     ; v0 = template_array[type_index]
sw    $v0, 0x003C($s0)     ; entity+0x3C = descriptor pointer
```

So: **entity+0x3C = template_array[entity_type_byte]**
- Global struct at `*(0x80054914)`
- Template array at `global+0x38`
- Indexed by `entity+0x04` (entity type byte)
- For falling rock: entity+0x3C = 0x800BF7EC

#### Descriptor → Template A1 relationship

| Address (RAM) | Address (BLAZE) | Content |
|---------------|-----------------|---------|
| 0x800BF7EC | 0x009ECFEC | Descriptor/parameter block (32 bytes) |
| 0x800BF80C | 0x009ED00C | Template A1 function (code) |

The descriptor is exactly **32 bytes (0x20)** before the Template A1 function.

#### Descriptor data at 0x009ECFEC (4 × 8-byte entries)

```
009ECFEC: 20 00 18 00 48 00 XX XX  00 10 02 01 XX XX XX XX
009ECFFC: XX XX XX XX XX XX XX XX  XX XX XX XX XX XX XX XX
```

Some of these bytes likely encode the damage% (value 10), but which field is unknown.

#### Dispatch is in OVERLAY code, NOT in EXE

**Comprehensive search of the entire EXE confirmed:**
- 55 `lw $reg, 0x3C($reg)` instructions found
- **NONE** follow the pattern `lw+0x3C → addiu/lw+0x20 → jalr`
- No chain exists: no `lw descriptor → add offset → jalr function` anywhere in EXE
- The dispatch from descriptor to Template A1 (descriptor+0x20) happens **inside overlay code**
  loaded from BLAZE.ALL at runtime (addresses like 0x80073xxx or 0x800Axxxx)

**EXE uses entity+0x3C in two known patterns:**
1. Static vtable dispatch at 0x80035744 and 0x80035CB8: loads global vtable+0x3C,
   calls 0x80037CD0 (NOT per-entity descriptor)
2. Combat dispatch save/restore at 0x800244F8: saves entity+0x3C to $s1, swaps it
   with ptr_array[creature_type]+0x10, calls overlay stub, then restores original

#### Next steps for falling rock damage%

1. **Find the overlay dispatch function** that reads entity+0x3C and calls descriptor+0x20.
   This is likely one of the 3 overlay stubs (0x800739D8, 0x80073B2C, 0x80073F9C) loaded
   from BLAZE.ALL at runtime. Need to find the stub code in BLAZE.ALL and disassemble it.
2. **Trace descriptor byte fields** — the 32-byte descriptor block at 0x009ECFEC may
   contain the damage% value, or the overlay dispatch may pass it as a hardcoded argument.
3. **Alternative**: search BLAZE.ALL overlay code for the byte pattern that computes
   descriptor+0x20 (addiu $reg, $reg, 0x20) followed by jalr.

---

### GPE Entity State Machine — WRONG LEAD (2026-02-10)

**CORRECTED 2026-02-10:** entity+0x14 is a **STATE MACHINE VARIABLE**, not a damage %.

#### What entity+0x14 actually is

Full analysis of code overlay region 0x009E0000-0x00A00000 revealed:
- entity+0x14 stores **state IDs**: 0x0A(10), 0x14(20), 0xC8(200), 0xC9(201), 0xCE(206), 0xD3(211)
- Code checks entity+0x14 against 0xCE (206) and 0xC8 (200) as state transitions
- Only 2 reads from entity+0x14 via $s5 in entire 128KB region (both are state comparisons)
- Values 10 and 20 are **state codes** that happen to coincide with damage percentages

#### Why patching these values didn't work

Patching `ori $v0, $zero, 10` → `ori $v0, $zero, 35` changes the state machine transition
to an unknown state (35), which likely falls through to a default/no-op case. The damage
value is determined elsewhere (still under investigation).

#### Pattern (still present in patcher, only $s5)
```
ori/addiu $v0, $zero, N     ; state ID (10, 20, etc.)
sh  $v0, 0x14($s5)          ; store to GPE entity state field
```

**95 sites** across 39 code overlay regions, each with pattern: 10, 20, 20 (+ sometimes 2).

#### Multi-register expansion ($s0/$s1/$s2/$s6) was also wrong

The Cavern's `$s1` variant writes to a DIFFERENT entity struct:
- `$s1`+0x14 = **camera shake intensity** (confirmed: patching increased shake, not damage)
- `$s0` is used for spell/action entries (82 reads vs 2 for $s5), offset 0x14 = different field
- **Reverted to $s5-only** in patcher v4.2

---

### BLAZE.ALL Architecture (DISCOVERED 2026-02-10)

Per-area data and executable code are stored SEPARATELY in BLAZE.ALL:

**Per-area DATA overlays** (at 0x009468A8 for Cavern F1):
- Contain: meshes, textures, animations, spawn scripts, 96-byte stats
- NO executable code (zero jalr, zero jal, zero jr instructions)
- Load to RAM 0x80080000

**Per-dungeon CODE overlays** (39 regions, 0x009E0000-0x02BB0000):
- Contain: GPE entity handlers, state machines, trap logic
- Each ~64-128KB, spaced at varying intervals
- Call EXE functions via direct `jal` (no `jalr` found)
- 6 `jal 0x80024F90` (damage function) in first region alone

**6 damage call sites** in first code overlay, organized as 3 pairs (2 templates):

Template A — "Proximity/range check" (sites at BLAZE 0x009ED16C, 0x009F3608, 0x009FBE8C):
- Functions at BLAZE 0x009ED00C, 0x009F34A8, 0x009FBD2C
- AoE: loops 4 entities, checks 3D distance vs radius, applies damage if in range
- `$a1` = damage% from saved register (`$s7` or `$s3`), loaded from **5th stack arg**
- Also takes element type (6th arg) and radius (7th arg)
- Sets 60-frame cooldown at entity+0x96 after hit

Template B — "Entity-based / bitmask guard" (sites at BLAZE 0x009ED748, 0x009F3BE4, 0x009FC468):
- Functions at BLAZE 0x009ED648, 0x009F3AE4, 0x009FC368
- Per-entity damage with bitmask/parity guards (0x10000000, 0x40000000 flags)
- `$a1` = damage% from `$s6`, loaded from **$a1 (2nd register arg)**
- Entity byte at +0x09 used for nibble-based flag extraction

**All 6 sites use saved registers**, never immediates. Damage % is always a
**pass-through argument** from the caller (EXE dispatch system).

**No intra-overlay calls**: all 153 jal targets are EXE functions. Overlay
functions are called indirectly from EXE via function pointers/dispatch table.

---

### Damage % Origin — BYTECODE SCRIPT SYSTEM (DISCOVERED 2026-02-10)

The damage % is embedded in **bytecode script data** in the per-area region of BLAZE.ALL.

#### Script Interpreter System (CONFIRMED)

**Two dispatch tables** for a bytecode script engine:

| Table | Base Address | Entries | Handler Range | Caller |
|-------|-------------|---------|---------------|--------|
| Table 1 | 0x8003BDE0 | 39 (opcodes 0-38) | 0x8001B678-0x8001C7A8 | 0x8001A03C |
| Table 2 | 0x8003BE84 | 32 (opcodes 0-31) | 0x8001CBB8-0x8001E03C | 0x8001CB2C |

**Dispatch function at 0x8001A03C:**
```
0x8001A0A4: lui   $s3, 0x8004
0x8001A0A8: addiu $s3, $s3, -16928   ; $s3 = 0x8003BDE0
0x8001A094: lbu   opcode              ; read opcode byte from script stream
0x8001A09C: beq   opcode, 0xFF, exit  ; 0xFF = script terminator
0x8001A0B4: sll   $v0, $a0, 2        ; opcode * 4
0x8001A0CC: addu  $v0, $v0, $s3      ; table_base + opcode*4
0x8001A0D0: lw    $v0, 0($v0)        ; load handler pointer
0x8001A0DC: jalr  $v0                 ; call handler
```

**Wrapper function at 0x80019FA8** — 11 call sites in EXE:
`0x80018754, 0x8001A160, 0x8001CAD8, 0x8001CCBC, 0x80020EF4, 0x8002116C,
 0x80021634, 0x800218B8, 0x80021A40, 0x80025E50, 0x80026420`

**Opcode 0x1F (31) = DAMAGE COMMAND:** (NOT 0x1E — off-by-one from table base)
- Handler at 0x8001C558 (Table 1, index 31 from base 0x8003BDE0)
- Reads byte[1] from script stream = **damage percentage**
- Calls `jal 0x80024F90` with `$a1 = byte[1]`
- (Opcode 0x1E = handler 0x8001C4E4 = entity state/flag manipulation, NOT damage)

#### Script bytecode NOT used for Cavern damage

Searched Cavern F1 script area (0xF7AA9C-0xF80000) for opcode 0x1F with damage values.
**ALL matches were FALSE POSITIVES** — data values in spawn/placement tables:
- 0xF7AE90: `1E 05` = inside spawn point entry 9 (data, not bytecode)
- 0xF7BD5C: `1E 02` = entity type ID 0x1E in placement table (word: 0xFFFF021E)
- 0xF7BD3C: `1F 02` = similar placement entry

Cavern falling rocks do NOT use the script bytecode system for damage.
Other areas may use it (investigation needed).

#### ALU Sub-interpreter (0x8001A3D4)

Commands 2-7 in Table 1 are ALU operations using a sub-interpreter:
- **188-entry jump table** at 0x80044444
- 3 data widths: 8-bit (0x00-0x3B), 16-bit (0x40-0x7B), 32-bit (0x80-0xBB)
- 3 addressing modes × 12 ALU ops + 8 comparison ops per width
- Operations: MOV, ADD, SUB, OR, AND, XOR, MUL, DIV, MOD, SHL, SHR, RMOD(rand)
- Comparisons: EQ, NE, GT, LT, GE, LE, TST, TSTZ
- Register files at fixed RAM: 0x80054B58, 0x80054BC0, 0x80054C08, 0x80054D10

#### Script loop entry point

Main script loop at **0x80037594** reads commands from byte stream,
dispatches via Table 1 (0x8003BDE0). Terminates on 0xFF byte.
Called through wrapper 0x80019FA8 with 11 call sites.

---

### Buffers and Queues — RULED OUT

**Buffer 0x8004B560** = Sound/SFX event queue (NOT damage dispatch):
- 24 entries × 64 bytes, write index at 0x8004B4FD
- Enqueue at 0x80019ADC stores sound event, calls SPU immediately (0x8002D804)
- Code 0x93 = sound effect ID (only written, never read back)
- Zero consumer functions found — ring buffer for sound subsystem only

**Buffer 0x8004BB60** = Entity collision event queue:
- 32 entries × 20 bytes, write index at 0x8004B4FD
- Enqueue (0x80019E5C): called from overlay code (63+ sites)
- Consumer (0x80019ED4): processes collision geometry, triggers sound as side effect
- Does NOT dispatch to damage functions

**Table 0x8004BF28** = Sound/VFX asset pointer array (NOT damage values):
- 60 word-sized entries, filled by asset loader at 0x8002AA60
- Each entry = pointer to loaded BLAZE.ALL audio/VFX data
- Indexed by collision type (0x38-0x3B for traps)
- Read by 0x80019ADC to attach VFX to sound events

**Entity callback vtable 0x800BF184** = 416-entry virtual method table:
- All entries initialized to `jr $ra` stub at 0x800BF684
- Slots populated at runtime when entities spawn
- Used by entity management system above the script interpreter

#### What we ruled out
- entity+0x14 via $s5 = GPE **state machine ID**, NOT damage %
- entity+0x14 via $s1 = **camera shake intensity**
- entity+0x14 via $s0 = different struct entirely (spell/action entries)
- No immediates at any of the 6 damage call sites in code overlay
- No lhu+0x14 → sw stack patterns in the code overlay
- 0x8004B560 buffer = sound queue, not damage dispatch
- 0x8004BF28 table = VFX pointers, not damage values

---

## Patcher Status (step 7d)

**File:** `patch_trap_damage.py`
**Config:** `trap_damage_config.json` (`overlay_patches.values`)

Config values:
```json
{"2": 10, "3": 15, "5": 22, "10": 50, "20": 50}
```

### Pass 1: JAL callers (15 sites) — CONFIRMED WORKING (Path 2)
- Searches for `jal 0x80024F90` with immediate `$a1`
- These are direct damage function calls in overlay code
- Catches traps that hardcode the damage % right before calling
- Only covers ~15 of ~189 total damage call sites

### Pass 2: DISABLED — GPE entity init was WRONG

**Removed from patcher.** entity+0x14 is a STATE MACHINE variable, not damage %.
Patching these BREAKS state transitions without changing damage.
See "GPE Entity State Machine" section for details.

### Pass 3: Entity init data (1 site) — WRONG OFFSET, NEEDS CORRECTION

**Current state:** patcher has BLAZE 0x009ECE8A in ENTITY_INIT_OFFSETS.
**In-game test confirmed this is WRONG** — it changes collision/hitbox, not damage%.
**This offset should be removed** until the correct damage% location is found.
See "Entity Init Data Block 0x009ECE8A — WRONG LEAD" section.

### UNSOLVED: Path 3 — Register-passed damage% (~168 sites)

The vast majority of damage call sites (168 of 189) pass damage% via registers loaded
from entity descriptor/data blocks. Finding the correct data locations requires:
1. Tracing the overlay dispatch that calls Template A/B with damage% arguments
2. Identifying the descriptor byte(s) that encode damage% in each entity type
3. Building a map of all descriptor block locations across 39 overlay regions

See "Entity Descriptor System" section for current understanding.

### UNSOLVED: Script bytecode damage (Path 1)

Some areas MAY use bytecode opcode 0x1F with damage% as byte[1].
Cavern F1 does NOT use this path (all matches were false positives).
Other dungeon areas need investigation.

---

## EXE Division Shift (REMOVED)

Was `patch_trap_damage_exe.py` (step 9d) - modified the division shift in the damage
function at EXE 0x80025004. **Removed** because it affects ALL 189 callers including
combat damage, not just traps. The overlay patcher (v4) is the correct solution.

---

## Previous Wrong Lead: 0x8008A3E4

Function 0x8008A3E4 is a **COLOR/TINT modifier**, NOT damage.
In-game test confirmed: modifying these values has NO effect on damage.

---

## ePSXe Savestate Format
- Compression: gzip
- Header: "ePSXe\x06\x00" + game ID (64 bytes)
- PS1 RAM: decompressed offset **0x1BA**, size 2MB
- Overlay mapping (Cavern): BLAZE_offset = RAM_offset + 0x008C68A8
