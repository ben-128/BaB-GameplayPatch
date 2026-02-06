#!/usr/bin/env python3
"""
TEST: Swap per-monster resource index (type-7 idx) between Goblin and Bat.

Hypothesis: The type-7 idx in the script area controls AI/behavior.
Evidence:
  - L+anim swap gave bat models on ground shooting arrows (slot 0's type-7=0x10)
  - L+anim swap gave goblin models flying (slot 2's type-7=0x12)
  - Type-7=0x10 -> Goblin behavior (ground + arrow), Type-7=0x12 -> Bat behavior (flying)

This test: swap ONLY the idx values in type-7 entries:
  - Slot 0 (Goblin): idx 0x10 -> 0x12 (Bat behavior)
  - Slot 2 (Bat):    idx 0x12 -> 0x10 (Goblin behavior)
  - Slot 1 (Shaman): unchanged (idx 0x11)

Expected if hypothesis is correct:
  - Slot 0: Goblin model on ground but behaves like Bat (flies? swoops?)
  - Slot 2: Bat model but behaves like Goblin (walks? shoots arrows?)

The type-7 entries are in the script area at these absolute offsets:
  0xF7ABE4: [80 05 00 00] [07 10 00 00]  <- Goblin (slot 0), idx=0x10
  0xF7ABEC: [88 05 00 00] [07 11 01 00]  <- Shaman (slot 1), idx=0x11
  0xF7ABF4: [90 05 00 00] [07 12 02 00]  <- Bat    (slot 2), idx=0x12

We only need to swap byte[5] (the idx) at 0xF7ABE5 and 0xF7ABF5.
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Type-7 entry positions (from find_ai_controller.py output)
# Format at each position: [uint32 offset] [type=07, idx, slot, 00]
# The idx byte is at base + 5
TYPE7_GOBLIN = 0xF7ABE4  # [80050000] [07 10 00 00]
TYPE7_SHAMAN = 0xF7ABEC  # [88050000] [07 11 01 00]
TYPE7_BAT    = 0xF7ABF4  # [90050000] [07 12 02 00]

IDX_OFFSET = 5  # byte offset within the 8-byte entry for the idx value


def main():
    print("=" * 70)
    print("  TEST: Swap type-7 resource index (Goblin <-> Bat)")
    print("  Keep: L values, R values, anim, 8-byte records, 96-byte entries")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    # Verify the entries are what we expect
    print("\n--- BEFORE ---")
    for name, addr in [("Goblin", TYPE7_GOBLIN), ("Shaman", TYPE7_SHAMAN), ("Bat", TYPE7_BAT)]:
        entry = data[addr:addr+8]
        off_val = int.from_bytes(entry[0:4], 'little')
        type_val = entry[4]
        idx_val = entry[5]
        slot_val = entry[6]
        print(f"  {name:8s} at 0x{addr:X}: off=0x{off_val:04X} type={type_val} idx=0x{idx_val:02X} slot={slot_val}")
        assert type_val == 7, f"Expected type=7, got {type_val}"

    # Verify idx values
    goblin_idx = data[TYPE7_GOBLIN + IDX_OFFSET]
    bat_idx = data[TYPE7_BAT + IDX_OFFSET]
    print(f"\n  Goblin idx = 0x{goblin_idx:02X}, Bat idx = 0x{bat_idx:02X}")
    assert goblin_idx == 0x10, f"Expected Goblin idx=0x10, got 0x{goblin_idx:02X}"
    assert bat_idx == 0x12, f"Expected Bat idx=0x12, got 0x{bat_idx:02X}"

    # Swap idx values
    print("\n  [Swapping type-7 idx: Goblin 0x10 <-> Bat 0x12]")
    data[TYPE7_GOBLIN + IDX_OFFSET] = bat_idx    # Goblin slot gets Bat idx
    data[TYPE7_BAT + IDX_OFFSET] = goblin_idx     # Bat slot gets Goblin idx

    # Show after
    print("\n--- AFTER ---")
    for name, addr in [("Goblin", TYPE7_GOBLIN), ("Shaman", TYPE7_SHAMAN), ("Bat", TYPE7_BAT)]:
        entry = data[addr:addr+8]
        off_val = int.from_bytes(entry[0:4], 'little')
        type_val = entry[4]
        idx_val = entry[5]
        slot_val = entry[6]
        print(f"  {name:8s} at 0x{addr:X}: off=0x{off_val:04X} type={type_val} idx=0x{idx_val:02X} slot={slot_val}")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print("\n" + "=" * 70)
    print("  Expected results:")
    print("  Slot 0 (Goblin model): should behave like Bat (fly? swoop?)")
    print("  Slot 1 (Shaman model): unchanged")
    print("  Slot 2 (Bat model):    should behave like Goblin (ground? arrows?)")
    print("")
    print("  If CRASH: the resource idx might also control texture loading,")
    print("  and swapping breaks the association. Would need to also swap")
    print("  texrefs or the offset field.")
    print("=" * 70)


if __name__ == '__main__':
    main()
