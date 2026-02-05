"""
Deep analysis of specific code regions found in first pass.
Focus on 0x029E24 which has type 0x18 near Stone Bullet, Magic Missile, Sleep.
"""

import struct

EXE_PATH = r"D:\projets\Bab_Gameplay_Patch\ghidra_work\SLES_008.45"
HEADER_SIZE = 0x800

# MIPS opcodes
OPCODES = {
    0x00: "special", 0x01: "regimm", 0x02: "j", 0x03: "jal",
    0x04: "beq", 0x05: "bne", 0x06: "blez", 0x07: "bgtz",
    0x08: "addi", 0x09: "addiu", 0x0A: "slti", 0x0B: "sltiu",
    0x0C: "andi", 0x0D: "ori", 0x0E: "xori", 0x0F: "lui",
    0x10: "cop0", 0x11: "cop1", 0x12: "cop2", 0x13: "cop3",
    0x20: "lb", 0x21: "lh", 0x22: "lwl", 0x23: "lw",
    0x24: "lbu", 0x25: "lhu", 0x26: "lwr", 0x27: "lwu",
    0x28: "sb", 0x29: "sh", 0x2A: "swl", 0x2B: "sw",
}

SPECIAL_FUNCS = {
    0x00: "sll", 0x02: "srl", 0x03: "sra", 0x04: "sllv",
    0x06: "srlv", 0x07: "srav", 0x08: "jr", 0x09: "jalr",
    0x0C: "syscall", 0x0D: "break", 0x10: "mfhi", 0x11: "mthi",
    0x12: "mflo", 0x13: "mtlo", 0x18: "mult", 0x19: "multu",
    0x1A: "div", 0x1B: "divu", 0x20: "add", 0x21: "addu",
    0x22: "sub", 0x23: "subu", 0x24: "and", 0x25: "or",
    0x26: "xor", 0x27: "nor", 0x2A: "slt", 0x2B: "sltu",
}

REGS = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
        "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]

def disasm(instr, addr):
    """Basic MIPS disassembler."""
    opcode = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    rd = (instr >> 11) & 0x1F
    shamt = (instr >> 6) & 0x1F
    funct = instr & 0x3F
    imm = instr & 0xFFFF
    target = instr & 0x3FFFFFF

    if imm & 0x8000:
        imm_signed = imm - 0x10000
    else:
        imm_signed = imm

    if opcode == 0x00:  # SPECIAL
        fname = SPECIAL_FUNCS.get(funct, f"special_{funct:02X}")
        if funct == 0x00 and rd == 0 and rt == 0 and shamt == 0:
            return "nop"
        elif funct in [0x00, 0x02, 0x03]:  # shifts
            return f"{fname} {REGS[rd]}, {REGS[rt]}, {shamt}"
        elif funct in [0x08, 0x09]:  # jr/jalr
            return f"{fname} {REGS[rs]}"
        elif funct in [0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B]:
            return f"{fname} {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        else:
            return f"{fname} ..."
    elif opcode == 0x02:  # J
        return f"j 0x{(addr & 0xF0000000) | (target << 2):08X}"
    elif opcode == 0x03:  # JAL
        return f"jal 0x{(addr & 0xF0000000) | (target << 2):08X}"
    elif opcode in [0x04, 0x05]:  # BEQ/BNE
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        branch_target = addr + 4 + (imm_signed << 2)
        return f"{op_name} {REGS[rs]}, {REGS[rt]}, 0x{branch_target:08X}"
    elif opcode in [0x06, 0x07]:  # BLEZ/BGTZ
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        branch_target = addr + 4 + (imm_signed << 2)
        return f"{op_name} {REGS[rs]}, 0x{branch_target:08X}"
    elif opcode in [0x08, 0x09, 0x0A, 0x0B]:  # ADDI/ADDIU/SLTI/SLTIU
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        if rs == 0:  # li pseudo-instruction
            return f"li {REGS[rt]}, 0x{imm:04X}  ; {imm}"
        return f"{op_name} {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}  ; {imm_signed}"
    elif opcode in [0x0C, 0x0D, 0x0E]:  # ANDI/ORI/XORI
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        if opcode == 0x0D and rs == 0:  # li pseudo-instruction
            return f"li {REGS[rt]}, 0x{imm:04X}  ; {imm}"
        return f"{op_name} {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    elif opcode == 0x0F:  # LUI
        return f"lui {REGS[rt]}, 0x{imm:04X}"
    elif opcode in [0x20, 0x21, 0x23, 0x24, 0x25]:  # LB/LH/LW/LBU/LHU
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        return f"{op_name} {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode in [0x28, 0x29, 0x2B]:  # SB/SH/SW
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        return f"{op_name} {REGS[rt]}, {imm_signed}({REGS[rs]})"
    else:
        op_name = OPCODES.get(opcode, f"op_{opcode:02X}")
        return f"{op_name} 0x{instr:08X}"

def analyze_region(data, file_offset, count=64):
    """Disassemble a region of code."""
    # PS1 load address is typically 0x80010000
    base_addr = 0x80010000 + file_offset

    print(f"\n{'='*70}")
    print(f"Disassembly at file offset 0x{file_offset:06X} (RAM: 0x{base_addr:08X})")
    print(f"{'='*70}")

    for i in range(count):
        offset = file_offset + i * 4
        if offset + 4 > len(data):
            break
        instr = struct.unpack('<I', data[offset:offset+4])[0]
        addr = base_addr + i * 4
        asm = disasm(instr, addr)

        # Highlight spell IDs and monster type IDs
        highlight = ""
        imm = instr & 0xFFFF
        if imm == 0x18:
            highlight = " <-- Monster type 0x18 (Goblin-Shaman)!"
        elif imm == 0x03:
            highlight = " <-- Spell ID 0x03 (Stone Bullet)!"
        elif imm == 0x08:
            highlight = " <-- Spell ID 0x08 (Magic Missile)!"
        elif imm == 0x1F:
            highlight = " <-- Spell ID 0x1F (Healing)!"
        elif imm == 0xA0:
            highlight = " <-- Spell ID 0xA0 (Sleep)!"

        print(f"0x{addr:08X}: {instr:08X}  {asm:40}{highlight}")

def main():
    with open(EXE_PATH, 'rb') as f:
        data = f.read()

    code_data = data[HEADER_SIZE:]

    # Key locations from first analysis (file offsets in code section)
    locations = [
        (0x029E24 - 64, "Type 0x18 near Sleep, Magic Missile, Stone Bullet"),
        (0x0235F4 - 64, "Type 0x18 near Healing, Magic Missile, Stone Bullet"),
        (0x02368C - 64, "Type 0x18 near Healing, Magic Missile, Stone Bullet"),
        (0x009BA8 - 64, "Type 0x18 near Sleep, Magic Missile, Stone Bullet"),
    ]

    for offset, desc in locations:
        print(f"\n\n*** {desc} ***")
        analyze_region(code_data, offset, 48)

    # Also look at the jump table at 0x02BDE0
    print("\n\n*** Jump Table Analysis (0x02BDE0) ***")
    table_offset = 0x02BDE0
    print(f"Jump table at file offset 0x{table_offset:06X}")
    print("Entries for monster types 0x16-0x1A:")
    for i in range(0x16, 0x1B):
        entry_offset = table_offset + i * 4
        if entry_offset + 4 <= len(code_data):
            addr = struct.unpack('<I', code_data[entry_offset:entry_offset+4])[0]
            file_off = (addr - 0x80010000) if addr >= 0x80010000 else 0
            print(f"  Type 0x{i:02X}: jump to 0x{addr:08X} (file offset ~0x{file_off:06X})")

if __name__ == "__main__":
    main()
