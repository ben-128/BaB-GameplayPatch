#!/usr/bin/env python3
"""
Add a new monster slot to an area by copying from another area.

This tool:
1. Extracts complete monster data (animation, assignments, stats) from source area
2. Relocates script area to make space for new slot
3. Inserts new monster slot
4. Updates all offsets and pointers

WARNING: This modifies binary structure and may require code patches!

Usage: python add_monster_slot.py --source "Castle F1" --target "Cavern F1 A1" --monster "Wolf"
"""

import struct
import json
import argparse
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Monster database - maps monster names to areas where they exist
MONSTER_LOCATIONS = {
    'Wolf': [
        {'area': 'Castle F1 A1', 'group': 0x24024FC, 'slot': 2, 'num': 5},
    ],
    'Vampire': [
        {'area': 'Castle F5 A1', 'group': 0x2434FEC, 'slot': 0, 'num': 3},
    ],
    # Add more as needed
}

# Area definitions
AREAS = {
    'Cavern F1 A1': {
        'group_offset': 0xF7A97C,
        'num_monsters': 3,
        'script_start': 0xF7AA9C,
        'json': 'Data/formations/cavern_of_death/floor_1_area_1.json',
    },
    'Castle F1 A1': {
        'group_offset': 0x24024FC,
        'num_monsters': 5,
        'script_start': 0x2402664,
        'json': 'Data/formations/castle_of_vamp/floor_1_area_1.json',
    },
}


def read_u32_le(data, offset):
    return struct.unpack('<I', data[offset:offset+4])[0]


def write_u32_le(data, offset, value):
    struct.pack_into('<I', data, offset, value)


def extract_monster_slot(blaze_data, area_info, slot_index):
    """Extract complete monster data for one slot"""

    group_offset = area_info['group_offset']
    num_monsters = area_info['num_monsters']

    # Calculate section offsets
    assignments_start = group_offset - (num_monsters * 8)

    # Find animation section
    search_start = max(0, assignments_start - 1000)
    anim_header_offset = None

    for i in range(assignments_start - 8, search_start, -1):
        if (blaze_data[i:i+4] == b'\x00\x00\x00\x00' and
            blaze_data[i+4:i+8] == b'\x04\x00\x00\x00'):
            anim_header_offset = i
            break

    if not anim_header_offset:
        return None

    anim_table_start = anim_header_offset + 8
    anim_records_start = anim_table_start + (num_monsters * 8)

    # Extract slot data
    slot_data = {
        'animation_table': blaze_data[anim_table_start + slot_index*8:anim_table_start + (slot_index+1)*8],
        'animation_record': blaze_data[anim_records_start + slot_index*8:anim_records_start + (slot_index+1)*8],
        'assignments': blaze_data[assignments_start + slot_index*8:assignments_start + (slot_index+1)*8],
        'stats': blaze_data[group_offset + slot_index*96:group_offset + (slot_index+1)*96],
    }

    # Extract name
    name_bytes = slot_data['stats'][:16]
    slot_data['name'] = name_bytes.rstrip(b'\x00').decode('ascii', errors='replace')

    return slot_data


def add_slot_to_area(blaze_data, target_area, slot_data):
    """
    Add a new slot to target area by:
    1. Moving script area forward by 120 bytes (space for new slot)
    2. Inserting new slot data at end of existing slots
    3. Updating offsets
    """

    group_offset = target_area['group_offset']
    num_monsters = target_area['num_monsters']
    script_start = target_area['script_start']

    BYTES_PER_SLOT = 120  # 8+8+8+96

    # Calculate insertion points
    stats_end = group_offset + (num_monsters * 96)
    new_script_start = script_start + BYTES_PER_SLOT

    print(f"\n[RELOCATION PLAN]")
    print(f"  Current script start: 0x{script_start:X}")
    print(f"  New script start:     0x{new_script_start:X}")
    print(f"  Moving {new_script_start - script_start} bytes forward")
    print(f"  Stats end:            0x{stats_end:X}")
    print()

    # This would require:
    # 1. Moving all script area data forward
    # 2. Updating ALL pointers that reference script area
    # 3. Updating formation patcher offsets
    # 4. Testing extensively

    print("[ERROR] Binary relocation is TOO RISKY!")
    print("Would break hardcoded offsets throughout the code.")
    print()
    print("SAFER ALTERNATIVE:")
    print("- Use formation editor to create varied encounters with existing 3 monsters")
    print("- Or mod a DIFFERENT area that has more monster variety")

    return None


def main():
    parser = argparse.ArgumentParser(description='Add monster slot to area')
    parser.add_argument('--monster', required=True, help='Monster name (e.g. Wolf)')
    parser.add_argument('--target', required=True, help='Target area (e.g. "Cavern F1 A1")')
    parser.add_argument('--dry-run', action='store_true', help='Show plan without modifying')

    args = parser.parse_args()

    print("="*60)
    print("MONSTER SLOT ADDITION TOOL")
    print("="*60)
    print()

    # Check if monster exists in database
    if args.monster not in MONSTER_LOCATIONS:
        print(f"[ERROR] Monster '{args.monster}' not in database")
        print(f"Available monsters: {', '.join(MONSTER_LOCATIONS.keys())}")
        return

    # Check if target area exists
    if args.target not in AREAS:
        print(f"[ERROR] Area '{args.target}' not in database")
        print(f"Available areas: {', '.join(AREAS.keys())}")
        return

    # Load BLAZE.ALL
    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found at: {BLAZE_ALL}")
        return

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = bytearray(f.read())

    print(f"[OK] Loaded BLAZE.ALL ({len(blaze_data):,} bytes)")
    print()

    # Get source location
    source_info = MONSTER_LOCATIONS[args.monster][0]
    print(f"[SOURCE] {args.monster} from {source_info['area']}, slot {source_info['slot']}")

    # Extract monster data
    source_area_info = {
        'group_offset': source_info['group'],
        'num_monsters': source_info['num'],
    }

    slot_data = extract_monster_slot(blaze_data, source_area_info, source_info['slot'])

    if not slot_data:
        print("[ERROR] Failed to extract monster data")
        return

    print(f"[OK] Extracted: {slot_data['name']}")
    print()

    # Try to add to target
    target_area = AREAS[args.target]
    result = add_slot_to_area(blaze_data, target_area, slot_data)


if __name__ == '__main__':
    # For now, just run analysis
    print("="*60)
    print("MONSTER SLOT ADDITION - FEASIBILITY ANALYSIS")
    print("="*60)
    print()
    print("[CONCLUSION]")
    print()
    print("Adding new monster slots requires RELOCATING the script area,")
    print("which would break hardcoded offsets throughout the game code.")
    print()
    print("This is TECHNICALLY POSSIBLE but EXTREMELY RISKY.")
    print()
    print("RECOMMENDED ALTERNATIVES:")
    print()
    print("1. USE EXISTING SLOTS CREATIVELY")
    print("   - Cavern has 3 monsters (Goblin, Shaman, Bat)")
    print("   - Can create varied formations with these 3")
    print("   - Use zone_spawn editor to place them strategically")
    print()
    print("2. MOD DIFFERENT AREAS")
    print("   - Some areas have 5-7 monster slots")
    print("   - More variety already available")
    print()
    print("3. REPLACE EXISTING SLOTS")
    print("   - Copy Wolf data OVER Goblin data")
    print("   - Changes Goblin to Wolf (loses Goblin)")
    print("   - Safe, no relocation needed")
    print()
    print("Would you like me to create a SLOT REPLACEMENT tool instead?")
