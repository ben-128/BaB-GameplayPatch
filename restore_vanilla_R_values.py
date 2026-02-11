#!/usr/bin/env python3
"""
Restore vanilla R values to all formation JSONs.

Reads vanilla BLAZE.ALL at each assignment entry offset,
extracts byte[5] (R field), and updates all JSONs.

This restores the "vanilla bytes" at these offsets, even though
vanilla didn't actually use them as assignment entries.
"""

import json
from pathlib import Path

VANILLA_BLAZE = Path("vanilla_BLAZE.ALL")
FORMATIONS_DIR = Path("Data/formations")

def restore_vanilla_R():
    print("Restore Vanilla R Values to Formation JSONs")
    print("=" * 70)
    print()

    if not VANILLA_BLAZE.exists():
        print(f"ERROR: {VANILLA_BLAZE} not found")
        print("Run: py -3 extract_vanilla_blaze.py")
        return

    with open(VANILLA_BLAZE, 'rb') as f:
        vanilla_data = f.read()

    print(f"Loaded vanilla BLAZE.ALL: {len(vanilla_data):,} bytes")
    print()

    # Process all formation JSONs
    json_files = list(FORMATIONS_DIR.glob("**/floor_*.json"))

    total_files = 0
    total_entries = 0
    total_changed = 0

    for json_file in sorted(json_files):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "assignment_entries" not in data:
            continue

        zone_name = f"{data.get('level_name', '?')}/{data.get('name', '?')}"

        changed = False

        for entry in data["assignment_entries"]:
            offset_str = entry.get("offset", "")
            if not offset_str:
                continue

            offset = int(offset_str, 16)
            slot = entry.get("slot", -1)
            monster = data.get("monsters", [])[slot] if slot < len(data.get("monsters", [])) else "?"

            # Read vanilla R at this offset
            vanilla_R = vanilla_data[offset + 5]
            current_R = entry.get("R", 0)

            if vanilla_R != current_R:
                entry["R"] = vanilla_R
                changed = True
                total_changed += 1
                print(f"  {zone_name:50} {monster:20} R: {current_R} -> {vanilla_R}")

            total_entries += 1

        if changed:
            # Write back to JSON
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            total_files += 1

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"Total files processed:    {len(json_files)}")
    print(f"Total files modified:     {total_files}")
    print(f"Total entries processed:  {total_entries}")
    print(f"Total R values changed:   {total_changed}")
    print()

    if total_changed > 0:
        print("[OK] Vanilla R values restored to all JSONs")
    else:
        print("[OK] All R values already match vanilla")

if __name__ == '__main__':
    restore_vanilla_R()
