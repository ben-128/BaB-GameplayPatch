#!/usr/bin/env python3
"""
TEST: Swap ONLY R values between Goblin (slot 0) and Bat (slot 2).

Key insight: Test 5 swapped L+R+anim -> AI swapped.
             Test 6 swapped L+anim only -> AI did NOT swap.
             The only difference: R was swapped in Test 5, not in Test 6.
             -> R likely controls AI!

Test 2 (R=4 for all) showed "no visible change" but the tester may not
have checked behavior specifically (only visuals).

Assignment entries for Cavern F1 Area 1 (paired: L then R per slot):
  0xF7A964: [00 00 00 00] L slot=0 val=0  (Goblin)
  0xF7A968: [00 02 00 40] R slot=0 val=2  (Goblin)
  0xF7A96C: [01 01 00 00] L slot=1 val=1  (Shaman)
  0xF7A970: [01 03 00 40] R slot=1 val=3  (Shaman)
  0xF7A974: [02 03 00 00] L slot=2 val=3  (Bat)
  0xF7A978: [02 04 00 40] R slot=2 val=4  (Bat)

This test: swap R_val only (byte[1] of R entries)
  Slot 0 R: 2 -> 4  (Goblin gets Bat's R)
  Slot 2 R: 4 -> 2  (Bat gets Goblin's R)
  Everything else unchanged (L, anim, 8-byte, type-7, 96-byte).

Expected if R=AI:
  Slot 0 (Goblin model): Bat behavior (flying? swooping?)
  Slot 2 (Bat model): Goblin behavior (ground? arrows?)
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# R entry addresses (byte[1] = R_val)
R_GOBLIN = 0xF7A968  # [00 02 00 40]
R_SHAMAN = 0xF7A970  # [01 03 00 40]
R_BAT    = 0xF7A978  # [02 04 00 40]

VAL_OFFSET = 1  # byte[1] is the value


def show_entries(data, label):
    print(f"\n--- {label} ---")
    assign_base = 0xF7A964
    names = ["Goblin", "Shaman", "Bat"]
    for i in range(3):
        off = assign_base + i * 8
        l_entry = data[off:off+4]
        r_entry = data[off+4:off+8]
        print(f"  Slot {i} ({names[i]:8s}): "
              f"L=[{l_entry.hex()}] val={l_entry[1]:2d} | "
              f"R=[{r_entry.hex()}] val={r_entry[1]:2d}")


def main():
    print("=" * 70)
    print("  TEST: Swap R values ONLY (Goblin <-> Bat)")
    print("  Keep: L, anim, 8-byte records, type-7, 96-byte entries")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    show_entries(data, "BEFORE")

    # Verify R entries
    assert data[R_GOBLIN+3] == 0x40, "Not an R entry (Goblin)"
    assert data[R_BAT+3] == 0x40, "Not an R entry (Bat)"

    gob_r = data[R_GOBLIN + VAL_OFFSET]
    bat_r = data[R_BAT + VAL_OFFSET]
    print(f"\n  Goblin R_val = {gob_r}, Bat R_val = {bat_r}")

    # Swap R values
    print(f"  [Swapping R: Goblin {gob_r} <-> Bat {bat_r}]")
    data[R_GOBLIN + VAL_OFFSET] = bat_r
    data[R_BAT + VAL_OFFSET] = gob_r

    show_entries(data, "AFTER")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print("\n" + "=" * 70)
    print("  Slot 0 (Goblin model) now has R=4 (Bat's R)")
    print("  Slot 2 (Bat model) now has R=2 (Goblin's R)")
    print("")
    print("  Watch for BEHAVIOR changes (not visuals):")
    print("  - Do Goblins fly/swoop? Do Bats walk/shoot arrows?")
    print("=" * 70)


if __name__ == '__main__':
    main()
