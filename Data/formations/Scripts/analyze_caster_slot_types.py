#!/usr/bin/env python3
"""
Analyze slot_types values for all spell-casting monsters across all areas.
"""

import json
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent

# Known spell casters to look for
SPELL_CASTERS = [
    "Shaman", "Goblin-Shaman",
    "Bat", "Giant-Bat", "Vampire-Bat",
    "Trent",
    "Magi", "Dark-Magi", "Magician",
    "Wizard", "Sorcerer",
    "Angel", "Dark-Angel",
    "Wisp", "Will-O-The-Wisp",
    "Wraith", "Ghost", "Specter",
    "Demon", "Devil", "Imp",
]

def main():
    print("=" * 70)
    print("  Spell Caster slot_types Analysis")
    print("=" * 70)
    print()

    # Find all area JSONs (excluding vanilla and backup)
    area_files = []
    for level_dir in sorted(SCRIPT_DIR.iterdir()):
        if not level_dir.is_dir() or level_dir.name in ['Scripts', 'docs', 'utils']:
            continue
        for json_file in sorted(level_dir.glob("*.json")):
            if '_vanilla' in json_file.stem or '_user_backup' in json_file.stem:
                continue
            area_files.append(json_file)

    # Collect slot_types for each monster type
    monster_slot_types = defaultdict(set)
    area_data = []

    for json_file in area_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            monsters = data.get('monsters', [])
            slot_types = data.get('slot_types', [])

            if not monsters or not slot_types:
                continue

            # Check if any spell casters in this area
            has_caster = False
            for monster in monsters:
                if any(caster.lower() in monster.lower() for caster in SPELL_CASTERS):
                    has_caster = True
                    break

            if not has_caster:
                continue

            # Map slot_types to monsters
            for slot_idx, monster in enumerate(monsters):
                if slot_idx < len(slot_types):
                    slot_type = slot_types[slot_idx]
                    monster_slot_types[monster].add(slot_type)

                    # Store for detailed output
                    if any(caster.lower() in monster.lower() for caster in SPELL_CASTERS):
                        area_data.append({
                            'area': json_file.parent.name + '/' + json_file.stem,
                            'monster': monster,
                            'slot_idx': slot_idx,
                            'slot_type': slot_type,
                        })

        except Exception as e:
            print(f"[ERROR] {json_file.name}: {e}")
            continue

    # Print summary
    print("SPELL CASTER slot_types SUMMARY:")
    print("-" * 70)

    # Group by slot_type value
    by_slot_type = defaultdict(list)
    for monster, types in sorted(monster_slot_types.items()):
        if any(caster.lower() in monster.lower() for caster in SPELL_CASTERS):
            for st in types:
                by_slot_type[st].append(monster)

    for slot_type in sorted(by_slot_type.keys()):
        monsters = by_slot_type[slot_type]
        print(f"\nslot_types = {slot_type}:")
        for monster in sorted(set(monsters)):
            print(f"  - {monster}")

    print()
    print("=" * 70)
    print()

    # Detailed list
    print("DETAILED AREA-BY-AREA LIST:")
    print("-" * 70)

    current_area = None
    for entry in sorted(area_data, key=lambda x: (x['area'], x['slot_idx'])):
        if entry['area'] != current_area:
            current_area = entry['area']
            print(f"\n{current_area}:")
        print(f"  Slot {entry['slot_idx']}: {entry['monster']:30} -> {entry['slot_type']}")

    print()
    print("=" * 70)
    print(f"Analyzed {len(area_files)} areas")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
