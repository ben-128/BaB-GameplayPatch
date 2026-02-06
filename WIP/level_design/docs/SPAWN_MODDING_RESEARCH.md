# Spawn Group Modding - Research Notes

Research on modifying monster spawn groups in **Blaze & Blade: Eternal Quest** (PSX).

Status: **Work In Progress** - visual/AI/spell swapping not yet achieved.

---

## What Works

### Monster Name + Stats Patching
The current `patch_spawn_groups.py` system successfully patches:
- **Monster name** (16-byte ASCII string) - confirmed in-game via identify items
- **Combat stats** (80 bytes = 40 x uint16 LE) - confirmed in-game (HP changes visible)

Each monster in BLAZE.ALL is a **96-byte entry**: 16 bytes name + 80 bytes stats.
When the JSON says to replace monster A with monster B, the script copies B's full 96-byte entry over A's slot.

### BIN Injection
`patch_blaze_all.py` correctly injects the patched BLAZE.ALL at both LBA locations (163167 and 185765) in the game BIN. Both copies are verified identical. RAW sector format: 2352 bytes/sector, 24-byte header, 2048 bytes user data.

---

## What Does NOT Work

### Visual Model / AI Behavior / Spells
Changing monster names+stats does **not** change:
- **3D model / sprite** - the original monster's visual remains
- **AI behavior** - movement patterns, attack patterns unchanged
- **Spell assignments** - the original monster's spells are used
- **Loot tables** - drops remain those of the original monster

**Example test:** Changed Cavern of Death Floor 1 from `[Lv20.Goblin, Goblin-Shaman, Giant-Bat]` to `[Kobold, Giant-Beetle, Giant-Ant]` (Forest enemies).
- Result: Monsters LOOK like Cavern enemies (Goblin visual, Bat visual...)
- Using an identify item shows Forest enemy NAMES (Kobold, Giant-Beetle...)
- HP matches the Forest enemy stats (patched correctly)
- But behavior, spells, visual model, and loot are all still Cavern enemies

### Conclusion
The 96-byte monster entries only define the **identity card** (name + stats) of each monster slot. The actual monster **type** (which controls model, AI, spells, loot) is defined elsewhere in the room/level data structure.

---

## Monster Entry Format (96 bytes)

```
Offset  Size    Description
0x00    16      ASCII name (null-padded)
0x10    2       Stat 0 (uint16 LE)
0x12    2       Stat 1
...
0x5E    2       Stat 39
```

Total: 16 + (40 x 2) = 96 bytes per monster.

Monsters are stored consecutively in groups of 2-6 entries per area.

---

## Pre-Group Structure (~176 bytes before each group)

Each monster group is preceded by a header structure containing:

| Relative Offset | Content | Description |
|-----------------|---------|-------------|
| -512 to -400 | Variable | Room script data or text strings |
| -400 to -256 | uint32 LE[] | Pointer/offset table |
| -224 to -176 | zeros | Padding |
| -160 to -128 | bytes | Sequential index table (00 01 02 03...) |
| -96 to -80 | uint32[] | Descriptor entries (8-byte records) |
| -48 to 0 | 8-byte records | Formation pairs with 0x40 flag |

### Formation Pairs (8 bytes each)
```
[slot_index, param_L, 0x00, 0x00] [slot_index, param_R, 0x00, 0x40]
```
- `slot_index`: increments (01, 02, 03...) per monster in group
- `param_L` and `param_R`: vary per group, NOT global monster IDs
- `0x40` flag: always present in second half of pair

**Important:** param_L/param_R are NOT monster type IDs. The same monster (e.g. Cave-Bear) has different param values in different groups.

---

## Monster IDs (_index.json)

124 monsters with IDs 0-123 (gaps at 85, 87, 89). IDs 0-22 are bosses.

Key IDs for tested monsters:
| Monster | ID | Hex |
|---------|-----|------|
| Giant-Ant | 48 | 0x30 |
| Giant-Bat | 49 | 0x31 |
| Giant-Beetle | 50 | 0x32 |
| Goblin-Leader | 58 | 0x3A |
| Goblin-Shaman | 59 | 0x3B |
| Kobold | 79 | 0x4F |
| Lv20.Goblin | 84 | 0x54 |

These IDs were **NOT found** as simple uint8 values in the 512-byte pre-group region.

---

## Where Monster Type ID Might Be

Possible locations still to investigate:

1. **Room script bytecode** (5-18KB gaps between groups) - contains opcodes (0x2C, 0x2D, 0x0D, 0x04, 0xFF delimiters), text strings, 3D coordinates. May reference monster type during room init.

2. **Pointer table in pre-group header** - the uint32 offset values may point to model/AI data elsewhere in BLAZE.ALL.

3. **LEVELS.DAT** - 46,278,656 bytes (71,680 bytes larger than BLAZE.ALL). Contains German monster names but different data layout. Could contain separate encounter definitions. Not currently used.

4. **Wider search** - Monster type IDs might be stored as uint16 LE (e.g., 0x0054 for Lv20.Goblin) or uint32 LE in a different region entirely, possibly a master room definition table.

---

## Spawn Group JSON Files

Located in `WIP/level_design/spawn_groups/`:

| File | Level | Groups |
|------|-------|--------|
| cavern_of_death.json | Cavern of Death | 10 |
| castle_of_vamp.json | Castle of Vamp | 12 |
| forest.json | The Forest | 9 |
| undersea.json | Undersea / Lake | 2 |
| hall_of_demons.json | Hall of Demons | 11 |

Each JSON defines monster **names** per group. The patching script replaces name+stats but this is insufficient for full monster swapping.

---

## Next Steps

1. **Search wider binary area** for monster type IDs as uint16/uint32 LE values
2. **Analyze room script bytecode** for monster spawn opcodes
3. **Cross-reference pointer tables** in pre-group headers to find model/AI references
4. **Investigate LEVELS.DAT** structure for encounter definitions
5. **Update patch_spawn_groups.py** once the type ID location is found, to also patch the visual/AI/spell/loot reference

---

*Last updated: 2026-02-05*
