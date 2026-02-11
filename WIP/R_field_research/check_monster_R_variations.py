#!/usr/bin/env python3
"""
Show monsters that appear in multiple zones with different R values.

This helps understand if R is monster-specific or zone-specific.
"""

import json
from pathlib import Path
from collections import defaultdict

VANILLA_BLAZE = Path("vanilla_BLAZE.ALL")
FORMATIONS_DIR = Path("Data/formations")

def analyze_monster_variations():
    print("Monster R Value Variations Across Zones")
    print("=" * 70)
    print()

    if not VANILLA_BLAZE.exists():
        print(f"ERROR: {VANILLA_BLAZE} not found")
        return

    with open(VANILLA_BLAZE, 'rb') as f:
        vanilla_data = f.read()

    # Collect all monsters with their R values per zone
    monster_instances = defaultdict(list)

    json_files = list(FORMATIONS_DIR.glob("**/floor_*.json"))

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

            # Read vanilla entry
            raw = vanilla_data[offset:offset+8]
            L = raw[1]
            R = raw[5]
            flag = raw[7]

            monster_instances[monster].append({
                "zone": zone_name,
                "L": L,
                "R": R,
                "flag": flag,
                "offset": offset_str
            })

    # Find monsters with varying R values
    print("MONSTERS WITH MULTIPLE APPEARANCES")
    print("=" * 70)
    print()

    monsters_with_variations = []

    for monster, instances in sorted(monster_instances.items()):
        if len(instances) <= 1:
            continue

        R_values = set(inst["R"] for inst in instances)
        L_values = set(inst["L"] for inst in instances)

        if len(R_values) > 1 or len(L_values) > 1:
            monsters_with_variations.append((monster, instances, R_values, L_values))

    print(f"Found {len(monsters_with_variations)} monsters with variations")
    print()

    # Show all variations
    for monster, instances, R_values, L_values in monsters_with_variations:
        print(f"{monster}")
        print(f"  Appears {len(instances)} times")
        print(f"  R values: {sorted(R_values)}")
        print(f"  L values: {sorted(L_values)}")
        print()

        for inst in instances:
            flag_str = "[0x40]" if inst["flag"] == 0x40 else "      "
            print(f"    {flag_str} L={inst['L']:3}, R={inst['R']:3}  offset={inst['offset']:10}  zone: {inst['zone']}")

        print()

    # Statistics
    print("=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print()

    total_monsters = len(monster_instances)
    monsters_appearing_once = sum(1 for m, insts in monster_instances.items() if len(insts) == 1)
    monsters_appearing_multiple = total_monsters - monsters_appearing_once
    monsters_with_R_variation = sum(1 for m, insts, R_vals, L_vals in monsters_with_variations if len(R_vals) > 1)
    monsters_with_L_variation = sum(1 for m, insts, R_vals, L_vals in monsters_with_variations if len(L_vals) > 1)

    print(f"Total unique monsters: {total_monsters}")
    print(f"  Appear once:        {monsters_appearing_once}")
    print(f"  Appear multiple:    {monsters_appearing_multiple}")
    print()
    print(f"Monsters with R variations: {monsters_with_R_variation}")
    print(f"Monsters with L variations: {monsters_with_L_variation}")
    print()

    # Focus on Goblin-Shaman
    print("=" * 70)
    print("GOBLIN-SHAMAN DETAILS")
    print("=" * 70)
    print()

    if "Goblin-Shaman" in monster_instances:
        shaman_instances = monster_instances["Goblin-Shaman"]
        print(f"Goblin-Shaman appears {len(shaman_instances)} times:")
        print()

        for inst in shaman_instances:
            flag_str = "[0x40]" if inst["flag"] == 0x40 else "      "
            raw_bytes = vanilla_data[int(inst["offset"], 16):int(inst["offset"], 16)+8]
            hex_str = ' '.join(f'{b:02X}' for b in raw_bytes)

            print(f"  {flag_str} L={inst['L']:3}, R={inst['R']:3}")
            print(f"        Raw: [{hex_str}]")
            print(f"        Zone: {inst['zone']}")
            print(f"        Offset: {inst['offset']}")
            print()

    # Conclusion
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()

    if monsters_with_R_variation > 0:
        print(f"  -> {monsters_with_R_variation} monsters have DIFFERENT R values in different zones")
        print("  -> R is ZONE-SPECIFIC, not monster-specific")
        print("  -> Confirms these are RANDOM BYTES at zone-specific offsets")
    else:
        print("  -> All monsters have consistent R values across zones")
        print("  -> R might be monster-specific")

if __name__ == '__main__':
    analyze_monster_variations()
