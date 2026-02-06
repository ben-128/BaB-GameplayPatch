#!/usr/bin/env python3
"""
TEST: Swap type-7 OFFSET values between Goblin and Bat.

Previous test (idx swap) had no effect - the idx is just a label.
The game follows the OFFSET to find the actual resource data.

Type-7 entries:
  0xF7ABE4: [off=0x0580] [07 10 00 00]  <- Goblin (slot 0)
  0xF7ABEC: [off=0x0588] [07 11 01 00]  <- Shaman (slot 1)
  0xF7ABF4: [off=0x0590] [07 12 02 00]  <- Bat    (slot 2)

This test: swap the uint32 offset values 0x0580 <-> 0x0590
  Slot 0 (Goblin) will load resource data from offset 0x0590 (Bat's data)
  Slot 2 (Bat) will load resource data from offset 0x0580 (Goblin's data)

Also restore idx to original values (undo previous test).
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

TYPE7_GOBLIN = 0xF7ABE4
TYPE7_SHAMAN = 0xF7ABEC
TYPE7_BAT    = 0xF7ABF4


def show_entry(data, name, addr):
    entry = data[addr:addr+8]
    off_val = struct.unpack_from('<I', entry, 0)[0]
    type_val, idx_val, slot_val, pad = entry[4], entry[5], entry[6], entry[7]
    print(f"  {name:8s} at 0x{addr:X}: off=0x{off_val:04X} type={type_val} "
          f"idx=0x{idx_val:02X} slot={slot_val} | raw=[{entry.hex()}]")
    return off_val


def main():
    print("=" * 70)
    print("  TEST: Swap type-7 OFFSET (Goblin <-> Bat)")
    print("  Keep: L, R, anim, 8-byte records, 96-byte entries, idx values")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    print("\n--- BEFORE ---")
    gob_off = show_entry(data, "Goblin", TYPE7_GOBLIN)
    sha_off = show_entry(data, "Shaman", TYPE7_SHAMAN)
    bat_off = show_entry(data, "Bat", TYPE7_BAT)

    # Swap offset values (first 4 bytes of each entry)
    print(f"\n  [Swapping offsets: Goblin 0x{gob_off:04X} <-> Bat 0x{bat_off:04X}]")

    gob_off_bytes = data[TYPE7_GOBLIN:TYPE7_GOBLIN+4]
    bat_off_bytes = data[TYPE7_BAT:TYPE7_BAT+4]

    data[TYPE7_GOBLIN:TYPE7_GOBLIN+4] = bat_off_bytes
    data[TYPE7_BAT:TYPE7_BAT+4] = gob_off_bytes

    print("\n--- AFTER ---")
    show_entry(data, "Goblin", TYPE7_GOBLIN)
    show_entry(data, "Shaman", TYPE7_SHAMAN)
    show_entry(data, "Bat", TYPE7_BAT)

    # Also show what's at the target offsets (relative to script area start)
    script_start = 0xF7AA9C  # group_offset + 3*96
    print(f"\n  Script area starts at 0x{script_start:X}")
    for name, off in [("Goblin's data", gob_off), ("Bat's data", bat_off)]:
        abs_addr = script_start + off
        chunk = data[abs_addr:abs_addr+32]
        print(f"  {name} at script+0x{off:04X} = 0x{abs_addr:X}:")
        print(f"    [{chunk[:16].hex()}]")
        print(f"    [{chunk[16:].hex()}]")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print("\n" + "=" * 70)
    print("  Slot 0 (Goblin model) now loads Bat's resource -> Bat behavior?")
    print("  Slot 2 (Bat model) now loads Goblin's resource -> Goblin behavior?")
    print("=" * 70)


if __name__ == '__main__':
    main()
