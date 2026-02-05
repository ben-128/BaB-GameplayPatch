"""
analyze_sles.py - Analyze SLES_008.45 for class stats
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SLES_FILE = SCRIPT_DIR.parent.parent / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"

# Class names to search for
CLASS_NAMES = [
    b'Warrior', b'Priest', b'Sorcerer', b'Wizard', b'Rogue', b'Thief',
    b'Hunter', b'Ranger', b'Elf', b'Dwarf', b'Fairy'
]

# Stat names
STAT_NAMES = [b'STR', b'INT', b'WIL', b'AGL', b'CON', b'POW', b'LUK', b'LCK']


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def search_class_names(data: bytes):
    """Search for class name strings"""
    print("\n" + "=" * 70)
    print("CLASS NAME OCCURRENCES IN SLES_008.45")
    print("=" * 70)

    for name in CLASS_NAMES:
        pos = 0
        found = []
        while len(found) < 5:
            pos = data.find(name, pos)
            if pos == -1:
                break
            found.append(pos)
            pos += 1

        if found:
            print(f"\n'{name.decode()}':")
            for occ in found:
                ctx_start = max(0, occ - 16)
                ctx_end = min(len(data), occ + 32)
                print(f"  0x{occ:08X}:")
                print(hexdump(data[ctx_start:ctx_end], ctx_start))


def search_stat_tables(data: bytes):
    """Search for potential stat tables (8 classes x 7-9 stats)"""
    print("\n" + "=" * 70)
    print("SEARCHING FOR STAT TABLES")
    print("=" * 70)

    # Look for 8 consecutive small numbers that could be base stats
    # Typical stats: HP 40-100, MP 10-80, STR/INT/etc 8-25

    print("\nSearching for 8-value HP patterns (40-120 range)...")
    found_hp = []
    for offset in range(0, len(data) - 16, 2):
        values = [struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0] for i in range(8)]
        if all(40 <= v <= 120 for v in values):
            if len(set(values)) >= 5:  # Variety
                found_hp.append((offset, values))

    print(f"Found {len(found_hp)} potential HP tables")
    for offset, values in found_hp[:20]:
        print(f"  0x{offset:08X}: {values}")

    print("\nSearching for 8-value stat patterns (5-30 range)...")
    found_stats = []
    for offset in range(0, len(data) - 16, 1):  # byte-aligned
        values = list(data[offset:offset+8])
        if all(5 <= v <= 30 for v in values):
            if len(set(values)) >= 4:
                found_stats.append((offset, values))

    print(f"Found {len(found_stats)} potential stat patterns")
    for offset, values in found_stats[:30]:
        print(f"  0x{offset:08X}: {values}")
        # Show context
        ctx = data[max(0, offset-8):offset+24]
        print(f"    Context: {ctx.hex()}")


def search_level_tables(data: bytes):
    """Search for level progression tables"""
    print("\n" + "=" * 70)
    print("SEARCHING FOR LEVEL PROGRESSION TABLES")
    print("=" * 70)

    # XP tables: increasing uint32 values
    print("\nSearching for XP tables (uint32, increasing)...")
    for offset in range(0, len(data) - 200, 4):
        values = [struct.unpack('<I', data[offset + i*4:offset + i*4 + 4])[0] for i in range(50)]

        # Check if mostly increasing
        increases = sum(1 for i in range(49) if values[i] < values[i+1])
        if increases >= 45:
            # Check reasonable XP range
            if 50 <= values[0] <= 500 and 10000 <= values[49] <= 10000000:
                print(f"  0x{offset:08X}: {values[0]} -> {values[49]}")
                print(f"    First 10: {values[:10]}")


def search_growth_tables(data: bytes):
    """Search for stat growth per level"""
    print("\n" + "=" * 70)
    print("SEARCHING FOR GROWTH TABLES")
    print("=" * 70)

    # Growth tables might be small numbers (1-10) repeated for each stat/level
    print("\nSearching for growth patterns (bytes 1-10)...")
    found = []
    for offset in range(0, len(data) - 50):
        values = list(data[offset:offset+50])
        # Check if all values are small growth increments
        if all(0 <= v <= 10 for v in values):
            # Check for some variety
            if 2 <= len(set(values)) <= 8:
                # Not all zeros
                if sum(values) > 20:
                    found.append((offset, values[:20]))

    print(f"Found {len(found)} potential growth sequences")
    for offset, values in found[:20]:
        print(f"  0x{offset:08X}: {values}")


def analyze_near_strings(data: bytes):
    """Analyze data near class/stat strings"""
    print("\n" + "=" * 70)
    print("ANALYZING DATA NEAR CLASS STRINGS")
    print("=" * 70)

    # Find all class name occurrences and look at nearby data
    for name in [b'Warrior', b'Sorcerer', b'Priest', b'Dwarf']:
        pos = data.find(name)
        if pos != -1:
            print(f"\n{name.decode()} at 0x{pos:08X}:")

            # Look at 128 bytes before and after
            start = max(0, pos - 64)
            end = min(len(data), pos + 64)
            print(hexdump(data[start:end], start))

            # Look for nearby numeric patterns
            # Check if there's a pointer to this location
            ptr_bytes = struct.pack('<I', pos)
            ptr_pos = data.find(ptr_bytes)
            if ptr_pos != -1:
                print(f"  Pointer to this at 0x{ptr_pos:08X}")


def search_class_struct_patterns(data: bytes):
    """Search for structured class data blocks"""
    print("\n" + "=" * 70)
    print("SEARCHING FOR CLASS DATA STRUCTURES")
    print("=" * 70)

    # Look for 8 consecutive blocks of similar structure
    # Each class might have: HP, MP, STR, INT, WIL, AGL, CON, POW, LUK
    # That's 9 stats per class = 18 bytes (uint16) or 9 bytes (uint8)

    print("\nSearching for 8 x 9-byte class blocks...")
    for offset in range(0, len(data) - 72, 4):
        # Read 8 classes x 9 stats
        valid = True
        classes = []
        for c in range(8):
            stats = list(data[offset + c*9:offset + c*9 + 9])
            # Check if looks like stats
            if not all(5 <= s <= 100 for s in stats[:2]):  # HP/MP range
                valid = False
                break
            if not all(5 <= s <= 30 for s in stats[2:]):  # Other stats
                valid = False
                break
            classes.append(stats)

        if valid:
            print(f"\n  0x{offset:08X}:")
            for i, c in enumerate(classes):
                print(f"    Class {i+1}: HP={c[0]:3} MP={c[1]:3} | {c[2:9]}")

    print("\nSearching for 8 x 18-byte class blocks (uint16)...")
    for offset in range(0, len(data) - 144, 4):
        valid = True
        classes = []
        for c in range(8):
            base = offset + c*18
            stats = [struct.unpack('<H', data[base + i*2:base + i*2 + 2])[0] for i in range(9)]
            # Check ranges
            if not (30 <= stats[0] <= 150):  # HP
                valid = False
                break
            if not (10 <= stats[1] <= 100):  # MP
                valid = False
                break
            if not all(5 <= s <= 35 for s in stats[2:9]):  # Other stats
                valid = False
                break
            classes.append(stats)

        if valid:
            print(f"\n  0x{offset:08X}:")
            for i, c in enumerate(classes):
                print(f"    Class {i+1}: HP={c[0]:3} MP={c[1]:3} | {c[2:9]}")


def main():
    print("=" * 70)
    print("  SLES_008.45 Analyzer")
    print("=" * 70)

    if not SLES_FILE.exists():
        print(f"ERROR: {SLES_FILE} not found!")
        return

    print(f"Reading {SLES_FILE}...")
    data = SLES_FILE.read_bytes()
    print(f"File size: {len(data):,} bytes ({len(data)/1024:.1f} KB)")

    search_class_names(data)
    analyze_near_strings(data)
    search_stat_tables(data)
    search_class_struct_patterns(data)
    search_growth_tables(data)
    search_level_tables(data)


if __name__ == '__main__':
    main()
