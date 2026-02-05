#!/usr/bin/env python3
"""
Patch auction base prices to 0 in BLAZE.ALL - ALL OCCURRENCES

Formula: Auction Price = Base@0x88 + 2 * sum(stat_fields)
By setting Base@0x88 to 0, we reduce auction prices without affecting gameplay stats.

This script finds ALL copies of each item structure and patches them all.
"""

import struct
import json
from pathlib import Path

# Paths
WORK_BLAZE = Path(__file__).parent.parent.parent / "output" / "BLAZE.ALL"
ITEMS_JSON = Path(__file__).parent.parent / "items" / "all_items_clean.json"

# Base price offset within item structure
BASE_PRICE_OFFSET = 0x88

def find_all_item_occurrences(data: bytes, item_name: str) -> list:
    """Find all occurrences of an item structure by searching for name pattern."""
    # Item structures have name padded with nulls to 16 bytes
    name_bytes = item_name.encode('ascii')
    padding = 16 - len(name_bytes)
    if padding > 0:
        search_pattern = name_bytes + b'\x00' * padding
    else:
        search_pattern = name_bytes[:16]

    # Bad regions that are NOT item data (spells, UI strings, herb name lists)
    BAD_RANGES = [
        (0x00908000, 0x00910000),  # Spells area
        (0x0090A000, 0x0090C000),  # UI strings, herb names list
    ]

    occurrences = []
    idx = 0
    while True:
        idx = data.find(search_pattern, idx)
        if idx == -1:
            break

        # Check if this offset is in a bad region
        in_bad_region = any(start <= idx < end for start, end in BAD_RANGES)

        if not in_bad_region:
            occurrences.append(idx)
        idx += 1

    return occurrences

def main():
    print("=" * 60)
    print(" Patching Auction Base Prices - ALL OCCURRENCES")
    print("=" * 60)
    print()

    # Load BLAZE.ALL
    if not WORK_BLAZE.exists():
        print(f"[ERROR] BLAZE.ALL not found: {WORK_BLAZE}")
        return 1

    data = bytearray(WORK_BLAZE.read_bytes())
    print(f"Loaded BLAZE.ALL: {len(data):,} bytes")

    # Load items data
    if not ITEMS_JSON.exists():
        print(f"[ERROR] Items JSON not found: {ITEMS_JSON}")
        return 1

    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)

    items = items_data.get('items', [])
    print(f"Found {len(items)} unique items in database")
    print()

    # Track statistics
    total_occurrences = 0
    total_patched = 0
    items_processed = 0

    # Process each unique item
    seen_names = set()

    for item in items:
        name = item.get('name', '')

        if not name or name in seen_names:
            continue

        seen_names.add(name)

        # Find ALL occurrences of this item
        occurrences = find_all_item_occurrences(data, name)

        if not occurrences:
            continue

        total_occurrences += len(occurrences)
        items_processed += 1

        # Patch each occurrence
        patched_this_item = 0
        for offset in occurrences:
            price_offset = offset + BASE_PRICE_OFFSET
            if price_offset + 2 > len(data):
                continue

            current_price = struct.unpack('<H', data[price_offset:price_offset+2])[0]

            # Skip if already 0
            if current_price == 0:
                continue

            # Set to 0
            struct.pack_into('<H', data, price_offset, 0)
            patched_this_item += 1
            total_patched += 1

        # Show progress for items with multiple copies
        if items_processed <= 5 or len(occurrences) > 1:
            print(f"  {name}: {len(occurrences)} copies, {patched_this_item} patched")

    print(f"  ...")
    print()
    print(f"Items processed: {items_processed}")
    print(f"Total occurrences found: {total_occurrences}")
    print(f"Total base prices patched: {total_patched}")

    # Save patched BLAZE.ALL
    WORK_BLAZE.write_bytes(data)
    print()
    print(f"[OK] Saved patched BLAZE.ALL")

    return 0

if __name__ == '__main__':
    exit(main())
