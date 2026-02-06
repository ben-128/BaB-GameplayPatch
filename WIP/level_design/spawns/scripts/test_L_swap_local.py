#!/usr/bin/env python3
"""
TEST: Does L control BOTH AI and 3D model (when model is loaded)?

Previous test: L=14 (Ogre from Floor 7) -> AI broke, mesh unchanged.
Hypothesis: Ogre mesh wasn't loaded on Floor 1, so mesh couldn't change.

New test: SWAP L values between Floor 1 monsters (all loaded on Floor 1):
  Goblin (slot 0):  L=0 -> L=3 (Bat's L)
  Shaman (slot 1):  L=1 -> L=0 (Goblin's L)
  Bat (slot 2):     L=3 -> L=1 (Shaman's L)

If L controls both AI and mesh:
  -> Slot 0: Bat mesh+AI, but named "Lv20.Goblin" with Goblin stats
  -> Slot 1: Goblin mesh+AI, but named "Goblin-Shaman" with Shaman stats
  -> Slot 2: Shaman mesh+AI, but named "Giant-Bat" with Bat stats

If L only controls AI (not mesh):
  -> Normal meshes, but AI swapped (Goblin behaves like Bat, etc.)
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Assignment entries for Cavern Floor 1 Area 1
# AI entries (flag 0x00) are at:
# 0xF7A964: [00, 00, 00, 00]  slot=0, L=0 (Goblin AI)
# 0xF7A96C: [01, 01, 00, 00]  slot=1, L=1 (Shaman AI)
# 0xF7A974: [02, 03, 00, 00]  slot=2, L=3 (Bat AI)

AI_ENTRIES = [
    (0xF7A964 + 1, 0, 3),   # slot 0: L=0 -> L=3 (Bat)
    (0xF7A96C + 1, 1, 0),   # slot 1: L=1 -> L=0 (Goblin)
    (0xF7A974 + 1, 3, 1),   # slot 2: L=3 -> L=1 (Shaman)
]

GROUP_OFFSET = 0xF7A97C


def main():
    print("=" * 70)
    print("  TEST: Swap L values between Floor 1 monsters")
    print("  (all models are loaded on Floor 1)")
    print("=" * 70)
    print()

    data = bytearray(BLAZE_SRC.read_bytes())

    # Show and patch
    print("--- Swapping AI (L) entries ---")
    for byte_off, old_l, new_l in AI_ENTRIES:
        assert data[byte_off] == old_l, f"Expected L={old_l} at 0x{byte_off:X}, got {data[byte_off]}"
        slot_off = byte_off - 1
        slot = data[slot_off]
        name_off = GROUP_OFFSET + slot * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        data[byte_off] = new_l
        print(f"  Slot {slot} ({name}): L={old_l} -> L={new_l}")

    # Show full entries
    print()
    print("--- Patched assignment entries ---")
    ENTRIES_BASE = 0xF7A964
    for i in range(3):
        ai_off = ENTRIES_BASE + i * 8
        model_off = ENTRIES_BASE + i * 8 + 4
        ai_e = data[ai_off:ai_off + 4]
        mod_e = data[model_off:model_off + 4]
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii')
        print(f"  Slot {i} '{name}': AI=[{ai_e.hex()}] L={ai_e[1]} | Model=[{mod_e.hex()}] R={mod_e[1]}")

    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print()
    print("=" * 70)
    print("  SI L CONTROLE AI + MESH (avec modeles charges):")
    print("    -> Slot 0 'Goblin': ressemble a Giant-Bat, vol de Bat")
    print("    -> Slot 1 'Shaman': ressemble a Goblin, marche de Goblin")
    print("    -> Slot 2 'Bat':    ressemble a Shaman, cast de Shaman")
    print()
    print("  SI L CONTROLE SEULEMENT AI:")
    print("    -> Meshes normaux, AI swappee")
    print("    -> Goblin vole comme Bat, Bat marche comme Shaman, etc.")
    print("=" * 70)


if __name__ == '__main__':
    main()
