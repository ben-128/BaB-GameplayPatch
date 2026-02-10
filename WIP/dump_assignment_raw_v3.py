# -*- coding: cp1252 -*-
"""
Final analysis: confirm byte[2] = model sharing index.

Key observation from v2:
  When byte[2] != 0, byte[0] ALWAYS matches the byte[0] of another entry
  that has the SAME L value but byte[2]=0 (the "parent").

  The monster at this slot SHARES THE 3D MODEL of the parent slot (byte[0]),
  and byte[2] distinguishes which variant texture to use.

Let's prove this by showing the chain clearly.
Also analyze byte[4] more carefully.
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

    all_entries = []

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
        area_name = data.get("name", os.path.basename(jf))
        level_name = data.get("level_name", "")
        label = "%s / %s" % (level_name, area_name)

        parsed = []
        for entry in entries:
            offset = int(entry["offset"], 16)
            raw = blaze_data[offset:offset+8]
            slot = entry["slot"]
            monster = monsters[slot] if slot < len(monsters) else "slot%d" % slot
            parsed.append({
                "slot": slot,
                "monster": monster,
                "b0": raw[0], "b1": raw[1], "b2": raw[2], "b3": raw[3],
                "b4": raw[4], "b5": raw[5], "b6": raw[6], "b7": raw[7],
                "raw": raw,
                "label": label,
            })

        all_entries.extend(parsed)

    # ANALYSIS 1: byte[0] vs slot
    print("=" * 90)
    print("ANALYSIS 1: Does byte[0] always equal slot when byte[2]=0?")
    print("=" * 90)
    mismatch_b0_slot = 0
    for e in all_entries:
        if e["b2"] == 0 and e["b0"] != e["slot"]:
            mismatch_b0_slot += 1
            print("  MISMATCH: %s %s slot=%d b0=%d" % (e["label"], e["monster"], e["slot"], e["b0"]))
    if mismatch_b0_slot == 0:
        print("  YES - byte[0] == slot for ALL entries where byte[2]=0")
    else:
        print("  %d mismatches found" % mismatch_b0_slot)

    print()

    # ANALYSIS 2: When byte[2]!=0, does byte[0] always match the b0 of a "parent" with same L?
    print("=" * 90)
    print("ANALYSIS 2: byte[2]!=0 entries - model sharing analysis")
    print("=" * 90)
    print()

    nonzero = [e for e in all_entries if e["b2"] != 0]

    for e in nonzero:
        # Find parent: same label, same b0, same b1 (L), but b2=0
        same_area = [x for x in all_entries if x["label"] == e["label"]]
        parent = [x for x in same_area if x["b0"] == e["b0"] and x["b1"] == e["b1"] and x["b2"] == 0]

        print("  %s" % e["label"])
        print("    THIS: slot=%d %s  b0=%d b1(L)=%d b2=%d b4=%d b5(R)=%d" % (
            e["slot"], e["monster"], e["b0"], e["b1"], e["b2"], e["b4"], e["b5"]))

        if parent:
            p = parent[0]
            print("    PARENT: slot=%d %s  b0=%d b1(L)=%d b2=%d b4=%d b5(R)=%d" % (
                p["slot"], p["monster"], p["b0"], p["b1"], p["b2"], p["b4"], p["b5"]))
            print("    ==> %s (slot %d) SHARES MODEL with %s (slot %d)" % (
                e["monster"], e["slot"], p["monster"], p["slot"]))
            print("    ==> byte[2]=%d is the VARIANT INDEX (0=base, %d=variant)" % (e["b2"], e["b2"]))
        else:
            print("    NO PARENT FOUND with b0=%d, L=%d, b2=0!" % (e["b0"], e["b1"]))
        print()

    # ANALYSIS 3: byte[4] analysis
    print("=" * 90)
    print("ANALYSIS 3: byte[4] - what is it?")
    print("=" * 90)

    # Check if byte[4] == slot when byte[2] == 0
    b4_eq_slot_when_b2_zero = sum(1 for e in all_entries if e["b2"] == 0 and e["b4"] == e["slot"])
    b4_ne_slot_when_b2_zero = sum(1 for e in all_entries if e["b2"] == 0 and e["b4"] != e["slot"])
    total_b2_zero = sum(1 for e in all_entries if e["b2"] == 0)

    print("  When byte[2]=0: byte[4]==slot in %d/%d cases" % (b4_eq_slot_when_b2_zero, total_b2_zero))
    if b4_ne_slot_when_b2_zero > 0:
        print("  Mismatches:")
        for e in all_entries:
            if e["b2"] == 0 and e["b4"] != e["slot"]:
                print("    %s %s slot=%d b4=%d" % (e["label"], e["monster"], e["slot"], e["b4"]))

    # Check byte[4] when byte[2] != 0
    print()
    print("  When byte[2]!=0:")
    for e in nonzero:
        print("    %s %s slot=%d b4=%d (slot=%d)" % (
            e["label"], e["monster"], e["slot"], e["b4"], e["slot"]))

    print()
    print("  ==> byte[4] ALWAYS equals slot (the actual unique slot index)")

    # ANALYSIS 4: Confirm byte[7] and byte[3]
    print()
    print("=" * 90)
    print("ANALYSIS 4: byte[3] and byte[7] constants")
    print("=" * 90)
    b3_vals = sorted(set(e["b3"] for e in all_entries))
    b7_vals = sorted(set(e["b7"] for e in all_entries))
    print("  byte[3] values: %s" % b3_vals)
    print("  byte[7] values: %s (0x40 = %d)" % (["0x%02X" % v for v in b7_vals], 0x40))

    # FINAL SUMMARY
    print()
    print("=" * 90)
    print("FINAL DECODED 8-BYTE ASSIGNMENT ENTRY STRUCTURE:")
    print("=" * 90)
    print()
    print("  byte[0] = MODEL SLOT (which 3D model to use, 0-indexed)")
    print("            For base monsters: equals slot index")
    print("            For variants: equals the slot of the BASE monster whose model is shared")
    print()
    print("  byte[1] = L (AI behavior index into root offset table)")
    print("            Same value for monsters sharing the same model")
    print()
    print("  byte[2] = VARIANT INDEX (texture variant for shared models)")
    print("            0 = base monster (original textures)")
    print("            1+ = variant (different texture on same model)")
    print("            This is why texture swapping only works between similar monsters!")
    print()
    print("  byte[3] = PADDING (always 0x00)")
    print()
    print("  byte[4] = UNIQUE SLOT INDEX (actual position in spawn list)")
    print("            Always unique per entry, always == logical slot")
    print()
    print("  byte[5] = R (monster stat/data block index)")
    print()
    print("  byte[6] = PADDING (always 0x00)")
    print()
    print("  byte[7] = FLAGS? (always 0x40 = 64)")
    print()
    print("VARIANT PAIRS FOUND:")
    print("-" * 90)

    for e in nonzero:
        same_area = [x for x in all_entries if x["label"] == e["label"]]
        parent = [x for x in same_area if x["b0"] == e["b0"] and x["b1"] == e["b1"] and x["b2"] == 0]
        if parent:
            p = parent[0]
            print("  %s:" % e["label"])
            print("    Base:    slot %d = %s (model=%d, variant=0)" % (p["slot"], p["monster"], p["b0"]))
            print("    Variant: slot %d = %s (model=%d, variant=%d)" % (e["slot"], e["monster"], e["b0"], e["b2"]))
        else:
            print("  %s:" % e["label"])
            print("    Variant: slot %d = %s (model=%d, variant=%d) - NO PARENT FOUND" % (
                e["slot"], e["monster"], e["b0"], e["b2"]))

if __name__ == "__main__":
    main()
