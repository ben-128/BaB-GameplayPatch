#!/usr/bin/env python3
"""
v16 Investigation: Fresh approach to chest despawn timer.

Key insight: If the timer decrements every 20th frame (not every frame),
then 20s @ 50fps = 1000 frames / 20 = 50 decrements.
The INIT value might be 50 (0x32), NOT 1000 (0x3E8)!

This script:
1. Disassembles the chest_update function around the known decrement
2. Finds the actual modulo/frequency of decrements
3. Searches for the REAL init value (50? 100? other?)
4. Searches both BLAZE.ALL and SLES for this value
"""

import struct
from pathlib import Path

REG = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
       '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
       '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
       '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def disasm(word, addr=0):
    """MIPS disassembler (common instructions)."""
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    target = (word & 0x03FFFFFF) << 2

    if word == 0:
        return "nop"

    # R-type
    if opcode == 0x00:
        if funct == 0x00: return f"sll {REG[rd]}, {REG[rt]}, {shamt}"
        if funct == 0x02: return f"srl {REG[rd]}, {REG[rt]}, {shamt}"
        if funct == 0x03: return f"sra {REG[rd]}, {REG[rt]}, {shamt}"
        if funct == 0x08: return f"jr {REG[rs]}"
        if funct == 0x09: return f"jalr {REG[rd]}, {REG[rs]}"
        if funct == 0x10: return f"mfhi {REG[rd]}"
        if funct == 0x12: return f"mflo {REG[rd]}"
        if funct == 0x18: return f"mult {REG[rs]}, {REG[rt]}"
        if funct == 0x19: return f"multu {REG[rs]}, {REG[rt]}"
        if funct == 0x1A: return f"div {REG[rs]}, {REG[rt]}"
        if funct == 0x1B: return f"divu {REG[rs]}, {REG[rt]}"
        if funct == 0x21: return f"addu {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x23: return f"subu {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x24: return f"and {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x25: return f"or {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x26: return f"xor {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x27: return f"nor {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x2A: return f"slt {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x2B: return f"sltu {REG[rd]}, {REG[rs]}, {REG[rt]}"
        return f"R:0x{word:08X}"

    # I-type
    if opcode == 0x01:
        if rt == 0x00: return f"bltz {REG[rs]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
        if rt == 0x01: return f"bgez {REG[rs]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
        return f"REGIMM:0x{word:08X}"
    if opcode == 0x02: return f"j 0x{(addr & 0xF0000000) | target:08X}"
    if opcode == 0x03: return f"jal 0x{(addr & 0xF0000000) | target:08X}"
    if opcode == 0x04: return f"beq {REG[rs]}, {REG[rt]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x05: return f"bne {REG[rs]}, {REG[rt]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x06: return f"blez {REG[rs]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x07: return f"bgtz {REG[rs]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x08: return f"addi {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x09: return f"addiu {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x0A: return f"slti {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x0B: return f"sltiu {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x0C: return f"andi {REG[rt]}, {REG[rs]}, 0x{imm:04X}"
    if opcode == 0x0D: return f"ori {REG[rt]}, {REG[rs]}, 0x{imm:04X}"
    if opcode == 0x0F: return f"lui {REG[rt]}, 0x{imm:04X}"
    if opcode == 0x20: return f"lb {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x21: return f"lh {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x23: return f"lw {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x24: return f"lbu {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x25: return f"lhu {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x28: return f"sb {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x29: return f"sh {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x2B: return f"sw {REG[rt]}, 0x{imm:04X}({REG[rs]})"

    return f"?:0x{word:08X}"


def blaze_to_ram(offset):
    """Convert BLAZE.ALL offset to RAM address."""
    if offset >= 0x009468A8:
        return (offset - 0x009468A8) + 0x80080000
    elif offset >= 0x0091D80C:
        return (offset - 0x0091D80C) + 0x80056F64
    return 0


def dump_region(data, start, count, label=""):
    """Disassemble a region of BLAZE.ALL."""
    if label:
        print(f"\n{'='*80}")
        print(f"  {label}")
        print(f"{'='*80}")
    for i in range(count):
        off = start + i * 4
        if off + 4 > len(data):
            break
        word = struct.unpack_from('<I', data, off)[0]
        ram = blaze_to_ram(off)
        d = disasm(word, ram)
        marker = ""
        # Highlight interesting patterns
        if "0x0014" in d and ("lhu" in d or "sh " in d or "lh " in d):
            marker = "  <-- entity+0x14 (timer?)"
        elif "0x0012" in d and ("lhu" in d or "sh " in d or "lh " in d):
            marker = "  <-- entity+0x12 (master timer?)"
        elif "0x0010" in d and ("lhu" in d or "sh " in d or "lh " in d):
            marker = "  <-- entity+0x10"
        elif "addiu" in d and ", -1" in d:
            marker = "  <-- DECREMENT"
        elif "0x02000000" in d or "0x0200" in d:
            marker = "  <-- dead flag?"
        elif "0x3E8" in d or ", 1000" in d:
            marker = "  <-- VALUE 1000!"
        elif ", 50" in d and "addiu" in d:
            marker = "  <-- VALUE 50?"
        elif ", 20" in d and "addiu" in d:
            marker = "  <-- VALUE 20?"
        print(f"  BLAZE 0x{off:08X}  RAM 0x{ram:08X}:  {d:45s}{marker}")


def search_init_patterns(data, init_value, entity_offset):
    """Search for: addiu $reg, $zero, VALUE + sh $reg, entity_offset($base)"""
    results = []
    # addiu $rt, $zero, VALUE = opcode 0x09, rs=0, rt=any, imm=VALUE
    # Encoding: 0x24000000 | (rt << 16) | (VALUE & 0xFFFF)
    for i in range(0, len(data) - 8, 4):
        word1 = struct.unpack_from('<I', data, i)[0]
        # Check addiu $rt, $zero, init_value
        if (word1 >> 26) != 0x09:  # addiu
            continue
        rs = (word1 >> 21) & 0x1F
        if rs != 0:  # $zero
            continue
        imm = word1 & 0xFFFF
        if imm != (init_value & 0xFFFF):
            continue
        rt = (word1 >> 16) & 0x1F

        # Look in next 4 instructions for sh $rt, entity_offset($base)
        for j in range(1, 5):
            off2 = i + j * 4
            if off2 + 4 > len(data):
                break
            word2 = struct.unpack_from('<I', data, off2)[0]
            if (word2 >> 26) != 0x29:  # sh
                continue
            rt2 = (word2 >> 16) & 0x1F
            imm2 = word2 & 0xFFFF
            if rt2 == rt and imm2 == entity_offset:
                results.append((i, off2, rt))
    return results


def search_comparison_patterns(data, comp_value):
    """Search for comparison with a constant (slti, sltiu, or addiu+slt)."""
    results = []
    for i in range(0, len(data) - 4, 4):
        word = struct.unpack_from('<I', data, i)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000
        # slti $rt, $rs, VALUE or sltiu
        if opcode in (0x0A, 0x0B) and abs(simm) == comp_value:
            results.append((i, "slti/sltiu", simm))
        # addiu $rt, $zero, VALUE (load for comparison)
        if opcode == 0x09:
            rs = (word >> 21) & 0x1F
            if rs == 0 and (simm == comp_value or imm == comp_value):
                # Check next few instr for slt
                for j in range(1, 4):
                    off2 = i + j * 4
                    if off2 + 4 > len(data):
                        break
                    w2 = struct.unpack_from('<I', data, off2)[0]
                    if (w2 & 0x3F) in (0x2A, 0x2B) and (w2 >> 26) == 0:  # slt/sltu
                        results.append((i, "addiu+slt", simm))
                        break
    return results


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'
    sles_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'SLES_008.45'

    print("=" * 80)
    print("  v16: Fresh Chest Timer Investigation")
    print("=" * 80)

    blaze = blaze_path.read_bytes()
    sles = sles_path.read_bytes()
    print(f"BLAZE.ALL: {len(blaze):,} bytes")
    print(f"SLES: {len(sles):,} bytes")

    # =========================================================================
    # PART 1: Disassemble the known chest_update function
    # =========================================================================
    # Timer decrement at BLAZE 0x0094E09C (RAM 0x800877F4)
    # Function starts at BLAZE 0x0094DECC (RAM 0x80087624)
    func_start = 0x0094DECC
    decrement = 0x0094E09C

    print(f"\n{'#'*80}")
    print(f"  PART 1: Disassembly of chest_update function")
    print(f"  BLAZE 0x{func_start:08X} -> RAM 0x{blaze_to_ram(func_start):08X}")
    print(f"  Timer decrement at BLAZE 0x{decrement:08X}")
    print(f"{'#'*80}")

    # Dump from function start to well past the decrement
    count = (decrement - func_start) // 4 + 40  # function start to 40 instr past decrement
    dump_region(blaze, func_start, count, "chest_update full function")

    # =========================================================================
    # PART 2: Search for init patterns with various timer values
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 2: Search init patterns in BLAZE.ALL")
    print(f"  Looking for 'addiu $reg, $zero, VALUE' + 'sh $reg, offset($base)'")
    print(f"{'#'*80}")

    # Test multiple possible timer values
    for init_val in [50, 40, 60, 100, 20, 25, 30, 75, 150, 200, 250, 500, 1000]:
        for ent_off in [0x0010, 0x0012, 0x0014]:
            results = search_init_patterns(blaze, init_val, ent_off)
            if results:
                print(f"\n  VALUE={init_val} (0x{init_val:04X}), entity+0x{ent_off:04X}: {len(results)} matches")
                for addr1, addr2, reg in results:
                    ram1 = blaze_to_ram(addr1)
                    print(f"    BLAZE 0x{addr1:08X} (RAM 0x{ram1:08X}): addiu {REG[reg]}, $zero, {init_val}")
                    # Show context
                    dump_region(blaze, addr1 - 8, 10, "")

    # =========================================================================
    # PART 3: Search SLES for same patterns
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 3: Search init patterns in SLES (EXE)")
    print(f"{'#'*80}")

    for init_val in [50, 40, 60, 100, 20, 25, 30, 75, 150, 200, 250, 500, 1000]:
        for ent_off in [0x0010, 0x0012, 0x0014]:
            results = search_init_patterns(sles, init_val, ent_off)
            if results:
                print(f"\n  VALUE={init_val} (0x{init_val:04X}), entity+0x{ent_off:04X}: {len(results)} in SLES")
                for addr1, addr2, reg in results:
                    ram = (addr1 - 0x800) + 0x80010000 if addr1 >= 0x800 else addr1
                    print(f"    SLES 0x{addr1:08X} (RAM ~0x{ram:08X})")

    # =========================================================================
    # PART 4: Search for modulo/frequency code near the decrement
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 4: Modulo/frequency analysis around decrement")
    print(f"{'#'*80}")

    # Look at broader context: 80 instructions before decrement
    dump_region(blaze, decrement - 80*4, 100, "Extended context around timer decrement")

    # =========================================================================
    # PART 5: Search for comparison patterns (timestamp hypothesis)
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 5: Comparison patterns (slti/slt) in BLAZE.ALL")
    print(f"  Looking for comparisons with timer-relevant values")
    print(f"{'#'*80}")

    for comp in [50, 1000, 20, 100, 40, 60]:
        results = search_comparison_patterns(blaze, comp)
        # Filter to overlay region only (0x0091D80C - end)
        overlay_results = [r for r in results if r[0] >= 0x0091D80C]
        if overlay_results:
            print(f"\n  Comparison with {comp}: {len(overlay_results)} in overlay region")
            for addr, ptype, val in overlay_results[:10]:
                ram = blaze_to_ram(addr)
                print(f"    BLAZE 0x{addr:08X} (RAM 0x{ram:08X}): {ptype} {val}")

    # =========================================================================
    # PART 6: Look for the 0x3E8 pattern in raw data (not code)
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 6: Raw halfword 0x03E8 (1000) in data sections")
    print(f"{'#'*80}")

    # Search in the first 0x0091D80C bytes (data area, not overlay code)
    count_data = 0
    count_code = 0
    for i in range(0, len(blaze) - 2, 2):
        val = struct.unpack_from('<H', blaze, i)[0]
        if val == 0x03E8:
            if i < 0x0091D80C:
                count_data += 1
                if count_data <= 30:
                    # Check surrounding context
                    ctx = ""
                    if i >= 2:
                        prev = struct.unpack_from('<H', blaze, i-2)[0]
                        ctx += f" prev=0x{prev:04X}"
                    if i + 2 < len(blaze):
                        nxt = struct.unpack_from('<H', blaze, i+2)[0]
                        ctx += f" next=0x{nxt:04X}"
                    print(f"  DATA 0x{i:08X}: halfword 0x03E8{ctx}")
            else:
                count_code += 1
    print(f"\n  Total in data section: {count_data}")
    print(f"  Total in code section: {count_code}")

    # =========================================================================
    # PART 7: Search for value 50 (0x32) as halfword in data near timer-related offsets
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 7: Raw halfword 0x0032 (50) near timer-init code")
    print(f"{'#'*80}")

    # Look near the known init offsets from v12
    v12_offsets = [0x01BA5648, 0x01BA5780, 0x01BA5E48, 0x01BA5F80,
                   0x0257C018, 0x0257C1B4, 0x02B771D8, 0x02B77374,
                   0x02B78830, 0x02BC9B60, 0x02BC9CFC, 0x02BCBA84]

    for voff in v12_offsets:
        if voff + 4 <= len(blaze):
            word = struct.unpack_from('<I', blaze, voff)[0]
            d = disasm(word, blaze_to_ram(voff))
            print(f"  v12 offset 0x{voff:08X}: {d}")
            # Show surrounding context (8 instr before and after)
            dump_region(blaze, voff - 32, 16, f"Context for v12 offset 0x{voff:08X}")


if __name__ == '__main__':
    main()
