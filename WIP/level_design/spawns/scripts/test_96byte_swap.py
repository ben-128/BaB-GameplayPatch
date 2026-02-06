#!/usr/bin/env python3
"""
TEST: Swap ENTIRE 96-byte entries between Goblin (slot 0) and Bat (slot 2).

Previous tests confirmed:
  - L = model mesh, type-7 offset = textures, neither controls AI
  - AI stays with the slot

This test: swap all 96 bytes (name + stats) between slot 0 and slot 2.
  - Slot 0 will have Bat's name+stats, but Goblin model (L unchanged)
  - Slot 2 will have Goblin's name+stats, but Bat model (L unchanged)

If AI swaps -> AI reference is in the 96-byte entry (name or a stat field)
If AI stays -> AI is positional (spawn commands or elsewhere in script area)
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

GROUP_OFFSET = 0xF7A97C
ENTRY_SIZE = 96

SLOT_0 = GROUP_OFFSET               # Lv20.Goblin
SLOT_1 = GROUP_OFFSET + ENTRY_SIZE   # Goblin-Shaman
SLOT_2 = GROUP_OFFSET + 2 * ENTRY_SIZE  # Giant-Bat


def show_entry(data, slot, addr):
    entry = data[addr:addr+ENTRY_SIZE]
    name = entry[:16].split(b'\x00')[0].decode('ascii')
    # Key stats
    exp = int.from_bytes(entry[16:18], 'little')
    level = int.from_bytes(entry[18:20], 'little')
    hp = int.from_bytes(entry[20:22], 'little')
    ctype = int.from_bytes(entry[36:38], 'little')
    collider = int.from_bytes(entry[26:28], 'little')
    print(f"  Slot {slot} at 0x{addr:X}: {name:20s} "
          f"lv={level} hp={hp} exp={exp} creature_type={ctype} collider={collider}")


def main():
    print("=" * 70)
    print("  TEST: Swap 96-byte entries (Goblin <-> Bat)")
    print("  Keep: L, R, anim, 8-byte records, type-7 (all original)")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    print("\n--- BEFORE ---")
    show_entry(data, 0, SLOT_0)
    show_entry(data, 1, SLOT_1)
    show_entry(data, 2, SLOT_2)

    # Swap entire 96 bytes between slot 0 and slot 2
    print("\n  [Swapping 96-byte entries: slot 0 <-> slot 2]")
    tmp = bytes(data[SLOT_0:SLOT_0+ENTRY_SIZE])
    data[SLOT_0:SLOT_0+ENTRY_SIZE] = data[SLOT_2:SLOT_2+ENTRY_SIZE]
    data[SLOT_2:SLOT_2+ENTRY_SIZE] = tmp

    print("\n--- AFTER ---")
    show_entry(data, 0, SLOT_0)
    show_entry(data, 1, SLOT_1)
    show_entry(data, 2, SLOT_2)

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print("\n" + "=" * 70)
    print("  Slot 0: Goblin model + 'Giant-Bat' name/stats")
    print("  Slot 2: Bat model + 'Lv20.Goblin' name/stats")
    print("")
    print("  If AI swaps -> AI is in the 96-byte entry")
    print("  If AI stays -> AI is positional (spawn commands)")
    print("=" * 70)


if __name__ == '__main__':
    main()
