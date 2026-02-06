#!/usr/bin/env python3
"""
TEST: Swap type-8 entry offsets.

Area 1 has 2 type-8 entries:
  0xF7ACB4 (script+0x218): off=0x1DC0 type=8 idx=0x1E slot=0
  0xF7ACD8 (script+0x23C): off=0x1FC4 type=8 idx=0x20 slot=0

These point to deep room bytecode. Swap their offsets to see if
encounter behavior changes.

Start from CLEAN BLAZE.ALL.
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Type-8 entry locations (absolute offsets in BLAZE.ALL)
# Each entry: [uint32 offset] [type=08, idx, slot, 00]
TYPE8_ENTRY_1 = 0xF7ACB4  # off=0x1DC0
TYPE8_ENTRY_2 = 0xF7ACD8  # off=0x1FC4


def main():
    print("=" * 70)
    print("  TEST: Swap type-8 entry offsets")
    print("  Cavern F1 Area1 - from CLEAN source")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    # Read current values
    off1 = struct.unpack_from('<I', data, TYPE8_ENTRY_1)[0]
    meta1 = data[TYPE8_ENTRY_1+4:TYPE8_ENTRY_1+8]
    off2 = struct.unpack_from('<I', data, TYPE8_ENTRY_2)[0]
    meta2 = data[TYPE8_ENTRY_2+4:TYPE8_ENTRY_2+8]

    print(f"\n  Entry 1 at 0x{TYPE8_ENTRY_1:X}: off=0x{off1:04X} meta={meta1.hex()}")
    print(f"  Entry 2 at 0x{TYPE8_ENTRY_2:X}: off=0x{off2:04X} meta={meta2.hex()}")

    # Swap offsets only (keep type/idx/slot intact)
    struct.pack_into('<I', data, TYPE8_ENTRY_1, off2)
    struct.pack_into('<I', data, TYPE8_ENTRY_2, off1)

    # Verify
    new_off1 = struct.unpack_from('<I', data, TYPE8_ENTRY_1)[0]
    new_off2 = struct.unpack_from('<I', data, TYPE8_ENTRY_2)[0]
    print(f"\n  After swap:")
    print(f"  Entry 1: off=0x{new_off1:04X} (was 0x{off1:04X})")
    print(f"  Entry 2: off=0x{new_off2:04X} (was 0x{off2:04X})")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print(f"\n{'='*70}")
    print("  WATCH FOR:")
    print("  - AI/behavior changes? -> type-8 offsets control room scripts")
    print("  - Crash? -> offsets are critical")
    print("  - No change? -> these are interchangeable or not AI-related")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
