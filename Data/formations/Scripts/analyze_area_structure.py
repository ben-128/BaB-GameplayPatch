#!/usr/bin/env python3
"""
Analyze complete area structure to understand space available for adding monster slots.

This script extracts:
1. Animation table (8 bytes per slot)
2. 8-byte records (animation offset + texture ref)
3. Assignment entries (L/R values, 8 bytes per slot)
4. 96-byte stat entries
5. Available space before script area

Usage: python analyze_area_structure.py
"""

import struct
import json
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# Test with Cavern of Death Floor 1 Area 1
TEST_AREA = {
    'name': 'Cavern of Death - Floor 1 Area 1',
    'group_offset': 0xF7A97C,  # 96-byte entries start
    'num_monsters': 3,
    'script_area_start': 0xF7AA9C,  # Script area starts here
}


def read_u32_le(data, offset):
    """Read uint32 little-endian"""
    return struct.unpack('<I', data[offset:offset+4])[0]


def read_u16_le(data, offset):
    """Read uint16 little-endian"""
    return struct.unpack('<H', data[offset:offset+2])[0]


def extract_area_structure(blaze_data, area_info):
    """Extract complete area structure"""

    group_offset = area_info['group_offset']
    num_monsters = area_info['num_monsters']
    script_start = area_info['script_area_start']

    # Calculate offsets working backwards from group_offset
    stats_start = group_offset
    stats_end = stats_start + (num_monsters * 96)

    assignments_start = group_offset - (num_monsters * 8)
    assignments_end = group_offset

    # Find animation section (work backwards from assignments)
    # Animation table header: [00000000 04000000]
    search_start = max(0, assignments_start - 1000)
    anim_header_offset = None

    for i in range(assignments_start - 8, search_start, -1):
        if (blaze_data[i:i+4] == b'\x00\x00\x00\x00' and
            blaze_data[i+4:i+8] == b'\x04\x00\x00\x00'):
            anim_header_offset = i
            break

    if not anim_header_offset:
        print("[WARNING] Animation header not found!")
        return None

    anim_table_start = anim_header_offset + 8
    anim_records_start = anim_table_start + (num_monsters * 8)
    anim_records_end = anim_records_start + (num_monsters * 8)

    # Extract data
    structure = {
        'area_name': area_info['name'],
        'num_monsters': num_monsters,
        'offsets': {
            'animation_header': hex(anim_header_offset),
            'animation_table': hex(anim_table_start),
            'animation_records': hex(anim_records_start),
            'assignments': hex(assignments_start),
            'stats': hex(stats_start),
            'script_area': hex(script_start),
        },
        'space_analysis': {
            'animation_section': anim_header_offset,
            'assignments_section': assignments_start,
            'stats_section': stats_start,
            'script_section': script_start,
            'total_monster_data_size': script_start - anim_header_offset,
            'bytes_per_monster': (script_start - anim_header_offset - 8) // num_monsters,  # -8 for header
        },
        'monsters': []
    }

    # Extract per-monster data
    for slot in range(num_monsters):
        # Animation table (8 bytes)
        anim_offset = anim_table_start + (slot * 8)
        anim_data = blaze_data[anim_offset:anim_offset+8]

        # Animation record (8 bytes: anim_off + texture_ref)
        rec_offset = anim_records_start + (slot * 8)
        anim_ptr = read_u32_le(blaze_data, rec_offset)
        texture_ref = read_u32_le(blaze_data, rec_offset + 4)

        # Assignments (L/R)
        assign_offset = assignments_start + (slot * 8)
        L_entry = blaze_data[assign_offset:assign_offset+4]
        R_entry = blaze_data[assign_offset+4:assign_offset+8]

        L_val = L_entry[1]
        R_val = R_entry[1]

        # Stats (96 bytes)
        stat_offset = stats_start + (slot * 96)
        name_bytes = blaze_data[stat_offset:stat_offset+16]
        name = name_bytes.rstrip(b'\x00').decode('ascii', errors='replace')

        level = read_u16_le(blaze_data, stat_offset + 18)
        hp = read_u16_le(blaze_data, stat_offset + 20)

        monster = {
            'slot': slot,
            'name': name,
            'level': level,
            'hp': hp,
            'animation_table': anim_data.hex(),
            'animation_pointer': hex(anim_ptr),
            'texture_ref': hex(texture_ref),
            'L_value': L_val,
            'R_value': R_val,
            'L_entry_raw': L_entry.hex(),
            'R_entry_raw': R_entry.hex(),
        }

        structure['monsters'].append(monster)

    # Calculate available space for new slots
    # Space available = script_start - stats_end
    available_space = script_start - stats_end
    bytes_per_slot = 8 + 8 + 8 + 96  # anim_table + anim_record + assignments + stats
    max_new_slots = available_space // bytes_per_slot

    structure['expansion_potential'] = {
        'available_bytes': available_space,
        'bytes_per_slot': bytes_per_slot,
        'max_new_slots': max_new_slots,
        'current_slots': num_monsters,
        'max_total_slots': num_monsters + max_new_slots,
    }

    return structure


def main():
    """Main analysis"""

    print("="*60)
    print("AREA STRUCTURE ANALYZER")
    print("="*60)
    print()

    if not BLAZE_ALL.exists():
        print(f"❌ BLAZE.ALL not found at: {BLAZE_ALL}")
        return

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = f.read()

    print(f"[OK] Loaded BLAZE.ALL ({len(blaze_data):,} bytes)")
    print()

    # Analyze test area
    structure = extract_area_structure(blaze_data, TEST_AREA)

    if not structure:
        print("[ERROR] Failed to extract structure")
        return

    # Display results
    print(f"[AREA] {structure['area_name']}")
    print(f"       Current monsters: {structure['num_monsters']}")
    print()

    print("[MEMORY LAYOUT]")
    for key, offset in structure['offsets'].items():
        print(f"  {key:20s} = {offset}")
    print()

    print("[MONSTER SLOTS]")
    for m in structure['monsters']:
        print(f"  Slot {m['slot']}: {m['name']:20s} Lv{m['level']:2d} HP{m['hp']:4d}")
        print(f"          L={m['L_value']:2d} R={m['R_value']:2d}")
        print(f"          Anim={m['animation_pointer']} Tex={m['texture_ref']}")
        print()

    print("[SPACE ANALYSIS]")
    exp = structure['expansion_potential']
    print(f"  Available space: {exp['available_bytes']} bytes")
    print(f"  Bytes per slot:  {exp['bytes_per_slot']} bytes")
    print(f"  Max new slots:   {exp['max_new_slots']} slots")
    print(f"  Current total:   {exp['current_slots']} slots")
    print(f"  Max possible:    {exp['max_total_slots']} slots")
    print()

    if exp['max_new_slots'] > 0:
        print(f"[SUCCESS] CAN ADD {exp['max_new_slots']} NEW MONSTER SLOTS!")
    else:
        print("[WARNING] No space available for new slots")

    # Save to JSON
    output_file = SCRIPT_DIR / 'area_structure_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(structure, f, indent=2)

    print()
    print(f"[SAVED] Detailed analysis to: {output_file.name}")


if __name__ == '__main__':
    main()
