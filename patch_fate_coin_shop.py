#!/usr/bin/env python3
"""
Patch Fate Coin Shop prices in BLAZE.ALL

This script reads fate_coin_shop.json and patches the prices
into all 10 locations in BLAZE.ALL where the shop data is stored.

The prices are the same for all 8 character classes.
Only the items differ at certain indices (10, 16, 20, 22).
"""

import json
import sys
import os

# Shop data offsets in BLAZE.ALL (10 copies for different game areas)
SHOP_OFFSETS = [
    0x00B1443C,
    0x00B14C3C,
    0x00B1EC24,
    0x00B1F424,
    0x00B29344,
    0x00B34C38,
    0x00B35438,
    0x00B402E8,
    0x00B4C41C,
    0x00B4CC1C,
]

NUM_ITEMS = 23  # Number of items in the shop


def get_item_name(item_data):
    """Get item name from item data (handles both formats)."""
    if 'item' in item_data:
        return item_data['item']
    elif 'item_by_class' in item_data:
        # Return first class-specific item as example
        items = item_data['item_by_class']
        first_class = list(items.keys())[0]
        return f"{items[first_class]} (varies by class)"
    return "Unknown"


def load_shop_data(json_path):
    """Load shop data from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def patch_blaze_all(blaze_path, shop_data, dry_run=False):
    """Patch BLAZE.ALL with new shop prices."""

    # Build price array from shop data
    items = shop_data['items']
    if len(items) != NUM_ITEMS:
        print(f"Error: Expected {NUM_ITEMS} items, got {len(items)}")
        return False

    prices = []
    for item in items:
        price = item['price']
        if not (0 <= price <= 255):
            print(f"Error: Price {price} for index {item['index']} out of range (0-255)")
            return False
        prices.append(price)

    print("Fate Coin Shop Prices:")
    print("=" * 60)
    for item in items:
        default = item.get('default_price', '?')
        name = get_item_name(item)
        changed = " [MODIFIED]" if item['price'] != default else ""
        print(f"  {item['index']:2d}. {name:35s} = {item['price']:3d} FC{changed}")
    print("=" * 60)
    print()

    if dry_run:
        print("DRY RUN - No changes written")
        return True

    # Read BLAZE.ALL
    with open(blaze_path, 'rb') as f:
        data = bytearray(f.read())

    # Patch all locations
    for offset in SHOP_OFFSETS:
        print(f"Patching offset 0x{offset:08X}...")
        for i, price in enumerate(prices):
            data[offset + i] = price

    # Write back
    with open(blaze_path, 'wb') as f:
        f.write(data)

    print(f"\nSuccessfully patched {len(SHOP_OFFSETS)} locations in {blaze_path}")
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    json_path = os.path.join(script_dir, 'fate_coin_shop.json')
    blaze_path = os.path.join(script_dir, 'work', 'BLAZE.ALL')

    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        return 1

    if not os.path.exists(blaze_path):
        print(f"Error: {blaze_path} not found")
        print("Make sure work/BLAZE.ALL exists (copy from extract/)")
        return 1

    print("Fate Coin Shop Patcher")
    print("=" * 60)
    print(f"JSON:  {json_path}")
    print(f"Target: {blaze_path}")
    print()

    shop_data = load_shop_data(json_path)

    if not patch_blaze_all(blaze_path, shop_data, dry_run):
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
