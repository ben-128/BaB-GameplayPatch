# -*- coding: cp1252 -*-
"""
Deep analysis of byte[2] in assignment entries - what does it mean?
Looking at the pattern: does byte[2] = index of a PARENT slot that shares the same model?
"""

import json
import glob
import os

FORMATIONS_DIR = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\Data\formations"
BLAZE_ALL = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL"

def main():
    with open(BLAZE_ALL, "rb") as f:
        blaze_data = f.read()

    json_files = sorted(glob.glob(os.path.join(FORMATIONS_DIR, "**", "*.json"), recursive=True))

    print("DETAILED ANALYSIS OF NON-ZERO byte[2] ENTRIES")
    print("=" * 100)
    print()
    print("Hypothesis: byte[2] might be a 'parent slot' index for texture sharing/variant")
    print("            (monster at this slot reuses the 3D model of the monster at slot byte[2]-1?)")
    print()

    for jf in json_files:
        with open(jf, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        if "assignment_entries" not in data:
            continue

        monsters = data.get("monsters", [])
        entries = data["assignment_entries"]

        # Check if any entries have non-zero byte[2]
        has_nonzero = False
        for entry in entries:
            offset = int(entry["offset"], 16)
            raw = blaze_data[offset:offset+8]
            if raw[2] != 0:
                has_nonzero = True
                break

        if not has_nonzero:
            continue

        area_name = data.get("name", os.path.basename(jf))
        level_name = data.get("level_name", "")
        label = f"{level_name} / {area_name}"

        print(f"--- {label} ---")
        print(f"  Monsters: {monsters}")
        print()

        # Print all entries for context
        for entry in entries:
            offset = int(entry["offset"], 16)
            raw = blaze_data[offset:offset+8]
            b = list(raw)
            slot = entry["slot"]
            monster = monsters[slot] if slot < len(monsters) else f"slot{slot}"
            marker = " <<<" if b[2] != 0 else ""

            # If byte2 is non-zero, show what slot it might reference
            ref_info = ""
            if b[2] != 0:
                # Check if b[0] (slot) of some other entry matches byte[2]
                # Or maybe byte[2] is 1-indexed parent slot?
                ref_slot = b[2]
                if ref_slot < len(monsters):
                    ref_info = f"  --> byte2={b[2]} might reference slot index? monster at slot {ref_slot} = {monsters[ref_slot]}"
                # Also check byte[0] of this entry vs byte[0] of another entry with same L
                for other in entries:
                    oraw = blaze_data[int(other["offset"], 16):int(other["offset"], 16)+8]
                    if oraw[1] == b[1] and oraw[2] == 0 and other["slot"] != slot:
                        ref_info += f"\n                     Same L={b[1]} as slot {other['slot']} ({monsters[other['slot']] if other['slot'] < len(monsters) else '?'})"

            print(f"  slot={slot:2d} [{monster:<20}]  "
                  f"b0={b[0]:3d} b1(L)={b[1]:3d} b2={b[2]:3d} b3={b[3]:3d} | "
                  f"b4={b[4]:3d} b5(R)={b[5]:3d} b6={b[6]:3d} b7={b[7]:3d}  "
                  f"raw={raw.hex().upper()}{marker}")
            if ref_info:
                print(f"                     {ref_info}")

        # Also show type07 entries for cross-reference
        if "type07_entries" in data:
            print(f"\n  type07_entries: {data['type07_entries']}")

        print()

    # Now check: is byte[2] always == byte[0] of another entry with the SAME L value?
    print("\n" + "=" * 100)
    print("PATTERN TEST: For non-zero byte[2] entries,")
    print("does byte[2] match some OTHER entry's byte[0] that has the SAME byte[1](L)?")
    print("=" * 100)

    for jf in json_files:
        with open(jf, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        if "assignment_entries" not in data:
            continue

        monsters = data.get("monsters", [])
        entries = data["assignment_entries"]

        # Build lookup of all entries with their raw bytes
        parsed = []
        for entry in entries:
            offset = int(entry["offset"], 16)
            raw = blaze_data[offset:offset+8]
            parsed.append({
                "slot": entry["slot"],
                "b0": raw[0], "b1": raw[1], "b2": raw[2], "b3": raw[3],
                "b4": raw[4], "b5": raw[5], "b6": raw[6], "b7": raw[7],
                "monster": monsters[entry["slot"]] if entry["slot"] < len(monsters) else f"slot{entry['slot']}",
                "raw": raw,
            })

        for p in parsed:
            if p["b2"] != 0:
                area_name = data.get("name", os.path.basename(jf))
                level_name = data.get("level_name", "")
                label = f"{level_name} / {area_name}"

                # Find entries with same L value
                same_L = [x for x in parsed if x["b1"] == p["b1"] and x["slot"] != p["slot"]]
                # Find entries where b0 == p.b2
                b0_match = [x for x in parsed if x["b0"] == p["b2"]]

                print(f"\n  {label} - {p['monster']} (slot={p['slot']})")
                print(f"    raw: {p['raw'].hex().upper()}")
                print(f"    b0={p['b0']} b1(L)={p['b1']} b2={p['b2']}")
                same_L_str = [(x['slot'], x['monster'], 'b0=%d' % x['b0'], 'b2=%d' % x['b2']) for x in same_L]
                b0_match_str = [(x['slot'], x['monster'], 'L=%d' % x['b1'], 'b2=%d' % x['b2']) for x in b0_match]
                print(f"    Entries with same L={p['b1']}: {same_L_str}")
                print(f"    Entries where b0=={p['b2']}: {b0_match_str}")

    print()
    print("=" * 100)
    print("STRUCTURE HYPOTHESIS:")
    print("  byte[0] = slot index (position in monster list)")
    print("  byte[1] = L (behavior/AI type index)")
    print("  byte[2] = ??? (only non-zero for variant/reskin monsters?)")
    print("  byte[3] = always 0x00")
    print("  byte[4] = sometimes == byte[0], sometimes different (needs study)")
    print("  byte[5] = R (monster ID / stat block index)")
    print("  byte[6] = always 0x00")
    print("  byte[7] = always 0x40")
    print("=" * 100)

if __name__ == "__main__":
    main()
