#!/usr/bin/env python3
"""
Analyze MIPS code to find references to growth rates table
Cherche les instructions qui accèdent à l'adresse 0x8003B3FE
"""

import struct

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"

# PS-X EXE header info
CODE_START = 0x800  # Code starts after 2048 byte header
LOAD_ADDR = 0x80010000  # Base load address

# Target addresses
GROWTH_RATES_FILE_OFFSET = 0x0002BBFE
GROWTH_RATES_MEM_ADDR = 0x8003B3FE  # When loaded in memory

def file_offset_to_mem_addr(offset):
    """Convert file offset to memory address"""
    if offset < CODE_START:
        return None
    return LOAD_ADDR + (offset - CODE_START)

def mem_addr_to_file_offset(addr):
    """Convert memory address to file offset"""
    if addr < LOAD_ADDR:
        return None
    return (addr - LOAD_ADDR) + CODE_START

def disassemble_mips_instruction(instr, addr):
    """Basic MIPS disassembly for load/store instructions"""
    opcode = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    imm = instr & 0xFFFF

    # Sign-extend immediate
    if imm & 0x8000:
        imm = imm - 0x10000

    # Register names
    reg_names = [
        "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
        "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
        "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
        "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"
    ]

    rs_name = reg_names[rs]
    rt_name = reg_names[rt]

    # Load/store instructions
    opcodes = {
        0x20: "LB",   # Load Byte
        0x24: "LBU",  # Load Byte Unsigned
        0x21: "LH",   # Load Halfword
        0x25: "LHU",  # Load Halfword Unsigned
        0x23: "LW",   # Load Word
        0x28: "SB",   # Store Byte
        0x29: "SH",   # Store Halfword
        0x2B: "SW",   # Store Word
        0x0F: "LUI",  # Load Upper Immediate
        0x09: "ADDIU",# Add Immediate Unsigned
    }

    if opcode in opcodes:
        mnemonic = opcodes[opcode]

        if opcode == 0x0F:  # LUI
            return f"{mnemonic} {rt_name}, 0x{imm & 0xFFFF:04X}"

        elif opcode == 0x09:  # ADDIU
            return f"{mnemonic} {rt_name}, {rs_name}, {imm}"

        else:  # Load/Store
            # Calculate effective address if base is known
            # For now, just show the instruction
            return f"{mnemonic} {rt_name}, {imm}({rs_name})"

    return None

def find_address_references(data, target_addr):
    """Find instructions that might reference the target address"""

    print(f"Recherche de references a 0x{target_addr:08X}...")
    print()

    references = []

    # The address might be loaded in two ways:
    # 1. LUI + ADDIU (load upper + add lower)
    # 2. Direct offset from a base register

    upper = (target_addr >> 16) & 0xFFFF
    lower = target_addr & 0xFFFF

    # Sign-extend lower for ADDIU
    if lower & 0x8000:
        lower_signed = lower - 0x10000
        upper_adjusted = upper + 1  # LUI compensates
    else:
        lower_signed = lower
        upper_adjusted = upper

    print(f"Adresse cible: 0x{target_addr:08X}")
    print(f"  Upper (LUI): 0x{upper:04X}")
    print(f"  Lower (offset): {lower_signed} (0x{lower & 0xFFFF:04X})")
    print()

    # Scan code for LUI with matching upper
    for i in range(0, len(data) - 4, 4):
        instr = struct.unpack('<I', data[i:i+4])[0]
        opcode = (instr >> 26) & 0x3F

        # LUI (Load Upper Immediate)
        if opcode == 0x0F:
            imm = instr & 0xFFFF
            rt = (instr >> 16) & 0x1F

            if imm == upper or imm == upper_adjusted:
                file_offset = CODE_START + i
                mem_addr = file_offset_to_mem_addr(file_offset)

                # Look for following ADDIU or load/store
                found_match = False
                context_instrs = []

                for j in range(1, 10):  # Check next 10 instructions
                    if i + j*4 >= len(data):
                        break

                    next_instr = struct.unpack('<I', data[i+j*4:i+j*4+4])[0]
                    next_opcode = (next_instr >> 26) & 0x3F
                    next_rt = (next_instr >> 16) & 0x1F
                    next_rs = (next_instr >> 21) & 0x1F
                    next_imm = next_instr & 0xFFFF

                    # Sign-extend
                    if next_imm & 0x8000:
                        next_imm_signed = next_imm - 0x10000
                    else:
                        next_imm_signed = next_imm

                    disasm = disassemble_mips_instruction(next_instr, mem_addr + j*4)
                    if disasm:
                        context_instrs.append((j, disasm))

                    # ADDIU with same register
                    if next_opcode == 0x09 and next_rt == rt:
                        if abs(next_imm_signed - lower_signed) <= 64:
                            found_match = True
                            break

                    # Load/Store with same register as base
                    if next_opcode in [0x20, 0x24, 0x21, 0x25, 0x23, 0x28, 0x29, 0x2B]:
                        if next_rs == rt:
                            if abs(next_imm_signed - lower_signed) <= 64:
                                found_match = True
                                break

                if found_match:
                    references.append({
                        'file_offset': file_offset,
                        'mem_addr': mem_addr,
                        'lui_imm': imm,
                        'context': context_instrs
                    })

    return references

def main():
    print("="*80)
    print("ANALYSE MIPS - RECHERCHE DES GROWTH RATES")
    print("="*80)
    print()

    # Read SLES
    with open(SLES_PATH, 'rb') as f:
        data = f.read()

    code_data = data[CODE_START:]

    print(f"Fichier: {SLES_PATH}")
    print(f"Taille code: {len(code_data):,} bytes")
    print()

    # Find references to growth rates address
    refs = find_address_references(code_data, GROWTH_RATES_MEM_ADDR)

    print("="*80)
    print(f"REFERENCES TROUVEES: {len(refs)}")
    print("="*80)
    print()

    if not refs:
        print("Aucune reference directe trouvee.")
        print()
        print("Possibilites:")
        print("  1. L'adresse est calculee dynamiquement")
        print("  2. Les growth rates sont dans BLAZE.ALL, pas SLES")
        print("  3. L'offset 0x8003B3FE n'est pas les growth rates")
        print()
        print("Prochaine etape: Analyser avec Ghidra (voir GHIDRA_ANALYSIS_GUIDE.md)")
    else:
        for idx, ref in enumerate(refs):
            print(f"\nREFERENCE {idx+1}:")
            print(f"  File offset: 0x{ref['file_offset']:08X}")
            print(f"  Mem address: 0x{ref['mem_addr']:08X}")
            print(f"  LUI immediate: 0x{ref['lui_imm']:04X}")
            print()
            print("  Code context:")

            for offset, disasm in ref['context'][:10]:
                print(f"    +{offset*4:2d}: {disasm}")

            print()

    print("="*80)
    print("ANALYSE TERMINEE")
    print("="*80)
    print()

if __name__ == "__main__":
    main()
