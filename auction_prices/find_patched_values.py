#!/usr/bin/env python3
"""
Search for the patched auction price values (99, 88, 77) in the BIN file.
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")

# Patched values
WORD0_VAL = 99   # Healing Potion at word 0
WORD2_VAL = 88   # Shortsword at word 2
WORD13_VAL = 77  # Leather Armor at word 13

def search_pattern():
    """Search for locations where word[0]=99, word[2]=88, word[13]=77"""
    print("=" * 70)
    print("  SEARCHING FOR PATCHED AUCTION PRICE PATTERN")
    print("=" * 70)
    print()
    print(f"Looking for: Word[0]=99, Word[2]=88, Word[13]=77")
    print()

    with open(BIN_PATH, 'rb') as f:
        bin_data = f.read()

    print(f"BIN file size: {len(bin_data):,} bytes")
    print("Searching... (this may take a minute)")
    print()

    matches = []

    # Search for word[0] = 99
    val99 = struct.pack('<H', 99)
    pos = 0
    checked = 0

    while True:
        pos = bin_data.find(val99, pos)
        if pos == -1:
            break

        checked += 1
        if checked % 100000 == 0:
            print(f"  Checked {checked:,} potential matches...")

        # Check if word[2] = 88 (offset +4 bytes)
        if pos + 4 + 2 <= len(bin_data):
            word2 = struct.unpack('<H', bin_data[pos+4:pos+6])[0]
            if word2 == 88:
                # Check if word[13] = 77 (offset +26 bytes)
                if pos + 26 + 2 <= len(bin_data):
                    word13 = struct.unpack('<H', bin_data[pos+26:pos+28])[0]
                    if word13 == 77:
                        matches.append(pos)

        pos += 1

    print()
    print("=" * 70)
    print(f"FOUND {len(matches)} MATCH(ES)")
    print("=" * 70)
    print()

    for i, offset in enumerate(matches, 1):
        # Calculate sector and LBA
        sector = offset // 2352
        offset_in_sector = offset % 2352

        print(f"Match #{i}:")
        print(f"  BIN offset: 0x{offset:08X} ({offset:,} bytes)")
        print(f"  Sector: {sector}")
        print(f"  Offset in sector: {offset_in_sector}")

        # Read surrounding values
        print(f"  Values:")
        for j in range(16):
            val_offset = offset + j * 2
            if val_offset + 2 <= len(bin_data):
                val = struct.unpack('<H', bin_data[val_offset:val_offset+2])[0]
                marker = ""
                if j == 0:
                    marker = " <- Healing Potion (99)"
                elif j == 2:
                    marker = " <- Shortsword (88)"
                elif j == 13:
                    marker = " <- Leather Armor (77)"
                print(f"    Word[{j:2d}] = {val:3d} (0x{val:04X}){marker}")
        print()

    return matches

if __name__ == '__main__':
    matches = search_pattern()

    if len(matches) > 2:
        print("=" * 70)
        print("  WARNING: MORE THAN 2 COPIES FOUND!")
        print("=" * 70)
        print()
        print("The game might be reading from a copy that wasn't patched.")
        print("patch_blaze_all.py only patches LBA 163167 and 185765")
    elif len(matches) == 2:
        print("Found exactly 2 copies (expected)")
    elif len(matches) < 2:
        print("WARNING: Expected 2 copies but found fewer!")
