# -*- coding: cp1252 -*-
"""
Dump raw 8 bytes of every assignment_entry from the source BLAZE.ALL.
Focus on finding non-zero values in bytes 2 and 6 (undocumented).
"""

import json
import glob
import os
import struct

BLAZE_ALL = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL"
FORMATIONS_DIR = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\Data\formations"

def main():
    with open(BLAZE_ALL, "rb") as f:
        blaze_data = f.read()

    print(f"BLAZE.ALL size: {len(blaze_data):,} bytes")
    print()

    # Collect all JSON files recursively
    json_files = sorted(glob.glob(os.path.join(FORMATIONS_DIR, "**", "*.json"), recursive=True))

    all_entries = []
    non_zero_entries = []

    for jf in json_files:
        with open(jf, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        if "assignment_entries" not in data:
            continue

        area_name = data.get("name", os.path.basename(jf))
        level_name = data.get("level_name", "")
        label = f"{level_name} / {area_name}"
        monsters = data.get("monsters", [])

        for entry in data["assignment_entries"]:
            offset = int(entry["offset"], 16)
            slot = entry["slot"]
            L = entry["L"]
            R = entry["R"]

            if offset + 8 > len(blaze_data):
                print(f"  WARNING: offset 0x{offset:08X} out of range for {label} slot {slot}")
                continue

            raw = blaze_data[offset:offset+8]
            b = list(raw)

            # Determine monster name from slot index
            monster = monsters[slot] if slot < len(monsters) else f"slot{slot}"

            rec = {
                "label": label,
                "monster": monster,
                "slot": slot,
                "offset": offset,
                "raw": raw,
                "bytes": b,
                "L_json": L,
                "R_json": R,
            }
            all_entries.append(rec)

            if b[2] != 0 or b[6] != 0:
                non_zero_entries.append(rec)

    # Print full table
    print("=" * 120)
    print(f"{'Area':<40} {'Monster':<16} {'Slot':>4}  {'b0':>4} {'b1(L)':>5} {'b2':>4} {'b3':>4} | {'b4':>4} {'b5(R)':>5} {'b6':>4} {'b7':>4}  Raw Hex")
    print("=" * 120)

    for rec in all_entries:
        b = rec["bytes"]
        marker = " <<<" if (b[2] != 0 or b[6] != 0) else ""
        print(f"{rec['label']:<40} {rec['monster']:<16} {rec['slot']:>4}  "
              f"{b[0]:>4} {b[1]:>5} {b[2]:>4} {b[3]:>4} | "
              f"{b[4]:>4} {b[5]:>5} {b[6]:>4} {b[7]:>4}  "
              f"{rec['raw'].hex().upper()}{marker}")

    print()
    print(f"Total assignment entries: {len(all_entries)}")
    print()

    # Summary of non-zero byte[2] and byte[6]
    print("=" * 120)
    print("ENTRIES WITH NON-ZERO byte[2] or byte[6]:")
    print("=" * 120)

    if non_zero_entries:
        for rec in non_zero_entries:
            b = rec["bytes"]
            print(f"  {rec['label']:<40} {rec['monster']:<16} slot={rec['slot']}  "
                  f"offset=0x{rec['offset']:08X}  "
                  f"byte2=0x{b[2]:02X} byte6=0x{b[6]:02X}  "
                  f"raw={rec['raw'].hex().upper()}")
    else:
        print("  NONE - all byte[2] and byte[6] values are zero!")

    print()

    # Also show unique values for each byte position
    print("=" * 80)
    print("UNIQUE VALUES PER BYTE POSITION:")
    print("=" * 80)
    for pos in range(8):
        vals = sorted(set(rec["bytes"][pos] for rec in all_entries))
        labels = {
            0: "b0 (slot)",
            1: "b1 (L)",
            2: "b2 (UNKNOWN)",
            3: "b3",
            4: "b4",
            5: "b5 (R)",
            6: "b6 (UNKNOWN)",
            7: "b7",
        }
        val_str = ", ".join(f"0x{v:02X}" for v in vals)
        print(f"  byte[{pos}] {labels[pos]:<16}: [{val_str}]")

    print()

    # Cross-check: verify JSON L/R match raw bytes
    print("=" * 80)
    print("CROSS-CHECK: JSON L/R vs raw byte[1]/byte[5]:")
    print("=" * 80)
    mismatches = 0
    for rec in all_entries:
        b = rec["bytes"]
        if b[1] != rec["L_json"] or b[5] != rec["R_json"]:
            mismatches += 1
            print(f"  MISMATCH: {rec['label']} slot={rec['slot']}  "
                  f"JSON L={rec['L_json']} R={rec['R_json']}  "
                  f"raw byte1={b[1]} byte5={b[5]}  "
                  f"raw={rec['raw'].hex().upper()}")

    if mismatches == 0:
        print("  All entries match!")
    else:
        print(f"  {mismatches} mismatches found!")

if __name__ == "__main__":
    main()
