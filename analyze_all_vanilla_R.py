#!/usr/bin/env python3
"""
Analyze R field (byte[5]) for ALL monsters in vanilla BLAZE.ALL.

Reads all formation JSON files, extracts assignment entry offsets,
and analyzes distribution of R values across the entire game.
"""

import json
from pathlib import Path
from collections import Counter

VANILLA_BLAZE = Path("vanilla_BLAZE.ALL")
FORMATIONS_DIR = Path("Data/formations")

def collect_all_assignment_offsets():
    """Collect all assignment entry offsets from all formation JSONs."""

    all_entries = []

    # Find all floor JSON files
    json_files = list(FORMATIONS_DIR.glob("**/floor_*.json"))

    print(f"Found {len(json_files)} formation files")
    print()

    for json_file in sorted(json_files):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "assignment_entries" not in data:
            continue

        zone_name = f"{data.get('level_name', '?')}/{data.get('name', '?')}"

        for entry in data["assignment_entries"]:
            offset_str = entry.get("offset", "")
            if not offset_str:
                continue

            offset = int(offset_str, 16)
            slot = entry.get("slot", -1)
            monster = data.get("monsters", [])[slot] if slot < len(data.get("monsters", [])) else "?"

            all_entries.append({
                "zone": zone_name,
                "monster": monster,
                "slot": slot,
                "offset": offset,
                "offset_hex": offset_str
            })

    return all_entries

def analyze_vanilla_R_values():
    print("Vanilla R Field (byte[5]) Analyzer - ALL MONSTERS")
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

    # Collect all offsets
    entries = collect_all_assignment_offsets()
    print(f"Found {len(entries)} assignment entries across all zones")
    print()

    # Analyze R values
    R_values = []
    R_by_zone = {}
    all_bytes = []

    for entry in entries:
        offset = entry["offset"]
        zone = entry["zone"]

        # Read 8-byte entry
        raw_entry = vanilla_data[offset:offset+8]

        # Extract fields
        byte0 = raw_entry[0]
        L = raw_entry[1]
        tex_variant = raw_entry[2]
        byte3 = raw_entry[3]
        byte4 = raw_entry[4]
        R = raw_entry[5]
        byte6 = raw_entry[6]
        flag = raw_entry[7]

        R_values.append(R)
        all_bytes.append(raw_entry)

        if zone not in R_by_zone:
            R_by_zone[zone] = []
        R_by_zone[zone].append({
            "monster": entry["monster"],
            "R": R,
            "L": L,
            "flag": flag,
            "raw": raw_entry
        })

    # Statistics
    print("=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print()

    R_counter = Counter(R_values)

    print(f"Total monsters analyzed: {len(R_values)}")
    print(f"Unique R values: {len(R_counter)}")
    print()

    print("R value distribution (top 20):")
    for value, count in R_counter.most_common(20):
        percentage = 100 * count / len(R_values)
        print(f"  R={value:3} ({value:#04x}): {count:3} occurrences ({percentage:5.1f}%)")

    print()
    print(f"R value range: min={min(R_values)}, max={max(R_values)}")
    print()

    # Check for 0x40 flags
    flags_0x40 = sum(1 for e in entries if vanilla_data[e["offset"]+7] == 0x40)
    print(f"Entries with flag 0x40: {flags_0x40}")
    print()

    # Show samples of different R values
    print("=" * 70)
    print("SAMPLE ENTRIES BY R VALUE")
    print("=" * 70)
    print()

    # Show first 3 entries for each of the most common R values
    for value, count in R_counter.most_common(10):
        print(f"R={value} ({value:#04x}) - {count} occurrences")

        samples = [e for e in entries if vanilla_data[e["offset"]+5] == value][:3]

        for entry in samples:
            raw = vanilla_data[entry["offset"]:entry["offset"]+8]
            hex_str = ' '.join(f'{b:02X}' for b in raw)

            print(f"  {entry['zone']:40} {entry['monster']:20}")
            print(f"    offset={entry['offset_hex']:10} raw=[{hex_str}]")

        print()

    # Check if R correlates with L
    print("=" * 70)
    print("R vs L CORRELATION")
    print("=" * 70)
    print()

    L_R_pairs = Counter()
    for entry in entries:
        offset = entry["offset"]
        raw = vanilla_data[offset:offset+8]
        L = raw[1]
        R = raw[5]
        L_R_pairs[(L, R)] += 1

    print("Most common (L, R) pairs:")
    for (L, R), count in L_R_pairs.most_common(20):
        print(f"  L={L:3}, R={R:3}: {count:3} occurrences")

    print()

    # Show per-zone summary
    print("=" * 70)
    print("PER-ZONE SUMMARY")
    print("=" * 70)
    print()

    for zone_name in sorted(R_by_zone.keys()):
        monsters = R_by_zone[zone_name]
        R_list = [m["R"] for m in monsters]
        R_str = ','.join(f'{r:3}' for r in R_list)

        print(f"{zone_name:50} R=[{R_str}]")

    print()

    # Final conclusion
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()

    all_zero = all(r == 0 for r in R_values)
    all_same = len(R_counter) == 1

    if all_zero:
        print("  [OK] ALL R values = 0")
    elif all_same:
        print(f"  [OK] ALL R values = {R_values[0]}")
    else:
        print(f"  [!!] R values VARY: {len(R_counter)} unique values")
        print(f"      Most common: R={R_counter.most_common(1)[0][0]} ({R_counter.most_common(1)[0][1]} times)")
        print(f"      Range: {min(R_values)} to {max(R_values)}")

    print()

    # Check if these are real assignment entries
    has_0x40 = any(vanilla_data[e["offset"]+7] == 0x40 for e in entries)

    if not has_0x40:
        print("  [!!] NO 0x40 flags found")
        print("      -> These offsets do NOT contain valid assignment entries in vanilla")
        print("      -> R values are just random bytes at these locations")
    else:
        print("  [OK] Some 0x40 flags found")
        print("      -> Vanilla has some valid assignment entries")

if __name__ == '__main__':
    analyze_vanilla_R_values()
