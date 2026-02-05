"""
patch_monster_stats.py
Patches monster stats in BLAZE.ALL only
(The BIN injection script will then copy BLAZE.ALL into the BIN)

Usage: py -3 patch_monster_stats.py
"""

import json
import struct
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"
JSON_DIR = SCRIPT_DIR

# Stats field order (offset from monster entry + 0x10)
# Must match inject_monster_stats.py STATS_ORDER
STATS_ORDER = [
    "exp_reward",           # 0  - 0x10
    "stat2",                # 1  - 0x12
    "hp",                   # 2  - 0x14
    "stat4_magic",          # 3  - 0x16
    "stat5_randomness",     # 4  - 0x18
    "stat6_collider_type",  # 5  - 0x1A
    "stat7_death_fx_size",  # 6  - 0x1C
    "stat8",                # 7  - 0x1E
    "stat9_collider_size",  # 8  - 0x20
    "stat10_drop_rate",     # 9  - 0x22
    "stat11_creature_type", # 10 - 0x24
    "stat12_armor_type",    # 11 - 0x26
    "stat13_elem_fire_ice", # 12 - 0x28
    "stat14_elem_poison_air", # 13 - 0x2A
    "stat15_elem_light_night", # 14 - 0x2C
    "stat16_elem_divine_malefic", # 15 - 0x2E
    "stat17_dmg",           # 16 - 0x30
    "stat18_armor",         # 17 - 0x32
    "stat19",               # 18 - 0x34
    "stat20",               # 19 - 0x36
    "stat21",               # 20 - 0x38
    "stat22_magic_atk",     # 21 - 0x3A
    "stat23",               # 22 - 0x3C
    "stat24",               # 23 - 0x3E
    "stat25",               # 24 - 0x40
    "stat26",               # 25 - 0x42
    "stat27",               # 26 - 0x44
    "stat28",               # 27 - 0x46
    "stat29",               # 28 - 0x48
    "stat30",               # 29 - 0x4A
    "stat31",               # 30 - 0x4C
    "stat32",               # 31 - 0x4E
    "stat33",               # 32 - 0x50
    "stat34",               # 33 - 0x52
    "stat35",               # 34 - 0x54
    "stat36",               # 35 - 0x56
    "stat37",               # 36 - 0x58
    "stat38",               # 37 - 0x5A
    "stat39",               # 38 - 0x5C
    "stat40",               # 39 - 0x5E
]


def patch_stats(data: bytearray, name_offset: int, stats: dict, name: str) -> bool:
    """Patch monster stats in data at given name offset"""
    stats_base = name_offset + 0x10

    for i, stat_name in enumerate(STATS_ORDER):
        if stat_name in stats:
            value = stats[stat_name]
            write_offset = stats_base + (i * 2)

            if write_offset + 2 > len(data):
                return False

            # Handle both negative and large positive values
            if value < 0:
                packed = struct.pack('<h', value)  # signed int16
            else:
                packed = struct.pack('<H', min(value, 65535))  # unsigned uint16, capped
            data[write_offset:write_offset+2] = packed

    return True


def find_all_occurrences(data: bytes, name: str) -> list:
    """Find all offsets where monster name appears"""
    search = name.encode('ascii')
    offsets = []
    pos = 0
    while True:
        pos = data.find(search, pos)
        if pos == -1:
            break

        # Check if substring of larger name
        if pos > 0:
            prev_char = data[pos-1]
            if (0x41 <= prev_char <= 0x5A) or (0x61 <= prev_char <= 0x7A) or prev_char == 0x2D:
                pos += 1
                continue

        # Verify proper monster entry
        entry = data[pos:pos+16]
        if b'\x00' in entry:
            actual_name = entry.split(b'\x00')[0].decode('ascii', errors='ignore')
            if actual_name == name:
                offsets.append(pos)
        pos += 1
    return offsets


def main():
    print("=" * 60)
    print("  Monster Stats BLAZE.ALL Patcher")
    print("=" * 60)
    print()

    # Read BLAZE.ALL
    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        return

    print(f"Reading {BLAZE_ALL}...")
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  Size: {len(blaze_data)} bytes")
    print()

    # Process JSON files
    json_files = [f for f in JSON_DIR.glob("**/*.json") if not f.name.startswith('_')]
    print(f"Processing {len(json_files)} monster files...")
    print()

    total_patched = 0

    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                monster = json.load(f)

            name = monster.get('name', json_file.stem)
            stats = monster.get('stats', {})

            # Find ALL occurrences
            offsets = find_all_occurrences(bytes(blaze_data), name)

            if not offsets:
                print(f"  WARNING: {name} - not found")
                continue

            # Patch at ALL locations
            for offset in offsets:
                patch_stats(blaze_data, offset, stats, name)

            total_patched += len(offsets)
            print(f"  {name}: patched {len(offsets)} occurrence{'s' if len(offsets) > 1 else ''}")

        except Exception as e:
            print(f"  ERROR: {json_file.name}: {e}")

    print()
    print(f"Patched {total_patched} total monster entries in BLAZE.ALL")
    print()

    # Write output
    print(f"Writing {BLAZE_ALL}...")
    BLAZE_ALL.write_bytes(blaze_data)

    print()
    print("=" * 60)
    print("  BLAZE.ALL patched successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
