#!/usr/bin/env python3
"""
TEST: Swap L values + animation table data (but NOT 8-byte record offsets).

Previous tests:
  - L-only swap: models swap but crash (animation mismatch)
  - Full swap (including 8-byte records): instant crash (offsets are positional)

This test: swap L values AND the animation table bytes at each slot's position.
  Keep 8-byte record offsets unchanged (0x0C, 0x14, 0x1C stay in place).
  Keep type-7 entries, R values, and texrefs unchanged.

Swap: Goblin (slot 0) <-> Bat (slot 2)

Animation table layout (section start at 0xF7A904):
  Offset 0x08 (shared header): 00 01 02 03
  Offset 0x0C (slot 0 / Goblin): 04 04 05 05 06 06 07 07  (8 bytes)
  Offset 0x14 (slot 1 / Shaman): 08 09 0A 0B 0C 0C 0D 0E  (8 bytes)
  Offset 0x1C (slot 2 / Bat):    0F 0F 10 10 11 12 13 14  (8 bytes)
  Offset 0x24+ (tail):           15 16 0E 17 06 06 06 06 06 18 18 18
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

GROUP_OFFSET = 0xF7A97C
SECTION_START = 0xF7A904

# Animation table: each slot has 8 bytes at section_start + anim_offset
ANIM_SLOT_0 = SECTION_START + 0x0C  # 0xF7A910
ANIM_SLOT_1 = SECTION_START + 0x14  # 0xF7A918
ANIM_SLOT_2 = SECTION_START + 0x1C  # 0xF7A920
ANIM_SIZE = 8

# L value offsets (byte[1] of each AI entry)
L_SLOT_0 = 0xF7A964 + 1  # currently L=0
L_SLOT_2 = 0xF7A974 + 1  # currently L=3


def main():
    print("=" * 70)
    print("  TEST: Swap L + animation data (Goblin <-> Bat)")
    print("  Keep: 8-byte record offsets, type-7, R values, texrefs")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    # Show before
    print("\n--- BEFORE ---")
    for i, (off, name_str) in enumerate([
        (ANIM_SLOT_0, "Goblin"), (ANIM_SLOT_1, "Shaman"), (ANIM_SLOT_2, "Bat")
    ]):
        anim = data[off:off+ANIM_SIZE]
        print(f"  Slot {i} ({name_str}): anim=[{anim.hex()}] at 0x{off:X}")
    print(f"  L values: slot0={data[L_SLOT_0]}, slot1={data[L_SLOT_0+8]}, slot2={data[L_SLOT_2]}")

    # Swap L values: slot 0 <-> slot 2
    print("\n  [Swapping L values...]")
    data[L_SLOT_0], data[L_SLOT_2] = data[L_SLOT_2], data[L_SLOT_0]

    # Swap animation table data: slot 0 <-> slot 2
    print("  [Swapping animation table bytes...]")
    tmp = bytes(data[ANIM_SLOT_0:ANIM_SLOT_0+ANIM_SIZE])
    data[ANIM_SLOT_0:ANIM_SLOT_0+ANIM_SIZE] = data[ANIM_SLOT_2:ANIM_SLOT_2+ANIM_SIZE]
    data[ANIM_SLOT_2:ANIM_SLOT_2+ANIM_SIZE] = tmp

    # Show after
    print("\n--- AFTER ---")
    for i, off in enumerate([ANIM_SLOT_0, ANIM_SLOT_1, ANIM_SLOT_2]):
        anim = data[off:off+ANIM_SIZE]
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off+16].split(b'\x00')[0].decode('ascii')
        print(f"  Slot {i} ({name}): anim=[{anim.hex()}] at 0x{off:X}")
    print(f"  L values: slot0={data[L_SLOT_0]}, slot1={data[L_SLOT_0+8]}, slot2={data[L_SLOT_2]}")

    # Verify 8-byte records are UNCHANGED
    RECORD_BASE = 0xF7A934
    print("\n--- 8-byte records (should be ORIGINAL) ---")
    for i in range(3):
        off = RECORD_BASE + i * 8
        raw = data[off:off+8]
        print(f"  Record {i}: [{raw.hex()}]")

    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print("\n" + "=" * 70)
    print("  Slot 0 'Goblin': L=3 (Bat) + Bat anim frames")
    print("  Slot 2 'Bat':    L=0 (Goblin) + Goblin anim frames")
    print("  8-byte records et type-7: inchanges")
    print("=" * 70)


if __name__ == '__main__':
    main()
