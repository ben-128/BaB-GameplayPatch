#!/usr/bin/env python3
"""
SAFE Monster Slot Addition - Réorganisation Interne

Principe:
- La zone de Cavern F1 A1 va de 0xF7A900 à 0xF7B37C (2684 bytes)
- Tout ce qui est APRÈS 0xF7B37C n'est PAS touché!
- On réorganise UNIQUEMENT À L'INTÉRIEUR de cette zone

Structure actuelle:
  [Animation+Stats: 412b][Script: 1376b][Formations: 896b] = 2684b total

Après ajout de 2 slots (240 bytes):
  [Animation+Stats: 652b][Script: 1136b][Formations: 896b] = 2684b total
                  +240b            -240b            (same)    (MÊME TOTAL)

Le reste du fichier (après 0xF7B37C) reste à la MÊME POSITION!

Usage:
  python add_slots_safe.py --area cavern_f1_a1 --add-slots 2 --dry-run
  python add_slots_safe.py --area cavern_f1_a1 --add-slots 2 --apply
"""

import struct
import json
import argparse
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern F1 A1 boundaries (HARD BOUNDARY at 0xF7B37C)
CAVERN_F1_A1 = {
    'name': 'Cavern of Death - Floor 1 Area 1',
    'zone_start': 0xF7A900,     # Animation header
    'zone_end': 0xF7B37C,       # HARD BOUNDARY - next area starts here!
    'zone_size': 2684,
    'current_slots': 3,
    'anim_header': 0xF7A900,
    'stats_start': 0xF7A97C,
    'script_start': 0xF7AA9C,
    'formation_start': 0xF7AFFC,
    'formation_size': 896,
}


def analyze_script_usage(blaze_data, script_start, script_size):
    """
    Analyze how much of the script area is actually used.
    Script areas typically have a lot of padding/free space.
    """
    script_data = blaze_data[script_start:script_start + script_size]

    # Find last non-zero byte to estimate usage
    last_nonzero = 0
    for i in range(len(script_data) - 1, -1, -1):
        if script_data[i] != 0:
            last_nonzero = i
            break

    used_bytes = last_nonzero + 1
    free_bytes = script_size - used_bytes

    return {
        'total_size': script_size,
        'used_bytes': used_bytes,
        'free_bytes': free_bytes,
        'usage_percent': (used_bytes / script_size * 100) if script_size > 0 else 0,
    }


def create_reorganized_zone(blaze_data, config, num_new_slots):
    """
    Reorganize the zone to add new monster slots.

    Steps:
    1. Extract all current data sections
    2. Create new monster slot data (placeholders)
    3. Rebuild zone with new layout
    4. Return reorganized zone bytes
    """

    zone_start = config['zone_start']
    zone_end = config['zone_end']
    zone_size = config['zone_size']
    current_slots = config['current_slots']

    bytes_per_slot = 120
    expansion_bytes = num_new_slots * bytes_per_slot

    # Extract current sections
    formation_start = config['formation_start']
    formation_size = config['formation_size']
    formation_data = blaze_data[formation_start:formation_start + formation_size]

    script_start = config['script_start']
    script_size = formation_start - script_start
    script_data = blaze_data[script_start:script_start + script_size]

    stats_start = config['stats_start']
    stats_size = script_start - stats_start
    monster_data_start = config['anim_header']
    monster_data_size = stats_start + stats_size - monster_data_start
    monster_data = blaze_data[monster_data_start:monster_data_start + monster_data_size]

    print(f"\n[EXTRACTION]")
    print(f"  Monster data: {monster_data_size} bytes (includes anim+stats for {current_slots} slots)")
    print(f"  Script data:  {script_size} bytes")
    print(f"  Formation data: {formation_size} bytes")
    print(f"  Total: {monster_data_size + script_size + formation_size} bytes")
    print()

    # Analyze script usage
    script_analysis = analyze_script_usage(blaze_data, script_start, script_size)
    print(f"[SCRIPT ANALYSIS]")
    print(f"  Script allocated: {script_analysis['total_size']} bytes")
    print(f"  Script used:      {script_analysis['used_bytes']} bytes ({script_analysis['usage_percent']:.1f}%)")
    print(f"  Script free:      {script_analysis['free_bytes']} bytes")
    print()

    # Check if we can shrink script area
    new_script_size = script_size - expansion_bytes

    if script_analysis['used_bytes'] > new_script_size:
        print(f"[ERROR] Cannot shrink script area by {expansion_bytes} bytes!")
        print(f"        Script uses {script_analysis['used_bytes']} bytes")
        print(f"        Would leave only {new_script_size} bytes")
        return None

    print(f"[OK] Script can be shrunk from {script_size} to {new_script_size} bytes")
    print(f"    (still has {new_script_size - script_analysis['used_bytes']} bytes free)")
    print()

    # Create placeholder data for new slots
    new_slot_data = bytearray()
    for i in range(num_new_slots):
        slot_index = current_slots + i

        # Animation table (8 bytes) - simple pattern
        anim_table = bytes([0x04, 0x04, 0x05, 0x05, 0x06, 0x06, 0x07, 0x07])

        # Animation record (8 bytes)
        anim_record = struct.pack('<I', 0x0C) + struct.pack('<I', 0x300)

        # Assignments L/R (8 bytes)
        assignments = bytes([slot_index, 0x00, 0x00, 0x00, slot_index, 0x00, 0x00, 0x40])

        # Stats (96 bytes)
        name = f"NewMonster{i+1}".encode('ascii')[:16].ljust(16, b'\x00')
        stats_values = [0, 1, 50] + [0]*37  # Basic stats: exp=0, level=1, hp=50
        stats_bytes = name + b''.join(struct.pack('<H', v) for v in stats_values)

        new_slot_data += anim_table + anim_record + assignments + stats_bytes

    print(f"[NEW SLOTS]")
    print(f"  Created {num_new_slots} placeholder slots ({len(new_slot_data)} bytes)")
    print()

    # Build new zone layout
    new_zone = bytearray(zone_size)

    offset = 0

    # 1. Original monster data
    new_zone[offset:offset + len(monster_data)] = monster_data
    offset += len(monster_data)

    # 2. New slot data
    new_zone[offset:offset + len(new_slot_data)] = new_slot_data
    offset += len(new_slot_data)

    # 3. Script data (shrunk)
    new_zone[offset:offset + new_script_size] = script_data[:new_script_size]
    offset += new_script_size

    # 4. Formation data (unchanged)
    new_zone[offset:offset + formation_size] = formation_data
    offset += formation_size

    print(f"[NEW LAYOUT]")
    print(f"  Monster data: {len(monster_data) + len(new_slot_data)} bytes ({current_slots + num_new_slots} slots)")
    print(f"  Script data:  {new_script_size} bytes")
    print(f"  Formation data: {formation_size} bytes")
    print(f"  Total: {offset} bytes (zone size: {zone_size} bytes)")
    print()

    if offset != zone_size:
        print(f"[WARNING] Layout size mismatch! {offset} != {zone_size}")

    return new_zone


def main():
    parser = argparse.ArgumentParser(
        description='Add monster slots via safe internal reorganization'
    )
    parser.add_argument('--area', default='cavern_f1_a1', help='Area to modify')
    parser.add_argument('--add-slots', type=int, required=True, help='Number of slots to add')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--apply', action='store_true')

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Use --dry-run or --apply")

    print("="*70)
    print("SAFE MONSTER SLOT ADDITION - Internal Reorganization")
    print("="*70)
    print()

    config = CAVERN_F1_A1

    print(f"[AREA] {config['name']}")
    print(f"       Zone: 0x{config['zone_start']:X} - 0x{config['zone_end']:X} ({config['zone_size']} bytes)")
    print(f"       Current slots: {config['current_slots']}")
    print(f"       Target slots:  {config['current_slots'] + args.add_slots}")
    print()
    print(f"[SAFETY] Everything after 0x{config['zone_end']:X} stays at SAME position!")
    print()

    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        return 1

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = bytearray(f.read())

    # Create reorganized zone
    new_zone = create_reorganized_zone(blaze_data, config, args.add_slots)

    if new_zone is None:
        return 1

    if args.dry_run:
        print("[DRY RUN] Not applying changes")
        print()
        print("Would reorganize zone WITHOUT affecting rest of file!")
        return 0

    # Apply changes
    print("[APPLYING]")

    # Backup
    backup_path = BLAZE_ALL.with_suffix('.ALL.backup')
    shutil.copy2(BLAZE_ALL, backup_path)
    print(f"  Created backup: {backup_path.name}")

    # Replace zone in binary
    zone_start = config['zone_start']
    zone_end = config['zone_end']

    blaze_data[zone_start:zone_end] = new_zone

    # Save
    with open(BLAZE_ALL, 'wb') as f:
        f.write(blaze_data)

    print(f"  Saved modified BLAZE.ALL")
    print()

    print("="*70)
    print("[SUCCESS] Monster slots added via internal reorganization!")
    print("="*70)
    print()
    print("IMPORTANT:")
    print("1. The REST OF THE FILE is UNCHANGED (same offsets)")
    print("2. Only the internal layout of THIS zone was reorganized")
    print("3. Test in-game to verify")
    print()
    print(f"Added {args.add_slots} new monster slots (NewMonster1, NewMonster2, ...)")

    return 0


if __name__ == '__main__':
    exit(main())
