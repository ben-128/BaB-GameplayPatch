#!/usr/bin/env python3
"""
Expand monster slots by relocating zone_spawns area.

Strategy:
1. Calculate available space in zone_spawns area
2. Move zone_spawns forward to make room for new monster slots
3. Insert new monster slot data in freed space
4. Update all offsets pointing to zone_spawns
5. Update JSON configuration

Usage:
  python expand_monster_slots.py --area cavern_f1_a1 --add-slots 2 --dry-run
  python expand_monster_slots.py --area cavern_f1_a1 --add-slots 2 --apply
"""

import struct
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
FORMATIONS_DIR = PROJECT_ROOT / "Data" / "formations"

# Area configurations
AREA_CONFIGS = {
    'cavern_f1_a1': {
        'name': 'Cavern of Death - Floor 1 Area 1',
        'json_path': 'cavern_of_death/floor_1_area_1.json',
        'group_offset': 0xF7A97C,
        'num_monsters': 3,
        'script_start': 0xF7AA9C,
        'zone_spawns_start': 0xF7B37C,  # From formation_area_start + formation_area_bytes
        'zone_spawns_bytes': 5416,       # From zone_spawns_area_bytes
    },
}

BYTES_PER_SLOT = 120  # 8 (anim_table) + 8 (anim_record) + 8 (assignments) + 96 (stats)


def read_u32_le(data, offset):
    """Read uint32 little-endian"""
    return struct.unpack('<I', data[offset:offset+4])[0]


def write_u32_le(data, offset, value):
    """Write uint32 little-endian"""
    struct.pack_into('<I', data, offset, value)


def find_offset_references(blaze_data, target_offset, search_range=None):
    """
    Find all references to a specific offset in the binary.
    Returns list of locations where the offset appears.
    """
    target_bytes = struct.pack('<I', target_offset)
    references = []

    search_start = search_range[0] if search_range else 0
    search_end = search_range[1] if search_range else len(blaze_data)

    offset = search_start
    while offset < search_end - 4:
        if blaze_data[offset:offset+4] == target_bytes:
            references.append(offset)
            offset += 4
        else:
            offset += 1

    return references


def analyze_expansion_feasibility(area_config, num_new_slots):
    """
    Analyze if we can add new slots by moving zone_spawns.
    """

    space_needed = num_new_slots * BYTES_PER_SLOT
    zone_spawns_bytes = area_config['zone_spawns_bytes']

    # Calculate how much we can actually move zone_spawns
    # We need to keep enough space for existing zone_spawn records
    # Assume we want to keep at least 50% of zone_spawn space free

    min_zone_spawn_space = zone_spawns_bytes // 2
    max_relocation = zone_spawns_bytes - min_zone_spawn_space

    return {
        'space_needed': space_needed,
        'zone_spawns_total': zone_spawns_bytes,
        'max_relocation': max_relocation,
        'can_add': max_relocation >= space_needed,
        'num_slots_possible': max_relocation // BYTES_PER_SLOT,
    }


def create_default_monster_slot(slot_index, template_monster_name="NewMonster"):
    """
    Create default data for a new monster slot.
    This creates a placeholder that can be customized later.
    """

    # Default animation table (8 bytes) - copy from a simple monster
    anim_table = bytes([0x04, 0x04, 0x05, 0x05, 0x06, 0x06, 0x07, 0x07])

    # Default animation record (8 bytes)
    anim_pointer = struct.pack('<I', 0x0C)  # Points to animation data
    texture_ref = struct.pack('<I', 0x00000300)  # Default texture
    anim_record = anim_pointer + texture_ref

    # Default assignments (8 bytes: L_entry + R_entry)
    L_entry = bytes([slot_index, 0x00, 0x00, 0x00])  # L = 0 (basic AI)
    R_entry = bytes([slot_index, 0x00, 0x00, 0x40])  # R = 0
    assignments = L_entry + R_entry

    # Default stats (96 bytes)
    name = template_monster_name.encode('ascii')[:16].ljust(16, b'\x00')

    # Stats as uint16 values
    stats_values = [
        0,      # exp
        1,      # level
        50,     # hp
        0,      # magic
        0,      # randomness
        1,      # collider_type
        1,      # death_fx_size
        0,      # hit_fx_id
        100,    # collider_size
        5,      # drop_rate
        0,      # creature_type
        0,      # armor_type
        0,      # elem_fire_ice
        0,      # elem_poison_air
        0,      # elem_light_night
        0,      # elem_divine_malefic
        10,     # dmg
        5,      # armor
    ] + [0] * 22  # Pad remaining 22 uint16 values

    stats_bytes = name + b''.join(struct.pack('<H', v) for v in stats_values)

    return {
        'animation_table': anim_table,
        'animation_record': anim_record,
        'assignments': assignments,
        'stats': stats_bytes,
        'total': anim_table + anim_record + assignments + stats_bytes
    }


def expand_area_slots(blaze_data, area_config, num_new_slots, template_names=None):
    """
    Expand monster slots by relocating zone_spawns.

    Steps:
    1. Move zone_spawns data forward by (num_new_slots * BYTES_PER_SLOT)
    2. Insert new monster slot data in freed space
    3. Update animation table header to include new slots
    4. Update offsets in formation JSON
    """

    if template_names is None:
        template_names = [f"NewMonster{i+1}" for i in range(num_new_slots)]

    relocation_bytes = num_new_slots * BYTES_PER_SLOT

    old_zone_start = area_config['zone_spawns_start']
    new_zone_start = old_zone_start + relocation_bytes
    zone_bytes = area_config['zone_spawns_bytes']

    print(f"\n[RELOCATION PLAN]")
    print(f"  Old zone_spawns start: 0x{old_zone_start:X}")
    print(f"  New zone_spawns start: 0x{new_zone_start:X}")
    print(f"  Relocation distance:   {relocation_bytes} bytes")
    print(f"  Adding {num_new_slots} slots:")
    for i, name in enumerate(template_names):
        print(f"    Slot {area_config['num_monsters'] + i}: {name}")
    print()

    # Step 1: Move zone_spawns data
    zone_spawns_data = blaze_data[old_zone_start:old_zone_start + zone_bytes]

    # Create new data with expansion
    new_data = bytearray(blaze_data)

    # Insert space for new slots
    insertion_point = old_zone_start
    new_data[insertion_point:insertion_point] = b'\x00' * relocation_bytes

    # Copy zone_spawns to new location
    new_data[new_zone_start:new_zone_start + zone_bytes] = zone_spawns_data

    # Step 2: Insert new monster slot data
    current_num = area_config['num_monsters']
    group_offset = area_config['group_offset']

    # Find animation section
    assignments_start = group_offset - (current_num * 8)

    # Search for animation header
    search_start = max(0, assignments_start - 1000)
    anim_header_offset = None

    for i in range(assignments_start - 8, search_start, -1):
        if (new_data[i:i+4] == b'\x00\x00\x00\x00' and
            new_data[i+4:i+8] == b'\x04\x00\x00\x00'):
            anim_header_offset = i
            break

    if not anim_header_offset:
        print("[ERROR] Animation header not found!")
        return None

    anim_table_start = anim_header_offset + 8
    anim_records_start = anim_table_start + (current_num * 8)

    # Insert new slots
    for i, name in enumerate(template_names):
        slot_index = current_num + i
        slot_data = create_default_monster_slot(slot_index, name)

        # Insert at end of each section
        # Animation table
        insert_pos = anim_records_start + (i * 8)
        new_data[insert_pos:insert_pos] = slot_data['animation_table']

        # Animation record
        insert_pos = assignments_start + (i * 8)
        new_data[insert_pos:insert_pos] = slot_data['animation_record']

        # Assignments
        insert_pos = group_offset + (i * 8)
        new_data[insert_pos:insert_pos] = slot_data['assignments']

        # Stats
        insert_pos = group_offset + (current_num * 96) + (i * 96)
        new_data[insert_pos:insert_pos] = slot_data['stats']

    return {
        'modified_data': new_data,
        'new_zone_start': new_zone_start,
        'new_num_monsters': current_num + num_new_slots,
        'monster_names': template_names,
    }


def update_formation_json(area_config, new_zone_start, new_num_monsters, new_monster_names):
    """
    Update formation JSON with new offsets and monster list.
    """

    json_path = FORMATIONS_DIR / area_config['json_path']

    with open(json_path) as f:
        data = json.load(f)

    # Update monsters list
    current_monsters = data.get('monsters', [])
    data['monsters'] = current_monsters + new_monster_names

    # Update zone_spawns offset if it exists
    if 'zone_spawns_area_start' in data:
        old_start = data['zone_spawns_area_start']
        data['zone_spawns_area_start'] = hex(new_zone_start)
        print(f"[JSON UPDATE] zone_spawns_area_start: {old_start} -> {hex(new_zone_start)}")

    # Add metadata
    if 'slot_expansion' not in data:
        data['slot_expansion'] = {}

    data['slot_expansion']['expanded'] = True
    data['slot_expansion']['original_slots'] = area_config['num_monsters']
    data['slot_expansion']['current_slots'] = new_num_monsters
    data['slot_expansion']['expansion_date'] = datetime.now().isoformat()

    # Save backup
    backup_path = json_path.with_suffix('.json.backup')
    shutil.copy2(json_path, backup_path)
    print(f"[BACKUP] Created: {backup_path.name}")

    # Save updated JSON
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[JSON UPDATE] Saved: {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Expand monster slots by relocating zone_spawns area',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would happen
  python expand_monster_slots.py --area cavern_f1_a1 --add-slots 2 --dry-run

  # Actually apply changes
  python expand_monster_slots.py --area cavern_f1_a1 --add-slots 2 --apply

  # Custom monster names
  python expand_monster_slots.py --area cavern_f1_a1 --add-slots 2 --names "Wolf,Troll" --apply
        """
    )

    parser.add_argument('--area', required=True, choices=list(AREA_CONFIGS.keys()),
                       help='Area to modify')
    parser.add_argument('--add-slots', type=int, required=True,
                       help='Number of slots to add (1-5)')
    parser.add_argument('--names', help='Comma-separated monster names (optional)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show plan without applying changes')
    parser.add_argument('--apply', action='store_true',
                       help='Apply changes to BLAZE.ALL')

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")

    if args.add_slots < 1 or args.add_slots > 5:
        parser.error("Number of slots must be between 1 and 5")

    # Parse monster names
    monster_names = None
    if args.names:
        monster_names = [n.strip() for n in args.names.split(',')]
        if len(monster_names) != args.add_slots:
            parser.error(f"Number of names ({len(monster_names)}) must match add-slots ({args.add_slots})")

    print("="*70)
    print("MONSTER SLOT EXPANSION TOOL")
    print("="*70)
    print()

    area_config = AREA_CONFIGS[args.area]

    print(f"[AREA] {area_config['name']}")
    print(f"       Current slots: {area_config['num_monsters']}")
    print(f"       Target slots:  {area_config['num_monsters'] + args.add_slots}")
    print()

    # Analyze feasibility
    analysis = analyze_expansion_feasibility(area_config, args.add_slots)

    print("[FEASIBILITY ANALYSIS]")
    print(f"  Space needed:        {analysis['space_needed']} bytes")
    print(f"  Zone_spawns total:   {analysis['zone_spawns_total']} bytes")
    print(f"  Max relocation:      {analysis['max_relocation']} bytes")
    print(f"  Max slots possible:  {analysis['num_slots_possible']} slots")
    print()

    if not analysis['can_add']:
        print(f"[ERROR] Cannot add {args.add_slots} slots!")
        print(f"        Maximum possible: {analysis['num_slots_possible']} slots")
        return 1

    print(f"[OK] Can add {args.add_slots} slots")
    print()

    if args.dry_run:
        print("[DRY RUN] Showing plan only, not applying changes")
        print()
        print("If --apply was used, would:")
        print(f"  1. Move zone_spawns +{analysis['space_needed']} bytes")
        print(f"  2. Insert {args.add_slots} new monster slots")
        print(f"  3. Update formation JSON")
        print(f"  4. Create BLAZE.ALL backup")
        print()
        print("To apply, run with --apply instead of --dry-run")
        return 0

    # Load BLAZE.ALL
    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        return 1

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = bytearray(f.read())

    print(f"[OK] Loaded BLAZE.ALL ({len(blaze_data):,} bytes)")
    print()

    # Create backup
    backup_path = BLAZE_ALL.with_suffix('.ALL.backup')
    shutil.copy2(BLAZE_ALL, backup_path)
    print(f"[BACKUP] Created: {backup_path.name}")
    print()

    # Perform expansion
    result = expand_area_slots(blaze_data, area_config, args.add_slots, monster_names)

    if not result:
        print("[ERROR] Expansion failed")
        return 1

    # Save modified binary
    with open(BLAZE_ALL, 'wb') as f:
        f.write(result['modified_data'])

    print(f"[OK] Saved modified BLAZE.ALL")
    print()

    # Update JSON
    update_formation_json(
        area_config,
        result['new_zone_start'],
        result['new_num_monsters'],
        result['monster_names']
    )

    print()
    print("="*70)
    print("[SUCCESS] Monster slots expanded!")
    print("="*70)
    print()
    print("NEXT STEPS:")
    print("1. Test in-game to verify expansion works")
    print("2. Use formation editor to assign monsters to new slots")
    print("3. Customize new monster stats/AI by copying from other areas")
    print()
    print(f"New slots: {', '.join(result['monster_names'])}")

    return 0


if __name__ == '__main__':
    exit(main())
