#!/usr/bin/env python3
"""
Verify that Blaze & Blade - Patched.bin contains the patched auction price values.
"""

import struct
import sys
from pathlib import Path

# Expected test modifications at 0x002EA500 in BLAZE.ALL
TEST_OFFSET_IN_BLAZE = 0x002EA500
# (word_index, item_name, original_value, expected_value)
TEST_MODIFICATIONS = [
    (0, "Healing Potion", 10, 99),
    (2, "Shortsword", 22, 88),
    (13, "Leather Armor", 36, 77),
]

# BIN file details
BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")
BLAZE_LBA_COPY1 = 163167
BLAZE_LBA_COPY2 = 185765
SECTOR_SIZE = 2352
DATA_START = 24  # Data starts at byte 24 in RAW sectors
DATA_SIZE = 2048  # 2048 bytes of data per sector

def calculate_bin_offset(blaze_offset, blaze_lba):
    """Calculate byte offset in BIN file for a given offset in BLAZE.ALL"""
    # Calculate which sector and byte offset within BLAZE.ALL
    sector_in_blaze = blaze_offset // DATA_SIZE
    offset_in_sector = blaze_offset % DATA_SIZE

    # Calculate LBA in disc
    lba = blaze_lba + sector_in_blaze

    # Calculate byte offset in BIN (RAW format: sector * 2352 + 24 header + offset)
    bin_offset = lba * SECTOR_SIZE + DATA_START + offset_in_sector

    return bin_offset, lba, sector_in_blaze, offset_in_sector

def read_16bit_value(file_path, offset):
    """Read a single 16-bit little-endian value from file at offset"""
    with open(file_path, 'rb') as f:
        f.seek(offset)
        data = f.read(2)
        return struct.unpack('<H', data)[0]

def main():
    print("=" * 70)
    print("  VERIFY BIN PATCH - Auction Price Test Values")
    print("=" * 70)
    print()

    if not BIN_PATH.exists():
        print(f"[ERROR] BIN file not found: {BIN_PATH}")
        return 1

    print(f"BIN file: {BIN_PATH}")
    print(f"BIN size: {BIN_PATH.stat().st_size:,} bytes")
    print()

    print(f"Test location base: 0x{TEST_OFFSET_IN_BLAZE:08X} in BLAZE.ALL")
    print()

    # Read values from both copies
    print("-" * 70)
    print("Reading 16-bit values from BIN file...")
    print("-" * 70)

    try:
        print()
        print(f"{'Word':<6} {'Item':<20} {'Original':<10} {'Expected':<10} {'Copy 1':<10} {'Copy 2':<10}")
        print("-" * 70)

        all_match = True

        for word_idx, item, orig, exp in TEST_MODIFICATIONS:
            # Calculate offset for this word
            word_offset = TEST_OFFSET_IN_BLAZE + (word_idx * 2)
            offset1, lba1, sec1, off1 = calculate_bin_offset(word_offset, BLAZE_LBA_COPY1)
            offset2, lba2, sec2, off2 = calculate_bin_offset(word_offset, BLAZE_LBA_COPY2)

            c1 = read_16bit_value(BIN_PATH, offset1)
            c2 = read_16bit_value(BIN_PATH, offset2)

            c1_status = "OK" if c1 == exp else "FAIL"
            c2_status = "OK" if c2 == exp else "FAIL"

            print(f"[{word_idx:3d}] {item:<20} {orig:<10} {exp:<10} {c1:<8} {c1_status:<2} {c2:<8} {c2_status:<2}")

            if c1 != exp or c2 != exp:
                all_match = False

        print()
        print("=" * 70)

        if all_match:
            print("  [SUCCESS] All patched values found in BIN file!")
            print("=" * 70)
            print()
            print("The BIN file contains the correct patched values.")
            print("This means the patching process worked correctly.")
            print()
            print("CONCLUSION: The auction prices are NOT at this location.")
            print("The game reads auction prices from somewhere else.")
            return 0
        else:
            print("  [WARNING] Patched values NOT found in BIN file!")
            print("=" * 70)
            print()
            print("Possible reasons:")
            print("1. The patching process failed")
            print("2. BLAZE.ALL wasn't properly modified before patching")
            print("3. The offset calculation is incorrect")
            print()
            print("Check that test_modify_16bit_prices.py successfully modified BLAZE.ALL")
            return 1

    except Exception as e:
        print(f"[ERROR] Failed to read BIN file: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
