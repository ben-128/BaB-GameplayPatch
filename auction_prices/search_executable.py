#!/usr/bin/env python3
"""
Search for auction prices in the PS1 executable (SLES_008.45)
First, we need to extract it from the BIN file.
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")
WORK_DIR = BIN_PATH.parent
SLES_PATH = WORK_DIR / "SLES_008.45"

# Known auction prices to search for
PRICES = [10, 22, 24, 26, 28, 36, 46, 72]

def extract_sles_from_bin():
    """Extract SLES_008.45 from the BIN file"""
    # PS1 executables are usually in the first sectors
    # We need to parse the ISO9660 filesystem

    print("=" * 70)
    print("  EXTRACT SLES_008.45 FROM BIN")
    print("=" * 70)
    print()

    # For now, let's check if it already exists
    if SLES_PATH.exists():
        print(f"[OK] SLES_008.45 already exists: {SLES_PATH}")
        print(f"     Size: {SLES_PATH.stat().st_size:,} bytes")
        return True

    print("[INFO] SLES_008.45 not found in work directory")
    print()
    print("To extract it, you can:")
    print("1. Use a tool like IsoBuster, CDMage, or 7-Zip")
    print("2. Mount the BIN file and copy SLES_008.45")
    print("3. Use command line: isoinfo, binchunker, etc.")
    print()
    return False

def search_for_prices(file_path):
    """Search for auction price patterns in a file"""
    print("=" * 70)
    print(f"  SEARCHING: {file_path.name}")
    print("=" * 70)
    print()

    data = file_path.read_bytes()
    print(f"File size: {len(data):,} bytes")
    print()

    # Search patterns:
    # 1. Consecutive 16-bit little-endian values
    # 2. Consecutive 8-bit values
    # 3. Individual occurrences

    print("-" * 70)
    print("PATTERN 1: Looking for sequence [10, 22] as 16-bit words...")
    print("-" * 70)
    pattern_16bit = struct.pack('<2H', 10, 22)
    matches_16 = []
    pos = 0
    while True:
        pos = data.find(pattern_16bit, pos)
        if pos == -1:
            break
        matches_16.append(pos)
        pos += 1

    print(f"Found {len(matches_16)} match(es) for [10, 22] pattern")
    for offset in matches_16[:10]:  # Show first 10
        vals = []
        for i in range(16):
            if offset + i*2 + 2 <= len(data):
                val = struct.unpack('<H', data[offset+i*2:offset+i*2+2])[0]
                vals.append(val)
        print(f"  Offset 0x{offset:08X}: {vals}")
    print()

    print("-" * 70)
    print("PATTERN 2: Looking for sequence [10, 22, 36] as bytes...")
    print("-" * 70)
    pattern_8bit = bytes([10, 22, 36])
    matches_8 = []
    pos = 0
    while True:
        pos = data.find(pattern_8bit, pos)
        if pos == -1:
            break
        matches_8.append(pos)
        pos += 1

    print(f"Found {len(matches_8)} match(es) for [10, 22, 36] byte pattern")
    for offset in matches_8[:10]:
        vals = list(data[offset:offset+20])
        print(f"  Offset 0x{offset:08X}: {vals}")
    print()

    print("-" * 70)
    print("PATTERN 3: Individual price occurrences (first 20)...")
    print("-" * 70)
    for price in [10, 22, 36, 46]:
        # Search as 16-bit LE
        pattern = struct.pack('<H', price)
        count = data.count(pattern)
        print(f"Price {price}: {count} occurrences as 16-bit word")

        # Show first few
        pos = 0
        shown = 0
        while shown < 5:
            pos = data.find(pattern, pos)
            if pos == -1:
                break
            print(f"  -> 0x{pos:08X}")
            pos += 1
            shown += 1

    print()
    return matches_16, matches_8

def main():
    print()

    # Try to find/extract SLES
    if not extract_sles_from_bin():
        print()
        print("=" * 70)
        print("  NEXT STEPS")
        print("=" * 70)
        print()
        print("Please extract SLES_008.45 from the BIN file to:")
        print(f"  {SLES_PATH}")
        print()
        print("Then run this script again.")
        return 1

    print()
    search_for_prices(SLES_PATH)

    print("=" * 70)
    print("  ANALYSIS")
    print("=" * 70)
    print()
    print("If we find the price patterns in SLES_008.45, that means")
    print("the auction prices are hardcoded in the executable, not in")
    print("BLAZE.ALL. We would then need to patch the executable instead.")
    print()

if __name__ == '__main__':
    import sys
    sys.exit(main())
