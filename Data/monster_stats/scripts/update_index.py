#!/usr/bin/env python3
"""
Update _index.json with current directory structure
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MONSTER_STATS_DIR = SCRIPT_DIR.parent

def main():
    # Read all monster JSON files
    json_files = sorted([f for f in MONSTER_STATS_DIR.glob("**/*.json") if not f.name.startswith('_')])

    print(f"Found {len(json_files)} monster files")
    print()

    monsters = []

    for json_file in json_files:
        # Get relative path from monster_stats directory
        rel_path = json_file.relative_to(MONSTER_STATS_DIR)

        # Read monster data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract key stats
        stats = data.get('stats', {})

        monster_entry = {
            "name": data.get('name', json_file.stem),
            "hp": stats.get('hp', 0),
            "exp": stats.get('exp_reward', 0),
            "dmg": stats.get('stat17_dmg', 0),
            "armor": stats.get('stat18_armor', 0),
            "file": str(rel_path).replace('\\', '/')  # Use forward slashes for JSON
        }

        monsters.append(monster_entry)
        print(f"  {monster_entry['name']:25s} -> {monster_entry['file']}")

    # Build complete index
    index = {
        "game_info": {
            "executable": "SLES_008.45",
            "region": "Europe (PAL)",
            "data_file": "BLAZE.ALL"
        },
        "data_structure": {
            "entry_size_bytes": 96,
            "name_offset": 0,
            "name_max_length": 16,
            "stats_offset": 16,
            "stats_count": 40,
            "endianness": "little-endian",
            "value_type": "int16/uint16"
        },
        "directory_structure": {
            "normal_enemies": "Regular monsters",
            "boss": "Boss monsters"
        },
        "stat_fields": {
            "stat1_exp_reward": "Points d'experience",
            "stat2": "Inconnu (niveau?)",
            "stat3_hp": "Points de vie",
            "stat4_magic": "Puissance magique",
            "stat5_randomness": "Variance degats",
            "stat6_collider_type": "Type de collider",
            "stat7_death_fx_size": "Taille FX mort",
            "stat8": "ID FX hit",
            "stat9_collider_size": "Taille hitbox",
            "stat10_drop_rate": "Taux de drop",
            "stat11_creature_type": "Type creature",
            "stat12_armor_type": "Type armure",
            "stat13_elem_fire_ice": "Element Feu/Glace",
            "stat14_elem_poison_air": "Element Poison/Air",
            "stat15_elem_light_night": "Element Lumiere/Nuit",
            "stat16_elem_divine_malefic": "Element Divin/Malefique",
            "stat17_dmg": "Degats attaque",
            "stat18_armor": "Armure",
            "stat24": "Resistance alterations"
        },
        "monsters": monsters
    }

    # Write index
    output_file = MONSTER_STATS_DIR / "_index.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print()
    print(f"Updated {output_file}")
    print(f"  Total monsters: {len(monsters)}")

    # Count by category
    normal_count = sum(1 for m in monsters if m['file'].startswith('normal_enemies/'))
    boss_count = sum(1 for m in monsters if m['file'].startswith('boss/'))

    print(f"  Normal enemies: {normal_count}")
    print(f"  Boss enemies: {boss_count}")

if __name__ == '__main__':
    main()
