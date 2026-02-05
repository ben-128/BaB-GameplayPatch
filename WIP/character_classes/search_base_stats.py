"""
search_base_stats.py
Search for base stats patterns using known game values
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

# Expected starting stats from typical RPG/Blaze & Blade
# Warrior: High HP/STR, low INT/WIL
# Sorcerer: Low HP/STR, high INT/WIL
# Etc.

# Known typical starting values (estimates to search for)
EXPECTED_HP_RANGE = (40, 120)  # Starting HP range
EXPECTED_MP_RANGE = (10, 80)   # Starting MP range


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def search_8_class_hp_patterns(data: bytes):
    """Search for 8 uint16 values that look like starting HP for 8 classes"""
    print("Searching for 8-class HP patterns (40-120 range)...")

    found = []
    for offset in range(0, len(data) - 16, 2):
        values = [struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0] for i in range(8)]

        # All values in HP range
        if all(40 <= v <= 120 for v in values):
            # Good variety (classes have different HP)
            if len(set(values)) >= 5:
                # Warrior-like class should have highest, caster lowest
                found.append((offset, values))

    print(f"Found {len(found)} potential HP patterns")
    for offset, values in found[:30]:
        print(f"  0x{offset:08X}: {values}")
        # Show context
        if offset >= 16:
            context = data[offset-16:offset+32]
            print(f"    Context: {context[:16].hex()} | {context[16:32].hex()}")


def search_stat_blocks(data: bytes):
    """Search for blocks of 7 stats (STR, INT, WIL, AGL, CON, POW, LUK)"""
    print("\nSearching for 7-stat blocks per class (8 classes x 7 stats = 56 bytes)...")

    # Look for 56-byte structures with reasonable stat values
    found = []
    for offset in range(0, len(data) - 56, 2):
        # Read 8 classes x 7 stats
        values = []
        valid = True
        for cls in range(8):
            cls_stats = []
            for stat in range(7):
                idx = offset + (cls * 14) + (stat * 2)
                if idx + 2 > len(data):
                    valid = False
                    break
                val = struct.unpack('<H', data[idx:idx+2])[0]
                if not (5 <= val <= 50):  # Typical stat range
                    valid = False
                    break
                cls_stats.append(val)
            if not valid:
                break
            values.append(cls_stats)

        if valid and len(values) == 8:
            # Check for variety
            all_stats = [s for cls in values for s in cls]
            if len(set(all_stats)) >= 10:
                found.append((offset, values))

    print(f"Found {len(found)} potential stat blocks")
    for offset, values in found[:10]:
        print(f"  0x{offset:08X}:")
        for i, cls in enumerate(values):
            print(f"    Class {i+1}: {cls}")


def search_level_tables(data: bytes):
    """Search for level progression tables (50 levels)"""
    print("\nSearching for 50-level progression tables...")

    # Look for 50 increasing uint16 values
    found = []
    for offset in range(0, len(data) - 100, 2):
        values = [struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0] for i in range(50)]

        # Check for mostly increasing pattern
        increases = sum(1 for i in range(49) if values[i] < values[i+1])
        if increases >= 45:  # At least 45 increases
            # Check reasonable progression (HP: 50 -> 500, stats: 10 -> 100)
            if 20 <= values[0] <= 100 and 100 <= values[49] <= 1000:
                found.append((offset, values[0], values[49], values))

    print(f"Found {len(found)} potential level tables")
    for offset, start, end, values in found[:20]:
        print(f"  0x{offset:08X}: {start} -> {end}")
        print(f"    Every 10 levels: {[values[i] for i in range(0, 50, 10)]}")


def search_around_class_names(data: bytes):
    """Search in a wider area around class names"""
    print("\nSearching wider area around class names...")

    # Class names end around 0x0090B7C8
    # Check if there's any referenced data structure
    CLASS_ZONE_END = 0x0090B7C8

    # Look for pointers in the class name area that might reference stat tables
    print(f"\nLooking for pointers near class names:")
    for offset in range(0x0090B6E0, 0x0090B800, 4):
        if offset + 4 <= len(data):
            ptr = struct.unpack('<I', data[offset:offset+4])[0]
            # Check if pointer is in reasonable range (BLAZE.ALL is 46MB)
            if 0x00100000 <= ptr <= 0x02C00000:
                # Check if target looks like stat data
                if ptr < len(data):
                    target_sample = [data[ptr + i] for i in range(16) if ptr + i < len(data)]
                    if all(0 <= v <= 100 for v in target_sample):
                        print(f"  0x{offset:08X} -> 0x{ptr:08X}: {target_sample}")


def search_string_references(data: bytes):
    """Search for stat-related strings"""
    print("\nSearching for stat-related strings...")

    strings_to_find = [
        b'Strength', b'STR', b'Intelligence', b'INT', b'Willpower', b'WIL',
        b'Agility', b'AGL', b'Constitution', b'CON', b'Power', b'POW',
        b'Luck', b'LUK', b'Attack', b'Defense', b'Magic',
        b'Experience', b'EXP', b'Level', b'LV', b'HP', b'MP',
        b'Hit Points', b'Mana', b'Growth', b'Progression',
    ]

    for s in strings_to_find:
        pos = data.find(s)
        if pos != -1:
            # Get context
            start = max(0, pos - 20)
            end = min(len(data), pos + len(s) + 40)
            context = data[start:end]
            print(f"  '{s.decode()}' at 0x{pos:08X}")
            # Show nearby hex
            print(f"    {hexdump(context, start)}")


def main():
    print("=" * 60)
    print("  Base Stats Search")
    print("=" * 60)

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        return

    data = BLAZE_ALL.read_bytes()
    print(f"File size: {len(data):,} bytes")

    search_8_class_hp_patterns(data)
    search_stat_blocks(data)
    search_level_tables(data)
    search_around_class_names(data)
    search_string_references(data)


if __name__ == '__main__':
    main()
