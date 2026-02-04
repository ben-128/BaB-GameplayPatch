#!/usr/bin/env python3
"""
Look for item inventory data in save file
Specifically looking for Shortsword (22), Leather Armor (36), Healing Potion (10)
"""

import struct
from pathlib import Path

MCR_PATH = Path(r"C:\Perso\BabLangue\other\ePSXe2018\memcards\epsxe000.mcr")

def main():
    print("=" * 70)
    print("  SEARCH FOR INVENTORY ITEMS IN SAVE FILE")
    print("=" * 70)
    print()

    data = MCR_PATH.read_bytes()

    # Look for patterns that might be item data
    # Pattern: [price, other_data...]

    print("Looking for potential item structures...")
    print()

    # Search for item name strings
    item_names = [
        (b'Shortsword', 22),
        (b'shortsword', 22),
        (b'Leather', 36),
        (b'leather', 36),
        (b'Healing', 10),
        (b'healing', 10),
    ]

    for name_bytes, expected_price in item_names:
        pos = data.find(name_bytes)
        if pos != -1:
            if pos < 128:
                slot = "Header"
            else:
                slot = (pos - 128) // 8192

            print(f"Found '{name_bytes.decode()}' at 0x{pos:06X} (Slot {slot})")

            # Look for the price value near the name
            # Check 64 bytes before and after
            search_start = max(0, pos - 64)
            search_end = min(len(data), pos + len(name_bytes) + 64)
            region = data[search_start:search_end]

            price_pattern = struct.pack('<H', expected_price)
            price_pos = region.find(price_pattern)

            if price_pos != -1:
                absolute_pos = search_start + price_pos
                offset_from_name = price_pos - (pos - search_start)
                print(f"  -> Price {expected_price} found at offset {offset_from_name:+d} from name")
                print(f"     Absolute position: 0x{absolute_pos:06X}")

                # Show context around price
                ctx_start = max(0, absolute_pos - 8)
                ctx_end = min(len(data), absolute_pos + 16)
                context_words = []
                for i in range(ctx_start, ctx_end - 1, 2):
                    val = struct.unpack('<H', data[i:i+2])[0]
                    context_words.append(val)
                print(f"     Context: {context_words}")
            else:
                print(f"  -> Price {expected_price} NOT found near name")
            print()

    print("-" * 70)
    print()

    # Look for the specific pattern from earlier analysis
    # Slot 4 had: [36, 72, 78, 47, 45, ...  , 22, 21, 52, 25]
    print("Checking Slot 4 (had interesting pattern)...")
    slot_4_start = 128 + (4 * 8192)
    slot_4_end = slot_4_start + 8192
    slot_4_data = data[slot_4_start:slot_4_end]

    # Search for [36, 72] pattern (Leather Armor price + something)
    pattern = struct.pack('<2H', 36, 72)
    pos = slot_4_data.find(pattern)
    if pos != -1:
        print(f"Found [36, 72] pattern at offset 0x{pos:04X} in Slot 4")
        print(f"Absolute: 0x{slot_4_start + pos:06X}")

        # Show surrounding data
        words = []
        for i in range(0, 32, 2):
            if pos + i + 2 <= len(slot_4_data):
                val = struct.unpack('<H', slot_4_data[pos+i:pos+i+2])[0]
                words.append(val)

        print(f"32 words starting here: {words[:16]}")
        print(f"                        {words[16:]}")
        print()

        # Check if price 22 (Shortsword) appears nearby
        for i, w in enumerate(words):
            if w == 22:
                print(f"  -> Price 22 (Shortsword) at word offset +{i}")
            if w == 10:
                print(f"  -> Price 10 (Healing Potion) at word offset +{i}")

    print()
    print("=" * 70)
    print("  CONCLUSION")
    print("=" * 70)
    print()
    print("If item prices are found NEAR item names in the save,")
    print("it means item prices are STORED WITH ITEMS in inventory.")
    print()
    print("In that case:")
    print("- Items already in inventory keep their old prices")
    print("- You need to GET NEW ITEMS from auction to see new prices")
    print("- OR create a new character with empty inventory")

if __name__ == '__main__':
    main()
