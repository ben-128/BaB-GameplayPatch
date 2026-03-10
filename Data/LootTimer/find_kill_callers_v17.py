#!/usr/bin/env python3
"""
v17 investigation: Find ALL callers of check_kill (0x80075060) and
understand the INLINED kill mechanism.

Two questions:
1. Who calls jal 0x80075060? (JAL word = 0x0C01D418)
2. What does the inlined 0x400003E8 check actually kill?
"""

import struct
from pathlib import Path


REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def disasm(word):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    if word == 0: return "nop"
    if word == 0x03E00008: return "jr $ra"

    if op == 0x23: return f"lw {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x09: return f"addiu {REGS[rt]}, {REGS[rs]}, {simm}"
    if op == 0x0F: return f"lui {REGS[rt]}, 0x{imm:04X}"
    if op == 0x0D: return f"ori {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    if op == 0x25: return f"lhu {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x29: return f"sh {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x2B: return f"sw {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x03:
        target = (word & 0x03FFFFFF) << 2
        return f"jal 0x{target:08X}"
    if op == 0x04: return f"beq {REGS[rs]}, {REGS[rt]}, {simm}"
    if op == 0x05: return f"bne {REGS[rs]}, {REGS[rt]}, {simm}"
    if op == 0x0C: return f"andi {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    if op == 0x00:
        func = word & 0x3F
        if func == 0x08: return f"jr {REGS[rs]}"
        if func == 0x21: return f"addu {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if func == 0x24: return f"and {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if func == 0x25: return f"or {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        sa = (word >> 6) & 0x1F
        if func == 0x00: return f"sll {REGS[rd]}, {REGS[rt]}, {sa}"
        if func == 0x03: return f"sra {REGS[rd]}, {REGS[rt]}, {sa}"
    return f"0x{word:08X}"


def blaze_to_ram(offset):
    """Convert BLAZE offset to approximate RAM address."""
    STUB_START = 0x0091D80C
    STUB_END = 0x009468A8
    MAIN_START = 0x009468A8

    if STUB_START <= offset < STUB_END:
        return (offset - STUB_START) + 0x80056F64
    elif offset >= MAIN_START:
        return (offset - MAIN_START) + 0x80080000
    return 0


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    blaze = blaze_path.read_bytes()
    print(f"BLAZE.ALL size: {len(blaze):,} bytes")

    # =========================================================================
    # Part 1: Find all jal 0x80075060 (JAL word = 0x0C01D418)
    # =========================================================================
    JAL_WORD = 0x0C01D418  # jal 0x80075060

    print("\n" + "=" * 80)
    print("  Part 1: Find all callers of check_kill (jal 0x80075060)")
    print("  JAL word: 0x0C01D418")
    print("=" * 80)

    jal_locs = []
    for i in range(0, len(blaze) - 4, 4):
        word = struct.unpack_from('<I', blaze, i)[0]
        if word == JAL_WORD:
            jal_locs.append(i)

    print(f"\n  Found {len(jal_locs)} callers")
    for loc in jal_locs:
        ram = blaze_to_ram(loc)
        region = "STUB" if loc < 0x009468A8 else "MAIN/ZONE"

        print(f"\n  Caller @ BLAZE 0x{loc:08X} (RAM ~0x{ram:08X}) [{region}]")
        # Show context: 6 instructions before + 6 after
        start = max(0, loc - 24)
        end = min(len(blaze) - 4, loc + 28)
        for a in range(start, end, 4):
            w = struct.unpack_from('<I', blaze, a)[0]
            marker = " <<<< JAL check_kill" if a == loc else ""
            print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}{marker}")

    # =========================================================================
    # Part 2: Understand the inlined bitmask check pattern
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 2: Analyze PARENT FLAG CHECK pattern near inlined copies")
    print("  Looking for the 0xD0000000 mask (parent entity cleanup detection)")
    print("=" * 80)

    # The inlined copies have lui 0x4000 + ori 0x03E8
    # Search for the 0xD0000000 pattern near them
    # lui with 0xD000 = 0x3C0XD000
    BITMASK_LOCS = [
        0x0092800C, 0x009F28C8, 0x00BC8108, 0x0100F8CC,
        0x0109201C, 0x012CCA88, 0x01338770, 0x015071B8,
        0x0169EFDC, 0x016A4A74, 0x01B99254, 0x020D6128,
        0x0264EFA4, 0x0277DC04, 0x02B72014, 0x02BBC228,
        0x02BBD2C0, 0x02BBE3B0
    ]

    # For each inlined copy, check what branch leads to it
    # The pattern before is: andi $v0, $reg, 0x0804 + beq $v0, $zero, skip
    for loc in BITMASK_LOCS[:3]:  # Just first 3 for brevity
        print(f"\n  --- Inlined copy @ BLAZE 0x{loc:08X} ---")
        # Show 40 instructions before
        start = max(0, loc - 160)
        for a in range(start, loc + 40, 4):
            w = struct.unpack_from('<I', blaze, a)[0]
            marker = " <-- LUI 0x4000" if a == loc else ""
            if w & 0xFFFF0000 == 0x3C030000 and (w & 0xFFFF) in [0xD000, 0x4000]:
                marker = f" <-- lui $v1, 0x{w & 0xFFFF:04X}"
            print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}{marker}")

    # =========================================================================
    # Part 3: Search for parent entity check patterns near inlined copies
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 3: Search for lw $reg, 0x0074($reg) near ALL inlined copies")
    print("  (within 2000 bytes before each bitmask)")
    print("=" * 80)

    for loc in BITMASK_LOCS:
        found = False
        for back in range(4, 2000, 4):
            addr = loc - back
            if addr < 0:
                break
            w = struct.unpack_from('<I', blaze, addr)[0]
            op = (w >> 26) & 0x3F
            imm = w & 0xFFFF
            if op == 0x23 and imm == 0x0074:
                rs = (w >> 21) & 0x1F
                rt = (w >> 16) & 0x1F
                print(f"  BLAZE 0x{loc:08X}: lw 0x0074 at 0x{addr:08X} ({back} bytes before)")
                print(f"    Instruction: {disasm(w)}")
                found = True
                break
        if not found:
            print(f"  BLAZE 0x{loc:08X}: NO lw 0x0074 within 2000 bytes!")

    # =========================================================================
    # Part 4: Check if any JAL callers are NEAR the inlined copies
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 4: JAL callers vs inlined copies - are they in same functions?")
    print("=" * 80)

    for jloc in jal_locs:
        # Find closest inlined copy
        closest = min(BITMASK_LOCS, key=lambda x: abs(x - jloc))
        dist = abs(closest - jloc)
        if dist < 5000:
            print(f"  JAL @ 0x{jloc:08X} is {dist} bytes from inlined @ 0x{closest:08X}")
        else:
            print(f"  JAL @ 0x{jloc:08X} - nearest inlined: 0x{closest:08X} ({dist} bytes)")

    # =========================================================================
    # Part 5: Check what CHECK happens after JAL returns 1
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 5: What does the caller do when check_kill returns 1?")
    print("=" * 80)

    for loc in jal_locs[:5]:  # First 5
        print(f"\n  Caller @ BLAZE 0x{loc:08X}:")
        # Show 10 instructions after JAL
        for k in range(10):
            a = loc + 4 + k * 4
            if a + 4 > len(blaze):
                break
            w = struct.unpack_from('<I', blaze, a)[0]
            print(f"    +{k*4:2d}: 0x{w:08X}  {disasm(w)}")


if __name__ == '__main__':
    main()
