#!/usr/bin/env python3
"""
Test AI/behavior assignment by swapping specific fields between monsters.

Creates test patches in BLAZE.ALL to swap data between Goblin (slot 0) and
Giant-Bat (slot 2) in Cavern F1 Area1. The user fights both to observe
whether AI/abilities change.

Test methodology:
- ONLY swap one data group per test
- Keep L assignment (model) the SAME
- Observe: does Goblin (with its own model) now behave like a Bat?
  Does Bat (with its own model) now behave like a Goblin?

96-byte stat entry layout (from hex analysis):
  +0x00..0x0F: Name (16 bytes, ASCII null-terminated)
  +0x10..0x11: u16 stat_a (Gob=20, Sha=24, Bat=15)
  +0x12..0x13: u16 stat_b (Gob=2, Sha=3, Bat=4)
  +0x14..0x15: u16 stat_c (Gob=38, Sha=35, Bat=36)
  +0x16..0x17: u16 stat_d (Gob=8, Sha=70, Bat=2)
  +0x18..0x19: u16 stat_e (Gob=20, Sha=24, Bat=15)
  +0x1A..0x1B: u16 stat_f (Gob=0, Sha=0, Bat=2)
  +0x1C..0x1D: u16 stat_g (Gob=60, Sha=50, Bat=30)
  +0x1E..0x1F: u16 stat_h (Gob=110, Sha=85, Bat=35)
  +0x20..0x21: u16 stat_i (Gob=30, Sha=40, Bat=40)
  +0x22..0x23: u16 stat_j (Gob=74, Sha=66, Bat=66)
  --- CANDIDATE AI BYTES (identical for Goblin & Shaman, different for Bat) ---
  +0x24: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x25: byte (Gob=0x0A, Sha=0x0A, Bat=0x02) <-- DIFFERS
  +0x26: byte (Gob=0x00, Sha=0x00, Bat=0x10) <-- DIFFERS
  +0x27: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x28: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x29: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x2A: byte (Gob=0x06, Sha=0x06, Bat=0x00) <-- DIFFERS
  +0x2B: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x2C: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x2D: byte (Gob=0x03, Sha=0x03, Bat=0x04) <-- DIFFERS
  +0x2E: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  +0x2F: byte (Gob=0x00, Sha=0x00, Bat=0x00)
  --- DEFENSE STATS ---
  +0x30..0x3F: 8 u16 defense values
  +0x40..0x5F: all zeros (padding)
"""

import struct
import subprocess
import shutil
from pathlib import Path

PROJECT_DIR = Path(r"D:\projets\Bab_Gameplay_Patch")
BLAZE_SRC = PROJECT_DIR / "output" / "BLAZE.ALL"  # Read from post-build (already patched)
BLAZE_DST = PROJECT_DIR / "output" / "BLAZE.ALL"  # Write back in-place

# Cavern F1 Area1 stat entries in BLAZE.ALL
STAT_BASE = 0xF7A97C
STAT_SIZE = 96

# Monster slot offsets
GOBLIN_OFF = STAT_BASE + 0 * STAT_SIZE   # 0xF7A97C
SHAMAN_OFF = STAT_BASE + 1 * STAT_SIZE   # 0xF7A9DC
BAT_OFF    = STAT_BASE + 2 * STAT_SIZE   # 0xF7AA3C


def read_stat(data, off):
    """Read a 96-byte stat entry."""
    return bytearray(data[off:off+STAT_SIZE])


def show_stat_comparison(data):
    """Show the 3 stat entries side by side."""
    names = ["Goblin", "Shaman", "Bat"]
    offsets = [GOBLIN_OFF, SHAMAN_OFF, BAT_OFF]
    entries = [read_stat(data, off) for off in offsets]

    print("\n  96-byte stat entry comparison (hex):")
    print(f"  {'Offset':<8s} {'Goblin':<50s} {'Shaman':<50s} {'Bat':<50s}")
    for row in range(6):
        base = row * 16
        for i, ent in enumerate(entries):
            hex_str = ' '.join(f"{b:02X}" for b in ent[base:base+16])
            if i == 0:
                print(f"  +0x{base:02X}:  {hex_str:<50s}", end="")
            else:
                print(f" {hex_str:<50s}", end="")
        print()

    # Show field-by-field with differ markers
    print("\n  Field-by-field comparison:")
    print(f"  {'Offset':<8s} {'Size':<5s} {'Goblin':<12s} {'Shaman':<12s} {'Bat':<12s} {'Same?':<6s} Description")
    fields = [
        (0x10, 2, "stat_a"),
        (0x12, 2, "stat_b"),
        (0x14, 2, "stat_c"),
        (0x16, 2, "stat_d"),
        (0x18, 2, "stat_e"),
        (0x1A, 2, "stat_f"),
        (0x1C, 2, "stat_g"),
        (0x1E, 2, "stat_h"),
        (0x20, 2, "stat_i"),
        (0x22, 2, "stat_j"),
        (0x24, 1, "unk_24"),
        (0x25, 1, "unk_25"),
        (0x26, 1, "unk_26"),
        (0x27, 1, "unk_27"),
        (0x28, 1, "unk_28"),
        (0x29, 1, "unk_29"),
        (0x2A, 1, "unk_2A"),
        (0x2B, 1, "unk_2B"),
        (0x2C, 1, "unk_2C"),
        (0x2D, 1, "unk_2D"),
        (0x2E, 1, "unk_2E"),
        (0x2F, 1, "unk_2F"),
        (0x30, 2, "def_0"),
        (0x32, 2, "def_1"),
        (0x34, 2, "def_2"),
        (0x36, 2, "def_3"),
        (0x38, 2, "def_4"),
        (0x3A, 2, "def_5"),
        (0x3C, 2, "def_6"),
        (0x3E, 2, "def_7"),
    ]

    for off, size, desc in fields:
        vals = []
        for ent in entries:
            if size == 2:
                v = struct.unpack_from('<H', ent, off)[0]
                vals.append(f"{v}")
            else:
                v = ent[off]
                vals.append(f"0x{v:02X}")
        same = "YES" if len(set(vals)) == 1 else "***"
        goblin_shaman_same = vals[0] == vals[1]
        bat_diff = vals[2] != vals[0]
        note = ""
        if goblin_shaman_same and bat_diff:
            note = " <-- Gob=Sha, Bat differs (AI candidate!)"
        elif not goblin_shaman_same and bat_diff:
            note = " <-- All different"
        print(f"  +0x{off:02X}   {size}B    {vals[0]:<12s} {vals[1]:<12s} {vals[2]:<12s} {same:<6s} {desc}{note}")


def apply_test(test_name, description, swaps):
    """
    Apply a test by swapping specific bytes in BLAZE.ALL.
    swaps = list of (src_off, dst_off, length) tuples
    """
    print(f"\n{'='*80}")
    print(f"  TEST: {test_name}")
    print(f"  {description}")
    print(f"{'='*80}")

    data = bytearray(BLAZE_SRC.read_bytes())

    for src_off, dst_off, length in swaps:
        orig_src = bytes(data[src_off:src_off+length])
        orig_dst = bytes(data[dst_off:dst_off+length])
        data[src_off:src_off+length] = orig_dst
        data[dst_off:dst_off+length] = orig_src
        print(f"  Swapped {length} bytes: 0x{src_off:08X} <-> 0x{dst_off:08X}")
        print(f"    Was: [{' '.join(f'{b:02X}' for b in orig_src[:32])}]{'...' if length > 32 else ''}")
        print(f"    Now: [{' '.join(f'{b:02X}' for b in orig_dst[:32])}]{'...' if length > 32 else ''}")

    BLAZE_DST.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_DST.write_bytes(data)
    print(f"\n  Output: {BLAZE_DST}")

    # Re-inject into BIN so the game actually uses the modified data
    print(f"\n  Re-injecting BLAZE.ALL into BIN...")
    result = subprocess.run(
        ["py", "-3", str(PROJECT_DIR / "patch_blaze_all.py")],
        cwd=str(PROJECT_DIR),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  [ERROR] BIN injection failed!")
        print(result.stderr)
    else:
        print(f"  [OK] BIN updated with test patch.")
        print(f"\n  Fight in Cavern F1 Area1. Compare Goblin and Bat AI/abilities vs original.")


def main():
    import sys

    if not BLAZE_SRC.exists():
        print(f"  [ERROR] {BLAZE_SRC} not found!")
        print(f"  Run build_gameplay_patch.bat FIRST, then run this script.")
        return

    data = bytearray(BLAZE_SRC.read_bytes())

    print("=" * 80)
    print("  MONSTER AI SWAP TEST GENERATOR")
    print("  Cavern F1 Area1: Goblin (slot 0) vs Giant-Bat (slot 2)")
    print("  NOTE: Run build_gameplay_patch.bat FIRST, then this script.")
    print("=" * 80)

    show_stat_comparison(data)

    # Define test options
    tests = {
        '1': (
            "FULL stat swap (96 bytes)",
            "Swap the ENTIRE 96-byte stat entry between Goblin and Bat.\n"
            "  This changes name, ALL stats, unknown bytes, defenses - everything.\n"
            "  If AI changes: the AI field is SOMEWHERE in the 96-byte entry.\n"
            "  If AI stays same: AI is NOT in the 96-byte entry at all.",
            [(GOBLIN_OFF, BAT_OFF, STAT_SIZE)]
        ),
        '2': (
            "Stats + unknown bytes swap (bytes 0x10-0x3F, NO name)",
            "Swap everything except the name (stat fields + unknown bytes + defenses).\n"
            "  Same test as #1 but keeps original names for identification.",
            [(GOBLIN_OFF + 0x10, BAT_OFF + 0x10, 0x30)]
        ),
        '3': (
            "Unknown bytes ONLY (stat+0x24..0x2F)",
            "Swap ONLY the 12 unknown bytes between Goblin and Bat.\n"
            "  These bytes are identical for Goblin & Shaman but differ for Bat.\n"
            "  Key candidates: +0x25 (0x0A vs 0x02), +0x26 (0x00 vs 0x10),\n"
            "                  +0x2A (0x06 vs 0x00), +0x2D (0x03 vs 0x04).\n"
            "  If AI changes: the AI field is in this 12-byte region!",
            [(GOBLIN_OFF + 0x24, BAT_OFF + 0x24, 12)]
        ),
        '4': (
            "Single byte swap: stat+0x2A only",
            "Swap ONLY byte +0x2A (Goblin=0x06, Bat=0x00).\n"
            "  Previously hypothesized as ability index (Goblin=6 -> Type6[6]=Fire Breath).\n"
            "  If AI changes with just this byte: this IS the AI index!",
            [(GOBLIN_OFF + 0x2A, BAT_OFF + 0x2A, 1)]
        ),
        '5': (
            "Single byte swap: stat+0x2D only",
            "Swap ONLY byte +0x2D (Goblin=0x03, Bat=0x04).\n"
            "  Another candidate for AI index.",
            [(GOBLIN_OFF + 0x2D, BAT_OFF + 0x2D, 1)]
        ),
        '6': (
            "Two bytes: stat+0x25 and stat+0x26",
            "Swap bytes +0x25 (0x0A vs 0x02) and +0x26 (0x00 vs 0x10).\n"
            "  These differ between Goblin and Bat but not between Goblin and Shaman.",
            [(GOBLIN_OFF + 0x25, BAT_OFF + 0x25, 2)]
        ),
        '7': (
            "Defense stats ONLY (stat+0x30..0x3F)",
            "Swap ONLY the 16 defense stat bytes.\n"
            "  Control test: defenses should NOT affect AI.\n"
            "  Use this to verify the test methodology works.",
            [(GOBLIN_OFF + 0x30, BAT_OFF + 0x30, 16)]
        ),
    }

    print("\n\n  Available tests:")
    for key in sorted(tests.keys()):
        name, desc, _ = tests[key]
        print(f"\n  [{key}] {name}")
        for line in desc.split('\n'):
            print(f"      {line.strip()}")

    print("\n  RECOMMENDED order: 1 -> 3 -> 4 or 5")
    print("  Test 1 first: if AI doesn't change, no point testing 3-5.")
    print("  If test 1 changes AI, use test 3 to narrow down.")
    print("  If test 3 changes AI, use test 4 or 5 to isolate the exact byte.")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("\n  Enter test number (1-7): ", end="")
        choice = input().strip()

    if choice not in tests:
        print(f"  Invalid choice: {choice}")
        return

    name, desc, swaps = tests[choice]
    apply_test(name, desc, swaps)


if __name__ == '__main__':
    main()
