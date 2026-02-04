#!/usr/bin/env python3
"""
Check what values are at both 0x002EA49A and 0x002EA500 in current BLAZE.ALL
"""

import struct
from pathlib import Path

BLAZE_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\BLAZE.ALL")

def read_price_table(data, offset, name):
    """Read and display 16 words from offset"""
    print(f"{name}: 0x{offset:08X}")
    print("-" * 50)

    for i in range(16):
        word_offset = offset + i * 2
        if word_offset + 2 <= len(data):
            val = struct.unpack('<H', data[word_offset:word_offset+2])[0]

            # Mark special values
            marker = ""
            if i == 0:
                if val == 10:
                    marker = " <- ORIGINAL (Healing Potion)"
                elif val == 99:
                    marker = " <- PATCHED (Healing Potion)"
            elif i == 2:
                if val == 22:
                    marker = " <- ORIGINAL (Shortsword)"
                elif val == 88:
                    marker = " <- PATCHED (Shortsword)"
            elif i == 13:
                if val == 36:
                    marker = " <- ORIGINAL (Leather Armor)"
                elif val == 77:
                    marker = " <- PATCHED (Leather Armor)"

            print(f"  Word[{i:2d}] = {val:3d} (0x{val:04X}){marker}")
    print()

def main():
    print("=" * 70)
    print("  CHECKING BLAZE.ALL - TWO POTENTIAL LOCATIONS")
    print("=" * 70)
    print()

    data = BLAZE_PATH.read_bytes()
    print(f"BLAZE.ALL size: {len(data):,} bytes")
    print()

    # Check our test location
    read_price_table(data, 0x002EA500, "Location 1 (our test patch)")

    # Check the found location
    read_price_table(data, 0x002EA49A, "Location 2 (script found)")

    print("=" * 70)
    print("  ANALYSIS")
    print("=" * 70)
    print()
    print("If 0x002EA500 has patched values (99, 88, 77) but")
    print("0x002EA49A has original values (10, 22, 36), then")
    print("the game might be reading from 0x002EA49A instead!")
    print()
    print("We need to patch BOTH locations (or find which one is correct)")

if __name__ == '__main__':
    main()
