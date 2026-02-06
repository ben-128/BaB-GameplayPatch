#!/usr/bin/env python3
"""
TEST 11: Swap ONLY L values (2-way, Goblin<->Bat), NO anim swap.

Critical insight:
  Test 5 (L only, 3-way rotation) -> appeared to swap EVERYTHING (model+AI)
  Test 6 (L + anim swap, 2-way)   -> model swapped but AI did NOT

The ONLY difference: test 6 also swapped animation bytes.
Hypothesis: L DOES control AI, but the anim byte swap in test 6
broke the AI association. The anim table might be what the game
uses to resolve AI behavior from the model reference.

This test: 2-way L swap (Goblin<->Bat) WITHOUT anim swap.
  Test 5 didn't crash with L-only, so this should be safe.

  Slot 0: L=0 -> L=3 (Goblin gets Bat's L)
  Slot 2: L=3 -> L=0 (Bat gets Goblin's L)
  Animation bytes: UNCHANGED (stay at original slot positions)

If AI swaps: L controls AI, and anim swap was breaking it!
If AI stays: L doesn't control AI (test 5 was misinterpreted)
If crash: 2-way L-only is unstable (test 5's 3-way was a lucky case)
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# L value byte positions (byte[1] of each L entry)
L_SLOT_0 = 0xF7A964 + 1  # currently L=0 (Goblin)
L_SLOT_2 = 0xF7A974 + 1  # currently L=3 (Bat)

GROUP_OFFSET = 0xF7A97C


def main():
    print("=" * 70)
    print("  TEST 11: L-only swap (Goblin <-> Bat), NO anim swap")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    # Show before
    print("\n--- BEFORE ---")
    for i in range(3):
        entry_off = GROUP_OFFSET + i * 96
        name = data[entry_off:entry_off+16].split(b'\x00')[0].decode('ascii')
        l_off = 0xF7A964 + i * 8 + 1
        print(f"  Slot {i} ({name}): L={data[l_off]}")

    # Swap L values only
    gob_l = data[L_SLOT_0]
    bat_l = data[L_SLOT_2]
    print(f"\n  [Swapping L only: slot 0 ({gob_l}) <-> slot 2 ({bat_l})]")
    data[L_SLOT_0] = bat_l
    data[L_SLOT_2] = gob_l

    # Show after
    print("\n--- AFTER ---")
    for i in range(3):
        entry_off = GROUP_OFFSET + i * 96
        name = data[entry_off:entry_off+16].split(b'\x00')[0].decode('ascii')
        l_off = 0xF7A964 + i * 8 + 1
        print(f"  Slot {i} ({name}): L={data[l_off]}")

    # Verify anim bytes are UNCHANGED
    ANIM_START = 0xF7A90C
    anim_data = data[ANIM_START:ANIM_START+40]
    print(f"\n  Anim table (UNCHANGED): [{anim_data.hex()}]")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print("\n" + "=" * 70)
    print("  Slot 0 'Goblin': L=3 (Bat model), anim bytes = original Goblin")
    print("  Slot 1 'Shaman': unchanged")
    print("  Slot 2 'Bat':    L=0 (Goblin model), anim bytes = original Bat")
    print("")
    print("  WATCH FOR:")
    print("  - If Goblin-slot shows Bat model AND Bat behavior -> L = AI!")
    print("  - If Goblin-slot shows Bat model but Goblin behavior -> L != AI")
    print("  - If crash -> 2-way L-only unstable")
    print("=" * 70)


if __name__ == '__main__':
    main()
