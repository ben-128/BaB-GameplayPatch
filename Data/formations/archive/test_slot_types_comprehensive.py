#!/usr/bin/env python3
"""
COMPREHENSIVE TEST: Test different slot_types values on multiple monsters/formations.

Test configuration for Cavern F1 A1:
- Formation 0: Shamans with 00000000 (Goblin base set)
- Formation 1: Shamans with 03000000 (Tower Shaman variant)
- Formation 2: Goblins with 02000000 (give Goblins Shaman spells?)

All formations are 3-monster encounters for consistency.
byte[8] stays correct for each entity type.
Only byte[0:4] prefix is modified.
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern F1 A1 Formation area starts at 0xF7AFFC
FORMATION_AREA_START = 0xF7AFFC
RECORD_SIZE = 32
SUFFIX_SIZE = 4

# slot_types values to test
SLOT_TYPES = {
    "goblin": bytes.fromhex("00000000"),    # Base set
    "shaman": bytes.fromhex("02000000"),    # Shaman Sleep
    "tower_shaman": bytes.fromhex("03000000"),  # Tower variant
    "bat": bytes.fromhex("00000a00"),       # Flying + spells
}


def build_formation(slot_list, prefix_override=None):
    """Build a formation with specified slots and optional prefix override.

    Returns (formation_bytes, byte_size)
    """
    area_id = bytes.fromhex("dc01")  # Cavern F1 A1
    binary = bytearray()

    for idx, slot in enumerate(slot_list):
        is_first = (idx == 0)

        # Build record
        rec = bytearray(RECORD_SIZE)

        # byte[0:4] = prefix (override if specified, else default)
        if prefix_override is not None:
            rec[0:4] = prefix_override
        elif is_first:
            rec[0:4] = bytes(4)  # 00000000 for first record
        else:
            # Use slot_types of previous slot
            prev_slot = slot_list[idx - 1]
            if prev_slot == 0:
                rec[0:4] = SLOT_TYPES["goblin"]
            elif prev_slot == 1:
                rec[0:4] = SLOT_TYPES["shaman"]
            elif prev_slot == 2:
                rec[0:4] = SLOT_TYPES["bat"]

        # byte[4:8] = FFFFFFFF for first, 00000000 for rest
        if is_first:
            rec[4:8] = b'\xff\xff\xff\xff'

        # byte[8] = slot_index (CRITICAL - controls entity type)
        rec[8] = slot

        # byte[9] = 0xFF
        rec[9] = 0xFF

        # byte[24:26] = area_id
        rec[24:26] = area_id

        # byte[26:32] = terminator
        rec[26:32] = b'\xff\xff\xff\xff\xff\xff'

        binary.extend(rec)

    # Suffix = slot_types of last monster
    last_slot = slot_list[-1]
    if prefix_override is not None:
        suffix = prefix_override
    elif last_slot == 0:
        suffix = SLOT_TYPES["goblin"]
    elif last_slot == 1:
        suffix = SLOT_TYPES["shaman"]
    elif last_slot == 2:
        suffix = SLOT_TYPES["bat"]

    binary.extend(suffix)

    return bytes(binary), len(binary)


def main():
    print("=" * 70)
    print("  COMPREHENSIVE slot_types TEST")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} does not exist!")
        return 1

    # Read BLAZE.ALL
    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())
        print(f"BLAZE.ALL: {len(data):,} bytes")
        print()

        # Test configurations
        print("TEST CONFIGURATIONS:")
        print("-" * 70)
        print()
        print("Formation 0 (offset 0x00):")
        print("  3x Shaman (slot 1) with prefix 00000000 (Goblin base set)")
        print("  Expected: Shamans with Goblin-like spells?")
        print()
        print("Formation 1 (offset 0x74):")
        print("  3x Shaman (slot 1) with prefix 03000000 (Tower variant)")
        print("  Expected: Shamans with different spell set")
        print()
        print("Formation 2 (offset 0xE8):")
        print("  3x Goblin (slot 0) with prefix 02000000 (Shaman set)")
        print("  Expected: Goblins with Shaman spells? (Sleep casting Goblins!)")
        print()

        response = input("Apply these test patches? (o/n): ").lower()
        if response != 'o':
            print("Cancelled.")
            return 0

        print()
        print("Applying patches...")
        print()

        # Build formations
        form0_data, form0_size = build_formation(
            [1, 1, 1],  # 3x Shaman
            prefix_override=SLOT_TYPES["goblin"]  # Force Goblin prefix on ALL records
        )

        form1_data, form1_size = build_formation(
            [1, 1, 1],  # 3x Shaman
            prefix_override=SLOT_TYPES["tower_shaman"]  # Force Tower Shaman prefix
        )

        form2_data, form2_size = build_formation(
            [0, 0, 0],  # 3x Goblin
            prefix_override=SLOT_TYPES["shaman"]  # Force Shaman prefix on Goblins!
        )

        # Write formations
        offset = FORMATION_AREA_START

        print(f"Formation 0 @ {hex(offset)}: {form0_size} bytes")
        data[offset:offset + form0_size] = form0_data
        offset += form0_size

        print(f"Formation 1 @ {hex(offset)}: {form1_size} bytes")
        data[offset:offset + form1_size] = form1_data
        offset += form1_size

        print(f"Formation 2 @ {hex(offset)}: {form2_size} bytes")
        data[offset:offset + form2_size] = form2_data
        offset += form2_size

        print()
        print("Writing BLAZE.ALL...")
        f.seek(0)
        f.write(data)
        print("Done!")
        print()

    print("=" * 70)
    print("  TEST READY")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Inject into BIN (py -3 patch_blaze_all.py)")
    print("  2. Test in-game: Cavern Floor 1 Area 1")
    print("  3. Trigger each formation and check spell lists")
    print()
    print("In-game testing:")
    print("  - Formation 0: Check Shaman spells (expect Goblin-like)")
    print("  - Formation 1: Check Shaman spells (expect Tower variant)")
    print("  - Formation 2: Check if Goblins can cast spells! (expect Sleep?)")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
