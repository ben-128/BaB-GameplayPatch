#!/usr/bin/env python3
"""
Test hypothesis: R field = spell_list_index for monsters.

If true, R should correspond to:
- R=0: Offensive spells (FireBullet, etc.)
- R=1: Support spells (Heal, etc.)
- R=2: Status spells (Sleep, Poison, etc.)
- R=3: Herb spells
- R=4+: Wave/Arrow/Stardust or Monster-only

Checks if R values in patched JSONs match expected spell behavior.
"""

import json
from pathlib import Path

FORMATIONS_DIR = Path("Data/formations")
MONSTER_STATS_DIR = Path("Data/monster_stats")

# Known caster monsters and their typical spell lists
KNOWN_SPELL_BEHAVIOR = {
    "Goblin-Shaman": {"typical_spells": ["Sleep", "Poison"], "expected_list": 2},  # Status
    "Dark-Wizard": {"typical_spells": ["FireBullet", "IceBullet"], "expected_list": 0},  # Offensive
    "Wizard": {"typical_spells": ["FireBullet", "IceBullet"], "expected_list": 0},  # Offensive
    "Ghost": {"typical_spells": ["Fear", "Curse"], "expected_list": 2},  # Status
    "Vampire": {"typical_spells": ["Drain", "Dark"], "expected_list": 0},  # Offensive
    "Lesser-Vampire": {"typical_spells": ["Drain"], "expected_list": 0},  # Offensive
    "Harpy": {"typical_spells": ["Wind", "Sonic"], "expected_list": 0},  # Offensive
    "Chimera": {"typical_spells": ["FireBreath"], "expected_list": 0},  # Offensive
}

SPELL_LIST_NAMES = {
    0: "Offensive",
    1: "Support",
    2: "Status",
    3: "Herbs",
    4: "Wave",
    5: "Arrow",
    6: "Stardust",
    7: "Monster-only"
}

def analyze_R_as_spell_index():
    print("Hypothesis: R Field = Spell List Index")
    print("=" * 70)
    print()

    # Collect all patched R values (from our JSONs)
    monster_R_values = {}

    json_files = list(FORMATIONS_DIR.glob("**/floor_*.json"))

    for json_file in sorted(json_files):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "assignment_entries" not in data:
            continue

        zone_name = f"{data.get('level_name', '?')}/{data.get('name', '?')}"

        for entry in data["assignment_entries"]:
            slot = entry.get("slot", -1)
            R = entry.get("R", 0)
            L = entry.get("L", 0)
            monster = data.get("monsters", [])[slot] if slot < len(data.get("monsters", [])) else "?"

            if monster not in monster_R_values:
                monster_R_values[monster] = []

            monster_R_values[monster].append({
                "zone": zone_name,
                "R": R,
                "L": L
            })

    # Check known casters
    print("KNOWN CASTERS - R vs EXPECTED SPELL LIST")
    print("=" * 70)
    print()

    matches = 0
    mismatches = 0

    for monster, info in KNOWN_SPELL_BEHAVIOR.items():
        if monster not in monster_R_values:
            print(f"{monster:20} - NOT FOUND in formations")
            continue

        expected_R = info["expected_list"]
        typical_spells = ", ".join(info["typical_spells"])

        print(f"{monster}")
        print(f"  Expected list: {expected_R} ({SPELL_LIST_NAMES.get(expected_R, '?')})")
        print(f"  Typical spells: {typical_spells}")
        print()

        for instance in monster_R_values[monster]:
            R = instance["R"]
            L = instance["L"]
            match = "MATCH" if R == expected_R else "MISMATCH"

            if R == expected_R:
                matches += 1
            else:
                mismatches += 1

            print(f"    {match:8} R={R} ({SPELL_LIST_NAMES.get(R, '?'):12}) L={L}  zone: {instance['zone']}")

        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    total = matches + mismatches
    if total > 0:
        print(f"Matches:    {matches}/{total} ({100*matches/total:.1f}%)")
        print(f"Mismatches: {mismatches}/{total} ({100*mismatches/total:.1f}%)")
    else:
        print("No data to compare")

    print()

    # Distribution of R values in patched JSONs
    print("=" * 70)
    print("R VALUE DISTRIBUTION (PATCHED JSONs)")
    print("=" * 70)
    print()

    from collections import Counter
    all_R_values = []
    for monster, instances in monster_R_values.items():
        for inst in instances:
            all_R_values.append(inst["R"])

    R_counter = Counter(all_R_values)

    print(f"Total monsters: {len(all_R_values)}")
    print()
    print("R value distribution:")
    for value in sorted(R_counter.keys()):
        count = R_counter[value]
        percentage = 100 * count / len(all_R_values)
        list_name = SPELL_LIST_NAMES.get(value, f"Unknown ({value})")
        print(f"  R={value:2} ({list_name:12}): {count:3} occurrences ({percentage:5.1f}%)")

    print()

    # Check Goblin-Shaman specifically (our test case)
    print("=" * 70)
    print("GOBLIN-SHAMAN ANALYSIS (Our Test Case)")
    print("=" * 70)
    print()

    if "Goblin-Shaman" in monster_R_values:
        print("Goblin-Shaman R values in patched JSONs:")
        print()

        for inst in monster_R_values["Goblin-Shaman"]:
            R = inst["R"]
            list_name = SPELL_LIST_NAMES.get(R, f"Unknown ({R})")
            print(f"  R={R} ({list_name:12}) L={inst['L']}  zone: {inst['zone']}")

        print()
        print("VANILLA BEHAVIOR:")
        print("  - Shaman casts Sleep (Status spells, list 2)")
        print()
        print("PATCHED BEHAVIOR:")
        print("  - Shaman casts FireBullet (Offensive spells, list 0)")
        print()
        print("IF R = spell_list_index:")
        print("  - Vanilla should have R=2 (but has R=0 in vanilla bytes)")
        print("  - Patched should have R=0 (matches current behavior!)")
        print()

        # Check current values
        cavern_f1_shaman = [inst for inst in monster_R_values["Goblin-Shaman"]
                            if "Cavern of Death/Floor 1" in inst["zone"]]

        if cavern_f1_shaman:
            current_R = cavern_f1_shaman[0]["R"]
            if current_R == 0:
                print("  -> Current Cavern F1 Shaman has R=0 (Offensive)")
                print("  -> This MATCHES patched behavior (FireBullet)")
                print("  -> To restore vanilla Sleep, need R=2!")
            elif current_R == 2:
                print("  -> Current Cavern F1 Shaman has R=2 (Status)")
                print("  -> This should restore vanilla behavior (Sleep)")

    # Conclusion
    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()

    if matches > mismatches and total > 0:
        print("  -> STRONG correlation: R likely IS spell_list_index!")
        print(f"     {matches}/{total} known casters match expected lists")
    elif matches > 0:
        print("  -> WEAK correlation: Some matches but inconsistent")
    else:
        print("  -> NO correlation: R doesn't seem to control spell lists")

    print()
    print("NEXT TEST:")
    print("  1. Change Cavern F1 Shaman R from 0 to 2")
    print("  2. Rebuild and test in-game")
    print("  3. Check if Shaman now casts Sleep instead of FireBullet")

if __name__ == '__main__':
    analyze_R_as_spell_index()
