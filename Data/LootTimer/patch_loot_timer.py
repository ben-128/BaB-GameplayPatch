#!/usr/bin/env python3
"""
Patch chest despawn timer in BLAZE.ALL stub region (v9).

v1-v8: Patched Function A in the main overlay (0x80080000+).
       All FAILED because Function A is NEVER called by the dispatcher.
       The dispatcher's function pointer table (0x8005A458) contains ONLY
       stub region functions (0x8006Exxx). Function A is dead code for chests.

v9: Patches Handler [0] in the stub region — the ONLY function in the
    dispatcher table that decrements a halfword timer.

    Handler [0] (RAM 0x8006E3AC, BLAZE 0x00934C54):
      - Probability-gated countdown: RNG % 100 < threshold → decrement
      - Timer at handler_data+0x10 (halfword, countdown 1000→0)
      - When timer reaches 0 → kill entity (sb $zero, +0x00)

    Target: NOP the `addiu $v0,$v0,-1` at BLAZE 0x00934CC8.
    This freezes the timer so chests never despawn.

    Note: Handler [0] is generic (used by all handler_type=0 entities).
    Side effects on other entity types need in-game testing.

Runs at build step 7 (patches output/BLAZE.ALL before BIN injection).
"""

import struct
import sys
from pathlib import Path

NOP = 0x00000000

# Handler [0] timer decrement: addiu $v0,$v0,-1 (0x2442FFFF)
# RAM 0x8006E420, BLAZE 0x00934CC8
TIMER_DECREMENT = 0x00934CC8
TIMER_EXPECTED  = 0x2442FFFF  # addiu $v0,$v0,-1


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'output' / 'BLAZE.ALL'

    print("Loot Timer v9: Handler [0] stub region patch")
    print(f"  Target: {blaze_path}")

    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    data = bytearray(blaze_path.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    if TIMER_DECREMENT + 4 > len(data):
        print(f"[ERROR] Offset 0x{TIMER_DECREMENT:08X} out of range")
        sys.exit(1)

    # Read current instruction
    current = struct.unpack_from('<I', data, TIMER_DECREMENT)[0]
    print(f"  0x{TIMER_DECREMENT:08X}: 0x{current:08X}", end="")

    if current == NOP:
        print(" (already NOPed)")
        print()
        print(f"{'='*60}")
        print(f"  Timer decrement already patched (NOP)")
        print(f"  Chest despawn timer frozen")
        print(f"{'='*60}")
        return

    if current != TIMER_EXPECTED:
        print(f" (UNEXPECTED! expected 0x{TIMER_EXPECTED:08X})")
        print(f"[ERROR] Instruction at 0x{TIMER_DECREMENT:08X} doesn't match.")
        print(f"        Expected: addiu $v0,$v0,-1 (0x{TIMER_EXPECTED:08X})")
        print(f"        Got:      0x{current:08X}")
        sys.exit(1)

    print(" (addiu $v0,$v0,-1)")

    # Apply NOP
    data[TIMER_DECREMENT:TIMER_DECREMENT+4] = struct.pack('<I', NOP)
    print(f"  PATCH 0x{TIMER_DECREMENT:08X}: addiu $v0,$v0,-1 -> nop")

    # Verify
    verify = struct.unpack_from('<I', data, TIMER_DECREMENT)[0]
    if verify != NOP:
        print(f"[ERROR] Verification failed: 0x{verify:08X}")
        sys.exit(1)

    blaze_path.write_bytes(data)

    print()
    print(f"{'='*60}")
    print(f"  Handler [0] timer decrement NOPed at BLAZE 0x{TIMER_DECREMENT:08X}")
    print(f"  (RAM 0x8006E420 = dispatcher table entry [0])")
    print(f"  Chest despawn timer frozen")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
