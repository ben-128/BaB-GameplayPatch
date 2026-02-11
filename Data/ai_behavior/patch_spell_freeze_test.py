# -*- coding: cp1252 -*-
"""
Spell offset freeze test - patches BLAZE.ALL with infinite loop.

This is a DIAGNOSTIC tool to verify if offset 0x0092BF74 executes during
Cavern of Death combat. If the game freezes, the offset is correct and
we can implement the real per-monster spell assignment patch.

Usage: Called from build_gameplay_patch.bat when TEST_SPELL_FREEZE=1
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_DIR / "output" / "BLAZE.ALL"

def mips_beq_infinite():
    """beq $zero, $zero, -1 (infinite loop)"""
    return 0x1000FFFF

def main():
    print("=" * 80)
    print("SPELL OFFSET FREEZE TEST - BLAZE.ALL Patcher")
    print("=" * 80)
    print()
    print("WARNING: This patches BLAZE.ALL with an INFINITE LOOP.")
    print("         The game will FREEZE during Cavern of Death combat.")
    print("         This is ONLY for testing if offset 0x0092BF74 executes.")
    print()

    if not BLAZE_ALL.exists():
        print(f"ERROR: BLAZE.ALL not found at {BLAZE_ALL}")
        print("This script must run AFTER step 1 (copy clean BLAZE.ALL)")
        return 1

    # Patch BLAZE.ALL
    print("Patching BLAZE.ALL with freeze at offset 0x0092BF74...")

    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())

        offset = 0x0092BF74
        old = struct.unpack_from('<I', data, offset)[0]
        new = mips_beq_infinite()

        print(f"  Offset:     0x{offset:08X}")
        print(f"  Old instr:  0x{old:08X} (ori $v0, $zero, 0x0001)")
        print(f"  New instr:  0x{new:08X} (beq $zero, $zero, -1)")
        print(f"  RAM addr:   0x{offset + 0x7F739758:08X}")

        struct.pack_into('<I', data, offset, new)

        f.seek(0)
        f.write(data)

    print()
    print("[OK] BLAZE.ALL patched with freeze test")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Build will continue and inject this BLAZE.ALL into BIN")
    print("2. Load the patched BIN in emulator")
    print("3. Go to Cavern of Death Floor 1")
    print("4. Trigger combat")
    print()
    print("EXPECTED RESULTS:")
    print("  - Game FREEZES at combat start -> Offset is CORRECT, we can patch!")
    print("  - Game runs normally -> Offset is wrong/dead code, need new approach")
    print()

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
