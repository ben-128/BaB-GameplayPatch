#!/usr/bin/env python3
"""
CLEAN TEST: 3 formations only, different prefix values.

Formation 0: 1 Shaman  + prefix 00000000 (Goblin base)
Formation 1: 2 Shamans + prefix 03000000 (Tower variant)
Formation 2: 3 Shamans + prefix 00000a00 (Bat - confirmed: FireBullet)

Area will have ONLY these 3 formations (no vanilla after).
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern F1 A1
FORMATION_AREA_START = 0xF7AFFC
FORMATION_AREA_BYTES = 896
SCRIPT_START = 0xF7AA9C
RECORD_SIZE = 32
SUFFIX_SIZE = 4

# Test values
PREFIXES = {
    "goblin": bytes.fromhex("00000000"),
    "tower": bytes.fromhex("03000000"),
    "bat": bytes.fromhex("00000a00"),
}


def build_formation(num_shamans, prefix_value):
    """Build a formation with N Shamans, all with same prefix."""
    area_id = bytes.fromhex("dc01")
    binary = bytearray()

    for idx in range(num_shamans):
        is_first = (idx == 0)
        rec = bytearray(RECORD_SIZE)

        # byte[0:4] = prefix (use specified value for ALL records)
        rec[0:4] = prefix_value

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

    # Suffix = same as prefix for consistency
    binary.extend(prefix_value)

    return bytes(binary)


def main():
    print("=" * 70)
    print("  CLEAN 3-FORMATION TEST")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} does not exist!")
        return 1

    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())
        print(f"BLAZE.ALL: {len(data):,} bytes")
        print()

        # Test configurations
        print("TEST CONFIGURATIONS:")
        print("-" * 70)
        print()
        print("Formation 0:")
        print("  1x Shaman + prefix 00000000 (Goblin base)")
        print("  Expected: ? (testing)")
        print()
        print("Formation 1:")
        print("  2x Shamans + prefix 03000000 (Tower variant)")
        print("  Expected: ? (testing)")
        print()
        print("Formation 2:")
        print("  3x Shamans + prefix 00000a00 (Bat)")
        print("  Expected: FireBullet (confirmed control)")
        print()
        print("Area will have ONLY these 3 formations.")
        print("Vanilla formations removed, area padded with zeros.")
        print()

        response = input("Apply test? (o/n): ").lower()
        if response != 'o':
            print("Cancelled.")
            return 0

        print()
        print("Building formations...")
        print()

        # Build 3 formations
        form0 = build_formation(1, PREFIXES["goblin"])    # 1 Shaman
        form1 = build_formation(2, PREFIXES["tower"])     # 2 Shamans
        form2 = build_formation(3, PREFIXES["bat"])       # 3 Shamans

        total_size = len(form0) + len(form1) + len(form2)
        print(f"Formation 0: {len(form0)} bytes (1 Shaman)")
        print(f"Formation 1: {len(form1)} bytes (2 Shamans)")
        print(f"Formation 2: {len(form2)} bytes (3 Shamans)")
        print(f"Total: {total_size} bytes / {FORMATION_AREA_BYTES} bytes budget")
        print()

        if total_size > FORMATION_AREA_BYTES:
            print(f"ERROR: Exceeds budget by {total_size - FORMATION_AREA_BYTES} bytes!")
            return 1

        # Build complete area binary
        area_binary = bytearray()
        area_binary.extend(form0)
        area_binary.extend(form1)
        area_binary.extend(form2)

        # Pad rest with zeros
        remaining = FORMATION_AREA_BYTES - len(area_binary)
        area_binary.extend(bytes(remaining))

        print(f"Padded with {remaining} zero bytes")
        print()

        # Update offset table in script area
        # Script area offset table: [entry0, 0, SP_offsets..., FM_offsets..., 0, 0]
        # For Cavern F1 A1: spawn_point_count = 2, so FM entries start at index 2+2 = 4
        fm_start_idx = 4

        # Calculate new offsets (relative to some implied base)
        # We need to read the current first FM offset to get the base
        current_fm0 = struct.unpack_from('<I', data, SCRIPT_START + fm_start_idx * 4)[0]

        # New offsets relative to same base
        offset0 = current_fm0  # Keep first offset same (formation area start)
        offset1 = offset0 + len(form0)
        offset2 = offset1 + len(form1)

        # Write offsets (3 formations only, so we have 8 entries but use 3)
        # Duplicate offset2 for the remaining 5 entries (round-robin to formation 2)
        offsets = [offset0, offset1, offset2, offset2, offset2, offset2, offset2, offset2]

        print("Updating offset table...")
        for i, offset in enumerate(offsets):
            struct.pack_into('<I', data, SCRIPT_START + (fm_start_idx + i) * 4, offset)
            print(f"  Entry {i}: {offset}")
        print()

        # Write formation area
        print(f"Writing formations to {hex(FORMATION_AREA_START)}...")
        data[FORMATION_AREA_START:FORMATION_AREA_START + FORMATION_AREA_BYTES] = area_binary

        # Write back
        f.seek(0)
        f.write(data)
        print("Done!")
        print()

    print("=" * 70)
    print("  TEST READY")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Inject: py -3 patch_blaze_all.py")
    print("  2. Test in-game: Cavern Floor 1 Area 1")
    print("  3. Document spell list for each formation:")
    print()
    print("     Formation 0 (1 Shaman, prefix 00000000):")
    print("       Spell 1: ?")
    print("       Spell 2: Magic Missile (expected)")
    print("       Spell 3: Stone Bullet (expected)")
    print()
    print("     Formation 1 (2 Shamans, prefix 03000000):")
    print("       Spell 1: ?")
    print("       Spell 2: Magic Missile (expected)")
    print("       Spell 3: Stone Bullet (expected)")
    print()
    print("     Formation 2 (3 Shamans, prefix 00000a00):")
    print("       Spell 1: FireBullet (confirmed)")
    print("       Spell 2: Magic Missile (expected)")
    print("       Spell 3: Stone Bullet (expected)")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
