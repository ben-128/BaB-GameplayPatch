#!/usr/bin/env python3
"""
Generate door modification presets from detected door structures
"""

import json
import csv
import os

def load_door_positions(csv_path):
    """Load door positions from CSV"""
    doors = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip padding entries at (0,0,0)
            x, y, z = int(row['x']), int(row['y']), int(row['z'])
            if x == 0 and y == 0 and z == 0:
                continue

            doors.append({
                'offset': row['offset'],
                'x': x,
                'y': y,
                'z': z,
                'type': int(row['type']),
                'type_desc': row['type_desc'],
                'key_id': int(row['key_id']),
                'dest_id': int(row['dest_id'])
            })

    return doors

def generate_unlock_all_preset(doors):
    """Generate preset to unlock all doors"""
    modifications = []

    for i, door in enumerate(doors):
        mod = {
            "name": f"Unlock door {i+1} at ({door['x']},{door['y']},{door['z']})",
            "offset": door['offset'],
            "current_type": door['type'],
            "new_type": 0,  # UNLOCKED
            "new_key_id": 0,  # No key required
            "new_dest_id": None,  # Keep destination
            "comment": f"Was: {door['type_desc']}",
            "enabled": True
        }
        modifications.append(mod)

    preset = {
        "name": "Unlock All Doors",
        "description": "Removes all locks from doors (makes them UNLOCKED)",
        "modifications": modifications
    }

    return preset

def generate_remove_keys_preset(doors):
    """Generate preset to remove key requirements"""
    modifications = []

    for i, door in enumerate(doors):
        # Only modify doors that have keys
        if door['key_id'] > 0:
            mod = {
                "name": f"Remove key from door {i+1}",
                "offset": door['offset'],
                "current_type": door['type'],
                "new_type": None,  # Keep type
                "new_key_id": 0,  # Remove key
                "new_dest_id": None,  # Keep destination
                "comment": f"Was: {door['type_desc']}, key_id={door['key_id']}",
                "enabled": True
            }
            modifications.append(mod)

    preset = {
        "name": "Remove All Key Requirements",
        "description": "Keeps door types but removes key requirements",
        "modifications": modifications
    }

    return preset

def generate_lock_all_preset(doors):
    """Generate preset to lock all doors (for testing)"""
    modifications = []

    for i, door in enumerate(doors):
        mod = {
            "name": f"Lock door {i+1} at ({door['x']},{door['y']},{door['z']})",
            "offset": door['offset'],
            "current_type": door['type'],
            "new_type": 1,  # KEY_LOCKED
            "new_key_id": 1,  # Require key ID 1
            "new_dest_id": None,
            "comment": f"Test: Lock with key requirement",
            "enabled": True
        }
        modifications.append(mod)

    preset = {
        "name": "Lock All Doors (Test)",
        "description": "Locks all doors with key requirement (for testing)",
        "modifications": modifications
    }

    return preset

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'door_positions.csv')
    presets_dir = os.path.join(script_dir, 'door_presets')

    print("Door Preset Generator")
    print("=" * 50)
    print()

    # Load doors
    print("Loading door positions from CSV...")
    doors = load_door_positions(csv_path)
    print(f"[OK] Found {len(doors)} valid doors (non-zero coordinates)")
    print()

    if len(doors) == 0:
        print("[WARNING] No valid doors found!")
        print("All doors are at (0,0,0) - likely padding data")
        print()
        print("Creating example presets with all detected structures...")
        # Load ALL doors including (0,0,0)
        doors = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                doors.append({
                    'offset': row['offset'],
                    'x': int(row['x']),
                    'y': int(row['y']),
                    'z': int(row['z']),
                    'type': int(row['type']),
                    'type_desc': row['type_desc'],
                    'key_id': int(row['key_id']),
                    'dest_id': int(row['dest_id'])
                })
        print(f"Using {len(doors)} structures as examples")
        print()

    # Generate presets
    print("Generating presets...")

    # 1. Unlock all
    unlock_preset = generate_unlock_all_preset(doors[:10])  # First 10 for example
    unlock_path = os.path.join(presets_dir, 'unlock_all_doors.json')
    with open(unlock_path, 'w') as f:
        json.dump(unlock_preset, f, indent=2)
    print(f"[OK] Generated: unlock_all_doors.json ({len(unlock_preset['modifications'])} mods)")

    # 2. Remove keys
    remove_keys_preset = generate_remove_keys_preset(doors[:10])
    remove_keys_path = os.path.join(presets_dir, 'remove_key_requirements.json')
    with open(remove_keys_path, 'w') as f:
        json.dump(remove_keys_preset, f, indent=2)
    print(f"[OK] Generated: remove_key_requirements.json ({len(remove_keys_preset['modifications'])} mods)")

    # 3. Lock all (test preset)
    lock_preset = generate_lock_all_preset(doors[:10])
    lock_path = os.path.join(presets_dir, 'lock_all_doors_test.json')
    with open(lock_path, 'w') as f:
        json.dump(lock_preset, f, indent=2)
    print(f"[OK] Generated: lock_all_doors_test.json ({len(lock_preset['modifications'])} mods)")

    print()
    print("=" * 50)
    print("Presets generated successfully!")
    print()
    print("Note: These are example/template presets.")
    print("You may need to:")
    print("  1. Find real locked doors using Unity visualization")
    print("  2. Identify their offsets in door_positions.csv")
    print("  3. Edit presets or door_modifications.json manually")

if __name__ == '__main__':
    main()
