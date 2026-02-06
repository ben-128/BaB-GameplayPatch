#!/usr/bin/env python3
"""
TEST: Does the R value (flag 0x40 entries) control the monster visual/model?

Previous test: L values (flag 0x00) -> controls AI/behavior, NOT visual.
This test: R values (flag 0x40) -> should control visual/model.

Cavern of Death, Floor 1, Area 1:
  Original entries (6 x 4 bytes at 0xF7A964):
    [00,00,00,00] monster 0 -> AI #0   (Goblin AI)
    [00,02,00,40] monster 0 -> Model #2 (Goblin model)
    [01,01,00,00] monster 1 -> AI #1   (Shaman AI)
    [01,03,00,40] monster 1 -> Model #3 (Shaman model)
    [02,03,00,00] monster 2 -> AI #3   (Bat AI)
    [02,04,00,40] monster 2 -> Model #4 (Bat model)

  Patch: Change ALL model entries to #4 (Giant-Bat model)
    monster 0: Model #2 -> #4 (should look like Giant-Bat)
    monster 1: Model #3 -> #4 (should look like Giant-Bat)
    monster 2: Model #4 -> #4 (stays as Giant-Bat)

  AI entries are LEFT UNCHANGED.

Expected results:
  IF R controls visual:
    -> 3 Giant-Bats on screen
    -> Names still Lv20.Goblin, Goblin-Shaman, Giant-Bat
    -> AI behavior normal (Goblin walks, Shaman casts, Bat flies)

  IF R does NOT control visual:
    -> Normal Goblin, Shaman, Bat visuals
    -> Possibly broken behavior

Run: py -3 test_visual_R.py
Then rebuild the BIN.
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern of Death, Floor 1, Area 1
GROUP_OFFSET = 0xF7A97C
NUM_MONSTERS = 3

# The 6 entries (3 pairs of [flag0x00][flag0x40]) are at:
# 0xF7A964: 00 00 00 00  <- AI entry for slot 0
# 0xF7A968: 00 02 00 40  <- Model entry for slot 0 (R=2)
# 0xF7A96C: 01 01 00 00  <- AI entry for slot 1
# 0xF7A970: 01 03 00 40  <- Model entry for slot 1 (R=3)
# 0xF7A974: 02 03 00 00  <- AI entry for slot 2
# 0xF7A978: 02 04 00 40  <- Model entry for slot 2 (R=4)

ENTRIES_BASE = 0xF7A964

# Target model: #4 = Giant-Bat model on this floor
TARGET_MODEL = 4

# Model entry offsets (the 0x40-flag entries)
# Each pair is 8 bytes: [AI 4 bytes][Model 4 bytes]
# Model entries are at base + 4, base + 12, base + 20
MODEL_ENTRIES = [
    ENTRIES_BASE + 4,   # 0xF7A968: slot 0 model
    ENTRIES_BASE + 12,  # 0xF7A970: slot 1 model
    ENTRIES_BASE + 20,  # 0xF7A978: slot 2 model
]


def main():
    print("=" * 70)
    print("  TEST: Change all Floor 1 models to Giant-Bat (R=4)")
    print("  (AI behavior entries are LEFT UNCHANGED)")
    print("=" * 70)
    print()

    print(f"Reading {BLAZE_SRC}...")
    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  Size: {len(data):,} bytes")

    # Show current state
    print()
    print("--- Current entries (Cavern Floor 1, Area 1) ---")
    for i in range(NUM_MONSTERS):
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')

        ai_off = ENTRIES_BASE + i * 8
        model_off = ENTRIES_BASE + i * 8 + 4

        ai_entry = data[ai_off:ai_off + 4]
        model_entry = data[model_off:model_off + 4]

        print(f"  Slot {i}: '{name}'")
        print(f"    AI entry:    [{ai_entry.hex()}] slot={ai_entry[0]} AI#{ai_entry[1]} flag=0x{ai_entry[3]:02X}")
        print(f"    Model entry: [{model_entry.hex()}] slot={model_entry[0]} Model#{model_entry[1]} flag=0x{model_entry[3]:02X}")

    # Verify flags are correct
    print()
    print("--- Verifying entry structure ---")
    ok = True
    for i in range(NUM_MONSTERS):
        ai_off = ENTRIES_BASE + i * 8
        model_off = ENTRIES_BASE + i * 8 + 4
        ai_flag = data[ai_off + 3]
        model_flag = data[model_off + 3]
        if ai_flag != 0x00:
            print(f"  WARNING: Slot {i} AI flag is 0x{ai_flag:02X}, expected 0x00")
            ok = False
        if model_flag != 0x40:
            print(f"  WARNING: Slot {i} Model flag is 0x{model_flag:02X}, expected 0x40")
            ok = False
    if ok:
        print("  OK - All flags match expected pattern (0x00=AI, 0x40=Model)")

    # Patch model entries
    print()
    print("--- Patching Model entries (R values) ---")
    for i in range(NUM_MONSTERS):
        model_off = MODEL_ENTRIES[i]
        old_model = data[model_off + 1]
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')

        data[model_off + 1] = TARGET_MODEL
        print(f"  Slot {i} ({name}): Model #{old_model} -> Model #{TARGET_MODEL} (Giant-Bat)")

    # Show patched state
    print()
    print("--- Patched entries ---")
    for i in range(NUM_MONSTERS):
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')

        ai_off = ENTRIES_BASE + i * 8
        model_off = ENTRIES_BASE + i * 8 + 4

        ai_entry = data[ai_off:ai_off + 4]
        model_entry = data[model_off:model_off + 4]

        print(f"  Slot {i}: '{name}'")
        print(f"    AI entry:    [{ai_entry.hex()}] slot={ai_entry[0]} AI#{ai_entry[1]} (UNCHANGED)")
        print(f"    Model entry: [{model_entry.hex()}] slot={model_entry[0]} Model#{model_entry[1]} (PATCHED)")

    # Save
    print()
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"[SAVED] {BLAZE_OUT}")

    print()
    print("=" * 70)
    print("  EN JEU - Cavern of Death, Floor 1:")
    print()
    print("  SI R CONTROLE LE VISUEL:")
    print("    -> 3 Giant-Bats (tous le meme modele chauve-souris)")
    print("    -> Noms: Lv20.Goblin, Goblin-Shaman, Giant-Bat")
    print("    -> Comportement normal (Goblin marche, Shaman cast, Bat vole)")
    print()
    print("  SI R NE CONTROLE PAS:")
    print("    -> Visuels normaux (Goblin, Shaman, Bat)")
    print("    -> Possible comportement casse")
    print("=" * 70)


if __name__ == '__main__':
    main()
