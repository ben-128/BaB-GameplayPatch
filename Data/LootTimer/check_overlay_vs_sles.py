#!/usr/bin/env python3
"""
Check whether the despawn countdown code at RAM 0x80099BD4 is SLES code
or overlay code loaded from BLAZE.ALL.

SLES load_addr=0x80010000, code_size=0xCD800
So SLES covers RAM 0x80010000 - 0x800DD800
0x80099BD4 IS within SLES range -> file offset 0x800 + 0x89BD4 = 0x8A3D4

Key question: does RAM at that address match the SLES file?
If YES -> it's SLES code, patchable like the batch timer
If NO  -> it's been overwritten by a runtime overlay from BLAZE.ALL
"""

import gzip
import struct
from pathlib import Path

SLES_PATH = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")
SAVESTATE_PATH = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\CoffreSolo\SLES_008.45.000")
BLAZE_ALL_PATH = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")

SLES_LOAD_ADDR = 0x80010000
SLES_HEADER    = 0x800
RAM_OFFSET_IN_SAVESTATE = 0x1BA  # After gzip decompression

# The target: despawn countdown at RAM 0x80099BD4
TARGET_RAM_ADDR = 0x80099BD4
# MIPS instructions (big-endian word values):
#   lhu $v0, 0x14($s1)  = 0x96220014
#   addiu $v0, $v0, -1  = 0x2442FFFF
#   sh $v0, 0x14($s1)   = 0xA6220014
COUNTDOWN_SIG = bytes([
    0x14, 0x00, 0x22, 0x96,  # lhu $v0, 0x14($s1)
    0xFF, 0xFF, 0x42, 0x24,  # addiu $v0, $v0, -1
    0x14, 0x00, 0x22, 0xA6,  # sh $v0, 0x14($s1)
])

def disasm_word(w):
    """Minimal MIPS disassembler for common instructions."""
    op = (w >> 26) & 0x3F
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    rd = (w >> 11) & 0x1F
    imm = w & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
            '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
            '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
            '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

    if w == 0:
        return "nop"
    if op == 0x25:  # lhu
        return f"lhu {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x29:  # sh
        return f"sh {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x09:  # addiu
        return f"addiu {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x23:  # lw
        return f"lw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x2B:  # sw
        return f"sw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x0F:  # lui
        return f"lui {regs[rt]}, 0x{imm:04X}"
    if op == 0x04:  # beq
        return f"beq {regs[rs]}, {regs[rt]}, {simm}"
    if op == 0x05:  # bne
        return f"bne {regs[rs]}, {regs[rt]}, {simm}"
    if op == 0x0D:  # ori
        return f"ori {regs[rt]}, {regs[rs]}, 0x{imm:04X}"
    if op == 0x21:  # lh
        return f"lh {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x24:  # lbu
        return f"lbu {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x0A:  # slti
        return f"slti {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x07:  # bgtz
        return f"bgtz {regs[rs]}, {simm}"
    if op == 0x01:  # bgez/bltz
        if rt == 1:
            return f"bgez {regs[rs]}, {simm}"
        else:
            return f"bltz {regs[rs]}, {simm}"
    if op == 0x06:  # blez
        return f"blez {regs[rs]}, {simm}"
    if op == 0:  # R-type
        funct = w & 0x3F
        sa = (w >> 6) & 0x1F
        if funct == 0x25:
            return f"or {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if funct == 0x24:
            return f"and {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if funct == 0x21:
            return f"addu {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if funct == 0x23:
            return f"subu {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if funct == 0x08:
            return f"jr {regs[rs]}"
        if funct == 0x09:
            return f"jalr {regs[rd]}, {regs[rs]}"
        if funct == 0x00:
            return f"sll {regs[rd]}, {regs[rt]}, {sa}"
        if funct == 0x02:
            return f"srl {regs[rd]}, {regs[rt]}, {sa}"
        if funct == 0x03:
            return f"sra {regs[rd]}, {regs[rt]}, {sa}"
    if op == 0x03:  # jal
        target = (w & 0x03FFFFFF) << 2
        return f"jal 0x{target:08X}"
    if op == 0x02:  # j
        target = (w & 0x03FFFFFF) << 2
        return f"j 0x{target:08X}"
    return f"??? 0x{w:08X}"


def extract_ram(savestate_path):
    """Extract PSX RAM from ePSXe savestate."""
    raw = savestate_path.read_bytes()
    decompressed = gzip.decompress(raw)
    ram = decompressed[RAM_OFFSET_IN_SAVESTATE : RAM_OFFSET_IN_SAVESTATE + 2*1024*1024]
    return ram


def main():
    print("=" * 70)
    print("  Check: is 0x80099BD4 SLES code or overlay code?")
    print("=" * 70)

    # 1. Load SLES file
    sles_data = SLES_PATH.read_bytes()
    print(f"\nSLES file: {len(sles_data):,} bytes")

    # 2. Load savestate RAM
    ram = extract_ram(SAVESTATE_PATH)
    print(f"RAM extracted: {len(ram):,} bytes")

    # 3. Calculate offsets
    sles_code_offset = TARGET_RAM_ADDR - SLES_LOAD_ADDR  # 0x89BD4
    sles_file_offset = SLES_HEADER + sles_code_offset      # 0x8A3D4
    ram_offset = TARGET_RAM_ADDR - 0x80000000               # 0x99BD4

    print(f"\nTarget RAM address: 0x{TARGET_RAM_ADDR:08X}")
    print(f"SLES code offset:  0x{sles_code_offset:X}")
    print(f"SLES file offset:  0x{sles_file_offset:X}")
    print(f"RAM data offset:   0x{ram_offset:X}")
    print(f"SLES code range:   0x80010000 - 0x{SLES_LOAD_ADDR + 0xCD800:08X}")
    print(f"Target in range:   {'YES' if SLES_LOAD_ADDR <= TARGET_RAM_ADDR < SLES_LOAD_ADDR + 0xCD800 else 'NO'}")

    # 4. Compare RAM vs SLES around the target
    print(f"\n{'='*70}")
    print(f"  COMPARISON: RAM vs SLES at 0x{TARGET_RAM_ADDR:08X} (+/- 64 bytes)")
    print(f"{'='*70}")

    context = 64  # bytes before and after
    match_count = 0
    mismatch_count = 0

    for off in range(-context, context + 12, 4):
        addr = TARGET_RAM_ADDR + off
        ram_off = addr - 0x80000000
        sles_off = SLES_HEADER + (addr - SLES_LOAD_ADDR)

        if 0 <= ram_off < len(ram) and 0 <= sles_off + 4 <= len(sles_data):
            ram_word = struct.unpack_from('<I', ram, ram_off)[0]
            sles_word = struct.unpack_from('<I', sles_data, sles_off)[0]
            match = "==" if ram_word == sles_word else "!="
            if ram_word == sles_word:
                match_count += 1
            else:
                mismatch_count += 1

            marker = " <<<" if off == 0 else (" <<<+4" if off == 4 else (" <<<+8" if off == 8 else ""))
            dis = disasm_word(ram_word)
            print(f"  0x{addr:08X}  RAM={ram_word:08X}  SLES={sles_word:08X}  {match}  {dis}{marker}")

    print(f"\n  Match: {match_count}, Mismatch: {mismatch_count}")
    if mismatch_count == 0:
        print(f"  >>> CODE IS IDENTICAL - this is SLES code, NOT overlay!")
    else:
        print(f"  >>> CODE DIFFERS - this region was overwritten by an overlay!")

    # 5. Broader comparison: check larger region around 0x80099BD4
    print(f"\n{'='*70}")
    print(f"  BROADER CHECK: 256-byte region comparison")
    print(f"{'='*70}")

    check_start = TARGET_RAM_ADDR - 128
    matches = 0
    mismatches = 0
    for off in range(0, 256, 4):
        addr = check_start + off
        ram_off = addr - 0x80000000
        sles_off = SLES_HEADER + (addr - SLES_LOAD_ADDR)
        if 0 <= ram_off < len(ram) and 0 <= sles_off + 4 <= len(sles_data):
            ram_word = struct.unpack_from('<I', ram, ram_off)[0]
            sles_word = struct.unpack_from('<I', sles_data, sles_off)[0]
            if ram_word == sles_word:
                matches += 1
            else:
                mismatches += 1

    print(f"  {matches} matches, {mismatches} mismatches in 256 bytes")
    if mismatches > 0:
        print(f"\n  First mismatches:")
        count = 0
        for off in range(0, 256, 4):
            addr = check_start + off
            ram_off = addr - 0x80000000
            sles_off = SLES_HEADER + (addr - SLES_LOAD_ADDR)
            if 0 <= ram_off < len(ram) and 0 <= sles_off + 4 <= len(sles_data):
                ram_word = struct.unpack_from('<I', ram, ram_off)[0]
                sles_word = struct.unpack_from('<I', sles_data, sles_off)[0]
                if ram_word != sles_word:
                    print(f"    0x{addr:08X}  RAM={ram_word:08X}  SLES={sles_word:08X}  RAM:{disasm_word(ram_word)}")
                    count += 1
                    if count >= 10:
                        break

    # 6. Search for countdown signature in SLES file
    print(f"\n{'='*70}")
    print(f"  SEARCH: Countdown signature in SLES file")
    print(f"  Pattern: lhu $v0,0x14($s1) / addiu $v0,$v0,-1 / sh $v0,0x14($s1)")
    print(f"  Bytes: {COUNTDOWN_SIG.hex()}")
    print(f"{'='*70}")

    pos = 0
    found = []
    while True:
        pos = sles_data.find(COUNTDOWN_SIG, pos)
        if pos == -1:
            break
        ram_addr = SLES_LOAD_ADDR + (pos - SLES_HEADER)
        found.append((pos, ram_addr))
        pos += 4

    print(f"  Found {len(found)} occurrence(s) in SLES")
    for fpos, faddr in found:
        print(f"    SLES offset 0x{fpos:X} -> RAM 0x{faddr:08X}")

    # 7. Search for countdown signature in RAM (broader)
    print(f"\n{'='*70}")
    print(f"  SEARCH: Countdown signature in RAM dump")
    print(f"{'='*70}")

    pos = 0
    found_ram = []
    while True:
        pos = ram.find(COUNTDOWN_SIG, pos)
        if pos == -1:
            break
        found_ram.append(pos + 0x80000000)
        pos += 4

    print(f"  Found {len(found_ram)} occurrence(s) in RAM")
    for addr in found_ram:
        in_sles = SLES_LOAD_ADDR <= addr < SLES_LOAD_ADDR + 0xCD800
        print(f"    RAM 0x{addr:08X}  {'(in SLES range)' if in_sles else '(OUTSIDE SLES)'}")

    # 8. Also search for any lhu+addiu(-1)+sh pattern with offset 0x14 and ANY register
    print(f"\n{'='*70}")
    print(f"  SEARCH: ANY lhu $r,0x14($base) / addiu $r,$r,-1 / sh $r,0x14($base)")
    print(f"{'='*70}")

    # lhu rt, 0x14(rs): opcode=100101, imm=0x0014
    # Pattern: 0x9620_0014 | (rs << 21) | (rt << 16)
    # addiu rt, rt, -1: 0x2400_FFFF | (rt << 21) | (rt << 16)
    # sh rt, 0x14(rs):  0xA620_0014 | (rs << 21) | (rt << 16)

    sles_code = sles_data[SLES_HEADER:]
    found_patterns = []

    for i in range(0, len(sles_code) - 12, 4):
        w0 = struct.unpack_from('<I', sles_code, i)[0]
        w1 = struct.unpack_from('<I', sles_code, i + 4)[0]
        w2 = struct.unpack_from('<I', sles_code, i + 8)[0]

        # Check w0: lhu rt, 0x14(rs)
        if (w0 >> 26) != 0x25 or (w0 & 0xFFFF) != 0x0014:
            continue
        rs0 = (w0 >> 21) & 0x1F
        rt0 = (w0 >> 16) & 0x1F

        # Check w1: addiu rt, rt, -1
        if (w1 >> 26) != 0x09 or (w1 & 0xFFFF) != 0xFFFF:
            continue
        rs1 = (w1 >> 21) & 0x1F
        rt1 = (w1 >> 16) & 0x1F
        if rs1 != rt0 or rt1 != rt0:
            continue

        # Check w2: sh rt, 0x14(rs)
        if (w2 >> 26) != 0x29 or (w2 & 0xFFFF) != 0x0014:
            continue
        rs2 = (w2 >> 21) & 0x1F
        rt2 = (w2 >> 16) & 0x1F
        if rt2 != rt0 or rs2 != rs0:
            continue

        addr = SLES_LOAD_ADDR + i
        found_patterns.append((i, addr, rs0, rt0))

    print(f"  Found {len(found_patterns)} pattern(s)")
    for foff, faddr, base_reg, val_reg in found_patterns:
        regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
        print(f"    SLES+0x{foff:X} -> RAM 0x{faddr:08X}: "
              f"lhu {regs[val_reg]},0x14({regs[base_reg]}) / "
              f"addiu {regs[val_reg]},-1 / "
              f"sh {regs[val_reg]},0x14({regs[base_reg]})")

        # Show context: 4 instructions before and after
        print(f"      Context:")
        for ctx_off in range(-16, 24, 4):
            ci = foff + ctx_off
            if 0 <= ci < len(sles_code) - 4:
                cw = struct.unpack_from('<I', sles_code, ci)[0]
                caddr = SLES_LOAD_ADDR + ci
                marker = " <<<" if ctx_off in [0, 4, 8] else ""
                print(f"        0x{caddr:08X}: {cw:08X}  {disasm_word(cw)}{marker}")

    # 9. Search for BROADER pattern: addiu $reg,$reg,-1 near sh $reg,0x14($base)
    print(f"\n{'='*70}")
    print(f"  SEARCH: addiu $r,$r,-1 within 4 instrs of sh $r,0x14($base)")
    print(f"{'='*70}")

    found_loose = []
    for i in range(0, len(sles_code) - 4, 4):
        w = struct.unpack_from('<I', sles_code, i)[0]
        # Check: sh rt, 0x14(rs)
        if (w >> 26) != 0x29 or (w & 0xFFFF) != 0x0014:
            continue
        sh_rs = (w >> 21) & 0x1F
        sh_rt = (w >> 16) & 0x1F

        # Look backwards up to 4 instructions for addiu rt, rt, -1
        for back in range(1, 5):
            bi = i - back * 4
            if bi < 0:
                break
            bw = struct.unpack_from('<I', sles_code, bi)[0]
            if (bw >> 26) == 0x09 and (bw & 0xFFFF) == 0xFFFF:
                brs = (bw >> 21) & 0x1F
                brt = (bw >> 16) & 0x1F
                if brt == sh_rt and brs == sh_rt:
                    addr = SLES_LOAD_ADDR + i
                    found_loose.append((i, addr, sh_rs, sh_rt, back))
                    break

    regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
            '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
            '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
            '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

    print(f"  Found {len(found_loose)} pattern(s)")
    for foff, faddr, base_reg, val_reg, dist in found_loose:
        print(f"    RAM 0x{faddr:08X}: sh {regs[val_reg]},0x14({regs[base_reg]}) "
              f"with addiu -1 at -{dist} instrs")

    # 10. Also check entity+0x14 with offset 0x0014 in lhu/sh anywhere
    print(f"\n{'='*70}")
    print(f"  SEARCH: All 'sh $reg, 0x0014($reg)' in SLES")
    print(f"{'='*70}")

    sh_14_count = 0
    for i in range(0, len(sles_code) - 4, 4):
        w = struct.unpack_from('<I', sles_code, i)[0]
        if (w >> 26) == 0x29 and (w & 0xFFFF) == 0x0014:
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            addr = SLES_LOAD_ADDR + i
            print(f"    0x{addr:08X}: sh {regs[rt]}, 0x0014({regs[rs]})")
            sh_14_count += 1

    print(f"  Total: {sh_14_count} sh instructions with offset 0x14")


if __name__ == '__main__':
    main()
