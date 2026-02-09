#!/usr/bin/env python3
"""
Patch the chest despawn timer in BLAZE.ALL overlay code.

The chest entity lifecycle is managed by a state machine in dungeon
overlay code loaded from BLAZE.ALL at runtime:
  State 1 (spawn):    entity+0x28 increases 200->1000 (fade-in)
  State 2 (alive):    entity+0x14 decrements by 1/frame (countdown)
  State 3 (despawn):  entity+0x28 decreases by 60/frame (fade-out)
  Kill:               entity+0x00 bit 14 set when entity+0x28 < 0

The countdown decrement in state 2 uses different base registers
($s0, $s1, $s2, $v1) depending on the overlay handler function:
  lhu  $v0, 0x14($base)   ; load timer
  nop
  addiu $v0, $v0, -1      ; DECREMENT  <-- NOP this
  sh   $v0, 0x14($base)   ; store back

With 1000 initial value at 50fps PAL = 20 seconds before despawn.
NOPping the decrement makes chests permanent.

35 occurrences across all dungeon overlays (7 $s1 + 9 $s0 + 16 $s2 + 3 $v1).
All must be patched — the chest entity may be processed by any handler.

Runs at build step 7 (patches output/BLAZE.ALL before BIN injection).
"""

import struct
import sys
from pathlib import Path

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

# Masked matching for ANY base register:
# w0: lhu $v0, 0x14(base) — (w0 & 0xFC1FFFFF) == 0x94020014
# w1: nop — 0x00000000
# w2: addiu $v0, $v0, -1 — 0x2442FFFF
# w3: sh $v0, 0x14(base) — (w3 & 0xFC1FFFFF) == 0xA4020014
# base register of w0 must equal base register of w3
LHU_MASK  = 0xFC1FFFFF
LHU_MATCH = 0x94020014
SH_MASK   = 0xFC1FFFFF
SH_MATCH  = 0xA4020014
NOP_WORD  = 0x00000000
ADDIU_WORD = 0x2442FFFF  # addiu $v0, $v0, -1

EXPECTED_MIN_MATCHES = 30
EXPECTED_MAX_MATCHES = 45


def find_patterns(data):
    """Find all lhu+nop+addiu(-1)+sh patterns with offset 0x14, any base register."""
    original = []
    patched = []

    for i in range(0, len(data) - 16, 4):
        w0 = struct.unpack_from('<I', data, i)[0]
        w1 = struct.unpack_from('<I', data, i + 4)[0]
        w2 = struct.unpack_from('<I', data, i + 8)[0]
        w3 = struct.unpack_from('<I', data, i + 12)[0]

        # w0: lhu $v0, 0x14(base)
        if (w0 & LHU_MASK) != LHU_MATCH:
            continue
        base0 = (w0 >> 21) & 0x1F

        # w1: nop
        if w1 != NOP_WORD:
            continue

        # w3: sh $v0, 0x14(base) — same base register
        if (w3 & SH_MASK) != SH_MATCH:
            continue
        base3 = (w3 >> 21) & 0x1F
        if base0 != base3:
            continue

        # w2: addiu $v0, $v0, -1 (original) or nop (already patched)
        if w2 == ADDIU_WORD:
            original.append((i, base0))
        elif w2 == NOP_WORD:
            patched.append((i, base0))

    return original, patched


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'output' / 'BLAZE.ALL'

    print("Loot Timer: patch chest despawn in dungeon overlay code")
    print(f"  Target: {blaze_path}")

    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    data = bytearray(blaze_path.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    original, patched = find_patterns(data)
    total = len(original) + len(patched)

    print(f"\n  Matches: {len(original)} unpatched, "
          f"{len(patched)} already patched ({total} total)")

    if total == 0:
        print("[ERROR] No patterns found in BLAZE.ALL!")
        sys.exit(1)

    if total < EXPECTED_MIN_MATCHES:
        print(f"[WARNING] Only {total} matches (expected >= {EXPECTED_MIN_MATCHES})")

    if total > EXPECTED_MAX_MATCHES:
        print(f"[ERROR] Too many matches ({total} > {EXPECTED_MAX_MATCHES}) - aborting")
        sys.exit(1)

    # Apply patches
    applied = 0
    for sig_pos, base in original:
        target_pos = sig_pos + 8  # word index 2 = addiu
        old_word = struct.unpack_from('<I', data, target_pos)[0]

        if old_word != ADDIU_WORD:
            print(f"  [SKIP] 0x{target_pos:08X}: unexpected 0x{old_word:08X}")
            continue

        data[target_pos:target_pos + 4] = struct.pack('<I', NOP_WORD)
        print(f"  PATCH 0x{target_pos:08X}: addiu $v0,$v0,-1 -> nop  (base={REGS[base]})")
        applied += 1

    for sig_pos, base in patched:
        print(f"  SKIP  0x{sig_pos + 8:08X}: already patched  (base={REGS[base]})")

    if applied == 0 and len(patched) == 0:
        print("\n[ERROR] No patches applied!")
        sys.exit(1)

    if applied > 0:
        blaze_path.write_bytes(data)

    print(f"\n{'='*60}")
    print(f"  {applied} new + {len(patched)} existing = "
          f"{applied + len(patched)} total overlay patches")
    print(f"  Chest despawn timer frozen in all dungeon areas")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
