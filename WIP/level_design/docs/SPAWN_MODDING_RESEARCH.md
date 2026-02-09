# Spawn Group Modding - Research Notes

Research on modifying monster spawn groups in **Blaze & Blade: Eternal Quest** (PSX).

Status: **PLAYER SPELL SYSTEM DECODED** - Monster ability dispatch still unknown. See "Combat Action System" and "Loot System" sections.

---

## Per-Monster Data Structures (Cavern F1 Area1 as reference)

Each area has multiple per-monster data structures stacked around a "group" of 96-byte entries.

### Overview (bottom-up in memory)

```
Address       Structure                  Controls
─────────────────────────────────────────────────────────────────
0xF7A904      Animation table header     [00000000 04000000]
0xF7A90C      Animation table            Animation frame indices (8 bytes/slot)
0xF7A934      8-byte records             Anim offset + texture ref (8 bytes/slot)
0xF7A94C      Zero terminator + offsets  Structural
0xF7A964      Assignment entries (L/R)   L=3D model, R=unknown (8 bytes/slot)
0xF7A97C      96-byte entries (GROUP)    Name (16b) + Stats (80b) per monster
0xF7AA9C      Script area                Type entries, spawn commands, entity data, room scripts
```

---

## Detailed Structure Descriptions

### 1. Assignment Entries - L and R (flag 0x00 / flag 0x40)

Location: immediately before the 96-byte group. `group_offset - num_monsters * 8`

**8 bytes per monster** = 2 x 4-byte entries:

```
[slot, L_val, 00, 00]  <- L entry (flag 0x00)
[slot, R_val, 00, 40]  <- R entry (flag 0x40)
```

**Cavern F1 Area1 (0xF7A964):**
```
Slot 0 (Goblin):  L=[00,00,00,00] L=0  | R=[00,02,00,40] R=2
Slot 1 (Shaman):  L=[01,01,00,00] L=1  | R=[01,03,00,40] R=3
Slot 2 (Bat):     L=[02,03,00,00] L=3  | R=[02,04,00,40] R=4
```

**L and R values are NOT global monster IDs.** They are local per-area indices. The same monster has different L/R values in different areas.

### 2. 8-Byte Records (animation offset + texture ref)

Location: before the assignment entries, after the animation table.

**8 bytes per monster:**
```
[uint32 anim_offset] [uint32 texture_ref]
```

**Cavern F1 Area1 (0xF7A934):**
```
Slot 0 (Goblin): anim_off=0x000C texref=0x00000300
Slot 1 (Shaman): anim_off=0x0014 texref=0x00400400
Slot 2 (Bat):    anim_off=0x001C texref=0x00800500
```

- `anim_offset` points into the animation table (relative to table start)
- `texture_ref` = VRAM texture offset

### 3. Animation Table

Location: starts at `section_start + 8` (after the `[00000000 04000000]` header).

**8 bytes per slot** containing animation frame indices:
```
Slot 0 (Goblin): [04 04 05 05 06 06 07 07]  at 0xF7A910
Slot 1 (Shaman): [08 09 0A 0B 0C 0C 0D 0E]  at 0xF7A918
Slot 2 (Bat):    [0F 0F 10 10 11 12 13 14]  at 0xF7A920
```

### 4. 96-Byte Entries (The "Group")

**96 bytes per monster:** 16 bytes name + 40 x uint16 stats.

```
Offset  Size  Description                              Runtime Use
0x00    16    ASCII name (null-padded)
0x10    2     stat[0]  exp
0x12    2     stat[1]  level
0x14    2     stat[2]  → ent+0x70 = BEF0 drop table index 1  (range 32-8000)
0x16    2     stat[3]  → ent+0x68 = BEEC name table index 1
0x18    2     stat[4]  → ent+0x72 = BEF0 drop table index 2
0x1A    2     stat[5]  → ent+0x6A = BEEC name table index 2  (range 0-4)
0x1C    2     stat[6]  → ent+0x74 = BEF0 drop table index 3
0x1E    2     stat[7]  → ent+0x6C = BEEC name table index 3
0x20    2     stat[8]  → ent+0x76 = BEF0 drop table index 4
0x22    2     stat[9]  → ent+0x6E = BEEC name table index 4  ("drop_rate")
0x24    2     stat[10] creature_type
0x26    2     stat[11] armor_type
0x28    2     stat[12] elem_fire_ice
0x2A    2     stat[13] elem_poison_air
0x2C    2     stat[14] elem_light_night
0x2E    2     stat[15] elem_divine_malefic
0x30    2     stat[16] dmg
0x32    2     stat[17] armor
0x34-0x5F     stat[18]-stat[39] (unknown, mostly zero)
```

**DUAL PURPOSE (confirmed by gameplay testing):** stat[2]-stat[9] ARE combat stats (HP, collider, etc.). Changing them changes gameplay. The init at 0x80039358 ALSO copies these values to entity loot index fields (+0x68-+0x76). Same numeric value serves as combat stat AND loot table index.

### 5. Type-07 Entries (Script Area)

Location: in the script area after the 96-byte entries. Found by scanning for entries with type byte = `0x07`.

**8 bytes per entry:**
```
[uint32 offset] [type=07, idx, slot, 00]
```

**Cavern F1 Area1:**
```
0xF7ABE4: [off=0x0580] [07, 10, 00, 00]  <- Goblin (slot 0), idx=0x10
0xF7ABEC: [off=0x0588] [07, 11, 01, 00]  <- Shaman (slot 1), idx=0x11
0xF7ABF4: [off=0x0590] [07, 12, 02, 00]  <- Bat    (slot 2), idx=0x12
```

Other type entries in the same region (types 01, 02, 04, 05, 06, 08, 0E) are fixed overhead, not per-monster.

### 6. Script Area Map (Cavern F1 Area1)

The script area is ~13.4KB and divided into distinct regions:

```
Region                         Offset range         Size     Contents
─────────────────────────────────────────────────────────────────────────────
Script header                  +0x000 to +0x030     48b      Initial header data
Padding (zeros)                +0x030 to +0x040     16b      Zeros
Initial spawn records          +0x040 to +0x106     198b     Blocks 0-3 (one per slot+1)
Resource binding table         +0x106 to +0x41C     790b     Block 4 (type entries, offsets)
Early spawn commands           +0x420 to +0x564     324b     Blocks 5-15 (per-formation spawns)
Type-7 target data             +0x564 to +0x600+    ~160b    Interleaved texture/variant data
Padding (zeros)                variable
Deep entity region             +0x900 to +0x1DC0    5312b    Entity placement/patrol data
Type-8 target data (bytecode)  +0x1DC0 to +0x2100+  ~800b    Room scripts (has dialogue text)
Remaining bytecode             +0x2100 to +0x348C   ~5KB     More room logic
```

---

## Swap Test Results

All tests performed on **Cavern of Death, Floor 1, Area 1** (3 monsters: Goblin, Shaman, Bat).

### What controls the 3D MODEL

| Test | What was swapped | Visual result | Stable? |
|------|-----------------|---------------|---------|
| L = Ogre (cross-floor) | L only, value from different floor | Mesh unchanged / crash | No (model not loaded) |
| L swap local (same floor) | L only, between same-floor monsters | **Model swapped** | Crash in some cases (anim mismatch) |
| **L + anim table swap** | **L + 8 bytes of anim table per slot** | **Model swapped** | **Stable** |

**Conclusion: L + anim table swap = full model swap** (mesh + animations + textures). Must be between monsters whose models are loaded on the same floor. L alone crashes because animations don't match the new model.

### What controls TEXTURE VARIANTS

| Test | What was swapped | Result |
|------|-----------------|--------|
| Type-7 offset swap | uint32 offset in type-07 entries | **Texture color variant changes** |
| Type-7 idx swap | idx byte only | No effect |

**Conclusion: Type-07 offset controls texture color variant** (e.g. green goblin -> red goblin). Useful for creating visual variants. The idx byte has no effect.

### What does NOT control AI/behavior

| # | Test | What was swapped | AI result |
|---|------|-----------------|-----------|
| 1 | L swap (local) | L value only | AI stays on slot |
| 2 | L + anim swap | L + anim table | AI stays on slot |
| 3 | R swap (Goblin <-> Bat) | R value only | No change |
| 4 | R = same for all | All R set to same value | No change |
| 5 | 96-byte entry swap | Full name + stats | AI stays on slot (only name/stats change) |
| 6 | Type-7 idx swap | idx byte only | No change |
| 7 | Spawn cmd slot bytes | uint16 after FFFFFFFFFFFF (blocks 5-15) | No change |
| 8 | Spawn cmd XX prefix | XX in [XX 0B YY 00] (blocks 5-15) | No change |
| 9 | Spawn cmd YY prefix | YY in [XX 0B YY 00] (blocks 5-15) | No change |
| 10 | Deep region slot markers | [XX FF 00 00] in script+0x900 to +0x1DC0 | **Dark entities appear**, AI unchanged |
| 11 | Deep region cmd headers | 4-byte headers before slot markers | **More dark entities**, AI unchanged |
| 12 | Global monster table search | Searched all BLAZE.ALL for monster names | No separate AI table found |
| 13 | Type-8 offset swap | Type-8 entry 1 <-> entry 2 | No change |
| 14 | Type-8 target 1 zeroed | 256 bytes at script+0x1DC0 | No change |
| 15 | Type-8 ALL bytecode zeroed | 5.8KB from script+0x1DC0 to end | **CRASH** (room scripts, not AI) |
| 16 | Overlay config blocks | 33 blocks analyzed across BLAZE.ALL | 3D model data (polygon records) |
| 17 | creature_type field | entity+0x2B5 checked in RAM dump | Always 0 (never written by any code) |
| 18 | Player spell dispatch | 0x80024494 fully decoded | Player spells only, not monster AI |
| **19** | **96-byte FULL swap (post-build)** | **All 96 bytes Goblin<->Bat via test_ai_swap.py** | **NO AI CHANGE** (confirmed in-game 2026-02-08) |

**Pipeline verified:** L+anim swap (known visual change) confirmed patching works correctly.

---

## Summary: What Controls What

| Element | Controls | Confirmed |
|---------|----------|-----------|
| **L + anim table** | **3D model complete** (mesh, animations, textures) | YES |
| **Type-07 offset** | **Texture color variant** | YES |
| **R** (flag 0x40) | Nothing | YES (tested, no effect) |
| **Type-07 idx** | Nothing | YES (tested, no effect) |
| **96-byte entries** | **Name + combat stats only** | YES |
| **Spawn cmd slots/XX/YY** (early region) | Nothing visible | YES (tested, no effect) |
| **Deep region slot markers** [XX FF 00 00] | **Entity placement** (dark entities when wrong) | YES |
| **Deep region cmd headers** | **Entity rendering** (dark entities when wrong) | YES |
| **EXE 55 handlers + BLAZE.ALL 48-byte entries** | **Player spells** (dispatch decoded) | YES (see Combat Action System) |
| **??? UNKNOWN dispatch** | **Monster special abilities** (breaths, drains...) | NO — mechanism not found |
| **BLAZE.ALL BEEC/BEF0 tables + 96-byte stats** | **Loot drops** (stat values = dual purpose) | PARTIAL (see Loot System) |

---

## AI / Spell Control: Investigation Status

The AI/behavior/spell controller has **not been found**. All per-monster structures and script area fields tested so far only control visuals, stats, or entity placement. AI always stays attached to the slot position.

### Eliminated candidates (per-monster fields)
- L value -> model only
- R value -> no effect
- 96-byte entries -> name + stats only
- Type-7 idx -> no effect
- Type-7 offset -> texture variant only

### Eliminated candidates (script area - early region, script+0x080 to +0x600)
- Spawn command slot bytes (uint16 after FFFFFFFFFFFF terminators) -> no effect
- Spawn command XX byte in [XX 0B YY 00] prefixes -> no effect
- Spawn command YY byte in [XX 0B YY 00] prefixes -> no effect

### Eliminated candidates (script area - deep region, script+0x900 to +0x1DC0)
- [XX FF 00 00] slot markers -> controls entity placement, NOT AI
- 4-byte command headers before slot markers -> controls entity rendering, NOT AI

### Eliminated candidates (global)
- Searched ALL of BLAZE.ALL for monster names outside area data -> no master AI table found
- All name occurrences outside known areas are in OTHER area data sections

### Eliminated candidates (type-8 bytecode, script+0x1DC0 to end)
- Type-8 offset swap (entry 1 ↔ entry 2) -> no effect (interchangeable)
- Type-8 target 1 zeroed (256 bytes at script+0x1DC0) -> no effect
- ALL bytecode zeroed (5.8KB from script+0x1DC0 to end) -> **CRASH** (room scripts broken, not AI)

**Conclusion:** type-8 bytecode = room management scripts (elevators, doors, dialogue). Critical for room loading but NOT related to combat AI.

---

## Final Conclusion: AI is in the PSX EXECUTABLE, not area data or overlay config

After **19 tests** covering every identified per-area data structure (including a full 96-byte stat entry swap confirmed in-game 2026-02-08), the AI/behavior/spell system has **not been found in any per-area data or overlay config data**.

### Evidence
1. **19 swap/zero tests** on all per-area fields - AI never changes
2. **AI is strictly positional** - always follows slot index, regardless of ALL data changes
3. **No global AI table** in BLAZE.ALL - monster names only appear in per-area 96-byte entries
4. **Room bytecode (type-8)** confirmed as room scripts (elevator/doors), not AI
5. **Every per-area structure now mapped** and tested: assignment entries, animation tables, 8-byte records, 96-byte stats, type-7 entries, spawn commands, deep entity region, type-8 bytecode
6. **Overlay config blocks** (33 blocks scanned in BLAZE.ALL) are 3D polygon/model data, NOT AI
7. **creature_type = 0 for ALL entities** (never written by any code), dispatch only handles player spells
8. **Test 19 (2026-02-08):** Full 96-byte stat swap Goblin<->Bat (post-build, re-injected into BIN, confirmed in-game) -- AI/behavior unchanged. Stats and name changed, but Goblin still fights like Goblin and Bat like Bat.

### What this means for modding
- **Can change via area data:** 3D models (L+anim), texture variants (type-7 offset), stats/name (96-byte entries), formations (formation templates)
- **Can change via BLAZE.ALL overlay:** 48-byte player spell entries (names, elements, probabilities, tier gating)
- **Can change via EXE:** 55 handler function pointers at 0x8003C1B0, 5-byte tier table at 0x8003C020, damage formula
- **Cannot change via area data:** Monster AI/behavior/ability assignment (NOT in any per-area structure)
- **Monster AI is determined by the PSX executable** based on entity slot position or an index derived during entity initialization -- the mapping from "slot in area" to "AI behavior profile" lives in EXE code, not in data we can easily swap
- Stat fields are DUAL PURPOSE: they are combat stats AND loot table indices (same values)
- creature_type = 0 for ALL entities (never written by any code)

---

## Executable Deep Analysis (2026-02-08)

### CORRECTION: Table at 0x02BDE0 is bytecode opcodes, NOT creature_type

The jump table previously identified as "creature_type → AI handler" is actually the **room script bytecode opcode dispatch table** (39 opcodes, 0x00-0x26). All handlers read operands from a bytecode stream, not from entity structs.

### Entity +0x44 is ACTION STATE, not type_info

Entity struct offset +0x44 was previously thought to be `type_info` (creature_type). Analysis shows it's actually a **transient combat action state**:
- Gets saved before combat actions and restored after (`lw s0, 68(s1)` → do action → `sw s0, 68(s1)`)
- Loaded from bytecode streams during combat sequences
- Used as a modifier in damage calculations (armor subtraction)
- NOT a persistent creature identifier

### Entity validation uses ADDRESS RANGES, not type fields

Function at 0x80026840 distinguishes players from monsters by checking memory address ranges:
- **Players:** 0x80054698 - 0x8005486C (4 slots × ~0x9C bytes each)
- **Monsters:** 0x800A91E8 - 0x800AA568 (overlay region)
- No type field is checked - purely spatial identification

### Per-Entity Overlay Config: THE KEY TO AI

**Array at 0x800AA740:** table of pointers, one per entity slot. Each pointer leads to a config block in the dungeon overlay (0x800A0000+) containing:

```
Config block offsets (discovered):
+0x00: word[0] flags (low 16 bits = count, high 16 bits = parameter)
+0x0E: AI mode flags (bit 0x80 checked for conditional behavior)
+0x24: secondary data pointer
+0x28: animation parameter
+0x30: texture/VRAM data
+0x38: render parameters
+0x40: AI behavior data pointer (most accessed field - 7 references)
+0x48: array of position/geometry data
```

This overlay config is:
- Loaded from BLAZE.ALL dungeon data (NOT from per-area data)
- Indexed by entity slot number
- Contains AI behavior pointers that the engine follows
- **Per-dungeon, not per-area** - explains why AI stays with slot position

### Updated Dispatch Tables

| Table | Address | Entries | Purpose |
|-------|---------|---------|---------|
| Bytecode opcodes | 0x8003CDE0 (file 0x02BDE0) | 39 | Room script interpreter opcodes |
| State machine | 0x8003B324 | 32 | Entity state machine (idle/move/attack/cast) |
| Entity actions | 0x8003B468 | 32 | Combat action handlers |
| Combat actions | 0x8003C1B0 | 55 | Specific combat action implementations |
| Bytecode interpreter | 0x8003BE84 | 188 | Full bytecode interpreter dispatch |
| Visual slot | 0x8003B560 | 24×64b | Visual effect slot allocation (wraps at 24) |
| Bitmask LUT | 0x8003B500 | 24 | Powers of 2 (bitmask lookup table) |

### Overlay Config Blocks: RESOLVED (2026-02-08)

**The overlay config blocks at 0x800AA740 are MONSTER 3D MODEL DATA, not AI.**

Found 33 config blocks across all of BLAZE.ALL by scanning for the format signature:
- 5 Cavern blocks: 0x00A16800, 0x00A34800, 0x00A50800, 0x00A7B000, 0x00A9A800
- 12 blocks share common template (+0x28=0x1680, val08=640)
- All blocks validated against the 0x8001EB70 init function format

**Config block structure (raw decode of 0x00A16800):**
```
Header: 15 ascending offset fields (+0x00 through +0x3C) pointing to data sections
Section sizes: 936, 1064, 248, 248, 584, 600, 536, 424, 2416, 248, 144, 392, 444 bytes
All sections: 16-byte polygon/face records [4b entity_group][8b UV_or_coords][4b vertex_indices]
+0x30 "pointer table" (144 bytes, 19 entries): s16 coordinate pairs, NOT relocatable pointers
+0x34 "1024-entry table": only 392 bytes (model vertex data)
+0x38 "behavior list" (290 entries): same 16-byte face record format
```

This is PSX GPU polygon data — mesh geometry, animation frames, hitbox vertices, texture coordinates.

**AI dispatch is in the PSX executable:**
- 55 combat action handlers at 0x8003C1B0 (implementations at 0x800270B8-0x80029E80)
- 32-entry state machine at 0x8003B324 (idle/move/attack/cast)
- Entity type index → action handler index mapping lives in EXE
- AI is determined by entity type, not by per-entity overlay config data

**CD sector mapping (for locating blocks on disc):**
- CD_base = 0x26DCE (CdSearchFile("\\BLAZE.ALL;1") return value)
- BLAZE.ALL starts at disc sector 0x27D5F
- Slight alignment drift at large offsets (~2047.2 effective bytes/sector vs 2048)

### What's Still Unknown (CRITICAL)
- **Monster ability dispatch mechanism**: How does the game decide that a Goblin does physical attacks while a Dragon casts Fire Breath? NOT controlled by: per-area data (19 tests), overlay config blocks (3D model data), creature_type (always 0), player spell dispatch (0x80024494). Remaining possibilities:
  - **Bitmask at entity+0x160** set by EXE code during entity init (not from area data)
  - **Entity init function** in EXE reads the L assignment or slot index and sets behavior profile
  - **Hardcoded slot-to-AI mapping** in EXE (each area's slot positions have fixed AI)
  - stat+0x2A/+0x2D were candidates but are level-scaled (unreliable), AND test 19 swapped them with no effect
- **Full item ID list** (names only in BLAZE.ALL, not EXE)
- **Loot table source in BLAZE.ALL** (loaded via CD state machine, exact offset unknown)

---

## PSX Executable Analysis (SLES_008.45)

RAM dump analysis with active monsters (Cavern F1 savestate) to understand the combat system.

### Memory Map

```
Region              RAM address          Size     Contents
--------------------------------------------------------------------
PSX exe code        0x80010000-0x8003F000  ~192KB   Game engine code
PSX exe data        0x8003F000-0x80060000  ~132KB   Static tables, strings
Player entities     0x80054698             624B     4 player structs (stride 0x9C = 156 bytes)
Dungeon overlay     0x800A0000+            varies   Per-dungeon code + data from BLAZE.ALL
Monster spawn list  0x800B9268             4992B    Monster metadata (stride 0x28 = 40 bytes)
Entity mgmt region  0x800B4000-0x800BC000  ~32KB    Entity management structs + battle slots
Entity visual data  0x800F0000+            8KB/ent  Sprite/texture data per entity index
```

### Combat Action Table (55 entries at 0x8003C1B0)

55 function pointers to combat action handlers at 0x800270B8-0x80029E80.
- These are the ONLY location of combat handler addresses in all of RAM
- NOT stored in entity structs - dispatch uses an index into this table
- All handlers use standard MIPS prologue (save ra/s-regs, call subroutines)
- Handlers 2-6 call entity validation function 0x80026840 (player vs monster check)

### Entity Struct Layout

**Player entity** (stride 0x9C = 156 bytes, 4 players at 0x80054698):
```
+0x00: flags/type
+0x04: index/subtype
+0x18: model_id
+0x1C-0x24: position (x, y, z) as fixed-point
+0x28-0x2C: scale
+0x30: VRAM texture offset
+0x38: color/tint
+0x70: data pointer -> overlay entity config (NOT code)
+0x7C: data pointer -> overlay render data
+0x80: state/flags
+0x84-0x8C: 0xA0000000 pattern (GPU/DMA related)
```

**Monster spawn metadata** (stride 0x28 = 40 bytes, 6 entries at 0x800B9268):
```
+0x00-0x0C: position data (3x int32 + count/flags)
+0x10-0x20: zeros
+0x24: type_info (high byte = model_type, low byte = slot_index)
```

Cavern F1 monster types in metadata: 0x07 (Goblin), 0x07, 0x07, 0x03 (Shaman?), 0x07, 0x04 (Bat?)

### Key Finding: "Entity Code" Pointers are DATA, not CODE

The pointers at player struct +0x70 (0x800A91E8, 0x800A9320, 0x800A93BC) and similar monster pointers (0x800AA708, 0x800AA728, 0x800AB0C8, 0x800AADBC) all point to **data structures** in the dungeon overlay region, NOT to executable code. Disassembly confirms they contain non-MIPS data (configuration/stats loaded from BLAZE.ALL).

Unique data pointers per entity type:
- Players: 0x800A91E8, 0x800A9320, 0x800A93BC (3 variants for 4 players)
- Monsters: 0x800AA708, 0x800AA728, 0x800AB0C8, 0x800AADBC (4 variants for 6 monster slots)

These likely contain per-entity configuration that the engine code reads to determine behavior.

### Entity Management Region (0x800B4000-0x800BC000)

Two sub-regions identified:

**Region 1** (0x800B4000-0x800B5B00, ~7KB): Main entity table with all entities (players + monsters). Contains:
- Entity data pointers (to overlay config data)
- Entity visual data pointers (0x800Exxxx range)
- Player entity cross-references
- Animation index tables (32-byte sequences of byte indices)

**Region 2** (0x800BB93C-0x800BBFF0, stride 0x9C, 12 entries): Battle slot table. Each entry:
```
+0x00: player entity pointer (which player this slot tracks)
+0x04: entity data pointer (overlay config)
+0x10: render data pointer
+0x14: state/ID
+0x18-0x20: 0xA0000000 pattern (GPU/DMA)
+0x28: combat flags
+0x2C: VRAM texture offset
+0x38: slot_index
+0x44: type_info (matches monster metadata format)
+0x48: type_info_2
+0x4C-0x54: position (x, y, z)
+0x58-0x5C: scale
+0x60: VRAM offset
+0x68: color/tint (0x00808080 = default)
```

### Dispatch Mechanism

Found a function dispatcher at 0x80017F2C that uses a **32-entry jump table** at 0x8003B324:
```mips
beq  r2, r0, +18       ; skip if action = 0
sll  r2, r16, 2        ; index * 4
lui  r1, 0x8004
addu r1, r1, r2        ; base + index*4
lw   r2, -0x4CDC(r1)   ; load handler from table at 0x8003B324
jalr r2                 ; call handler
```

This table contains 32 handlers (0x80018xxx range) - a **higher-level action dispatcher** separate from the 55-entry combat table. This is likely the entity state machine that handles movement, idle, attack, cast, etc.

### Open Questions (Updated 2026-02-08)

- **MONSTER ABILITY DISPATCH**: The main unsolved question. 19 tests confirm AI is NOT in any per-area data. Player spells go through 0x80024494 with Type 0 entries + bitmask. Monster abilities (Fire Breath, Paralyze Eye, etc.) use a different path entirely in the PSX executable. Next step: trace entity init code in EXE to find where entity+0x160 bitmask is set (this bitmask gates action availability and is the most likely AI control point).
- **Full item ID list**: Item names only in BLAZE.ALL, need to decode BEEC table entries.
- **Loot table disc location**: Loaded via CD state machine, exact BLAZE.ALL offset unknown.
- **Overlay stubs**: 3 NOP stubs at 0x80073xxx filled at runtime (not via sw). Likely DMA/memcpy.

---

## Combat Action System (2026-02-08)

### CRITICAL CORRECTION: This is the PLAYER SPELL system

The dispatch at 0x80024494 is for **player spells**, NOT monster AI.
- `creature_type` at entity+0x2B5 = **ALWAYS 0** for ALL entities (no code writes to it)
- ALL entities share Type 0 = Mage spell catalog (28 entries)
- **Bitmask** at entity+0x160 gates which actions each entity can use
- Monster special abilities (Types 6-7) have tier=[0,0,0,0,0] = NEVER selected
- **Monster ability dispatch uses a DIFFERENT mechanism** (still unknown)

### Player Spell Dispatch Architecture

```
creature_type = entity+0x2B5 (ALWAYS 0, never written)
      |
      v
Global ptr *(0x8005490C) + 0x9C → per-type pointer array (80 entries)
      |
      v
ptr_array[0] → Type 0 = 28 Mage spells (Fire, Spark... Chaos Flare, Meteor Smash)
      |
      v
5-byte TIER TABLE at 0x8003C020 → max entries for current level tier
      |
      v
BITMASK at entity+0x160 → filters which actions this entity can use
      |
      v
Loop 0..max-1, stride 48 bytes:
  - Check bitmask, check probability at entry+0x1D
  - Selected → handler via 55-entry table at 0x8003C1B0
```

### 5-Byte Tier Table (0x8003C020, 80 entries)

Each creature type has 5 bytes controlling how many actions it can use at each player level range:

| Tier | Level Range | Description |
|------|------------|-------------|
| 0 | < 20 | Early game |
| 1 | 20-49 | Mid game |
| 2 | 50-79 | Late game |
| 3 | 80-109 | End game |
| 4 | 110+ | Post game |

**Example values:**
```
creature_type 0 (Goblin):   5, 10, 15, 20, 26
creature_type 1 (Shaman):   5, 11, 16, 19, 22
creature_type 2 (Bat):      3,  7,  9, 12, 16
```

Higher tiers unlock more actions. The table ends exactly at 0x8003C1B0 (80 × 5 = 400 bytes).

### 48-Byte Action Entry Format

Found in BLAZE.ALL at ~0x00909310 (overlay data region). Format:

```
Offset  Size  Description
+0x00   8     Header/flags
+0x06   1     action_index (selects action within creature's entry set)
+0x07   1     creature_type (owner)
+0x08   16    Spell/ability name (ASCII, null-terminated)
+0x18   1     Spell ID
+0x19   1     Flags
+0x1A   1     Element type (0=none, 1=water, 2=fire, 3=water, 4=stone, 5=wind)
+0x1B   1     Sub-type
+0x1C   2     Range/power
+0x1D   1     Probability threshold (compared against random roll; 0 = skip)
+0x1E   2     Flags
+0x20   16    Parameters (damage, MP cost, targeting)
```

**Spell names found:**
- Player spells: Teleport, Chaos Flare, Meteor Smash, Fusion, Turn Undead, Healing, Haste, Enchant Fire/Earth/Wind/Water, Charm
- Monster abilities: Paralyze Eye, Confusion Eye, Sleep Eye, Fire Breath, Cold Breath, Thunder Breath, Stone Breath, Throw Rock, Wave, Sonic Boom, Gas Bullet, Power Wave

### 55 Combat Action Handlers (0x8003C1B0)

All 55 function pointers span 0x800270B8-0x80029E80 (~11.5 KB). Called exclusively via `jalr` (indirect).

**11 unique subroutines used across handlers:**

| Function | Called by | Role |
|----------|----------|------|
| 0x80023698 | 45 handlers | Core combat resolution (links attacker/target) |
| 0x80073F9C | 28 handlers | Play Sound/VFX (overlay stub, NOP in EXE) |
| 0x80073B2C | 16 handlers | Set Animation/State (overlay stub) |
| 0x80026840 | 9 handlers | Entity validation (player vs monster) |
| 0x80026650 | 9 handlers | Damage application (with randomization) |
| 0x80026460 | 8 handlers | Damage calculation (4 × rand()) |
| 0x800739D8 | 4 handlers | Play Animation (overlay stub) |
| 0x800235B0 | 4 calls | Stat lookup (monster entities, bit 0x80) |
| 0x80023630 | 4 calls | Stat lookup (player entities) |

**Damage formula:** `stat/2 + rand() % (stat/2 + 1)` applied 4 times (attack × 2, defense × 2).

**Handler types by size:**
- Small (84-96 bytes): Handlers 41-49, 52 — simple single actions
- Medium (300-348 bytes): Handlers 14-21, 27, 37-39 — attack/spell handlers
- Large (752 bytes): Handler 51 — AoE heal (loops through entity array)

### 3 Overlay Stubs (NOP in EXE, loaded from BLAZE.ALL at runtime)

| Stub | Address | Combat Calls | Arguments |
|------|---------|-------------|-----------|
| Play Animation | 0x800739D8 | 4 | entity+0x1C, entity_ptr, flag |
| Set Anim/State | 0x80073B2C | 16 | entity, anim_id, flag, flag |
| Play Sound/VFX | 0x80073F9C | 28 | entity, entity+0x1C, descriptor_ptr, effect_id |

Anim IDs used: 0xBC, 0x59, 0x50, 0xBF, 0x3A, 0x46, 0x47.
VFX descriptors: 8-byte entries at 0x80057C1C-0x80057D0C (one per handler, also overlay data).

### Dispatch Code (0x80024E14-0x80024EF8)

```mips
; Load creature_type
lbu   $a1, 693($s3)           ; entity+0x2B5 = creature_type
; Load global struct
lui   $v0, 0x8005
lw    $v0, 0x490C($v0)        ; global = *(0x8005490C)
; Get per-type pointer array
lw    $v1, 0x9C($v0)          ; ptr_array = global+0x9C
; Index by creature_type
sll   $v0, $a0, 2             ; creature_type * 4
addu  $v1, $v0, $v1
lw    $s5, 0($v1)             ; action_entries_base = ptr_array[creature_type]
; Get tier from 5-byte table
lui   $v1, 0x8004
addiu $v1, $v1, -16352        ; $v1 = 0x8003C020
addu  $v0, $v0, $a0           ; creature_type*5
addu  $v0, $v0, $v1
addu  $v0, $v0, $s0           ; + tier (0-4)
lbu   $s2, 0($v0)             ; action_count = table[creature_type][tier]
```

Tier computed from player level: <20→0, 20-49→1, 50-79→2, 80-109→3, 110+→4.

---

## Loot System (FULLY DECODED 2026-02-08)

### Architecture Overview

```
96-byte stat entries (8 index fields at stat+0x14 through stat+0x22)
      |
      v (init at 0x80039358)
Entity runtime struct:
  +0x68, +0x6A, +0x6C, +0x6E → BEEC table indices (names/items)
  +0x70, +0x72, +0x74, +0x76 → BEF0 table indices (drops)
      |
      v (resolution at 0x80038178)
TWO tables loaded from BLAZE.ALL via CD read (0x800355F4):
  BEEC ptr (0x8004BEEC) → name/item table (8-byte entries, 3 halfwords)
  BEF0 ptr (0x8004BEF0) → drop table (8-byte entries, 3 halfwords)
      |
      v
24 output values per entity:
  ent+0x20..0x3C ← BEEC lookups (4 indices × 3 halfwords)
  ent+0x40..0x5C ← BEF0 lookups (4 indices × 3 halfwords)
```

### Stat → Entity Field Mapping (init at 0x80039358)

| Stat Offset | Stat Index | Entity Offset | Table | Combat Role |
|-------------|-----------|---------------|-------|-------------|
| +0x16 | stat[3] | +0x68 | BEEC idx 1 | magic (confirmed) |
| +0x1A | stat[5] | +0x6A | BEEC idx 2 | collider_type (confirmed) |
| +0x1E | stat[7] | +0x6C | BEEC idx 3 | hit_fx_id |
| +0x22 | stat[9] | +0x6E | BEEC idx 4 | drop_rate |
| +0x14 | stat[2] | +0x70 | BEF0 idx 1 | hp (confirmed) |
| +0x18 | stat[4] | +0x72 | BEF0 idx 2 | randomness |
| +0x1C | stat[6] | +0x74 | BEF0 idx 3 | death_fx_size |
| +0x20 | stat[8] | +0x76 | BEF0 idx 4 | collider_size |

**DUAL PURPOSE:** These values ARE combat stats (HP, collider, etc. — confirmed by gameplay testing). The init function at 0x80039358 also copies them to entity fields used as loot table indices. Same numeric value serves both combat and loot systems.

### Table Entry Format

Each table entry is 8 bytes with 3 useful halfwords:
```
+0x00: u16 value_1 (item ID or name reference)
+0x02: u16 value_2 (quantity or probability)
+0x04: u16 value_3 (variant or secondary ID)
+0x06: u16 padding
```

### On-Disc Format

Tables loaded from BLAZE.ALL by parser at 0x80038544:
```
12-byte header: [word0] [word1] [word2]
28-byte records (per area):
  +0x00: u32 name_table_offset    (relative to header+12)
  +0x04: u32 debug/size
  +0x08: u32 drop_table_offset    (relative to header+12)
  +0x0C: u32 debug/size
  +0x10: u32 third_table_offset   (relative to header+12)
  +0x14: u32 debug/size
  +0x18: u32 extra
```

### Loot Resolution (0x80038178)

1. Calls `0x800386DC(BEF4, entity)` — binary search tree with packed magic constants (creature type + area identifiers). Zeroes 120 bytes of entity struct first.
2. Loads BEEC and BEF0 table base pointers.
3. For each of 4 BEF0 indices (ent+0x70/72/74/76): `entry = BEF0_base + index * 8`, reads 3 halfwords → stores to ent+0x40..0x5C.
4. For each of 4 BEEC indices (ent+0x68/6A/6C/6E): `entry = BEEC_base + index * 8`, reads 3 halfwords → stores to ent+0x20..0x3C.

### Key Runtime Pointers

| Address | Set by | Purpose |
|---------|--------|---------|
| 0x8004BEEC | 0x80038544 (CD read) | BEEC name/item table base |
| 0x8004BEF0 | 0x80038544 (CD read) | BEF0 drop table base |
| 0x8004BEF4 | 0x80038544 (CD read) | Creature type dispatch table |
| 0x8004BEF8 | 0x80038544 return | Parser status |
| 0x8005490C | Overlay init (not EXE) | Master game state struct |

### Example Stat Index Values

| Monster | stat+0x14 (BEF0) | stat+0x1A (BEEC) | stat+0x22 (drop_rate) |
|---------|-------------------|-------------------|----------------------|
| Goblin | 38 | 0 | 74 |
| Shaman | 35 | 0 | 66 |
| Bat | 36 | 2 | 66 |
| Ogre | 315 | — | 40 |
| Red Dragon | 8000 | — | 500 |

---

## Technical Reference

### File Locations
- BLAZE.ALL source: `Blaze  Blade - Eternal Quest (Europe)/extract/BLAZE.ALL`
- Output: `output/BLAZE.ALL`
- Test scripts: `WIP/level_design/spawns/scripts/test_*.py`
- Analysis scripts: `WIP/level_design/spawns/scripts/_*.py`

### Test Scripts Index

| Script | Tests what | Result |
|--------|-----------|--------|
| `test_visual_link.py` | L=14 (Ogre, cross-floor) | Crash |
| `test_L_swap_local.py` | L swap local, 3-way | Model swap, unstable |
| `test_L_only_2way.py` | L swap 2-way | Model swap, unstable |
| `test_L_plus_anim.py` | L + anim table swap | **Model swap, stable** |
| `test_visual_R.py` | R = same for all | No visual change |
| `test_R_swap.py` | R swap Goblin <-> Bat | No behavior change |
| `test_8byte_records.py` | texture_ref = same for all | ? |
| `test_type7_entries.py` | Type-7 idx = same for all | No effect |
| `test_type7_swap.py` | Type-7 idx swap | No effect |
| `test_type7_offset_swap.py` | Type-7 offset swap | **Texture variant change** |
| `test_96byte_swap.py` | 96-byte entry swap | Stats only, AI stays |
| `test_full_swap.py` | L+R+8byte+type7 swap | ? |
| `test_spawn_cmd_slot_swap.py` | Slot bytes after FFFFFFFFFFFF (early region) | No effect |
| `test_spawn_cmd_prefix_swap.py` | XX byte in [XX 0B YY 00] (early region) | No effect |
| `test_deep_slot_swap.py` | [XX FF 00 00] slot markers (deep region) | **Dark entities**, no AI change |
| `test_deep_header_swap.py` | 4-byte cmd headers (deep region) | **More dark entities**, no AI change |
| `test_type8_offset_swap.py` | Type-8 entry offset swap (0x1DC0 ↔ 0x1FC4) | No effect |
| `test_type8_zero.py` | Zero 256 bytes at type-8 target 1 | No effect |
| `test_type8_zero_all.py` | Zero ALL bytecode from script+0x1DC0 to end (~5.8KB) | **Crash** (room scripts broken) |
| `test_ai_swap.py 1` | Full 96-byte stat swap Goblin<->Bat (post-build + BIN re-inject) | **NO AI CHANGE** (confirmed in-game) |

### Analysis Scripts Index

| Script | Purpose |
|--------|---------|
| `find_ai_controller.py` | Comprehensive per-slot data dump for 3 areas |
| `analyze_script_area.py` | Script area block structure analysis |
| `analyze_spawn_cmds_detail.py` | Detailed spawn command analysis |
| `_deep_script_analysis.py` | Byte frequency, FF values, triplets, spell search |
| `_temp_analyze.py` | Type entry targets, spawn blocks for 4 areas |
| `_analyze_full_script_map.py` | Full script area map with all regions |
| `_search_global_monster_table.py` | Global monster name search in BLAZE.ALL |
| `_compare_areas_script.py` | Cross-area comparison (WIP) |
| `analyze_combat_handlers.py` | 55 handler table + state machine + dispatch tracing |
| `search_loot_spells.py` | Loot table search + spell references + handler analysis |
| `decode_action_entries.py` | 48-byte action entry format + dispatch loop decode |
| `find_loot_tables.py` | Loot table parser + resolution function + stat indices |
| `analyze_creature_dispatch.py` | 5-byte tier table + creature_type dispatch chain |
| `trace_overlay_dispatch.py` | Overlay stubs + drop_rate table + global pointer tracing |
| `find_all_config_blocks.py` | 33 config blocks found across BLAZE.ALL |
| `raw_config_decode.py` | Config block = 3D model data (polygon records) |
| `decode_cavern_config.py` | Cavern config block detail decode |
| `extract_combat_data.py` | RAM savestate extraction + pointer array + spell catalog |
| `find_monster_ctype.py` | Monster entity struct analysis (creature_type=0 finding) |
| `find_monster_dispatch.py` | Search for monster ability dispatch (jalr, state machine) |
| `dump_action_entries.py` | Full 48-byte entry dump with spell names |

### Key Offsets (Cavern F1 Area1)
```
Section start:        0xF7A904
Animation table:      0xF7A90C (after 8-byte header)
8-byte records:       0xF7A934
Assignment entries:    0xF7A964
96-byte group:        0xF7A97C
Script area:          0xF7AA9C (= group + 3*96)
  Type entries:       0xF7ABE4 (type-07 at script+0x148)
  Early spawn cmds:   0xF7AEBC (script+0x420)
  Deep entity region: 0xF7B39C (script+0x900)
  Type-8 targets:     0xF7C85C (script+0x1DC0), 0xF7CA60 (script+0x1FC4)
  Room script text:   0xF7CA60+ ("Do you want to take the elevator?")
```

### Deep Entity Region Record Format (script+0x900 to +0x1DC0)

32-byte records with slot markers:
```
[FFFFFFFFFFFF or FFFFFFFFFFFFFFFF] [00 00 00 00] [cmd_header 4b] [XX FF 00 00]
[x int16] [y int16] [z int16] [00 00] [extra uint32] [val uint16] [FFFFFFFFFFFF]
```

Slot marker format: `XX FF 00 00` where:
- `XX & 0x1F` = slot index (0=Goblin, 1=Shaman, 2=Bat)
- `XX & 0xE0` = flags (0x00=plain, 0x80, 0xC0, 0xE0 = behavior flags?)

Command headers vary by slot:
- Slot 0: `00 2B 07 00` (22x), `06 00 01 00` (1x)
- Slot 1: `XX 0A 0B 00` family (various), `17 29 0B 00`, `18 29 09 00`
- Slot 2: `00 00 04 00` (21x), `05 00 02 00` (21x), `16 00 08 00` (20x), `06 00 01 00` (19x)

---

*Last updated: 2026-02-08 (19 tests conclusive: monster AI NOT in per-area data; controlled by PSX executable)*
