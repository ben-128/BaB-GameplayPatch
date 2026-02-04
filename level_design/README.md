# Level Design Analysis & Door Modding

Complete level design extraction and door modification system for **Blaze & Blade: Eternal Quest** (PSX).

---

## Quick Start

### 1. Modify Levels (Chests & Spawns by Game Level) ⭐ NEW

```batch
# 1. Edit level files
notepad levels_chests\castle_of_vamp.json
notepad levels_spawns\castle_of_vamp.json

# 2. Apply changes
apply_level_mods.bat

# Done! Test in emulator
```

See `LEVEL_MODS_GUIDE.md` for detailed examples.

### 2. Modify Doors

```batch
# Unlock all doors
unlock_all_doors.bat

# Or remove key requirements
remove_keys.bat

# Or test locking doors
lock_all_doors_test.bat
```

### 3. Visualize in Unity

1. Create new Unity project (3D)
2. Copy CSV files to `Assets/Data/`
3. Add `unity/CompleteVisualizationV2.cs` to a GameObject
4. See: `unity/COMPLETE_VISUALIZATION_GUIDE.md`

---

## Features

### Level Modification by Game Level ⭐ NEW
- Edit spawns and chests organized by actual game levels
- JSON files per level (Castle, Cavern, Ruins, etc.)
- Modify monster types, spawn rates, quantities
- Change chest contents and item quantities
- Binary patching with automatic backup
- Simple workflow: Edit JSON → Run .bat → Test

### Door Modification System
- Unlock/lock doors
- Change key requirements
- Modify destinations
- Binary patching with automatic backup
- Preset configurations for common mods

### Data Extraction
- **100 chests** with items and quantities
- **150 enemy spawns** with randomness data
- **50 door structures** with types, keys, destinations
- **2,500+ 3D coordinates** from 5 zones

### Unity Visualization
- 3D level geometry display
- Chests (yellow cubes) with item labels
- Enemy spawns (red/magenta spheres) with stats
- Doors (blue cylinders) with unlock conditions
- Toggle layers independently

---

## File Structure

```
level_design/
├── README.md                          # This file
├── DOOR_MODDING_QUICKSTART.md         # Door mod quick guide
├── DOOR_PATCHING_GUIDE.md             # Detailed door guide
├── SPAWNS_BY_LEVEL.md                 # Spawn organization
│
├── Scripts - Analysis
│   ├── add_ids_to_databases.py        # Add IDs to items/monsters
│   ├── analyze_chests.py              # Extract chest data
│   ├── analyze_doors.py               # Extract door data
│   ├── analyze_enemy_spawns.py        # Extract spawn data
│   ├── analyze_level_data.py          # Extract level names
│   ├── deep_structure_analysis.py     # Binary structure analysis
│   ├── explore_level_design.py        # Initial exploration
│   ├── export_coordinates.py          # Export 3D coordinates
│   ├── extract_spawn_data.py          # Extract spawn structures
│   └── organize_spawns_by_level.py    # Organize spawn data
│
├── Scripts - Modding
│   ├── patch_doors.py                 # Door patching system
│   ├── patch_levels.py                # Level patching system ⭐ NEW
│   ├── generate_door_presets.py       # Generate preset configs
│   ├── organize_by_game_levels.py     # Organize data by level ⭐ NEW
│   ├── apply_door_mods.bat            # Door automation
│   ├── apply_level_mods.bat           # Level automation ⭐ NEW
│   ├── unlock_all_doors.bat           # Unlock preset
│   ├── remove_keys.bat                # Remove keys preset
│   ├── lock_all_doors_test.bat        # Lock preset (test)
│   └── run_all_analyses.bat           # Re-run all analyses
│
├── Data - Chests
│   ├── chest_analysis.json            # Detailed chest data
│   └── chest_positions.csv            # Unity-compatible format
│
├── Data - Spawns
│   ├── spawn_analysis.json            # Detailed spawn data
│   ├── spawn_positions.csv            # Unity-compatible format
│   └── spawns_by_level.json           # Organized by zone
│
├── Data - Doors
│   ├── door_analysis.json             # Detailed door data
│   ├── door_positions.csv             # Unity-compatible format
│   ├── door_modifications.json        # Your custom mods
│   └── door_presets/                  # Preset configurations
│       ├── unlock_all_doors.json
│       ├── remove_key_requirements.json
│       └── lock_all_doors_test.json
│
├── Data - Coordinates
│   ├── coordinates_zone_1mb.csv       # Zone 1 geometry
│   ├── coordinates_zone_2mb.csv       # Zone 2 geometry
│   ├── coordinates_zone_3mb.csv       # Zone 3 vertex data
│   ├── coordinates_zone_5mb.csv       # Floor/ceiling geometry
│   └── coordinates_zone_9mb.csv       # Cameras/spawns
│
├── Data - Levels (Organized by Game Level) ⭐ NEW
│   ├── levels_index.json              # Master index
│   ├── levels_chests/                 # Chest data by level
│   │   ├── castle_of_vamp.json        # 91 chests
│   │   └── ...
│   └── levels_spawns/                 # Spawn data by level
│       ├── castle_of_vamp.json        # 16 spawns
│       ├── ruins.json                 # 50 spawns
│       ├── unknown.json               # 10 spawns
│       └── ...
│
└── Unity
    ├── CompleteVisualizationV2.cs     # Main visualization script
    ├── CoordinateLoader.cs            # Single zone loader
    ├── MultiZoneLoader.cs             # Multi-zone loader
    ├── COMPLETE_VISUALIZATION_GUIDE.md # Detailed guide
    └── UNITY_SETUP.md                 # Setup instructions
```

---

## Door Modification Workflow

### Option 1: Use Presets (5 minutes)

```batch
cd level_design

# Choose a preset
unlock_all_doors.bat
# OR remove_keys.bat
# OR lock_all_doors_test.bat

# Done! Test in emulator
```

### Option 2: Custom Modifications

```batch
cd level_design

# 1. Find door offsets (Unity or door_positions.csv)
# 2. Edit configuration
notepad door_modifications.json

# 3. Apply changes
apply_door_mods.bat

# 4. Test in emulator
```

**Example door_modifications.json:**
```json
{
  "modifications": [
    {
      "name": "Unlock Castle Door",
      "offset": "0x100000",
      "new_type": 0,
      "new_key_id": 0,
      "enabled": true
    }
  ]
}
```

**Door Types:**
- 0 = UNLOCKED (always open)
- 1 = KEY_LOCKED (requires key)
- 2 = MAGIC_LOCKED (magic spell)
- 3 = DEMON_ENGRAVED (demon item)
- 4 = GHOST_ENGRAVED (ghost item)
- 5 = EVENT_LOCKED (boss defeated)
- 6 = BOSS_DOOR (boss room)
- 7 = ONE_WAY (one direction only)

---

## Data Statistics

| Category | Count | Format |
|----------|-------|--------|
| Chests | 100 | JSON + CSV |
| Enemy Spawns | 150 | JSON + CSV |
| Doors | 50 | JSON + CSV |
| 3D Coordinates | 2,500+ | CSV (5 zones) |
| Door Presets | 3 | JSON |

---

## Re-generate Data

If you modify `BLAZE.ALL`:

```batch
cd level_design

# Re-run all analyses
run_all_analyses.bat

# Or individually
py -3 analyze_chests.py
py -3 analyze_enemy_spawns.py
py -3 analyze_doors.py
py -3 export_coordinates.py
```

---

## Unity Visualization

### Setup (5 minutes)

1. Create new Unity project (3D)
2. Create folder: `Assets/Data/`
3. Copy all CSV files to `Assets/Data/`
4. Create empty GameObject in scene
5. Add `CompleteVisualizationV2.cs` script
6. Play!

### Features

- **Toggle Layers**: Show/hide geometry, chests, spawns, doors
- **Color Coded**:
  - Yellow cubes = Chests
  - Red spheres = Normal enemies
  - Magenta spheres = Boss enemies
  - Blue cylinders = Doors
- **Interactive Labels**: Click objects to see details
- **Context Menu**: Right-click script to reload data

See `unity/COMPLETE_VISUALIZATION_GUIDE.md` for details.

---

## Guides

- **LEVEL_MODS_GUIDE.md** - ⭐ Modify chests & spawns by game level (NEW)
- **DOOR_MODDING_QUICKSTART.md** - 5-minute door modding guide
- **DOOR_PATCHING_GUIDE.md** - Complete door modification reference
- **SPAWNS_BY_LEVEL.md** - Spawn data organized by zone
- **unity/COMPLETE_VISUALIZATION_GUIDE.md** - Unity setup and usage
- **unity/UNITY_SETUP.md** - Unity installation guide

---

## Backup & Safety

### Automatic Backup
All scripts create automatic backups:
```
work/BLAZE.ALL.backup
```

### Restore if Problem
```batch
cd work
copy BLAZE.ALL.backup BLAZE.ALL
```

---

## Technical Details

### Extracted Structures

**Chest Structure (14 bytes):**
```
Offset+0:  int16 x, y, z (6 bytes)
Offset+6:  uint16 item_id (2 bytes)
Offset+8:  uint16 quantity (2 bytes)
Offset+10: uint16 flags (2 bytes)
Offset+12: uint16 padding (2 bytes)
```

**Spawn Structure (16 bytes):**
```
Offset+0:  int16 x, y, z (6 bytes)
Offset+6:  uint16 monster_id (2 bytes)
Offset+8:  uint8 spawn_chance (1 byte)
Offset+9:  uint8 spawn_count (1 byte)
Offset+10: uint16 zone_id (2 bytes)
Offset+12: uint32 flags (4 bytes)
```

**Door Structure (14 bytes):**
```
Offset+0:  int16 x, y, z (6 bytes)
Offset+6:  uint16 type (2 bytes)
Offset+8:  uint16 key_id (2 bytes)
Offset+10: uint16 dest_id (2 bytes)
Offset+12: uint16 flags (2 bytes)
```

### Coordinate Zones

| Zone | Offset | Range | Description |
|------|--------|-------|-------------|
| 1MB | 0x100000 | 0-7966 | Level geometry |
| 2MB | 0x200000 | 0-5911 | Level geometry |
| 3MB | 0x300000 | -61-246 | Vertex data |
| 5MB | 0x500000 | ±4085 | **Floor/ceiling** |
| 9MB | 0x900000 | ±8192 | Cameras/spawns |

---

## Known Issues

- Many detected doors at (0,0,0) are padding data
- No locked doors found in current analysis (all type=0)
- Use Unity visualization to identify real door positions
- In-game testing required for validation

---

## Contributing

For questions or improvements:
- Main project: `../README.md`
- Repository: GameplayPatch/level_design/

---

## License

Extracted data for research and video game preservation.

*Blaze & Blade: Eternal Quest © 1998 T&E Soft*

---

**Last Updated:** 2026-02-04
