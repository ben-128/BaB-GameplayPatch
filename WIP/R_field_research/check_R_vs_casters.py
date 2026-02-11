#!/usr/bin/env python3
"""
Check if monsters with R != 0 in vanilla are spell casters.

Cross-references vanilla R values with:
- L field (L=1 = caster)
- Monster types known to cast spells
"""

import json
from pathlib import Path

VANILLA_BLAZE = Path("vanilla_BLAZE.ALL")
FORMATIONS_DIR = Path("Data/formations")
MONSTER_STATS_DIR = Path("Data/monster_stats")

# Known caster monsters (from game knowledge)
KNOWN_CASTERS = {
    "Goblin-Shaman", "Dark-Wizard", "Wizard", "Lich", "Necromancer",
    "Ghost", "Wraith", "Vampire", "Lesser-Vampire", "Vampire-Lord",
    "Demon", "Succubus", "Harpy", "Gargoyle", "Marble-Gargoyle",
    "Medusa", "Chimera", "Dragon", "Wyvern"
}

def load_vanilla_R_and_L():
    """Load R and L values from vanilla BLAZE.ALL."""

    with open(VANILLA_BLAZE, 'rb') as f:
        vanilla_data = f.read()

    # Collect all assignment entries
    entries = []
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

            entries.append({
                "zone": zone_name,
                "monster": monster,
                "L": L,
                "R": R,
                "flag": flag,
                "is_known_caster": monster in KNOWN_CASTERS
            })

    return entries

def analyze_R_vs_casters():
    print("R Field vs Spell Casters Analysis")
    print("=" * 70)
    print()

    if not VANILLA_BLAZE.exists():
        print(f"ERROR: {VANILLA_BLAZE} not found")
        return

    entries = load_vanilla_R_and_L()

    print(f"Total monsters: {len(entries)}")
    print()

    # Split by R value
    R_zero = [e for e in entries if e["R"] == 0]
    R_nonzero = [e for e in entries if e["R"] != 0]

    print(f"R=0:     {len(R_zero)} monsters")
    print(f"R != 0:  {len(R_nonzero)} monsters")
    print()

    # Check casters in each group
    print("=" * 70)
    print("KNOWN CASTERS")
    print("=" * 70)
    print()

    casters_R0 = [e for e in R_zero if e["is_known_caster"]]
    casters_R_nonzero = [e for e in R_nonzero if e["is_known_caster"]]

    print(f"Known casters with R=0:     {len(casters_R0)}")
    print(f"Known casters with R != 0:  {len(casters_R_nonzero)}")
    print()

    if casters_R0:
        print("Casters with R=0:")
        for e in casters_R0[:10]:
            print(f"  {e['monster']:20} L={e['L']:3}  zone: {e['zone']}")
        if len(casters_R0) > 10:
            print(f"  ... and {len(casters_R0)-10} more")
        print()

    if casters_R_nonzero:
        print("Casters with R != 0:")
        for e in casters_R_nonzero:
            print(f"  {e['monster']:20} L={e['L']:3}, R={e['R']:3}  zone: {e['zone']}")
        print()

    # Check L=1 (confirmed caster flag)
    print("=" * 70)
    print("L=1 CASTERS (confirmed casting behavior)")
    print("=" * 70)
    print()

    L1_monsters = [e for e in entries if e["L"] == 1]
    L1_R0 = [e for e in L1_monsters if e["R"] == 0]
    L1_R_nonzero = [e for e in L1_monsters if e["R"] != 0]

    print(f"L=1 with R=0:     {len(L1_R0)}")
    print(f"L=1 with R != 0:  {len(L1_R_nonzero)}")
    print()

    if L1_R0:
        print("L=1 with R=0:")
        for e in L1_R0:
            print(f"  {e['monster']:20} R={e['R']:3}  zone: {e['zone']}")
        print()

    if L1_R_nonzero:
        print("L=1 with R != 0:")
        for e in L1_R_nonzero:
            print(f"  {e['monster']:20} R={e['R']:3}  zone: {e['zone']}")
        print()

    # Show all R != 0 monsters
    print("=" * 70)
    print("ALL MONSTERS WITH R != 0 (sorted by R value)")
    print("=" * 70)
    print()

    R_nonzero_sorted = sorted(R_nonzero, key=lambda e: e["R"])

    for e in R_nonzero_sorted:
        caster_mark = "[CASTER]" if e["is_known_caster"] else "        "
        L1_mark = "[L=1]" if e["L"] == 1 else "     "
        flag_mark = "[0x40]" if e["flag"] == 0x40 else "      "

        print(f"  R={e['R']:3} {caster_mark} {L1_mark} {flag_mark} {e['monster']:20} L={e['L']:3}  zone: {e['zone']}")

    print()

    # Statistical test
    print("=" * 70)
    print("STATISTICAL CORRELATION")
    print("=" * 70)
    print()

    total_casters = len([e for e in entries if e["is_known_caster"]])
    total_R_nonzero = len(R_nonzero)

    casters_in_R_nonzero = len(casters_R_nonzero)
    casters_in_R0 = len(casters_R0)

    print(f"Total known casters: {total_casters}")
    print(f"  - With R=0:     {casters_in_R0} ({100*casters_in_R0/total_casters:.1f}%)")
    print(f"  - With R != 0:  {casters_in_R_nonzero} ({100*casters_in_R_nonzero/total_casters:.1f}%)")
    print()

    print(f"Total R != 0 monsters: {total_R_nonzero}")
    print(f"  - Known casters:     {casters_in_R_nonzero} ({100*casters_in_R_nonzero/total_R_nonzero:.1f}%)")
    print(f"  - Non-casters:       {total_R_nonzero - casters_in_R_nonzero} ({100*(total_R_nonzero - casters_in_R_nonzero)/total_R_nonzero:.1f}%)")
    print()

    # Conclusion
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()

    if casters_in_R_nonzero > casters_in_R0:
        print("  -> R != 0 CORRELATES with spell casting!")
        print(f"     {casters_in_R_nonzero}/{total_casters} casters have R != 0")
    elif casters_in_R_nonzero == 0:
        print("  -> NO correlation: No known casters have R != 0")
    else:
        print("  -> WEAK or NO correlation")
        print(f"     Most casters ({casters_in_R0}/{total_casters}) have R=0")

    print()

    # Check if R values are just random bytes
    non_casters_R_nonzero = total_R_nonzero - casters_in_R_nonzero
    if non_casters_R_nonzero > casters_in_R_nonzero:
        print("  -> R values appear to be RANDOM DATA, not caster flags")
        print(f"     {non_casters_R_nonzero} non-casters have R != 0")

if __name__ == '__main__':
    analyze_R_vs_casters()
