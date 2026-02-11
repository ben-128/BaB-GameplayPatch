# -*- coding: cp1252 -*-
"""
Freeze test v2 - Test EXACT offset found by pattern search.

Creates a minimal test patch with infinite loop at 0x0092BF74.
This offset is 100% confirmed to be in Cavern overlay range.

If game freezes on combat start in Cavern F1 → code executes, we can patch!
If no freeze → code is dead/unused, need alternate approach.
"""

import struct
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
BLAZE_CLEAN = PROJECT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_TEST = PROJECT_DIR / "output" / "BLAZE.ALL"
BIN_CLEAN = PROJECT_DIR / "Blaze  Blade - Eternal Quest (Europe).bin"
BIN_TEST = PROJECT_DIR / "output" / "Blaze & Blade - Patched.bin"

# LBA locations from memory
BLAZE_LBA1 = 163167
BLAZE_LBA2 = 185765

def mips_beq_infinite():
    """beq $zero, $zero, -1 (infinite loop)"""
    # offset = -1 word = -4 bytes, but in branch instruction units (word offset)
    # beq encoding: 0x04 << 26 | rs << 21 | rt << 16 | offset (signed 16-bit)
    # beq $zero, $zero, offset = 0x1000FFFF for offset=-1
    return 0x1000FFFF

def inject_blaze_to_bin(blaze_path, bin_path):
    """Inject BLAZE.ALL into BIN at 2 LBA locations."""
    with open(blaze_path, 'rb') as f:
        blaze_data = f.read()

    # Ensure BIN file exists
    if not Path(bin_path).exists():
        print(f"  ERROR: BIN file not found: {bin_path}")
        return False

    with open(bin_path, 'r+b') as f:
        for lba in [BLAZE_LBA1, BLAZE_LBA2]:
            offset = 0
            while offset < len(blaze_data):
                chunk_size = min(2048, len(blaze_data) - offset)
                chunk = blaze_data[offset:offset + chunk_size]

                sector_offset = (lba * 2352) + 24 + (offset // 2048) * 2352
                f.seek(sector_offset)
                f.write(chunk)

                offset += chunk_size

    print(f"  Injected {len(blaze_data):,} bytes to BIN at LBA {BLAZE_LBA1} and {BLAZE_LBA2}")
    return True

def main():
    print("=" * 80)
    print("FREEZE TEST v2 - Exact Offset (0x0092BF74)")
    print("=" * 80)
    print()

    # Step 1: Check if BLAZE.ALL already exists in output (from build pipeline)
    if BLAZE_TEST.exists():
        print("[1/4] Using existing BLAZE.ALL from build pipeline...")
    else:
        print("[1/4] Copying clean BLAZE.ALL...")
        shutil.copy2(BLAZE_CLEAN, BLAZE_TEST)

    # Step 2: Check if BIN already exists
    if BIN_TEST.exists():
        print("[2/4] Using existing BIN from build pipeline...")
    else:
        print("[2/4] Copying clean BIN...")
        shutil.copy2(BIN_CLEAN, BIN_TEST)

    # Step 2: Patch BLAZE.ALL with freeze
    print("[3/4] Patching BLAZE.ALL with infinite loop...")
    with open(BLAZE_TEST, 'r+b') as f:
        offset = 0x0092BF74
        old_word = struct.unpack_from('<I', f.read(len(f.read())), offset)[0]
        f.seek(0)
        data = bytearray(f.read())
        old = struct.unpack_from('<I', data, offset)[0]
        new = mips_beq_infinite()

        print(f"  Offset: 0x{offset:08X}")
        print(f"  Old:    0x{old:08X} (ori $v0, $zero, 0x0001)")
        print(f"  New:    0x{new:08X} (beq $zero, $zero, -1)")

        struct.pack_into('<I', data, offset, new)
        f.seek(0)
        f.write(data)

    # Step 3: Inject into BIN
    print("[4/4] Injecting patched BLAZE.ALL into BIN...")
    if not inject_blaze_to_bin(BLAZE_TEST, BIN_TEST):
        print()
        print("=" * 80)
        print("ERROR: Injection failed!")
        print("=" * 80)
        return 1

    print()
    print("=" * 80)
    print("TEST READY")
    print("=" * 80)
    print()
    print("OUTPUT: output/Blaze & Blade - Patched.bin")
    print()
    print("TEST PROCEDURE:")
    print("  1. Load patched BIN in emulator")
    print("  2. Start new game or load save")
    print("  3. Go to Cavern of Death Floor 1")
    print("  4. Walk until combat triggers")
    print()
    print("EXPECTED RESULTS:")
    print("  - If game FREEZES during combat start → CODE EXECUTES ✅")
    print("    → We can patch the bitfield init!")
    print()
    print("  - If game runs normally → CODE IS DEAD ❌")
    print("    → Need to find alternate approach (see MONSTER_SPELL_RESEARCH.md)")
    print()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
