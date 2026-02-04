#!/usr/bin/env python3
"""
Search ORIGINAL BIN for ALL occurrences of the price pattern
"""

import struct
from pathlib import Path

# Use the backup which should be original
ORIGINAL_BIN = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin.backup")

# The exact pattern we found at 0x002EA49A
PRICE_PATTERN = struct.pack('<16H', 10, 16, 22, 13, 16, 23, 13, 24, 25, 26, 27, 28, 29, 36, 16, 46)

def search_all_occurrences():
    """Find every occurrence of the price pattern"""
    print("=" * 70)
    print("  SEARCH ORIGINAL BIN FOR ALL PRICE TABLE COPIES")
    print("=" * 70)
    print()

    if not ORIGINAL_BIN.exists():
        print(f"[ERROR] Original BIN not found: {ORIGINAL_BIN}")
        return []

    print(f"BIN: {ORIGINAL_BIN}")
    print(f"Size: {ORIGINAL_BIN.stat().st_size:,} bytes")
    print()

    print("Searching for pattern:")
    print("  [10, 16, 22, 13, 16, 23, 13, 24, 25, 26, 27, 28, 29, 36, 16, 46]")
    print()
    print("This may take a minute...")
    print()

    with open(ORIGINAL_BIN, 'rb') as f:
        data = f.read()

    matches = []
    pos = 0
    count = 0

    while True:
        pos = data.find(PRICE_PATTERN, pos)
        if pos == -1:
            break

        count += 1
        if count % 100 == 0:
            print(f"  ...found {count} matches so far...")

        matches.append(pos)
        pos += 1

    print()
    print(f"FOUND {len(matches)} OCCURRENCE(S)!")
    print()
    print("=" * 70)

    for i, offset in enumerate(matches, 1):
        # Calculate LBA and sector info
        lba = offset // 2352
        offset_in_sector = offset % 2352

        print(f"Match #{i}:")
        print(f"  BIN offset: 0x{offset:08X} ({offset:,} bytes)")
        print(f"  LBA: {lba}")
        print(f"  Offset in sector: {offset_in_sector}")

        # Determine which file/region
        if 163167 * 2352 <= offset < (163167 + 22562) * 2352:
            file_offset = offset - (163167 * 2352 + 24)
            # Account for sector structure
            sector_num = file_offset // 2352
            data_offset = (file_offset % 2352) - 24
            if data_offset < 0:
                data_offset += 2352
            real_offset = sector_num * 2048 + data_offset
            print(f"  -> LEVELS.DAT at file offset ~0x{real_offset:08X}")

        elif 185765 * 2352 <= offset < (185765 + 22562) * 2352:
            file_offset = offset - (185765 * 2352 + 24)
            sector_num = file_offset // 2352
            data_offset = (file_offset % 2352) - 24
            if data_offset < 0:
                data_offset += 2352
            real_offset = sector_num * 2048 + data_offset
            print(f"  -> BLAZE.ALL at file offset ~0x{real_offset:08X}")

        else:
            print(f"  -> UNKNOWN REGION!")
            # Check other files
            if 27439 * 2352 <= offset < (27439 + 32391) * 2352:
                print(f"     (Might be in MUSIC03.XA)")
            elif 295081 * 2352 <= offset < (295081 + 413) * 2352:
                print(f"     (Might be in SLES_008.45)")
            else:
                print(f"     (In unknown file or unallocated space)")

        # Show full 32 words from this location
        words = []
        for j in range(32):
            if offset + j*2 + 2 <= len(data):
                val = struct.unpack('<H', data[offset+j*2:offset+j*2+2])[0]
                words.append(val)

        print(f"  Full pattern (32 words):")
        print(f"    {words[:16]}")
        print(f"    {words[16:]}")
        print()

    return matches

if __name__ == '__main__':
    matches = search_all_occurrences()

    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()

    if len(matches) == 0:
        print("No matches found - backup might be already patched!")
    elif len(matches) == 2:
        print(f"Found exactly 2 copies (in LEVELS.DAT and BLAZE.ALL)")
        print("These are the ones we already patched.")
        print("No additional copies found.")
        print()
        print("Mystery remains - why doesn't patching work?")
    elif len(matches) > 2:
        print(f"Found {len(matches)} copies!")
        print()
        print("SOLUTION: We need to patch ALL these locations!")
        print("The game might be reading from one we haven't patched yet.")
    else:
        print("Unexpected result!")
