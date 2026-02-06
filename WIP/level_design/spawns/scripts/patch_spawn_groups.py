#!/usr/bin/env python3
"""
patch_spawn_groups.py
Read edited spawn group JSON files and patch them back into BLAZE.ALL.

When a monster name is changed, stats are automatically copied from
another occurrence of that monster found in BLAZE.ALL.

Usage: py -3 patch_spawn_groups.py
Input:  spawn_groups/*.json
Output: Patched BLAZE.ALL
"""

import struct
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent  # spawns/scripts/
LEVEL_DESIGN_DIR = SCRIPT_DIR.parent.parent  # level_design/
PROJECT_ROOT = LEVEL_DESIGN_DIR.parent.parent  # Racine projet
SPAWN_DIR = SCRIPT_DIR.parent / "data" / "spawn_groups"  # spawns/data/spawn_groups/

BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# All valid monster names
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


def read_name_at(data, offset):
    """Read monster name from 16-byte field at offset."""
    field = data[offset:offset + 16]
    null_idx = field.find(b'\x00')
    if null_idx <= 0:
        return ""
    return field[:null_idx].decode('ascii', errors='replace')


def build_monster_lookup(data):
    """Build a lookup: monster_name -> 96-byte entry (first occurrence found).
    Used to copy stats when replacing a monster with a different one."""
    lookup = {}
    for name in sorted(MONSTER_NAMES):
        name_bytes = name.encode('ascii')
        pos = 0
        while True:
            pos = data.find(name_bytes, pos)
            if pos == -1:
                break
            # Validate: name field must be exactly this name + null padding
            field = data[pos:pos + 16]
            null_idx = field.find(b'\x00')
            if null_idx == len(name_bytes):
                all_zero = all(field[i] == 0 for i in range(null_idx, 16))
                if all_zero and name not in lookup:
                    lookup[name] = bytes(data[pos:pos + 96])
            pos += 1
    return lookup


def main():
    print("=" * 70)
    print("  SPAWN GROUP PATCHER")
    print("=" * 70)
    print()

    # Load BLAZE.ALL
    print(f"Loading {BLAZE_ALL}...")
    data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  Size: {len(data):,} bytes")
    print()

    # Build monster stats lookup from BLAZE.ALL
    print("Building monster stats lookup...")
    lookup = build_monster_lookup(data)
    print(f"  Found entries for {len(lookup)} monsters")
    print()

    # Load spawn files
    print(f"Loading spawn files from {SPAWN_DIR}/...")
    files = sorted(SPAWN_DIR.glob('*.json'))
    if not files:
        print(f"[ERROR] No JSON files in {SPAWN_DIR}/")
        return

    print(f"  Found {len(files)} level files")
    print()

    # Apply patches
    total_checked = 0
    total_changed = 0
    errors = []

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            level_data = json.load(f)

        level_name = level_data.get('level_name', filepath.stem)
        groups = level_data.get('groups', [])
        if not groups:
            continue

        level_changes = 0

        for group in groups:
            group_name = group.get('name', '?')
            group_offset = int(group['offset'], 16)
            monsters = group['monsters']

            for i, new_name in enumerate(monsters):
                offset = group_offset + i * 96
                current_name = read_name_at(data, offset)
                total_checked += 1

                if new_name == current_name:
                    continue

                # Validate new name
                if new_name not in MONSTER_NAMES:
                    errors.append(f"{level_name} / {group_name} slot {i}: unknown monster '{new_name}'")
                    continue

                # Look up the 96-byte entry for the new monster
                if new_name not in lookup:
                    errors.append(f"{level_name} / {group_name} slot {i}: no stats found for '{new_name}'")
                    continue

                # Copy full 96-byte entry
                entry = lookup[new_name]
                data[offset:offset + 96] = entry

                print(f"  [{level_name}] {group_name} slot {i}: {current_name} -> {new_name}")
                total_changed += 1
                level_changes += 1

        if level_changes > 0:
            print()

    # Errors
    if errors:
        print()
        for err in errors:
            print(f"  [ERROR] {err}")
        print()

    # Save
    if total_changed > 0:
        print(f"Saving {total_changed} changes...")
        BLAZE_ALL.write_bytes(data)
        print(f"[SAVED]  {BLAZE_ALL}")
    else:
        print("No changes detected.")

    # Summary
    print()
    print("=" * 70)
    print(f"Entries checked:  {total_checked}")
    print(f"Entries changed:  {total_changed}")
    print(f"Errors:           {len(errors)}")
    print("=" * 70)


if __name__ == '__main__':
    main()
