# Monster Spell System - Complete Research (2026-02-10)

## Problem (SOLVED)
Goblin-Shaman still casts original spells (Fire Bullet, Magic Missile, Enchant Weapon, Stone Bullet)
despite patching both the spell SET table and the EXE spell_index.

**Root cause**: Both patches targeted the wrong systems. The spell SET table is for player
spell learning only, and the EXE patch hit CD-ROM DMA code, not spell assignment.

## What We Patched (and why it doesn't work)

### Patch 1: Spell SET table (BLAZE.ALL)
- 16 entries x 16 bytes at 6 offsets in BLAZE.ALL
- We changed entry #6 content to match entry #8 (Blaze, Lightningbolt, Blizzard, Poison Cloud)
- All 6 copies correctly patched (verified)
- **RESULT: No effect on monster spells** (this table is player-only)

### Patch 2: EXE spell_index
- Changed byte at BIN offset 0x29601050 (SLES 0x1BE38, RAM 0x8002BE38)
- **FINDING: This code is CD-ROM DMA/transfer init, NOT spell assignment**
- **RESULT: No effect (wrong code patched)**

---

## Complete Spell System Architecture (DECODED via savestate analysis)

### Spell Pointer Table (data_ptr + 0x9C)

At runtime, `data_ptr` = 0x800DD8AC (from BSS at 0x8005490C).
`pointer_table` = 0x800DDA68 (from data_ptr + 0x9C).
16 pointer entries, 8 used:

| Index | RAM Address | Count | Category | Contents |
|-------|-------------|-------|----------|----------|
| 0 | 0x800DE714 | 29 | **Offensive** | Fire Bullet, Spark Bullet, Water Bullet, Stone Bullet, Striking, Lightbolt, Dark Wave, Smash, Magic Missile, Enchant Weapon, Blaze, Lightningbolt, Blizzard, Poison Cloud, Extend Spell, Magic Ray, Shining, Dark Breath, Dispell Magic, Petrifaction, Explosion, Thunderbolt, Freeze Beast, Earth Javelin, Death Spell, Teleport, Chaos Flare, Meteor Smash, Fusion |
| 1 | 0x800DEC84 | 24 | **Priest/Support** | Turn Undead, Healing, Protection, Resist, Detect Align, Refresh, Detect Enemies, Anti-poison, Anti-paralysis, Anti-feeble, Sanity, Restore, Barrier, Resist Field, Stone Flesh, Requiem, Holy Word, Remove Curse, Remove Silence, Regeneration, Resurrection, Recover Energy, Reincarnation, Call Angel |
| 2 | 0x800DF104 | 20 | **Status/Enchantment** | Sleep, Slow, Haste, Enchant Fire, Enchant Earth, Enchant Wind, Enchant Water, Charm, Silence, Magic Shield, Levitate, Shield, Heavy Slow, Quick, Invincible, Anti-Circle, Summon Water, Summon Fire, Summon Wind, Summon Earth |
| 3 | 0x800DF4C4 | 7 | **Herbs** | Lavender, Sage, Vervain, Savory, Rue, Hyssop, NightShade |
| 4 | 0x800DF614 | 1 | **Dwarf skill** | Wave |
| 5 | 0x800DF644 | 1 | **Hunter skill** | Arrow |
| 6 | 0x800DF674 | 1 | **Fairy skill** | Stardust |
| 7 | 0x800DF6A4 | 30 | **Monster abilities** | Poison Touch, Paralyze Touch, Paralyze Eye, Confusion Eye, Sleep Eye, Fire Breath, Cold Breath, Thunder Breath, Acid Breath, Poison Breath, Stun Breath, Mad Scream, Drain, Howling, Knockback, Stun, Sleep Song, Evil Eye, Evil Howling, Evil Field, Invincible, Regeneration, Earthquake, Flare Breath, Dead Gate, Destroyer, Wind Smash, Tidalwave, Hell Holwing, Dark Blaze |
| 8 | NULL | - | - | Unused |

**CRITICAL**: pointer_table entries are **byte-for-byte identical** to the spell definition
table at BLAZE.ALL offset 0x908E68. The data is loaded into RAM via the overlay loader.

### 48-byte Spell Entry Format

| Offset | Size | Field | Example (Fire Bullet) |
|--------|------|-------|-----------------------|
| +0x00 | 16 | Name (ASCII, null-padded) | "Fire\0Bullet\0\0\0\0\0" |
| +0x10 | u8 | Spell ID (sequential) | 0x00 |
| +0x11 | u8 | Unknown flags | 0x00 |
| +0x12 | u8 | Unknown param | 0x02 |
| +0x13 | u8 | MP cost (base?) | 0x04 |
| +0x14 | u8 | Spell level/power | 0x02 |
| +0x15 | u8 | Unknown | 0x00 |
| +0x16 | u8 | Element type | 0x02 (fire) |
| +0x17 | u8 | Unknown | 0x00 |
| +0x18 | u8 | Damage/effect value | 0x0A |
| +0x19-1B | 3 | Unknown | 0x00 0x00 0x00 |
| +0x1C | u8 | Target type | 0x01 (single) |
| +0x1D | u8 | Cast probability/priority | 0x0A |
| +0x1E | u8 | Unknown param | 0x03 |
| +0x1F | u8 | Ingredient count | 0x03 |
| +0x20-2F | 16 | Ingredient list (spell recipe) | varies |

Element types: 0=none, 1=thunder, 2=fire, 3=water, 4=earth, 5=wind, 6=light, 7=dark, 8=holy, 9=evil

### Spell Count / Level Unlock Table (0x8003C020)

5-byte groups per spell_list_index, interpreted as cumulative spell counts at each tier:

| List | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 | Total entries |
|------|--------|--------|--------|--------|--------|---------------|
| 0 (Offensive) | 5 | 10 | 15 | 20 | 26 | 29 |
| 1 (Support) | 5 | 11 | 16 | 19 | 22 | 24 |
| 2 (Status) | 3 | 7 | 9 | 12 | 16 | 20 |
| 3 (Herbs) | 0 | 0 | 0 | 0 | 8 | 7 |
| 4-7 | sparse | - | - | - | - | varies |

Additionally, per-list spell counts at **0x80057A34** (indexed by spell_list_index).

### Entity Spell Fields

| Offset | Size | Purpose | Set by |
|--------|------|---------|--------|
| +0x150 | byte | class_type (& 0x07 = class 0-7) | Overlay init |
| +0x160 | 8 bytes | Spell availability **bitfield** (for spell_list[idx]) | Overlay init at 0x0098A6A0 |
| +0x168 | 8 bytes | Spell availability bitfield (slot 1) | Overlay init |
| +0x2B5 | byte | **spell_list_index** (into pointer_table) | Overlay at 0x0098A630 |
| +0x2BF | byte | Current spell slot (being cast) | Overlay runtime |

### spell_list_index Initialization

At overlay 0x0098A630 (RAM during Cavern):
```
andi $v0, $v0, 0x0007        ; entity+0x150 & 7 = class (0-7)
lui $at, 0x8006
addu $at, $at, $v0
lbu $v0, -29904($at)         ; table[class] at RAM 0x80058B30
sb $v0, 0x2B5($v1)           ; store to entity+0x2B5
```

The 8-byte lookup table at RAM 0x80058B30 is BSS (all zeros).
Result: entity+0x2B5 = **always 0** (offensive spells) for ALL entities.

Player overrides: Player "Impy" (Elf, class 0x07) has spell_idx=2 at runtime,
meaning the overlay or player init code sets it differently for players.

---

## Overlay Code Analysis (3 clusters, disassembled from savestate)

### Overlay RAM Mapping
- Overlay code loaded at RAM 0x80060000+ (overwrites upper EXE region)
- BLAZE.ALL offset formula: `BLAZE_offset = (RAM - 0x80000000) + 0x008C68A8`
- Example: RAM 0x80061478 -> BLAZE 0x00927D20

### Cluster 1: Spell Casting Decision (RAM 0x80061400-0x80061B00)
- Reads entity+0x2B5, loads pointer_table[spell_idx]
- Checks entity+0x160 bitfield to find which spells are available
- entity+0x2B6 used as secondary parameter (checked with bltz)
- Checks `entity+0x1FC4` (element resistance?) bitfield
- Calls **0x80026A90** (EXE spell select function) at 2 sites
- Calls overlay 0x80061A3C, 0x8006E044, 0x80073D48

### Cluster 2: Spell Availability Builder (RAM 0x80067200-0x80068100)
- Builds list of available spell IDs into RAM 0x800A3F20
- Reads entity+0x2B5, computes bitfield at entity+0x160+(idx*8)
- Reads spell count from **0x80057A64** (via `lw $a0, 31332($at)`)
- Iterates: for each spell in list, checks bitfield bit
  - Bit set → store positive spell ID (available)
  - Bit clear → store negative spell ID (unavailable)
- Calls **ai_run_bytecode (0x80017B6C)** for spell animations
- Heavy use of entity positioning (0x80014DBC, 0x80012D40, 0x80015CF8)

### Cluster 3: Spell Selection & Execution (RAM 0x8006C500-0x8006D500)
- Reads entity+0x2BF (current spell slot index)
- Uses spell_list_index to compute bitfield offset
- Reads spell count from **0x80057A34** + spell_list_index
- Selection loop: decrements entity+0x2BF, wraps around using spell count
- Calls combat functions: 0x80023A10, 0x80024024, 0x80023C2C, 0x80023E7C, 0x80024088
- Calls 0x80021F88 (entity spawn/init?)

### JAL Call Summary (from overlay clusters)
Key EXE functions called:
| Function | Called from | Purpose |
|----------|-----------|---------|
| 0x80026A90 | Cluster 1 (x2) | Spell select/execute |
| 0x80017B6C | Cluster 2 (x2) | ai_run_bytecode (animation) |
| 0x80017B20 | Cluster 2 (x5) | Related to bytecode |
| 0x80019DAC | Clusters 2,3 | Unknown (called 4x) |
| 0x80019DD8 | Clusters 2,3 | Unknown (called 5x) |
| 0x80014DBC | Clusters 2,3 | Entity positioning |
| 0x80012D40 | Clusters 2,3 | Entity positioning |
| 0x80024024 | Cluster 3 | Combat utility |
| 0x80024088 | Cluster 3 | Combat utility |
| 0x80023A10 | Cluster 3 | Combat handler |
| 0x80023C2C | Cluster 3 | Combat handler |
| 0x80023E7C | Cluster 3 | Combat handler |
| 0x80021F88 | Cluster 3 | Entity spawn/init? |

---

## How Monster Spell Casting Works (Complete Flow)

```
1. INITIALIZATION (overlay init, 0x0098A6xx):
   - entity+0x2B5 = 0 (from BSS table, always offensive list)
   - entity+0x160 = bitfield (which spells this entity can cast)
   - entity+0x2BF = starting spell slot

2. SPELL AVAILABILITY (Cluster 2, per-frame):
   - Read spell_list_index from entity+0x2B5
   - Compute bitfield address: entity + 0x160 + (spell_list_index * 8)
   - Read spell count from 0x80057A34 + spell_list_index
   - For each spell 0..count-1:
     - Check bit in bitfield
     - Build available/unavailable list at 0x800A3F20

3. SPELL SELECTION (Cluster 3, when casting):
   - Read entity+0x2BF (current spell slot)
   - Index into available spell list
   - Check bitfield to confirm spell is usable
   - Wrap around using spell count if needed

4. SPELL EXECUTION (Cluster 1 + EXE):
   - Load spell entry from pointer_table[spell_list_index][spell_id]
   - Read 48-byte entry: name, MP cost, element, damage, range
   - Call 0x80026A90 (EXE spell select function)
   - Run spell animation via ai_run_bytecode (0x80017B6C)
```

---

## How to Mod Monster Spells

### Option 1: Change spell PARAMETERS (affects ALL casters)
Modify the 48-byte entries at BLAZE.ALL 0x908E68:
- Change damage, MP cost, element, range, cast probability
- **WARNING**: Shared by players and monsters - changes affect everyone

### Option 2: Change WHICH spells a monster has (per-entity bitfield)
Modify the overlay init code that sets entity+0x160:
- Each bit in the 64-bit bitfield = one spell from pointer_table[spell_list_index]
- Bit 0 = Fire Bullet, Bit 8 = Magic Missile, Bit 9 = Enchant Weapon, etc.
- Find the overlay init at 0x0098A6A0 that writes entity+0x160
- Patch the bitfield to enable/disable specific spells

### Option 3: Change spell LIST assignment
Modify entity+0x2B5 to use a different pointer_table index:
- Currently all monsters use index 0 (offensive spells)
- Setting to 7 would give monster-only abilities
- Requires patching the overlay init at 0x0098A630

### Option 4: Modify spell entries in the monster-only list
pointer_table[7] (30 entries) contains monster-exclusive abilities.
These use a simpler format (most fields zero except name, element, damage).
Modifying these won't affect player spells.

---

## Spell SET Table (6 copies - PLAYER ONLY, confirmed)

- Offsets: 0x9E8D8E, 0xA1755E, 0xA3555E, 0xA5155E, 0xA7BD66, 0xA9B55E
- 16 entries x 16 bytes; bytes[2-9]=offensive IDs, bytes[0-1,10-15]=support
- **NOT used during monster spell casting** (patching all 6 copies had zero effect)
- Likely used for player spell learning / shop menus

## Per-Monster Spell Assignment — Disassembly Analysis (2026-02-10)

### Overlay Init Code Structure

The overlay init at BLAZE 0x0098A5E0 - 0x0098A7A0 is a long sequence of
`lui+lw+nop+sb` groups. Each group:
1. Loads entity pointer from global RAM 0x80066E2C (`lui $v0, 0x8006` + `lw $v0, 0x6E2C($v0)`)
2. Waits 1 instruction (NOP for load delay)
3. Stores a byte to the entity struct (sb)

The entity pointer is reloaded from the global for EVERY SINGLE store. This is
verbose/unoptimized compiler output — the same pattern repeats ~30 times.

### Entity Pointer Global

**RAM 0x80066E2C** = overlay BSS variable holding pointer to current entity being initialized.
- Loaded via: `lui $v0, 0x8006` + `lw $v0, 28204($v0)` (28204 = 0x6E2C)
- 0x8006 << 16 + 0x6E2C = **0x80066E2C**
- Same global used by ALL init groups in the overlay

### BLAZE <-> RAM Mapping

Formula: `RAM = BLAZE_offset + 0x7F739758` (= BLAZE - 0x008C68A8 + 0x80000000)

| BLAZE offset | RAM address | Purpose |
|-------------|-------------|---------|
| 0x0098A69C | 0x800C3DF4 | byte0_ori (PATCH START) |
| 0x0098A6D0 | 0x800C3E28 | byte3_sb (PATCH END) |
| 0x0098A6D4 | 0x800C3E2C | First instruction AFTER patch |

### Patch Site: 14-Instruction Verbose Pattern (0x0098A69C - 0x0098A6D0)

```
[0]  0x0098A69C  34030001  ori  $v1,$zero,0x0001     ; value=1
[1]  0x0098A6A0  A0430160  sb   $v1,0x160($v0)       ; entity+0x160 byte 0 = 1
[2]  0x0098A6A4  3C028006  lui  $v0,0x8006            ; reload entity ptr
[3]  0x0098A6A8  8C426E2C  lw   $v0,0x6E2C($v0)
[4]  0x0098A6AC  00000000  nop                         ; load delay
[5]  0x0098A6B0  A0400161  sb   $zero,0x161($v0)     ; entity+0x161 = 0
[6]  0x0098A6B4  3C028006  lui  $v0,0x8006            ; reload entity ptr
[7]  0x0098A6B8  8C426E2C  lw   $v0,0x6E2C($v0)
[8]  0x0098A6BC  00000000  nop                         ; load delay
[9]  0x0098A6C0  A0400162  sb   $zero,0x162($v0)     ; entity+0x162 = 0
[10] 0x0098A6C4  3C028006  lui  $v0,0x8006            ; reload entity ptr
[11] 0x0098A6C8  8C426E2C  lw   $v0,0x6E2C($v0)
[12] 0x0098A6CC  00000000  nop                         ; load delay
[13] 0x0098A6D0  A0400163  sb   $zero,0x163($v0)     ; entity+0x163 = 0
```

Effect: writes entity+0x160 = 0x00000001 (little-endian: 01 00 00 00)

### Context Before Patch Site

Before 0x0098A69C, the init code writes:
- entity+0x2B2, +0x2B3, +0x2B4 (some init values, 0xFF for +0x2B3/4)
- entity+0x2B5 = spell_list_index (from BSS table, always 0)
- entity+0x2B6 through +0x2BB = 0 (zeroed)

**Critically:** at BLAZE 0x0098A614, the code reads `lbu $v0, 0x150($v1)` (entity+0x150
= class_type/flags byte), meaning the entity struct is already partially initialized.

### Context After Patch Site

After 0x0098A6D0, the SAME pattern continues for bitfield slots 1-3:
- entity+0x168-0x16B: slot 1 (value=1,0,0,0) — creature_type 1 (never used)
- entity+0x170-0x173: slot 2 (value=1,0,0,0) — creature_type 2 (never used)
- entity+0x178-0x17B: slot 3 (value=3,3,3,3) — creature_type 3 (never used)

These are DEAD for monsters (creature_type always 0), but initialized anyway.

### Register Usage at Patch Site Entry

At instruction [0] (0x0098A69C):
- **$v0** = entity pointer (loaded by lui+lw at 0x0098A694-0x0098A698, BUT still in
  load delay at [0] — becomes usable starting at [1])
- **$v1** = was set to 0xFF by earlier code, but we overwrite it with ori
- **$at** = free (used as scratch by compiler-generated lui)
- **$a0-$a3** = unknown, not used in the dump range

### Monster Identity Byte

From 96-byte stat entries in BLAZE.ALL (Cavern F1 Area1 at 0xF7A97C):

| Monster | stat_a (+0x10, level) | stat_b (+0x12, identity) |
|---------|----------------------|--------------------------|
| Goblin | 20 (0x0014) | 2 (0x0002) |
| Shaman | 24 (0x0018) | 3 (0x0003) |
| Bat | 15 (0x000F) | 4 (0x0004) |

Entity struct mapping (from MEMORY): "+0x10 = stat_b+unk_bytes"
However, in 96-byte stat entries: +0x10 = stat_a (level), +0x12 = stat_b (identity).
**Needs in-game verification: is the identity byte at entity+0x10 or entity+0x12?**

### Replacement MIPS Code (Per-Monster Table Lookup)

Uses 8 instructions + 6 embedded table entries = 14 slots total:

```mips
; $v0 = entity pointer (ready from previous lui+lw, usable from instr [1])
[0]  lui   $at, TABLE_HI          ; table addr high (fills $v0 load delay)
[1]  lbu   $v1, ID_OFF($v0)       ; identity byte from entity struct
[2]  nop                            ; $v1 load delay
[3]  sll   $v1, $v1, 2            ; identity * 4 (table index)
[4]  addu  $at, $at, $v1          ; &table[identity]
[5]  lw    $v1, TABLE_LO($at)     ; bitfield = table[identity]
[6]  beq   $zero, $zero, +7       ; branch past table data (to 0x0098A6D4)
[7]  sw    $v1, 0x160($v0)        ; DELAY SLOT: store 32-bit bitfield
[8]  table[0]                      ; data: identity 0 bitfield
[9]  table[1]                      ; data: identity 1 bitfield
[10] table[2]                      ; data: identity 2 (Goblin)
[11] table[3]                      ; data: identity 3 (Shaman)
[12] table[4]                      ; data: identity 4 (Bat)
[13] table[5]                      ; data: identity 5 (default)
```

TABLE address = RAM of instruction [8] = BLAZE 0x0098A6BC + 0x7F739758 = 0x800C3E14
TABLE_HI = 0x800C, TABLE_LO = 0x3E14
Branch at [6] targets BLAZE 0x0098A6D4 = RAM 0x800C3E2C, offset = +7

### Free Space (for zones needing >6 table entries)

Large zero block at **BLAZE 0x0098DC4C** (25,524 bytes), at end of overlay section.
Preceded by RAM pointer 0x8005FD44. Available for external table placement if identity
values exceed 0-5 range.

### Approach Validation

- `sw` at entity+0x160 writes a full 32-bit word — replaces 4 separate `sb` instructions
- Branch delay slot trick: `sw` in delay slot executes BEFORE branch, using $v1 from
  the `lw` 2 instructions earlier (load delay satisfied by `beq` instruction)
- Code AFTER the patch (0x0098A6D4+) reloads entity ptr from scratch — no register deps
- $at, $v0, $v1 are the only registers used — all temporary, safe to clobber

## Implementation Status (2026-02-10)

### Per-Monster Spell Bitfield — TWO SITES PATCHED, NO EFFECT

**Critical discovery**: There are **two separate code sites** that write entity+0x160:

1. **Spawn init** at BLAZE 0x0098A69C (14 instructions, entity in $v0)
   - Runs once when monster spawns into the world
   - Original: writes 0x00000001 (Fire Bullet only)

2. **Combat init** at BLAZE 0x0092BF74 (13 instructions, entity in $s5)
   - Runs at the START of every combat encounter
   - Original: RESETS entity+0x160 = 0x00000001 regardless of spawn init
   - **This is why the first patch alone had no effect!**

**Files:**
- `Data/ai_behavior/patch_monster_spells.py` — MIPS code generator + table builder
- `Data/ai_behavior/overlay_bitfield_config.json` — per-zone monster spell config

### Approach v1: Table Lookup Only (NO EFFECT)

Both sites replaced with per-monster table lookup (identity byte → bitfield).
6-entry tables, no sentinel.

**In-game test result: NO EFFECT** — Shaman still casts same vanilla spells.

### Approach v2: Table Lookup + Sentinel (NO EFFECT)

Added sentinel write: entity+0x146 = 9999 (0x270F) at both sites.
Purpose: force the dispatch OR-loop to skip entirely so our bitfield is definitive.
Used compact 3-entry tables with identity subtraction (addiu $v1, -min_identity).

Diagnostic test: set ALL monsters to 0x03FFFFFF (26 spells, tier 1-5).

**In-game test result: STILL NO EFFECT** — Shaman still casts same vanilla spells.
Expected: if sentinel worked, monsters would cast Explosion, Thunderbolt, etc.
Actual: identical vanilla behavior.

### Why the Sentinel Doesn't Work

Detailed dispatch function analysis (see section below) revealed:

1. **Sentinel = 9999 causes function EXIT, not loop skip**:
   The check at 0x800244D0 is `bne counter, 9999, post_loop` then `j 0x80024F04`.
   When counter == 9999 → **jumps to near end of function** (0x80024F04).
   This likely skips the entire action dispatch (not just the level-up sim).

2. **The OR-loop rarely runs** — it's timer-gated:
   entity+0x158 must accumulate to >= 9999 before the loop body executes.
   For fresh combat (timer=0), the function exits without modifying +0x160.
   So the OR-loop was **never the problem** — it doesn't overwrite on first call.

3. **Our code may not execute at all**, OR the identity offset is wrong.
   Monsters behave identically to vanilla, which means either:
   - Our overlay patches are ignored (code path not taken)
   - entity+0x10 contains wrong identity value → table returns default → vanilla
   - Something else resets +0x160 after our writes

### Current Hypotheses (ranked)

**H1: Wrong identity offset (most likely)**
- Our code reads entity+0x10 but identity might be at +0x12
- If entity+0x10 is some other value (not 2/3/4), compact table index overflows
- With addiu -2, a wrong byte could produce index far out of range
- PSX reads garbage from out-of-bounds table access → random bitfield
- But behavior looks vanilla → could be that entity+0x10 = 0 for all monsters
  and compact index 0-2 = -2 (0xFFFFFFFE) → garbage read → crashes? No crash observed.

**H2: Code doesn't execute for this area**
- Overlay loading might not use the code at these offsets for Cavern F1
- The BLAZE-to-RAM mapping might be wrong for this specific overlay region

**H3: Entity init (site 3) erases our values**
- Entity init at 0x916C44 zeroes +0x160..+0x163
- Could run AFTER combat init, negating our writes

### Approach v3: Hardcoded Constant (NO EFFECT — DEFINITIVE)

Replaced both sites with the simplest possible code:
```mips
; Spawn init (entity in $v0):
lui  $v1, 0x03FF           ; high 16 bits
ori  $v1, $v1, 0xFFFF      ; $v1 = 0x03FFFFFF
sw   $v1, 0x160($v0)       ; store bitfield
nop x 11                    ; padding

; Combat init (entity in $s5):
lui  $v0, 0x03FF
ori  $v0, $v0, 0xFFFF
sw   $v0, 0x160($s5)
nop x 10
```

No table lookup, no identity read, no sentinel. Just hardcoded constant write.

**Patches verified present in output/BLAZE.ALL** (27 words differ from clean).
**BIN injection confirmed** (patch_blaze_all.py ran successfully).

**In-game test: STILL NO EFFECT.**

### CONCLUSION: Wrong BLAZE.ALL Offsets

**The code at BLAZE 0x0098A69C and 0x0092BF74 does NOT execute for Cavern F1.**

These offsets were identified from RAM disassembly mapped back to BLAZE.ALL using
the delta formula (RAM - 0x80000000 + 0x008C68A8). But the mapping is wrong for
these specific addresses — they belong to a different dungeon's overlay, or the
overlay loader doesn't use a simple linear copy from these regions.

The BLAZE.ALL file is 46MB, and our search was limited to 0x900000-0x9A0000 (640KB).
The actual Cavern init code could be anywhere in the file.

### Approach v4: Infinite Loop Freeze Test (NO FREEZE — DEFINITIVE)

Replaced both sites with `beq $zero, $zero, -1` (infinite loop).
Game runs normally in Cavern F1, no freeze at spawn or combat.

**DEFINITIVE PROOF: Code at BLAZE 0x0098A69C / 0x0092BF74 is never executed
for Cavern of Death Floor 1.**

Additional verification:
- Searched entire 46MB BLAZE.ALL: only 1 copy of each pattern exists
- Patched bytes confirmed in output BIN (2 injection copies, 0 clean bytes remaining)
- Yet game behavior unchanged → these bytes are not loaded into active RAM for Cavern

### Root Cause: Wrong Overlay Region

The BLAZE-to-RAM delta (0x7F739758) may only be valid for a subset of BLAZE.ALL.
Different dungeons load different overlay ranges. The code at 0x0098xxxx may belong
to a larger dungeon whose overlay extends to RAM 0x800Cxxxx, while the Cavern overlay
only covers RAM 0x80060000-0x800Axxxx (approx).

The original RAM disassembly that identified these offsets may have been from a
different game state or dungeon context.

### Approach v5: Freeze Test at Entity Init 0x916C44 (NO FREEZE — DEFINITIVE)

Entity init (the third write site at BLAZE 0x00916C44, RAM 0x8005039C) was also
tested with an infinite loop. **No freeze** — the game runs normally in Cavern F1.

**ALL THREE overlay write sites in BLAZE.ALL are never executed for Cavern F1:**
- 0x0098A69C (spawn init) — no freeze
- 0x0092BF74 (combat init) — no freeze
- 0x00916C44 (entity init) — no freeze

### Comprehensive Verification

1. **Only 1 copy** of each init pattern exists in entire 46MB BLAZE.ALL
2. Patches **confirmed present** in output BIN (2 LBA injection copies, 0 clean bytes)
3. **ALL `lui $v0, 0x8006` patterns** (779 occurrences) in BLAZE.ALL are in 0x09xxxxxx range
4. The BLAZE-to-RAM formula `RAM = BLAZE + 0x7F739758` maps all three sites to
   RAM 0x8005-0x800C range, but **the game never loads these bytes into active RAM**
   for the Cavern of Death area

---

## EXE Overlay Loading Analysis (2026-02-10)

### No Hardcoded BLAZE.ALL Offsets in EXE

Searched the entire EXE (SLES_008.45) for:
- All `lui` instructions followed by `addiu/ori` that form BLAZE.ALL byte offsets
- String references to "BLAZE" or "blaze"
- Constants matching known data offsets (0xF7A964, 0x908E68, etc.)

**Result: NO hardcoded BLAZE.ALL byte offsets found in the EXE.**

The game uses `CdSearchFile` at 0x800316DC with the ISO9660 path `\BLAZE.ALL;1` to
locate the file's starting sector on disc, then uses **sector-based addressing**
to read specific regions.

### Sector-Based Area Loading

Key loading pattern found at RAM 0x80017CF0:
```mips
lbu   $v0, 20($s2)       ; sector count byte from area descriptor (struct+0x14)
nop                        ; load delay
addu  $v0, $v0, $v1       ; accumulate sector count
sll   $a0, $v0, 11        ; * 2048 (sector → byte offset)
lui   $v1, 0x8005
addiu $v1, $v1, -14832    ; base = 0x8004C610
addu  $a0, $a0, $v1       ; RAM target = base + sector_offset
```

- **Area descriptors** use a byte at struct+0x14 as a sector count
- Sector counts are accumulated (each area's start = sum of previous counts)
- Shifted left by 11 (×2048) to convert sectors to bytes
- Added to **RAM base 0x8004C610** to get the RAM load address

### LEVELS.DAT — NOT a Level Database

LEVELS.DAT (1,310,720 bytes) is a **flat TIM texture archive** containing 1070 PSX
TIM images (identified by 0x00000010 magic at regular intervals). It contains NO
area descriptors, overlay code, or level definitions. Used for textures only.

### Implications for Overlay Loading

The three overlay offsets we identified (0x0098xxxx, 0x0092xxxx, 0x0091xxxx) were
derived from a RAM disassembly using the formula:
  `BLAZE_offset = (RAM - 0x80000000) + 0x008C68A8`

This formula was derived from ONE verified mapping (RAM 0x80061478 ↔ BLAZE 0x00927D20).
**But different dungeons load different overlay regions.** The Cavern of Death overlay
may be loaded from a completely different BLAZE.ALL range than 0x0092-0x0098xxxx.

The game has TWO separate loading mechanisms:
1. **Area data** (formations, stats, scripts): loaded via sector-based addressing to ~0x800E27CC
2. **Overlay code** (spell init, combat): loaded to RAM 0x80060000+ from an unknown BLAZE region

---

## Corrected Overlay Mapping (2026-02-10)

### Mapping IS Correct (100% Verified)

The delta formula `BLAZE_offset = (RAM - 0x80000000) + 0x008C68A8` was verified by
comparing RAM savestate bytes against BLAZE.ALL content:
- **20/20 random cross-validation samples** matched perfectly
- **0 mismatches** across the entire 256KB overlay
- **7 independent reference points** all yield the same delta

### Cavern of Death Overlay Range

| Location | BLAZE Offset | RAM Address |
|----------|-------------|-------------|
| Overlay start | 0x009268A8 | 0x80060000 |
| Overlay end | 0x009668A8 | 0x800A0000 |
| Size | 256 KB | 256 KB |

### Re-classified Write Sites

| # | BLAZE | RAM | In Cavern Overlay? |
|---|-------|-----|--------------------|
| 1 | 0x0098A69C | 0x800C3DF4 | **NO** (above 0x800A0000) — different dungeon |
| 2 | 0x0092BF78 | 0x800656D0 | **YES** (between 0x80060000-0x800A0000) |
| 3 | 0x00916C44 | 0x8005039C | **NO** (below 0x80060000) — shared/common overlay |

**Only site #2 (0x0092BF78) is in the Cavern overlay.** It sets entity+0x160 = 0x00000001
via `ori $v0, $zero, 1` + `sb $v0, 0x160($s5)`.

### Init Block at RAM 0x80065580 - 0x80065710 (BLAZE 0x0092BE28 - 0x0092BFC8)

This is a combat/entity initialization block that sets:
- entity+0x0144 = 1 (level)
- entity+0x0146 = 1 (dispatch counter)
- entity+0x014A/014C/014E = 1 (other counters)
- entity+0x0160 = 0x00000001 (bitmask slot 0: Fire Bullet only)
- entity+0x0168 = 0x00000001 (bitmask slot 1)
- entity+0x0170 = 0x00000001 (bitmask slot 2)
- entity+0x0178 = 0x03030303 (bitmask slot 3)
- Then calls `jal 0x80023A10` (EXE stat copy function)

### Bitmask Access Points in Cavern Overlay

**Reads:**
1. RAM 0x8006153C (BLAZE 0x00927DE4): `lw $v1, 0x160($v1)` — bit check (dispatch path)
2. RAM 0x80061604 (BLAZE 0x00927EAC): `lw $v1, 0x160($v1)` — bit check + action select
3. RAM 0x8006801C (BLAZE 0x0092E8C4): `lbu $a3, 0x160($v0)` — byte-by-byte enumeration

**Counter +0x0146 interactions:**
- RAM 0x80065588: reads counter, computes timer (`val*2 + val/4 + 0x30`), calls dispatch wrapper 0x80024414
- RAM 0x80065C24: reads counter, clamps to 9999 sentinel if ≥ 10000

### Previous Freeze Test Issue

The earlier freeze test used the BUILD SYSTEM (build_gameplay_patch.bat). However:
- The freeze was at 0x0098A69C (SPAWN init, NOT in Cavern overlay) and 0x0092BF74 (COMBAT init, IS in Cavern overlay)
- It's possible the earlier test didn't trigger combat encounters, or the game loaded from a cached region

### Fresh Diagnostic (2026-02-10) — NO FREEZE (DEFINITIVE)

Standalone diagnostic (`WIP/spells/_diag_freeze_combat_init.py`):
- Copies clean BLAZE.ALL, applies freeze at 3 points in the init function
- Copies clean BIN, injects directly (no other patches applied)
- Verifies read-back from BIN: all 6 checks PASS (bytes confirmed in disc image)
- Freeze points: RAM 0x80065588, 0x800655DC, 0x800656CC

**Result: NO FREEZE.** Game runs normally, combat works.

Despite the code being present in RAM (confirmed by savestate byte comparison),
the init function is **never called** during Cavern F1 combat.

---

## DEFINITIVE CONCLUSION (2026-02-10)

### ALL overlay write sites to entity+0x160 are DEAD CODE for Cavern F1

| # | BLAZE | RAM | In Cavern Overlay? | Freeze Test |
|---|-------|-----|--------------------|-------------|
| 1 | 0x0098A69C | 0x800C3DF4 | NO (above range) | NO FREEZE |
| 2 | 0x0092BF78 | 0x800656D0 | **YES** (in range) | NO FREEZE |
| 3 | 0x00916C44 | 0x8005039C | NO (below range) | NO FREEZE |

- Site #2 is confirmed present in RAM by 100% savestate byte-matching
- BIN read-back verification confirmed freeze bytes are on disc
- Yet the code is **never reached** during Cavern F1 gameplay (area load + combat)
- The init function exists in RAM but is likely for a different entity type (players?)
  or a different game phase (character creation? town NPCs?)

### How entity+0x160 is actually set for monsters

The ONLY confirmed write to entity+0x160 that executes is the **EXE dispatch OR-loop**
at RAM 0x800244F4 (`lw/or/sw` inside the level-up simulation at 0x80024494).

The overlay code at RAM 0x80065588 reads entity+0x0146, computes a timer value,
and calls the dispatch wrapper (0x80024414). The dispatch function then runs the
level-up simulation which ORs spell bits into +0x160 over multiple iterations.

**Monster spell availability is built entirely by the EXE dispatch function,
not by any overlay init code.**

### Implication for modding

To change which spells monsters cast, the options are:
1. **Patch the EXE dispatch function** (0x80024494) — change tier thresholds, bit
   selection, or the OR-loop behavior. Requires EXE patching (SLES_008.45).
2. **Patch the tier table** at EXE 0x8003C020 — change how many spells unlock per tier.
3. **Find and patch the entity+0x0146 counter init** — if the counter starts higher,
   monsters would have more spells from the start. But entity struct init location
   in the EXE is unknown.
4. **Patch the overlay timer computation** at RAM 0x80065588 — force the timer to
   9999 immediately, causing the dispatch to run the OR-loop right away. This would
   give monsters ALL spells for their level instantly.

### Approaches NOT viable (proven)
- Overlay init patching (all 3 write sites are dead code for Cavern F1)
- Sentinel trick (sentinel causes function EXIT, not loop skip)
- Hardcoded bitfield in overlay (code never executes)

---

## Dispatch Function — Detailed Analysis (2026-02-10)

### Entry and Sentinel Check (0x80024494 - 0x800244E4)

The dispatch function starts with a sentinel check on entity+0x146:

```mips
0x800244D0: lhu  $v1, 0x0146($s3)      ; Read loop counter
0x800244D4: ori  $v0, $zero, 0x270F     ; 9999
0x800244D8: bne  $v1, $v0, 0x8002453C  ; If counter != 9999 → post-loop
0x800244DC: nop
0x800244E0: j    0x80024F04            ; If counter == 9999 → EXIT function
0x800244E4: sw   $zero, 0x0158($s3)    ; (delay slot) clear timer
```

- counter != 9999 (normal monsters): falls through to post-loop at 0x8002453C
- counter == 9999 (our sentinel): **exits function entirely** (jumps to 0x80024F04)

### Post-Loop: Timer-Gated Level-Up (0x8002453C - 0x800245C4)

```mips
0x80024560: ori  $s1, $zero, 0x270F    ; $s1 = 9999
0x80024564: lw   $v0, 0x0158($s3)      ; timer
0x8002456C: sltu $v0, $v0, $s1         ; timer < 9999?
0x80024570: bne  $v0, $zero, 0x80024F04 ; YES → exit function (no level-up)
...
0x8002457C: sw   $zero, 0x0158($s3)    ; Reset timer
0x80024580: lhu  $v0, 0x0144($s3)      ; Read level counter
0x80024588: addiu $v0, $v0, 1          ; Increment
0x8002458C: sh   $v0, 0x0144($s3)      ; Store level++
0x80024590: lhu  $v0, 0x0146($s3)      ; Read loop counter
0x80024598: addiu $v0, $v0, 1          ; Increment
0x8002459C: sh   $v0, 0x0146($s3)      ; Store counter++
```

Then the OR-bitmask writes to +0x160 and loops back to 0x800244D0.

### Key Insight: Timer Controls Everything

- entity+0x158 = combat timer (accumulates each dispatch call)
- When timer < 9999: **exit function** (no action selection? or skip level-up only?)
- When timer >= 9999: reset timer, increment +0x144 and +0x146, run OR-bitmask
- entity+0x146 only written HERE (2 sites), never initialized to 0 elsewhere in EXE

### What 0x80024F04 Does

Unknown — this is near the end of the ~2.7KB dispatch function. Could be:
- Function return (= no action this turn)
- Action selection code (= use current bitfield for spell choice)
- Jump to overlay for actual spell execution

**This needs further investigation.** If 0x80024F04 is the return, then sentinel
causes "no spell cast" (monsters still attack physically). The user observing
"same spells" suggests our sentinel either doesn't get written or gets overwritten.

---

## Comprehensive entity+0x160 Write Site Search (2026-02-10)

Searched ENTIRE EXE (SLES_008.45) and BLAZE.ALL overlay region (0x900000-0x9A0000)
for ALL MIPS store instructions (sw/sb/sh) with offset 0x0160-0x0163.

### All Write Sites Found

| # | Location | RAM Address | BLAZE Offset | Instruction | Purpose |
|---|----------|-------------|-------------|-------------|---------|
| 1 | EXE | 0x800244F4 | — | `sw $v0, 0x160($s6)` | **Dispatch OR-loop** (level-up simulation) |
| 2 | Overlay | 0x8005039C | 0x916C44 | `sb $zero, 0x160($s1)` | **Entity init** (zeroes all 4 bytes) |
| 3 | Overlay | 0x800656D0 | 0x92BF78 | `sb $v0, 0x160($s5)` | Combat init (PATCHED — site 2) |
| 4 | Overlay | 0x800C3DF8 | 0x98A6A0 | `sb $v1, 0x160($v0)` | Spawn init (PATCHED — site 1) |

Sites 3 and 4 are our patched sites. Sites 1 and 2 are NEW discoveries.

### Site 1 — EXE Dispatch OR-Loop (0x800244F4)

Inside the combat action dispatch function (0x80024494, ~2.7KB). This is a
**read-modify-write OR operation** in a loop:

```mips
0x800244E8: lw   $v0, 0x160($s6)     ; load current bitfield
0x800244F0: or   $v0, $s4, $v0       ; OR in new spell bit ($s4)
0x800244F4: sw   $v0, 0x160($s6)     ; store accumulated bitfield
```

Loop structure:
- Sentinel: entity+0x146 compared to 0x270F (9999 decimal)
- Each iteration ORs one spell bit ($s4) into the bitfield
- Loop back at 0x80024534 → jumps to 0x800244D0
- This IS the "level-up simulation" — builds spell availability by accumulating bits

**Key insight**: This loop does NOT overwrite — it ADDS bits via OR. So any bits
set by our combat init patch would be PRESERVED, and additional bits ORed on top.
Our per-monster bitfield should survive this loop.

### Site 2 — Entity Init Zeroing (BLAZE 0x916C44, RAM 0x8005039C)

Part of an entity initialization function that clears the entire bitfield:

```mips
0x8005039C: sb $zero, 0x160($s1)   ; byte 0 = 0
0x800503A0: sb $zero, 0x161($s1)   ; byte 1 = 0
0x800503A4: sb $zero, 0x162($s1)   ; byte 2 = 0
0x800503A8: sb $zero, 0x163($s1)   ; byte 3 = 0
```

Also zeroes entity+0x15E, +0x15F, +0x165, +0x166, +0x167.
Contains a table lookup at 0x80057A34+(val&7) stored to entity+0x15D.
Followed by a loop zeroing 10 entries at stride -640 bytes (entity substructure).

**Execution order unknown** — if this runs AFTER our combat init patch,
it would erase our per-monster bitfields before the dispatch OR-loop rebuilds
from scratch, producing vanilla behavior.

### Three Post-Combat-Init Functions — ALL RULED OUT

These are called immediately after our combat init patch site (at 0x0092BFA8+):

| Function | SLES offset | Purpose | Writes +0x160? |
|----------|------------|---------|----------------|
| 0x80023A10 | 0x14210 | Copies entity+0x280→0x120 (4 words) | **NO** |
| 0x80024024 | 0x14824 | Scales 8 stat halfwords by reduction factor | **NO** |
| 0x80023C2C | 0x1442C | Computes derived stats (ATK/DEF) from +0x120 | **NO** |
| 0x80023E7C | 0x1467C | Aggregates equipment/buff bonuses | **NO** |

None of these 4 functions contain ANY store to offset 0x160-0x167.
None call subroutines (no jal instructions). All are pure stat computation.

### Execution Flow (Hypothesized)

```
Entity creation:
  1. Entity init (0x916C44) zeroes entity+0x160 (all spells disabled)

Combat start:
  2. Combat init (0x0092BF74, OUR PATCH) sets per-monster bitfield
  3. Stat functions run (0x80023A10, 0x80024024, 0x80023C2C, 0x80023E7C)
  4. Dispatch OR-loop (0x800244F4) accumulates bits on top via OR

During combat:
  5. Dispatch function reads accumulated bitfield for spell selection
```

If this order is correct, our patch SHOULD work (OR only adds bits).
But in-game test shows no effect. Two hypotheses remain:

### Hypothesis A: Wrong Identity Offset

Our code reads entity+0x10 as the identity byte. If this offset is wrong
(e.g., should be +0x12, or the field is always 0 at execution time),
ALL monsters would index table[0] = default = 0x00000001 (vanilla FireBullet).
This would make the patch completely invisible — identical to vanilla.

Evidence for:
- Config note: "If monsters behave wrong, try 0x12 instead."
- stat_b is at +0x12 in 96-byte stat entry; entity struct mapping uncertain
- If entity+0x10 is always 0, table[0]=default=0x00000001 for ALL monsters

Evidence against:
- MEMORY says entity struct +0x10 = stat_b (but this needs verification)

### Hypothesis B: Entity Init Runs AFTER Combat Init

If the zeroing at 0x916C44 (RAM 0x8005039C) runs AFTER our combat init
at 0x0092BF74, it would erase our values. Then the dispatch OR-loop
rebuilds from scratch → vanilla behavior.

Evidence for:
- Would perfectly explain "same spells" observation
- Entity init is at lower RAM address (different function, unknown call order)

Evidence against:
- Entity init typically runs once at creation, not every combat
- Combat init is explicitly in the "battle start" code path

### Next Steps

1. **Try identity_offset = 0x12** (quick config change, rebuild, test)
2. **Add debug output**: Write a known constant (e.g., 0xDEADBEEF) to entity+0x160
   at combat init and check via savestate if the value persists into combat
3. **Trace call order**: Find what calls the entity init (0x916C44) function
   and the combat init (0x0092BF74) function to determine execution sequence

## Non-functional Patchers (kept for reference)
- `patch_monster_spells.py` (EXE at 0x8002BE38 = CD-ROM DMA code, NOT spells)
- `patch_spell_table.py` (spell SET table = player system only)

## Investigation Scripts
- `WIP/spells/analyze_combat_savestates.py` - Comprehensive savestate analyzer (10 sections)
- `WIP/spells/decode_spell_entries.py` - Focused spell entry decoder + overlay disassembler
- `WIP/spells/disasm_overlay_init.py` - Overlay init disassembly for per-monster spell work
- Savestates: `C:\Perso\BabLangue\other\ePSXe2018\sstates\combat\`
