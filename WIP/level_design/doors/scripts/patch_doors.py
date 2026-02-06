"""
patch_doors.py
Modify door states and reinject into BLAZE.ALL

Usage: py -3 patch_doors.py
"""

from pathlib import Path
import struct
import json

SCRIPT_DIR = Path(__file__).parent  # doors/scripts/
LEVEL_DESIGN_DIR = SCRIPT_DIR.parent.parent  # level_design/
WIP_DIR = LEVEL_DESIGN_DIR.parent.parent  # WIP/
BLAZE_ALL = WIP_DIR / "work" / "BLAZE.ALL"

# Door type constants
DOOR_TYPES = {
    'UNLOCKED': 0,
    'KEY_LOCKED': 1,
    'MAGIC_LOCKED': 2,
    'DEMON_ENGRAVED': 3,
    'GHOST_ENGRAVED': 4,
    'EVENT_LOCKED': 5,
    'BOSS_DOOR': 6,
    'ONE_WAY': 7
}

def load_door_config():
    """Load door modification configuration"""
    config_file = SCRIPT_DIR.parent / "data" / "door_modifications.json"

    if not config_file.exists():
        print(f"Configuration file not found: {config_file}")
        print("Creating default configuration...")
        create_default_config(config_file)
        return None

    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_default_config(config_file):
    """Create default door modification configuration"""
    default_config = {
        "_comment": "Door Modification Configuration",
        "_instructions": [
            "Modify the 'modifications' array to change door states",
            "offset: Hex offset from door_analysis.json",
            "new_type: Door type (0=Unlocked, 1=KeyLocked, 2=MagicLocked, etc.)",
            "new_key_id: Key ID required (0 = no key)",
            "new_dest_id: Destination level ID",
            "Set enabled: true to apply the modification"
        ],
        "_door_types": {
            "UNLOCKED": 0,
            "KEY_LOCKED": 1,
            "MAGIC_LOCKED": 2,
            "DEMON_ENGRAVED": 3,
            "GHOST_ENGRAVED": 4,
            "EVENT_LOCKED": 5,
            "BOSS_DOOR": 6,
            "ONE_WAY": 7
        },
        "modifications": [
            {
                "name": "Example: Unlock first door",
                "offset": "0x100000",
                "current_type": 1,
                "new_type": 0,
                "new_key_id": 0,
                "new_dest_id": None,
                "comment": "Change from Key Locked to Unlocked",
                "enabled": False
            },
            {
                "name": "Example: Remove key requirement",
                "offset": "0x100010",
                "current_type": 1,
                "new_type": None,
                "new_key_id": 0,
                "new_dest_id": None,
                "comment": "Keep type, just remove key requirement",
                "enabled": False
            },
            {
                "name": "Example: Change destination",
                "offset": "0x100020",
                "current_type": None,
                "new_type": None,
                "new_key_id": None,
                "new_dest_id": 10,
                "comment": "Redirect door to level 10",
                "enabled": False
            }
        ]
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2)

    print(f"Default configuration created: {config_file}")
    print("\nEdit this file to configure door modifications, then run this script again.")

def apply_door_modifications(data, config):
    """Apply door modifications to BLAZE.ALL data"""
    modifications = config.get('modifications', [])
    applied = []
    skipped = []

    for mod in modifications:
        if not mod.get('enabled', False):
            skipped.append(mod['name'])
            continue

        offset_str = mod['offset']
        offset = int(offset_str, 16) if offset_str.startswith('0x') else int(offset_str)

        if offset < 0 or offset >= len(data) - 16:
            print(f"  [ERROR] Invalid offset: {offset_str}")
            continue

        # Read current door structure
        current = {
            'x': struct.unpack_from('<h', data, offset)[0],
            'y': struct.unpack_from('<h', data, offset+2)[0],
            'z': struct.unpack_from('<h', data, offset+4)[0],
            'type': struct.unpack_from('<H', data, offset+6)[0],
            'key_id': struct.unpack_from('<H', data, offset+8)[0],
            'dest_id': struct.unpack_from('<H', data, offset+10)[0],
            'flags': struct.unpack_from('<H', data, offset+12)[0]
        }

        print(f"\n  Modifying: {mod['name']}")
        print(f"    Offset: {offset_str}")
        print(f"    Current: Type={current['type']}, Key={current['key_id']}, Dest={current['dest_id']}")

        # Apply modifications
        new_type = mod.get('new_type')
        new_key_id = mod.get('new_key_id')
        new_dest_id = mod.get('new_dest_id')

        if new_type is not None:
            struct.pack_into('<H', data, offset+6, new_type)
            print(f"    -> Type changed to {new_type}")

        if new_key_id is not None:
            struct.pack_into('<H', data, offset+8, new_key_id)
            print(f"    -> Key ID changed to {new_key_id}")

        if new_dest_id is not None:
            struct.pack_into('<H', data, offset+10, new_dest_id)
            print(f"    -> Destination changed to {new_dest_id}")

        applied.append(mod['name'])

    return applied, skipped

def backup_blaze_all():
    """Create backup of BLAZE.ALL"""
    backup_file = BLAZE_ALL.parent / "BLAZE.ALL.backup"

    if not backup_file.exists():
        print(f"\nCreating backup: {backup_file.name}")
        import shutil
        shutil.copy2(BLAZE_ALL, backup_file)
        print("  Backup created!")
    else:
        print(f"\nBackup already exists: {backup_file.name}")

    return backup_file

def create_preset_configs():
    """Create preset modification examples"""
    presets_dir = SCRIPT_DIR / "level_design" / "door_presets"
    presets_dir.mkdir(exist_ok=True)

    # Preset 1: Unlock all doors
    unlock_all = {
        "name": "Unlock All Doors",
        "description": "Removes all locks from doors (makes them UNLOCKED)",
        "modifications": []
    }

    # Load door analysis to get actual offsets
    door_file = SCRIPT_DIR / "level_design" / "door_analysis.json"
    if door_file.exists():
        with open(door_file, 'r', encoding='utf-8') as f:
            door_data = json.load(f)

        structures = door_data.get('door_structures', [])

        # Add modifications for locked doors
        for i, door in enumerate(structures[:20]):  # First 20 doors
            if door.get('type', 0) > 0:  # If locked
                unlock_all['modifications'].append({
                    "name": f"Unlock door {i+1}",
                    "offset": door['offset'],
                    "current_type": door['type'],
                    "new_type": 0,
                    "new_key_id": 0,
                    "new_dest_id": None,
                    "enabled": True
                })

    preset_file = presets_dir / "unlock_all_doors.json"
    with open(preset_file, 'w', encoding='utf-8') as f:
        json.dump(unlock_all, f, indent=2)

    print(f"  Created preset: {preset_file.name}")

    # Preset 2: Remove key requirements
    no_keys = {
        "name": "Remove All Key Requirements",
        "description": "Keeps door types but removes key requirements",
        "modifications": []
    }

    if door_file.exists():
        for i, door in enumerate(structures[:20]):
            if door.get('key_id', 0) > 0:  # If requires key
                no_keys['modifications'].append({
                    "name": f"Remove key from door {i+1}",
                    "offset": door['offset'],
                    "current_type": door['type'],
                    "new_type": None,
                    "new_key_id": 0,
                    "new_dest_id": None,
                    "enabled": True
                })

    preset_file = presets_dir / "remove_key_requirements.json"
    with open(preset_file, 'w', encoding='utf-8') as f:
        json.dump(no_keys, f, indent=2)

    print(f"  Created preset: {preset_file.name}")

    return presets_dir

def main():
    print("=" * 70)
    print("  DOOR PATCHER")
    print("=" * 70)
    print()

    # Check if BLAZE.ALL exists
    if not BLAZE_ALL.exists():
        print(f"ERROR: BLAZE.ALL not found at {BLAZE_ALL}")
        return

    print(f"Target: {BLAZE_ALL}")
    print(f"Size: {BLAZE_ALL.stat().st_size:,} bytes")

    # Load configuration
    print("\n[1] LOADING CONFIGURATION")
    print("-" * 70)
    config = load_door_config()

    if config is None:
        print("\nConfiguration file created. Please edit it and run again.")
        print("\nPreset configurations available in door_presets/ folder")
        print("\n[2] CREATING PRESET CONFIGURATIONS")
        print("-" * 70)
        presets_dir = create_preset_configs()
        print(f"\nPresets created in: {presets_dir}")
        print("\nTo use a preset:")
        print("  1. Copy a preset file to door_modifications.json")
        print("  2. Run this script again")
        return

    # Create backup
    print("\n[2] CREATING BACKUP")
    print("-" * 70)
    backup_file = backup_blaze_all()

    # Load BLAZE.ALL
    print("\n[3] LOADING BLAZE.ALL")
    print("-" * 70)
    data = bytearray(BLAZE_ALL.read_bytes())
    print(f"Loaded {len(data):,} bytes")

    # Apply modifications
    print("\n[4] APPLYING MODIFICATIONS")
    print("-" * 70)
    applied, skipped = apply_door_modifications(data, config)

    if not applied:
        print("\n  No modifications applied (all disabled or none configured)")
        print(f"  Skipped: {len(skipped)} modifications")
        return

    # Save modified BLAZE.ALL
    print("\n[5] SAVING MODIFIED BLAZE.ALL")
    print("-" * 70)
    BLAZE_ALL.write_bytes(data)
    print(f"Saved to: {BLAZE_ALL}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Modifications applied: {len(applied)}")
    for name in applied:
        print(f"  - {name}")

    if skipped:
        print(f"\nModifications skipped: {len(skipped)}")

    print(f"\nBackup location: {backup_file}")
    print("\nNext steps:")
    print("  1. Run: py -3 ../patch_blaze_all.py")
    print("     (Inject BLAZE.ALL into the BIN)")
    print("  2. Test in-game with emulator")
    print("  3. If issues, restore backup:")
    print(f"     copy {backup_file.name} BLAZE.ALL")
    print("=" * 70)

if __name__ == '__main__':
    main()
