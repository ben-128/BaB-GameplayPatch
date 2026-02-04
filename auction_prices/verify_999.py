#!/usr/bin/env python3
"""
Verify that the BIN contains 999 values at the correct location
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")

PRICE_TABLE_OFFSET = 0x002EA49A
BLAZE_LBA_COPY1 = 163167
BLAZE_LBA_COPY2 = 185765
SECTOR_SIZE = 2352
DATA_START = 24
DATA_SIZE = 2048

def calculate_bin_offset(blaze_offset, blaze_lba):
    """Calculate byte offset in BIN file"""
    sector_in_blaze = blaze_offset // DATA_SIZE
    offset_in_sector = blaze_offset % DATA_SIZE
    lba = blaze_lba + sector_in_blaze
    bin_offset = lba * SECTOR_SIZE + DATA_START + offset_in_sector
    return bin_offset, lba

def main():
    print("=" * 70)
    print("  VERIFY 999 VALUES IN BIN")
    print("=" * 70)
    print()

    with open(BIN_PATH, 'rb') as f:
        # Check Copy 1
        offset1, lba1 = calculate_bin_offset(PRICE_TABLE_OFFSET, BLAZE_LBA_COPY1)
        print(f"Copy 1: LBA {lba1}, offset 0x{offset1:08X}")
        f.seek(offset1)
        words1 = []
        for i in range(32):
            data = f.read(2)
            val = struct.unpack('<H', data)[0]
            words1.append(val)

        all_999_c1 = all(w == 999 for w in words1)
        print(f"  First 32 words: {words1[:16]}")
        print(f"                  {words1[16:]}")
        print(f"  Status: {'ALL 999 OK' if all_999_c1 else 'FAILED - not all 999'}")
        print()

        # Check Copy 2
        offset2, lba2 = calculate_bin_offset(PRICE_TABLE_OFFSET, BLAZE_LBA_COPY2)
        print(f"Copy 2: LBA {lba2}, offset 0x{offset2:08X}")
        f.seek(offset2)
        words2 = []
        for i in range(32):
            data = f.read(2)
            val = struct.unpack('<H', data)[0]
            words2.append(val)

        all_999_c2 = all(w == 999 for w in words2)
        print(f"  First 32 words: {words2[:16]}")
        print(f"                  {words2[16:]}")
        print(f"  Status: {'ALL 999 OK' if all_999_c2 else 'FAILED - not all 999'}")
        print()

    print("=" * 70)
    if all_999_c1 and all_999_c2:
        print("  [SUCCESS] Both copies have all 999 values!")
        print("=" * 70)
        print()
        print("BIN is ready for testing.")
        print()
        print("TEST IN-GAME:")
        print("1. Close emulator")
        print("2. Load this BIN")
        print("3. New game")
        print("4. Look EVERYWHERE for 999 prices:")
        print("   - Auction House")
        print("   - Shops")
        print("   - When selling items")
        print("   - Item values in inventory")
        print("   - Anywhere!")
    else:
        print("  [ERROR] Not all values are 999!")
        print("=" * 70)

if __name__ == '__main__':
    main()
