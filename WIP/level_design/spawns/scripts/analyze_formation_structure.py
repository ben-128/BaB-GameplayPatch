#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Deep analysis of formation record structure in BLAZE.ALL.

Goals:
1. Verify 4-byte gap is universal and always exactly 4 bytes
2. Examine gap content across all areas/levels
3. Check what's BEFORE the first formation of each area
4. Check what's AFTER the last formation of each area
5. Determine if gap is a formation suffix, prefix, or something else
"""

import json
import struct
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

FORMATIONS_DIR = PROJECT_ROOT / "Data" / "formations"


def load_all_formations():
    """Load all formation JSONs."""
    results = []
    for level_dir in sorted(FORMATIONS_DIR.iterdir()):
        if not level_dir.is_dir():
            continue
        for json_file in sorted(level_dir.glob("*.json")):
            with open(json_file, 'r') as f:
                area = json.load(f)
            if area.get("formations"):
                results.append(area)
    return results


def analyze_gaps(data, area):
    """Analyze 4-byte gaps between formations in one area."""
    formations = area["formations"]
    if len(formations) < 2:
        return []

    gaps = []
    for i in range(len(formations) - 1):
        f_curr = formations[i]
        f_next = formations[i + 1]

        curr_end = int(f_curr["offset"], 16) + len(f_curr["slots"]) * 32
        next_start = int(f_next["offset"], 16)
        gap_size = next_start - curr_end

        gap_data = bytes(data[curr_end:next_start])
        gaps.append({
            "from_formation": i,
            "to_formation": i + 1,
            "gap_size": gap_size,
            "gap_hex": gap_data.hex(),
            "gap_bytes": gap_data,
            "curr_slots": f_curr["slots"],
            "next_slots": f_next["slots"],
            "curr_offset": curr_end,
        })
    return gaps


def analyze_before_first(data, area):
    """Check what's in the 4 bytes before the first formation."""
    formations = area["formations"]
    if not formations:
        return None
    first_offset = int(formations[0]["offset"], 16)
    before = data[first_offset - 4:first_offset]
    return before


def analyze_after_last(data, area):
    """Check what's in the 4 bytes after the last formation."""
    formations = area["formations"]
    if not formations:
        return None
    last_f = formations[-1]
    last_end = int(last_f["offset"], 16) + len(last_f["slots"]) * 32
    after = data[last_end:last_end + 4]
    return after


def main():
    print("Loading BLAZE.ALL from {}...".format(BLAZE_ALL))
    data = BLAZE_ALL.read_bytes()
    print("Size: {:,} bytes".format(len(data)))
    print()

    areas = load_all_formations()
    print("Areas with formations: {}".format(len(areas)))
    print()

    # === Gap analysis ===
    all_gap_sizes = Counter()
    all_gap_values = Counter()
    gap_details = []
    problem_gaps = []

    for area in areas:
        gaps = analyze_gaps(data, area)
        for g in gaps:
            all_gap_sizes[g["gap_size"]] += 1
            all_gap_values[g["gap_hex"]] += 1
            gap_details.append({
                "level": area["level_name"],
                "area": area["name"],
                "from": g["from_formation"],
                "to": g["to_formation"],
                "size": g["gap_size"],
                "hex": g["gap_hex"],
            })
            if g["gap_size"] != 4:
                problem_gaps.append(g)

    print("=" * 70)
    print("  GAP SIZE DISTRIBUTION")
    print("=" * 70)
    for size, count in sorted(all_gap_sizes.items()):
        print("  {} bytes: {} occurrences".format(size, count))

    if problem_gaps:
        print()
        print("!!! NON-4-BYTE GAPS FOUND !!!")
        for g in problem_gaps:
            print("  {}".format(g))
    else:
        print()
        print("  ALL gaps are exactly 4 bytes")

    print()
    print("=" * 70)
    print("  GAP VALUE DISTRIBUTION (4-byte content)")
    print("=" * 70)
    for val, count in all_gap_values.most_common():
        print("  {}: {} occurrences".format(val, count))

    # === Before first / after last analysis ===
    print()
    print("=" * 70)
    print("  BEFORE FIRST FORMATION (4 bytes)")
    print("=" * 70)
    before_values = Counter()
    for area in areas:
        before = analyze_before_first(data, area)
        if before:
            before_values[before.hex()] += 1

    for val, count in before_values.most_common():
        print("  {}: {} occurrences".format(val, count))

    print()
    print("=" * 70)
    print("  AFTER LAST FORMATION (4 bytes)")
    print("=" * 70)
    after_values = Counter()
    for area in areas:
        after = analyze_after_last(data, area)
        if after:
            after_values[after.hex()] += 1

    for val, count in after_values.most_common():
        print("  {}: {} occurrences".format(val, count))

    # === Detailed per-area gap report ===
    print()
    print("=" * 70)
    print("  DETAILED GAP REPORT (non-zero gaps only)")
    print("=" * 70)
    current_level = None
    for area in areas:
        gaps = analyze_gaps(data, area)
        non_zero = [g for g in gaps if g["gap_hex"] != "00000000"]
        if not non_zero:
            continue
        if area["level_name"] != current_level:
            print()
            print("--- {} ---".format(area["level_name"]))
            current_level = area["level_name"]
        print("  {}:".format(area["name"]))
        for g in non_zero:
            # Also print composition of both formations
            curr_comp = "+".join("{}x{}".format(
                c["count"], c["monster"]) for c in
                area["formations"][g["from_formation"]]["composition"])
            next_comp = "+".join("{}x{}".format(
                c["count"], c["monster"]) for c in
                area["formations"][g["to_formation"]]["composition"])
            val = struct.unpack_from('<I', g["gap_bytes"])[0]
            print("    F{:02d}->F{:02d}: {} (uint32={}) | [{}] -> [{}]".format(
                g["from_formation"], g["to_formation"],
                g["gap_hex"], val,
                curr_comp, next_comp))

    # === Correlation analysis: do gap bytes correlate with slots used? ===
    print()
    print("=" * 70)
    print("  CORRELATION: gap value vs formation composition")
    print("=" * 70)
    print()

    # For each gap, check if it relates to the PREVIOUS formation's slots
    # or the NEXT formation's slots
    for area in areas:
        formations = area["formations"]
        gaps = analyze_gaps(data, area)
        monsters = area["monsters"]
        if not gaps:
            continue

        # Also check after last formation
        after = analyze_after_last(data, area)
        after_hex = after.hex() if after else "?"

        all_suffix = []
        for g in gaps:
            all_suffix.append({
                "hex": g["gap_hex"],
                "prev_slots": set(g["curr_slots"]),
                "prev_monsters": [monsters[s] for s in set(g["curr_slots"])],
            })
        # After last formation = suffix of last formation
        last_f = formations[-1]
        all_suffix.append({
            "hex": after_hex,
            "prev_slots": set(last_f["slots"]),
            "prev_monsters": [monsters[s] for s in set(last_f["slots"])],
        })

        # Check if gap values are consistent for same slot sets
        slot_to_gaps = {}
        for s in all_suffix:
            key = tuple(sorted(s["prev_slots"]))
            slot_to_gaps.setdefault(key, set()).add(s["hex"])

        inconsistent = {k: v for k, v in slot_to_gaps.items() if len(v) > 1}
        if inconsistent:
            print("{} / {}:".format(area["level_name"], area["name"]))
            for slots, vals in inconsistent.items():
                slot_names = [monsters[s] for s in slots]
                print("  slots {} -> MULTIPLE values: {}".format(
                    slot_names, vals))


if __name__ == '__main__':
    main()
