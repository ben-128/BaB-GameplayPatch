"""
analyze_class_stats.py
Analyze BLAZE.ALL around class name offsets to find stat structures

Usage: py -3 analyze_class_stats.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

# Known class name offsets from research
CLASS_OFFSETS = {
    "Warrior": 0x0090B6E8,
    "Priest": 0x0090B6F8,
    "Rogue": 0x0090B708,
    "Sorcerer": 0x0090B718,
    "Hunter": 0x0090B728,
    "Elf": 0x0090B738,
    "Dwarf": 0x0090B748,
    "Fairy": 0x0090B758,
}

# Monster-style stats layout (for reference)
STATS_LAYOUT = [
    (0x10, "exp_reward"),
    (0x12, "stat2"),
    (0x14, "hp"),
    (0x16, "mp/magic"),
    (0x18, "randomness"),
    (0x1A, "collider_type"),
    (0x1C, "death_fx_size"),
    (0x1E, "stat8"),
    (0x20, "collider_size"),
    (0x22, "drop_rate"),
    (0x24, "creature_type"),
    (0x26, "armor_type"),
    (0x28, "elem_fire_ice"),
    (0x2A, "elem_poison_air"),
    (0x2C, "elem_light_night"),
    (0x2E, "elem_divine_malefic"),
    (0x30, "damage"),
    (0x32, "armor/defense"),
    (0x34, "stat19"),
    (0x36, "stat20"),
    (0x38, "stat21"),
    (0x3A, "magic_atk"),
]


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    """Create a hex dump with ASCII view"""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def read_uint16_le(data: bytes, offset: int) -> int:
    """Read uint16 little-endian"""
    return struct.unpack('<H', data[offset:offset+2])[0]


def analyze_class_area(data: bytes, name: str, offset: int, output_file):
    """Analyze data around a class name offset"""
    output_file.write(f"\n{'='*70}\n")
    output_file.write(f"CLASS: {name} @ 0x{offset:08X}\n")
    output_file.write(f"{'='*70}\n")

    # Read 256 bytes before and after
    start = max(0, offset - 64)
    end = min(len(data), offset + 192)
    chunk = data[start:end]

    # Show hex dump
    output_file.write(f"\nHex dump (offset - 64 to offset + 192):\n")
    output_file.write(hexdump(chunk, start) + "\n")

    # Try to read as monster-style stats (offset + 0x10)
    output_file.write(f"\nIf monster-style stats at +0x10:\n")
    for stat_offset, stat_name in STATS_LAYOUT:
        abs_offset = offset + stat_offset
        if abs_offset + 2 <= len(data):
            value = read_uint16_le(data, abs_offset)
            output_file.write(f"  +0x{stat_offset:02X} ({stat_name:20}): {value:5} (0x{value:04X})\n")

    # Look for small number patterns (typical stats: 1-255)
    output_file.write(f"\nSmall numbers (1-255) in range:\n")
    small_nums = []
    for i in range(0, min(128, end - offset), 2):
        val = read_uint16_le(data, offset + i)
        if 1 <= val <= 255:
            small_nums.append((i, val))
    for off, val in small_nums[:20]:
        output_file.write(f"  +0x{off:02X}: {val}\n")


def search_stat_tables(data: bytes, output_file):
    """Search for potential stat growth tables"""
    output_file.write(f"\n{'='*70}\n")
    output_file.write("SEARCHING FOR STAT GROWTH TABLES\n")
    output_file.write(f"{'='*70}\n")

    # Search for sequences of 8 similar small numbers (one per class)
    # Common stat ranges: HP 50-150, MP 20-80, Stats 10-30

    output_file.write("\nLooking for 8-value sequences (potential class stats)...\n")

    found_patterns = []
    for i in range(0, len(data) - 16, 2):
        values = [read_uint16_le(data, i + j*2) for j in range(8)]

        # Check if all values are in reasonable stat range
        if all(10 <= v <= 200 for v in values):
            # Check for variety (not all same value)
            if len(set(values)) >= 3:
                avg = sum(values) / 8
                # Check if values are reasonably clustered
                if all(abs(v - avg) < 100 for v in values):
                    found_patterns.append((i, values))

    # Show first 50 matches
    output_file.write(f"Found {len(found_patterns)} potential 8-class stat sequences\n\n")
    for offset, values in found_patterns[:50]:
        output_file.write(f"  0x{offset:08X}: {values}\n")


def search_xp_tables(data: bytes, output_file):
    """Search for XP progression tables"""
    output_file.write(f"\n{'='*70}\n")
    output_file.write("SEARCHING FOR XP PROGRESSION TABLES\n")
    output_file.write(f"{'='*70}\n")

    # XP tables typically have increasing values
    # Level 1-50 with exponential growth

    found_tables = []
    for i in range(0, len(data) - 100, 4):
        # Try uint32 values
        values = [struct.unpack('<I', data[i + j*4:i + j*4 + 4])[0] for j in range(10)]

        # Check for strictly increasing sequence
        if all(values[j] < values[j+1] for j in range(9)):
            # Check reasonable XP range (100 to 1000000)
            if 100 <= values[0] <= 5000 and values[9] <= 5000000:
                found_tables.append((i, values))

    output_file.write(f"Found {len(found_tables)} potential XP tables (uint32, 10+ levels)\n\n")
    for offset, values in found_tables[:20]:
        output_file.write(f"  0x{offset:08X}: {values}\n")


def search_level_growth(data: bytes, output_file):
    """Search for level-based growth patterns"""
    output_file.write(f"\n{'='*70}\n")
    output_file.write("SEARCHING FOR LEVEL GROWTH PATTERNS\n")
    output_file.write(f"{'='*70}\n")

    # Growth tables might be small increments (1-10 per level)
    found = []
    for i in range(0, len(data) - 100, 1):
        # Look for sequences of small positive numbers
        values = list(data[i:i+20])

        # Check if mostly small positive numbers (1-15)
        if all(1 <= v <= 15 for v in values):
            # Not all the same
            if len(set(values)) >= 3:
                found.append((i, values))

    output_file.write(f"Found {len(found)} potential growth sequences (bytes 1-15)\n\n")
    for offset, values in found[:30]:
        output_file.write(f"  0x{offset:08X}: {values}\n")


def main():
    print("=" * 60)
    print("  Class Stats Analyzer")
    print("=" * 60)

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        print("Make sure to extract BLAZE.ALL to the output folder first.")
        return

    print(f"Reading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"  Size: {len(data):,} bytes")

    output_path = SCRIPT_DIR / "CLASS_STATS_ANALYSIS.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("CLASS STATS ANALYSIS - BLAZE.ALL\n")
        f.write(f"File size: {len(data):,} bytes\n")
        f.write(f"Generated by analyze_class_stats.py\n")

        # Analyze each class offset
        for name, offset in CLASS_OFFSETS.items():
            print(f"  Analyzing {name}...")
            analyze_class_area(data, name, offset, f)

        # Search for stat tables
        print("  Searching for stat tables...")
        search_stat_tables(data, f)

        # Search for XP tables
        print("  Searching for XP tables...")
        search_xp_tables(data, f)

        # Search for growth patterns
        print("  Searching for growth patterns...")
        search_level_growth(data, f)

    print()
    print(f"Analysis saved to: {output_path}")
    print()


if __name__ == '__main__':
    main()
