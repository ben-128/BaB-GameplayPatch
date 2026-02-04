#!/usr/bin/env python3
"""
Verify that the CORRECT location (0x002EA49A) is patched in the BIN file
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")

# CORRECT location!
CORRECT_OFFSET = 0x002EA49A
WRONG_OFFSET = 0x002EA500

BLAZE_LBA_COPY1 = 163167
BLAZE_LBA_COPY2 = 185765
SECTOR_SIZE = 2352
DATA_START = 24
DATA_SIZE = 2048

TEST_MODIFICATIONS = [
    (0, "Healing Potion", 10, 99),
    (2, "Shortsword", 22, 88),
    (13, "Leather Armor", 36, 77),
]

def calculate_bin_offset(blaze_offset, blaze_lba):
    """Calculate byte offset in BIN file"""
    sector_in_blaze = blaze_offset // DATA_SIZE
    offset_in_sector = blaze_offset % DATA_SIZE
    lba = blaze_lba + sector_in_blaze
    bin_offset = lba * SECTOR_SIZE + DATA_START + offset_in_sector
    return bin_offset

def read_16bit_value(file_path, offset):
    """Read 16-bit little-endian value"""
    with open(file_path, 'rb') as f:
        f.seek(offset)
        data = f.read(2)
        return struct.unpack('<H', data)[0]

def check_location(location_offset, location_name):
    """Check if a location has the expected patched values"""
    print(f"{location_name}: 0x{location_offset:08X}")
    print("-" * 70)

    all_correct = True

    for word_idx, item, orig, expected in TEST_MODIFICATIONS:
        word_offset = location_offset + (word_idx * 2)

        # Calculate offsets in BIN for both copies
        offset1 = calculate_bin_offset(word_offset, BLAZE_LBA_COPY1)
        offset2 = calculate_bin_offset(word_offset, BLAZE_LBA_COPY2)

        c1 = read_16bit_value(BIN_PATH, offset1)
        c2 = read_16bit_value(BIN_PATH, offset2)

        c1_status = "OK" if c1 == expected else "FAIL"
        c2_status = "OK" if c2 == expected else "FAIL"

        print(f"Word[{word_idx:2d}] {item:<20} Exp:{expected:<4} Copy1:{c1:<4}{c1_status:<6} Copy2:{c2:<4}{c2_status}")

        if c1 != expected or c2 != expected:
            all_correct = False

    print()
    return all_correct

def main():
    print("=" * 70)
    print("  VERIFY CORRECT LOCATION IN BIN FILE")
    print("=" * 70)
    print()
    print(f"BIN: {BIN_PATH}")
    print()

    print("Checking CORRECT location (0x002EA49A - the one game reads):")
    print()
    correct_ok = check_location(CORRECT_OFFSET, "CORRECT LOCATION")

    print("Checking WRONG location (0x002EA500 - our old test):")
    print()
    wrong_ok = check_location(WRONG_OFFSET, "WRONG LOCATION")

    print("=" * 70)
    print("  RESULT")
    print("=" * 70)
    print()

    if correct_ok:
        print("[SUCCESS] CORRECT location (0x002EA49A) is patched!")
        print()
        print("NOW TEST IN-GAME:")
        print("1. Close emulator completely")
        print("2. Load the patched BIN")
        print("3. Start a NEW game")
        print("4. Go to Auction House")
        print("5. Check prices:")
        print("   - Healing Potion should be 99 gold")
        print("   - Shortsword should be 88 gold")
        print("   - Leather Armor should be 77 gold")
        print()
        print("If prices changed: SUCCESS! We found it!")
    else:
        print("[ERROR] Correct location is NOT patched properly!")

    if wrong_ok:
        print()
        print("[INFO] Old wrong location (0x002EA500) still has patched values")
        print("      (This is OK, it doesn't matter)")

if __name__ == '__main__':
    main()
