# Level Modifications Guide

Modify enemy spawns and chest contents by game level.

---

## Quick Start

### 1. View Available Levels

Open `levels_index.json` to see all available levels:
- castle_of_vamp (Castle of Vamp)
- cavern_of_death (Cavern of Death)
- ruins (Ancient Ruins)
- forest (The Forest)
- etc.

### 2. Edit Level Data

**Edit Chests:**
```
levels_chests/castle_of_vamp.json
```

**Edit Spawns:**
```
levels_spawns/castle_of_vamp.json
```

### 3. Apply Changes

```batch
apply_level_mods.bat
```

Done! Test in emulator.

---

## File Structure

```
level_design/
├── levels_index.json              # Master index of all levels
├── levels_chests/                 # Chest data by level
│   ├── castle_of_vamp.json
│   ├── cavern_of_death.json
│   └── ...
├── levels_spawns/                 # Spawn data by level
│   ├── castle_of_vamp.json
│   ├── ruins.json
│   └── ...
├── patch_levels.py                # Patching script
├── apply_level_mods.bat           # Automation
└── organize_by_game_levels.py    # Data organizer
```

---

## Chest Modifications

### Example: castle_of_vamp.json

```json
{
  "level_name": "Castle of Vamp",
  "chests": [
    {
      "item_name": "Normal Sword",
      "item_id": 0,
      "quantity": 16,
      "position": { "x": 255, "y": 0, "z": 0 },
      "offset": "0x1017f8"
    }
  ]
}
```

### What You Can Modify

**item_id** - Change the item in the chest
- Find item IDs in `../items/all_items_clean.json`
- Example: 0 = Normal Sword, 5 = Healing Potion, etc.

**quantity** - Change how many items
- Range: 1-255
- Example: 99 for lots of potions

**position** - Change chest location (careful!)
- x, y, z coordinates
- Only change if you know what you're doing

**offset** - DO NOT CHANGE
- This is the memory location in BLAZE.ALL

---

## Spawn Modifications

### Example: castle_of_vamp.json

```json
{
  "level_name": "Castle of Vamp",
  "spawns": [
    {
      "monster_name": "Behemoth",
      "monster_id": 0,
      "spawn_chance": 75,
      "spawn_count": 3,
      "position": { "x": 100, "y": 50, "z": 200 },
      "zone_id": 0,
      "offset": "0x100008"
    }
  ]
}
```

### What You Can Modify

**monster_id** - Change which monster spawns
- Find monster IDs in `../monster_stats/_index.json`
- Example: 0 = Behemoth, 15 = Goblin, 100 = Red Dragon, etc.

**spawn_chance** - Probability of spawn (0-100%)
- 0 = Never spawns
- 50 = 50% chance
- 100 = Always spawns
- Note: Values above 100 are treated as 100%

**spawn_count** - Number of monsters per spawn
- Range: 1-255
- Example: 5 = spawn 5 monsters at once

**position** - Spawn location (careful!)
- x, y, z coordinates
- Only change if testing

**zone_id** - Zone identifier
- Usually don't change this

**offset** - DO NOT CHANGE
- This is the memory location in BLAZE.ALL

---

## Common Modifications

### Make Chests Give More Items

```json
{
  "item_name": "Healing Potion",
  "item_id": 5,
  "quantity": 99,    // Changed from 1 to 99
  "offset": "0x1017f8"
}
```

### Change Chest Contents to Better Items

Find item IDs in `items/all_items_clean.json`, then:

```json
{
  "item_name": "Elixir",
  "item_id": 42,     // Changed from Potion to Elixir
  "quantity": 10,
  "offset": "0x1017f8"
}
```

### Make Spawns Always Appear

```json
{
  "monster_name": "Red Dragon",
  "monster_id": 100,
  "spawn_chance": 100,   // Changed from 25 to 100
  "spawn_count": 1,
  "offset": "0x100008"
}
```

### Spawn More Monsters

```json
{
  "monster_name": "Goblin",
  "monster_id": 15,
  "spawn_chance": 100,
  "spawn_count": 10,     // Changed from 3 to 10
  "offset": "0x100008"
}
```

### Spawn Different Monster

```json
{
  "monster_name": "Red Dragon",  // Changed from Goblin
  "monster_id": 100,              // Changed from 15 to 100
  "spawn_chance": 50,
  "spawn_count": 1,
  "offset": "0x100008"
}
```

---

## Item ID Reference

Common items (see `items/all_items_clean.json` for full list):

| ID | Item Name |
|----|-----------|
| 0 | Normal Sword |
| 5 | Healing Potion |
| 10 | Elixir |
| 15 | Magic Potion |
| 20 | Antidote |
| 42 | Full Heal Elixir |
| 100 | Legendary Sword |

---

## Monster ID Reference

Common monsters (see `monster_stats/_index.json` for full list):

| ID | Monster Name | Type |
|----|--------------|------|
| 0 | Behemoth | Normal |
| 15 | Goblin | Normal |
| 30 | Dark Knight | Normal |
| 50 | Vampire | Normal |
| 100 | Red Dragon | Boss |
| 110 | Demon Lord | Boss |

---

## Workflow

### Basic Modification

```
1. Edit JSON files in levels_chests/ or levels_spawns/
2. Run: apply_level_mods.bat
3. Test in emulator
4. Repeat if needed
```

### Multiple Levels

```
1. Edit castle_of_vamp.json
2. Edit cavern_of_death.json
3. Edit ruins.json
4. Run: apply_level_mods.bat once
   (applies ALL changes)
5. Test in emulator
```

---

## Safety

### Automatic Backup

The script automatically creates:
```
work/BLAZE.ALL.backup
```

### Restore if Needed

```batch
cd work
copy BLAZE.ALL.backup BLAZE.ALL
```

---

## Regenerate Level Files

If you modify BLAZE.ALL manually and want to re-extract data:

```batch
py -3 analyze_chests.py
py -3 analyze_enemy_spawns.py
py -3 organize_by_game_levels.py
```

This will recreate all JSON files with current data.

---

## Advanced

### Create New Spawn Point

Add a new entry to the spawns array:

```json
{
  "monster_name": "New Monster",
  "monster_id": 50,
  "spawn_chance": 75,
  "spawn_count": 2,
  "position": { "x": 500, "y": 100, "z": 300 },
  "zone_id": 0,
  "offset": "0xNEWOFFSET"
}
```

**Note:** This requires finding a free offset in BLAZE.ALL (advanced).

### Batch Changes

Use a text editor with find/replace to change all instances:
- Find: `"spawn_chance": 50`
- Replace: `"spawn_chance": 100`

---

## Troubleshooting

**No changes in game?**
- Make sure you ran apply_level_mods.bat
- Check that patched.bin was created
- Load patched.bin in emulator, not original

**Game crashes?**
- Restore backup: `copy work\BLAZE.ALL.backup work\BLAZE.ALL`
- Check your modifications (invalid item_id or monster_id?)
- Don't change position values drastically

**Can't find a level?**
- Check levels_index.json for available levels
- Some levels might not have spawns/chests detected

---

## Reference Files

- **Item Database:** `items/all_items_clean.json`
- **Monster Database:** `monster_stats/_index.json`
- **Level Index:** `levels_index.json`
- **Main README:** `README.md`

---

**Happy Modding!** 🎮✨

Last Updated: 2026-02-04
