"""
extract_spawn_data.py
Extract spawn points and level design structures from BLAZE.ALL

Usage: py -3 extract_spawn_data.py
"""

from pathlib import Path
import struct
import json

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def find_monster_references(data):
    """Find references to monster IDs in the level data"""
    # Load monster index to get names
    monster_index_file = SCRIPT_DIR / "monster_stats" / "_index.json"

    if not monster_index_file.exists():
        print("Warning: Monster index not found")
        return []

    with open(monster_index_file, 'r') as f:
        monster_index = json.load(f)

    # Build a map of monster IDs to names
    monster_map = {}
    for monster in monster_index.get('monsters', []):
        monster_id = monster.get('id')
        if monster_id is not None:
            monster_map[monster_id] = monster.get('name', 'Unknown')

    print(f"\nLoaded {len(monster_map)} monster IDs")

    # Search for monster ID patterns in the binary
    # Monster IDs are likely stored as int16 or uint16
    results = []

    print("\nSearching for monster spawn patterns...")

    # Sample the file in chunks
    chunk_size = 1024 * 1024  # 1MB chunks
    for chunk_offset in range(0, len(data), chunk_size):
        chunk = data[chunk_offset:chunk_offset + chunk_size]

        # Look for sequences that might be spawn data
        # Pattern: [monster_id, x, y, z, ...] or similar
        for i in range(0, len(chunk) - 10, 2):
            try:
                # Read potential monster ID
                val = struct.unpack_from('<H', chunk, i)[0]  # unsigned 16-bit

                if val in monster_map:
                    # Found a potential monster ID
                    offset = chunk_offset + i

                    # Read surrounding data for context
                    context_start = max(0, offset - 32)
                    context_end = min(len(data), offset + 64)
                    context = data[context_start:context_end]

                    # Try to parse as structured data
                    struct_data = []
                    for j in range(0, min(32, len(context)), 2):
                        try:
                            v = struct.unpack_from('<h', context, j)[0]
                            struct_data.append(v)
                        except:
                            break

                    results.append({
                        'offset': hex(offset),
                        'monster_id': val,
                        'monster_name': monster_map[val],
                        'context_hex': context[:32].hex(),
                        'int16_values': struct_data[:16]
                    })

            except:
                pass

        # Limit results
        if len(results) > 200:
            break

    return results

def find_chest_keywords(data):
    """Find chest-related data"""
    print("\nSearching for chest-related structures...")

    chest_keywords = [
        b'chest',
        b'treasure',
        b'Chest',
        b'Treasure'
    ]

    results = []
    for keyword in chest_keywords:
        offset = 0
        while True:
            pos = data.find(keyword, offset)
            if pos == -1:
                break

            # Read context
            context_start = max(0, pos - 64)
            context_end = min(len(data), pos + 128)
            context = data[context_start:context_end]

            # Try to find structured data nearby
            # Look backwards for potential header
            struct_offset = max(0, pos - 32)
            struct_data = []
            for i in range(0, 32, 2):
                try:
                    v = struct.unpack_from('<h', data, struct_offset + i)[0]
                    struct_data.append(v)
                except:
                    break

            results.append({
                'keyword': keyword.decode('ascii'),
                'offset': hex(pos),
                'context_before_hex': data[max(0, pos-32):pos].hex(),
                'context_after_hex': data[pos:min(len(data), pos+32)].hex(),
                'struct_before': struct_data
            })

            offset = pos + 1

            if len(results) > 100:
                break

        if len(results) > 100:
            break

    return results

def analyze_level_structure_zones(data):
    """Analyze specific memory zones that might contain level structures"""
    print("\nAnalyzing potential level structure zones...")

    # Based on the project, we know:
    # - Monster stats are at specific offsets
    # - Fate coin shop at 0x00B1443C
    # - Auction prices at 0x002EA500
    # Let's look for level data in between

    zones_to_check = [
        (0x00100000, 0x00200000, "Zone 1MB-2MB"),
        (0x00300000, 0x00400000, "Zone 3MB-4MB"),
        (0x00500000, 0x00600000, "Zone 5MB-6MB"),
        (0x00700000, 0x00800000, "Zone 7MB-8MB"),
        (0x00900000, 0x00A00000, "Zone 9MB-10MB"),
    ]

    results = []
    for start, end, name in zones_to_check:
        if end > len(data):
            continue

        zone_data = data[start:end]

        # Look for repeated structures
        # Check for patterns that repeat every N bytes
        for struct_size in [16, 20, 24, 32, 40, 48, 64]:
            # Sample first few structures
            samples = []
            for i in range(0, min(struct_size * 10, len(zone_data)), struct_size):
                chunk = zone_data[i:i+struct_size]
                if len(chunk) == struct_size:
                    # Check if it's not all zeros or all 0xFF
                    if not (all(b == 0 for b in chunk) or all(b == 0xFF for b in chunk)):
                        samples.append(chunk.hex())

            if len(samples) >= 3:  # Found at least 3 non-empty structures
                # Check if they look similar (heuristic)
                results.append({
                    'zone': name,
                    'offset': hex(start),
                    'struct_size': struct_size,
                    'sample_count': len(samples),
                    'samples': samples[:5]
                })

    return results

def main():
    print("=" * 70)
    print("  SPAWN DATA EXTRACTION")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Step 1: Find monster references
    print("\n[1] MONSTER SPAWN ANALYSIS")
    print("-" * 70)
    monster_spawns = find_monster_references(data)

    print(f"\nFound {len(monster_spawns)} potential monster spawn references")
    if monster_spawns:
        print("\nFirst 20 monster spawn candidates:")
        for spawn in monster_spawns[:20]:
            print(f"  {spawn['offset']}: {spawn['monster_name']} (ID {spawn['monster_id']})")
            print(f"    Values: {spawn['int16_values'][:8]}")

    # Step 2: Find chest data
    print("\n[2] CHEST/TREASURE ANALYSIS")
    print("-" * 70)
    chest_data = find_chest_keywords(data)
    print(f"\nFound {len(chest_data)} chest/treasure references")

    # Step 3: Analyze structure zones
    print("\n[3] LEVEL STRUCTURE ZONES")
    print("-" * 70)
    structure_zones = analyze_level_structure_zones(data)
    print(f"\nFound {len(structure_zones)} potential structure zones:")
    for zone in structure_zones:
        print(f"  {zone['zone']} at {zone['offset']}: {zone['sample_count']} x {zone['struct_size']}-byte structures")

    # Save results
    output_file = SCRIPT_DIR / "spawn_data_analysis.json"
    results = {
        'monster_spawns': monster_spawns[:100],  # Limit to first 100
        'chest_data': chest_data[:50],
        'structure_zones': structure_zones,
        'summary': {
            'total_monster_spawns': len(monster_spawns),
            'total_chest_references': len(chest_data),
            'total_structure_zones': len(structure_zones)
        }
    }

    print(f"\nSaving results to {output_file.name}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Monster spawn candidates: {len(monster_spawns)}")
    print(f"Chest/treasure references: {len(chest_data)}")
    print(f"Structure zones: {len(structure_zones)}")
    print(f"\nResults saved to: {output_file.name}")
    print("="*70)

if __name__ == '__main__':
    main()
