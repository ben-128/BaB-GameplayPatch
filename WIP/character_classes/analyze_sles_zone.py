"""
analyze_sles_zone.py - Detailed analysis of promising SLES zones
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SLES_FILE = SCRIPT_DIR.parent.parent / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def analyze_zone_as_class_stats(data: bytes, start: int, num_classes: int = 8):
    """Try to interpret a zone as class stat blocks"""
    print(f"\n=== Analyzing 0x{start:08X} as class stats ===\n")

    # Try different interpretations

    # 1. 8 bytes per class (8 stats, 1 byte each)
    print("Interpretation 1: 8 bytes per class (8 x uint8 stats)")
    print("Class    | S1  S2  S3  S4  S5  S6  S7  S8")
    print("-" * 50)
    for c in range(num_classes):
        stats = list(data[start + c*8:start + c*8 + 8])
        print(f"Class {c+1}  | {stats}")

    # 2. 9 bytes per class
    print("\nInterpretation 2: 9 bytes per class (9 x uint8 stats)")
    print("Class    | HP  MP  ST  IN  WI  AG  CO  PO  LK")
    print("-" * 60)
    for c in range(num_classes):
        stats = list(data[start + c*9:start + c*9 + 9])
        print(f"Class {c+1}  | {stats}")

    # 3. 16 bytes per class (8 x uint16)
    print("\nInterpretation 3: 16 bytes per class (8 x uint16 stats)")
    print("Class    | S1    S2    S3    S4    S5    S6    S7    S8")
    print("-" * 70)
    for c in range(num_classes):
        base = start + c*16
        stats = [struct.unpack('<H', data[base + i*2:base + i*2 + 2])[0] for i in range(8)]
        print(f"Class {c+1}  | {stats}")


def main():
    print("=" * 70)
    print("  SLES Zone Analyzer")
    print("=" * 70)

    data = SLES_FILE.read_bytes()
    print(f"File size: {len(data):,} bytes")

    # Zone 1: 0x0002BBA0 - Stat-like patterns found here
    print("\n" + "=" * 70)
    print("ZONE 0x0002BB00 - 0x0002BD00 (Potential stat zone)")
    print("=" * 70)
    print(hexdump(data[0x0002BB00:0x0002BD00], 0x0002BB00))

    analyze_zone_as_class_stats(data, 0x0002BBA8)
    analyze_zone_as_class_stats(data, 0x0002BBD0)
    analyze_zone_as_class_stats(data, 0x0002BC00)

    # Zone 2: 0x0002EA00 - HP progression patterns
    print("\n" + "=" * 70)
    print("ZONE 0x0002EA00 - 0x0002EC00 (HP progression?)")
    print("=" * 70)
    print(hexdump(data[0x0002EA00:0x0002EC00], 0x0002EA00))

    # Zone 3: 0x00033600 - More HP patterns
    print("\n" + "=" * 70)
    print("ZONE 0x00033600 - 0x00033800 (Level tables?)")
    print("=" * 70)
    print(hexdump(data[0x00033600:0x00033800], 0x00033600))

    # Show as uint16 level progression
    print("\nAs uint16 level values (from 0x00033664):")
    start = 0x00033664
    values = [struct.unpack('<H', data[start + i*2:start + i*2 + 2])[0] for i in range(50)]
    for i in range(0, 50, 10):
        print(f"  Lv{i+1:2}-{i+10:2}: {values[i:i+10]}")

    # Zone 4: 0x0002C700 - More data
    print("\n" + "=" * 70)
    print("ZONE 0x0002C700 - 0x0002C900 (More data)")
    print("=" * 70)
    print(hexdump(data[0x0002C700:0x0002C900], 0x0002C700))

    # Specific pattern at 0x0002C820
    print("\nData at 0x0002C820:")
    start = 0x0002C820
    for i in range(10):
        values = list(data[start + i*8:start + i*8 + 8])
        print(f"  +{i*8:02X}: {values}")

    # Search for 8-class patterns more specifically
    print("\n" + "=" * 70)
    print("SEARCHING FOR 8-CLASS BASE STAT PATTERNS")
    print("=" * 70)

    # Expected patterns for 8 classes:
    # Warrior: high STR/CON, low INT
    # Sorcerer: high INT/POW, low STR
    # etc.

    print("\nLooking for 8 values where some are high (15-25) and some low (5-12)...")
    for offset in range(0, len(data) - 8):
        values = list(data[offset:offset+8])
        high_count = sum(1 for v in values if 15 <= v <= 30)
        low_count = sum(1 for v in values if 5 <= v <= 12)

        # Should have mix of high and low
        if high_count >= 2 and low_count >= 2 and high_count + low_count >= 6:
            # Check all values are in stat range
            if all(5 <= v <= 30 for v in values):
                if len(set(values)) >= 5:  # Good variety
                    print(f"  0x{offset:08X}: {values}")
                    # Show context
                    if offset >= 8:
                        prev = list(data[offset-8:offset])
                        next8 = list(data[offset+8:offset+16])
                        print(f"    Before: {prev}")
                        print(f"    After:  {next8}")


if __name__ == '__main__':
    main()
