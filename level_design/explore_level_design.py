"""
explore_level_design.py
Explores BLAZE.ALL for level design data

Usage: py -3 explore_level_design.py
"""

from pathlib import Path
import struct
import re

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def extract_strings(data, min_length=5):
    """Extract readable ASCII strings from binary data"""
    strings = []
    current = []

    for byte in data:
        if 32 <= byte <= 126:  # Printable ASCII
            current.append(chr(byte))
        else:
            if len(current) >= min_length:
                strings.append(''.join(current))
            current = []

    if len(current) >= min_length:
        strings.append(''.join(current))

    return strings

def search_level_keywords(strings):
    """Search for level-related keywords"""
    keywords = [
        'level', 'stage', 'map', 'dungeon', 'floor', 'zone', 'area',
        'room', 'chamber', 'castle', 'town', 'village', 'forest',
        'cave', 'mountain', 'temple', 'tower', 'gate', 'ruins',
        'spawn', 'enemy', 'monster', 'boss', 'chest', 'treasure',
        'door', 'portal', 'exit', 'entrance'
    ]

    results = {}
    for keyword in keywords:
        matches = [s for s in strings if keyword.lower() in s.lower()]
        if matches:
            results[keyword] = matches

    return results

def find_coordinate_patterns(data):
    """Look for potential coordinate data (int16 triplets that could be x,y,z)"""
    candidates = []

    # Search for patterns that look like coordinates
    # Looking for sequences of 6 bytes (3 int16) within reasonable ranges
    for i in range(0, len(data) - 6, 2):
        try:
            x = struct.unpack_from('<h', data, i)[0]
            y = struct.unpack_from('<h', data, i+2)[0]
            z = struct.unpack_from('<h', data, i+4)[0]

            # Reasonable coordinate ranges (adjust based on game)
            if all(-10000 < coord < 10000 for coord in [x, y, z]):
                # Look for multiple similar patterns nearby (table of positions)
                if i > 0 and i % 100 == 0:  # Sample every 100 offsets
                    candidates.append({
                        'offset': hex(i),
                        'x': x, 'y': y, 'z': z
                    })
        except:
            pass

    return candidates[:50]  # Return first 50 candidates

def analyze_file_structure(data):
    """Analyze general structure of the file"""
    size = len(data)

    # Look for repeated patterns that might indicate data tables
    # Check for common PlayStation PSX data signatures

    print(f"File size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
    print(f"\nFirst 64 bytes (hex): {data[:64].hex()}")

    # Check for PSX TIM image format markers
    tim_markers = []
    for i in range(0, size - 4, 4):
        if data[i:i+4] == b'\x10\x00\x00\x00':
            tim_markers.append(hex(i))

    print(f"\nPSX TIM image markers found: {len(tim_markers)}")
    if tim_markers[:10]:
        print(f"  First 10 locations: {', '.join(tim_markers[:10])}")

    # Look for potential data tables (repeated byte patterns)
    print(f"\n\nLooking for repeated structures...")

    # Sample different offsets for structure analysis
    sample_offsets = [
        0x100000,  # 1MB
        0x200000,  # 2MB
        0x500000,  # 5MB
        0x800000,  # 8MB
        0xA00000,  # 10MB
        0x1000000, # 16MB
        0x2000000, # 32MB
    ]

    for offset in sample_offsets:
        if offset < size:
            sample = data[offset:offset+64]
            # Check if it's not padding
            if not all(b == 0xCC or b == 0x00 for b in sample):
                print(f"\n  Offset {hex(offset)}: {sample[:32].hex()}")

def main():
    print("=" * 60)
    print("  LEVEL DESIGN EXPLORER")
    print("=" * 60)
    print()

    print(f"Reading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes\n")

    # Step 1: Analyze file structure
    print("\n[1] FILE STRUCTURE ANALYSIS")
    print("-" * 60)
    analyze_file_structure(data)

    # Step 2: Extract strings
    print("\n\n[2] STRING EXTRACTION")
    print("-" * 60)
    print("Extracting ASCII strings (min length 5)...")
    strings = extract_strings(data, min_length=5)
    print(f"Found {len(strings)} strings")

    # Step 3: Search for level-related keywords
    print("\n\n[3] LEVEL-RELATED KEYWORDS")
    print("-" * 60)
    keyword_results = search_level_keywords(strings)

    if keyword_results:
        for keyword, matches in sorted(keyword_results.items()):
            print(f"\n'{keyword}' ({len(matches)} matches):")
            for match in matches[:10]:  # Show first 10
                print(f"  - {match}")
            if len(matches) > 10:
                print(f"  ... and {len(matches) - 10} more")
    else:
        print("No obvious level-related keywords found")

    # Step 4: Look for coordinate patterns
    print("\n\n[4] COORDINATE PATTERN ANALYSIS")
    print("-" * 60)
    print("Searching for potential coordinate data (x,y,z triplets)...")
    coords = find_coordinate_patterns(data)

    if coords:
        print(f"\nFound {len(coords)} candidate coordinate patterns:")
        for c in coords[:20]:  # Show first 20
            print(f"  Offset {c['offset']}: ({c['x']}, {c['y']}, {c['z']})")

    # Step 5: Sample interesting strings
    print("\n\n[5] INTERESTING STRINGS SAMPLE")
    print("-" * 60)
    interesting = [s for s in strings if len(s) >= 8 and not s.startswith('\\')]
    print(f"Showing 50 interesting strings (length >= 8):")
    for s in interesting[:50]:
        print(f"  {s}")

    print("\n\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
