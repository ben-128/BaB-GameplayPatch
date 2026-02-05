"""
inject_monster_stats.py
Reads monster stats from JSON files and injects them into BLAZE.ALL

Usage: py -3 inject_monster_stats.py --blaze BLAZE.ALL --json-dir monster_stats --out output/BLAZE.ALL
"""

import argparse
import json
import struct
from pathlib import Path

# Stats field order matching the README structure
# Offset from monster entry start:
#   0x00: Name (16 bytes) - not modified
#   0x10-0x3C: Stats (23 x uint16)

STATS_OFFSET = 0x10  # Stats start 16 bytes after entry start (after name)
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

def inject_stats(blaze_data: bytearray, offset: int, stats: dict, name: str) -> None:
    """Inject monster stats at the given offset in BLAZE.ALL"""
    stats_offset = offset + STATS_OFFSET

    for i, stat_name in enumerate(STATS_ORDER):
        value = stats.get(stat_name, 0)
        write_offset = stats_offset + (i * 2)

        # Handle both negative and large positive values
        if value < 0:
            packed = struct.pack('<h', value)  # signed int16
        else:
            packed = struct.pack('<H', min(value, 65535))  # unsigned uint16, capped
        blaze_data[write_offset:write_offset+2] = packed


def find_all_occurrences(data: bytes, name: str) -> list:
    """Find all offsets where monster name appears in BLAZE.ALL"""
    # Monster names are padded to 16 bytes with nulls
    search = name.encode('ascii')
    offsets = []
    pos = 0
    while True:
        pos = data.find(search, pos)
        if pos == -1:
            break
        # Check if this is a substring of a larger name (e.g., "Durahan" in "Black-Durahan")
        # by checking if the character before is a letter or hyphen
        if pos > 0:
            prev_char = data[pos-1]
            # If previous char is A-Z, a-z, or hyphen, this is a substring - skip
            if (0x41 <= prev_char <= 0x5A) or (0x61 <= prev_char <= 0x7A) or prev_char == 0x2D:
                pos += 1
                continue

        # Verify it's a proper monster entry (name followed by null within 16 bytes)
        entry = data[pos:pos+16]
        if b'\x00' in entry:
            # Check if name matches exactly (not a substring of another name)
            actual_name = entry.split(b'\x00')[0].decode('ascii', errors='ignore')
            if actual_name == name:
                offsets.append(pos)
        pos += 1
    return offsets


def main():
    parser = argparse.ArgumentParser(description='Inject monster stats into BLAZE.ALL')
    parser.add_argument('--blaze', required=True, help='Input BLAZE.ALL file')
    parser.add_argument('--json-dir', required=True, help='Directory containing monster JSON files')
    parser.add_argument('--out', required=True, help='Output BLAZE.ALL file')
    args = parser.parse_args()

    blaze_path = Path(args.blaze)
    json_dir = Path(args.json_dir)
    out_path = Path(args.out)

    # Read BLAZE.ALL
    print(f"Reading {blaze_path}...")
    blaze_data = bytearray(blaze_path.read_bytes())
    print(f"  Size: {len(blaze_data)} bytes")

    # Create output directory if needed
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Process all JSON files (including subdirectories like boss/)
    json_files = list(json_dir.glob("**/*.json"))
    json_files = [f for f in json_files if not f.name.startswith('_')]  # Skip _README.txt etc

    print(f"\nProcessing {len(json_files)} monster files...")

    total_injected = 0
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                monster = json.load(f)

            name = monster.get('name', json_file.stem)
            stats = monster.get('stats', {})

            # Find ALL occurrences of this monster in BLAZE.ALL
            offsets = find_all_occurrences(bytes(blaze_data), name)

            if not offsets:
                print(f"  WARNING: {name} - not found in BLAZE.ALL")
                continue

            # Inject stats at ALL locations
            for offset in offsets:
                inject_stats(blaze_data, offset, stats, name)

            total_injected += len(offsets)
            print(f"  {name}: patched {len(offsets)} occurrence{'s' if len(offsets) > 1 else ''}")

        except Exception as e:
            print(f"  ERROR processing {json_file.name}: {e}")

    print(f"\nInjected stats at {total_injected} locations")

    # Write output
    print(f"Writing {out_path}...")
    out_path.write_bytes(blaze_data)
    print("Done!")


if __name__ == '__main__':
    main()
