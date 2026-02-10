# -*- coding: cp1252 -*-
"""Add spell_info section to all monster JSON files.

Reads each monster JSON, determines if it's a likely spell caster based on
stat4_magic, and adds a spell_info section documenting available spells.

The spell system works zone-wide: ALL monsters in a zone share the same
initial spell bitfield. Only monsters with spell-casting AI actually use it.
stat4_magic is the best indicator of spell-casting ability (MP pool).

Usage: py -3 Data/monster_stats/scripts/add_spell_info.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MONSTER_DIR = SCRIPT_DIR.parent

# Threshold: monsters with stat4_magic >= this are likely spell casters
MAGIC_THRESHOLD = 50

# Known spell casters from game observation (name patterns)
KNOWN_CASTERS = {
    "Goblin-Shaman", "Goblin-Wizard", "Dark-Magi", "Arch-Magi",
    "Dark-Wizard", "Undead-Master", "Dark-Angel", "Demon-Lord",
    "Dark-Elf", "Efreet", "Greater-Demon",
    "Spirit-Ball", "Evil-Ball", "Will-O-The-Wisp",
    "Succubus", "Gremlin",
}

# Known NON-casters despite potentially high magic (use monster abilities instead of spells)
KNOWN_ABILITY_USERS = {
    "Red-Dragon", "Zombie-Dragon", "Carberos", "Behemoth", "Budgietom",
    "Chimera", "Gorgon", "Basirisk", "Salamander", "Ice-Salamander",
    "Hell-Hound", "Wyvern",
}


def build_spell_info(monster_data):
    """Build spell_info dict for a monster."""
    name = monster_data.get("name", "")
    stats = monster_data.get("stats", {})
    magic = stats.get("stat4_magic", 0)

    # Determine if spell caster
    is_known_caster = name in KNOWN_CASTERS
    is_ability_user = name in KNOWN_ABILITY_USERS
    is_likely_caster = magic >= MAGIC_THRESHOLD and not is_ability_user

    if is_known_caster or is_likely_caster:
        caster_type = "offensive_spells"
    elif is_ability_user:
        caster_type = "monster_abilities"
    else:
        caster_type = "melee_only"

    info = {}

    if caster_type == "offensive_spells":
        info["caster_type"] = "offensive_spells"
        info["spell_list"] = 0
        info["_how_it_works"] = [
            "1. Overlay init sets bitfield = 0x01 (FireBullet only) for ALL monsters in zone",
            "2. Level-up simulation then ADDS more bits (tiers) based on monster level",
            "3. Final runtime bitfield = init + level-up additions",
            "4. Only monsters whose AI includes spell-casting actually use it"
        ]
        info["_how_to_modify"] = [
            "ZONE-WIDE (all monsters in zone get same spells):",
            "  Edit: Data/ai_behavior/overlay_bitfield_config.json",
            "  Section: overlay_bitfield_patches",
            "  Set bitfield_value to choose which spells (see MONSTER_SPELLS.md for bit table)",
            "",
            "SPELL STATS (damage, mp, element - affects ALL casters):",
            "  Edit: Data/spells/spell_config.json",
            "  Section: spell_definition_overrides",
            "",
            "PER-MONSTER: NOT YET POSSIBLE",
            "  The overlay init code has only 1 bitfield per zone.",
            "  Giving Shaman different spells than Goblin requires decoding",
            "  the level-up simulation (computed addresses, not yet reversed)."
        ]
    elif caster_type == "monster_abilities":
        info["caster_type"] = "monster_abilities"
        info["spell_list"] = 7
        info["_note"] = "Uses monster-only abilities (breaths, eyes, etc.), not offensive spell list"
    else:
        info["caster_type"] = "melee_only"
        info["_note"] = "Does not cast spells (melee/physical only)"

    info["stat4_magic"] = magic

    return info


def process_monster_file(filepath):
    """Add spell_info to a monster JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    spell_info = build_spell_info(data)

    # Remove old spell_info if exists
    if "spell_info" in data:
        del data["spell_info"]

    # Insert spell_info after "floors" (or at end)
    new_data = {}
    inserted = False
    for key, val in data.items():
        new_data[key] = val
        if key == "floors" and not inserted:
            new_data["spell_info"] = spell_info
            inserted = True
    if not inserted:
        new_data["spell_info"] = spell_info

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)

    return data.get("name", "?"), spell_info["caster_type"]


def main():
    print("  Add Spell Info to Monster JSONs")
    print("  " + "-" * 40)

    dirs = ["normal_enemies", "boss"]
    files = []
    for d in dirs:
        dirpath = MONSTER_DIR / d
        if dirpath.exists():
            files.extend(sorted(dirpath.glob("*.json")))

    caster_count = 0
    ability_count = 0
    melee_count = 0

    for filepath in files:
        name, ctype = process_monster_file(filepath)
        if ctype == "offensive_spells":
            caster_count += 1
            print("  [CASTER] {}".format(name))
        elif ctype == "monster_abilities":
            ability_count += 1
            print("  [ABILITY] {}".format(name))
        else:
            melee_count += 1

    total = caster_count + ability_count + melee_count
    print()
    print("  Updated {} monster files:".format(total))
    print("    {} spell casters (offensive list)".format(caster_count))
    print("    {} ability users (monster list)".format(ability_count))
    print("    {} melee only".format(melee_count))


if __name__ == "__main__":
    main()
