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

# Base price offset within item structure (only valid for item_entry format)
BASE_PRICE_OFFSET = 0x88


def is_valid_item_entry(data: bytes, offset: int, item_name: str) -> bool:
    """Validate that offset points to a real 128-byte item entry.
    Checks: exact name match + structural markers (b3F=0x00, b40=0x0C)."""
    if offset < 0 or offset + 0x89 >= len(data):
        return False
    # Check name
    name_data = data[offset:offset + 32]
    null_pos = name_data.find(b'\x00')
    if null_pos <= 0:
        return False
    found_name = name_data[:null_pos].decode('ascii', errors='ignore')
    if found_name != item_name:
        return False
    # Structural check: real item entries have 0x00 at +0x3F and 0x0C at +0x40
    return data[offset + 0x3F] == 0x00 and data[offset + 0x40] == 0x0C

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

        # Patch ALL structurally valid item_entry occurrences
        # (base price at +0x88 only exists in 128-byte item_entry format)
        all_offsets = item.get('all_offsets', [])
        if not all_offsets:
            offset = item.get('offset_decimal', 0)
            if offset > 0:
                all_offsets = [f"0x{offset:08X}"]

        items_processed += 1
        patched_this = 0

        for offset_hex in all_offsets:
            try:
                offset = int(offset_hex, 16)
            except (ValueError, TypeError):
                continue
            if offset <= 0:
                continue
            if not is_valid_item_entry(data, offset, name):
                continue

            total_occurrences += 1
            price_offset = offset + BASE_PRICE_OFFSET
            current_price = struct.unpack('<H', data[price_offset:price_offset+2])[0]

            if current_price == 0:
                continue

            struct.pack_into('<H', data, price_offset, 0)
            total_patched += 1
            patched_this += 1

        if items_processed <= 5 and patched_this > 0:
            print(f"  {name}: {patched_this} copies patched")

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
