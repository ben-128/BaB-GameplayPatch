#!/usr/bin/env python3
"""
TEST: Does the formation pair L value control the monster visual/model?

Test on Cavern of Death, Floor 1, Area 1:
  Original: Lv20.Goblin (L=0), Goblin-Shaman (L=1), Giant-Bat (L=3)
  Patched:  All 3 slots get L=14 (Ogre visual from Floor 7)

Names/stats are kept UNCHANGED so we can verify:
  - If L controls visual: 3 Ogres named Lv20.Goblin, Goblin-Shaman, Giant-Bat
  - If L does NOT control: still Goblin, Shaman, Bat visuals unchanged

Run: py -3 test_visual_link.py
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

# Formation pairs: 3*8 = 24 bytes before the group
PAIR_BASE = GROUP_OFFSET - NUM_MONSTERS * 8  # 0xF7A964

# Ogre's L value in Cavern of Death (from Floor 7 data)
OGRE_L = 14


def main():
    print("=" * 70)
    print("  TEST: Change all Floor 1 visuals to Ogre (L=14)")
    print("=" * 70)
    print()

    print(f"Reading {BLAZE_SRC}...")
    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  Size: {len(data):,} bytes")

    # Show current state
    print()
    print("--- Current state (Cavern Floor 1, Area 1) ---")
    for i in range(NUM_MONSTERS):
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        pair_off = PAIR_BASE + i * 8
        l_val = data[pair_off + 1]
        r_val = data[pair_off + 5]
        hp = struct.unpack_from('<H', data, name_off + 16 + 4)[0]
        print(f"  Slot {i}: '{name}' HP={hp} | L={l_val} R={r_val} | pair={data[pair_off:pair_off+8].hex()}")

    # Patch all 3 L values to Ogre (14)
    print()
    print("--- Patching L values ---")
    for i in range(NUM_MONSTERS):
        pair_off = PAIR_BASE + i * 8
        l_byte_off = pair_off + 1
        old_l = data[l_byte_off]
        data[l_byte_off] = OGRE_L
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        print(f"  Slot {i} ({name}): L={old_l} -> L={OGRE_L} (Ogre)")

    # Show patched state
    print()
    print("--- Patched state ---")
    for i in range(NUM_MONSTERS):
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        pair_off = PAIR_BASE + i * 8
        l_val = data[pair_off + 1]
        r_val = data[pair_off + 5]
        print(f"  Slot {i}: '{name}' | L={l_val} R={r_val} | pair={data[pair_off:pair_off+8].hex()}")

    # Save
    print()
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"[SAVED] {BLAZE_OUT}")

    print()
    print("=" * 70)
    print("  EN JEU - Cavern of Death, Floor 1:")
    print()
    print("  SI L CONTROLE LE VISUEL:")
    print("    -> 3 gros OGRES (modele Floor 7)")
    print("    -> Noms: Lv20.Goblin, Goblin-Shaman, Giant-Bat (via Identify)")
    print("    -> Stats inchangees (HP faibles de Floor 1)")
    print()
    print("  SI L NE CONTROLE PAS:")
    print("    -> Toujours Goblin, Shaman, Bat visuellement")
    print()
    print("  SI CRASH:")
    print("    -> Le modele Ogre n'est pas charge au Floor 1")
    print("    -> Il faudra tester avec un L d'un monstre du Floor 1")
    print("=" * 70)


if __name__ == '__main__':
    main()
