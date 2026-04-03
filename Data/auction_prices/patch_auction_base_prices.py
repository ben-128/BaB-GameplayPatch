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

    # Item data lives in 0x006C0000-0x006E0000 range
    # Offsets outside this are false positives (overlay code, scripts, etc.)
    ITEM_RANGE_START = 0x006C0000
    ITEM_RANGE_END   = 0x006E0000

    occurrences = []
    idx = ITEM_RANGE_START
    while idx < min(ITEM_RANGE_END, len(data)):
        idx = data.find(search_pattern, idx)
        if idx == -1 or idx >= ITEM_RANGE_END:
            break
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

        # Use only the verified primary offset (offset_decimal)
        # Searching by name produces false positives for short names
        offset = item.get('offset_decimal', 0)
        if offset <= 0:
            continue

        total_occurrences += 1
        items_processed += 1

        price_offset = offset + BASE_PRICE_OFFSET
        if price_offset + 2 > len(data):
            continue

        current_price = struct.unpack('<H', data[price_offset:price_offset+2])[0]

        # Skip if already 0
        if current_price == 0:
            continue

        # Set to 0
        struct.pack_into('<H', data, price_offset, 0)
        total_patched += 1

        if items_processed <= 5:
            print(f"  {name}: price {current_price} -> 0")

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
