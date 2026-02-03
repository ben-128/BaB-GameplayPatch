"""
patch_monster_stats_bin.py
Patches monster stats directly into the BIN file at BOTH locations
(the game has two copies of the monster data)

Usage: py -3 patch_monster_stats_bin.py
"""

import json
import struct
from pathlib import Path

# Configuration
BIN_FILE = Path(r"work\Blaze & Blade - Patched.bin")
JSON_DIR = Path(r"monster_stats")

# Disc format
SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048

# BLAZE.ALL location
LBA_BLAZE_ALL = 163167

# Offset between the two copies of monster data in the BIN
# The game uses the SECOND copy, but we patch both to be safe
SECOND_COPY_OFFSET = 0x32B0320  # 53,150,496 bytes

# Stats field order (offset from monster entry + 0x10)
# 23 stats total (indices 0-22, written at offsets 0x10-0x3C)
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


def blaze_offset_to_bin_offset(blaze_offset: int) -> int:
    """Convert an offset within BLAZE.ALL to an offset in the RAW BIN file"""
    sector_in_blaze = blaze_offset // USER_SIZE
    offset_in_sector = blaze_offset % USER_SIZE
    lba = LBA_BLAZE_ALL + sector_in_blaze
    return lba * SECTOR_RAW + USER_OFF + offset_in_sector


def patch_stats(bin_data: bytearray, bin_offset: int, stats: dict, name: str) -> bool:
    """Patch monster stats at the given BIN offset. Returns True if successful."""
    stats_offset = bin_offset + 0x10  # Stats start after 16-byte name

    # 23 stats * 2 bytes = 46 bytes needed
    if stats_offset + 46 > len(bin_data):
        return False

    for i, stat_name in enumerate(STATS_ORDER):
        value = stats.get(stat_name, 0)
        write_offset = stats_offset + (i * 2)
        packed = struct.pack('<H', value)
        bin_data[write_offset:write_offset+2] = packed

    return True


def main():
    print("=" * 60)
    print("  Monster Stats BIN Patcher (patches both data copies)")
    print("=" * 60)
    print()

    # Read BIN
    print(f"Reading {BIN_FILE}...")
    bin_data = bytearray(BIN_FILE.read_bytes())
    print(f"  Size: {len(bin_data)} bytes")
    print()

    # Process JSON files
    json_files = [f for f in JSON_DIR.glob("*.json") if not f.name.startswith('_')]
    print(f"Processing {len(json_files)} monster files...")
    print()

    patched_first = 0
    patched_second = 0

    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                monster = json.load(f)

            name = monster.get('name', json_file.stem)
            blaze_offset = monster.get('offset_decimal')
            stats = monster.get('stats', {})

            if blaze_offset is None:
                print(f"  WARNING: {name} - no offset, skipping")
                continue

            # Calculate BIN offsets for both copies
            bin_offset_1 = blaze_offset_to_bin_offset(blaze_offset)
            bin_offset_2 = bin_offset_1 + SECOND_COPY_OFFSET

            # Patch first copy
            if patch_stats(bin_data, bin_offset_1, stats, name):
                patched_first += 1

            # Patch second copy (the one the game actually uses)
            if bin_offset_2 + 0x40 <= len(bin_data):
                if patch_stats(bin_data, bin_offset_2, stats, name):
                    patched_second += 1

        except Exception as e:
            print(f"  ERROR: {json_file.name}: {e}")

    print(f"Patched {patched_first} monsters in first copy")
    print(f"Patched {patched_second} monsters in second copy")
    print()

    # Write output
    print(f"Writing {BIN_FILE}...")
    BIN_FILE.write_bytes(bin_data)

    print()
    print("=" * 60)
    print("  Patch complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
