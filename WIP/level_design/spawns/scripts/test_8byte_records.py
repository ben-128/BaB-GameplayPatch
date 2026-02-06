#!/usr/bin/env python3
"""
TEST: Do the 8-byte records control the monster visual?

Structure of 8-byte records (N per spawn group, one per monster):
  [uint32 anim_offset] [uint32 packed_model_ref]

Cavern Floor 1, Area 1 (3 monsters):
  0xF7A934: [0C000000] [00000300]  record 0 (Goblin)   model_ref=0x00030000
  0xF7A93C: [14000000] [00400400]  record 1 (Shaman)   model_ref=0x00044000
  0xF7A944: [1C000000] [00800500]  record 2 (Bat)      model_ref=0x00058000

Test: Change all 3 model_ref values to Giant-Bat's value (0x00058000).
Keep animation offsets unchanged. Keep assignment entries unchanged.

Expected if model_ref controls visual:
  -> 3 Giant-Bats with Goblin/Shaman/Bat names, stats, and AI

Run: py -3 test_8byte_records.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# 8-byte records for Cavern Floor 1 Area 1
RECORD_BASE = 0xF7A934
NUM_RECORDS = 3

# Target: Giant-Bat's model_ref (record 2)
TARGET_MODEL_REF = 0x00058000


def main():
    print("=" * 70)
    print("  TEST: Change 8-byte record model_ref to Giant-Bat")
    print("=" * 70)
    print()

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    # Show current state
    print()
    print("--- Current 8-byte records ---")
    for i in range(NUM_RECORDS):
        off = RECORD_BASE + i * 8
        anim_off = struct.unpack_from('<I', data, off)[0]
        model_ref = struct.unpack_from('<I', data, off + 4)[0]
        raw = data[off:off + 8]
        print(f"  Record {i} at 0x{off:X}: anim_off=0x{anim_off:04X} model_ref=0x{model_ref:08X} raw=[{raw.hex()}]")

    # Patch: change model_ref for all 3 records
    print()
    print(f"--- Patching model_ref to 0x{TARGET_MODEL_REF:08X} (Giant-Bat) ---")
    for i in range(NUM_RECORDS):
        off = RECORD_BASE + i * 8 + 4  # second uint32
        old_ref = struct.unpack_from('<I', data, off)[0]
        struct.pack_into('<I', data, off, TARGET_MODEL_REF)
        print(f"  Record {i}: 0x{old_ref:08X} -> 0x{TARGET_MODEL_REF:08X}")

    # Show patched state
    print()
    print("--- Patched 8-byte records ---")
    for i in range(NUM_RECORDS):
        off = RECORD_BASE + i * 8
        anim_off = struct.unpack_from('<I', data, off)[0]
        model_ref = struct.unpack_from('<I', data, off + 4)[0]
        raw = data[off:off + 8]
        print(f"  Record {i} at 0x{off:X}: anim_off=0x{anim_off:04X} model_ref=0x{model_ref:08X} raw=[{raw.hex()}]")

    # Verify assignment entries and names are untouched
    GROUP_OFFSET = 0xF7A97C
    ENTRIES_BASE = 0xF7A964
    print()
    print("--- Assignment entries (should be ORIGINAL) ---")
    for i in range(3):
        ai_off = ENTRIES_BASE + i * 8
        model_off = ENTRIES_BASE + i * 8 + 4
        ai_e = data[ai_off:ai_off + 4]
        mod_e = data[model_off:model_off + 4]
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        print(f"  Slot {i} '{name}': AI=[{ai_e.hex()}] Model=[{mod_e.hex()}]")

    # Save
    print()
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"[SAVED] {BLAZE_OUT}")

    print()
    print("=" * 70)
    print("  SI model_ref CONTROLE LE VISUEL:")
    print("    -> 3 Giant-Bats, noms/stats/AI normaux")
    print("  SI model_ref NE CONTROLE PAS:")
    print("    -> Visuels normaux OU crash")
    print("=" * 70)


if __name__ == '__main__':
    main()
