#!/usr/bin/env python3
"""
Analyze PS1 memory card save file to look for auction prices
"""

import struct
from pathlib import Path

MCR_PATH = Path(r"C:\Perso\BabLangue\other\ePSXe2018\memcards\epsxe000.mcr")

# Known auction prices to search for
PRICES = [10, 22, 24, 26, 28, 36, 46, 72]

def analyze_mcr():
    """Analyze the memory card file"""
    print("=" * 70)
    print("  PS1 MEMORY CARD ANALYZER")
    print("=" * 70)
    print()

    if not MCR_PATH.exists():
        print(f"[ERROR] Memory card not found: {MCR_PATH}")
        return False

    data = MCR_PATH.read_bytes()
    print(f"Memory card: {MCR_PATH}")
    print(f"Size: {len(data):,} bytes")
    print()

    # PS1 memory card structure:
    # - 128 byte header
    # - 15 slots of 8192 bytes each
    # Total: 128 + (15 * 8192) = 122,880 bytes (standard)

    expected_size = 128 + (15 * 8192)
    if len(data) != expected_size:
        print(f"[WARNING] Unusual size (expected {expected_size:,} bytes)")
    print()

    # Search for price patterns
    print("-" * 70)
    print("SEARCHING FOR AUCTION PRICE PATTERNS...")
    print("-" * 70)
    print()

    # Pattern 1: Look for [10, 22] sequence as 16-bit words
    pattern_10_22 = struct.pack('<2H', 10, 22)
    matches_10_22 = []
    pos = 0
    while True:
        pos = data.find(pattern_10_22, pos)
        if pos == -1:
            break
        matches_10_22.append(pos)
        pos += 1

    print(f"Pattern [10, 22] (16-bit): {len(matches_10_22)} match(es)")
    for offset in matches_10_22[:10]:
        # Show which slot this is in
        if offset < 128:
            slot = "Header"
        else:
            slot = (offset - 128) // 8192

        # Read surrounding words
        words = []
        for i in range(16):
            if offset + i*2 + 2 <= len(data):
                val = struct.unpack('<H', data[offset+i*2:offset+i*2+2])[0]
                words.append(val)

        print(f"  Offset 0x{offset:06X} (Slot {slot}): {words}")
    print()

    # Pattern 2: Look for [10, 22, 36] as bytes
    pattern_bytes = bytes([10, 22, 36])
    matches_bytes = []
    pos = 0
    while True:
        pos = data.find(pattern_bytes, pos)
        if pos == -1:
            break
        matches_bytes.append(pos)
        pos += 1

    print(f"Pattern [10, 22, 36] (bytes): {len(matches_bytes)} match(es)")
    for offset in matches_bytes[:10]:
        if offset < 128:
            slot = "Header"
        else:
            slot = (offset - 128) // 8192

        vals = list(data[offset:offset+20])
        print(f"  Offset 0x{offset:06X} (Slot {slot}): {vals}")
    print()

    # Pattern 3: Look for any of the distinctive prices
    print("Individual price occurrences:")
    for price in [10, 22, 36, 46]:
        pattern = struct.pack('<H', price)
        count = data.count(pattern)
        print(f"  Price {price}: {count} occurrences")

        # Show first few
        pos = 0
        shown = 0
        for _ in range(5):
            pos = data.find(pattern, pos)
            if pos == -1:
                break
            if pos < 128:
                slot = "Header"
            else:
                slot = (pos - 128) // 8192
            print(f"    -> 0x{pos:06X} (Slot {slot})")
            pos += 1
            shown += 1
        if shown == 0:
            print(f"    (none found)")
    print()

    # Pattern 4: Look for the exact sequence we found in BLAZE.ALL
    # [10, 16, 22, 13, 16, 23, 13, 24, 25, 26, 27, 28, 29, 36, 16, 46]
    exact_pattern = struct.pack('<16H', 10, 16, 22, 13, 16, 23, 13, 24, 25, 26, 27, 28, 29, 36, 16, 46)
    pos = data.find(exact_pattern)

    print(f"Exact BLAZE.ALL price table pattern:")
    if pos != -1:
        if pos < 128:
            slot = "Header"
        else:
            slot = (pos - 128) // 8192
        print(f"  [FOUND] at offset 0x{pos:06X} (Slot {slot})")
        print(f"  This means the save file contains a COPY of the price table!")
        print(f"  The game might be reading prices from the save instead of BLAZE.ALL!")
    else:
        print(f"  [NOT FOUND] in save file")
    print()

    # Analyze each save slot
    print("-" * 70)
    print("ANALYZING SAVE SLOTS...")
    print("-" * 70)
    print()

    for slot in range(15):
        slot_offset = 128 + (slot * 8192)
        slot_data = data[slot_offset:slot_offset+8192]

        # Check if slot is used (first byte != 0x00 or some header data)
        if slot_data[:4] == b'\x00\x00\x00\x00':
            continue

        # Try to read slot header (first 128 bytes usually contain save info)
        header = slot_data[:128]

        # Look for "BLAZE" or "BLADE" text
        if b'BLAZE' in header or b'BLADE' in header:
            print(f"Slot {slot}: Contains 'BLAZE/BLADE' text")

            # Search this slot for price patterns
            pattern = struct.pack('<H', 10)
            if pattern in slot_data:
                print(f"  -> Contains price value 10")
            pattern = struct.pack('<H', 22)
            if pattern in slot_data:
                print(f"  -> Contains price value 22")
            print()

    print("=" * 70)
    print("  CONCLUSION")
    print("=" * 70)
    print()

    if pos != -1:
        print("[CRITICAL] The exact price table from BLAZE.ALL exists in the save!")
        print()
        print("This explains why patching doesn't work:")
        print("The game loads auction prices from the SAVE FILE, not from BLAZE.ALL!")
        print()
        print("Solution: Delete all saves and start completely fresh!")
    else:
        print("Price table not found in save file.")
        print("The mystery continues...")

    return True

if __name__ == '__main__':
    analyze_mcr()
