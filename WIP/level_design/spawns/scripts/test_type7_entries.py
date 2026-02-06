#!/usr/bin/env python3
"""
TEST: Do the "type 7" entries in the script area control the 3D model?

After the 96-byte entries, there's a resource definition table.
Entries with first byte = 0x07 are per-monster, one per slot.

Cavern Floor 1 Area 1 (3 monsters):
  Script area starts at 0xF7AA9C (after 96-byte entries end)

  Type+index entries found at:
    0xF7ABCC: [0568] [04, 00, 00, 00]  <- fixed overhead
    0xF7ABD4: [0570] [05, 01, 00, 00]  <- fixed overhead
    0xF7ABDC: [0578] [06, 02, 00, 00]  <- fixed overhead
    0xF7ABE4: [0580] [07, 10, 00, 00]  <- MONSTER 0 (Goblin), index=0x10
    0xF7ABEC: [0588] [07, 11, 01, 00]  <- MONSTER 1 (Shaman), index=0x11
    0xF7ABF4: [0590] [07, 12, 02, 00]  <- MONSTER 2 (Bat), index=0x12
    0xF7ABFC: [0598] [0E, 13, 00, 00]  <- fixed overhead

Test: Set all 3 monster type-7 entries to index 0x12 (Bat).
  Monster 0 (Goblin): index 0x10 -> 0x12
  Monster 1 (Shaman): index 0x11 -> 0x12
  Monster 2 (Bat): index 0x12 -> 0x12 (unchanged)

Expected if type-7 index controls 3D model:
  -> 3 Giant-Bat meshes
  -> Names/stats: Goblin, Shaman, Bat
  -> AI: original (Goblin walks, Shaman casts, Bat flies)
  -> Textures: original (unless texture is also linked)
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Type-7 entry locations (absolute offsets in BLAZE.ALL)
# Format: [uint32 offset][byte type, byte index, byte slot, byte 0]
# We patch the "index" byte (byte 5 of the 8-byte entry)
TYPE7_ENTRIES = [
    0xF7ABE4,  # Monster 0 (Goblin): [0580] [07, 10, 00, 00]
    0xF7ABEC,  # Monster 1 (Shaman): [0588] [07, 11, 01, 00]
    0xF7ABF4,  # Monster 2 (Bat):    [0590] [07, 12, 02, 00]
]

# Index byte offset within the 8-byte entry
INDEX_BYTE_OFFSET = 5  # byte[5] = the index value (0x10, 0x11, 0x12)

TARGET_INDEX = 0x12  # Bat's index


def main():
    print("=" * 70)
    print("  TEST: Change type-7 entry indices to Bat (0x12)")
    print("=" * 70)
    print()

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    # Show current state - dump the full entry region
    print()
    print("--- Current type+index entries ---")
    region_start = TYPE7_ENTRIES[0] - 24  # include 3 entries before
    region_end = TYPE7_ENTRIES[-1] + 16   # include 1 entry after
    for off in range(region_start, region_end, 8):
        entry_offset = struct.unpack_from('<I', data, off)[0]
        val = data[off+4:off+8]
        type_byte = val[0]
        index_byte = val[1]
        slot_byte = val[2]
        flag_byte = val[3]
        marker = ""
        if off in TYPE7_ENTRIES:
            idx = TYPE7_ENTRIES.index(off)
            marker = f"  <-- MONSTER {idx}"
        print(f"  0x{off:08X}: [0x{entry_offset:04X}] [{val.hex()}] type={type_byte:2d} idx=0x{index_byte:02X} slot={slot_byte} flag={flag_byte}{marker}")

    # Patch type-7 entries
    print()
    print(f"--- Patching type-7 index bytes to 0x{TARGET_INDEX:02X} ---")
    for i, off in enumerate(TYPE7_ENTRIES):
        idx_off = off + INDEX_BYTE_OFFSET
        old_idx = data[idx_off]
        data[idx_off] = TARGET_INDEX
        print(f"  Monster {i} at 0x{off:X}: index 0x{old_idx:02X} -> 0x{TARGET_INDEX:02X}")

    # Show patched state
    print()
    print("--- Patched type+index entries ---")
    for off in range(region_start, region_end, 8):
        entry_offset = struct.unpack_from('<I', data, off)[0]
        val = data[off+4:off+8]
        type_byte = val[0]
        index_byte = val[1]
        slot_byte = val[2]
        flag_byte = val[3]
        marker = ""
        if off in TYPE7_ENTRIES:
            idx = TYPE7_ENTRIES.index(off)
            marker = f"  <-- MONSTER {idx} (PATCHED)"
        print(f"  0x{off:08X}: [0x{entry_offset:04X}] [{val.hex()}] type={type_byte:2d} idx=0x{index_byte:02X} slot={slot_byte} flag={flag_byte}{marker}")

    # Verify name entries are untouched
    GROUP_OFFSET = 0xF7A97C
    print()
    print("--- Monster names (should be original) ---")
    for i in range(3):
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        print(f"  Slot {i}: {name}")

    # Save
    print()
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"[SAVED] {BLAZE_OUT}")

    print()
    print("=" * 70)
    print("  SI type-7 index CONTROLE LE MODELE 3D:")
    print("    -> 3 meshes de Giant-Bat")
    print("    -> Noms: Goblin, Shaman, Bat")
    print("    -> AI/comportement normal")
    print()
    print("  SI type-7 index NE CONTROLE PAS:")
    print("    -> Visuels normaux OU crash")
    print("=" * 70)


if __name__ == '__main__':
    main()
