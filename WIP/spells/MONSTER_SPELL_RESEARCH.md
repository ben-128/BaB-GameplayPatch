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

## Non-functional Patchers (kept for reference)
- `patch_monster_spells.py` (EXE at 0x8002BE38 = CD-ROM DMA code, NOT spells)
- `patch_spell_table.py` (spell SET table = player system only)

## Investigation Scripts
- `WIP/spells/analyze_combat_savestates.py` - Comprehensive savestate analyzer (10 sections)
- `WIP/spells/decode_spell_entries.py` - Focused spell entry decoder + overlay disassembler
- Savestates: `C:\Perso\BabLangue\other\ePSXe2018\sstates\combat\`
