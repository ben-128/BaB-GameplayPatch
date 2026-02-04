#!/usr/bin/env python3
"""
Check if any 999 values appear in save file (to see if game copies price table to save)
"""

import struct
from pathlib import Path

MCR_PATH = Path(r"C:\Perso\BabLangue\other\ePSXe2018\memcards\epsxe000.mcr")

def main():
    print("=" * 70)
    print("  CHECK FOR 999 VALUES IN SAVE FILE")
    print("=" * 70)
    print()

    if not MCR_PATH.exists():
        print(f"[ERROR] Save file not found: {MCR_PATH}")
        return

    data = MCR_PATH.read_bytes()
    print(f"Save file: {MCR_PATH}")
    print(f"Size: {len(data):,} bytes")
    print()

    # Search for 999 as 16-bit word
    pattern_999 = struct.pack('<H', 999)
    matches = []
    pos = 0

    while True:
        pos = data.find(pattern_999, pos)
        if pos == -1:
            break
        matches.append(pos)
        pos += 1

    print(f"Found {len(matches)} occurrence(s) of value 999")
    print()

    if len(matches) == 0:
        print("[GOOD] No 999 values in save file.")
        print()
        print("This means:")
        print("- The game does NOT save the price table")
        print("- You can use an existing character")
        print("- No need to create a new character")
        return

    # If found, show context
    print("[INFO] Found some 999 values, checking context...")
    print()

    for i, offset in enumerate(matches[:5], 1):
        if offset < 128:
            slot = "Header"
        else:
            slot = (offset - 128) // 8192

        print(f"Match #{i} at 0x{offset:06X} (Slot {slot}):")

        # Show as words
        start = offset
        words = []
        for j in range(8):
            if start + j*2 + 2 <= len(data):
                val = struct.unpack('<H', data[start+j*2:start+j*2+2])[0]
                words.append(val)

        print(f"  Context: {words}")

        # Check if it's followed by more 999s (which would indicate price table)
        consecutive_999 = 0
        for w in words:
            if w == 999:
                consecutive_999 += 1
            else:
                break

        if consecutive_999 >= 4:
            print(f"  [WARNING] {consecutive_999} consecutive 999s - might be price table!")
        print()

    print("=" * 70)
    print("CONCLUSION:")
    print("=" * 70)
    print()

    # Check for pattern of multiple 999s
    pattern_multiple = struct.pack('<4H', 999, 999, 999, 999)
    if pattern_multiple in data:
        print("[WARNING] Multiple consecutive 999s found!")
        print()
        print("The game MIGHT be saving the price table to save file.")
        print("To be safe: Create a NEW character after loading the patched BIN.")
    else:
        print("[GOOD] No consecutive 999 pattern found.")
        print()
        print("The price table is NOT saved to character save.")
        print("You can use an existing character - no need to create new one!")

if __name__ == '__main__':
    main()
