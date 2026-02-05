"""
Analyze the Goblin-Shaman AI handler code at 0x8001C218.
"""

import struct

EXE_PATH = r"D:\projets\Bab_Gameplay_Patch\ghidra_work\SLES_008.45"
HEADER_SIZE = 0x800

REGS = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
        "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]

SPELL_IDS = {
    0x03: "Stone Bullet",
    0x08: "Magic Missile",
    0x1F: "Healing",
    0xA0: "Sleep",
}

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

    imm_signed = imm - 0x10000 if imm & 0x8000 else imm

    if opcode == 0x00:  # SPECIAL
        if funct == 0x00 and rd == 0 and rt == 0 and shamt == 0:
            return "nop"
        elif funct == 0x08:
            return f"jr {REGS[rs]}"
        elif funct == 0x09:
            return f"jalr {REGS[rs]}"
        elif funct == 0x21:
            return f"addu {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        elif funct == 0x23:
            return f"subu {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        elif funct == 0x2A:
            return f"slt {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
        elif funct == 0x00:
            return f"sll {REGS[rd]}, {REGS[rt]}, {shamt}"
        else:
            return f"special_{funct:02X}"
    elif opcode == 0x02:
        return f"j 0x{(addr & 0xF0000000) | (target << 2):08X}"
    elif opcode == 0x03:
        return f"jal 0x{(addr & 0xF0000000) | (target << 2):08X}"
    elif opcode == 0x04:
        return f"beq {REGS[rs]}, {REGS[rt]}, 0x{addr + 4 + (imm_signed << 2):08X}"
    elif opcode == 0x05:
        return f"bne {REGS[rs]}, {REGS[rt]}, 0x{addr + 4 + (imm_signed << 2):08X}"
    elif opcode == 0x06:
        return f"blez {REGS[rs]}, 0x{addr + 4 + (imm_signed << 2):08X}"
    elif opcode == 0x07:
        return f"bgtz {REGS[rs]}, 0x{addr + 4 + (imm_signed << 2):08X}"
    elif opcode == 0x09:
        if rs == 0:
            return f"li {REGS[rt]}, 0x{imm:04X}  ; {imm}"
        return f"addiu {REGS[rt]}, {REGS[rs]}, {imm_signed}"
    elif opcode == 0x0A:
        return f"slti {REGS[rt]}, {REGS[rs]}, {imm_signed}"
    elif opcode == 0x0C:
        return f"andi {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    elif opcode == 0x0D:
        if rs == 0:
            return f"li {REGS[rt]}, 0x{imm:04X}  ; {imm}"
        return f"ori {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    elif opcode == 0x0F:
        return f"lui {REGS[rt]}, 0x{imm:04X}"
    elif opcode == 0x20:
        return f"lb {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x21:
        return f"lh {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x23:
        return f"lw {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x24:
        return f"lbu {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x25:
        return f"lhu {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x28:
        return f"sb {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x29:
        return f"sh {REGS[rt]}, {imm_signed}({REGS[rs]})"
    elif opcode == 0x2B:
        return f"sw {REGS[rt]}, {imm_signed}({REGS[rs]})"
    else:
        return f"op_{opcode:02X} 0x{instr:08X}"

def analyze_handler(data, file_offset, ram_addr, name):
    """Analyze an AI handler function."""
    print(f"\n{'='*70}")
    print(f"{name} Handler at RAM 0x{ram_addr:08X} (file 0x{file_offset:06X})")
    print(f"{'='*70}")

    # Track spell ID references
    spell_refs = []

    for i in range(128):  # Analyze 128 instructions
        offset = file_offset + i * 4
        if offset + 4 > len(data):
            break
        instr = struct.unpack('<I', data[offset:offset+4])[0]
        addr = ram_addr + i * 4
        asm = disasm(instr, addr)

        # Check for spell ID references
        imm = instr & 0xFFFF
        highlight = ""
        if imm in SPELL_IDS:
            highlight = f" <-- SPELL: {SPELL_IDS[imm]}!"
            spell_refs.append((addr, SPELL_IDS[imm], asm))
        elif imm == 0x18:
            highlight = " <-- TYPE 0x18 (Goblin-Shaman)"

        # Check for branch/jump out of function (likely end)
        opcode = (instr >> 26) & 0x3F
        if opcode == 0x00 and (instr & 0x3F) == 0x08:  # jr
            rs = (instr >> 21) & 0x1F
            if rs == 31:  # jr ra (return)
                print(f"0x{addr:08X}: {instr:08X}  {asm:45}{highlight}")
                # Print one more instruction (delay slot)
                if offset + 8 <= len(data):
                    next_instr = struct.unpack('<I', data[offset+4:offset+8])[0]
                    next_asm = disasm(next_instr, addr + 4)
                    print(f"0x{addr+4:08X}: {next_instr:08X}  {next_asm}")
                break

        print(f"0x{addr:08X}: {instr:08X}  {asm:45}{highlight}")

    if spell_refs:
        print(f"\nSpell ID references found in this handler:")
        for addr, spell, asm in spell_refs:
            print(f"  0x{addr:08X}: {spell} - {asm}")

def main():
    with open(EXE_PATH, 'rb') as f:
        data = f.read()

    code_data = data[HEADER_SIZE:]

    # Goblin-Shaman handler from jump table
    # Type 0x18 -> 0x8001C218
    goblin_shaman_file_offset = 0x8001C218 - 0x80010000
    analyze_handler(code_data, goblin_shaman_file_offset, 0x8001C218, "Goblin-Shaman (Type 0x18)")

    # Also check neighboring handlers for comparison
    print("\n\n" + "#"*70)
    print("Comparing with nearby monster type handlers:")
    print("#"*70)

    handlers = [
        (0x8001C0C0, "Type 0x16"),
        (0x8001C1D0, "Type 0x17"),
        (0x8001C2F4, "Type 0x19 (Orc-Shaman?)"),
        (0x8001C33C, "Type 0x1A"),
    ]

    for ram_addr, name in handlers:
        file_offset = ram_addr - 0x80010000
        analyze_handler(code_data, file_offset, ram_addr, name)

if __name__ == "__main__":
    main()
