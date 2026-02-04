#!/usr/bin/env python3
"""
Final check: Read directly from the BIN file and show what's at both locations
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")

CORRECT_OFFSET = 0x002EA49A  # The one game actually reads
WRONG_OFFSET = 0x002EA500    # Our old test location

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

def read_words_from_bin(f, offset, count=16):
    """Read count 16-bit words from BIN file"""
    f.seek(offset)
    data = f.read(count * 2)
    return [struct.unpack('<H', data[i:i+2])[0] for i in range(0, len(data), 2)]

def show_location(f, blaze_offset, location_name):
    """Show what's at a location in both copies"""
    print(f"{location_name}")
    print("=" * 70)
    print(f"Offset in BLAZE.ALL: 0x{blaze_offset:08X}")
    print()

    # Copy 1
    offset1, lba1 = calculate_bin_offset(blaze_offset, BLAZE_LBA_COPY1)
    print(f"Copy 1: LBA {lba1}, BIN offset 0x{offset1:08X}")
    words1 = read_words_from_bin(f, offset1)

    print("  Word[ 0] (Healing Potion):  ", end="")
    if words1[0] == 99:
        print(f"{words1[0]} <- PATCHED OK")
    else:
        print(f"{words1[0]} <- ORIGINAL (should be 99!)")

    print("  Word[ 2] (Shortsword):      ", end="")
    if words1[2] == 88:
        print(f"{words1[2]} <- PATCHED OK")
    else:
        print(f"{words1[2]} <- ORIGINAL (should be 88!)")

    print("  Word[13] (Leather Armor):   ", end="")
    if words1[13] == 77:
        print(f"{words1[13]} <- PATCHED OK")
    else:
        print(f"{words1[13]} <- ORIGINAL (should be 77!)")

    print()

    # Copy 2
    offset2, lba2 = calculate_bin_offset(blaze_offset, BLAZE_LBA_COPY2)
    print(f"Copy 2: LBA {lba2}, BIN offset 0x{offset2:08X}")
    words2 = read_words_from_bin(f, offset2)

    print("  Word[ 0] (Healing Potion):  ", end="")
    if words2[0] == 99:
        print(f"{words2[0]} <- PATCHED OK")
    else:
        print(f"{words2[0]} <- ORIGINAL (should be 99!)")

    print("  Word[ 2] (Shortsword):      ", end="")
    if words2[2] == 88:
        print(f"{words2[2]} <- PATCHED OK")
    else:
        print(f"{words2[2]} <- ORIGINAL (should be 88!)")

    print("  Word[13] (Leather Armor):   ", end="")
    if words2[13] == 77:
        print(f"{words2[13]} <- PATCHED OK")
    else:
        print(f"{words2[13]} <- ORIGINAL (should be 77!)")

    print()
    print("All 16 words:")
    print("  Copy 1:", words1)
    print("  Copy 2:", words2)
    print()

    return (words1[0] == 99 and words1[2] == 88 and words1[13] == 77 and
            words2[0] == 99 and words2[2] == 88 and words2[13] == 77)

def main():
    print("=" * 70)
    print("  FINAL VERIFICATION - READING DIRECTLY FROM BIN FILE")
    print("=" * 70)
    print()

    if not BIN_PATH.exists():
        print(f"[ERROR] BIN not found: {BIN_PATH}")
        return False

    print(f"BIN: {BIN_PATH}")
    print(f"Size: {BIN_PATH.stat().st_size:,} bytes")
    print()

    with open(BIN_PATH, 'rb') as f:
        print("-" * 70)
        correct_ok = show_location(f, CORRECT_OFFSET, "CORRECT LOCATION (0x002EA49A - game reads here)")
        print("-" * 70)
        wrong_ok = show_location(f, WRONG_OFFSET, "OLD LOCATION (0x002EA500 - not used by game)")
        print("-" * 70)

    print()
    print("=" * 70)
    print("  FINAL RESULT")
    print("=" * 70)
    print()

    if correct_ok:
        print("[SUCCESS] CORRECT location (0x002EA49A) is PATCHED in BIN!")
        print()
        print("Expected in-game auction prices:")
        print("  - Healing Potion: 99 gold (was 10)")
        print("  - Shortsword: 88 gold (was 22)")
        print("  - Leather Armor: 77 gold (was 36)")
        print()
        print("Ready to test in-game!")
        return True
    else:
        print("[ERROR] CORRECT location is NOT properly patched!")
        print("Something went wrong with the patching process.")
        return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
