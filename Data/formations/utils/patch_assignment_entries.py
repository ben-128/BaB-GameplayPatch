#!/usr/bin/env python3
"""
Quick patcher for assignment entries (L/R values).

The main formation patcher doesn't touch assignment_entries.
This script reads L/R from JSONs and patches them into BLAZE.ALL.
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_PATH = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

# Areas to patch
AREAS = [
    SCRIPT_DIR / "cavern_of_death" / "floor_1_area_1.json",
]

def patch_assignment_entries():
    print("Assignment Entries Patcher")
    print("=" * 50)
    print()

    if not BLAZE_PATH.exists():
        print(f"ERROR: {BLAZE_PATH} not found")
        return False

    with open(BLAZE_PATH, "r+b") as f:
        blaze_data = bytearray(f.read())

        for json_path in AREAS:
            if not json_path.exists():
                print(f"SKIP: {json_path.name} not found")
                continue

            with open(json_path, 'r', encoding='utf-8') as jf:
                area_data = json.load(jf)

            area_name = area_data.get('name', json_path.name)
            print(f"Patching: {area_name}")

            entries = area_data.get('assignment_entries', [])
            if not entries:
                print(f"  No assignment_entries found")
                continue

            for entry in entries:
                slot = entry['slot']
                L = entry['L']
                R = entry['R']
                offset_str = entry['offset']
                offset = int(offset_str, 16)

                # Assignment entry structure (8 bytes):
                # [0] = model_slot
                # [1] = L (AI behavior)
                # [2] = tex_variant
                # [3] = 0x00
                # [4] = unique_slot
                # [5] = R (unknown)
                # [6] = 0x00
                # [7] = 0x40

                # Read current entry
                current = blaze_data[offset:offset+8]
                current_L = current[1]
                current_R = current[5]

                # Patch L and R
                blaze_data[offset + 1] = L
                blaze_data[offset + 5] = R

                if current_L != L or current_R != R:
                    print(f"  Slot {slot}: L={current_L}->{L}, R={current_R}->{R}")

            print()

        # Write back
        f.seek(0)
        f.write(blaze_data)

    print("=" * 50)
    print("Assignment entries patched!")
    return True

if __name__ == '__main__':
    import sys
    success = patch_assignment_entries()
    sys.exit(0 if success else 1)
