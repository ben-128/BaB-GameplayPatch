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
    "stat2_unknown",        # 1  - 0x12
    "hp",                   # 2  - 0x14
    "stat4_magic",          # 3  - 0x16
    "stat5_randomness",     # 4  - 0x18
    "stat6_collider_type",  # 5  - 0x1A
    "stat7_death_fx_size",  # 6  - 0x1C
    "stat8_unknown",        # 7  - 0x1E
    "stat9_collider_size",  # 8  - 0x20
    "stat10_drop_rate",     # 9  - 0x22
    "stat11_creature_type", # 10 - 0x24 (bitfield)
    "stat12_flags",         # 11 - 0x26 (bitfield)
    "stat13_flags",         # 12 - 0x28 (bitfield)
    "stat14_flags",         # 13 - 0x2A (bitfield)
    "stat15_flags",         # 14 - 0x2C (bitfield)
    "stat16_atk1",          # 15 - 0x2E
    "stat17_def1",          # 16 - 0x30
    "stat18_atk2",          # 17 - 0x32
    "stat19_def2",          # 18 - 0x34
    "stat20_atk3",          # 19 - 0x36
    "stat21_def3",          # 20 - 0x38
    "stat22_atk4",          # 21 - 0x3A
    "stat23_def4",          # 22 - 0x3C
]

def inject_stats(blaze_data: bytearray, offset: int, stats: dict, name: str) -> None:
    """Inject monster stats at the given offset in BLAZE.ALL"""
    stats_offset = offset + STATS_OFFSET

    for i, stat_name in enumerate(STATS_ORDER):
        value = stats.get(stat_name, 0)
        write_offset = stats_offset + (i * 2)

        # Pack as little-endian uint16
        packed = struct.pack('<H', value)
        blaze_data[write_offset:write_offset+2] = packed


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

    # Process all JSON files
    json_files = list(json_dir.glob("*.json"))
    json_files = [f for f in json_files if not f.name.startswith('_')]  # Skip _README.txt etc

    print(f"\nProcessing {len(json_files)} monster files...")

    injected = 0
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                monster = json.load(f)

            name = monster.get('name', json_file.stem)
            offset = monster.get('offset_decimal')
            stats = monster.get('stats', {})

            if offset is None:
                print(f"  WARNING: {name} - no offset_decimal, skipping")
                continue

            inject_stats(blaze_data, offset, stats, name)
            injected += 1

        except Exception as e:
            print(f"  ERROR processing {json_file.name}: {e}")

    print(f"\nInjected stats for {injected} monsters")

    # Write output
    print(f"Writing {out_path}...")
    out_path.write_bytes(blaze_data)
    print("Done!")


if __name__ == '__main__':
    main()
