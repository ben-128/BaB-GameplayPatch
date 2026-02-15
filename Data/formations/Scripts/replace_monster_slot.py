#!/usr/bin/env python3
"""
SAFE Monster Slot Replacement Tool

Instead of adding slots (which breaks offsets), this tool REPLACES
an existing slot with data from another monster.

Example: Replace Goblin with Wolf in Cavern F1 A1

This is SAFE because:
- No bytes inserted/removed (file size unchanged)
- No offsets broken
- Direct data replacement

Usage:
  python replace_monster_slot.py --area cavern_f1_a1 --replace-slot 0 --with "Wolf" --from castle_f1_a1 --dry-run
  python replace_monster_slot.py --area cavern_f1_a1 --replace-slot 0 --with "Wolf" --from castle_f1_a1 --apply
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

# Area configurations with known monster locations
AREA_CONFIGS = {
    'cavern_f1_a1': {
        'name': 'Cavern of Death - Floor 1 Area 1',
        'json_path': 'cavern_of_death/floor_1_area_1.json',
        'group_offset': 0xF7A97C,
        'num_monsters': 3,
        'monsters': ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat'],
    },
    'castle_f1_a1': {
        'name': 'Castle of Vamp - Floor 1 Area 1',
        'json_path': 'castle_of_vamp/floor_1_area_1.json',
        'group_offset': 0x24024FC,
        'num_monsters': 5,
        'monsters': ['Vampire-Bat', 'Vampire', 'Wolf', 'Lesser-Vampire', 'Living-Sword'],
    },
}


def read_u32_le(data, offset):
    return struct.unpack('<I', data[offset:offset+4])[0]


def extract_monster_slot_data(blaze_data, area_config, slot_index):
    """
    Extract complete monster data for one slot:
    - Animation table (8 bytes)
    - Animation record (8 bytes)
    - Assignments L/R (8 bytes)
    - Stats (96 bytes)
    Total: 120 bytes
    """

    group_offset = area_config['group_offset']
    num_monsters = area_config['num_monsters']

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

    # Extract each section for this slot
    data = {
        'animation_table': blaze_data[anim_table_start + slot_index*8 : anim_table_start + (slot_index+1)*8],
        'animation_record': blaze_data[anim_records_start + slot_index*8 : anim_records_start + (slot_index+1)*8],
        'assignments': blaze_data[assignments_start + slot_index*8 : assignments_start + (slot_index+1)*8],
        'stats': blaze_data[group_offset + slot_index*96 : group_offset + (slot_index+1)*96],
    }

    # Extract name from stats
    name_bytes = data['stats'][:16]
    data['name'] = name_bytes.rstrip(b'\x00').decode('ascii', errors='replace')

    # Extract level and HP for display
    data['level'] = struct.unpack('<H', data['stats'][18:20])[0]
    data['hp'] = struct.unpack('<H', data['stats'][20:22])[0]

    # Store offsets for replacement
    data['offsets'] = {
        'animation_table': anim_table_start + slot_index*8,
        'animation_record': anim_records_start + slot_index*8,
        'assignments': assignments_start + slot_index*8,
        'stats': group_offset + slot_index*96,
    }

    return data


def replace_monster_slot(blaze_data, target_area, target_slot, source_data):
    """
    Replace target slot with source data.
    Returns modified data.
    """

    group_offset = target_area['group_offset']
    num_monsters = target_area['num_monsters']

    # Calculate target offsets
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

    # Create modified data
    new_data = bytearray(blaze_data)

    # Replace each section
    offsets = {
        'animation_table': anim_table_start + target_slot*8,
        'animation_record': anim_records_start + target_slot*8,
        'assignments': assignments_start + target_slot*8,
        'stats': group_offset + target_slot*96,
    }

    new_data[offsets['animation_table']:offsets['animation_table']+8] = source_data['animation_table']
    new_data[offsets['animation_record']:offsets['animation_record']+8] = source_data['animation_record']
    new_data[offsets['assignments']:offsets['assignments']+8] = source_data['assignments']
    new_data[offsets['stats']:offsets['stats']+96] = source_data['stats']

    return new_data


def main():
    parser = argparse.ArgumentParser(
        description='Replace monster slot with data from another area',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replace Goblin (slot 0) with Wolf from Castle
  python replace_monster_slot.py --area cavern_f1_a1 --replace-slot 0 --with "Wolf" --from castle_f1_a1 --dry-run

  # Replace Bat (slot 2) with Vampire
  python replace_monster_slot.py --area cavern_f1_a1 --replace-slot 2 --with "Vampire" --from castle_f1_a1 --apply
        """
    )

    parser.add_argument('--area', required=True, choices=list(AREA_CONFIGS.keys()),
                       help='Target area to modify')
    parser.add_argument('--replace-slot', type=int, required=True,
                       help='Slot index to replace (0, 1, 2, etc.)')
    parser.add_argument('--with', dest='monster_name', required=True,
                       help='Monster name to copy (e.g. "Wolf")')
    parser.add_argument('--from', dest='source_area', required=True, choices=list(AREA_CONFIGS.keys()),
                       help='Source area to copy from')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show plan without applying')
    parser.add_argument('--apply', action='store_true',
                       help='Apply changes to BLAZE.ALL')

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")

    print("="*70)
    print("MONSTER SLOT REPLACEMENT TOOL")
    print("="*70)
    print()

    target_config = AREA_CONFIGS[args.area]
    source_config = AREA_CONFIGS[args.source_area]

    # Validate slot index
    if args.replace_slot < 0 or args.replace_slot >= target_config['num_monsters']:
        print(f"[ERROR] Slot {args.replace_slot} out of range for {target_config['name']}")
        print(f"        Valid range: 0-{target_config['num_monsters']-1}")
        return 1

    # Find monster in source area
    try:
        source_slot = source_config['monsters'].index(args.monster_name)
    except ValueError:
        print(f"[ERROR] Monster '{args.monster_name}' not found in {source_config['name']}")
        print(f"        Available: {', '.join(source_config['monsters'])}")
        return 1

    print(f"[TARGET] {target_config['name']}")
    print(f"         Replacing slot {args.replace_slot}: {target_config['monsters'][args.replace_slot]}")
    print()
    print(f"[SOURCE] {source_config['name']}")
    print(f"         Copying slot {source_slot}: {args.monster_name}")
    print()

    # Load BLAZE.ALL
    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        return 1

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = bytearray(f.read())

    print(f"[OK] Loaded BLAZE.ALL ({len(blaze_data):,} bytes)")
    print()

    # Extract source monster data
    source_data = extract_monster_slot_data(blaze_data, source_config, source_slot)

    if not source_data:
        print("[ERROR] Failed to extract source monster data")
        return 1

    print(f"[EXTRACTED] {source_data['name']}")
    print(f"            Level: {source_data['level']}")
    print(f"            HP:    {source_data['hp']}")
    print()

    if args.dry_run:
        print("[DRY RUN] Not applying changes")
        print()
        print("Would replace:")
        print(f"  {target_config['monsters'][args.replace_slot]} -> {source_data['name']}")
        print()
        print("This is SAFE because:")
        print("  - No bytes inserted/removed")
        print("  - File size unchanged")
        print("  - No offsets broken")
        print()
        print("To apply, use --apply instead of --dry-run")
        return 0

    # Apply replacement
    print("[REPLACING] Monster data...")

    new_data = replace_monster_slot(blaze_data, target_config, args.replace_slot, source_data)

    if not new_data:
        print("[ERROR] Replacement failed")
        return 1

    # Create backup
    backup_path = BLAZE_ALL.with_suffix('.ALL.backup')
    shutil.copy2(BLAZE_ALL, backup_path)
    print(f"[BACKUP] Created: {backup_path.name}")

    # Save modified binary
    with open(BLAZE_ALL, 'wb') as f:
        f.write(new_data)

    print(f"[OK] Saved modified BLAZE.ALL")
    print()

    # Update JSON
    json_path = FORMATIONS_DIR / target_config['json_path']

    with open(json_path) as f:
        json_data = json.load(f)

    # Backup JSON
    json_backup = json_path.with_suffix('.json.backup')
    shutil.copy2(json_path, json_backup)
    print(f"[BACKUP] Created: {json_backup.name}")

    # Update monster list
    json_data['monsters'][args.replace_slot] = source_data['name']

    # Add metadata
    if 'slot_replacements' not in json_data:
        json_data['slot_replacements'] = []

    json_data['slot_replacements'].append({
        'slot': args.replace_slot,
        'original': target_config['monsters'][args.replace_slot],
        'replacement': source_data['name'],
        'source_area': args.source_area,
        'date': datetime.now().isoformat(),
    })

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"[JSON] Updated: {json_path.name}")
    print()

    print("="*70)
    print("[SUCCESS] Monster slot replaced!")
    print("="*70)
    print()
    print(f"Replaced: {target_config['monsters'][args.replace_slot]} -> {source_data['name']}")
    print()
    print("NEXT STEPS:")
    print("1. Test in-game to verify replacement works")
    print("2. Use formation editor to update formations using this slot")
    print("3. Rebuild game with build_gameplay_patch.bat")

    return 0


if __name__ == '__main__':
    exit(main())
