#!/usr/bin/env python3
"""
Search the ENTIRE BIN file for ALL copies of the price pattern
The pattern is too specific to be a coincidence - we must find all copies!
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")

# The distinctive pattern we found (ORIGINAL values, not 999)
# We need to search the ORIGINAL BIN or restore it first
# For now, let's search for the 999 pattern to see where it was written

def search_for_pattern():
    """Search entire BIN for the pattern"""
    print("=" * 70)
    print("  SEARCH ENTIRE BIN FOR ALL PRICE TABLE COPIES")
    print("=" * 70)
    print()

    print(f"BIN: {BIN_PATH}")
    print(f"Size: {BIN_PATH.stat().st_size:,} bytes")
    print()

    # We patched to 999, so search for that pattern
    # Pattern: 32 consecutive 999 values
    pattern_999 = struct.pack('<32H', *([999] * 32))

    print("Searching for 32 consecutive 999 values...")
    print("(This shows where our patches were applied)")
    print()

    with open(BIN_PATH, 'rb') as f:
        data = f.read()

    matches = []
    pos = 0

    while True:
        pos = data.find(pattern_999, pos)
        if pos == -1:
            break
        matches.append(pos)
        pos += 1

    print(f"Found {len(matches)} location(s) with 32x999 pattern:")
    print()

    for i, offset in enumerate(matches, 1):
        # Calculate LBA
        lba = offset // 2352
        offset_in_sector = offset % 2352

        print(f"Match #{i}:")
        print(f"  BIN offset: 0x{offset:08X} ({offset:,} bytes)")
        print(f"  LBA: {lba}")
        print(f"  Offset in sector: {offset_in_sector}")

        # Try to determine which file this is in
        if 163167 * 2352 <= offset < (163167 + 22562) * 2352:
            print(f"  -> In LEVELS.DAT region")
        elif 185765 * 2352 <= offset < (185765 + 22562) * 2352:
            print(f"  -> In BLAZE.ALL region")
        else:
            print(f"  -> UNKNOWN REGION! Might be in another file!")

        print()

    print("=" * 70)
    print("  NEED TO CHECK ORIGINAL BIN")
    print("=" * 70)
    print()
    print("The current BIN has been patched with 999.")
    print("To find ALL original copies, we need to search the ORIGINAL BIN")
    print("for the pattern [10, 16, 22, 13, 16, 23, 13, 24...]")
    print()
    print("Do you have a backup of the original BIN before any patches?")

if __name__ == '__main__':
    search_for_pattern()
