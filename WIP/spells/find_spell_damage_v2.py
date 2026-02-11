# -*- coding: cp1252 -*-
"""
Spell damage formula search v2 - Deep analysis of combat action handlers.

Key findings from v1:
- 0x80027764, 0x8002785C, 0x80027954, 0x80027A4C: lhu $v0, 0x18($a1) near mult
  These are INSIDE combat action handlers [10]-[14] (0x800276B0-0x80027A90 range)
- They load a halfword at offset 0x18 and multiply
- Handlers 0-1 use offset 0x14C/0x14E (entity stat area)
- Need to understand what $a1 points to at the lhu instruction
- 0x80026840 called by almost every handler -- need to understand it

Also investigate:
- 0x80023F04: lbu $v0, 0x18($v0) near entity+0x156 load
- 0x800260A8: div $s6, $v0 where $v0 = lbu 0x1E (spell +0x1E field?)
- The overlay call 0x80073B2C from spell_select function
"""

import struct
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
EXE_PATH = os.path.join(PROJECT_DIR,
    "Blaze  Blade - Eternal Quest (Europe)", "extract", "SLES_008.45")

with open(EXE_PATH, 'rb') as f:
    exe_data = f.read()

REG_NAMES = [
    "$zero","$at","$v0","$v1","$a0","$a1","$a2","$a3",
    "$t0","$t1","$t2","$t3","$t4","$t5","$t6","$t7",
    "$s0","$s1","$s2","$s3","$s4","$s5","$s6","$s7",
    "$t8","$t9","$k0","$k1","$gp","$sp","$fp","$ra"
]

def sign_extend_16(val):
    if val & 0x8000:
        return val - 0x10000
    return val

def disasm_one(word, addr):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    imms = sign_extend_16(imm)
    target = (word & 0x3FFFFFF) << 2

    if word == 0:
        return "nop"
    if op == 0:
        if funct == 0x20: return "add %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x21: return "addu %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x22: return "sub %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x23: return "subu %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x24: return "and %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x25: return "or %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x26: return "xor %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x27: return "nor %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x2A: return "slt %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x2B: return "sltu %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x00: return "sll %s, %s, %d" % (REG_NAMES[rd], REG_NAMES[rt], shamt)
        if funct == 0x02: return "srl %s, %s, %d" % (REG_NAMES[rd], REG_NAMES[rt], shamt)
        if funct == 0x03: return "sra %s, %s, %d" % (REG_NAMES[rd], REG_NAMES[rt], shamt)
        if funct == 0x04: return "sllv %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rt], REG_NAMES[rs])
        if funct == 0x06: return "srlv %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rt], REG_NAMES[rs])
        if funct == 0x07: return "srav %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rt], REG_NAMES[rs])
        if funct == 0x08: return "jr %s" % REG_NAMES[rs]
        if funct == 0x09: return "jalr %s, %s" % (REG_NAMES[rd], REG_NAMES[rs])
        if funct == 0x0C: return "syscall"
        if funct == 0x10: return "mfhi %s" % REG_NAMES[rd]
        if funct == 0x11: return "mthi %s" % REG_NAMES[rs]
        if funct == 0x12: return "mflo %s" % REG_NAMES[rd]
        if funct == 0x13: return "mtlo %s" % REG_NAMES[rs]
        if funct == 0x18: return "mult %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x19: return "multu %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x1A: return "div %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x1B: return "divu %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        return "R-type funct=0x%02X" % funct
    if op == 0x02:
        return "j 0x%08X" % ((addr & 0xF0000000) | target)
    if op == 0x03:
        return "jal 0x%08X" % ((addr & 0xF0000000) | target)
    if op == 0x04: return "beq %s, %s, 0x%08X" % (REG_NAMES[rs], REG_NAMES[rt], addr + 4 + (imms << 2))
    if op == 0x05: return "bne %s, %s, 0x%08X" % (REG_NAMES[rs], REG_NAMES[rt], addr + 4 + (imms << 2))
    if op == 0x06: return "blez %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
    if op == 0x07: return "bgtz %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
    if op == 0x01:
        if rt == 0: return "bltz %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        if rt == 1: return "bgez %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        return "REGIMM rt=%d" % rt
    if op == 0x08: return "addi %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x09: return "addiu %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0A: return "slti %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0B: return "sltiu %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0C: return "andi %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0D: return "ori %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0E: return "xori %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0F: return "lui %s, 0x%04X" % (REG_NAMES[rt], imm)
    if op == 0x20: return "lb %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x21: return "lh %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x23: return "lw %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x24: return "lbu %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x25: return "lhu %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x28: return "sb %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x29: return "sh %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x2B: return "sw %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x22: return "lwl %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x26: return "lwr %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x10: return "COP0 (0x%08X)" % word
    if op == 0x12: return "COP2/GTE (0x%08X)" % word
    return "??? op=0x%02X (0x%08X)" % (op, word)


def ram_to_file(ram_addr):
    return (ram_addr - 0x80010000) + 0x800

def read_word(file_off):
    if file_off < 0 or file_off + 4 > len(exe_data):
        return None
    return struct.unpack_from('<I', exe_data, file_off)[0]

def disasm_range(ram_start, ram_end, label=""):
    if label:
        print("\n" + "=" * 70)
        print("  %s" % label)
        print("=" * 70)
    for addr in range(ram_start, ram_end, 4):
        foff = ram_to_file(addr)
        w = read_word(foff)
        if w is None:
            continue
        asm = disasm_one(w, addr)
        print("  0x%08X: %08X  %s" % (addr, w, asm))


# ============================================================
# SECTION 1: Function 0x80026840 (called by nearly all handlers)
# ============================================================

print("=" * 70)
print("SECTION 1: Function 0x80026840 (miss/hit check?)")
print("=" * 70)
disasm_range(0x80026840, 0x80026A90, "0x80026840 - called by all handlers")


# ============================================================
# SECTION 2: Combat action handler [10] = 0x800276B0 (has the 0x18 load pattern)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 2: Handler [10] = 0x800276B0 (contains lhu $v0, 0x18($a1))")
print("=" * 70)
disasm_range(0x800276B0, 0x800277A8, "Handler [10] - healing/damage with 0x18 field")


# ============================================================
# SECTION 3: Handler [11] = 0x800277A8 (also has 0x18 pattern)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 3: Handler [11] = 0x800277A8")
print("=" * 70)
disasm_range(0x800277A8, 0x800278A0, "Handler [11]")


# ============================================================
# SECTION 4: Handler [12] = 0x800278A0 (also has 0x18 pattern)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 4: Handler [12] = 0x800278A0")
print("=" * 70)
disasm_range(0x800278A0, 0x80027998, "Handler [12]")


# ============================================================
# SECTION 5: Handler [13] = 0x80027998 (also has 0x18 pattern)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 5: Handler [13] = 0x80027998")
print("=" * 70)
disasm_range(0x80027998, 0x80027A90, "Handler [13]")


# ============================================================
# SECTION 6: Handler [14] = 0x80027A90 - larger handler
# ============================================================

print("\n" + "=" * 70)
print("SECTION 6: Handler [14] = 0x80027A90")
print("=" * 70)
disasm_range(0x80027A90, 0x80027BEC, "Handler [14]")


# ============================================================
# SECTION 7: Handlers [15]-[19] -- check for different damage patterns
# ============================================================

print("\n" + "=" * 70)
print("SECTION 7: Handler [15] = 0x80027BEC (bigger handler)")
print("=" * 70)
disasm_range(0x80027BEC, 0x80027D1C, "Handler [15]")


# ============================================================
# SECTION 8: The function 0x80073B2C called from spell_select
# This is in overlay space - cannot read from EXE
# ============================================================

print("\n" + "=" * 70)
print("SECTION 8: 0x80073B2C is overlay code (not in EXE)")
print("  Spell_select (0x80026A90) calls overlay 0x80073B2C with:")
print("  $a0=entity_ptr, $a1=spell_id, $a2=byte_11, $a3=byte_12")
print("  Overlay handles spell execution, including damage calculation")
print("=" * 70)


# ============================================================
# SECTION 9: Area around 0x80023F04: lbu $v0, 0x18($v0)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 9: 0x80023E7C - Equipment/buff function (has lbu 0x18)")
print("=" * 70)
disasm_range(0x80023E7C, 0x80024024, "0x80023E7C function with lbu 0x18")


# ============================================================
# SECTION 10: Area around 0x800260A8 - div with lbu 0x1E
# ============================================================

print("\n" + "=" * 70)
print("SECTION 10: Region around 0x80026000 (attack damage calculation?)")
print("=" * 70)
disasm_range(0x80025F00, 0x80026200, "0x80025F00 - possible damage calc area")


# ============================================================
# SECTION 11: Handler [0] and [1] detailed - base attack handlers
# ============================================================

print("\n" + "=" * 70)
print("SECTION 11: Handler [0] = 0x800270B8 and [1] = 0x800271C8")
print("  These access entity+0x14C/0x14E (ATK/DEF related)")
print("=" * 70)
# Already dumped in v1, but check the key offsets:
# Handler [0] loads: lhu +0x126, sh +0x14C, lh +0x148
# Does it use +0x18 at all? Let's check the full handlers

disasm_range(0x800270B8, 0x800271C8, "Handler [0] - Physical attack?")
disasm_range(0x800271C8, 0x800272D8, "Handler [1] - Physical attack variant?")


# ============================================================
# SECTION 12: Big handlers in 0x80029A84 range (handlers [51]-[54])
# ============================================================

print("\n" + "=" * 70)
print("SECTION 12: Handler [51] = 0x80029A84 (big handler)")
print("=" * 70)
disasm_range(0x80029A84, 0x80029D74, "Handler [51]")


# ============================================================
# SECTION 13: Handler [50] = 0x80029980 (last normal)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 13: Handler [50] = 0x80029980")
print("=" * 70)
disasm_range(0x80029980, 0x80029A84, "Handler [50]")


# ============================================================
# SECTION 14: Look for what calls combat handlers
# The dispatch that indexes into 0x8003C1B0 table
# ============================================================

print("\n" + "=" * 70)
print("SECTION 14: Search for code that loads from handler table 0x8003C1B0")
print("  Looking for lui 0x8004 + lw patterns that access 0x8003C1B0")
print("=" * 70)

# The table is at RAM 0x8003C1B0
# Access pattern: lui $reg, 0x8004 + lw $reg, -0x3E50($reg)
# or: lui $reg, 0x8003 + lw $reg, 0xC1B0+offset($reg)
# Signed offset: 0xC1B0 = -15952 from 0x8004
# Actually: 0x8003C1B0. lui 0x8004 + addiu -15952 = 0x8004 + 0xC1B0 (unsigned)
# Wait: 0x8003C1B0 = 0x80040000 + (-0x3E50) = 0x80040000 - 0x3E50
# So pattern is: lui 0x8004 -> reg, then lw reg2, -0x3E50(reg) with sll index
# OR: addiu to form base, then lw

# Simpler: search for the constant 0x8003C1B0 in two parts
# lui 0x8004, offset = 0xC1B0 - 0x10000 = -0x3E50 (signed)
# So: lw $reg, -0x3E50($reg_with_0x80040000) i.e. offset = 0xC1B0

# Search for any lw with offset that would reach 0xC1B0 range
# Actually let's search for lui 0x8004 near sll (index scaling) near jalr (jump to handler)
for foff in range(0x800, len(exe_data) - 4, 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    # Look for addiu $reg, $reg, -15952 (= 0xC1B0 as signed = actually unsigned imm)
    if op == 0x09:  # addiu
        imm = w & 0xFFFF
        imms = sign_extend_16(imm)
        if imms == -15952:  # 0xC1B0 as signed from 0x8004xxxx
            ram = (foff - 0x800) + 0x80010000
            print("  addiu with -15952 at 0x%08X" % ram)
    # Look for lui $X, 0x8004 (table base high)
    if op == 0x0F:
        imm = w & 0xFFFF
        rt = (w >> 16) & 0x1F
        if imm == 0x8004:
            # Check next few instr for offset -15952 or +0xC1B0
            for d in range(1, 8):
                nfoff = foff + d * 4
                if nfoff + 4 > len(exe_data):
                    break
                nw = struct.unpack_from('<I', exe_data, nfoff)[0]
                nop = (nw >> 26) & 0x3F
                nimm = sign_extend_16(nw & 0xFFFF)
                if nop in (0x09, 0x23) and nimm == -15952:  # addiu/lw with this offset
                    nram = (nfoff - 0x800) + 0x80010000
                    ram = (foff - 0x800) + 0x80010000
                    print("  ** TABLE ACCESS at 0x%08X: lui 0x8004 -> lw/addiu -15952 at 0x%08X" % (ram, nram))
                    # Print context
                    for dd in range(-2, 12):
                        cf = foff + dd * 4
                        if cf < 0x800 or cf + 4 > len(exe_data):
                            continue
                        cw = struct.unpack_from('<I', exe_data, cf)[0]
                        cram = (cf - 0x800) + 0x80010000
                        casm = disasm_one(cw, cram)
                        print("    0x%08X: %08X  %s" % (cram, cw, casm))


# ============================================================
# SECTION 15: The dispatch wrapper at 0x80024414
# ============================================================

print("\n" + "=" * 70)
print("SECTION 15: Dispatch wrapper at 0x80024414")
print("  (called from overlay with entity+0x146 counter)")
print("=" * 70)
disasm_range(0x80024414, 0x80024494, "0x80024414 - dispatch wrapper")


# ============================================================
# SECTION 16: Full analysis around handler [16] and beyond
# Handlers 15-19 cover the "big" spell effect handlers
# ============================================================

print("\n" + "=" * 70)
print("SECTION 16: Handler [16] = 0x80027D1C through [19] = 0x800280E0")
print("=" * 70)
disasm_range(0x80027D1C, 0x80027E6C, "Handler [16]")
disasm_range(0x80027E6C, 0x80027F9C, "Handler [17]")
disasm_range(0x80027F9C, 0x800280E0, "Handler [18]")
disasm_range(0x800280E0, 0x80028224, "Handler [19]")

print("\n" + "=" * 70)
print("DONE - v2 analysis complete")
print("=" * 70)
