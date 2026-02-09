#!/usr/bin/env python3
"""
Count ALL lhu+nop+addiu(-1)+sh patterns with offset 0x14 in BLAZE.ALL,
with ANY base register. Group by overlay region.
"""
import struct
from pathlib import Path

BLAZE_ALL_PATH = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

def main():
    blaze = BLAZE_ALL_PATH.read_bytes()
    print(f"BLAZE.ALL: {len(blaze):,} bytes")

    matches = []
    for i in range(0, len(blaze) - 16, 4):
        w0 = struct.unpack_from('<I', blaze, i)[0]
        w1 = struct.unpack_from('<I', blaze, i + 4)[0]
        w2 = struct.unpack_from('<I', blaze, i + 8)[0]
        w3 = struct.unpack_from('<I', blaze, i + 12)[0]

        # w0: lhu $v0, 0x14(base) — opcode 100101, rt=$v0=2, imm=0x0014
        if (w0 & 0xFC1FFFFF) != 0x94020014:
            continue
        base0 = (w0 >> 21) & 0x1F

        # w1: NOP
        if w1 != 0x00000000:
            continue

        # w2: addiu $v0, $v0, -1
        if w2 != 0x2442FFFF:
            continue

        # w3: sh $v0, 0x14(base) — opcode 101001, rt=$v0=2, imm=0x0014
        if (w3 & 0xFC1FFFFF) != 0xA4020014:
            continue
        base3 = (w3 >> 21) & 0x1F

        # Base registers must match
        if base0 != base3:
            continue

        matches.append((i, base0))

    print(f"\nTotal: {len(matches)} patterns (lhu+nop+addiu(-1)+sh with offset 0x14)")

    # Group by base register
    by_reg = {}
    for off, base in matches:
        reg_name = REGS[base]
        by_reg.setdefault(reg_name, []).append(off)

    print(f"\nBy register:")
    for reg, offsets in sorted(by_reg.items()):
        print(f"  {reg}: {len(offsets)} matches")
        for off in offsets:
            print(f"    0x{off:08X} (addiu at 0x{off+8:08X})")

    print(f"\nAll patch targets (addiu offsets):")
    for off, base in matches:
        print(f"  0x{off+8:08X}")

if __name__ == '__main__':
    main()
