#!/usr/bin/env python3
"""
TEST: Change Shaman's slot_types (byte[0:4] prefix) to modify spells.

This script tests if slot_types values control monster spell lists.

Test cases:
1. Shaman with Goblin prefix (00000000) -> should change spells
2. Shaman with Bat prefix (00000a00) -> should change spells differently
3. Shaman with vanilla prefix (02000000) -> should keep Sleep

How to use:
1. Run this script to modify BLAZE.ALL
2. Inject into BIN (steps 10-11 of build)
3. Test in-game at Cavern F1 A1
4. Compare spell lists for each test case
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern F1 A1 Formation 0 starts at 0xF7AFFC
# Records in formation:
#   Record 0-4: Goblins (slot 0)
#   Record 5-6: Shamans (slot 1)
# Each record is 32 bytes, prefix is at byte[0:4]

# Shaman records offsets
SHAMAN_RECORDS = [
    0xF7B09C,  # Shaman 1 (Record 5)
    0xF7B0BC,  # Shaman 2 (Record 6)
]

# slot_types from floor_1_area_1.json
SLOT_TYPES = {
    "goblin": bytes.fromhex("00000000"),
    "shaman": bytes.fromhex("02000000"),
    "bat": bytes.fromhex("00000a00"),
}


def show_current_prefixes(data):
    """Show current prefix values for Shaman records."""
    print("Current Shaman prefixes:")
    for i, offset in enumerate(SHAMAN_RECORDS, 1):
        prefix = data[offset:offset+4]
        prefix_hex = prefix.hex()
        slot_type = next((name for name, val in SLOT_TYPES.items()
                         if val == prefix), "unknown")
        print(f"  Shaman {i} @ {hex(offset)}: {prefix_hex} ({slot_type})")
    print()


def patch_prefixes(data, new_prefix_name):
    """Patch Shaman prefixes with specified slot_type."""
    if new_prefix_name not in SLOT_TYPES:
        print(f"ERROR: Unknown slot_type '{new_prefix_name}'")
        return False

    new_prefix = SLOT_TYPES[new_prefix_name]

    print(f"Patching Shaman prefixes to {new_prefix_name} ({new_prefix.hex()}):")
    for i, offset in enumerate(SHAMAN_RECORDS, 1):
        old_prefix = data[offset:offset+4]
        data[offset:offset+4] = new_prefix
        print(f"  Shaman {i}: {old_prefix.hex()} -> {new_prefix.hex()}")
    print()
    return True


def main():
    print("=" * 70)
    print("  TEST: slot_types (byte[0:4] prefix) control monster spells")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} does not exist!")
        print("Run build_gameplay_patch.bat first")
        return 1

    # Read BLAZE.ALL
    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())
        print(f"BLAZE.ALL: {len(data):,} bytes")
        print()

        # Show current state
        show_current_prefixes(data)

        # Show test options
        print("Test options:")
        print("  1. Goblin prefix (00000000) - test if Shaman gets Goblin-like spells")
        print("  2. Bat prefix (00000a00) - test if Shaman gets Bat-like spells")
        print("  3. Vanilla Shaman prefix (02000000) - restore vanilla (Sleep)")
        print()

        choice = input("Select test (1/2/3) or 'q' to quit: ").strip()

        if choice == 'q':
            print("Cancelled.")
            return 0

        prefix_map = {
            '1': 'goblin',
            '2': 'bat',
            '3': 'shaman',
        }

        if choice not in prefix_map:
            print("Invalid choice.")
            return 1

        prefix_name = prefix_map[choice]

        # Apply patch
        if not patch_prefixes(data, prefix_name):
            return 1

        # Write back
        f.seek(0)
        f.write(data)
        print("BLAZE.ALL modified!")
        print()

    print("=" * 70)
    print("  TEST READY")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Run build_gameplay_patch.bat (steps 10-11 only)")
    print("  2. Test in-game: Cavern Floor 1 Area 1")
    print("  3. Check Shaman spell list in combat")
    print()
    print("Expected results:")
    print("  - Goblin prefix: Shaman should have modified spell list")
    print("  - Bat prefix: Shaman should have different spell list")
    print("  - Shaman prefix: Shaman should cast Sleep (vanilla)")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
