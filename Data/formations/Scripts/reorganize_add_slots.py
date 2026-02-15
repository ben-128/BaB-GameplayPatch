#!/usr/bin/env python3
"""
Add Monster Slots via Zone Reorganization

Strategy (as per user suggestion):
1. Expand monster slot section by 240 bytes (2 new slots)
2. Shift script+formations+zone_spawns RIGHT by 240 bytes
3. "Eat" 240 bytes from zone_spawns free space (reduce allocation)
4. Update offset references (only 4 found for formation_start!)

Result:
- Monster slots: 3 -> 5
- Zone_spawns: 5416 -> 5176 bytes (still has >2900 bytes free)
- Everything AFTER this zone: UNCHANGED!

Usage:
  python reorganize_add_slots.py --dry-run
  python reorganize_add_slots.py --apply
"""

import struct
import json
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
JSON_PATH = PROJECT_ROOT / "Data/formations/cavern_of_death/floor_1_area_1.json"

# Current offsets
CURRENT = {
    'anim_header': 0xF7A900,
    'stats_start': 0xF7A97C,
    'script_start': 0xF7AA9C,
    'formation_start': 0xF7AFFC,
    'zone_spawns_start': 0xF7B37C,
    'num_monsters': 3,
}

# After reorganization (+240 bytes for 2 new slots)
SHIFT = 240  # bytes to shift right

NEW = {
    'anim_header': 0xF7A900,  # Unchanged
    'stats_start': 0xF7A944,  # +40 bytes (anim table grows)
    'script_start': 0xF7AADC,  # +240 (shifted)
    'formation_start': 0xF7B03C,  # +240 (shifted)
    'zone_spawns_start': 0xF7B3BC,  # +240 (shifted)
    'num_monsters': 5,
}

# Offset references found in binary
FORMATION_START_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]


def create_new_monster_slots(num_slots=2):
    """Create placeholder data for new monster slots"""

    slots_data = bytearray()

    for i in range(num_slots):
        slot_idx = CURRENT['num_monsters'] + i

        # Animation table (8 bytes)
        anim_table = bytes([0x04, 0x04, 0x05, 0x05, 0x06, 0x06, 0x07, 0x07])

        # Animation record (8 bytes)
        anim_record = struct.pack('<II', 0x0C, 0x300)

        # Assignments L/R (8 bytes)
        L_entry = bytes([slot_idx, 0x00, 0x00, 0x00])
        R_entry = bytes([slot_idx, 0x00, 0x00, 0x40])

        # Stats (96 bytes)
        name = f"NewSlot{i+1}".encode('ascii')[:16].ljust(16, b'\x00')
        stats = [0, 1, 50] + [0]*37  # exp=0, level=1, hp=50, rest=0
        stats_bytes = name + b''.join(struct.pack('<H', v) for v in stats)

        slots_data += anim_table + anim_record + L_entry + R_entry + stats_bytes

    return slots_data


def reorganize_zone(blaze_data):
    """
    Reorganize the zone by shifting script+formations+zone_spawns right
    and inserting new monster slots in the freed space.
    """

    data = bytearray(blaze_data)

    # 1. Extract sections that will move
    stats_start = CURRENT['stats_start']
    stats_size = 3 * 96  # 3 monsters
    stats_data = data[stats_start:stats_start + stats_size]

    script_start = CURRENT['script_start']
    script_end = CURRENT['formation_start']
    script_data = data[script_start:script_end]

    formation_start = CURRENT['formation_start']
    formation_end = CURRENT['zone_spawns_start']
    formation_data = data[formation_start:formation_end]

    zone_spawns_start = CURRENT['zone_spawns_start']
    zone_spawns_size = 5416  # Current allocation
    zone_spawns_data = data[zone_spawns_start:zone_spawns_start + zone_spawns_size]

    # 2. Extract animation section (before stats, won't move much)
    anim_start = CURRENT['anim_header']
    anim_size = stats_start - anim_start
    anim_data_original = data[anim_start:stats_start]

    # 3. Create new monster slots
    new_slots = create_new_monster_slots(2)

    # 4. Expand animation section for new slots (add 2x8 bytes for anim table)
    # Animation table grows by 16 bytes (2 slots * 8 bytes)
    # Animation records grow by 16 bytes (2 slots * 8 bytes)
    # Assignments grow by 16 bytes (2 slots * 8 bytes)
    # Total animation section growth: 48 bytes

    # For simplicity, we'll add placeholder animation data
    # The actual animation data would be copied from another monster
    extra_anim_table = bytes([0x04, 0x04, 0x05, 0x05, 0x06, 0x06, 0x07, 0x07] * 2)  # 16 bytes
    extra_anim_records = struct.pack('<II', 0x0C, 0x300) * 2  # 16 bytes

    # Build new animation section
    # Insert new anim table/records before the original assignments
    anim_header = anim_data_original[:8]  # [00000000 04000000]
    anim_table_old = anim_data_original[8:8+24]  # 3 monsters * 8
    anim_records_old = anim_data_original[32:32+24]  # 3 monsters * 8
    anim_rest = anim_data_original[56:]  # Remaining (zero terminator + offsets + assignments)

    new_anim_section = (anim_header + anim_table_old + extra_anim_table +
                        anim_records_old + extra_anim_records + anim_rest)

    # 5. Rebuild zone
    # Clear the zone first
    zone_start = anim_start
    zone_old_end = zone_spawns_start + zone_spawns_size
    zone_size = zone_old_end - zone_start

    # Build new layout
    new_zone = bytearray()

    # Animation section (expanded)
    new_zone += new_anim_section

    # Stats section (expanded to 5 monsters)
    new_zone += stats_data  # Original 3 monsters
    new_zone += new_slots[32:32+96*2]  # Stats for 2 new monsters (skip anim parts)

    # Script section (moved right)
    new_zone += script_data

    # Formation section (moved right)
    new_zone += formation_data

    # Zone_spawns section (moved right, reduced allocation)
    new_zone_spawns_size = zone_spawns_size - SHIFT
    new_zone += zone_spawns_data[:new_zone_spawns_size]

    # Write back
    data[zone_start:zone_start + len(new_zone)] = new_zone

    print(f"\n[REORGANIZATION]")
    print(f"  Zone rebuilt: {len(new_zone)} bytes")
    print(f"  Animation section: {len(new_anim_section)} bytes")
    print(f"  Stats: {len(stats_data) + 96*2} bytes (5 monsters)")
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

    print(f"\n[OFFSETS] Updated {updated}/{len(FORMATION_START_REFS)} references")

    return data


def update_json():
    """Update formation JSON with new monster count"""

    with open(JSON_PATH) as f:
        data = json.load(f)

    # Backup
    backup = JSON_PATH.with_suffix('.json.backup')
    shutil.copy2(JSON_PATH, backup)

    # Update monsters list (create if doesn't exist)
    if 'monsters' not in data:
        data['monsters'] = []

    # Ensure we have at least 3 monsters (vanilla)
    if len(data['monsters']) < 3:
        data['monsters'] = ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat']

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
        print("Usage: python reorganize_add_slots.py --dry-run")
        print("       python reorganize_add_slots.py --apply")
        return 1

    print("="*70)
    print("MONSTER SLOT ADDITION - Zone Reorganization")
    print("="*70)
    print()

    print("[PLAN]")
    print(f"  Add 2 monster slots (120 bytes each = 240 bytes total)")
    print(f"  Shift script+formations+zone_spawns RIGHT by {SHIFT} bytes")
    print(f"  Reduce zone_spawns allocation by {SHIFT} bytes")
    print(f"  Update {len(FORMATION_START_REFS)} offset references")
    print()

    print("[OFFSETS]")
    print(f"  Stats start:      0x{CURRENT['stats_start']:X} -> 0x{NEW['stats_start']:X}")
    print(f"  Script start:     0x{CURRENT['script_start']:X} -> 0x{NEW['script_start']:X}")
    print(f"  Formation start:  0x{CURRENT['formation_start']:X} -> 0x{NEW['formation_start']:X}")
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
    backup = BLAZE_ALL.with_suffix('.ALL.backup')
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
    print("RESULT:")
    print("  Cavern F1 A1: 3 -> 5 monster slots")
    print("  New slots: NewSlot1, NewSlot2 (placeholders)")
    print()
    print("NEXT STEPS:")
    print("  1. Test in-game (load Cavern F1)")
    print("  2. If works: use replace_monster_slot.py to copy real monsters")
    print("  3. Update formations to use new slots")

    return 0


if __name__ == '__main__':
    exit(main())
