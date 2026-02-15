#!/usr/bin/env python3
"""
Add Monster Slots via Zone Reorganization - FIXED VERSION

Corrections:
1. Proper extraction of stats from new_slots
2. Correct animation section reconstruction with assignments
3. Proper size calculations

Usage:
  python reorganize_add_slots_FIXED.py --dry-run
  python reorganize_add_slots_FIXED.py --apply
"""

import struct
import json
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
JSON_PATH = PROJECT_ROOT / "Data/formations/cavern_of_death/floor_1_area_1.json"

# Current offsets (vanilla 3 monsters)
CURRENT = {
    'anim_header': 0xF7A900,
    'stats_start': 0xF7A97C,
    'script_start': 0xF7AA9C,
    'formation_start': 0xF7AFFC,
    'zone_spawns_start': 0xF7B37C,
    'num_monsters': 3,
}

# After reorganization
# Adding 2 slots = +244 bytes total (16+16+4+16+192)
# NOT 240! Must account for middle section +4 bytes
SHIFT = 244  # bytes to shift right (and reduce from zone_spawns)

NEW = {
    'anim_header': 0xF7A900,  # Unchanged
    'stats_start': 0xF7A97C + SHIFT,  # Shifted
    'script_start': 0xF7AA9C + SHIFT,  # Shifted
    'formation_start': 0xF7AFFC + SHIFT,  # Shifted
    'zone_spawns_start': 0xF7B37C + SHIFT,  # Shifted
    'num_monsters': 5,
}

# Offset references found in binary
FORMATION_START_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]


def create_new_monster_slots(num_slots=2):
    """Create placeholder data for new monster slots

    Returns: List of dicts, each containing separate sections
    """

    slots = []

    for i in range(num_slots):
        slot_idx = CURRENT['num_monsters'] + i

        # Animation table (8 bytes)
        anim_table = bytes([0x04, 0x04, 0x05, 0x05, 0x06, 0x06, 0x07, 0x07])

        # Animation record (8 bytes)
        anim_record = struct.pack('<II', 0x0C, 0x300)

        # Assignments L/R (8 bytes total)
        L_entry = bytes([slot_idx, 0x00, 0x00, 0x00])
        R_entry = bytes([slot_idx, 0x00, 0x00, 0x40])

        # Stats (96 bytes)
        name = f"NewSlot{i+1}".encode('ascii')[:16].ljust(16, b'\x00')
        stats = [0, 1, 50] + [0]*37  # exp=0, level=1, hp=50, rest=0
        stats_bytes = name + b''.join(struct.pack('<H', v) for v in stats)

        slots.append({
            'anim_table': anim_table,
            'anim_record': anim_record,
            'L_entry': L_entry,
            'R_entry': R_entry,
            'stats': stats_bytes,
        })

    return slots


def reorganize_zone(blaze_data):
    """
    Reorganize the zone by shifting everything right and inserting new slots.

    Structure BEFORE:
    [Anim Header 8B][Anim Tables 3×8][Anim Records 3×8][Zero Term][Assigns 3×8][Stats 3×96][Script][Formations][Zone_spawns]

    Structure AFTER:
    [Anim Header 8B][Anim Tables 5×8][Anim Records 5×8][Zero Term][Assigns 5×8][Stats 5×96][Script][Formations][Zone_spawns]
    """

    data = bytearray(blaze_data)

    # 1. Extract original sections
    anim_header_start = CURRENT['anim_header']
    stats_start = CURRENT['stats_start']
    script_start = CURRENT['script_start']
    formation_start = CURRENT['formation_start']
    zone_spawns_start = CURRENT['zone_spawns_start']

    # Animation header (8 bytes: 00000000 04000000)
    anim_header = data[anim_header_start:anim_header_start+8]

    # Animation tables (3 × 8 bytes)
    anim_tables_start = anim_header_start + 8
    anim_tables = data[anim_tables_start:anim_tables_start+24]

    # Animation records (3 × 8 bytes)
    anim_records_start = anim_tables_start + 24
    anim_records = data[anim_records_start:anim_records_start+24]

    # Everything between anim_records and assignments (zero terminator + offsets)
    # For 3 monsters: 44 bytes
    # For 5 monsters: 48 bytes (need to add 4 bytes)
    assignments_start = stats_start - 24  # 3 monsters × 8 bytes assignments
    middle_section_old = data[anim_records_start+24:assignments_start]

    # Expand middle section from 44 to 48 bytes
    # Insert 4 zero bytes after the first 8 bytes (after first 2 uint32)
    middle_section = bytearray(middle_section_old[:8] + bytes([0, 0, 0, 0]) + middle_section_old[8:])

    # CRITICAL: Update monster count in middle section byte[2]
    # Cavern vanilla has count at byte[2] = 0x03
    # Change it to 0x05 for 5 monsters
    if middle_section[2] == 0x03:
        middle_section[2] = 0x05
        print(f"  [PATCH] Middle section byte[2]: 0x03 -> 0x05 (monster count)")

    # Assignments (3 × 8 bytes: L and R entries)
    assignments = data[assignments_start:stats_start]

    # Stats (3 × 96 bytes)
    stats_size = CURRENT['num_monsters'] * 96
    stats_data = data[stats_start:stats_start + stats_size]

    # Script section
    script_size = formation_start - script_start
    script_data = data[script_start:formation_start]

    # Formation section
    formation_size = zone_spawns_start - formation_start
    formation_data = data[formation_start:zone_spawns_start]

    # Zone_spawns section
    zone_spawns_size = 5416  # Current allocation
    zone_spawns_data = data[zone_spawns_start:zone_spawns_start + zone_spawns_size]

    # 2. Create new slots
    new_slots = create_new_monster_slots(2)

    # 3. Build expanded animation section
    new_anim_tables = anim_tables
    new_anim_records = anim_records
    new_assignments = assignments
    new_stats = stats_data

    for slot in new_slots:
        new_anim_tables += slot['anim_table']
        new_anim_records += slot['anim_record']
        new_assignments += slot['L_entry'] + slot['R_entry']
        new_stats += slot['stats']

    # 4. Build new zone layout
    new_zone = bytearray()

    # Animation section
    new_zone += anim_header  # 8 bytes
    new_zone += new_anim_tables  # 5 × 8 = 40 bytes
    new_zone += new_anim_records  # 5 × 8 = 40 bytes
    new_zone += middle_section  # Variable (zero terminator + offsets)
    new_zone += new_assignments  # 5 × 8 = 40 bytes

    # Stats section
    new_zone += new_stats  # 5 × 96 = 480 bytes

    # Script section (moved right)
    new_zone += script_data

    # Formation section (moved right)
    new_zone += formation_data

    # Zone_spawns section (moved right, reduced allocation)
    new_zone_spawns_size = zone_spawns_size - SHIFT
    new_zone += zone_spawns_data[:new_zone_spawns_size]

    # 5. Write back to BLAZE.ALL
    zone_start = anim_header_start
    data[zone_start:zone_start + len(new_zone)] = new_zone

    print(f"\n[REORGANIZATION]")
    print(f"  Zone rebuilt: {len(new_zone)} bytes")
    print(f"  Animation header: {len(anim_header)} bytes")
    print(f"  Animation tables: {len(new_anim_tables)} bytes (5 slots)")
    print(f"  Animation records: {len(new_anim_records)} bytes (5 slots)")
    print(f"  Middle section: {len(middle_section)} bytes")
    print(f"  Assignments: {len(new_assignments)} bytes (5 slots)")
    print(f"  Stats: {len(new_stats)} bytes (5 slots)")
    print(f"  Script: {len(script_data)} bytes")
    print(f"  Formations: {len(formation_data)} bytes")
    print(f"  Zone_spawns: {new_zone_spawns_size} bytes")

    return data


def update_offset_references(blaze_data):
    """Update the 4 hardcoded references to formation_start"""

    data = bytearray(blaze_data)

    old_offset = CURRENT['formation_start']
    new_offset = NEW['formation_start']

    old_bytes = struct.pack('<I', old_offset)
    new_bytes = struct.pack('<I', new_offset)

    updated = 0
    for ref_loc in FORMATION_START_REFS:
        if data[ref_loc:ref_loc+4] == old_bytes:
            data[ref_loc:ref_loc+4] = new_bytes
            updated += 1
            print(f"  Updated ref at 0x{ref_loc:X}: 0x{old_offset:X} -> 0x{new_offset:X}")
        else:
            print(f"  WARNING: Ref at 0x{ref_loc:X} already different!")

    print(f"\n[OFFSETS] Updated {updated}/{len(FORMATION_START_REFS)} references")

    return data


def update_json():
    """Update formation JSON with new monster count"""

    with open(JSON_PATH) as f:
        data = json.load(f)

    # Backup
    backup = JSON_PATH.with_suffix('.json.backup2')
    shutil.copy2(JSON_PATH, backup)

    # Update monsters list
    if 'monsters' not in data:
        data['monsters'] = []

    if len(data['monsters']) < 3:
        data['monsters'] = ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat']

    # Replace if already has 5 slots (from previous run)
    if len(data['monsters']) >= 5:
        data['monsters'] = ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat', 'NewSlot1', 'NewSlot2']
    else:
        data['monsters'].extend(['NewSlot1', 'NewSlot2'])

    data['formation_area_start'] = hex(NEW['formation_start'])

    if 'zone_spawns_area_start' in data:
        data['zone_spawns_area_start'] = hex(NEW['zone_spawns_start'])
        data['zone_spawns_area_bytes'] = 5176  # Reduced by 240

    data['slot_expansion'] = {
        'expanded': True,
        'original_slots': 3,
        'current_slots': 5,
        'method': 'zone_reorganization',
        'shift_amount': SHIFT,
        'date': '2026-02-15',
    }

    with open(JSON_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n[JSON] Updated {JSON_PATH.name}")
    print(f"  Backup: {backup.name}")


def main():
    import sys

    dry_run = '--dry-run' in sys.argv
    apply_changes = '--apply' in sys.argv

    if not dry_run and not apply_changes:
        print("Usage: python reorganize_add_slots_FIXED.py --dry-run")
        print("       python reorganize_add_slots_FIXED.py --apply")
        return 1

    print("="*70)
    print("MONSTER SLOT ADDITION - Zone Reorganization (FIXED)")
    print("="*70)
    print()

    print("[PLAN]")
    print(f"  Add 2 monster slots (120 bytes each = 240 bytes total)")
    print(f"  Shift everything RIGHT by {SHIFT} bytes within zone")
    print(f"  Reduce zone_spawns allocation by {SHIFT} bytes")
    print(f"  Update {len(FORMATION_START_REFS)} offset references")
    print()

    print("[OFFSETS]")
    print(f"  Stats start:       0x{CURRENT['stats_start']:X} -> 0x{NEW['stats_start']:X}")
    print(f"  Script start:      0x{CURRENT['script_start']:X} -> 0x{NEW['script_start']:X}")
    print(f"  Formation start:   0x{CURRENT['formation_start']:X} -> 0x{NEW['formation_start']:X}")
    print(f"  Zone_spawns start: 0x{CURRENT['zone_spawns_start']:X} -> 0x{NEW['zone_spawns_start']:X}")
    print()

    if dry_run:
        print("[DRY RUN] Not applying changes")
        print()
        print("Would:")
        print("  1. Reorganize zone (shift+expand)")
        print("  2. Update 4 offset references")
        print("  3. Update JSON configuration")
        print()
        print("Run with --apply to execute")
        return 0

    # Load binary
    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        return 1

    with open(BLAZE_ALL, 'rb') as f:
        data = f.read()

    print(f"[OK] Loaded BLAZE.ALL ({len(data):,} bytes)\n")

    # Backup
    backup = BLAZE_ALL.with_suffix('.ALL.backup_fixed')
    shutil.copy2(BLAZE_ALL, backup)
    print(f"[BACKUP] {backup.name}\n")

    # Reorganize
    data = reorganize_zone(data)

    # Update offsets
    data = update_offset_references(data)

    # Save
    with open(BLAZE_ALL, 'wb') as f:
        f.write(data)

    print(f"\n[SAVED] {BLAZE_ALL.name}")

    # Update JSON
    update_json()

    print()
    print("="*70)
    print("[SUCCESS] Added 2 monster slots!")
    print("="*70)
    print()
    print("NEXT STEPS:")
    print("  1. Copy to bin: cp output/BLAZE.ALL 'Blaze  Blade.../extract/'")
    print("  2. Inject to BIN: python patch_blaze_all.py")
    print("  3. Test in-game (load Cavern F1)")

    return 0


if __name__ == '__main__':
    exit(main())
