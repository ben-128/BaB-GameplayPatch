#!/usr/bin/env python3
"""
TEST: Full monster swap - swap ALL per-monster structures.

Previous test: swapping only L crashed because animation data didn't match.
This test: swap EVERYTHING per-monster between Goblin (slot 0) and Bat (slot 2).

Structures to swap for each monster slot:
1. Assignment entries: flag 0x00 (L/AI) + flag 0x40 (R/unknown)
2. 8-byte records: anim_offset + model_ref (texture)
3. Type-7 entries in script area: index + slot
4. 96-byte entries: KEEP ORIGINAL (names/stats stay)

Swap plan: Goblin (slot 0) <-> Bat (slot 2), Shaman (slot 1) stays.
  Slot 0 should look/behave like Bat but be named "Lv20.Goblin"
  Slot 2 should look/behave like Goblin but be named "Giant-Bat"
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# ---- Cavern Floor 1 Area 1 ----
GROUP_OFFSET = 0xF7A97C

# 1. Assignment entries (6 x 4 bytes at 0xF7A964)
#    Slot 0: AI=[00,00,00,00] Model=[00,02,00,40]
#    Slot 1: AI=[01,01,00,00] Model=[01,03,00,40]
#    Slot 2: AI=[02,03,00,00] Model=[02,04,00,40]
ASSIGN_BASE = 0xF7A964  # 3 pairs of 8 bytes

# 2. 8-byte records (animation + texture)
#    Record 0: [0C000000] [00000300]  (Goblin)
#    Record 1: [14000000] [00400400]  (Shaman)
#    Record 2: [1C000000] [00800500]  (Bat)
RECORD_BASE = 0xF7A934  # 3 records of 8 bytes

# 3. Type-7 entries in script area
#    0xF7ABE4: [0580] [07,10,00,00]  monster 0
#    0xF7ABEC: [0588] [07,11,01,00]  monster 1
#    0xF7ABF4: [0590] [07,12,02,00]  monster 2
TYPE7_BASE = 0xF7ABE4  # 3 entries of 8 bytes


def swap_bytes(data, off1, off2, length):
    """Swap 'length' bytes between off1 and off2."""
    tmp = bytes(data[off1:off1+length])
    data[off1:off1+length] = data[off2:off2+length]
    data[off2:off2+length] = tmp


def show_state(data, label):
    print(f"\n--- {label} ---")

    print("  Assignment entries:")
    for i in range(3):
        ai_off = ASSIGN_BASE + i * 8
        mod_off = ASSIGN_BASE + i * 8 + 4
        ai = data[ai_off:ai_off+4]
        mod = data[mod_off:mod_off+4]
        name_off = GROUP_OFFSET + i * 96
        name = data[name_off:name_off+16].split(b'\x00')[0].decode('ascii')
        print(f"    Slot {i} '{name}': AI=[{ai.hex()}] L={ai[1]} | Model=[{mod.hex()}] R={mod[1]}")

    print("  8-byte records:")
    for i in range(3):
        off = RECORD_BASE + i * 8
        anim = struct.unpack_from('<I', data, off)[0]
        texref = struct.unpack_from('<I', data, off+4)[0]
        print(f"    Record {i}: anim=0x{anim:04X} texref=0x{texref:08X} raw=[{data[off:off+8].hex()}]")

    print("  Type-7 entries:")
    for i in range(3):
        off = TYPE7_BASE + i * 8
        entry_off = struct.unpack_from('<I', data, off)[0]
        val = data[off+4:off+8]
        print(f"    Entry {i}: [0x{entry_off:04X}] [{val.hex()}] type={val[0]} idx=0x{val[1]:02X} slot={val[2]}")


def main():
    print("=" * 70)
    print("  TEST: Full swap Goblin (slot 0) <-> Bat (slot 2)")
    print("  Swapping: assignment entries + 8-byte records + type-7 entries")
    print("  NOT swapping: 96-byte entries (names/stats)")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    show_state(data, "BEFORE swap")

    # --- SWAP slot 0 <-> slot 2 ---

    # 1. Assignment entries: swap the full 8-byte pairs (AI + Model)
    #    Slot 0 pair at ASSIGN_BASE + 0*8 = ASSIGN_BASE
    #    Slot 2 pair at ASSIGN_BASE + 2*8 = ASSIGN_BASE + 16
    print("\n  [Swapping assignment entries...]")
    s0_ai = ASSIGN_BASE + 0 * 8
    s2_ai = ASSIGN_BASE + 2 * 8
    # Swap the L (AI param) bytes
    data[s0_ai + 1], data[s2_ai + 1] = data[s2_ai + 1], data[s0_ai + 1]
    # Swap the R (Model param) bytes
    s0_mod = s0_ai + 4
    s2_mod = s2_ai + 4
    data[s0_mod + 1], data[s2_mod + 1] = data[s2_mod + 1], data[s0_mod + 1]
    # Keep slot bytes unchanged (slot 0 stays 0, slot 2 stays 2)

    # 2. 8-byte records: swap the full records
    #    Record 0 at RECORD_BASE + 0*8
    #    Record 2 at RECORD_BASE + 2*8
    print("  [Swapping 8-byte records...]")
    swap_bytes(data, RECORD_BASE + 0*8, RECORD_BASE + 2*8, 8)

    # 3. Type-7 entries: swap the value bytes (keep offsets, swap type/idx/slot)
    #    Entry 0 value at TYPE7_BASE + 0*8 + 4
    #    Entry 2 value at TYPE7_BASE + 2*8 + 4
    print("  [Swapping type-7 entries...]")
    t0_val = TYPE7_BASE + 0*8 + 4
    t2_val = TYPE7_BASE + 2*8 + 4
    # Swap index byte (byte 1 of value)
    data[t0_val + 1], data[t2_val + 1] = data[t2_val + 1], data[t0_val + 1]
    # Keep slot bytes as-is (slot 0 stays 0, slot 2 stays 2)
    # Keep type byte as-is (both are 0x07)

    show_state(data, "AFTER swap")

    # Save
    print()
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"[SAVED] {BLAZE_OUT}")

    print()
    print("=" * 70)
    print("  ATTENDU:")
    print("    Slot 0: mesh=Bat, AI=Bat, anims=Bat, nom='Lv20.Goblin'")
    print("    Slot 1: inchange (Goblin-Shaman)")
    print("    Slot 2: mesh=Goblin, AI=Goblin, anims=Goblin, nom='Giant-Bat'")
    print()
    print("  SI CA CRASH ENCORE:")
    print("    -> Il manque encore un element a swapper")
    print("    -> Regarder la table d'animation bytes")
    print("=" * 70)


if __name__ == '__main__':
    main()
