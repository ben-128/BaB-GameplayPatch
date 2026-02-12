#!/usr/bin/env python3
"""
TEST: Isolate SUFFIX effect (no filler spawns).

Use duplicate offsets for entries 3-7 to avoid filler spawns.
Only test formations 0-2 will be selectable.
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

FORMATION_AREA_START = 0xF7AFFC
FORMATION_AREA_BYTES = 896
SCRIPT_START = 0xF7AA9C
RECORD_SIZE = 32
SUFFIX_SIZE = 4

SUFFIXES = {
    "vanilla_shaman": bytes.fromhex("02000000"),  # Sleep, MM, Stone Bullet
    "tower": bytes.fromhex("03000000"),            # Sleep, MM, Heal
    "bat": bytes.fromhex("00000a00"),              # FireBullet, MM, Stone Bullet
}


def build_formation(num_shamans, suffix_value):
    """Build formation with vanilla structure, custom SUFFIX only.

    All records use vanilla prefix structure (first=00000000, rest=02000000).
    Only the SUFFIX is changed to test its effect.
    """
    area_id = bytes.fromhex("dc01")
    binary = bytearray()

    for idx in range(num_shamans):
        is_first = (idx == 0)
        rec = bytearray(RECORD_SIZE)

        # byte[0:4] = prefix (vanilla structure)
        if is_first:
            rec[0:4] = bytes(4)  # 00000000
        else:
            rec[0:4] = SUFFIXES["vanilla_shaman"]  # 02000000 (vanilla Shaman)

        # byte[4:8] = FFFFFFFF for first, 00000000 for rest
        if is_first:
            rec[4:8] = b'\xff\xff\xff\xff'

        # byte[8] = slot_index (1 = Shaman)
        rec[8] = 0x01

        # byte[9] = 0xFF
        rec[9] = 0xFF

        # byte[24:26] = area_id
        rec[24:26] = area_id

        # byte[26:32] = terminator
        rec[26:32] = b'\xff\xff\xff\xff\xff\xff'

        binary.extend(rec)

    # SUFFIX = TEST VALUE (this is what we're testing!)
    binary.extend(suffix_value)

    return bytes(binary)


def main():
    print("=" * 70)
    print("  SUFFIX-ONLY TEST (No Filler Spawns)")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} does not exist!")
        return 1

    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())
        print(f"BLAZE.ALL: {len(data):,} bytes")
        print()

        print("HYPOTHESIS: SUFFIX controls spell set, not prefix!")
        print()
        print("TEST CONFIGURATIONS:")
        print("-" * 70)
        print()
        print("Formation 0: 3 Shamans + SUFFIX 02000000 (vanilla)")
        print("  Expected: Sleep, Magic Missile, Stone Bullet")
        print()
        print("Formation 1: 3 Shamans + SUFFIX 03000000 (Tower)")
        print("  Expected: Sleep, Magic Missile, Heal")
        print()
        print("Formation 2: 3 Shamans + SUFFIX 00000a00 (Bat)")
        print("  Expected: FireBullet, Magic Missile, Stone Bullet")
        print()
        print("Offset table: Entries 3-7 duplicate Formation 2")
        print("  (No filler spawns - only test formations selectable)")
        print()

        response = input("Apply test? (o/n): ").lower()
        if response != 'o':
            print("Cancelled.")
            return 0

        print()
        print("Building formations...")
        print()

        # Build 3 formations (all 3 Shamans, only SUFFIX differs)
        form0 = build_formation(3, SUFFIXES["vanilla_shaman"])  # Control
        form1 = build_formation(3, SUFFIXES["tower"])           # Test 1
        form2 = build_formation(3, SUFFIXES["bat"])             # Test 2

        total_size = len(form0) + len(form1) + len(form2)

        print(f"Formation 0: {len(form0)} bytes (3 Shamans, suffix vanilla)")
        print(f"Formation 1: {len(form1)} bytes (3 Shamans, suffix Tower)")
        print(f"Formation 2: {len(form2)} bytes (3 Shamans, suffix Bat)")
        print(f"Total: {total_size} bytes / {FORMATION_AREA_BYTES} bytes budget")
        print()

        # Build area binary
        area_binary = bytearray()
        area_binary.extend(form0)
        area_binary.extend(form1)
        area_binary.extend(form2)

        # Pad rest with zeros
        remaining = FORMATION_AREA_BYTES - len(area_binary)
        area_binary.extend(bytes(remaining))
        print(f"Padded with {remaining} zero bytes")
        print()

        # Update offset table (8 entries, but only 3 formations)
        fm_start_idx = 4
        current_fm0 = struct.unpack_from('<I', data, SCRIPT_START + fm_start_idx * 4)[0]

        offset0 = current_fm0
        offset1 = offset0 + len(form0)
        offset2 = offset1 + len(form1)

        # Entries 3-7: Duplicate offset2 (Formation 2)
        # This prevents filler spawns - game will only pick formations 0-2
        offsets = [offset0, offset1, offset2, offset2, offset2, offset2, offset2, offset2]

        print("Updating offset table...")
        for i, offset in enumerate(offsets):
            struct.pack_into('<I', data, SCRIPT_START + (fm_start_idx + i) * 4, offset)
            if i < 3:
                print(f"  Entry {i}: {offset} (test formation {i})")
            else:
                print(f"  Entry {i}: {offset} (duplicate -> Formation 2)")
        print()

        # Write formation area
        data[FORMATION_AREA_START:FORMATION_AREA_START + FORMATION_AREA_BYTES] = area_binary

        f.seek(0)
        f.write(data)
        print("Done!")
        print()

    print("=" * 70)
    print("  TEST READY")
    print("=" * 70)
    print()
    print("All formations have 3 Shamans for easy identification.")
    print("Only the SUFFIX differs:")
    print()
    print("  Test 1 encounter -> Formation 0 (suffix 02000000)")
    print("    Expected: Sleep, Magic Missile, Stone Bullet")
    print()
    print("  Test 2 encounter -> Formation 1 (suffix 03000000)")
    print("    Expected: Sleep, Magic Missile, Heal")
    print()
    print("  Test 3 encounter -> Formation 2 (suffix 00000a00)")
    print("    Expected: FireBullet, Magic Missile, Stone Bullet")
    print()
    print("No Goblin fillers should spawn!")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
