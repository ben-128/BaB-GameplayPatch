# Formation Templates - Encounter Composition System

## Overview

When monsters spawn in Blaze & Blade, two systems work together:

1. **Spawn Groups** (`Data/spawn_groups/`) define which monster **types** are available in an area (96-byte stat entries + AI/model assignments)
2. **Formation Templates** (`Data/formations/`) define the **composition** of each encounter: how many monsters, and which types from the spawn group

## Location in BLAZE.ALL

Formation templates are stored in the **script area** that follows the 96-byte monster stat entries of each spawn group.

```
[96-byte entries x N monsters]   <-- spawn group (stats/names)
[script area]                    <-- contains formation templates + spawn points + dialog
```

The templates are found at varying offsets within the script area, typically after an initial block of spawn point records.

## Record Format (32 bytes)

Each formation template record is 32 bytes:

```
Offset  Size  Field
------  ----  -----
0x00    1     byte[0]  - flags (linked slot reference, usually 0x00 or 0x02)
0x01    3     padding  (00 00 00)
0x04    4     delimiter - FF FF FF FF = START of new formation, else 00 00 00 00
0x08    1     SLOT INDEX - monster type (0, 1, 2... = position in spawn group)
0x09    1     0xFF marker (identifies this as a template record)
0x0A    2     padding (00 00)
0x0C    6     coordinates (3x int16 LE) - always (0, 0, 0) for templates
0x12    6     additional params (zeros)
0x18    2     area identifier (constant per area, e.g. 0xDC 0x01)
0x1A    6     terminator: FF FF FF FF FF FF
```

### Key Fields

- **byte[8] = slot index**: This is THE key field. It references which monster in the spawn group appears. Slot 0 = first monster listed, slot 1 = second, etc.
- **bytes[4:8] = formation delimiter**: `FF FF FF FF` marks the first record of a new formation group. Subsequent records in the same formation have `00 00 00 00`.

## How Formations Work

- Each 32-byte record = **one monster** in the encounter
- Records are grouped into **formations** delimited by `FF FF FF FF` at bytes[4:8]
- The number of records in a formation = total monsters that spawn
- The distribution of byte[8] values = which monster types and how many of each

### Example: Cavern Floor 1 Area 1

Spawn group slots: 0=Lv20.Goblin, 1=Goblin-Shaman, 2=Giant-Bat

| # | Size | Composition | Slot values |
|---|------|-------------|-------------|
| 0 | 3 | 3x Goblin | [0, 0, 0] |
| 1 | 3 | 2x Goblin + 1x Shaman | [0, 0, 1] |
| 2 | 2 | 2x Shaman | [1, 1] |
| 3 | 4 | 4x Bat | [2, 2, 2, 2] |
| 4 | 4 | 2x Goblin + 2x Bat | [0, 0, 2, 2] |
| 5 | 3 | 3x Shaman | [1, 1, 1] |
| 6 | 4 | 2x Goblin + 2x Shaman | [0, 0, 1, 1] |
| 7 | 4 | 2x Goblin + 1x Shaman + 1x Bat | [0, 0, 1, 2] |

## Modifying Formations

### Changing monster types (easy)

To swap which monster appears in a formation without changing counts:
- Change **byte[8]** of each record to a different slot index
- No size change, no offset issues

Example: Change F03 from "4x Bat" to "4x Goblin":
- Change all 4 records from byte[8]=2 to byte[8]=0

### Changing formation size (complex)

Adding or removing records shifts all subsequent data in the script area,
which breaks offset tables and script pointers. This requires:

1. Inserting/removing 32 bytes for each monster added/removed
2. Updating all offset tables that reference data after the change
3. Updating the script area size if tracked somewhere

A safer alternative: **repurpose existing records** within a formation.
For example, to reduce a 4-monster formation to 3, you could set byte[8]
of the 4th record to match the 3rd (making a "duplicate" that still spawns
but as the same type). However, this doesn't truly reduce the count.

### Areas with 0 formations

Some areas show 0 detected formations. These are likely:
- Boss rooms with scripted/fixed spawns
- Cutscene/transition areas
- Areas using a different spawn mechanism (direct script commands)

## Directory Structure

One JSON per area, organized in level subdirectories:

```
Data/formations/
  cavern_of_death/
    floor_1_area_1.json
    floor_1_area_2.json
    ...
  forest/
    floor_1_area_1.json
    ...
```

Each area JSON:

```json
{
  "level_name": "Cavern of Death",
  "name": "Floor 1 - Area 1",
  "group_offset": "0xF7A97C",
  "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
  "formation_count": 8,
  "formations": [
    {
      "total": 3,
      "composition": [
        {"count": 3, "slot": 0, "monster": "Lv20.Goblin"}
      ],
      "slots": [0, 0, 0],
      "offset": "0xF7AFFC"
    }
  ]
}
```

## Extraction Script

Run `extract_formations.py` to regenerate all JSONs from BLAZE.ALL:

```
py -3 Data/formations/extract_formations.py
```

## Relation to Other Systems

```
Spawn Group (96-byte entries)  -->  WHAT monsters exist (types, stats, names)
Formation Templates            -->  HOW MANY of each type per encounter
Assignment Pairs (L/R)         -->  AI behavior + 3D model mapping
Animation Table                -->  Animation data per slot
Room Script spawn commands     -->  WHERE encounters trigger (coordinates)
```
