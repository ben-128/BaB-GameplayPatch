#!/usr/bin/env python3
"""
Patch ALL prices in the table to ridiculous values
This will help us see if ANY part of this table affects the game
"""

from pathlib import Path
import struct
import shutil
from datetime import datetime

PRICE_TABLE_BASE = 0x002EA49A

def main():
    script_dir = Path(__file__).parent
    work_dir = script_dir.parent / "work"
    blaze_all = work_dir / "BLAZE.ALL"

    if not blaze_all.exists():
        print(f"Error: {blaze_all} not found")
        return 1

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = work_dir / f"BLAZE.ALL.backup_{timestamp}"

    print("="*70)
    print("PATCH ALL PRICES TO 999")
    print("="*70)
    print()
    print("This will set ALL 32 words to 999")
    print("If this table is used ANYWHERE in game, we'll see 999 prices")
    print()

    shutil.copy2(blaze_all, backup)
    print(f"Backup: {backup}")
    print()

    data = bytearray(blaze_all.read_bytes())

    print("Current values:")
    for i in range(32):
        offset = PRICE_TABLE_BASE + (i * 2)
        val = struct.unpack('<H', data[offset:offset+2])[0]
        print(f"  Word[{i:2d}] = {val:3d}")

    print()
    print("Setting all to 999...")

    for i in range(32):
        offset = PRICE_TABLE_BASE + (i * 2)
        struct.pack_into('<H', data, offset, 999)

    blaze_all.write_bytes(data)

    print()
    print("Verification:")
    verify_data = blaze_all.read_bytes()
    all_ok = True
    for i in range(32):
        offset = PRICE_TABLE_BASE + (i * 2)
        val = struct.unpack('<H', verify_data[offset:offset+2])[0]
        if val != 999:
            print(f"  Word[{i:2d}] = {val} FAIL")
            all_ok = False

    if all_ok:
        print("  All 32 words set to 999 OK")
        print()
        print("="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Run: python ..\\patch_blaze_all.py")
        print("2. Test in-game")
        print("3. If you see 999 ANYWHERE: this table IS used")
        print("4. If still normal prices: this table is NOT used")
    else:
        print("FAILED")

    return 0 if all_ok else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
