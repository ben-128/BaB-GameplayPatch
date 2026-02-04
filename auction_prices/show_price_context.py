#!/usr/bin/env python3
"""
Show context around price values in the save file
"""

import struct
from pathlib import Path

MCR_PATH = Path(r"C:\Perso\BabLangue\other\ePSXe2018\memcards\epsxe000.mcr")

def show_context(data, offset, label, context_words=16):
    """Show context around an offset"""
    print(f"{label} at 0x{offset:06X}:")

    # Determine slot
    if offset < 128:
        slot = "Header"
    else:
        slot = (offset - 128) // 8192
    print(f"  Location: Slot {slot}")

    # Show as 16-bit words
    start = offset - 4  # Start 4 bytes before
    words = []
    positions = []

    for i in range(context_words):
        pos = start + i * 2
        if pos >= 0 and pos + 2 <= len(data):
            val = struct.unpack('<H', data[pos:pos+2])[0]
            words.append(val)
            positions.append(pos)
        else:
            words.append('--')
            positions.append(None)

    # Print with markers
    print(f"  Context (16-bit words):")
    marker_index = 2  # The target value is at index 2 (after skipping 4 bytes = 2 words)
    for i, (val, pos) in enumerate(zip(words, positions)):
        marker = " <-- TARGET" if i == marker_index else ""
        if pos is not None:
            print(f"    [{i-marker_index:+2d}] 0x{pos:06X}: {val:5} (0x{val:04X}){marker}")
        else:
            print(f"    [{i-marker_index:+2d}]         : {val}")

    # Show as bytes too
    byte_start = offset - 8
    byte_end = offset + 8
    if byte_start >= 0 and byte_end <= len(data):
        byte_data = data[byte_start:byte_end]
        print(f"  Context (bytes): {' '.join(f'{b:02X}' for b in byte_data)}")
        print(f"                   {' '.join('^^' if i == 8 or i == 9 else '  ' for i in range(16))}")

    print()

def main():
    print("=" * 70)
    print("  SAVE FILE PRICE CONTEXT ANALYSIS")
    print("=" * 70)
    print()

    data = MCR_PATH.read_bytes()
    print(f"Memory card: {MCR_PATH}")
    print(f"Size: {len(data):,} bytes")
    print()

    # Show context for each price
    prices_to_check = [
        (10, 3),   # Show first 3 occurrences
        (22, 3),
        (36, 3),
        (46, 3),
    ]

    for price, max_show in prices_to_check:
        pattern = struct.pack('<H', price)
        print("-" * 70)
        print(f"PRICE VALUE: {price}")
        print("-" * 70)
        print()

        pos = 0
        count = 0

        while count < max_show:
            pos = data.find(pattern, pos)
            if pos == -1:
                break

            show_context(data, pos, f"Occurrence #{count + 1}")
            pos += 2
            count += 1

        if count == 0:
            print("  (No occurrences found)")
            print()

    print("=" * 70)
    print("  ANALYSIS")
    print("=" * 70)
    print()
    print("Look for patterns:")
    print("- Are these values surrounded by other item-related data?")
    print("- Do you see sequences like [10, ?, 22, ?, 36] ?")
    print("- Are there item names or IDs nearby?")
    print("- Do the values appear in structures (repeated patterns)?")

if __name__ == '__main__':
    main()
