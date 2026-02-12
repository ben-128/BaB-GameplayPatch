#!/usr/bin/env python3
"""
FIXED TEST: Respect formation record structure.

KEY FIX: First record ALWAYS has byte[0:4] = 00000000
         Only subsequent records use the prefix value!
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

PREFIXES = {
    "goblin": bytes.fromhex("00000000"),
    "tower": bytes.fromhex("03000000"),
    "bat": bytes.fromhex("00000a00"),
    "shaman": bytes.fromhex("02000000"),
}


def build_formation(num_shamans, prefix_value):
    """Build formation with correct prefix structure.

    CRITICAL: First record has byte[0:4] = 00000000
              Subsequent records use prefix_value
    """
    area_id = bytes.fromhex("dc01")
    binary = bytearray()

    for idx in range(num_shamans):
        is_first = (idx == 0)
        rec = bytearray(RECORD_SIZE)

        # byte[0:4] = prefix
        # CRITICAL FIX: First record ALWAYS 00000000
        if is_first:
            rec[0:4] = bytes(4)  # 00000000
        else:
            rec[0:4] = prefix_value  # Use test value for subsequent records

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

    # Suffix = prefix_value (type of last monster)
    binary.extend(prefix_value)

    return bytes(binary)


def build_filler(filler_idx):
    """Build a 1-record filler formation for padding."""
    area_id = bytes.fromhex("dc01")
    rec = bytearray(RECORD_SIZE)

    # First record: byte[0:4] = 00000000
    rec[0:4] = bytes(4)
    # byte[4:8] = FFFFFFFF (formation start)
    rec[4:8] = b'\xff\xff\xff\xff'
    # byte[8] = slot 0 (Goblin)
    rec[8] = 0x00
    # byte[9] = 0xFF
    rec[9] = 0xFF
    # byte[24:26] = area_id
    rec[24:26] = area_id
    # byte[26:32] = terminator
    rec[26:32] = b'\xff\xff\xff\xff\xff\xff'

    # Suffix = Goblin type
    suffix = PREFIXES["goblin"]

    return bytes(rec) + suffix


def main():
    print("=" * 70)
    print("  FIXED 3-FORMATION TEST")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} does not exist!")
        return 1

    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())
        print(f"BLAZE.ALL: {len(data):,} bytes")
        print()

        print("TEST CONFIGURATIONS:")
        print("-" * 70)
        print()
        print("Formation 0: 1 Shaman")
        print("  Record 0: byte[0:4] = 00000000 (first record rule)")
        print("  Suffix:   00000000 (Goblin base test)")
        print()
        print("Formation 1: 2 Shamans")
        print("  Record 0: byte[0:4] = 00000000 (first record rule)")
        print("  Record 1: byte[0:4] = 03000000 (Tower test)")
        print("  Suffix:   03000000")
        print()
        print("Formation 2: 3 Shamans")
        print("  Record 0: byte[0:4] = 00000000 (first record rule)")
        print("  Record 1: byte[0:4] = 00000a00 (Bat test)")
        print("  Record 2: byte[0:4] = 00000a00 (Bat test)")
        print("  Suffix:   00000a00")
        print()
        print("Formations 3-7: Fillers (1 Goblin each)")
        print()

        response = input("Apply test? (o/n): ").lower()
        if response != 'o':
            print("Cancelled.")
            return 0

        print()
        print("Building formations...")
        print()

        # Build test formations
        # Use SUFFIX to control the spell modifier test
        form0 = build_formation(1, PREFIXES["goblin"])   # 1 Shaman
        form1 = build_formation(2, PREFIXES["tower"])    # 2 Shamans
        form2 = build_formation(3, PREFIXES["bat"])      # 3 Shamans

        # Build 5 fillers (to have 8 formations total as expected)
        fillers = [build_filler(i) for i in range(5)]

        # Calculate sizes
        user_size = len(form0) + len(form1) + len(form2)
        filler_size = sum(len(f) for f in fillers)
        total_size = user_size + filler_size

        print(f"Formation 0: {len(form0)} bytes (1 Shaman)")
        print(f"Formation 1: {len(form1)} bytes (2 Shamans)")
        print(f"Formation 2: {len(form2)} bytes (3 Shamans)")
        print(f"Fillers (5): {filler_size} bytes")
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
        for filler in fillers:
            area_binary.extend(filler)

        # Pad rest with zeros
        remaining = FORMATION_AREA_BYTES - len(area_binary)
        if remaining > 0:
            area_binary.extend(bytes(remaining))
            print(f"Padded with {remaining} zero bytes")
        print()

        # Update offset table
        fm_start_idx = 4
        current_fm0 = struct.unpack_from('<I', data, SCRIPT_START + fm_start_idx * 4)[0]

        offset0 = current_fm0
        offset1 = offset0 + len(form0)
        offset2 = offset1 + len(form1)
        offset3 = offset2 + len(form2)
        offset4 = offset3 + len(fillers[0])
        offset5 = offset4 + len(fillers[1])
        offset6 = offset5 + len(fillers[2])
        offset7 = offset6 + len(fillers[3])

        offsets = [offset0, offset1, offset2, offset3, offset4, offset5, offset6, offset7]

        print("Updating offset table...")
        for i, offset in enumerate(offsets):
            struct.pack_into('<I', data, SCRIPT_START + (fm_start_idx + i) * 4, offset)
            if i < 3:
                print(f"  Entry {i}: {offset} (test formation)")
            else:
                print(f"  Entry {i}: {offset} (filler)")
        print()

        # Write formation area
        print(f"Writing formations to {hex(FORMATION_AREA_START)}...")
        data[FORMATION_AREA_START:FORMATION_AREA_START + FORMATION_AREA_BYTES] = area_binary

        f.seek(0)
        f.write(data)
        print("Done!")
        print()

    print("=" * 70)
    print("  TEST READY")
    print("=" * 70)
    print()
    print("Key insight: byte[0:4] of SUBSEQUENT records (not first)")
    print("             controls the spell modifier!")
    print()
    print("Expected results:")
    print("  Formation 0 (1 Shaman): ? (only has first record)")
    print("  Formation 1 (2 Shamans): Record 1 has Tower prefix")
    print("  Formation 2 (3 Shamans): Records 1-2 have Bat prefix -> FireBullet")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
