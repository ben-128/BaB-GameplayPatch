#!/usr/bin/env python3
"""
Search the CoffreSolo overlay code for ALL timer decrement patterns.
We need to find which field is the REAL chest despawn timer.

Previous research suggested +0x12, our overlay analysis found +0x14.
The +0x14 patch didn't work, so let's find ALL decrement patterns.
"""

import gzip
import struct
from pathlib import Path

SAVESTATE_PATH = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\CoffreSolo\SLES_008.45.000")
RAM_OFFSET_IN_SAVESTATE = 0x1BA

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

def disasm_word(w):
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    rd = (w >> 11) & 0x1F
    imm = w & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    if w == 0:
        return "nop"
    if op == 0x25: return f"lhu {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x21: return f"lh {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x29: return f"sh {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x09: return f"addiu {REGS[rt]}, {REGS[rs]}, {simm}"
    if op == 0x23: return f"lw {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x2B: return f"sw {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x0F: return f"lui {REGS[rt]}, 0x{imm:04X}"
    if op == 0x04: return f"beq {REGS[rs]}, {REGS[rt]}, {simm}"
    if op == 0x05: return f"bne {REGS[rs]}, {REGS[rt]}, {simm}"
    if op == 0x0D: return f"ori {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    if op == 0x0A: return f"slti {REGS[rt]}, {REGS[rs]}, {simm}"
    if op == 0x07: return f"bgtz {REGS[rs]}, {simm}"
    if op == 0x06: return f"blez {REGS[rs]}, {simm}"
    if op == 0x01:
        if rt == 1: return f"bgez {REGS[rs]}, {simm}"
        return f"bltz {REGS[rs]}, {simm}"
    if op == 0x24: return f"lbu {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x20: return f"lb {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0x28: return f"sb {REGS[rt]}, 0x{imm:04X}({REGS[rs]})"
    if op == 0:
        funct = w & 0x3F
        sa = (w >> 6) & 0x1F
        if funct == 0x25: return f"or {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if funct == 0x24: return f"and {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if funct == 0x21: return f"addu {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if funct == 0x23: return f"subu {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if funct == 0x08: return f"jr {REGS[rs]}"
        if funct == 0x09: return f"jalr {REGS[rd]}, {REGS[rs]}"
        if funct == 0x00: return f"sll {REGS[rd]}, {REGS[rt]}, {sa}"
        if funct == 0x02: return f"srl {REGS[rd]}, {REGS[rt]}, {sa}"
        if funct == 0x03: return f"sra {REGS[rd]}, {REGS[rt]}, {sa}"
        if funct == 0x2A: return f"slt {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        if funct == 0x2B: return f"sltu {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
    if op == 0x03:
        target = (w & 0x03FFFFFF) << 2
        return f"jal 0x{target:08X}"
    if op == 0x02:
        target = (w & 0x03FFFFFF) << 2
        return f"j 0x{target:08X}"
    return f"??? 0x{w:08X}"


def extract_ram(savestate_path):
    raw = savestate_path.read_bytes()
    decompressed = gzip.decompress(raw)
    return decompressed[RAM_OFFSET_IN_SAVESTATE : RAM_OFFSET_IN_SAVESTATE + 2*1024*1024]


def main():
    ram = extract_ram(SAVESTATE_PATH)
    print(f"RAM extracted: {len(ram):,} bytes")

    # Overlay region: 0x80080000 - 0x800A1A5C
    overlay_start = 0x80000  # RAM offset
    overlay_end = 0xA1A5C
    overlay = ram[overlay_start:overlay_end]
    overlay_size = len(overlay)
    print(f"Overlay region: {overlay_size:,} bytes (0x80080000-0x800A1A5C)")

    # =================================================================
    # Search 1: ALL "addiu $reg, $reg, -1" instructions in overlay
    # =================================================================
    print(f"\n{'='*70}")
    print(f"  ALL addiu $r,$r,-1 in overlay (potential timer decrements)")
    print(f"{'='*70}")

    addiu_minus1 = []
    for i in range(0, overlay_size - 4, 4):
        w = struct.unpack_from('<I', overlay, i)[0]
        if (w >> 26) != 0x09:  # addiu
            continue
        if (w & 0xFFFF) != 0xFFFF:  # imm = -1
            continue
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        if rs != rt:  # addiu $r, $r, -1 (same reg)
            continue
        addr = 0x80080000 + i
        addiu_minus1.append((i, addr, rt))

    print(f"  Found {len(addiu_minus1)} addiu $r,$r,-1 instructions")

    # For each, look at surrounding context (what field is being decremented?)
    for off, addr, reg in addiu_minus1:
        # Look backwards for load (lhu/lh) and forwards for store (sh)
        load_info = None
        store_info = None

        # Look back up to 3 instructions for load
        for back in range(1, 4):
            bi = off - back * 4
            if bi < 0:
                break
            bw = struct.unpack_from('<I', overlay, bi)[0]
            bop = (bw >> 26) & 0x3F
            brt = (bw >> 16) & 0x1F
            brs = (bw >> 21) & 0x1F
            bimm = bw & 0xFFFF
            if bop in (0x25, 0x21) and brt == reg:  # lhu or lh into same reg
                load_info = (bi, brs, bimm, "lhu" if bop == 0x25 else "lh")
                break

        # Look forward up to 3 instructions for store
        for fwd in range(1, 4):
            fi = off + fwd * 4
            if fi >= overlay_size:
                break
            fw = struct.unpack_from('<I', overlay, fi)[0]
            fop = (fw >> 26) & 0x3F
            frt = (fw >> 16) & 0x1F
            frs = (fw >> 21) & 0x1F
            fimm = fw & 0xFFFF
            if fop == 0x29 and frt == reg:  # sh from same reg
                store_info = (fi, frs, fimm)
                break

        if load_info and store_info:
            l_off, l_base, l_imm, l_type = load_info
            s_off, s_base, s_imm = store_info

            # Only show if load and store use same base+offset (real decrement)
            if l_base == s_base and l_imm == s_imm:
                field_offset = l_imm
                base_reg = REGS[l_base]
                val_reg = REGS[reg]
                print(f"\n  0x{addr:08X}: {val_reg} -= 1  ->  {base_reg}+0x{field_offset:04X}")
                # Show context
                ctx_start = max(0, off - 5*4)
                ctx_end = min(overlay_size, off + 6*4)
                for ci in range(ctx_start, ctx_end, 4):
                    cw = struct.unpack_from('<I', overlay, ci)[0]
                    caddr = 0x80080000 + ci
                    marker = " <<<" if ci == off else ""
                    print(f"    0x{caddr:08X}: {cw:08X}  {disasm_word(cw)}{marker}")

    # =================================================================
    # Search 2: Specifically look for entity+0x12 access
    # =================================================================
    print(f"\n{'='*70}")
    print(f"  ALL loads/stores with offset 0x12 in overlay")
    print(f"{'='*70}")

    for i in range(0, overlay_size - 4, 4):
        w = struct.unpack_from('<I', overlay, i)[0]
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F

        if imm != 0x0012:
            continue

        if op in (0x21, 0x25, 0x29, 0x24, 0x20, 0x28):  # lh, lhu, sh, lbu, lb, sb
            addr = 0x80080000 + i
            names = {0x21: "lh", 0x25: "lhu", 0x29: "sh", 0x24: "lbu", 0x20: "lb", 0x28: "sb"}
            print(f"  0x{addr:08X}: {names[op]} {REGS[rt]}, 0x0012({REGS[rs]})")

    # =================================================================
    # Search 3: subu patterns (some timers use subtraction, not addiu -1)
    # =================================================================
    print(f"\n{'='*70}")
    print(f"  ALL subu near sh in overlay (alternative timer patterns)")
    print(f"{'='*70}")

    for i in range(0, overlay_size - 4, 4):
        w = struct.unpack_from('<I', overlay, i)[0]
        if (w >> 26) != 0 or (w & 0x3F) != 0x23:  # subu
            continue
        rd = (w >> 11) & 0x1F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F

        # Look forward for sh of the result
        for fwd in range(1, 4):
            fi = i + fwd * 4
            if fi >= overlay_size:
                break
            fw = struct.unpack_from('<I', overlay, fi)[0]
            if (fw >> 26) == 0x29:  # sh
                frt = (fw >> 16) & 0x1F
                frs = (fw >> 21) & 0x1F
                fimm = fw & 0xFFFF
                if frt == rd:  # storing the subu result
                    addr = 0x80080000 + i
                    print(f"  0x{addr:08X}: subu {REGS[rd]},{REGS[rs]},{REGS[rt]} "
                          f"-> sh {REGS[frt]},0x{fimm:04X}({REGS[frs]})")
                    break

    # =================================================================
    # Search 4: stores of value 1000 (0x3E8) - timer initialization
    # =================================================================
    print(f"\n{'='*70}")
    print(f"  ALL 'addiu $r,$zero,1000' + 'sh' in overlay (timer init)")
    print(f"{'='*70}")

    for i in range(0, overlay_size - 8, 4):
        w = struct.unpack_from('<I', overlay, i)[0]
        # addiu rt, $zero, 1000
        if (w >> 26) != 0x09:
            continue
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        if rs != 0 or imm != 0x03E8:
            continue

        addr = 0x80080000 + i
        # Look forward for sh
        for fwd in range(1, 6):
            fi = i + fwd * 4
            if fi >= overlay_size:
                break
            fw = struct.unpack_from('<I', overlay, fi)[0]
            if (fw >> 26) == 0x29:  # sh
                frt = (fw >> 16) & 0x1F
                frs = (fw >> 21) & 0x1F
                fimm = fw & 0xFFFF
                if frt == rt:
                    saddr = 0x80080000 + fi
                    print(f"  0x{addr:08X}: addiu {REGS[rt]},$zero,1000")
                    print(f"    -> 0x{saddr:08X}: sh {REGS[frt]},0x{fimm:04X}({REGS[frs]})")
                    # Show more context
                    for ci in range(max(0, i-8), min(overlay_size, fi+12), 4):
                        cw = struct.unpack_from('<I', overlay, ci)[0]
                        caddr = 0x80080000 + ci
                        marker = " <<<" if ci == i or ci == fi else ""
                        print(f"      0x{caddr:08X}: {cw:08X}  {disasm_word(cw)}{marker}")
                    break

    # =================================================================
    # Search 5: ALL stores of value ~1000 (900-1100 range)
    # =================================================================
    print(f"\n{'='*70}")
    print(f"  ALL 'addiu $r,$zero,N' + 'sh' where N in 900..1100")
    print(f"{'='*70}")

    for i in range(0, overlay_size - 8, 4):
        w = struct.unpack_from('<I', overlay, i)[0]
        if (w >> 26) != 0x09:
            continue
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        if rs != 0:
            continue
        if imm < 900 or imm > 1100:
            continue

        for fwd in range(1, 4):
            fi = i + fwd * 4
            if fi >= overlay_size:
                break
            fw = struct.unpack_from('<I', overlay, fi)[0]
            if (fw >> 26) == 0x29 and ((fw >> 16) & 0x1F) == rt:
                frs = (fw >> 21) & 0x1F
                fimm = fw & 0xFFFF
                addr = 0x80080000 + i
                saddr = 0x80080000 + fi
                print(f"  0x{addr:08X}: li {REGS[rt]},{imm} -> sh {REGS[rt]},0x{fimm:04X}({REGS[frs]})")
                break


if __name__ == '__main__':
    main()
