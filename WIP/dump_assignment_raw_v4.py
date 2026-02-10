# -*- coding: cp1252 -*-
"""
Corrected analysis - byte[4] does NOT always equal slot.
Let's understand byte[0] and byte[4] by looking at ALL cases carefully.

New hypothesis:
  byte[0] + byte[2] together select the model/texture
  byte[4] might be a secondary identifier (animation group? slot within a different indexing?)
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

    # Focus on cases where byte[0] != slot OR byte[4] != slot
    print("=" * 110)
    print("ALL AREAS WHERE byte[0] or byte[4] DIFFER FROM SLOT")
    print("(These reveal the true meaning of byte[0] vs byte[4])")
    print("=" * 110)

    # Group by area
    areas = {}
    for e in all_entries:
        if e["label"] not in areas:
            areas[e["label"]] = []
        areas[e["label"]].append(e)

    for label, entries in sorted(areas.items()):
        has_mismatch = any(e["b0"] != e["slot"] or e["b4"] != e["slot"] for e in entries)
        if not has_mismatch:
            continue

        print()
        print("  %s" % label)
        print("  %s" % ("-" * 100))
        print("  %-4s %-20s  %4s %5s %4s   %4s %5s   raw" % (
            "slot", "monster", "b0", "b1(L)", "b2", "b4", "b5(R)"))

        for e in entries:
            m0 = "*" if e["b0"] != e["slot"] else " "
            m4 = "*" if e["b4"] != e["slot"] else " "
            print("  %-4d %-20s %s%3d %5d %4d  %s%3d %5d   %s" % (
                e["slot"], e["monster"],
                m0, e["b0"], e["b1"], e["b2"],
                m4, e["b4"], e["b5"],
                e["raw"].hex().upper()))

    # NEW HYPOTHESIS: maybe byte[0] and byte[4] are BOTH model references,
    # but for DIFFERENT PURPOSES (L-half model, R-half model?)
    # The entry structure might be:
    #   [model_L][L][variant_L][pad] [model_R][R][variant_R][flags]
    print()
    print("=" * 110)
    print("REVISED HYPOTHESIS: The 8-byte record is TWO 4-byte halves")
    print("  Left half:  [model_index_L][L_behavior][variant_L][pad]")
    print("  Right half: [model_index_R][R_stat][variant_R][flags=0x40]")
    print("=" * 110)
    print()

    # Check: do b0 values map to something consistent?
    # Let's see if within each area, the set of b0 values maps to model groups
    print("AREA-BY-AREA b0/b4 ANALYSIS:")
    print("-" * 110)

    for label, entries in sorted(areas.items()):
        has_mismatch = any(e["b0"] != e["slot"] or e["b4"] != e["slot"] for e in entries)
        if not has_mismatch:
            continue

        print()
        print("  %s" % label)
        # Show model groups based on b0
        groups_b0 = {}
        for e in entries:
            if e["b0"] not in groups_b0:
                groups_b0[e["b0"]] = []
            groups_b0[e["b0"]].append(e)

        for b0val, group in sorted(groups_b0.items()):
            monsters_str = ", ".join("%s(slot%d,var%d)" % (e["monster"], e["slot"], e["b2"]) for e in group)
            print("    b0=%d: %s" % (b0val, monsters_str))

        # Show groups based on b4
        groups_b4 = {}
        for e in entries:
            if e["b4"] not in groups_b4:
                groups_b4[e["b4"]] = []
            groups_b4[e["b4"]].append(e)

        for b4val, group in sorted(groups_b4.items()):
            monsters_str = ", ".join("%s(slot%d)" % (e["monster"], e["slot"]) for e in group)
            print("    b4=%d: %s" % (b4val, monsters_str))

    # Let's check: does the number of unique b0 values always match the
    # number of unique b0 values with b2=0 (i.e. the number of base models)?
    print()
    print("=" * 110)
    print("MODEL COUNT CHECK: unique b0 values vs slot count per area")
    print("=" * 110)

    for label, entries in sorted(areas.items()):
        n_slots = len(entries)
        n_b0 = len(set(e["b0"] for e in entries))
        base_models = len(set(e["b0"] for e in entries if e["b2"] == 0))
        variants = [e for e in entries if e["b2"] != 0]
        if n_b0 != n_slots:
            print("  %s: %d slots, %d unique b0, %d base models, %d variants" % (
                label, n_slots, n_b0, base_models, len(variants)))

if __name__ == "__main__":
    main()
