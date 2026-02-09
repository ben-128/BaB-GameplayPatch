#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Analyze the PSX bytecode interpreter in the Blaze & Blade executable.

Reads SLES_008.45 from the game BIN (RAW sector format) and disassembles
the bytecode interpreter at RAM 0x8001A03C, the opcode dispatch table at
0x8003BDE0, and the init functions that map monster types to spell indices.

Key questions:
1. How does the interpreter process the root offset table from the script area?
2. What happens when root[L] is NULL (0x00000000)?
3. How are bytecode offset values (0x1000-0x4FF0 range) resolved to addresses?
4. What is the relationship between interpreter and the 63-opcode dispatch?
"""

import struct
import sys
from pathlib import Path

# ===========================================================================
# Configuration
# ===========================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BIN_PATH = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"

# BIN format: RAW sectors
SECTOR_RAW = 2352       # bytes per raw sector
SECTOR_HDR = 24         # header before user data
SECTOR_USER = 2048      # user data per sector

# SLES_008.45 starts at LBA 295081 in the BIN
SLES_LBA = 295081

# PS1 EXE loads at RAM 0x80010000
# File has a 0x800-byte PS-X EXE header, but for the BIN copy we read
# starting from the sector that contains the file.  The first 0x800 bytes
# of the file on disc ARE the PS-X header.  Code starts at file offset 0x800.
# However, the RAM mapping is: file_offset 0x800 -> RAM 0x80010000.
# So RAM 0x8001XXXX -> file_offset = 0x800 + (0x0001XXXX - 0x00010000)
#                    = 0x800 + 0xXXXX
#
# But the user says: RAM 0x8001XXXX -> file offset 0x0000XXXX
# Let's trust the user note: "RAM 0x8001XXXX corresponds to file offset 0x0000XXXX"
# That means the PS-X header occupies file bytes 0x0000..0x07FF and code starts
# at 0x0800 which maps to RAM 0x80010800.  But many PS1 executables have load
# address = 0x80010000, meaning the header is NOT loaded, and the first code
# byte at file offset 0x800 goes to RAM 0x80010000.
#
# For the key addresses given:
#   Bytecode interpreter: RAM 0x8001A03C -> file offset 0xA03C
#   Opcode dispatch:      RAM 0x8003BDE0 -> file offset 0x2BDE0
#   Opcode 0x18 handler:  RAM 0x8001C218 -> file offset 0xC218
#   Init 0x8002B630:      file offset 0x1B630
#   Init 0x8002A788:      file offset 0x19788
#
# The mapping is: file_offset = (RAM_addr - 0x80010000) + 0x0000
# Wait, 0x8001A03C - 0x80010000 = 0xA03C.  That checks out.
# 0x8003BDE0 - 0x80010000 = 0x2BDE0.  Also checks.
# So the mapping is simply: file_offset = RAM - 0x80010000

EXE_LOAD_ADDR = 0x80010000

# MIPS register names
REGS = [
    '$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
    '$t0',   '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
    '$s0',   '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
    '$t8',   '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra',
]

# Key RAM addresses to analyze
INTERPRETER_ADDR   = 0x8001A03C
OPCODE_TABLE_ADDR  = 0x8003BDE0
OPCODE_TABLE_COUNT = 63
OPCODE_18_HANDLER  = 0x8001C218
INIT_B630          = 0x8002B630
INIT_A788          = 0x8002A788


# ===========================================================================
# BIN reading utilities
# ===========================================================================

def read_file_from_bin(bin_data, lba, file_offset, length):
    """Read `length` bytes from a file stored at `lba` in the BIN.

    The file's byte at `file_offset` is found in:
      sector = lba + (file_offset // SECTOR_USER)
      offset within sector = SECTOR_HDR + (file_offset % SECTOR_USER)
      absolute BIN offset = sector * SECTOR_RAW + offset_in_sector
    """
    result = bytearray()
    remaining = length
    cur_file_off = file_offset

    while remaining > 0:
        sector_idx = cur_file_off // SECTOR_USER
        offset_in_sector = cur_file_off % SECTOR_USER
        bytes_in_this_sector = min(remaining, SECTOR_USER - offset_in_sector)

        abs_sector = lba + sector_idx
        bin_offset = abs_sector * SECTOR_RAW + SECTOR_HDR + offset_in_sector

        if bin_offset + bytes_in_this_sector > len(bin_data):
            # Pad with zeros if we run past the end
            result.extend(bin_data[bin_offset:])
            result.extend(b'\x00' * (bytes_in_this_sector - (len(bin_data) - bin_offset)))
        else:
            result.extend(bin_data[bin_offset:bin_offset + bytes_in_this_sector])

        cur_file_off += bytes_in_this_sector
        remaining -= bytes_in_this_sector

    return bytes(result)


def ram_to_file_offset(ram_addr):
    """Convert a RAM address to a file offset within SLES_008.45."""
    return ram_addr - EXE_LOAD_ADDR


def read_exe_bytes(bin_data, ram_addr, length):
    """Read `length` bytes from the EXE at the given RAM address."""
    file_off = ram_to_file_offset(ram_addr)
    return read_file_from_bin(bin_data, SLES_LBA, file_off, length)


def read_u32(buf, offset):
    """Read a little-endian uint32."""
    if offset + 4 > len(buf):
        return 0
    return struct.unpack_from('<I', buf, offset)[0]


# ===========================================================================
# MIPS disassembler
# ===========================================================================

def disasm(word, addr):
    """Disassemble a single MIPS R3000 instruction."""
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)

    if opcode == 0:  # SPECIAL
        if funct == 0x00:
            if word == 0:
                return "nop"
            return "sll     %s,%s,%d" % (REGS[rd], REGS[rt], shamt)
        if funct == 0x02: return "srl     %s,%s,%d" % (REGS[rd], REGS[rt], shamt)
        if funct == 0x03: return "sra     %s,%s,%d" % (REGS[rd], REGS[rt], shamt)
        if funct == 0x04: return "sllv    %s,%s,%s" % (REGS[rd], REGS[rt], REGS[rs])
        if funct == 0x06: return "srlv    %s,%s,%s" % (REGS[rd], REGS[rt], REGS[rs])
        if funct == 0x08: return "jr      %s" % REGS[rs]
        if funct == 0x09:
            if rd == 31:
                return "jalr    %s" % REGS[rs]
            return "jalr    %s,%s" % (REGS[rd], REGS[rs])
        if funct == 0x0C: return "syscall"
        if funct == 0x0D: return "break"
        if funct == 0x10: return "mfhi    %s" % REGS[rd]
        if funct == 0x11: return "mthi    %s" % REGS[rs]
        if funct == 0x12: return "mflo    %s" % REGS[rd]
        if funct == 0x13: return "mtlo    %s" % REGS[rs]
        if funct == 0x18: return "mult    %s,%s" % (REGS[rs], REGS[rt])
        if funct == 0x19: return "multu   %s,%s" % (REGS[rs], REGS[rt])
        if funct == 0x1A: return "div     %s,%s" % (REGS[rs], REGS[rt])
        if funct == 0x1B: return "divu    %s,%s" % (REGS[rs], REGS[rt])
        if funct == 0x20: return "add     %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x21: return "addu    %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x22: return "sub     %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x23: return "subu    %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x24: return "and     %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x25: return "or      %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x26: return "xor     %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x27: return "nor     %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x2A: return "slt     %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        if funct == 0x2B: return "sltu    %s,%s,%s" % (REGS[rd], REGS[rs], REGS[rt])
        return "SPECIAL.%02X %s,%s,%s" % (funct, REGS[rd], REGS[rs], REGS[rt])

    elif opcode == 1:  # REGIMM
        t = addr + 4 + (simm << 2)
        if rt == 0x00: return "bltz    %s,0x%08X" % (REGS[rs], t)
        if rt == 0x01: return "bgez    %s,0x%08X" % (REGS[rs], t)
        if rt == 0x10: return "bltzal  %s,0x%08X" % (REGS[rs], t)
        if rt == 0x11: return "bgezal  %s,0x%08X" % (REGS[rs], t)
        return "REGIMM.%02X %s" % (rt, REGS[rs])

    elif opcode == 0x02: return "j       0x%08X" % target
    elif opcode == 0x03: return "jal     0x%08X" % target
    elif opcode == 0x04:
        t = addr + 4 + (simm << 2)
        return "beq     %s,%s,0x%08X" % (REGS[rs], REGS[rt], t)
    elif opcode == 0x05:
        t = addr + 4 + (simm << 2)
        return "bne     %s,%s,0x%08X" % (REGS[rs], REGS[rt], t)
    elif opcode == 0x06:
        t = addr + 4 + (simm << 2)
        return "blez    %s,0x%08X" % (REGS[rs], t)
    elif opcode == 0x07:
        t = addr + 4 + (simm << 2)
        return "bgtz    %s,0x%08X" % (REGS[rs], t)
    elif opcode == 0x08: return "addi    %s,%s,%d" % (REGS[rt], REGS[rs], simm)
    elif opcode == 0x09: return "addiu   %s,%s,%d" % (REGS[rt], REGS[rs], simm)
    elif opcode == 0x0A: return "slti    %s,%s,%d" % (REGS[rt], REGS[rs], simm)
    elif opcode == 0x0B: return "sltiu   %s,%s,%d" % (REGS[rt], REGS[rs], simm)
    elif opcode == 0x0C: return "andi    %s,%s,0x%04X" % (REGS[rt], REGS[rs], imm)
    elif opcode == 0x0D: return "ori     %s,%s,0x%04X" % (REGS[rt], REGS[rs], imm)
    elif opcode == 0x0E: return "xori    %s,%s,0x%04X" % (REGS[rt], REGS[rs], imm)
    elif opcode == 0x0F: return "lui     %s,0x%04X" % (REGS[rt], imm)
    elif opcode == 0x20: return "lb      %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x21: return "lh      %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x23: return "lw      %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x24: return "lbu     %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x25: return "lhu     %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x28: return "sb      %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x29: return "sh      %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x2B: return "sw      %s,%d(%s)" % (REGS[rt], simm, REGS[rs])
    elif opcode == 0x31: return "lwc1    $f%d,%d(%s)" % (rt, simm, REGS[rs])
    elif opcode == 0x32: return "lwc2    $%d,%d(%s)" % (rt, simm, REGS[rs])
    elif opcode == 0x39: return "swc1    $f%d,%d(%s)" % (rt, simm, REGS[rs])
    elif opcode == 0x3A: return "swc2    $%d,%d(%s)" % (rt, simm, REGS[rs])

    return "op%02X    0x%08X" % (opcode, word)


def disasm_range(bin_data, ram_start, count):
    """Disassemble `count` instructions starting at `ram_start`."""
    raw = read_exe_bytes(bin_data, ram_start, count * 4)
    lines = []
    for i in range(count):
        addr = ram_start + i * 4
        word = read_u32(raw, i * 4)
        asm = disasm(word, addr)
        lines.append((addr, word, asm))
    return lines


def find_function_start(bin_data, addr, max_search=0x2000):
    """Find function prologue (addiu $sp,$sp,-N) searching backwards."""
    for search_addr in range(addr, max(addr - max_search, EXE_LOAD_ADDR), -4):
        raw = read_exe_bytes(bin_data, search_addr, 4)
        word = read_u32(raw, 0)
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        simm = (word & 0xFFFF)
        if simm >= 0x8000:
            simm -= 0x10000
        if opcode == 0x09 and rs == 29 and rt == 29 and simm < 0:
            return search_addr
    return None


# ===========================================================================
# Analysis helpers
# ===========================================================================

def resolve_lui_pair(lines, idx):
    """Given a lui instruction at lines[idx], search forward for the matching
    addiu/ori that completes the 32-bit constant load.
    Returns (full_address, partner_idx) or (None, None)."""
    addr_i, word_i, asm_i = lines[idx]
    opcode_i = (word_i >> 26) & 0x3F
    if opcode_i != 0x0F:  # not lui
        return None, None
    rt_lui = (word_i >> 16) & 0x1F
    hi = (word_i & 0xFFFF) << 16

    for j in range(idx + 1, min(idx + 10, len(lines))):
        addr_j, word_j, asm_j = lines[j]
        opcode_j = (word_j >> 26) & 0x3F
        rs_j = (word_j >> 21) & 0x1F
        rt_j = (word_j >> 16) & 0x1F
        imm_j = word_j & 0xFFFF

        if rs_j != rt_lui:
            continue

        if opcode_j == 0x09:  # addiu (sign-extended)
            simm_j = imm_j if imm_j < 0x8000 else imm_j - 0x10000
            full = (hi + simm_j) & 0xFFFFFFFF
            return full, j
        elif opcode_j == 0x0D:  # ori (zero-extended)
            full = hi | imm_j
            return full, j

    return None, None


def annotate_line(addr, word, asm, known_addrs=None):
    """Add annotation comments to a disassembly line."""
    notes = []
    if known_addrs and addr in known_addrs:
        notes.append(known_addrs[addr])

    # Common pattern annotations
    opcode = (word >> 26) & 0x3F
    funct = word & 0x3F

    if opcode == 0 and funct == 0x09:  # jalr
        rs = (word >> 21) & 0x1F
        notes.append("INDIRECT CALL via %s" % REGS[rs])
    elif opcode == 0 and funct == 0x08:  # jr
        rs = (word >> 21) & 0x1F
        if rs == 31:
            notes.append("RETURN")
        else:
            notes.append("INDIRECT JUMP via %s" % REGS[rs])
    elif opcode == 0x03:  # jal
        target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
        notes.append("call 0x%08X" % target)
    elif opcode == 0x04 or opcode == 0x05:  # beq/bne
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        if rt == 0 and opcode == 0x04:
            notes.append("if %s == 0" % REGS[rs])
        elif rt == 0 and opcode == 0x05:
            notes.append("if %s != 0" % REGS[rs])

    if notes:
        return "  ; %s" % " | ".join(notes)
    return ""


# ===========================================================================
# Section 1: Bytecode interpreter at 0x8001A03C
# ===========================================================================

def section1_interpreter(bin_data):
    print()
    print("=" * 90)
    print("  SECTION 1: Bytecode Interpreter at 0x%08X" % INTERPRETER_ADDR)
    print("=" * 90)

    # First, find the function start
    func_start = find_function_start(bin_data, INTERPRETER_ADDR)
    if func_start:
        print("  Function prologue found at: 0x%08X" % func_start)
    else:
        func_start = INTERPRETER_ADDR - 0x100
        print("  WARNING: Could not find function prologue, using 0x%08X" % func_start)

    # Disassemble a generous range: from function start to well past the
    # interpreter core (512 instructions = 2KB should cover it)
    num_instrs = 512
    start_addr = func_start
    lines = disasm_range(bin_data, start_addr, num_instrs)

    print("  Disassembling %d instructions from 0x%08X to 0x%08X" %
          (num_instrs, start_addr, start_addr + num_instrs * 4))
    print()

    # Track register values for constant propagation
    # Look for key patterns:
    #   1. Loading the opcode dispatch table address (0x8003BDE0)
    #   2. Loading/reading from root table entries
    #   3. Null checks (beq $reg, $zero)
    #   4. sll $reg, $reg, 2 (index * 4 for table lookup)

    opcode_table_hi = (OPCODE_TABLE_ADDR >> 16) & 0xFFFF
    opcode_table_lo = OPCODE_TABLE_ADDR & 0xFFFF
    # With sign extension for addiu: if lo >= 0x8000, lui loads hi+1
    if opcode_table_lo >= 0x8000:
        lui_expected = opcode_table_hi + 1
    else:
        lui_expected = opcode_table_hi

    # Print the disassembly with annotations
    print("  --- Full disassembly ---")
    print()

    for i, (addr, word, asm) in enumerate(lines):
        # Build annotation
        notes = []

        # Check for lui that could form the opcode table address
        op = (word >> 26) & 0x3F
        if op == 0x0F:
            imm = word & 0xFFFF
            if imm == lui_expected:
                notes.append("LUI for opcode table 0x%08X" % OPCODE_TABLE_ADDR)
            # Check for other known addresses
            full, _ = resolve_lui_pair(lines, i)
            if full is not None:
                if full == OPCODE_TABLE_ADDR:
                    notes.append("-> OPCODE_TABLE 0x%08X" % full)
                elif 0x80000000 <= full < 0x80800000:
                    notes.append("-> 0x%08X" % full)

        # Check for beq/bne with $zero (null checks)
        if op in (0x04, 0x05):
            rs = (word >> 21) & 0x1F
            rt = (word >> 16) & 0x1F
            if rt == 0:
                if op == 0x04:
                    notes.append("NULL CHECK: skip if %s == 0" % REGS[rs])
                else:
                    notes.append("NOT-NULL CHECK: continue if %s != 0" % REGS[rs])
            elif rs == 0:
                if op == 0x04:
                    notes.append("NULL CHECK: skip if %s == 0" % REGS[rt])
                else:
                    notes.append("NOT-NULL CHECK: continue if %s != 0" % REGS[rt])

        # Check for sll by 2 (multiply by 4 for table indexing)
        if op == 0 and (word & 0x3F) == 0:
            shamt = (word >> 6) & 0x1F
            if shamt == 2 and word != 0:
                notes.append("INDEX * 4 (table lookup)")

        # Check for jalr (indirect call)
        if op == 0 and (word & 0x3F) == 0x09:
            rs = (word >> 21) & 0x1F
            notes.append("INDIRECT CALL via %s (opcode handler dispatch?)" % REGS[rs])

        # Check for jr (indirect jump / return)
        if op == 0 and (word & 0x3F) == 0x08:
            rs = (word >> 21) & 0x1F
            if rs == 31:
                notes.append("RETURN")
            else:
                notes.append("INDIRECT JUMP via %s" % REGS[rs])

        # Check for lw with offsets that suggest table reads
        if op == 0x23:  # lw
            simm = (word & 0xFFFF)
            if simm >= 0x8000:
                simm -= 0x10000
            rs = (word >> 21) & 0x1F
            rt = (word >> 16) & 0x1F
            if simm == 0:
                notes.append("lw %s from [%s+0] (root table read?)" % (REGS[rt], REGS[rs]))

        # Check for lbu (bytecode byte fetch)
        if op == 0x24:  # lbu
            notes.append("byte fetch (bytecode read?)")

        # Mark the specific address
        if addr == INTERPRETER_ADDR:
            notes.insert(0, "<<<< INTERPRETER ENTRY POINT >>>>")

        note_str = ""
        if notes:
            note_str = "  ; %s" % " | ".join(notes)

        print("    0x%08X: [%08X] %-44s%s" % (addr, word, asm, note_str))

        # Stop if we hit two consecutive jr $ra + nop (likely end of function)
        if (i > 10 and op == 0 and (word & 0x3F) == 0x08 and
                ((word >> 21) & 0x1F) == 31):
            # Check if next is nop
            if i + 1 < len(lines) and lines[i + 1][1] == 0:
                # Check if this is far enough from the start
                if addr > INTERPRETER_ADDR + 0x100:
                    print("    0x%08X: [%08X] %-44s" % lines[i + 1])
                    print("    ... (function end)")
                    break

    print()

    # Now do a focused analysis: scan for specific patterns
    print("  --- Pattern Analysis ---")
    print()

    # 1. Find all lui + addiu/ori pairs that form known addresses
    print("  [1] Constant loads (lui + addiu/ori pairs):")
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        if op == 0x0F:  # lui
            full, partner = resolve_lui_pair(lines, i)
            if full is not None and 0x80000000 <= full < 0x81000000:
                print("      0x%08X: lui -> 0x%08X" % (addr, full))

    # 2. Find all null/zero checks
    print()
    print("  [2] Null/zero checks (beq/bne with $zero):")
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        if op == 0x04 and (rs == 0 or rt == 0):  # beq
            checked_reg = REGS[rs] if rt == 0 else REGS[rt]
            simm = (word & 0xFFFF)
            if simm >= 0x8000:
                simm -= 0x10000
            target = addr + 4 + (simm << 2)
            print("      0x%08X: beq %s,$zero -> 0x%08X (skip if NULL)" %
                  (addr, checked_reg, target))
        elif op == 0x05 and (rs == 0 or rt == 0):  # bne
            checked_reg = REGS[rs] if rt == 0 else REGS[rt]
            simm = (word & 0xFFFF)
            if simm >= 0x8000:
                simm -= 0x10000
            target = addr + 4 + (simm << 2)
            print("      0x%08X: bne %s,$zero -> 0x%08X (continue if NOT NULL)" %
                  (addr, checked_reg, target))

    # 3. Find all sll by 2 (table index calculations)
    print()
    print("  [3] Table index calculations (sll $r, $r, 2):")
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        if op == 0 and (word & 0x3F) == 0 and word != 0:
            shamt = (word >> 6) & 0x1F
            rd = (word >> 11) & 0x1F
            rt = (word >> 16) & 0x1F
            if shamt == 2:
                print("      0x%08X: sll %s,%s,2  (index*4 for uint32 table)" %
                      (addr, REGS[rd], REGS[rt]))

    # 4. Find all jalr (indirect dispatches)
    print()
    print("  [4] Indirect calls (jalr):")
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        if op == 0 and (word & 0x3F) == 0x09:
            rs = (word >> 21) & 0x1F
            # Look back for the lw that loaded the function pointer
            for back in range(1, 8):
                if i - back < 0:
                    break
                ba, bw, basm = lines[i - back]
                bop = (bw >> 26) & 0x3F
                brt = (bw >> 16) & 0x1F
                if bop == 0x23 and brt == rs:  # lw into jalr reg
                    brs = (bw >> 21) & 0x1F
                    boff = bw & 0xFFFF
                    if boff >= 0x8000:
                        boff -= 0x10000
                    print("      0x%08X: jalr %s  <-- loaded by lw %s,%d(%s) at 0x%08X" %
                          (addr, REGS[rs], REGS[rs], boff, REGS[brs], ba))
                    break
            else:
                print("      0x%08X: jalr %s" % (addr, REGS[rs]))

    # 5. Find all jal (direct calls)
    print()
    print("  [5] Direct calls (jal):")
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        if op == 0x03:
            target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
            print("      0x%08X: jal 0x%08X" % (addr, target))


# ===========================================================================
# Section 2: Opcode dispatch table at 0x8003BDE0
# ===========================================================================

def section2_opcode_table(bin_data):
    print()
    print("=" * 90)
    print("  SECTION 2: Opcode Dispatch Table at 0x%08X (%d entries)" %
          (OPCODE_TABLE_ADDR, OPCODE_TABLE_COUNT))
    print("=" * 90)

    # Read the table: 63 uint32 function pointers
    raw = read_exe_bytes(bin_data, OPCODE_TABLE_ADDR, OPCODE_TABLE_COUNT * 4)

    handlers = []
    for i in range(OPCODE_TABLE_COUNT):
        ptr = read_u32(raw, i * 4)
        handlers.append(ptr)

    # Print the table
    print()
    print("  Opcode  | Handler Address   | File Offset  | Notes")
    print("  --------+-------------------+--------------+------")

    # Collect unique handlers for later analysis
    unique_handlers = {}

    for i, ptr in enumerate(handlers):
        file_off = ram_to_file_offset(ptr) if ptr >= EXE_LOAD_ADDR else 0
        notes = ""
        if i == 0x18:
            notes = "opcode 0x18 (add to spell list)"
        elif i == 0x19:
            notes = "opcode 0x19 (remove from list)"
        elif ptr == 0:
            notes = "NULL handler"

        if ptr not in unique_handlers:
            unique_handlers[ptr] = []
        unique_handlers[ptr].append(i)

        print("  0x%02X    | 0x%08X        | 0x%05X      | %s" %
              (i, ptr, file_off, notes))

    # Show which opcodes share handlers
    print()
    print("  --- Shared handlers ---")
    for ptr in sorted(unique_handlers.keys()):
        opcodes = unique_handlers[ptr]
        if len(opcodes) > 1:
            opc_str = ", ".join("0x%02X" % o for o in opcodes)
            print("    0x%08X: shared by opcodes [%s] (%d opcodes)" %
                  (ptr, opc_str, len(opcodes)))

    # Show stats
    print()
    print("  Total entries: %d" % OPCODE_TABLE_COUNT)
    print("  Unique handler addresses: %d" % len(unique_handlers))
    null_count = sum(1 for p in handlers if p == 0)
    print("  NULL entries: %d" % null_count)
    if handlers:
        non_null = [p for p in handlers if p != 0]
        if non_null:
            print("  Handler address range: 0x%08X - 0x%08X" %
                  (min(non_null), max(non_null)))

    return handlers


# ===========================================================================
# Section 3: Opcode 0x18 handler at 0x8001C218
# ===========================================================================

def section3_opcode18(bin_data):
    print()
    print("=" * 90)
    print("  SECTION 3: Opcode 0x18 Handler at 0x%08X" % OPCODE_18_HANDLER)
    print("=" * 90)

    func_start = find_function_start(bin_data, OPCODE_18_HANDLER)
    if func_start:
        print("  Function starts at: 0x%08X" % func_start)
        start = func_start
    else:
        start = OPCODE_18_HANDLER - 0x20
        print("  WARNING: No prologue found, starting at 0x%08X" % start)

    lines = disasm_range(bin_data, start, 80)

    print()
    for addr, word, asm in lines:
        notes = []
        if addr == OPCODE_18_HANDLER:
            notes.append("<<<< OPCODE 0x18 ENTRY >>>>")

        op = (word >> 26) & 0x3F
        # Check for jal to add-to-list subroutine (0x8001C16C)
        if op == 0x03:
            target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
            if target == 0x8001C16C:
                notes.append("call add_to_list_if_not_present")
            elif target == 0x8001C260:
                notes.append("call remove_from_list")
            else:
                notes.append("call 0x%08X" % target)

        note_str = ""
        if notes:
            note_str = "  ; %s" % " | ".join(notes)
        print("    0x%08X: [%08X] %-44s%s" % (addr, word, asm, note_str))

    # Also disassemble the add-to-list subroutine
    print()
    print("  --- Subroutine: add_to_list_if_not_present at 0x8001C16C ---")
    sub_start = find_function_start(bin_data, 0x8001C16C) or 0x8001C16C
    lines = disasm_range(bin_data, sub_start, 60)
    for addr, word, asm in lines:
        print("    0x%08X: [%08X] %s" % (addr, word, asm))
        op = (word >> 26) & 0x3F
        if op == 0 and (word & 0x3F) == 0x08 and ((word >> 21) & 0x1F) == 31:
            if addr > 0x8001C16C + 0x10:
                # Print the delay slot
                break

    # Also disassemble the remove-from-list subroutine
    print()
    print("  --- Subroutine: remove_from_list at 0x8001C260 ---")
    sub_start = find_function_start(bin_data, 0x8001C260) or 0x8001C260
    lines = disasm_range(bin_data, sub_start, 60)
    for addr, word, asm in lines:
        print("    0x%08X: [%08X] %s" % (addr, word, asm))
        op = (word >> 26) & 0x3F
        if op == 0 and (word & 0x3F) == 0x08 and ((word >> 21) & 0x1F) == 31:
            if addr > 0x8001C260 + 0x10:
                break


# ===========================================================================
# Section 4: Init functions (type -> spell index mapping)
# ===========================================================================

def section4_init_functions(bin_data):
    print()
    print("=" * 90)
    print("  SECTION 4: Init Functions (monster type -> spell index mapping)")
    print("=" * 90)

    for label, addr in [("Init at 0x8002B630", INIT_B630),
                         ("Init at 0x8002A788", INIT_A788)]:
        print()
        print("  --- %s ---" % label)

        func_start = find_function_start(bin_data, addr)
        if func_start:
            print("  Function starts at: 0x%08X" % func_start)
            start = func_start
        else:
            start = addr - 0x40
            print("  WARNING: No prologue found, starting at 0x%08X" % start)

        # Disassemble 128 instructions to cover the full init function
        lines = disasm_range(bin_data, start, 128)

        for i, (a, word, asm) in enumerate(lines):
            notes = []
            if a == addr:
                notes.append("<<<< TARGET ADDRESS >>>>")

            op = (word >> 26) & 0x3F

            # Look for lui pairs that form addresses
            if op == 0x0F:
                full, _ = resolve_lui_pair(lines, i)
                if full is not None and 0x80000000 <= full < 0x81000000:
                    notes.append("-> 0x%08X" % full)
                    # Known addresses
                    if full == 0x80054670:
                        notes.append("spell list buffer")
                    elif full == 0x8004C594:
                        notes.append("type->spell mapping buffer")

            # Check for stores (mapping writes)
            if op == 0x28:  # sb
                notes.append("store byte (mapping write?)")
            elif op == 0x29:  # sh
                notes.append("store halfword")
            elif op == 0x2B:  # sw
                notes.append("store word")

            note_str = ""
            if notes:
                note_str = "  ; %s" % " | ".join(notes)
            print("    0x%08X: [%08X] %-44s%s" % (a, word, asm, note_str))

            # Stop at function end
            if (i > 10 and op == 0 and (word & 0x3F) == 0x08 and
                    ((word >> 21) & 0x1F) == 31 and a > addr + 0x20):
                if i + 1 < len(lines):
                    print("    0x%08X: [%08X] %s" % lines[i + 1])
                print("    ... (function end)")
                break


# ===========================================================================
# Section 5: Focused analysis around interpreter entry
# ===========================================================================

def section5_interpreter_focused(bin_data):
    """Analyze just 256 bytes around 0x8001A03C with detailed annotation."""
    print()
    print("=" * 90)
    print("  SECTION 5: Focused Interpreter Analysis (0x8001A03C +/- 256 bytes)")
    print("=" * 90)

    # Read a wider region for context
    start = INTERPRETER_ADDR - 64
    lines = disasm_range(bin_data, start, 128)

    print()
    print("  Register tracking through the interpreter loop:")
    print("  (Manual trace of likely data flow)")
    print()

    # Simple register tracker
    reg_values = {}  # reg_index -> description

    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        rd = (word >> 11) & 0x1F
        funct = word & 0x3F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000

        notes = []

        # Track lui loads
        if op == 0x0F:
            reg_values[rt] = "0x%04X0000" % imm
            full, _ = resolve_lui_pair(lines, i)
            if full is not None:
                notes.append("= 0x%08X" % full)

        # Track addiu pairs
        if op == 0x09 and rs in reg_values:
            if "0000" in reg_values.get(rs, ""):
                # Completing a lui pair
                hi_str = reg_values[rs]
                try:
                    hi = int(hi_str, 16)
                    full = (hi + simm) & 0xFFFFFFFF
                    reg_values[rt] = "0x%08X" % full
                except ValueError:
                    pass

        # Track loads from memory
        if op == 0x23:  # lw
            if rs in reg_values:
                notes.append("load from [%s + %d]" % (reg_values.get(rs, REGS[rs]), simm))

        # Track sll by 2
        if op == 0 and funct == 0 and word != 0:
            shamt = (word >> 6) & 0x1F
            if shamt == 2:
                notes.append("index * 4")

        # Track addu (often base + index*4)
        if op == 0 and funct == 0x21:
            rs_desc = reg_values.get(rs, REGS[rs])
            rt_desc = reg_values.get(rt, REGS[rt])
            notes.append("%s + %s" % (rs_desc, rt_desc))

        # Null checks
        if op == 0x04:  # beq
            target = addr + 4 + (simm << 2)
            if rt == 0:
                notes.append("if %s == NULL goto 0x%08X" % (REGS[rs], target))
            elif rs == 0:
                notes.append("if %s == NULL goto 0x%08X" % (REGS[rt], target))
        if op == 0x05:  # bne
            target = addr + 4 + (simm << 2)
            if rt == 0:
                notes.append("if %s != NULL goto 0x%08X" % (REGS[rs], target))
            elif rs == 0:
                notes.append("if %s != NULL goto 0x%08X" % (REGS[rt], target))

        # Check for comparison/bounds check patterns
        if op == 0x0B:  # sltiu (compare with unsigned immediate)
            notes.append("bounds check: %s < %d (unsigned)?" % (REGS[rs], simm))
        if op == 0x0A:  # slti
            notes.append("bounds check: %s < %d (signed)?" % (REGS[rs], simm))

        if addr == INTERPRETER_ADDR:
            notes.insert(0, "===> INTERPRETER ENTRY <===")

        note_str = ""
        if notes:
            note_str = "  ; %s" % " | ".join(notes)

        print("    0x%08X: [%08X] %-44s%s" % (addr, word, asm, note_str))


# ===========================================================================
# Section 6: Search for NULL-handling patterns in the interpreter
# ===========================================================================

def section6_null_handling(bin_data):
    """Specifically search the interpreter region for patterns that handle
    NULL root table entries."""
    print()
    print("=" * 90)
    print("  SECTION 6: NULL Root Table Entry Handling")
    print("=" * 90)

    # The interpreter reads root[L] as a uint32. If it's 0 (NULL), the game
    # must either skip the entry, use a default, or crash.
    # Look for beq $reg, $zero patterns near lw instructions.

    # Scan a wide range around the interpreter
    scan_start = INTERPRETER_ADDR - 0x200
    scan_end = INTERPRETER_ADDR + 0x400
    lines = disasm_range(bin_data, scan_start, (scan_end - scan_start) // 4)

    print()
    print("  Searching 0x%08X - 0x%08X for lw + beq/bne $zero patterns..." %
          (scan_start, scan_end))
    print()

    # Find all lw instructions followed within 3 instructions by a zero check
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        if op != 0x23:  # not lw
            continue
        rt = (word >> 16) & 0x1F  # destination register
        rs = (word >> 21) & 0x1F
        simm_val = word & 0xFFFF
        if simm_val >= 0x8000:
            simm_val -= 0x10000

        # Look ahead for beq/bne with this register and $zero
        for j in range(i + 1, min(i + 5, len(lines))):
            ja, jw, jasm = lines[j]
            jop = (jw >> 26) & 0x3F
            jrs = (jw >> 21) & 0x1F
            jrt = (jw >> 16) & 0x1F

            if jop == 0x04:  # beq
                if (jrs == rt and jrt == 0) or (jrt == rt and jrs == 0):
                    jimm = jw & 0xFFFF
                    if jimm >= 0x8000:
                        jimm -= 0x10000
                    target = ja + 4 + (jimm << 2)
                    print("  FOUND: lw %s,%d(%s) at 0x%08X" %
                          (REGS[rt], simm_val, REGS[rs], addr))
                    print("         beq %s,$zero,0x%08X at 0x%08X" %
                          (REGS[rt], target, ja))
                    print("         -> If loaded value is NULL, branch to 0x%08X" % target)
                    print("         Context:")
                    ctx_start = max(0, i - 3)
                    ctx_end = min(len(lines), j + 4)
                    for k in range(ctx_start, ctx_end):
                        ka, kw, kasm = lines[k]
                        marker = ""
                        if k == i:
                            marker = "  <-- LOAD"
                        elif k == j:
                            marker = "  <-- NULL CHECK"
                        print("           0x%08X: %-44s%s" % (ka, kasm, marker))
                    print()

            elif jop == 0x05:  # bne
                if (jrs == rt and jrt == 0) or (jrt == rt and jrs == 0):
                    jimm = jw & 0xFFFF
                    if jimm >= 0x8000:
                        jimm -= 0x10000
                    target = ja + 4 + (jimm << 2)
                    print("  FOUND: lw %s,%d(%s) at 0x%08X" %
                          (REGS[rt], simm_val, REGS[rs], addr))
                    print("         bne %s,$zero,0x%08X at 0x%08X" %
                          (REGS[rt], target, ja))
                    print("         -> If loaded value is NOT NULL, branch to 0x%08X" % target)
                    print("         (Fall-through when NULL)")
                    print("         Context:")
                    ctx_start = max(0, i - 3)
                    ctx_end = min(len(lines), j + 4)
                    for k in range(ctx_start, ctx_end):
                        ka, kw, kasm = lines[k]
                        marker = ""
                        if k == i:
                            marker = "  <-- LOAD"
                        elif k == j:
                            marker = "  <-- NOT-NULL CHECK"
                        print("           0x%08X: %-44s%s" % (ka, kasm, marker))
                    print()


# ===========================================================================
# Section 7: Search for bytecode offset resolution (0x1000-0x4FF0 range)
# ===========================================================================

def section7_offset_resolution(bin_data):
    """Search for how bytecode offsets in the 0x1000-0x4FF0 range are resolved
    to actual RAM addresses. Look for add/addu with a base pointer."""
    print()
    print("=" * 90)
    print("  SECTION 7: Bytecode Offset Resolution (0x1000-0x4FF0 range)")
    print("=" * 90)

    # The root table contains offsets like 0x3C, 0x50, 0xF4 etc.
    # The offset tables within the script area contain values 0x1000-0x4FF0.
    # These must be resolved somehow - either:
    #   A) Added to a base address (script_area_start in RAM)
    #   B) Used as-is with some offset calculation
    #   C) Multiplied/shifted before use

    # Search the interpreter region for addiu/addu patterns that could be
    # base address calculations
    scan_start = INTERPRETER_ADDR - 0x100
    scan_end = INTERPRETER_ADDR + 0x600
    lines = disasm_range(bin_data, scan_start, (scan_end - scan_start) // 4)

    print()
    print("  Looking for base+offset address calculations in interpreter...")
    print()

    # Find addu instructions (reg = base + offset_from_table)
    for i, (addr, word, asm) in enumerate(lines):
        op = (word >> 26) & 0x3F
        funct = word & 0x3F

        # addu rd, rs, rt (could be base_ptr + table_offset)
        if op == 0 and funct == 0x21:
            rd = (word >> 11) & 0x1F
            rs = (word >> 21) & 0x1F
            rt = (word >> 16) & 0x1F
            # Check if this feeds into a jalr or lw shortly after
            for j in range(i + 1, min(i + 6, len(lines))):
                ja, jw, jasm = lines[j]
                jop = (jw >> 26) & 0x3F
                jfunct = jw & 0x3F
                jrs = (jw >> 21) & 0x1F

                if (jop == 0 and jfunct == 0x09 and jrs == rd):  # jalr using result
                    print("  addu %s,%s,%s at 0x%08X -> jalr %s at 0x%08X" %
                          (REGS[rd], REGS[rs], REGS[rt], addr, REGS[rd], ja))
                    # Show context
                    for k in range(max(0, i - 4), min(len(lines), j + 3)):
                        ka, kw, kasm = lines[k]
                        marker = ""
                        if k == i:
                            marker = "  <-- base+offset"
                        elif k == j:
                            marker = "  <-- call computed addr"
                        print("      0x%08X: %-44s%s" % (ka, kasm, marker))
                    print()

                if jop == 0x23 and jrs == rd:  # lw using result as base
                    print("  addu %s,%s,%s at 0x%08X -> lw from [%s] at 0x%08X" %
                          (REGS[rd], REGS[rs], REGS[rt], addr, REGS[rd], ja))
                    for k in range(max(0, i - 4), min(len(lines), j + 3)):
                        ka, kw, kasm = lines[k]
                        marker = ""
                        if k == i:
                            marker = "  <-- base+offset"
                        elif k == j:
                            marker = "  <-- read from computed addr"
                        print("      0x%08X: %-44s%s" % (ka, kasm, marker))
                    print()


# ===========================================================================
# Section 8: Disassemble specific opcode handlers
# ===========================================================================

def section8_opcode_handlers(bin_data, handlers):
    """Disassemble a few interesting opcode handlers beyond 0x18."""
    print()
    print("=" * 90)
    print("  SECTION 8: Selected Opcode Handler Disassembly")
    print("=" * 90)

    # Pick a few interesting opcodes to analyze
    interesting_opcodes = [0x00, 0x01, 0x02, 0x18, 0x19]

    for opc in interesting_opcodes:
        if opc >= len(handlers) or handlers[opc] == 0:
            print()
            print("  --- Opcode 0x%02X: NULL handler ---" % opc)
            continue

        handler_addr = handlers[opc]
        print()
        print("  --- Opcode 0x%02X: handler at 0x%08X ---" % (opc, handler_addr))

        func_start = find_function_start(bin_data, handler_addr)
        start = func_start if func_start else handler_addr
        lines = disasm_range(bin_data, start, 40)

        for addr, word, asm in lines:
            marker = ""
            if addr == handler_addr:
                marker = "  <-- entry"
            op = (word >> 26) & 0x3F
            if op == 0x03:  # jal
                target = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
                marker = "  ; call 0x%08X" % target
            elif op == 0 and (word & 0x3F) == 0x08 and ((word >> 21) & 0x1F) == 31:
                marker = "  ; RETURN"
            print("    0x%08X: [%08X] %-44s%s" % (addr, word, asm, marker))

            # Stop at return
            if (op == 0 and (word & 0x3F) == 0x08 and ((word >> 21) & 0x1F) == 31 and
                    addr > handler_addr + 8):
                break


# ===========================================================================
# Section 9: Summary and hypothesis
# ===========================================================================

def section9_summary():
    print()
    print("=" * 90)
    print("  SECTION 9: Summary and Hypothesis")
    print("=" * 90)
    print("""
  BYTECODE INTERPRETER ARCHITECTURE (expected from prior research):

  1. SCRIPT AREA per spawn group contains:
     a. Root offset table: uint32 entries indexed by L value (behavior type)
        - Entry 0..max_L: per-monster-type behavior block offsets
        - NULL (0x00000000) entries = monster shares behavior with another
     b. Per-behavior data blocks (animation, stats, spawn positions)
     c. Config/model table
     d. Bytecode offset tables (values 0x1000-0x4FF0)
     e. Command record sections (0B records)

  2. INTERPRETER reads the root table and resolves offsets:
     - root[L] gives the offset to the behavior data for monster type L
     - If root[L] == 0, the interpreter should skip or use defaults
     - Bytecode offset values are relative to some base (script area start?)

  3. OPCODE DISPATCH TABLE at 0x8003BDE0:
     - 63 function pointers for bytecode opcodes 0x00-0x3E
     - Opcode 0x18: adds a parameter byte to a list at 0x80054670
     - Opcode 0x19: removes from that list
     - The interpreter fetches bytes from the bytecode stream,
       uses the opcode byte as an index into this table,
       then calls the handler via jalr

  4. INIT FUNCTIONS map monster types to spell indices:
     - 0x8002B630: maps type_0x18 -> spell_index=6 at 0x8004C594
     - 0x8002A788: maps type_0x12 -> spell_index=4

  KEY QUESTIONS TO ANSWER FROM DISASSEMBLY:
  Q1: How does the interpreter fetch the next bytecode instruction?
      (lbu from a program counter register)
  Q2: Where is the root table pointer loaded from?
      (likely from a struct field on the monster/entity)
  Q3: What happens for NULL root entries?
      (beq $reg,$zero -> skip/default branch)
  Q4: How are offsets resolved to RAM addresses?
      (addu with script_area_base_ptr)
""")


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("=" * 90)
    print("  BLAZE & BLADE - PSX Bytecode Interpreter Analysis")
    print("=" * 90)
    print()
    print("  BIN file: %s" % BIN_PATH)
    print("  SLES LBA: %d" % SLES_LBA)
    print()

    if not BIN_PATH.exists():
        print("[ERROR] BIN file not found: %s" % BIN_PATH)
        print("  Expected at: %s" % BIN_PATH.resolve())
        return 1

    print("  Loading BIN file...")
    bin_data = BIN_PATH.read_bytes()
    print("  BIN size: %s bytes (%d sectors)" %
          (format(len(bin_data), ','), len(bin_data) // SECTOR_RAW))
    print()

    # Quick verify: read the first 16 bytes of the EXE
    # PS-X EXE header starts with "PS-X EXE" ASCII
    exe_header = read_file_from_bin(bin_data, SLES_LBA, 0, 16)
    header_str = exe_header[:8].decode('ascii', errors='replace')
    print("  EXE header magic: '%s'" % header_str)
    if header_str.startswith("PS-X EXE"):
        print("  EXE header verified OK")
    else:
        print("  WARNING: EXE header does not start with 'PS-X EXE'!")
        print("  Got bytes: %s" % ' '.join('%02X' % b for b in exe_header[:16]))

    # Read EXE metadata from header
    # Offset 0x10: initial PC
    # Offset 0x18: destination address in RAM
    # Offset 0x1C: file size
    header_full = read_file_from_bin(bin_data, SLES_LBA, 0, 0x30)
    initial_pc = read_u32(header_full, 0x10)
    dest_addr = read_u32(header_full, 0x18)
    file_size = read_u32(header_full, 0x1C)
    print("  Initial PC:       0x%08X" % initial_pc)
    print("  Dest RAM addr:    0x%08X" % dest_addr)
    print("  Code size:        %d bytes (0x%X)" % (file_size, file_size))
    print()

    # Verify the RAM mapping
    # The PS-X EXE header says dest_addr is where the code (starting at
    # file offset 0x800) gets loaded.  So file offset 0x800 -> dest_addr.
    # Our mapping: file_offset = RAM - 0x80010000
    # If dest_addr = 0x80010000, then file offset 0x800 -> 0x80010000
    # means file_offset = RAM - 0x80010000 + 0x800... wait, that contradicts.
    #
    # Actually: the PS-X EXE header is 0x800 bytes.  The code body starts
    # at file offset 0x800.  This code body is loaded at dest_addr in RAM.
    # So: RAM_addr = dest_addr + (file_offset - 0x800)
    #     file_offset = (RAM_addr - dest_addr) + 0x800
    #
    # If dest_addr = 0x80010000:
    #   RAM 0x8001A03C -> file_offset = 0x8001A03C - 0x80010000 + 0x800 = 0xA83C
    #   But the user says RAM 0x8001A03C -> file offset 0xA03C
    #
    # So the mapping RAM->file is: file_offset = RAM - dest_addr
    # This means the header bytes (0x000-0x7FF) map to RAM 0x80010000-0x800107FF
    # and code at file 0x800 maps to RAM 0x80010800.
    # OR: the dest_addr is 0x80010000 but it includes the header somehow.
    # OR: the user note is simply: subtract 0x80010000.
    #
    # Let's just verify by checking known code at 0x8001A03C:
    print("  Verifying RAM mapping...")
    test_bytes_method1 = read_file_from_bin(bin_data, SLES_LBA, 0xA03C, 4)
    test_bytes_method2 = read_file_from_bin(bin_data, SLES_LBA, 0xA83C, 4)
    w1 = read_u32(test_bytes_method1, 0)
    w2 = read_u32(test_bytes_method2, 0)

    # A valid MIPS instruction at the interpreter entry should not be all zeros
    # and should decode to something reasonable
    print("  Method 1 (file_off = RAM - 0x80010000):")
    print("    0x8001A03C -> file 0xA03C: word=0x%08X  asm=%s" % (w1, disasm(w1, 0x8001A03C)))
    print("  Method 2 (file_off = RAM - 0x80010000 + 0x800):")
    print("    0x8001A03C -> file 0xA83C: word=0x%08X  asm=%s" % (w2, disasm(w2, 0x8001A03C)))
    print()

    # Check which method gives valid MIPS code
    # A valid instruction should not be 0x00000000 at the interpreter entry
    # and should decode to a recognized instruction
    method1_valid = (w1 != 0 and not disasm(w1, 0x8001A03C).startswith("op"))
    method2_valid = (w2 != 0 and not disasm(w2, 0x8001A03C).startswith("op"))

    if method1_valid and not method2_valid:
        print("  -> Using Method 1: file_offset = RAM - 0x80010000")
    elif method2_valid and not method1_valid:
        print("  -> Using Method 2: file_offset = RAM - 0x80010000 + 0x800")
        print("  WARNING: Need to adjust EXE_LOAD_ADDR! Setting to 0x8000F800")
        # Adjust the global - this is a hack but works for this script
        global EXE_LOAD_ADDR
        EXE_LOAD_ADDR = 0x8000F800
    elif method1_valid and method2_valid:
        print("  -> Both methods give valid code. Using Method 1 (user-specified).")
    else:
        print("  WARNING: Neither method gives clearly valid code.")
        print("  Proceeding with Method 1 (user-specified).")
    print()

    # Also try to check the opcode table to validate
    print("  Validating opcode table at 0x%08X..." % OPCODE_TABLE_ADDR)
    table_sample = read_exe_bytes(bin_data, OPCODE_TABLE_ADDR, 16)
    for i in range(4):
        ptr = read_u32(table_sample, i * 4)
        print("    opcode_table[%d] = 0x%08X%s" % (
            i, ptr,
            " (valid EXE range)" if 0x80010000 <= ptr < 0x80050000 else
            " (WARNING: outside expected range)" if ptr != 0 else " (NULL)"))
    print()

    # Run all analysis sections
    section1_interpreter(bin_data)
    handlers = section2_opcode_table(bin_data)
    section3_opcode18(bin_data)
    section4_init_functions(bin_data)
    section5_interpreter_focused(bin_data)
    section6_null_handling(bin_data)
    section7_offset_resolution(bin_data)
    section8_opcode_handlers(bin_data, handlers)
    section9_summary()

    print()
    print("=" * 90)
    print("  ANALYSIS COMPLETE")
    print("=" * 90)
    return 0


if __name__ == '__main__':
    sys.exit(main())
