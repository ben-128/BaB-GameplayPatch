"""
deep_structure_analysis.py
Deep analysis of binary structures in identified zones

Usage: py -3 deep_structure_analysis.py
"""

from pathlib import Path
import struct

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def analyze_coordinates_in_zone(data, start_offset, size, struct_size):
    """
    Analyze a zone for 3D coordinate patterns
    Looks for (x, y, z) triplets that could be positions
    """
    candidates = []

    for i in range(start_offset, start_offset + size - struct_size, struct_size):
        chunk = data[i:i+struct_size]

        # Skip all-zero or all-0xFF chunks
        if all(b == 0 for b in chunk) or all(b == 0xFF for b in chunk):
            continue

        # Try to parse as coordinate data
        # PSX typically uses int16 for fixed-point coordinates
        try:
            # Parse first 3 int16 as potential x, y, z
            x = struct.unpack_from('<h', chunk, 0)[0]
            y = struct.unpack_from('<h', chunk, 2)[0]
            z = struct.unpack_from('<h', chunk, 4)[0]

            # Check if values are in reasonable ranges for game coordinates
            # PSX games typically use ranges like -8192 to 8192 for world coords
            if all(-8192 <= coord <= 8192 for coord in [x, y, z]):
                # Parse additional data that might be in the structure
                values = []
                for j in range(0, min(struct_size, 32), 2):
                    v = struct.unpack_from('<h', chunk, j)[0]
                    values.append(v)

                candidates.append({
                    'offset': hex(i),
                    'x': x, 'y': y, 'z': z,
                    'all_values': values,
                    'hex': chunk[:min(32, struct_size)].hex()
                })
        except:
            pass

    return candidates

def find_table_structures(data, start_offset, size, min_entries=5):
    """
    Look for table-like structures with repeated patterns
    """
    results = []

    # Try different struct sizes
    for struct_size in [8, 12, 16, 20, 24, 28, 32, 40, 48, 64]:
        entries = []

        for i in range(start_offset, start_offset + size - struct_size * min_entries, struct_size):
            # Check if we have at least min_entries similar structures
            similar_count = 0

            for j in range(min_entries):
                offset = i + j * struct_size
                if offset + struct_size > start_offset + size:
                    break

                chunk = data[offset:offset+struct_size]

                # Skip padding
                if all(b == 0 for b in chunk) or all(b == 0xCC for b in chunk):
                    break

                similar_count += 1

            if similar_count >= min_entries:
                # Found a potential table
                table_entries = []
                for j in range(similar_count):
                    offset = i + j * struct_size
                    chunk = data[offset:offset+struct_size]

                    # Parse as int16 array
                    values = []
                    for k in range(0, struct_size, 2):
                        try:
                            v = struct.unpack_from('<h', chunk, k)[0]
                            values.append(v)
                        except:
                            break

                    table_entries.append({
                        'offset': hex(offset),
                        'values': values,
                        'hex': chunk.hex()
                    })

                results.append({
                    'table_start': hex(i),
                    'struct_size': struct_size,
                    'entry_count': similar_count,
                    'entries': table_entries[:10]  # First 10 entries
                })

                # Skip ahead to avoid overlapping detections
                break

        if len(results) >= 10:  # Limit results
            break

    return results

def analyze_specific_offset(data, offset, context=256):
    """
    Detailed analysis of a specific offset
    """
    start = max(0, offset - context)
    end = min(len(data), offset + context)
    chunk = data[start:end]

    # Multiple interpretations
    analysis = {
        'offset': hex(offset),
        'hex_dump': chunk.hex()[:128],  # First 64 bytes
        'ascii': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk[:64])
    }

    # As int16 array
    int16_array = []
    for i in range(0, min(64, len(chunk)), 2):
        try:
            v = struct.unpack_from('<h', chunk, i)[0]
            int16_array.append(v)
        except:
            break
    analysis['int16_array'] = int16_array

    # As uint16 array
    uint16_array = []
    for i in range(0, min(64, len(chunk)), 2):
        try:
            v = struct.unpack_from('<H', chunk, i)[0]
            uint16_array.append(v)
        except:
            break
    analysis['uint16_array'] = uint16_array

    # As int32 array
    int32_array = []
    for i in range(0, min(64, len(chunk)), 4):
        try:
            v = struct.unpack_from('<i', chunk, i)[0]
            int32_array.append(v)
        except:
            break
    analysis['int32_array'] = int32_array

    # As float array (PSX doesn't use floats much, but worth checking)
    float_array = []
    for i in range(0, min(64, len(chunk)), 4):
        try:
            v = struct.unpack_from('<f', chunk, i)[0]
            # Only include if reasonable
            if -10000 < v < 10000:
                float_array.append(round(v, 3))
        except:
            break
    analysis['float_array'] = float_array[:16]

    return analysis

def main():
    print("=" * 70)
    print("  DEEP STRUCTURE ANALYSIS")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Analyze specific interesting zones
    zones = [
        (0x100000, 0x10000, "Zone 1MB"),
        (0x200000, 0x10000, "Zone 2MB"),
        (0x300000, 0x10000, "Zone 3MB"),
        (0x500000, 0x10000, "Zone 5MB"),
        (0x800000, 0x10000, "Zone 8MB"),
        (0x900000, 0x10000, "Zone 9MB"),
    ]

    print("\n[1] COORDINATE PATTERN ANALYSIS")
    print("-" * 70)

    for start, size, name in zones:
        if start + size > len(data):
            continue

        print(f"\nAnalyzing {name} ({hex(start)})...")

        for struct_size in [16, 20, 24, 32]:
            coords = analyze_coordinates_in_zone(data, start, size, struct_size)
            if coords:
                print(f"  {struct_size}-byte structures: {len(coords)} coordinate candidates")

                # Show first 5
                for coord in coords[:5]:
                    print(f"    {coord['offset']}: ({coord['x']}, {coord['y']}, {coord['z']})")
                    print(f"      Values: {coord['all_values'][:8]}")

    print("\n[2] TABLE STRUCTURE DETECTION")
    print("-" * 70)

    for start, size, name in zones:
        if start + size > len(data):
            continue

        print(f"\nSearching for tables in {name}...")
        tables = find_table_structures(data, start, size)

        if tables:
            print(f"  Found {len(tables)} potential tables:")
            for table in tables[:3]:  # Show first 3
                print(f"    Table at {table['table_start']}: {table['entry_count']} x {table['struct_size']}-byte entries")
                print(f"      First entry values: {table['entries'][0]['values'][:8]}")

    print("\n[3] SPECIFIC OFFSET ANALYSIS")
    print("-" * 70)

    # Analyze offsets near known level names
    interesting_offsets = [
        0x907AD9,   # Near "The Mountain of the Fire Dragon"
        0x907AFD,   # Near "The Wood of Ruins"
        0x907B5D,   # Near "The Ancient Ruins"
        0x240AD14,  # "Castle Of Vamp 02"
    ]

    print("\nAnalyzing offsets near level names...")
    for offset in interesting_offsets:
        if offset < len(data):
            print(f"\nOffset {hex(offset)}:")
            analysis = analyze_specific_offset(data, offset, 128)
            print(f"  ASCII: {analysis['ascii']}")
            print(f"  Int16:  {analysis['int16_array'][:12]}")
            print(f"  Uint16: {analysis['uint16_array'][:12]}")

    print("\n[4] PATTERN DETECTION: MONSTER IDs")
    print("-" * 70)

    # Look for patterns that match known data structures
    # Monster stats structure is known (40 values per monster)
    print("\nSearching for 40-value structures (monster-like)...")

    for start, size, name in zones[:3]:  # Check first 3 zones
        if start + size > len(data):
            continue

        found = 0
        for i in range(start, start + size - 80, 2):
            # Check for 40 int16 values
            chunk = data[i:i+80]

            # Skip padding
            if all(b == 0 for b in chunk) or all(b == 0xCC for b in chunk):
                continue

            # Parse as int16
            values = []
            for j in range(0, 80, 2):
                try:
                    v = struct.unpack_from('<h', chunk, j)[0]
                    values.append(v)
                except:
                    break

            if len(values) == 40:
                # Check if first value looks like HP (100-9999)
                if 100 <= values[0] <= 9999:
                    found += 1
                    if found <= 3:  # Show first 3
                        print(f"  {hex(i)}: HP={values[0]}, possible monster: {values[:8]}")

        if found > 0:
            print(f"  Total candidates in {name}: {found}")

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nRecommendations:")
    print("1. Coordinate patterns found - investigate for spawn points")
    print("2. Table structures detected - may contain level data")
    print("3. Check specific offsets near level names for metadata")
    print("="*70)

if __name__ == '__main__':
    main()
