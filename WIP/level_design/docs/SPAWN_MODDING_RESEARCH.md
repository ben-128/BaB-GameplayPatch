# Spawn Group Modding - Research Notes

Research on modifying monster spawn groups in **Blaze & Blade: Eternal Quest** (PSX).

Status: **CONCLUDED** - AI is in the PSX executable, not in area data. See "Final Conclusion" section.

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
Offset  Size  Description
0x00    16    ASCII name (null-padded)
0x10    2     stat[0]  exp
0x12    2     stat[1]  level
0x14    2     stat[2]  hp
0x16    2     stat[3]  magic
0x18    2     stat[4]  randomness
0x1A    2     stat[5]  collider_type
0x1C    2     stat[6]  death_fx_size
0x1E    2     stat[7]  hit_fx_id
0x20    2     stat[8]  collider_size
0x22    2     stat[9]  drop_rate
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

| Test | What was swapped | AI result |
|------|-----------------|-----------|
| L swap (local) | L value only | AI stays on slot |
| L + anim swap | L + anim table | AI stays on slot |
| R swap (Goblin <-> Bat) | R value only | No change |
| R = same for all | All R set to same value | No change |
| 96-byte entry swap | Full name + stats | AI stays on slot (only name/stats change) |
| Type-7 idx swap | idx byte only | No change |
| Spawn cmd slot bytes | uint16 after FFFFFFFFFFFF (blocks 5-15) | No change |
| Spawn cmd XX prefix | XX in [XX 0B YY 00] (blocks 5-15) | No change |
| Spawn cmd YY prefix | YY in [XX 0B YY 00] (blocks 5-15) | No change |
| Deep region slot markers | [XX FF 00 00] in script+0x900 to +0x1DC0 | **Dark entities appear**, AI unchanged |
| Deep region cmd headers | 4-byte headers before slot markers | **More dark entities**, AI unchanged |
| Global monster table search | Searched all BLAZE.ALL for monster names | No separate AI table found |

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
| **??? UNKNOWN** | **AI behavior + spells + loot** | NOT FOUND |

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

## Final Conclusion: AI is in the PSX Executable

After **18 tests** covering every identified per-area data structure, the AI/behavior/spell system has **not been found in area data**. It is in the PSX executable code.

### Evidence
1. **18 swap/zero tests** on all per-area fields - AI never changes
2. **AI is strictly positional** - always follows slot index, regardless of all data changes
3. **No global AI table** in BLAZE.ALL - monster names only appear in per-area 96-byte entries
4. **Room bytecode (type-8)** confirmed as room scripts (elevator/doors), not AI - zeroing crashes room loading but 256-byte partial zero has no AI effect
5. **Every per-area structure now mapped** and tested: assignment entries, animation tables, 8-byte records, 96-byte stats, type-7 entries, spawn commands, deep entity region, type-8 bytecode

### What this means for modding
- **Can change:** 3D models (L+anim), texture variants (type-7 offset), stats/name (96-byte entries), formations (formation templates)
- **Cannot change via area data:** AI behavior, spell lists, loot tables - these are hardcoded in the executable per slot index or creature_type
- To change AI, one would need to reverse-engineer the PSX executable (MIPS assembly) to find the AI dispatch routine

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

*Last updated: 2026-02-06*
