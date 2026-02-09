#!/usr/bin/env python3
"""Analyze the function pointer tables found by find_monster_dispatch.py"""
import gzip, struct
from pathlib import Path

SAVESTATE = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\combat\SLES_008.45.000")
EXE_PATH = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")
RAM_BASE = 0x80000000
RAM_SIZE = 0x200000

raw = gzip.open(str(SAVESTATE), 'rb').read()
ram = bytearray(raw[0x1BA : 0x1BA + RAM_SIZE])
exe = bytearray(Path(EXE_PATH).read_bytes())

def ru32(addr):
    return struct.unpack_from('<I', ram, addr - RAM_BASE)[0]

def exe_off(addr):
    return addr - 0x80010000 + 0x800

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

# =====================================================
# Table at 0x8003BDE0 (Dispatch #2/3)
# =====================================================
print("=== Table at 0x8003BDE0 (Dispatch #2/3 bytecode table) ===")
for i in range(40):
    addr = 0x8003BDE0 + i * 4
    val = ru32(addr)
    in_code = 0x80010000 <= val < 0x80040000
    marker = " (code ptr)" if in_code else ""
    if val == 0:
        marker = " (null)"
    print(f"  [{i:3d}] 0x{addr:08X}: 0x{val:08X}{marker}")

# =====================================================
# Table at 0x8003BE84 (Dispatch #5)
# =====================================================
print()
print("=== Table at 0x8003BE84 (Dispatch #5 bytecode table) ===")
for i in range(40):
    addr = 0x8003BE84 + i * 4
    val = ru32(addr)
    in_code = 0x80010000 <= val < 0x80040000
    marker = " (code ptr)" if in_code else ""
    if val == 0:
        marker = " (null)"
    print(f"  [{i:3d}] 0x{addr:08X}: 0x{val:08X}{marker}")

# =====================================================
# Find where $s6 is loaded in function 0x80017B6C
# =====================================================
print()
print("=== Function 0x80017B6C - searching for where $s6 is set ===")
for i in range(300):
    addr = 0x80017B6C + i * 4
    off = exe_off(addr)
    if off < 0 or off + 4 > len(exe):
        continue
    word = struct.unpack_from('<I', exe, off)[0]
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    writes_s6 = False
    if opcode == 0 and rd == 22 and funct in (0x21, 0x25, 0x24, 0x00, 0x23):
        writes_s6 = True
    elif opcode in (0x09, 0x0D, 0x0C, 0x0F, 0x20, 0x21, 0x23, 0x24, 0x25) and rt == 22:
        writes_s6 = True

    if writes_s6:
        if opcode == 0x0F:
            print(f"  0x{addr:08X}: lui $s6, 0x{imm:04X}")
            for j in range(1, 6):
                a2 = addr + j * 4
                o2 = exe_off(a2)
                if o2 + 4 > len(exe): break
                w2 = struct.unpack_from('<I', exe, o2)[0]
                op2 = (w2 >> 26) & 0x3F
                rs2 = (w2 >> 21) & 0x1F
                rt2 = (w2 >> 16) & 0x1F
                im2 = w2 & 0xFFFF
                si2 = im2 if im2 < 0x8000 else im2 - 0x10000
                if op2 == 0x09 and rs2 == 22 and rt2 == 22:
                    eff = (imm << 16) + si2
                    print(f"  0x{a2:08X}: addiu $s6, $s6, {si2} => $s6 = 0x{eff:08X}")
                    break
                elif op2 == 0x0D and rs2 == 22 and rt2 == 22:
                    eff = (imm << 16) | im2
                    print(f"  0x{a2:08X}: ori $s6, $s6, 0x{im2:04X} => $s6 = 0x{eff:08X}")
                    break
        elif opcode == 0 and funct == 0x21:
            print(f"  0x{addr:08X}: addu $s6, {REGS[rs]}, {REGS[rt]}")
        elif opcode == 0x09:
            print(f"  0x{addr:08X}: addiu $s6, {REGS[rs]}, {simm}")
        elif opcode == 0x23 and rt == 22:
            print(f"  0x{addr:08X}: lw $s6, {simm}({REGS[rs]})")
        else:
            print(f"  0x{addr:08X}: writes $s6 (opcode={opcode}, word=0x{word:08X})")

# =====================================================
# Verify: Dispatch #0 at 0x80017DD4 uses $s6 as table base
# Check what table it dispatches from
# Also look at the lw 2216($s2) at 0x80017F14
# =====================================================
print()
print("=== What table does Dispatch #0 use? ===")
# If $s6 = address of the 32-entry state table 0x8003B324, that would make sense
# with the sltiu $s0, 32 check at 0x80017DCC
print("  Dispatch #0: sltiu check is 32 entries")
print("  If $s6 = 0x8003B324 (state table), then this is the state machine dispatch")

# =====================================================
# Analyze the KEY function 0x800254E4 (the one that calls spell dispatch)
# This is the combat turn function - look at its full structure
# =====================================================
print()
print("=== Key function 0x800254E4 (spell dispatch caller) - what calls it? ===")

# Search for JAL 0x800254E4
target_field = (0x800254E4 & 0x0FFFFFFF) >> 2
expected_word = (0x03 << 26) | target_field
for addr in range(0x80010000, 0x80040000, 4):
    off = exe_off(addr)
    if off < 0 or off + 4 > len(exe):
        continue
    word = struct.unpack_from('<I', exe, off)[0]
    if word == expected_word:
        print(f"  jal 0x800254E4 found at 0x{addr:08X}")

# Also search for callers of the sibling functions
print()
print("=== Callers of sibling function 0x80023E7C ===")
target_field = (0x80023E7C & 0x0FFFFFFF) >> 2
expected_word = (0x03 << 26) | target_field
for addr in range(0x80010000, 0x80040000, 4):
    off = exe_off(addr)
    if off < 0 or off + 4 > len(exe):
        continue
    word = struct.unpack_from('<I', exe, off)[0]
    if word == expected_word:
        print(f"  jal 0x80023E7C found at 0x{addr:08X}")

# =====================================================
# Look at 0x80029A84 - interesting: has stride 0x9C + entity_validate
# =====================================================
print()
print("=== Function 0x80029A84 (stride 0x9C + entity_validate) ===")
print("  Disassembly (first 80 instructions):")
for i in range(80):
    addr = 0x80029A84 + i * 4
    off = exe_off(addr)
    if off < 0 or off + 4 > len(exe):
        break
    word = struct.unpack_from('<I', exe, off)[0]
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    # Quick disasm
    if word == 0:
        asm = "nop"
    elif opcode == 0x03:
        target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
        asm = f"jal     0x{target:08X}"
    elif opcode == 0x02:
        target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
        asm = f"j       0x{target:08X}"
    elif opcode == 0 and funct == 0x09:
        asm = f"jalr    {REGS[rd]},{REGS[rs]}"
    elif opcode == 0 and funct == 0x08:
        asm = f"jr      {REGS[rs]}"
    elif opcode == 0x09:
        asm = f"addiu   {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0F:
        asm = f"lui     {REGS[rt]},0x{imm:04X}"
    elif opcode == 0x23:
        asm = f"lw      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x24:
        asm = f"lbu     {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x25:
        asm = f"lhu     {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x04:
        t = addr + 4 + (simm << 2)
        asm = f"beq     {REGS[rs]},{REGS[rt]},0x{t:08X}"
    elif opcode == 0x05:
        t = addr + 4 + (simm << 2)
        asm = f"bne     {REGS[rs]},{REGS[rt]},0x{t:08X}"
    elif opcode == 0x2B:
        asm = f"sw      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x0C:
        asm = f"andi    {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0 and funct == 0x00:
        shamt = (word >> 6) & 0x1F
        asm = f"sll     {REGS[rd]},{REGS[rt]},{shamt}"
    elif opcode == 0 and funct == 0x21:
        asm = f"addu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 0x28:
        asm = f"sb      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x0A:
        asm = f"slti    {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0B:
        asm = f"sltiu   {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x29:
        asm = f"sh      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x0D:
        asm = f"ori     {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0 and funct == 0x2B:
        asm = f"sltu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 0x06:
        t = addr + 4 + (simm << 2)
        asm = f"blez    {REGS[rs]},0x{t:08X}"
    elif opcode == 0x07:
        t = addr + 4 + (simm << 2)
        asm = f"bgtz    {REGS[rs]},0x{t:08X}"
    else:
        asm = f"0x{word:08X}"

    marker = ""
    if "0x80026840" in asm: marker = "  <-- entity_validate"
    elif ",156" in asm: marker = "  <-- stride 0x9C"
    elif "jalr" in asm: marker = "  <-- INDIRECT CALL"
    print(f"    0x{addr:08X}: {asm:48s}{marker}")

# =====================================================
# Overlay lbu at 0x800CF434: lbu $s1, 45($v0)
# This reads offset 0x2D! Let's see context
# =====================================================
print()
print("=== Overlay code at 0x800CF434: lbu $s1, 45($v0) - reads stat +0x2D ===")
for i in range(-20, 30):
    addr = 0x800CF434 + i * 4
    idx = addr - RAM_BASE
    if idx < 0 or idx + 4 > len(ram):
        continue
    word = struct.unpack_from('<I', ram, idx)[0]
    # Quick decode
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    if word == 0:
        asm = "nop"
    elif opcode == 0x03:
        target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
        asm = f"jal     0x{target:08X}"
    elif opcode == 0x02:
        target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
        asm = f"j       0x{target:08X}"
    elif opcode == 0 and funct == 0x09:
        asm = f"jalr    {REGS[rd]},{REGS[rs]}"
    elif opcode == 0 and funct == 0x08:
        asm = f"jr      {REGS[rs]}"
    elif opcode == 0x09:
        asm = f"addiu   {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0F:
        asm = f"lui     {REGS[rt]},0x{imm:04X}"
    elif opcode == 0x23:
        asm = f"lw      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x24:
        asm = f"lbu     {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x25:
        asm = f"lhu     {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x04:
        t = addr + 4 + (simm << 2)
        asm = f"beq     {REGS[rs]},{REGS[rt]},0x{t:08X}"
    elif opcode == 0x05:
        t = addr + 4 + (simm << 2)
        asm = f"bne     {REGS[rs]},{REGS[rt]},0x{t:08X}"
    elif opcode == 0x2B:
        asm = f"sw      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x0C:
        asm = f"andi    {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0 and funct == 0x00:
        shamt = (word >> 6) & 0x1F
        asm = f"sll     {REGS[rd]},{REGS[rt]},{shamt}"
    elif opcode == 0 and funct == 0x21:
        asm = f"addu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 0x28:
        asm = f"sb      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x0A:
        asm = f"slti    {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0D:
        asm = f"ori     {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0 and funct == 0x2B:
        asm = f"sltu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 0x20:
        asm = f"lb      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x21:
        asm = f"lh      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0 and funct == 0x23:
        asm = f"subu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 1:
        t = addr + 4 + (simm << 2)
        rt_val = (word >> 16) & 0x1F
        if rt_val == 1:
            asm = f"bgez    {REGS[rs]},0x{t:08X}"
        elif rt_val == 0:
            asm = f"bltz    {REGS[rs]},0x{t:08X}"
        else:
            asm = f"REGIMM  0x{word:08X}"
    else:
        asm = f"0x{word:08X}"

    marker = ""
    if addr == 0x800CF434: marker = "  <-- lbu $s1, 45($v0) !!!"
    elif "jalr" in asm: marker = "  <-- INDIRECT CALL"
    print(f"    0x{addr:08X}: {asm:48s}{marker}")

# =====================================================
# Also check the combat handlers at 0x80027730 etc (lhu $v1, 42($v1))
# These are INSIDE the handler range - they read stat+0x2A!
# =====================================================
print()
print("=== Combat handler code reading stat field +0x2A ===")
print("  0x800276B0, 0x800277A8, 0x800278A0, 0x80027998 all read lhu $v1, 42($v1)")
print("  These ARE combat handler functions (in range 0x800270B8-0x80029E80)")
print("  They read the 96-byte stat entry's field 0x2A (= elemental table)")
print()

# Check which handler indices these correspond to
handler_table = 0x8003C1B0
for i in range(55):
    h = ru32(handler_table + i * 4)
    if h in (0x800276B0, 0x800277A8, 0x800278A0, 0x80027998):
        print(f"  handler[{i}] = 0x{h:08X}")
