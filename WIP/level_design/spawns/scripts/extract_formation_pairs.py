"""
Extract and analyze formation pairs from all spawn groups.

Hypothesis: The L value (byte 1 of LEFT 4-byte entry in formation pairs)
is a ZONE-LOCAL model/visual index that controls which 3D model the game uses.

This script extracts all formation pairs and checks if L is consistent
per monster type within each zone.
"""

import struct
import json
import os
from collections import defaultdict

BLAZE_ALL = r"Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL"
SPAWN_DIR = r"WIP\level_design\spawns\data\spawn_groups"
INDEX_FILE = r"Data\monster_stats\_index.json"


def load_monster_index():
    with open(INDEX_FILE, 'r') as f:
        data = json.load(f)
    return {m['name']: m for m in data['monsters']}


def load_all_spawn_groups():
    groups = []
    for fname in sorted(os.listdir(SPAWN_DIR)):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(SPAWN_DIR, fname), 'r') as f:
            data = json.load(f)
        level = data.get('level_name', fname)
        for g in data['groups']:
            groups.append({
                'level': level,
                'name': g['name'],
                'offset': int(g['offset'], 16),
                'monsters': g['monsters'],
                'num_monsters': len(g['monsters'])
            })
    return groups


def find_formation_pairs(blaze_data, group_offset, num_monsters):
    """
    Find formation pairs in the region before the group offset.

    Structure found:
    - Animation table (variable size, incrementing byte values)
    - 8-byte records: [uint32 offset] [packed: flags + value]
    - Zero padding
    - Offset table: N x uint32 values
    - Zero terminator
    - Formation pairs: N x 8 bytes each = [slot, L_param, 0, 0] [slot, R_param, 0, 0x40]
    - Then the 96-byte monster entries start
    """
    # Search backwards from group_offset for the formation pairs
    # They should be in the last ~128 bytes before the names

    pairs = []

    # Read up to 128 bytes before the group
    search_start = max(0, group_offset - 128)
    pre_data = blaze_data[search_start:group_offset]

    # The formation pairs end right at group_offset
    # They are 8 bytes each: [slot, L, extra, flags_L] [slot, R, extra, flags_R]
    # The 0x40 flag marks the RIGHT entry of each pair

    # Work backwards from the end to find pairs
    # The last few bytes before group should be formation pairs
    # ending pattern: XX YY 00 40 (the last RIGHT entry)

    # Find all 4-byte entries with 0x40 in byte 3 (RIGHT entries)
    right_entries = []
    for i in range(len(pre_data) - 4, -1, -4):
        entry = pre_data[i:i+4]
        if len(entry) == 4:
            if entry[3] == 0x40 and entry[2] == 0x00:
                right_entries.append((search_start + i, entry))
            elif entry[3] == 0x00 and entry[2] == 0x00:
                # Could be a LEFT entry
                pass

    # Now find contiguous formation pair region
    # Scan backwards from group_offset looking for paired entries
    pos = group_offset - 8  # Start 8 bytes before names
    found_pairs = []

    while pos >= search_start and len(found_pairs) < num_monsters + 2:
        right_entry = blaze_data[pos+4:pos+8]
        left_entry = blaze_data[pos:pos+4]

        if len(right_entry) < 4 or len(left_entry) < 4:
            break

        r_slot, r_param, r_extra, r_flag = right_entry[0], right_entry[1], right_entry[2], right_entry[3]
        l_slot, l_param, l_extra, l_flag = left_entry[0], left_entry[1], left_entry[2], left_entry[3]

        # A valid pair has: flag_R = 0x40, flag_L = 0x00
        # And slot values should be small (0-7)
        if r_flag == 0x40 and r_extra == 0x00 and l_flag == 0x00 and l_extra == 0x00:
            if l_slot < 16 and r_slot < 16:
                found_pairs.insert(0, {
                    'offset': pos,
                    'l_slot': l_slot,
                    'l_param': l_param,
                    'r_slot': r_slot,
                    'r_param': r_param,
                    'hex': blaze_data[pos:pos+8].hex()
                })
                pos -= 8
                continue

        # Check if we hit the zero terminator or offset table
        break

    return found_pairs


def main():
    print("=" * 80)
    print("FORMATION PAIR ANALYSIS - Monster Visual/Model Link")
    print("=" * 80)

    monster_index = load_monster_index()
    groups = load_all_spawn_groups()

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = f.read()

    # Per-zone tracking: zone -> {monster_name -> set of L values}
    zone_model_map = defaultdict(lambda: defaultdict(set))
    # Per-zone: zone -> {L_value -> set of monster names}
    zone_l_to_monsters = defaultdict(lambda: defaultdict(set))
    # All pairs data
    all_pairs_data = []

    for group in groups:
        offset = group['offset']
        num = group['num_monsters']
        level = group['level']

        # Verify monster names at offset
        verified_names = []
        for i in range(num):
            name_off = offset + i * 96
            if name_off + 16 <= len(blaze_data):
                name = blaze_data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii', errors='replace')
                verified_names.append(name)
            else:
                verified_names.append('???')

        # Extract formation pairs
        pairs = find_formation_pairs(blaze_data, offset, num)

        print(f"\n--- {level} / {group['name']} (offset 0x{offset:X}) ---")
        print(f"  Monsters ({num}): {', '.join(verified_names)}")
        print(f"  Pairs found: {len(pairs)}")

        if not pairs:
            print(f"  WARNING: No pairs found!")
            continue

        for p in pairs:
            # Map L slot to monster name
            l_slot = p['l_slot']
            monster_name = verified_names[l_slot] if l_slot < len(verified_names) else f'slot{l_slot}'

            print(f"  Pair: slot={p['l_slot']} L={p['l_param']:2d} | "
                  f"slot={p['r_slot']} R={p['r_param']:2d} | "
                  f"hex={p['hex']} -> {monster_name}")

            zone_model_map[level][monster_name].add(p['l_param'])
            zone_l_to_monsters[level][p['l_param']].add(monster_name)

            all_pairs_data.append({
                'level': level,
                'group': group['name'],
                'monster': monster_name,
                'l_param': p['l_param'],
                'r_param': p['r_param'],
                'l_slot': p['l_slot'],
                'r_slot': p['r_slot']
            })

    # ANALYSIS: Check consistency of L values per monster per zone
    print("\n" + "=" * 80)
    print("CONSISTENCY CHECK: L value per monster per zone")
    print("=" * 80)

    consistent_count = 0
    inconsistent_count = 0
    shared_model_count = 0

    for zone in sorted(zone_model_map.keys()):
        print(f"\n  Zone: {zone}")
        print(f"  {'Monster':<20s} {'L values':<20s} {'Consistent?'}")
        print(f"  {'-'*60}")

        for monster in sorted(zone_model_map[zone].keys()):
            l_values = zone_model_map[zone][monster]
            consistent = len(l_values) == 1
            status = "YES" if consistent else "NO !!!"
            if consistent:
                consistent_count += 1
            else:
                inconsistent_count += 1
            print(f"  {monster:<20s} {str(l_values):<20s} {status}")

    print(f"\n  TOTAL: {consistent_count} consistent, {inconsistent_count} inconsistent")

    # Show L -> Monster mapping per zone
    print("\n" + "=" * 80)
    print("L VALUE -> MONSTER MAPPING (per zone)")
    print("=" * 80)

    for zone in sorted(zone_l_to_monsters.keys()):
        print(f"\n  Zone: {zone}")
        for l_val in sorted(zone_l_to_monsters[zone].keys()):
            monsters = zone_l_to_monsters[zone][l_val]
            shared = " [SHARED MODEL]" if len(monsters) > 1 else ""
            print(f"    L={l_val:2d} -> {', '.join(sorted(monsters))}{shared}")

    # Cross-zone check: same monster in different zones
    print("\n" + "=" * 80)
    print("CROSS-ZONE CHECK: Same monster, different zones")
    print("=" * 80)

    monster_zones = defaultdict(list)
    for zone in zone_model_map:
        for monster in zone_model_map[zone]:
            for l_val in zone_model_map[zone][monster]:
                monster_zones[monster].append((zone, l_val))

    for monster in sorted(monster_zones.keys()):
        appearances = monster_zones[monster]
        if len(appearances) > 1:
            # Check if L is the same across zones
            l_values = set(l for _, l in appearances)
            cross_consistent = len(l_values) == 1
            status = "SAME L" if cross_consistent else "DIFFERENT L (zone-local!)"
            zones_str = ', '.join(f'{z}: L={l}' for z, l in appearances)
            print(f"  {monster:<20s} {status:30s} [{zones_str}]")


if __name__ == '__main__':
    main()
