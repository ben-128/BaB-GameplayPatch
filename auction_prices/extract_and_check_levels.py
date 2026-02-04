#!/usr/bin/env python3
"""
Extract LEVELS.DAT and check if it contains the price table
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")
WORK_DIR = BIN_PATH.parent
LEVELS_PATH = WORK_DIR / "LEVELS.DAT"

LEVELS_LBA = 163167
LEVELS_SIZE = 46278656
SECTOR_SIZE = 2352
DATA_OFFSET = 24
DATA_SIZE = 2048

PRICE_TABLE_OFFSET = 0x002EA49A

def extract_levels():
    """Extract LEVELS.DAT from BIN"""
    print("=" * 70)
    print("  EXTRACT LEVELS.DAT")
    print("=" * 70)
    print()

    if LEVELS_PATH.exists():
        print(f"[OK] LEVELS.DAT already exists: {LEVELS_PATH}")
        print(f"     Size: {LEVELS_PATH.stat().st_size:,} bytes")
        return True

    print(f"Extracting LEVELS.DAT from BIN...")
    print(f"  LBA: {LEVELS_LBA}")
    print(f"  Size: {LEVELS_SIZE:,} bytes")
    print()

    sectors_needed = (LEVELS_SIZE + DATA_SIZE - 1) // DATA_SIZE

    with open(BIN_PATH, 'rb') as f:
        data = bytearray()

        for i in range(sectors_needed):
            f.seek((LEVELS_LBA + i) * SECTOR_SIZE + DATA_OFFSET)
            data.extend(f.read(DATA_SIZE))

        # Trim to actual size
        data = data[:LEVELS_SIZE]

        LEVELS_PATH.write_bytes(data)

    print(f"[OK] Extracted: {LEVELS_PATH}")
    print(f"     Size: {len(data):,} bytes")
    return True

def check_price_table():
    """Check if LEVELS.DAT contains the price table"""
    print()
    print("=" * 70)
    print("  CHECK FOR PRICE TABLE IN LEVELS.DAT")
    print("=" * 70)
    print()

    data = LEVELS_PATH.read_bytes()

    # Check at the expected offset
    if PRICE_TABLE_OFFSET + 32 > len(data):
        print(f"[ERROR] Offset 0x{PRICE_TABLE_OFFSET:08X} beyond file size")
        return

    print(f"Reading at offset 0x{PRICE_TABLE_OFFSET:08X}...")
    print()

    words = []
    for i in range(32):
        offset = PRICE_TABLE_OFFSET + i * 2
        val = struct.unpack('<H', data[offset:offset+2])[0]
        words.append(val)

    print(f"First 16 words: {words[:16]}")
    print(f"Next 16 words:  {words[16:]}")
    print()

    # Check if it's the 999 pattern
    if all(w == 999 for w in words):
        print("[SUCCESS] LEVELS.DAT contains 999 values!")
        print()
        print("This means patch_blaze_all.py DID patch LEVELS.DAT.")
        print()
        print("BUT the game still shows original prices...")
        print("So even LEVELS.DAT is not being used for auction prices!")
    elif words[:7] == [10, 16, 22, 13, 16, 23, 13]:
        print("[INFO] LEVELS.DAT contains ORIGINAL price pattern!")
        print()
        print("This means:")
        print("  - patch_blaze_all.py did NOT patch LEVELS.DAT")
        print("  - Only BLAZE.ALL was patched")
        print("  - The game might be reading from LEVELS.DAT instead!")
        print()
        print("SOLUTION: We need to patch LEVELS.DAT too!")
    else:
        print(f"[UNEXPECTED] Pattern: {words[:16]}")
        print()
        print("This location doesn't match expected patterns.")

if __name__ == '__main__':
    if extract_levels():
        check_price_table()
