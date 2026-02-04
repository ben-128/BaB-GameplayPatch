"""
analyze_enemy_spawns.py
Analyze enemy spawn points: monsters, positions, and spawn conditions

Usage: py -3 analyze_enemy_spawns.py
"""

from pathlib import Path
import struct
import json

SCRIPT_DIR = Path(__file__).parent.parent
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def load_monster_database():
    """Load monster stats database"""
    monster_index = SCRIPT_DIR / "monster_stats" / "_index.json"

    if not monster_index.exists():
        print("Warning: Monster index not found, searching for monster files...")
        # Try to load from individual files
        monsters = []
        boss_dir = SCRIPT_DIR / "monster_stats" / "boss"
        normal_dir = SCRIPT_DIR / "monster_stats" / "normal_enemies"

        for directory in [boss_dir, normal_dir]:
            if directory.exists():
                for json_file in directory.glob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            monster = json.load(f)
                            monsters.append(monster)
                    except:
                        pass

        return monsters
    else:
        with open(monster_index, 'r') as f:
            data = json.load(f)
            return data.get('monsters', [])

def find_level_names_offsets(data):
    """Find level name locations to map spawns to zones"""
    level_names = [
        b"Castle Of Vamp",
        b"CAVERN OF DEATH",
        b"The Sealed Cave",
        b"The Ancient Ruins",
        b"VALLEY OF WHITE WIND"
    ]

    zones = {}
    for name in level_names:
        offset = data.find(name)
        if offset != -1:
            zones[name.decode('ascii', errors='ignore')] = offset

    return zones

def find_spawn_structures(data, monsters):
    """
    Search for enemy spawn structures
    Hypothesis: spawn structure contains:
    - Monster ID (2 bytes)
    - Position X, Y, Z (6 bytes)
    - Spawn chance/probability (2 bytes)
    - Spawn count min/max (2-4 bytes)
    - Flags (2 bytes)
    Total: ~14-18 bytes
    """

    # Build monster ID map
    monster_map = {}
    for monster in monsters:
        mid = monster.get('id')
        if mid is not None:
            monster_map[mid] = monster

    print(f"Loaded {len(monster_map)} monster IDs")

    if not monster_map:
        print("ERROR: No monsters loaded!")
        return []

    spawns = []

    # Search zones where spawns might be
    search_zones = [
        (0x100000, 0x300000, "Level Data 1-3MB"),
        (0x500000, 0x700000, "Level Data 5-7MB"),
        (0x900000, 0xA00000, "Level Data 9-10MB")
    ]

    for zone_start, zone_end, zone_name in search_zones:
        if zone_end > len(data):
            continue

        print(f"\nSearching {zone_name} ({hex(zone_start)} - {hex(zone_end)})...")

        found_in_zone = 0

        for i in range(zone_start, zone_end - 18, 2):
            try:
                # Read potential monster ID
                monster_id = struct.unpack_from('<H', data, i)[0]  # unsigned 16-bit

                # Check if it's a valid monster ID
                if monster_id not in monster_map:
                    continue

                # Read potential spawn structure
                x = struct.unpack_from('<h', data, i+2)[0]
                y = struct.unpack_from('<h', data, i+4)[0]
                z = struct.unpack_from('<h', data, i+6)[0]

                # Validate coordinates
                if not all(-8192 <= coord <= 8192 for coord in [x, y, z]):
                    # Maybe different structure format?
                    # Try alternative: ID at different position
                    continue

                # Read additional spawn data
                spawn_chance = struct.unpack_from('<H', data, i+8)[0]
                spawn_count = struct.unpack_from('<H', data, i+10)[0]
                flags = struct.unpack_from('<H', data, i+12)[0]

                # Validate spawn data (reasonable values)
                if spawn_chance > 255 or spawn_count > 20:
                    continue

                # Found a potential spawn!
                monster = monster_map[monster_id]

                spawns.append({
                    'offset': hex(i),
                    'zone': zone_name,
                    'monster_id': monster_id,
                    'monster_name': monster.get('name', 'Unknown'),
                    'monster_type': 'Boss' if monster.get('category') == 'boss' else 'Normal',
                    'position': {'x': x, 'y': y, 'z': z},
                    'spawn_chance': spawn_chance,
                    'spawn_count': spawn_count,
                    'flags': hex(flags),
                    'raw_hex': data[i:i+18].hex()
                })

                found_in_zone += 1

                if found_in_zone >= 50:  # Limit per zone
                    break

            except:
                pass

        print(f"  Found {found_in_zone} potential spawns in {zone_name}")

    return spawns

def find_spawn_tables(data, monsters):
    """
    Look for spawn tables (arrays of spawn entries)
    A spawn table would have multiple consecutive spawn structures
    """

    monster_ids = set(m.get('id') for m in monsters if m.get('id') is not None)

    tables = []

    # Sample regions
    for base in range(0x100000, 0xA00000, 0x100000):  # Every 1MB
        if base > len(data):
            break

        # Look for sequences of monster IDs
        consecutive = 0
        table_start = None

        for i in range(base, min(base + 0x10000, len(data) - 2), 2):
            try:
                mid = struct.unpack_from('<H', data, i)[0]

                if mid in monster_ids:
                    if consecutive == 0:
                        table_start = i
                    consecutive += 1
                else:
                    if consecutive >= 3:  # At least 3 consecutive monster IDs
                        tables.append({
                            'offset': hex(table_start),
                            'entry_count': consecutive,
                            'estimated_size': consecutive * 16  # Assume 16 bytes per entry
                        })
                    consecutive = 0
            except:
                consecutive = 0

    return tables

def analyze_spawn_randomness(spawns):
    """Analyze spawn patterns and randomness"""
    if not spawns:
        return {}

    # Group by monster
    by_monster = {}
    for spawn in spawns:
        mid = spawn['monster_id']
        if mid not in by_monster:
            by_monster[mid] = []
        by_monster[mid].append(spawn)

    # Analyze
    analysis = {
        'unique_monsters': len(by_monster),
        'total_spawn_points': len(spawns),
        'monsters_with_multiple_spawns': 0,
        'spawn_chance_distribution': {}
    }

    for mid, spawn_list in by_monster.items():
        if len(spawn_list) > 1:
            analysis['monsters_with_multiple_spawns'] += 1

    # Spawn chance distribution
    for spawn in spawns:
        chance = spawn['spawn_chance']
        if chance not in analysis['spawn_chance_distribution']:
            analysis['spawn_chance_distribution'][chance] = 0
        analysis['spawn_chance_distribution'][chance] += 1

    return analysis

def main():
    print("=" * 70)
    print("  ENEMY SPAWN ANALYSIS")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Load monster database
    print("\n[1] LOADING MONSTER DATABASE")
    print("-" * 70)
    monsters = load_monster_database()
    print(f"Loaded {len(monsters)} monsters")

    if not monsters:
        print("\nERROR: No monsters loaded!")
        print("Please ensure monster_stats/_index.json exists or")
        print("monster files are in monster_stats/boss/ and monster_stats/normal_enemies/")
        return

    # Find level zones
    print("\n[2] IDENTIFYING LEVEL ZONES")
    print("-" * 70)
    zones = find_level_names_offsets(data)
    print(f"Found {len(zones)} level zones:")
    for name, offset in zones.items():
        print(f"  {name}: {hex(offset)}")

    # Find spawn structures
    print("\n[3] SEARCHING FOR SPAWN STRUCTURES")
    print("-" * 70)
    spawns = find_spawn_structures(data, monsters)
    print(f"\nTotal spawns found: {len(spawns)}")

    if spawns:
        print("\nFirst 20 spawns:")
        for spawn in spawns[:20]:
            print(f"\n  {spawn['offset']} - {spawn['monster_name']} ({spawn['monster_type']})")
            print(f"    Position: ({spawn['position']['x']}, {spawn['position']['y']}, {spawn['position']['z']})")
            print(f"    Spawn chance: {spawn['spawn_chance']}%")
            print(f"    Count: {spawn['spawn_count']}")

    # Find spawn tables
    print("\n[4] DETECTING SPAWN TABLES")
    print("-" * 70)
    tables = find_spawn_tables(data, monsters)
    print(f"Found {len(tables)} potential spawn tables")

    if tables:
        print("\nSpawn tables:")
        for table in tables[:10]:
            print(f"  Offset: {table['offset']}, Entries: {table['entry_count']}, Size: {table['estimated_size']} bytes")

    # Analyze randomness
    print("\n[5] SPAWN RANDOMNESS ANALYSIS")
    print("-" * 70)
    if spawns:
        analysis = analyze_spawn_randomness(spawns)
        print(f"Unique monsters that spawn: {analysis['unique_monsters']}")
        print(f"Total spawn points: {analysis['total_spawn_points']}")
        print(f"Monsters with multiple spawn points: {analysis['monsters_with_multiple_spawns']}")

        print("\nSpawn chance distribution:")
        for chance, count in sorted(analysis['spawn_chance_distribution'].items())[:10]:
            print(f"  {chance}%: {count} spawns")

    # Save results
    output_file = SCRIPT_DIR / "level_design" / "spawn_analysis.json"
    results = {
        'level_zones': zones,
        'spawn_structures': spawns,
        'spawn_tables': tables,
        'analysis': analyze_spawn_randomness(spawns) if spawns else {},
        'summary': {
            'total_spawns': len(spawns),
            'total_tables': len(tables),
            'monsters_loaded': len(monsters)
        }
    }

    print(f"\n\nSaving results to {output_file.name}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Create CSV for Unity
    if spawns:
        csv_file = SCRIPT_DIR / "level_design" / "spawn_positions.csv"
        with open(csv_file, 'w') as f:
            f.write("offset,zone,x,y,z,monster_id,monster_name,type,spawn_chance,spawn_count\n")
            for spawn in spawns:
                f.write(f"{spawn['offset']},{spawn['zone']},")
                f.write(f"{spawn['position']['x']},{spawn['position']['y']},{spawn['position']['z']},")
                f.write(f"{spawn['monster_id']},{spawn['monster_name']},{spawn['monster_type']},")
                f.write(f"{spawn['spawn_chance']},{spawn['spawn_count']}\n")

        print(f"Spawn positions saved to: {csv_file.name}")
        print("  -> Can be imported into Unity for visualization")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Monsters loaded: {len(monsters)}")
    print(f"Level zones found: {len(zones)}")
    print(f"Spawn structures: {len(spawns)}")
    print(f"Spawn tables: {len(tables)}")
    print(f"\nFiles created:")
    print(f"  - spawn_analysis.json")
    if spawns:
        print(f"  - spawn_positions.csv (Unity-ready)")
    print("="*70)

if __name__ == '__main__':
    main()
