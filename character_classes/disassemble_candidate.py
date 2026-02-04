#!/usr/bin/env python3
"""
Disassemble candidate functions - Désassemble le code autour des candidats
"""

import struct

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"

CODE_START = 0x800
LOAD_ADDR = 0x80010000

# Candidats prometteurs trouvés par find_levelup_code.py
CANDIDATES = [
    0x80012D48,  # Candidat 1 - Boucle 8, SLL *8, LBU
    0x80014E88,  # Candidat 7
    0x80017670,  # Candidat 15 - Loop 7
]

def disassemble_mips(instr, addr):
    """Désassemble une instruction MIPS"""
    opcode = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    rd = (instr >> 11) & 0x1F
    shamt = (instr >> 6) & 0x1F
    funct = instr & 0x3F
    imm = instr & 0xFFFF
    target = instr & 0x3FFFFFF

    # Sign-extend immediate
    if imm & 0x8000:
        imm_signed = imm - 0x10000
    else:
        imm_signed = imm

    # Register names
    REG = [
        "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
        "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
        "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
        "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"
    ]

    # Special opcode (R-type)
    if opcode == 0x00:
        FUNCT_NAMES = {
            0x00: "SLL", 0x02: "SRL", 0x03: "SRA",
            0x08: "JR", 0x09: "JALR",
            0x20: "ADD", 0x21: "ADDU", 0x22: "SUB", 0x23: "SUBU",
            0x24: "AND", 0x25: "OR", 0x26: "XOR", 0x27: "NOR",
            0x2A: "SLT", 0x2B: "SLTU",
        }

        if funct in FUNCT_NAMES:
            name = FUNCT_NAMES[funct]

            if funct in [0x00, 0x02, 0x03]:  # Shifts
                if funct == 0x00 and rd == 0 and rt == 0 and shamt == 0:
                    return "NOP"
                return f"{name} {REG[rd]}, {REG[rt]}, {shamt}"
            elif funct in [0x08]:  # JR
                return f"{name} {REG[rs]}"
            elif funct in [0x09]:  # JALR
                return f"{name} {REG[rd]}, {REG[rs]}"
            else:  # ALU ops
                return f"{name} {REG[rd]}, {REG[rs]}, {REG[rt]}"

    # I-type and others
    OPCODES = {
        0x02: "J", 0x03: "JAL",
        0x04: "BEQ", 0x05: "BNE", 0x06: "BLEZ", 0x07: "BGTZ",
        0x08: "ADDI", 0x09: "ADDIU", 0x0A: "SLTI", 0x0B: "SLTIU",
        0x0C: "ANDI", 0x0D: "ORI", 0x0E: "XORI", 0x0F: "LUI",
        0x20: "LB", 0x21: "LH", 0x23: "LW", 0x24: "LBU", 0x25: "LHU",
        0x28: "SB", 0x29: "SH", 0x2B: "SW",
    }

    if opcode in OPCODES:
        name = OPCODES[opcode]

        if opcode in [0x02, 0x03]:  # J, JAL
            jump_addr = ((addr + 4) & 0xF0000000) | (target << 2)
            return f"{name} 0x{jump_addr:08X}"

        elif opcode in [0x04, 0x05, 0x06, 0x07]:  # Branches
            branch_addr = addr + 4 + (imm_signed << 2)
            return f"{name} {REG[rs]}, {REG[rt]}, 0x{branch_addr:08X}"

        elif opcode == 0x0F:  # LUI
            return f"{name} {REG[rt]}, 0x{imm:04X}"

        elif opcode in [0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E]:  # Immediate ALU
            return f"{name} {REG[rt]}, {REG[rs]}, {imm_signed}"

        elif opcode in [0x20, 0x21, 0x23, 0x24, 0x25]:  # Loads
            return f"{name} {REG[rt]}, {imm_signed}({REG[rs]})"

        elif opcode in [0x28, 0x29, 0x2B]:  # Stores
            return f"{name} {REG[rt]}, {imm_signed}({REG[rs]})"

    return f"??? (0x{instr:08X})"

def disassemble_function(data, start_addr, num_instrs=50):
    """Désassemble une fonction"""

    file_offset = (start_addr - LOAD_ADDR) + CODE_START

    print(f"DESASSEMBLAGE @ 0x{start_addr:08X} (file offset: 0x{file_offset:08X})")
    print("="*80)
    print()

    for i in range(num_instrs):
        offset = file_offset + (i * 4)

        if offset + 4 > len(data):
            break

        instr = struct.unpack('<I', data[offset:offset+4])[0]
        addr = start_addr + (i * 4)

        disasm = disassemble_mips(instr, addr)

        # Highlight interesting instructions
        marker = ""
        if "LBU" in disasm:
            marker = "  <-- LOAD BYTE (growth rate?)"
        elif "SLL" in disasm and (" 3" in disasm or " 2" in disasm):
            marker = "  <-- SHIFT (*8 ou *4)"
        elif "LUI" in disasm:
            marker = "  <-- LOAD UPPER (adresse table?)"
        elif "ADDIU" in disasm and ("8" in disasm or "6" in disasm or "7" in disasm):
            marker = "  <-- ADD (loop counter?)"

        print(f"  0x{addr:08X}: {disasm:40s} {marker}")

    print()

def main():
    print("="*80)
    print("DESASSEMBLAGE DES CANDIDATS")
    print("="*80)
    print()

    with open(SLES_PATH, 'rb') as f:
        data = f.read()

    for cand_addr in CANDIDATES:
        disassemble_function(data, cand_addr, num_instrs=60)
        print()

if __name__ == "__main__":
    main()
