"""
analyze_level_data.py
Detailed analysis of level design data in BLAZE.ALL

Usage: py -3 analyze_level_data.py
"""

from pathlib import Path
import struct
import json

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

# Known level names from initial exploration
LEVEL_NAMES = [
    "Castle Of Vamp",
    "CAVERN OF DEATH",
    "The Sealed Cave",
    "The Wood of Ruins",
    "The Ancient Ruins",
    "The Ruins in the Lake",
    "The Forest",
    "The Mountain of the Fire Dragon",
    "VALLEY OF WHITE WIND",
    "Map03",
    "MAP10",
]

def find_string_in_data(data, search_str):
    """Find all occurrences of a string in binary data"""
    search_bytes = search_str.encode('ascii')
    offsets = []
    start = 0
    while True:
        pos = data.find(search_bytes, start)
        if pos == -1:
            break
        offsets.append(pos)
        start = pos + 1
    return offsets

def read_context_around_offset(data, offset, before=64, after=64):
    """Read context around an offset"""
    start = max(0, offset - before)
    end = min(len(data), offset + after)
    return data[start:end], start

def parse_potential_structure(data, offset, size=256):
    """Try to parse structured data around an offset"""
    chunk = data[offset:offset+size]

    # Try interpreting as various data types
    result = {
        'offset': hex(offset),
        'hex': chunk[:64].hex(),
        'ascii': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk[:64])
    }

    # Try parsing as int16 values
    int16_values = []
    for i in range(0, min(32, len(chunk)), 2):
        try:
            val = struct.unpack_from('<h', chunk, i)[0]
            int16_values.append(val)
        except:
            break

    result['int16_samples'] = int16_values[:16]

    # Try parsing as int32 values
    int32_values = []
    for i in range(0, min(32, len(chunk)), 4):
        try:
            val = struct.unpack_from('<i', chunk, i)[0]
            int32_values.append(val)
        except:
            break

    result['int32_samples'] = int32_values[:8]

    return result

def find_level_name_structures(data):
    """Find all level names and analyze surrounding data"""
    results = {}

    for level_name in LEVEL_NAMES:
        print(f"\nSearching for '{level_name}'...")
        offsets = find_string_in_data(data, level_name)

        if offsets:
            print(f"  Found {len(offsets)} occurrence(s)")
            level_data = []

            for i, offset in enumerate(offsets[:5]):  # Analyze first 5 occurrences
                print(f"    Occurrence {i+1} at offset {hex(offset)}")

                # Read before and after
                before_data = data[max(0, offset-128):offset]
                after_data = data[offset+len(level_name):offset+len(level_name)+128]

                # Check for null-terminated string
                string_end = offset + len(level_name)
                while string_end < len(data) and data[string_end] != 0:
                    string_end += 1

                full_string = data[offset:string_end].decode('ascii', errors='ignore')

                # Parse structures before and after
                before_struct = parse_potential_structure(data, max(0, offset-64))
                after_struct = parse_potential_structure(data, offset + len(full_string) + 1)

                level_data.append({
                    'offset': hex(offset),
                    'full_string': full_string,
                    'before': before_struct,
                    'after': after_struct
                })

            results[level_name] = level_data

    return results

def search_for_map_data_patterns(data):
    """Search for common map data patterns"""
    print("\n" + "="*60)
    print("SEARCHING FOR MAP DATA PATTERNS")
    print("="*60)

    patterns = []

    # Look for "Map" or "MAP" followed by numbers
    import re

    # Convert relevant portions to string for regex
    # Sample every 1MB to avoid memory issues
    for base_offset in range(0, len(data), 1024*1024):
        chunk_size = min(1024*1024, len(data) - base_offset)
        chunk = data[base_offset:base_offset + chunk_size]

        # Look for Map references
        try:
            text = chunk.decode('ascii', errors='ignore')
            map_matches = list(re.finditer(r'[Mm][Aa][Pp]\s*\d+', text))

            for match in map_matches[:10]:  # First 10 per chunk
                actual_offset = base_offset + match.start()
                context, _ = read_context_around_offset(data, actual_offset, 32, 32)
                patterns.append({
                    'type': 'map_number',
                    'offset': hex(actual_offset),
                    'text': match.group(),
                    'context_hex': context.hex()
                })
        except:
            pass

    return patterns[:50]  # Return first 50

def analyze_floor_references(data):
    """Analyze floor/level references"""
    print("\n" + "="*60)
    print("ANALYZING FLOOR/LEVEL REFERENCES")
    print("="*60)

    floor_terms = ["1st Floor", "2nd Floor", "3rd Floor", "Floor", "Underlevel"]
    results = {}

    for term in floor_terms:
        offsets = find_string_in_data(data, term)
        if offsets:
            print(f"\n'{term}': {len(offsets)} occurrences")
            results[term] = [hex(o) for o in offsets[:10]]

    return results

def main():
    print("=" * 70)
    print("  DETAILED LEVEL DATA ANALYSIS")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes\n")

    # Step 1: Find and analyze level names
    print("\n[1] LEVEL NAME ANALYSIS")
    print("-" * 70)
    level_structures = find_level_name_structures(data)

    # Save detailed results to JSON
    output_file = SCRIPT_DIR / "level_data_analysis.json"
    print(f"\nSaving detailed analysis to {output_file.name}...")

    # Step 2: Search for map data patterns
    print("\n[2] MAP DATA PATTERNS")
    print("-" * 70)
    map_patterns = search_for_map_data_patterns(data)
    print(f"\nFound {len(map_patterns)} map-related patterns")
    for pattern in map_patterns[:10]:
        print(f"  {pattern['type']} at {pattern['offset']}: {pattern['text']}")

    # Step 3: Analyze floor references
    print("\n[3] FLOOR/LEVEL REFERENCES")
    print("-" * 70)
    floor_data = analyze_floor_references(data)

    # Compile all results
    full_results = {
        'level_names': {k: v for k, v in level_structures.items()},
        'map_patterns': map_patterns,
        'floor_references': floor_data,
        'summary': {
            'total_levels_found': len(level_structures),
            'total_map_patterns': len(map_patterns),
            'file_size': len(data)
        }
    }

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Detailed analysis saved to {output_file.name}")

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Levels analyzed: {len(level_structures)}")
    print(f"Map patterns found: {len(map_patterns)}")
    print(f"Output: {output_file.name}")
    print("="*70)

if __name__ == '__main__':
    main()
