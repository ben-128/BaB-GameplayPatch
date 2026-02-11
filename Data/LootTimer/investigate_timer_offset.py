#!/usr/bin/env python3
"""
Investigation: Verify timer offset in chest_update code.

v10 savestates show timer at entity+0x10 (NOT +0x14).
But v10 code analysis shows lhu/sh from +0x14.

This script checks ALL entity field accesses in the chest_update patterns
to resolve the contradiction.
"""

import struct
from pathlib import Path


def disasm_simple(word):
    """Simple MIPS disassembly for common instructions."""
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    signed_imm = imm if imm < 0x8000 else imm - 0x10000

    REG = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
           '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
           '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
           '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

    # Load/Store halfword
    if opcode == 0x25:  # lhu
        return f"lhu {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    elif opcode == 0x29:  # sh
        return f"sh {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    # Load/Store word
    elif opcode == 0x23:  # lw
        return f"lw {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    elif opcode == 0x2B:  # sw
        return f"sw {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    # Immediate
    elif opcode == 0x09:  # addiu
        return f"addiu {REG[rt]}, {REG[rs]}, {signed_imm}"
    elif opcode == 0x0F:  # lui
        return f"lui {REG[rt]}, 0x{imm:04X}"
    elif opcode == 0x0D:  # ori
        return f"ori {REG[rt]}, {REG[rs]}, 0x{imm:04X}"
    # Branch
    elif opcode == 0x05:  # bne
        return f"bne {REG[rs]}, {REG[rt]}, {signed_imm*4:+d}"
    elif opcode == 0x04:  # beq
        return f"beq {REG[rs]}, {REG[rt]}, {signed_imm*4:+d}"
    elif opcode == 0x14:  # bnez (actually bgtz)
        return f"bnez {REG[rs]}, {signed_imm*4:+d}"
    # R-type
    elif opcode == 0x00:
        funct = word & 0x3F
        if funct == 0x00:  # sll
            shamt = (word >> 6) & 0x1F
            return f"sll {REG[rd]}, {REG[rt]}, {shamt}"
        elif funct == 0x25:  # or
            return f"or {REG[rd]}, {REG[rs]}, {REG[rt]}"

    return f"0x{word:08X}"


def find_timer_patterns(data):
    """Find the v10 chest timer decrement patterns."""
    matches = []

    # v10 pattern: lhu 0x14 / nop / addiu -1 / sh 0x14 / ... / lui 0x0200
    for i in range(0, len(data) - 28, 4):
        pre2 = struct.unpack_from('<I', data, i)[0]
        pre1 = struct.unpack_from('<I', data, i + 4)[0]
        target = struct.unpack_from('<I', data, i + 8)[0]
        post1 = struct.unpack_from('<I', data, i + 12)[0]

        # Check pattern
        if (pre1 != 0x00000000 or  # nop
            target != 0x2442FFFF or  # addiu $v0,$v0,-1
            (pre2 >> 26) != 0x25 or  # lhu
            (post1 >> 26) != 0x29):  # sh
            continue

        # Check offsets
        pre2_offset = pre2 & 0xFFFF
        post1_offset = post1 & 0xFFFF

        # Both should be 0x14 according to v10
        if pre2_offset == 0x0014 and post1_offset == 0x0014:
            matches.append(i)

    return matches


def analyze_context(data, offset, context_size=80):
    """Analyze entity field accesses around the timer pattern."""
    print(f"\n{'='*70}")
    print(f"Pattern at offset 0x{offset:08X}")
    ram_main = (offset - 0x009468A8) + 0x80080000 if offset >= 0x009468A8 else 0
    ram_stub = (offset - 0x0091D80C) + 0x80056F64 if 0x0091D80C <= offset < 0x009468A8 else 0
    ram = ram_main if ram_main else ram_stub
    print(f"RAM address: ~0x{ram:08X}")
    print(f"{'='*70}")

    # Track entity pointer register (usually $s0, $s1, $s2, etc.)
    entity_bases = set()

    start = max(0, offset - context_size)
    end = min(len(data), offset + context_size)

    for i in range(start, end, 4):
        word = struct.unpack_from('<I', data, i)[0]
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF

        marker = ''
        if i == offset + 8:  # addiu -1
            marker = ' <-- TARGET (timer decrement)'

        # Track load/store to entity offsets
        if opcode in [0x23, 0x25, 0x29, 0x2B]:  # lw, lhu, sh, sw
            if imm in [0x0010, 0x0012, 0x0014, 0x0016, 0x0028, 0x002A]:
                entity_bases.add(rs)
                marker += f' <-- entity+0x{imm:04X} (base=${rs})'

        disasm = disasm_simple(word)
        print(f"  0x{i:08X}: {disasm:40s}{marker}")

    print(f"\nEntity base registers detected: {[f'${r}' for r in sorted(entity_bases)]}")


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    print("="*70)
    print("Investigation: Timer offset in chest_update code")
    print("="*70)
    print(f"Analyzing: {blaze_path}")
    print()

    data = blaze_path.read_bytes()
    print(f"BLAZE.ALL size: {len(data):,} bytes")

    matches = find_timer_patterns(data)
    print(f"Found {len(matches)} timer decrement patterns")

    for offset in matches:
        analyze_context(data, offset)

    print("\n" + "="*70)
    print("Summary:")
    print("="*70)
    print("Check if timer loads/stores use offset 0x10 or 0x14")
    print("Compare with v10 savestate analysis (timer at entity+0x10)")
    print("="*70)


if __name__ == '__main__':
    main()
