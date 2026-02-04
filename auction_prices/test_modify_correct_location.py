#!/usr/bin/env python3
"""
Test script to modify auction prices at the CORRECT location: 0x002EA49A
This is the location the game actually reads from!
"""

from pathlib import Path
import struct
import shutil
from datetime import datetime

# CORRECT location of the price table (the one the game actually reads!)
PRICE_TABLE_BASE = 0x002EA49A  # NOT 0x002EA500!

# Test modifications - same as before
TEST_MODIFICATIONS = [
    # (word_index, item_name, old_price, new_price)
    (0, "Healing Potion", 10, 99),
    (2, "Shortsword", 22, 88),
    (13, "Leather Armor", 36, 77),
]

def main():
    script_dir = Path(__file__).parent
    parent_dir = script_dir.parent
    work_dir = parent_dir / "work"
    blaze_all = work_dir / "BLAZE.ALL"

    if not blaze_all.exists():
        print(f"Error: {blaze_all} not found")
        return 1

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = work_dir / f"BLAZE.ALL.backup_{timestamp}"

    print("="*70)
    print("AUCTION PRICE MODIFIER - CORRECT LOCATION TEST")
    print("="*70)
    print()
    print(f"!!! PATCHING CORRECT LOCATION: 0x{PRICE_TABLE_BASE:08X} !!!")
    print()
    print(f"Source: {blaze_all}")
    print(f"Backup: {backup}")
    print()

    print("Creating backup...")
    shutil.copy2(blaze_all, backup)
    print(f"OK Backup created: {backup}")
    print()

    # Read file
    print("Reading BLAZE.ALL...")
    data = bytearray(blaze_all.read_bytes())
    print(f"OK File size: {len(data):,} bytes")
    print()

    # Show current values
    print("="*70)
    print("CURRENT VALUES AT CORRECT PRICE TABLE")
    print("="*70)
    print()

    for word_idx, item_name, old_price, new_price in TEST_MODIFICATIONS:
        offset = PRICE_TABLE_BASE + (word_idx * 2)
        current_value = struct.unpack('<H', data[offset:offset+2])[0]

        status = "OK MATCH" if current_value == old_price else f"!! MISMATCH (expected {old_price})"
        print(f"Word[{word_idx:3d}] at 0x{offset:08X}: {current_value:5d} {status}")
        print(f"  -> {item_name}")

    print()

    # Apply modifications
    print("="*70)
    print("APPLYING MODIFICATIONS")
    print("="*70)
    print()

    for word_idx, item_name, old_price, new_price in TEST_MODIFICATIONS:
        offset = PRICE_TABLE_BASE + (word_idx * 2)
        current_value = struct.unpack('<H', data[offset:offset+2])[0]

        if current_value != old_price:
            print(f"WARNING: Word[{word_idx}] value is {current_value}, expected {old_price}")
            print(f"  Skipping modification for safety")
            continue

        # Write new value
        struct.pack_into('<H', data, offset, new_price)
        print(f"OK Word[{word_idx:3d}] 0x{offset:08X}: {old_price} -> {new_price} ({item_name})")

    print()

    # Write modified file
    print("="*70)
    print("WRITING MODIFIED FILE")
    print("="*70)
    print()

    print(f"Writing to {blaze_all}...")
    blaze_all.write_bytes(data)
    print("OK File written successfully")
    print()

    # Verify
    print("="*70)
    print("VERIFICATION")
    print("="*70)
    print()

    verify_data = blaze_all.read_bytes()
    all_good = True

    for word_idx, item_name, old_price, new_price in TEST_MODIFICATIONS:
        offset = PRICE_TABLE_BASE + (word_idx * 2)
        verified_value = struct.unpack('<H', verify_data[offset:offset+2])[0]

        if verified_value == new_price:
            print(f"OK Word[{word_idx:3d}]: {verified_value} (correct)")
        else:
            print(f"!! Word[{word_idx:3d}]: {verified_value} (expected {new_price})")
            all_good = False

    print()

    if all_good:
        print("="*70)
        print("SUCCESS - CORRECT LOCATION PATCHED!")
        print("="*70)
        print()
        print("NEXT STEPS:")
        print("1. Run: python ..\\patch_blaze_all.py")
        print("2. Test in-game - prices SHOULD change now!")
        print("3. Expected in-game auction prices:")
        print("   - Healing Potion: 99 gold (was 10)")
        print("   - Shortsword: 88 gold (was 22)")
        print("   - Leather Armor: 77 gold (was 36)")
    else:
        print("VERIFICATION FAILED")
        shutil.copy2(backup, blaze_all)

    return 0 if all_good else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
