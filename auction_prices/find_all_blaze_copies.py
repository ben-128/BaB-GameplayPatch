#!/usr/bin/env python3
"""
Search the entire BIN file for all copies of BLAZE.ALL by finding the signature.
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")
SECTOR_SIZE = 2352
DATA_START = 24
DATA_SIZE = 2048

# BLAZE.ALL signature - first 16 bytes should be unique
# Let's use the auction price pattern we know
SIGNATURE = struct.pack('<7H', 10, 0, 22, 0, 0, 0, 0)  # Words 0-6: 10, 0, 22, 0, 0, 0, 0

# Offset where this signature appears in BLAZE.ALL
SIGNATURE_OFFSET = 0x002EA500

def search_bin_for_signature():
    """Search entire BIN for the auction price signature"""
    print("=" * 70)
    print("  SEARCHING BIN FILE FOR AUCTION PRICE SIGNATURES")
    print("=" * 70)
    print()

    with open(BIN_PATH, 'rb') as f:
        bin_data = f.read()

    print(f"BIN file size: {len(bin_data):,} bytes")
    print(f"Searching for signature: {SIGNATURE.hex()}")
    print()

    matches = []
    pos = 0

    while True:
        pos = bin_data.find(SIGNATURE, pos)
        if pos == -1:
            break

        # Calculate LBA
        sector = pos // SECTOR_SIZE
        offset_in_sector = pos % SECTOR_SIZE

        # Check if it's in the data portion of a sector (bytes 24-2071)
        if DATA_START <= offset_in_sector < (DATA_START + DATA_SIZE):
            # Calculate what the LBA would be if this is BLAZE.ALL
            data_offset_in_sector = offset_in_sector - DATA_START
            data_offset_in_blaze = (sector * DATA_SIZE) + data_offset_in_sector - SIGNATURE_OFFSET

            # This would be the LBA where BLAZE.ALL starts
            blaze_start_sector = data_offset_in_blaze // DATA_SIZE
            blaze_lba = sector - blaze_start_sector

            matches.append({
                'bin_offset': pos,
                'lba': sector,
                'estimated_blaze_lba': blaze_lba,
                'offset_in_sector': offset_in_sector
            })

        pos += 1

    print(f"Found {len(matches)} potential match(es):")
    print()

    for i, match in enumerate(matches, 1):
        print(f"Match #{i}:")
        print(f"  BIN offset: 0x{match['bin_offset']:08X} ({match['bin_offset']:,})")
        print(f"  LBA: {match['lba']}")
        print(f"  Estimated BLAZE.ALL start LBA: ~{match['estimated_blaze_lba']}")
        print()

        # Read the actual values at this location
        offset = match['bin_offset']
        values = []
        for i in range(16):
            val = struct.unpack('<H', bin_data[offset + i*2:offset + i*2 + 2])[0]
            values.append(val)

        print(f"  First 16 words: {values}")
        print()

    return matches

if __name__ == '__main__':
    matches = search_bin_for_signature()

    print("=" * 70)
    print(f"KNOWN COPIES (from patch_blaze_all.py):")
    print(f"  Copy 1: LBA 163167")
    print(f"  Copy 2: LBA 185765")
    print()
    print(f"If there are more matches, the game might be reading from a copy")
    print(f"that wasn't patched!")
    print("=" * 70)
