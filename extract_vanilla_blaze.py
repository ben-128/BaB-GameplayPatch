#!/usr/bin/env python3
"""
Extract vanilla BLAZE.ALL from source BIN for comparison.

BLAZE.ALL is stored at LBA 163167 in the source BIN.
Size: ~46MB
"""

from pathlib import Path

SOURCE_BIN = Path("Blaze  Blade - Eternal Quest (Europe)") / "Blaze & Blade - Eternal Quest (Europe).bin"
OUTPUT_FILE = Path("vanilla_BLAZE.ALL")

BLAZE_LBA = 163167
SECTOR_SIZE = 2352
SECTOR_HEADER = 24
DATA_PER_SECTOR = 2048

# BLAZE.ALL size (from current output)
BLAZE_SIZE = 48234496  # bytes

def extract_blaze():
    print("Vanilla BLAZE.ALL Extractor")
    print("=" * 50)
    print()

    if not SOURCE_BIN.exists():
        print(f"ERROR: {SOURCE_BIN} not found")
        print("Please ensure the source BIN is in the project root")
        return False

    print(f"Source BIN: {SOURCE_BIN}")
    print(f"BLAZE.ALL at LBA: {BLAZE_LBA}")
    print(f"Expected size: {BLAZE_SIZE:,} bytes")
    print()

    with open(SOURCE_BIN, 'rb') as f:
        # Calculate number of sectors needed
        sectors_needed = (BLAZE_SIZE + DATA_PER_SECTOR - 1) // DATA_PER_SECTOR

        print(f"Reading {sectors_needed} sectors...")

        blaze_data = bytearray()

        for i in range(sectors_needed):
            # Seek to sector
            sector_lba = BLAZE_LBA + i
            offset = sector_lba * SECTOR_SIZE + SECTOR_HEADER

            f.seek(offset)

            # Read data part of sector (2048 bytes)
            sector_data = f.read(DATA_PER_SECTOR)

            # How much do we need from this sector?
            bytes_needed = min(DATA_PER_SECTOR, BLAZE_SIZE - len(blaze_data))
            blaze_data.extend(sector_data[:bytes_needed])

            if (i + 1) % 1000 == 0:
                print(f"  {i+1}/{sectors_needed} sectors...")

    print(f"Extracted {len(blaze_data):,} bytes")
    print()

    # Write to file
    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(blaze_data)

    print(f"[OK] Vanilla BLAZE.ALL extracted!")
    print()
    print("Now run:")
    print(f"  py -3 compare_vanilla_patched.py {OUTPUT_FILE} output/BLAZE.ALL")

    return True

if __name__ == '__main__':
    import sys
    success = extract_blaze()
    sys.exit(0 if success else 1)
