#!/usr/bin/env python3
"""
Find ALL copies of the check_kill function in BLAZE.ALL.

Signature: the unique bitmask 0x400003E8 loaded via lui+ori.
For each copy, search backwards for function start (lw $reg, 0x0074($reg))
or standard function prologue (addiu $sp, $sp, -N).
"""

import struct
from pathlib import Path


def disasm_simple(word):
    """Minimal MIPS disassembly for display."""
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
            '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
            '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
            '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

    if word == 0: return "nop"
    if word == 0x03E00008: return "jr $ra"

    if op == 0x23:  # lw
        return f"lw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x09:  # addiu
        return f"addiu {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x0F:  # lui
        return f"lui {regs[rt]}, 0x{imm:04X}"
    if op == 0x0D:  # ori
        return f"ori {regs[rt]}, {regs[rs]}, 0x{imm:04X}"
    if op == 0x25:  # lhu
        return f"lhu {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x29:  # sh
        return f"sh {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x2B:  # sw
        return f"sw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x03:  # jal
        target = (word & 0x03FFFFFF) << 2
        return f"jal 0x{target:08X}"
    if op == 0x00:
        func = word & 0x3F
        if func == 0x08: return f"jr {regs[rs]}"
        if func == 0x21: return f"addu {regs[rd]}, {regs[rs]}, {regs[rt]}"
    return f"0x{word:08X}"


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    blaze = blaze_path.read_bytes()
    print(f"BLAZE.ALL size: {len(blaze):,} bytes")

    # Step 1: Find all lui $v1, 0x4000 (part of loading bitmask 0x400003E8)
    # lui encoding: opcode=0x0F, rt=$v1(3)
    # lui $v1, 0x4000 = 0x3C034000
    LUI_PATTERN = 0x3C034000

    # ori $v1, $v1, 0x03E8 = 0x346303E8
    ORI_PATTERN = 0x346303E8

    print("\n" + "=" * 80)
    print("  Step 1: Find all lui $v1, 0x4000 + ori $v1, $v1, 0x03E8 pairs")
    print("=" * 80)

    bitmask_locs = []
    for i in range(0, len(blaze) - 8, 4):
        word = struct.unpack_from('<I', blaze, i)[0]
        if word == LUI_PATTERN:
            # Check next few instructions for ori
            for j in range(1, 8):
                off2 = i + j * 4
                if off2 + 4 > len(blaze):
                    break
                w2 = struct.unpack_from('<I', blaze, off2)[0]
                if w2 == ORI_PATTERN:
                    bitmask_locs.append((i, off2))
                    break

    print(f"  Found {len(bitmask_locs)} bitmask pairs")
    for lui_off, ori_off in bitmask_locs:
        print(f"    lui @ BLAZE 0x{lui_off:08X}, ori @ BLAZE 0x{ori_off:08X}")

    # Step 2: For each bitmask, search backwards for function start
    print("\n" + "=" * 80)
    print("  Step 2: Find function starts")
    print("=" * 80)

    func_starts = []

    for idx, (lui_off, ori_off) in enumerate(bitmask_locs):
        print(f"\n  --- Copy {idx + 1}/{len(bitmask_locs)} (bitmask @ BLAZE 0x{lui_off:08X}) ---")

        found_start = None

        # Strategy A: Search backwards for lw $reg, 0x0074($reg)
        # lw opcode = 0x23, imm = 0x0074
        # Encoding: (0x23 << 26) | (rs << 21) | (rt << 16) | 0x0074
        # Mask: top 6 bits must be 0x23 (100011), bottom 16 must be 0x0074
        for back in range(4, 512, 4):
            addr = lui_off - back
            if addr < 0:
                break
            w = struct.unpack_from('<I', blaze, addr)[0]
            op = (w >> 26) & 0x3F
            imm = w & 0xFFFF
            if op == 0x23 and imm == 0x0074:
                # Found lw $reg, 0x0074($reg) - likely function start
                rs = (w >> 21) & 0x1F
                rt = (w >> 16) & 0x1F
                print(f"    FOUND: lw at BLAZE 0x{addr:08X} ({disasm_simple(w)}), "
                      f"{back} bytes before bitmask")

                # Verify: check if previous instruction is a function boundary
                # (jr $ra from previous function, or addiu $sp prologue)
                if addr >= 4:
                    prev = struct.unpack_from('<I', blaze, addr - 4)[0]
                    prev2 = struct.unpack_from('<I', blaze, addr - 8)[0] if addr >= 8 else 0
                    # jr $ra in delay slot position means prev func ends
                    # or nop/sw $ra is common before function start
                    print(f"           prev-2: {disasm_simple(prev2)}")
                    print(f"           prev-1: {disasm_simple(prev)}")

                found_start = addr
                break

        # Strategy B: If no lw 0x0074, search for addiu $sp, $sp, -N (prologue)
        if found_start is None:
            for back in range(4, 512, 4):
                addr = lui_off - back
                if addr < 0:
                    break
                w = struct.unpack_from('<I', blaze, addr)[0]
                op = (w >> 26) & 0x3F
                rs = (w >> 21) & 0x1F
                rt = (w >> 16) & 0x1F
                simm = (w & 0xFFFF) if (w & 0xFFFF) < 0x8000 else (w & 0xFFFF) - 0x10000
                if op == 0x09 and rs == 29 and rt == 29 and simm < 0:
                    # addiu $sp, $sp, -N (function prologue)
                    print(f"    FOUND prologue: addiu $sp, $sp, {simm} at BLAZE 0x{addr:08X}, "
                          f"{back} bytes before bitmask")
                    found_start = addr
                    break

        if found_start is None:
            print(f"    WARNING: No function start found within 512 bytes!")
            # Dump context around bitmask
            print(f"    Context around lui @ 0x{lui_off:08X}:")
            start = max(0, lui_off - 64)
            for a in range(start, lui_off + 32, 4):
                w = struct.unpack_from('<I', blaze, a)[0]
                marker = " <-- LUI" if a == lui_off else (" <-- ORI" if a == ori_off else "")
                print(f"      0x{a:08X}: 0x{w:08X} {disasm_simple(w)}{marker}")
        else:
            func_starts.append(found_start)
            # Show first 8 instructions
            print(f"    Function disassembly:")
            for k in range(20):
                a = found_start + k * 4
                if a + 4 > len(blaze):
                    break
                w = struct.unpack_from('<I', blaze, a)[0]
                marker = ""
                if a == lui_off: marker = " <-- LUI 0x4000"
                if a == ori_off: marker = " <-- ORI 0x03E8"
                print(f"      0x{a:08X}: 0x{w:08X} {disasm_simple(w)}{marker}")

    # Step 3: Summary
    print("\n" + "=" * 80)
    print(f"  SUMMARY: {len(func_starts)} function starts found out of {len(bitmask_locs)} copies")
    print("=" * 80)

    # Check which have lw $a0, 0x0074($a0) = 0x8C840074 at start
    for i, fs in enumerate(func_starts):
        w = struct.unpack_from('<I', blaze, fs)[0]
        w2 = struct.unpack_from('<I', blaze, fs + 4)[0]
        is_standard = (w == 0x8C840074)
        has_nop = (w2 == 0x00000000)
        print(f"  Copy {i+1}: BLAZE 0x{fs:08X}  "
              f"first=0x{w:08X} ({disasm_simple(w)})  "
              f"second=0x{w2:08X} ({disasm_simple(w2)})  "
              f"{'STANDARD' if is_standard else 'VARIANT'}")

    # Generate patcher data
    print("\n" + "=" * 80)
    print("  PATCHER DATA (copy-paste into patch_loot_timer.py)")
    print("=" * 80)
    print("KILL_FUNC_OFFSETS = [")
    for fs in sorted(set(func_starts)):
        w = struct.unpack_from('<I', blaze, fs)[0]
        w2 = struct.unpack_from('<I', blaze, fs + 4)[0]
        print(f"    (0x{fs:08X}, 0x{w:08X}, 0x{w2:08X}),  # {disasm_simple(w)}")
    print("]")


if __name__ == '__main__':
    main()
