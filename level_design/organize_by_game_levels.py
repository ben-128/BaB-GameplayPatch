#!/usr/bin/env python3
"""
Organize spawns and chests by actual game levels
Creates separate JSON files per level for easy modification
"""

import json
import os
import struct

# Game level definitions based on coordinate zones
GAME_LEVELS = {
    "castle_of_vamp": {
        "name": "Castle of Vamp",
        "zone_offsets": [(0x100000, 0x300000)],
        "description": "Main castle area with multiple floors"
    },
    "cavern_of_death": {
        "name": "Cavern of Death",
        "zone_offsets": [(0x300000, 0x400000)],
        "description": "Dark cave system"
    },
    "sealed_cave": {
        "name": "The Sealed Cave",
        "zone_offsets": [(0x400000, 0x500000)],
        "description": "Sealed underground area"
    },
    "ruins": {
        "name": "Ancient Ruins",
        "zone_offsets": [(0x500000, 0x600000)],
        "description": "Ruined structures and chambers"
    },
    "forest": {
        "name": "The Forest",
        "zone_offsets": [(0x600000, 0x700000)],
        "description": "Forest and outdoor areas"
    },
    "fire_mountain": {
        "name": "Mountain of Fire Dragon",
        "zone_offsets": [(0x700000, 0x800000)],
        "description": "Volcanic mountain area"
    },
    "valley": {
        "name": "Valley of White Wind",
        "zone_offsets": [(0x800000, 0x900000)],
        "description": "Valley region"
    },
    "unknown": {
        "name": "Unknown/Mixed Areas",
        "zone_offsets": [(0x900000, 0xA00000)],
        "description": "Unidentified or mixed level data"
    }
}

def offset_to_level(offset_str):
    """Determine which game level an offset belongs to"""
    offset = int(offset_str, 16)

    for level_id, level_data in GAME_LEVELS.items():
        for start, end in level_data['zone_offsets']:
            if start <= offset < end:
                return level_id

    return "unknown"

def load_spawns():
    """Load spawn data from spawn_analysis.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    spawn_path = os.path.join(script_dir, 'spawn_analysis.json')

    with open(spawn_path, 'r') as f:
        return json.load(f)

def load_chests():
    """Load chest data from chest_analysis.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chest_path = os.path.join(script_dir, 'chest_analysis.json')

    with open(chest_path, 'r') as f:
        return json.load(f)

def organize_spawns_by_level(spawn_data):
    """Organize spawns into game levels"""
    levels = {}

    for level_id in GAME_LEVELS.keys():
        levels[level_id] = {
            "level_name": GAME_LEVELS[level_id]["name"],
            "description": GAME_LEVELS[level_id]["description"],
            "spawns": []
        }

    # Process each spawn
    for spawn in spawn_data.get('spawn_structures', []):
        offset = spawn.get('offset', '0x0')
        level_id = offset_to_level(offset)

        # Skip padding data (0,0,0 with chance=0)
        x, y, z = spawn['position']['x'], spawn['position']['y'], spawn['position']['z']
        chance = spawn.get('spawn_chance', 0)
        if x == 0 and y == 0 and z == 0 and chance == 0:
            continue

        spawn_entry = {
            "monster_name": spawn.get('monster_name', 'Unknown'),
            "monster_id": spawn.get('monster_id', 0),
            "position": spawn['position'],
            "spawn_chance": spawn.get('spawn_chance', 0),
            "spawn_count": spawn.get('spawn_count', 1),
            "zone_id": spawn.get('zone_id', 0),
            "offset": offset,
            "comment": f"Spawn chance: {spawn.get('spawn_chance', 0)}%, Count: {spawn.get('spawn_count', 1)}"
        }

        levels[level_id]['spawns'].append(spawn_entry)

    return levels

def organize_chests_by_level(chest_data):
    """Organize chests into game levels"""
    levels = {}

    for level_id in GAME_LEVELS.keys():
        levels[level_id] = {
            "level_name": GAME_LEVELS[level_id]["name"],
            "description": GAME_LEVELS[level_id]["description"],
            "chests": []
        }

    # Process each chest
    for chest in chest_data.get('chest_structures', []):
        offset = chest.get('offset', '0x0')
        level_id = offset_to_level(offset)

        # Skip padding data (0,0,0)
        x, y, z = chest['position']['x'], chest['position']['y'], chest['position']['z']
        if x == 0 and y == 0 and z == 0:
            continue

        chest_entry = {
            "item_name": chest.get('item_name', 'Unknown'),
            "item_id": chest.get('item_id', 0),
            "quantity": chest.get('quantity', 1),
            "position": chest['position'],
            "offset": offset,
            "comment": f"Contains: {chest.get('quantity', 1)}x {chest.get('item_name', 'Unknown')}"
        }

        levels[level_id]['chests'].append(chest_entry)

    return levels

def save_level_files(levels_data, data_type):
    """Save separate JSON files for each level"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, f'levels_{data_type}')

    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    for level_id, level_data in levels_data.items():
        # Skip empty levels
        if data_type == 'spawns' and len(level_data['spawns']) == 0:
            continue
        if data_type == 'chests' and len(level_data['chests']) == 0:
            continue

        filename = f"{level_id}.json"
        filepath = os.path.join(output_dir, filename)

        # Add modification instructions
        output_data = {
            "_readme": f"Modify {data_type} for {level_data['level_name']}",
            "_instructions": [
                f"Edit the {data_type} array to change values",
                "monster_id/item_id: Change to spawn different monsters/items",
                "spawn_chance: 0-100 percentage (for spawns)",
                "spawn_count: Number of monsters per spawn (for spawns)",
                "quantity: Number of items in chest (for chests)",
                "position: x,y,z coordinates (careful with these)",
                "Save and run patch script to apply changes"
            ],
            **level_data
        }

        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=2)

        saved_files.append(filename)

        count = len(level_data.get('spawns', [])) if data_type == 'spawns' else len(level_data.get('chests', []))
        print(f"[OK] Saved {filename} - {count} {data_type}")

    return saved_files, output_dir

def create_master_index(spawn_files, chest_files):
    """Create a master index of all level files"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    index = {
        "_readme": "Master index of all level data files",
        "_usage": "Edit individual level files in levels_spawns/ and levels_chests/ folders",
        "levels": {}
    }

    for level_id, level_info in GAME_LEVELS.items():
        spawn_file = f"{level_id}.json"
        chest_file = f"{level_id}.json"

        index['levels'][level_id] = {
            "name": level_info['name'],
            "description": level_info['description'],
            "spawns_file": f"levels_spawns/{spawn_file}" if spawn_file in spawn_files else None,
            "chests_file": f"levels_chests/{chest_file}" if chest_file in chest_files else None
        }

    index_path = os.path.join(script_dir, 'levels_index.json')
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"[OK] Created levels_index.json")

def main():
    print("Level Data Organizer")
    print("=" * 60)
    print()

    # Load data
    print("Loading spawn data...")
    spawn_data = load_spawns()
    print(f"[OK] Loaded {len(spawn_data.get('spawns', []))} spawns")

    print("Loading chest data...")
    chest_data = load_chests()
    print(f"[OK] Loaded {len(chest_data.get('chests', []))} chests")
    print()

    # Organize by level
    print("Organizing spawns by game level...")
    spawn_levels = organize_spawns_by_level(spawn_data)
    print("[OK] Spawns organized")

    print("Organizing chests by game level...")
    chest_levels = organize_chests_by_level(chest_data)
    print("[OK] Chests organized")
    print()

    # Save files
    print("Saving spawn files...")
    spawn_files, spawn_dir = save_level_files(spawn_levels, 'spawns')
    print(f"[OK] Saved to: {spawn_dir}")
    print()

    print("Saving chest files...")
    chest_files, chest_dir = save_level_files(chest_levels, 'chests')
    print(f"[OK] Saved to: {chest_dir}")
    print()

    # Create master index
    print("Creating master index...")
    create_master_index(spawn_files, chest_files)
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Spawn files created: {len(spawn_files)}")
    print(f"Chest files created: {len(chest_files)}")
    print()
    print("Files are organized in:")
    print(f"  - levels_spawns/")
    print(f"  - levels_chests/")
    print(f"  - levels_index.json (master index)")
    print()
    print("Next steps:")
    print("  1. Edit JSON files in levels_spawns/ and levels_chests/")
    print("  2. Run patch script to apply changes (TODO)")

if __name__ == '__main__':
    main()
