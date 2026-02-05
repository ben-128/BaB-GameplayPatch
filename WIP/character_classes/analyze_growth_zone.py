"""
analyze_growth_zone.py
Detailed analysis of the zone around 0x00203000 which contains
potential stat/growth data
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def analyze_as_bytes(data: bytes, start: int, count: int = 100):
    """Analyze as individual bytes"""
    print(f"\nBytes from 0x{start:08X}:")
    values = list(data[start:start+count])
    for i in range(0, len(values), 10):
        chunk = values[i:i+10]
        print(f"  +{i:3}: {chunk}")


def analyze_as_uint16(data: bytes, start: int, count: int = 50):
    """Analyze as uint16 values"""
    print(f"\nuint16 from 0x{start:08X}:")
    values = []
    for i in range(count):
        offset = start + i * 2
        if offset + 2 <= len(data):
            val = struct.unpack('<H', data[offset:offset+2])[0]
            values.append(val)

    for i in range(0, len(values), 8):
        chunk = values[i:i+8]
        print(f"  +{i*2:3}: {chunk}")


def find_8_class_patterns(data: bytes, start: int, length: int):
    """Look for patterns of 8 values (one per class)"""
    print(f"\n8-value class patterns in range 0x{start:08X} - 0x{start+length:08X}:")

    # Try byte patterns
    print("\n  As bytes (8 consecutive):")
    for offset in range(start, start + length - 8):
        values = list(data[offset:offset+8])
        # Look for reasonable stat values (10-100)
        if all(10 <= v <= 100 for v in values):
            if len(set(values)) >= 4:  # Some variety
                print(f"    0x{offset:08X}: {values}")

    # Try uint16 patterns
    print("\n  As uint16 (8 consecutive):")
    for offset in range(start, start + length - 16, 2):
        values = [struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0] for i in range(8)]
        # Look for HP/MP like values (20-200)
        if all(20 <= v <= 200 for v in values):
            if len(set(values)) >= 4:
                print(f"    0x{offset:08X}: {values}")


def find_level_progressions(data: bytes, start: int, length: int):
    """Look for level progression patterns (50 levels, increasing values)"""
    print(f"\nLevel progression patterns in range 0x{start:08X}:")

    # Look for sequences of increasing uint16 values
    for offset in range(start, start + length - 100, 2):
        values = [struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0] for i in range(50)]

        # Check if mostly increasing
        increasing_count = sum(1 for i in range(49) if values[i] < values[i+1])

        if increasing_count >= 40:  # At least 40 increases out of 49
            # Check reasonable range
            if 50 <= values[0] <= 200 and 200 <= values[49] <= 2000:
                print(f"  0x{offset:08X}: start={values[0]}, end={values[49]}")
                print(f"    First 10: {values[:10]}")
                print(f"    Last 10: {values[-10:]}")


def main():
    print("=" * 60)
    print("  Growth Zone Analyzer")
    print("=" * 60)

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        return

    data = BLAZE_ALL.read_bytes()
    print(f"File size: {len(data):,} bytes")

    # Zone discovered in previous analysis
    ZONE_START = 0x00203000
    ZONE_LENGTH = 0x2000  # 8KB to analyze

    print(f"\n{'='*60}")
    print(f"Analyzing zone 0x{ZONE_START:08X} - 0x{ZONE_START + ZONE_LENGTH:08X}")
    print(f"{'='*60}")

    # Hex dump of first 512 bytes
    print("\nHex dump (first 512 bytes of zone):")
    print(hexdump(data[ZONE_START:ZONE_START+512], ZONE_START))

    # Analyze specific offsets from previous findings
    interesting_offsets = [
        0x00203086,  # First pattern found
        0x002030C2,  # Another pattern
    ]

    for offset in interesting_offsets:
        print(f"\n{'='*60}")
        print(f"Detail at 0x{offset:08X}")
        print(f"{'='*60}")
        analyze_as_bytes(data, offset, 64)
        analyze_as_uint16(data, offset, 32)

    # Search for 8-class patterns
    find_8_class_patterns(data, ZONE_START, ZONE_LENGTH)

    # Search for level progressions
    find_level_progressions(data, ZONE_START, ZONE_LENGTH)

    # Also check near the class names area
    print(f"\n{'='*60}")
    print(f"Checking zone after class names (0x0090B7D0)")
    print(f"{'='*60}")

    CLASS_END = 0x0090B7D0
    print(hexdump(data[CLASS_END:CLASS_END+256], CLASS_END))

    # Search for "level" or similar keywords
    print(f"\n{'='*60}")
    print("Searching for level-related strings...")
    print(f"{'='*60}")

    keywords = [b'Level', b'Lv', b'Exp', b'HP', b'MP', b'Str', b'Int', b'Wil', b'Agl', b'Con', b'Pow']
    for keyword in keywords:
        pos = 0
        found = []
        while True:
            pos = data.find(keyword, pos)
            if pos == -1:
                break
            found.append(pos)
            pos += 1
        if found:
            print(f"  '{keyword.decode()}': {len(found)} occurrences")
            if len(found) <= 10:
                for offset in found:
                    context = data[max(0, offset-10):offset+len(keyword)+20]
                    print(f"    0x{offset:08X}: {context}")


if __name__ == '__main__':
    main()
