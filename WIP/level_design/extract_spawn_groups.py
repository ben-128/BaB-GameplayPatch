#!/usr/bin/env python3
"""
extract_spawn_groups.py
Find all monster spawn groups in BLAZE.ALL and export them as editable JSON files.

Each spawn group = consecutive 96-byte monster entries (16-byte name + 80-byte stats).
Groups are organized per level and per floor/area.

Usage: py -3 extract_spawn_groups.py
Output: spawn_groups/<level_name>.json
"""

import struct
import json
import os
from pathlib import Path
from collections import defaultdict

# ----- Paths -----
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = SCRIPT_DIR / "spawn_groups"

BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

INDEX_FILE = PROJECT_ROOT / "Data" / "monster_stats" / "_index.json"

# ----- Monster names (all valid names that can appear in spawn data) -----
MONSTER_NAMES = {
    'Behemoth', 'Black-Durahan', 'Budgietom', 'Carberos', 'Dark-Angel',
    'Dark-Elf', 'Dark-Wizard', 'Demon-Lord', 'Dragon-Puppy', 'Durahan',
    'Efreet', 'Greater-Demon', 'Griffin', 'Kraken-Foot', 'Kraken-Hand',
    'Kraken', 'OwlBear', 'Red-Dragon', 'Troll', 'Undead-Master',
    'Vampire-Lord', 'Weretiger', 'Werewolf', 'Zombie-Dragon',
    'Arch-Magi', 'Barricade', 'Basirisk', 'Big-Viper', 'Black-Knight',
    'Black-Lizard', 'Blood-Mummy', 'Blood-Shadow', 'Blood-Skeleton',
    'Blue-Slime', 'Born-Golem', 'Cave-Bear', 'Cave-Scissors', 'Chimera',
    'Crimson-Lizard', 'Dark-Goblin', 'Dark-Magi', 'Death-Knight',
    'Desert-Lizard', 'Evil-Ball', 'Evil-Crystal', 'Evil-Stalker',
    'Gargoyle', 'Ghost', 'Ghoul', 'Giant-Ant', 'Giant-Bat',
    'Giant-Beetle', 'Giant-Centipede', 'Giant-Club', 'Giant-Scorpion',
    'Giant-Snake', 'Giant-Spider', 'Giant', 'Goblin-Fly', 'Goblin-Leader',
    'Goblin-Shaman', 'Goblin-Wizard', 'Goblin', 'Gorgon', 'Gray-Arm',
    'Green-Giant', 'Green-Slime', 'Gremlin', 'Guard-Golem', 'Hard-Born',
    'Harpy', 'Hell-Harpy', 'Hell-Hound', 'Hell-Ogre', 'Hippogriff',
    'Ice-Salamander', 'Killer-Bear', 'Killer-Bee', 'Killer-Fish',
    'King-Mummy', 'Kobold', 'Lesser-Vampire', 'Living-Armor',
    'Living-Sword', 'Lizard-Man', 'Lv20.Goblin', 'Lv30.Goblin',
    'Lv6.Kobold', 'Marble-Gargoyle', 'Metal-Ball', 'Metal-Slime',
    'Mummy', 'Noble-Mummy', 'Ogre', 'Platinum-Knight', 'Poison-Flower',
    'Red-Knight', 'Red-Slime', 'Revenant', 'Salamander', 'Shadow-Demon',
    'Shadow', 'Silver-Wolf', 'Skeleton', 'Snow-Bear', 'Spirit-Ball',
    'Stalker', 'Succubus', 'Trent', 'Undead-Knight', 'Vampire-Bat',
    'Vampire', 'Wight', 'Will-O-The-Wisp', 'Wing-Fish', 'Winter-Wolf',
    'Wolf', 'Wraith', 'Wyrm', 'Wyvern', 'Yellow-Slime', 'Zombie',
}

# Stat field names for the 40 uint16 values at bytes 16-95
STAT_NAMES = {
    0: 'exp', 1: 'level', 2: 'hp', 3: 'magic', 4: 'randomness',
    5: 'collider_type', 6: 'death_fx_size', 7: 'hit_fx_id',
    8: 'collider_size', 9: 'drop_rate', 10: 'creature_type',
    11: 'armor_type', 12: 'elem_fire_ice', 13: 'elem_poison_air',
    14: 'elem_light_night', 15: 'elem_divine_malefic',
    16: 'dmg', 17: 'armor',
}

# ----- Level regions in BLAZE.ALL -----
# Each level occupies a range of offsets. Defined from the spawn group analysis.
# 'strings' = positions of the level name string, used to split into floors.
LEVELS = [
    {
        'id': 'cavern_of_death',
        'name': 'Cavern of Death',
        'range': (0xF70000, 0xFA0000),
        'strings': [0xF7FB9C, 0xF83BE4, 0xF88BDC, 0xF8C19C, 0xF8DF14, 0xF8E714],
    },
    {
        'id': 'fire_mountain',
        'name': 'Fire Mountain',
        'range': (0x1020000, 0x1040000),
        'strings': [0x102F655],
    },
    {
        'id': 'forest',
        'name': 'The Forest',
        'range': (0x1480000, 0x14C0000),
        'strings': [0x149F70C],
    },
    {
        'id': 'tower',
        'name': 'The Tower (Old Palace)',
        'range': (0x1960000, 0x19A0000),
        'strings': [],
    },
    {
        'id': 'sealed_cave',
        'name': 'The Sealed Cave',
        'range': (0x1DD0000, 0x1E00000),
        'strings': [],
    },
    {
        'id': 'castle_of_vamp',
        'name': 'Castle of Vamp',
        'range': (0x23F0000, 0x2440000),
        'strings': [0x240AD14, 0x2411CA4, 0x24189D8, 0x241EAE0],
    },
    {
        'id': 'ancient_ruins',
        'name': 'Ancient Ruins',
        'range': (0x2510000, 0x2520000),
        'strings': [],
    },
    {
        'id': 'valley',
        'name': 'Valley of White Wind',
        'range': (0x25D0000, 0x25E0000),
        'strings': [0x25D1AC8],
    },
    {
        'id': 'undersea',
        'name': 'Undersea / Lake',
        'range': (0x2690000, 0x26A0000),
        'strings': [],
    },
    {
        'id': 'hall_of_demons',
        'name': 'Hall of Demons',
        'range': (0x2BE0000, 0x2C10000),
        'strings': [],
    },
]


def is_valid_entry(data, pos):
    """Check if position is the start of a valid 96-byte monster entry."""
    if pos + 96 > len(data):
        return False, None

    # Read 16-byte name field
    name_field = data[pos:pos + 16]

    # Find null terminator
    null_idx = name_field.find(b'\x00')
    if null_idx <= 0:
        return False, None

    # Extract name
    name = name_field[:null_idx].decode('ascii', errors='replace')

    # Must be a known monster name
    if name not in MONSTER_NAMES:
        return False, None

    # All bytes after the name must be zero (prevents substring matches)
    for i in range(null_idx, 16):
        if name_field[i] != 0:
            return False, None

    return True, name


def find_all_entries(data):
    """Find all valid 96-byte monster entries in the file."""
    entries = []

    # Search by looking for known monster names
    for name in sorted(MONSTER_NAMES):
        name_bytes = name.encode('ascii')
        pos = 0
        while True:
            pos = data.find(name_bytes, pos)
            if pos == -1:
                break

            valid, found_name = is_valid_entry(data, pos)
            if valid and found_name == name:
                entries.append(pos)

            pos += 1

    # Remove duplicates and sort
    entries = sorted(set(entries))
    return entries


def build_groups(data, entries):
    """Build groups of consecutive 96-byte entries."""
    if not entries:
        return []

    groups = []
    current_group = [entries[0]]

    for i in range(1, len(entries)):
        prev = current_group[-1]
        curr = entries[i]

        if curr == prev + 96:
            current_group.append(curr)
        else:
            if len(current_group) >= 2:
                groups.append(current_group)
            current_group = [curr]

    if len(current_group) >= 2:
        groups.append(current_group)

    return groups


def assign_level(offset):
    """Determine which level a group belongs to based on its offset."""
    for level in LEVELS:
        lo, hi = level['range']
        if lo <= offset <= hi:
            return level
    return None


def assign_floor(group_offset, level):
    """Determine floor number based on level string positions."""
    strings = level.get('strings', [])
    if not strings:
        return 0

    floor = 0
    for s_pos in sorted(strings):
        if group_offset > s_pos:
            floor += 1

    return floor


def read_stats(data, pos):
    """Read 40 uint16 stats from bytes 16-95 of a 96-byte entry."""
    stats = []
    for i in range(40):
        val = struct.unpack_from('<H', data, pos + 16 + i * 2)[0]
        stats.append(val)
    return stats


def stats_summary(stats):
    """Create a human-readable summary of key stats."""
    parts = []
    for idx, label in sorted(STAT_NAMES.items()):
        if idx < len(stats) and label in ('exp', 'level', 'hp', 'dmg', 'armor'):
            parts.append(f"{label}={stats[idx]}")
    return "  ".join(parts)


def extract_group(data, positions):
    """Extract monster names from a group of entry positions."""
    names = []
    for pos in positions:
        _, name = is_valid_entry(data, pos)
        names.append(name)
    return names


def main():
    print("=" * 70)
    print("  SPAWN GROUP EXTRACTOR")
    print("=" * 70)

    # Load BLAZE.ALL
    print(f"\nLoading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Find all valid monster entries
    print("\nScanning for monster entries (96-byte blocks)...")
    entries = find_all_entries(data)
    print(f"Found {len(entries)} individual monster entries")

    # Build groups
    groups = build_groups(data, entries)
    print(f"Formed {len(groups)} groups (2+ consecutive monsters)")

    # Organize by level
    levels_data = defaultdict(lambda: {'groups': [], 'level_info': None})

    ungrouped = []
    for group_positions in groups:
        group_start = group_positions[0]
        level = assign_level(group_start)

        if level is None:
            ungrouped.append(group_positions)
            continue

        level_id = level['id']
        levels_data[level_id]['level_info'] = level

        floor = assign_floor(group_start, level)
        monsters = extract_group(data, group_positions)

        levels_data[level_id]['groups'].append({
            'floor': floor,
            'offset_start': group_start,
            'names': monsters,
        })

    # Sort groups within each level by offset
    for level_id in levels_data:
        levels_data[level_id]['groups'].sort(key=lambda g: g['offset_start'])

    # Export per-level JSON files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nExporting to {OUTPUT_DIR}/")

    for level_id, ldata in sorted(levels_data.items()):
        level_info = ldata['level_info']
        groups_list = ldata['groups']

        # Determine floor labels
        max_floor = max(g['floor'] for g in groups_list) if groups_list else 0
        floor_counts = defaultdict(int)
        for g in groups_list:
            floor_counts[g['floor']] += 1

        # Build JSON output
        json_groups = []
        area_counter = defaultdict(int)

        for g in groups_list:
            floor = g['floor']
            area_counter[floor] += 1
            area_num = area_counter[floor]

            if max_floor > 0:
                group_label = f"Floor {floor + 1} - Area {area_num}"
            else:
                group_label = f"Area {len(json_groups) + 1}"

            json_groups.append({
                'name': group_label,
                'offset': f"0x{g['offset_start']:X}",
                'monsters': g['names'],
            })

        output = {
            '_readme': f"Spawn groups for {level_info['name']}",
            '_usage': "Edit monster names, then run: py -3 patch_spawn_groups.py",
            'level_name': level_info['name'],
            'groups': json_groups,
        }

        filename = f"{level_id}.json"
        filepath = OUTPUT_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        total_m = sum(len(g['monsters']) for g in json_groups)
        print(f"  {filename}: {len(json_groups)} groups, {total_m} monsters")
        for g in json_groups:
            print(f"    {g['name']} ({g['offset']}): {', '.join(g['monsters'])}")

    # Handle ungrouped
    if ungrouped:
        print(f"\n  WARNING: {len(ungrouped)} groups not assigned to any level:")
        for gp in ungrouped:
            names = []
            for pos in gp:
                _, name = is_valid_entry(data, pos)
                names.append(name or '?')
            print(f"    {hex(gp[0])}: {', '.join(names)}")

    # Summary
    total_groups = sum(len(ld['groups']) for ld in levels_data.values())
    total_monsters = sum(
        sum(len(g['names']) for g in ld['groups'])
        for ld in levels_data.values()
    )
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total_groups} groups, {total_monsters} monsters across {len(levels_data)} levels")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
