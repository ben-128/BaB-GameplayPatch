#!/usr/bin/env python3
"""
Deep search in SLES_008.45 for auction prices
Try multiple patterns and formats
"""

import struct
from pathlib import Path

SLES_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\SLES_008.45")

# Known auction prices
PRICES = [10, 22, 24, 26, 28, 36, 46, 72]

def search_all_patterns():
    """Search for prices in various formats"""
    print("=" * 70)
    print("  DEEP SEARCH IN SLES_008.45")
    print("=" * 70)
    print()

    data = SLES_PATH.read_bytes()
    print(f"File size: {len(data):,} bytes")
    print()

    results = []

    # Pattern 1: [10, 22, 24, 26, 28] as consecutive 16-bit LE
    print("[1] Searching [10, 22, 24, 26, 28] as 16-bit LE...")
    pattern = struct.pack('<5H', 10, 22, 24, 26, 28)
    pos = data.find(pattern)
    if pos != -1:
        print(f"    FOUND at 0x{pos:06X}!")
        results.append(('16bit_seq', pos))
    else:
        print(f"    Not found")

    # Pattern 2: [10, 22, 36] as 16-bit LE
    print("[2] Searching [10, 22, 36] as 16-bit LE...")
    pattern = struct.pack('<3H', 10, 22, 36)
    pos = data.find(pattern)
    if pos != -1:
        print(f"    FOUND at 0x{pos:06X}!")
        results.append(('16bit_short', pos))
    else:
        print(f"    Not found")

    # Pattern 3: As bytes
    print("[3] Searching [10, 22, 36, 46] as bytes...")
    pattern = bytes([10, 22, 36, 46])
    pos = data.find(pattern)
    if pos != -1:
        print(f"    FOUND at 0x{pos:06X}!")
        results.append(('bytes', pos))
    else:
        print(f"    Not found")

    # Pattern 4: As 32-bit values
    print("[4] Searching [10, 22, 36] as 32-bit LE...")
    pattern = struct.pack('<3I', 10, 22, 36)
    pos = data.find(pattern)
    if pos != -1:
        print(f"    FOUND at 0x{pos:06X}!")
        results.append(('32bit', pos))
    else:
        print(f"    Not found")

    # Pattern 5: Look for ANY sequence of 4+ known prices
    print("[5] Searching for any 4 consecutive known prices...")
    for i in range(len(PRICES) - 3):
        pattern = struct.pack('<4H', *PRICES[i:i+4])
        pos = data.find(pattern)
        if pos != -1:
            print(f"    FOUND {PRICES[i:i+4]} at 0x{pos:06X}!")
            results.append(('any_4', pos))
            break
    else:
        print(f"    Not found")

    print()

    if not results:
        print("=" * 70)
        print("  NO PRICE PATTERNS FOUND IN EXECUTABLE")
        print("=" * 70)
        print()
        print("The auction prices are NOT in SLES_008.45 either.")
        print()
        print("FINAL CONCLUSION:")
        print("- NOT in BLAZE.ALL")
        print("- NOT in LEVELS.DAT")
        print("- NOT in SLES_008.45")
        print()
        print("The prices must be:")
        print("1. Calculated by complex code logic")
        print("2. Stored in a format we haven't tried")
        print("3. In overlay code loaded dynamically")
        print()
        print("At this point, finding auction prices requires:")
        print("- Memory debugging while game runs")
        print("- Reverse engineering the executable")
        print("- Or accepting defeat...")
    else:
        print("=" * 70)
        print("  FOUND PATTERNS!")
        print("=" * 70)
        print()
        for pattern_type, offset in results:
            print(f"{pattern_type} at 0x{offset:06X}")
            # Show context
            context = data[offset:offset+32]
            words = [struct.unpack('<H', context[i:i+2])[0] for i in range(0, 32, 2)]
            print(f"  Context: {words}")
            print()

if __name__ == '__main__':
    search_all_patterns()
