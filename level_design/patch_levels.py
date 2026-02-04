#!/usr/bin/env python3
"""
Patch BLAZE.ALL with modified spawn and chest data from level JSON files
"""

import json
import os
import struct
import shutil
from datetime import datetime

def load_blaze_all():
    """Load BLAZE.ALL file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir = os.path.join(script_dir, '..', 'work')
    blaze_path = os.path.join(work_dir, 'BLAZE.ALL')

    if not os.path.exists(blaze_path):
        raise FileNotFoundError(f"BLAZE.ALL not found at {blaze_path}")

    with open(blaze_path, 'rb') as f:
        return bytearray(f.read())

def save_blaze_all(data):
    """Save modified BLAZE.ALL"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    work_dir = os.path.join(script_dir, '..', 'work')
    blaze_path = os.path.join(work_dir, 'BLAZE.ALL')

    # Create backup
    backup_path = blaze_path + '.backup'
    if not os.path.exists(backup_path):
        shutil.copy2(blaze_path, backup_path)
        print(f"[BACKUP] Created: {backup_path}")

    # Save modified file
    with open(blaze_path, 'wb') as f:
        f.write(data)

    print(f"[OK] Saved: {blaze_path}")

def load_level_files(folder_name):
    """Load all JSON files from a levels folder"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, folder_name)

    if not os.path.exists(folder_path):
        return []

    level_files = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                level_files.append({
                    'filename': filename,
                    'data': data
                })

    return level_files

def patch_chest(data, chest, index):
    """Patch a single chest in BLAZE.ALL"""
    offset = int(chest['offset'], 16)

    # Chest structure (14 bytes):
    # Offset+0:  int16 x, y, z (6 bytes)
    # Offset+6:  uint16 item_id (2 bytes)
    # Offset+8:  uint16 quantity (2 bytes)
    # Offset+10: uint16 flags (2 bytes)
    # Offset+12: uint16 padding (2 bytes)

    try:
        # Pack position (x, y, z)
        struct.pack_into('<hhh', data, offset,
                        chest['position']['x'],
                        chest['position']['y'],
                        chest['position']['z'])

        # Pack item_id
        struct.pack_into('<H', data, offset + 6, chest['item_id'])

        # Pack quantity
        struct.pack_into('<H', data, offset + 8, chest['quantity'])

        return True

    except Exception as e:
        print(f"[ERROR] Failed to patch chest {index} at {chest['offset']}: {e}")
        return False

def patch_spawn(data, spawn, index):
    """Patch a single spawn in BLAZE.ALL"""
    offset = int(spawn['offset'], 16)

    # Spawn structure (16 bytes):
    # Offset+0:  int16 x, y, z (6 bytes)
    # Offset+6:  uint16 monster_id (2 bytes)
    # Offset+8:  uint8 spawn_chance (1 byte)
    # Offset+9:  uint8 spawn_count (1 byte)
    # Offset+10: uint16 zone_id (2 bytes)
    # Offset+12: uint32 flags (4 bytes)

    try:
        # Pack position (x, y, z)
        struct.pack_into('<hhh', data, offset,
                        spawn['position']['x'],
                        spawn['position']['y'],
                        spawn['position']['z'])

        # Pack monster_id
        struct.pack_into('<H', data, offset + 6, spawn['monster_id'])

        # Pack spawn_chance and spawn_count
        struct.pack_into('<BB', data, offset + 8,
                        spawn['spawn_chance'],
                        spawn['spawn_count'])

        # Pack zone_id
        struct.pack_into('<H', data, offset + 10, spawn['zone_id'])

        return True

    except Exception as e:
        print(f"[ERROR] Failed to patch spawn {index} at {spawn['offset']}: {e}")
        return False

def apply_chest_patches(data, level_files):
    """Apply all chest patches"""
    total_patched = 0
    total_errors = 0

    for level_file in level_files:
        level_name = level_file['data'].get('level_name', 'Unknown')
        chests = level_file['data'].get('chests', [])

        if len(chests) == 0:
            continue

        print(f"\n[CHESTS] Patching {level_name}...")

        for i, chest in enumerate(chests):
            if patch_chest(data, chest, i):
                total_patched += 1
            else:
                total_errors += 1

        print(f"  [OK] Patched {len(chests)} chests")

    return total_patched, total_errors

def apply_spawn_patches(data, level_files):
    """Apply all spawn patches"""
    total_patched = 0
    total_errors = 0

    for level_file in level_files:
        level_name = level_file['data'].get('level_name', 'Unknown')
        spawns = level_file['data'].get('spawns', [])

        if len(spawns) == 0:
            continue

        print(f"\n[SPAWNS] Patching {level_name}...")

        for i, spawn in enumerate(spawns):
            if patch_spawn(data, spawn, i):
                total_patched += 1
            else:
                total_errors += 1

        print(f"  [OK] Patched {len(spawns)} spawns")

    return total_patched, total_errors

def main():
    print("=" * 70)
    print("Level Data Patcher")
    print("=" * 70)
    print()

    # Load BLAZE.ALL
    print("[1/5] Loading BLAZE.ALL...")
    try:
        data = load_blaze_all()
        print(f"[OK] Loaded BLAZE.ALL ({len(data):,} bytes)")
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    print()

    # Load level files
    print("[2/5] Loading chest level files...")
    chest_files = load_level_files('levels_chests')
    print(f"[OK] Loaded {len(chest_files)} chest files")

    print("[3/5] Loading spawn level files...")
    spawn_files = load_level_files('levels_spawns')
    print(f"[OK] Loaded {len(spawn_files)} spawn files")
    print()

    # Apply patches
    print("[4/5] Applying patches...")
    chest_patched, chest_errors = apply_chest_patches(data, chest_files)
    spawn_patched, spawn_errors = apply_spawn_patches(data, spawn_files)
    print()

    # Save
    print("[5/5] Saving BLAZE.ALL...")
    save_blaze_all(data)
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Chests patched:  {chest_patched}")
    print(f"Spawns patched:  {spawn_patched}")
    print(f"Total patched:   {chest_patched + spawn_patched}")
    print(f"Errors:          {chest_errors + spawn_errors}")
    print()
    print("Next steps:")
    print("  1. cd ..")
    print("  2. py -3 patch_blaze_all.py  (reinject into BIN)")
    print("  3. Test in emulator")
    print()

if __name__ == '__main__':
    main()
