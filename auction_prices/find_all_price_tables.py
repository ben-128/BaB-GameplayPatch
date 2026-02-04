#!/usr/bin/env python3
"""
Search BLAZE.ALL for ALL occurrences of the auction price pattern.
There might be multiple copies that we need to patch!
"""

import struct
from pathlib import Path

BLAZE_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\BLAZE.ALL")

# Known prices (original values)
# Word indices based on the pattern we found
KNOWN_PRICES = {
    0: 10,   # Healing Potion
    2: 22,   # Shortsword
    7: 24,   # Wooden Wand / Normal Sword
    9: 26,   # Tomahawk
    11: 28,  # Dagger
    13: 36,  # Leather Armor
    15: 46,  # Leather Shield
}

def check_price_table(data, offset):
    """Check if offset contains the known price pattern"""
    matches = 0
    mismatches = []

    for word_idx, expected_price in KNOWN_PRICES.items():
        word_offset = offset + (word_idx * 2)
        if word_offset + 2 > len(data):
            return 0, []

        actual_price = struct.unpack('<H', data[word_offset:word_offset+2])[0]
        if actual_price == expected_price:
            matches += 1
        else:
            mismatches.append((word_idx, expected_price, actual_price))

    return matches, mismatches

def find_all_price_tables():
    """Find all locations in BLAZE.ALL with the price pattern"""
    print("=" * 70)
    print("  SEARCHING BLAZE.ALL FOR ALL PRICE TABLE COPIES")
    print("=" * 70)
    print()

    if not BLAZE_PATH.exists():
        print(f"[ERROR] BLAZE.ALL not found: {BLAZE_PATH}")
        return []

    data = BLAZE_PATH.read_bytes()
    print(f"BLAZE.ALL size: {len(data):,} bytes")
    print()

    print("Known price pattern:")
    for word_idx, price in sorted(KNOWN_PRICES.items()):
        print(f"  Word[{word_idx:2d}] = {price}")
    print()

    print("-" * 70)
    print("Searching for pattern matches...")
    print("-" * 70)
    print()

    # Strategy 1: Search for the distinctive sequence [10, ?, 22]
    # This is word[0]=10, word[2]=22
    pattern = struct.pack('<H', 10)  # Start with healing potion price

    candidates = []
    pos = 0

    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break

        # Check if this could be word[0] of a price table
        matches, mismatches = check_price_table(data, pos)

        if matches >= 5:  # At least 5 out of 7 prices match
            candidates.append({
                'offset': pos,
                'matches': matches,
                'mismatches': mismatches
            })

        pos += 1

    print(f"Found {len(candidates)} potential price table(s):")
    print()

    for i, candidate in enumerate(candidates, 1):
        offset = candidate['offset']
        matches = candidate['matches']
        mismatches = candidate['mismatches']

        print(f"Location #{i}: 0x{offset:08X}")
        print(f"  Matches: {matches}/{len(KNOWN_PRICES)}")

        if mismatches:
            print(f"  Mismatches:")
            for word_idx, expected, actual in mismatches:
                print(f"    Word[{word_idx}]: expected {expected}, got {actual}")

        # Show all 16 words
        print(f"  All values:")
        for j in range(16):
            word_offset = offset + j * 2
            if word_offset + 2 <= len(data):
                val = struct.unpack('<H', data[word_offset:word_offset+2])[0]
                marker = ""
                if j in KNOWN_PRICES:
                    if val == KNOWN_PRICES[j]:
                        marker = " <- MATCH"
                    else:
                        marker = f" <- MISMATCH (expected {KNOWN_PRICES[j]})"
                print(f"    Word[{j:2d}] = {val:3d} (0x{val:04X}){marker}")
        print()

    return candidates

def main():
    candidates = find_all_price_tables()

    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()

    if not candidates:
        print("No price table patterns found!")
        print()
        print("This is strange because we know 0x002EA500 should match.")
        print("The original BLAZE.ALL might have been modified.")
        return 1

    perfect_matches = [c for c in candidates if c['matches'] == len(KNOWN_PRICES)]

    print(f"Total locations found: {len(candidates)}")
    print(f"Perfect matches (7/7): {len(perfect_matches)}")
    print()

    if len(perfect_matches) > 1:
        print("!" * 70)
        print("  MULTIPLE PRICE TABLES FOUND!")
        print("!" * 70)
        print()
        print("This explains why patching 0x002EA500 didn't work!")
        print("The game might be reading from a different copy.")
        print()
        print("Locations to patch:")
        for i, c in enumerate(perfect_matches, 1):
            print(f"  {i}. 0x{c['offset']:08X}")
        print()
        print("We need to patch ALL of these locations!")
    else:
        print("Only one price table found at the expected location.")
        print("The mystery continues...")

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
