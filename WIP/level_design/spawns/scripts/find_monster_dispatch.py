#!/usr/bin/env python3
"""
Find the REAL monster ability dispatch mechanism.

The player spell system at 0x80024E14 uses creature_type=0 for everything.
Types 6-7 (monster abilities: Fire Breath, Paralyze Eye, etc.) have tier=[0,0,0,0,0],
meaning they are NEVER selected via the tier gate. Monster special abilities must
use a DIFFERENT dispatch mechanism.

This script searches for:
1. All callers of the 55 combat handler functions (via jalr from table 0x8003C1B0)
2. The 3 callers of the spell dispatch wrapper (0x80024414) - context analysis
3. State machine handler analysis (32 entries at 0x8003B324)
4. Overlay code searches for function pointer dispatch patterns
5. 96-byte stat field analysis (+0x2A, +0x2D offsets)
6. Entity validation cross-references (callers of 0x80026840 + jalr)
7. Battle turn management code (iteration over 0x800BB93C)
"""

import gzip
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------
# Paths
# ---------------------------------------------------------------
SAVESTATE = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\combat\SLES_008.45.000")
BLAZE_ALL = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
EXE_PATH  = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")

# ---------------------------------------------------------------
# Constants
# ---------------------------------------------------------------
RAM_BASE         = 0x80000000
RAM_SIZE         = 0x200000       # 2 MB
SAVESTATE_RAM_OFF = 0x1BA

EXE_LOAD_ADDR    = 0x80010000
EXE_HEADER_SIZE  = 0x800

# Key addresses
HANDLER_TABLE    = 0x8003C1B0     # 55-entry function pointer table
HANDLER_COUNT    = 55
HANDLER_RANGE_LO = 0x800270B8     # First handler function
HANDLER_RANGE_HI = 0x80029E80     # Last handler function end
STATE_TABLE      = 0x8003B324     # 32-entry state machine table
STATE_COUNT      = 32
SPELL_DISPATCH   = 0x80024414     # Player spell dispatch wrapper
ENTITY_VALIDATE  = 0x80026840     # Entity validation function
PLAYER_ENTITIES  = 0x80054698
MONSTER_ENTITIES = 0x800B9268
BATTLE_TABLE     = 0x800BB93C     # 12 entries, stride 0x9C

# MIPS register names
REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def ram_idx(addr):
    return addr - RAM_BASE

def exe_idx(addr):
    """Convert RAM address to EXE file offset."""
    return addr - EXE_LOAD_ADDR + EXE_HEADER_SIZE

def read_u32(buf, idx):
    if idx < 0 or idx + 4 > len(buf):
        return 0
    return struct.unpack_from('<I', buf, idx)[0]

def read_u32_ram(ram, addr):
    return read_u32(ram, ram_idx(addr))

def read_u8_ram(ram, addr):
    idx = ram_idx(addr)
    if idx < 0 or idx >= len(ram):
        return 0
    return ram[idx]


def disasm(word, addr):
    """Disassemble a single MIPS instruction."""
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
            if word == 0: return "nop"
            return f"sll     {REGS[rd]},{REGS[rt]},{shamt}"
        if funct == 0x02: return f"srl     {REGS[rd]},{REGS[rt]},{shamt}"
        if funct == 0x03: return f"sra     {REGS[rd]},{REGS[rt]},{shamt}"
        if funct == 0x04: return f"sllv    {REGS[rd]},{REGS[rt]},{REGS[rs]}"
        if funct == 0x06: return f"srlv    {REGS[rd]},{REGS[rt]},{REGS[rs]}"
        if funct == 0x08: return f"jr      {REGS[rs]}"
        if funct == 0x09: return f"jalr    {REGS[rd]},{REGS[rs]}"
        if funct == 0x0C: return f"syscall"
        if funct == 0x0D: return f"break"
        if funct == 0x10: return f"mfhi    {REGS[rd]}"
        if funct == 0x11: return f"mthi    {REGS[rs]}"
        if funct == 0x12: return f"mflo    {REGS[rd]}"
        if funct == 0x13: return f"mtlo    {REGS[rs]}"
        if funct == 0x18: return f"mult    {REGS[rs]},{REGS[rt]}"
        if funct == 0x19: return f"multu   {REGS[rs]},{REGS[rt]}"
        if funct == 0x1A: return f"div     {REGS[rs]},{REGS[rt]}"
        if funct == 0x1B: return f"divu    {REGS[rs]},{REGS[rt]}"
        if funct == 0x20: return f"add     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x21: return f"addu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x22: return f"sub     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x23: return f"subu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x24: return f"and     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x25: return f"or      {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x26: return f"xor     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x27: return f"nor     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x2A: return f"slt     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x2B: return f"sltu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        return f"SPECIAL.{funct:02X} {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 1:  # REGIMM
        if rt == 0x00:
            t = addr + 4 + (simm << 2)
            return f"bltz    {REGS[rs]},0x{t:08X}"
        if rt == 0x01:
            t = addr + 4 + (simm << 2)
            return f"bgez    {REGS[rs]},0x{t:08X}"
        if rt == 0x10:
            t = addr + 4 + (simm << 2)
            return f"bltzal  {REGS[rs]},0x{t:08X}"
        if rt == 0x11:
            t = addr + 4 + (simm << 2)
            return f"bgezal  {REGS[rs]},0x{t:08X}"
        return f"REGIMM.{rt:02X}"
    elif opcode == 0x02: return f"j       0x{target:08X}"
    elif opcode == 0x03: return f"jal     0x{target:08X}"
    elif opcode == 0x04:
        t = addr + 4 + (simm << 2)
        return f"beq     {REGS[rs]},{REGS[rt]},0x{t:08X}"
    elif opcode == 0x05:
        t = addr + 4 + (simm << 2)
        return f"bne     {REGS[rs]},{REGS[rt]},0x{t:08X}"
    elif opcode == 0x06:
        t = addr + 4 + (simm << 2)
        return f"blez    {REGS[rs]},0x{t:08X}"
    elif opcode == 0x07:
        t = addr + 4 + (simm << 2)
        return f"bgtz    {REGS[rs]},0x{t:08X}"
    elif opcode == 0x08: return f"addi    {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x09: return f"addiu   {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0A: return f"slti    {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0B: return f"sltiu   {REGS[rt]},{REGS[rs]},{simm}"
    elif opcode == 0x0C: return f"andi    {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0x0D: return f"ori     {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0x0E: return f"xori    {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0x0F: return f"lui     {REGS[rt]},0x{imm:04X}"
    elif opcode == 0x20: return f"lb      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x21: return f"lh      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x23: return f"lw      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x24: return f"lbu     {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x25: return f"lhu     {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x28: return f"sb      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x29: return f"sh      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x2B: return f"sw      {REGS[rt]},{simm}({REGS[rs]})"
    elif opcode == 0x31: return f"lwc1    $f{rt},{simm}({REGS[rs]})"
    elif opcode == 0x39: return f"swc1    $f{rt},{simm}({REGS[rs]})"
    elif opcode == 0x32: return f"lwc2    ${rt},{simm}({REGS[rs]})"
    elif opcode == 0x3A: return f"swc2    ${rt},{simm}({REGS[rs]})"
    return f"op{opcode:02X}    0x{word:08X}"


def disasm_range(data, base_addr, start_addr, count, data_offset=0):
    """Disassemble `count` instructions starting at `start_addr`.
    data: byte buffer, base_addr: RAM address of data[data_offset].
    """
    lines = []
    for i in range(count):
        addr = start_addr + i * 4
        idx = (addr - base_addr) + data_offset
        if idx < 0 or idx + 4 > len(data):
            lines.append((addr, 0, "??? (out of range)"))
            continue
        word = struct.unpack_from('<I', data, idx)[0]
        asm = disasm(word, addr)
        lines.append((addr, word, asm))
    return lines


def find_function_start(data, addr, base_addr=EXE_LOAD_ADDR, data_offset=EXE_HEADER_SIZE):
    """Find the function prologue (addiu $sp, $sp, -N) searching backwards from addr."""
    for search_addr in range(addr, max(addr - 0x2000, base_addr), -4):
        idx = (search_addr - base_addr) + data_offset
        if idx < 0 or idx + 4 > len(data):
            continue
        word = struct.unpack_from('<I', data, idx)[0]
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000
        if opcode == 0x09 and rs == 29 and rt == 29 and simm < 0:
            return search_addr
    return None


def find_jal_callers(data, target_addr, search_start, search_end, base_addr=EXE_LOAD_ADDR, data_offset=EXE_HEADER_SIZE):
    """Find all JAL instructions that call target_addr."""
    callers = []
    jal_opcode = 0x03
    target_field = (target_addr & 0x0FFFFFFF) >> 2
    expected_word = (jal_opcode << 26) | target_field

    for addr in range(search_start, search_end, 4):
        idx = (addr - base_addr) + data_offset
        if idx < 0 or idx + 4 > len(data):
            continue
        word = struct.unpack_from('<I', data, idx)[0]
        if word == expected_word:
            callers.append(addr)
    return callers


def find_jalr_sites(data, search_start, search_end, base_addr=EXE_LOAD_ADDR, data_offset=EXE_HEADER_SIZE):
    """Find all jalr instructions in the given range."""
    sites = []
    for addr in range(search_start, search_end, 4):
        idx = (addr - base_addr) + data_offset
        if idx < 0 or idx + 4 > len(data):
            continue
        word = struct.unpack_from('<I', data, idx)[0]
        opcode = (word >> 26) & 0x3F
        funct = word & 0x3F
        if opcode == 0 and funct == 0x09:
            rs = (word >> 21) & 0x1F
            rd = (word >> 11) & 0x1F
            sites.append((addr, rs, rd))
    return sites


# ===================================================================
# SECTION 1: Find ALL callers of the 55 combat handlers
# ===================================================================
def section1_find_handler_callers(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 1: Find ALL callers of the 55 combat handler functions")
    print("=" * 100)
    print(f"  Handler table: 0x{HANDLER_TABLE:08X} ({HANDLER_COUNT} entries)")
    print(f"  Handler code range: 0x{HANDLER_RANGE_LO:08X} - 0x{HANDLER_RANGE_HI:08X}")

    # Read handler addresses from RAM
    handlers = {}
    for i in range(HANDLER_COUNT):
        addr = HANDLER_TABLE + i * 4
        h = read_u32_ram(ram, addr)
        handlers[i] = h

    unique_handlers = sorted(set(handlers.values()))
    print(f"  Unique handler addresses: {len(unique_handlers)}")

    # Strategy 1: Search for lui/addiu/ori that form 0x8003C1B0 or nearby
    print(f"\n  --- Strategy 1: Search for code that loads table base 0x{HANDLER_TABLE:08X} ---")
    table_hi = (HANDLER_TABLE >> 16) & 0xFFFF
    table_lo = HANDLER_TABLE & 0xFFFF
    # Account for sign extension: if lo >= 0x8000, hi gets +1
    if table_lo >= 0x8000:
        lui_val = table_hi + 1
        addiu_val = table_lo - 0x10000  # negative
    else:
        lui_val = table_hi
        addiu_val = table_lo

    print(f"  Looking for lui $r,0x{lui_val:04X} + addiu/ori $r,$r,0x{table_lo:04X}")

    # Search EXE for lui with the hi value
    exe_start = EXE_LOAD_ADDR
    exe_end = EXE_LOAD_ADDR + len(exe) - EXE_HEADER_SIZE
    table_ref_sites = []

    for addr in range(exe_start, exe_end, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF

        if opcode == 0x0F and imm == lui_val:  # lui
            # Look forward for addiu/ori with table_lo
            for fwd in range(1, 8):
                fwd_addr = addr + fwd * 4
                fwd_idx = exe_idx(fwd_addr)
                if fwd_idx < 0 or fwd_idx + 4 > len(exe):
                    break
                fwd_word = struct.unpack_from('<I', exe, fwd_idx)[0]
                fwd_opcode = (fwd_word >> 26) & 0x3F
                fwd_imm = fwd_word & 0xFFFF
                fwd_rs = (fwd_word >> 21) & 0x1F
                fwd_rt = (fwd_word >> 16) & 0x1F

                if fwd_opcode in (0x09, 0x0D) and fwd_imm == table_lo and fwd_rs == rt:
                    table_ref_sites.append((addr, fwd_addr, rt, fwd_rt))

    if table_ref_sites:
        print(f"\n  Found {len(table_ref_sites)} direct table references:")
        for lui_addr, lo_addr, lui_reg, lo_reg in table_ref_sites:
            func = find_function_start(exe, lui_addr)
            func_str = f"in func 0x{func:08X}" if func else "func unknown"
            print(f"    lui at 0x{lui_addr:08X}, lo at 0x{lo_addr:08X} ({func_str})")
            # Disassemble context
            ctx_start = lui_addr - 4 * 4
            lines = disasm_range(exe, EXE_LOAD_ADDR, ctx_start, 20, EXE_HEADER_SIZE)
            for a, w, asm in lines:
                marker = ""
                if a == lui_addr: marker = "  <-- lui table_hi"
                elif a == lo_addr: marker = "  <-- lo table_lo"
                elif 'jalr' in asm: marker = "  <-- JALR!"
                print(f"      0x{a:08X}: {asm:48s}{marker}")
    else:
        print("  No direct table references found via lui/addiu pattern.")

    # Strategy 2: Search for the classic function pointer dispatch pattern:
    #   sll $r, $r, 2       (multiply index by 4)
    #   addu $r, $r, $base  (add to table base)
    #   lw $r, offset($r)   (load function pointer)
    #   jalr $r              (call it)
    print(f"\n  --- Strategy 2: Search for sll+addu+lw+jalr dispatch patterns ---")

    dispatch_sites = []
    for addr in range(exe_start, exe_end - 16, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 16 > len(exe):
            continue
        w0 = struct.unpack_from('<I', exe, idx)[0]

        # Check for sll $rd, $rt, 2 (opcode=0, funct=0, shamt=2)
        if (w0 >> 26) != 0 or (w0 & 0x3F) != 0:
            continue
        shamt = (w0 >> 6) & 0x1F
        if shamt != 2:
            continue

        sll_rd = (w0 >> 11) & 0x1F
        sll_rt = (w0 >> 16) & 0x1F

        # Look forward for addu using sll_rd, then lw, then jalr
        found_addu = False
        found_lw = False
        found_jalr = False
        addu_addr = lw_addr = jalr_addr = 0
        addu_rd = lw_rt = lw_base = lw_off = 0

        for fwd in range(1, 12):
            fwd_addr = addr + fwd * 4
            fwd_idx = exe_idx(fwd_addr)
            if fwd_idx < 0 or fwd_idx + 4 > len(exe):
                break
            fw = struct.unpack_from('<I', exe, fwd_idx)[0]
            fo = (fw >> 26) & 0x3F
            frs = (fw >> 21) & 0x1F
            frt = (fw >> 16) & 0x1F
            frd = (fw >> 11) & 0x1F
            ff = fw & 0x3F

            if not found_addu and fo == 0 and ff == 0x21:
                # addu - check if one of rs/rt is sll_rd
                if frs == sll_rd or frt == sll_rd:
                    found_addu = True
                    addu_addr = fwd_addr
                    addu_rd = frd

            if found_addu and not found_lw and fo == 0x23:
                # lw - check if base reg relates to addu result
                if frs == addu_rd or frs == sll_rd:
                    found_lw = True
                    lw_addr = fwd_addr
                    lw_rt = frt
                    lw_base = frs
                    lw_off = fw & 0xFFFF
                    if lw_off >= 0x8000:
                        lw_off -= 0x10000

            if found_lw and not found_jalr and fo == 0 and ff == 0x09:
                # jalr - check if rs is the loaded value
                if frs == lw_rt:
                    found_jalr = True
                    jalr_addr = fwd_addr

        if found_jalr:
            dispatch_sites.append({
                'sll_addr': addr,
                'addu_addr': addu_addr,
                'lw_addr': lw_addr,
                'jalr_addr': jalr_addr,
                'sll_rd': sll_rd,
                'addu_rd': addu_rd,
                'lw_rt': lw_rt,
                'lw_base': lw_base,
                'lw_off': lw_off,
            })

    print(f"  Found {len(dispatch_sites)} sll*4+addu+lw+jalr dispatch sites")

    # Filter: which ones could reference the handler table?
    # The table is at 0x8003C1B0. Look for dispatches where the base register
    # could plausibly hold this address.
    interesting = []
    for site in dispatch_sites:
        func = find_function_start(exe, site['sll_addr'])
        # Check if function also references 0x8003C1B0 nearby
        site['func_start'] = func

        # Check 40 instructions before sll for lui 0x8004/0x8003
        has_table_ref = False
        check_start = site['sll_addr'] - 40 * 4
        for ca in range(max(check_start, exe_start), site['sll_addr'], 4):
            ci = exe_idx(ca)
            if ci < 0 or ci + 4 > len(exe):
                continue
            cw = struct.unpack_from('<I', exe, ci)[0]
            co = (cw >> 26) & 0x3F
            cimm = cw & 0xFFFF
            if co == 0x0F and cimm in (lui_val, 0x8004, 0x8003):
                has_table_ref = True
                break

        site['has_table_ref'] = has_table_ref
        interesting.append(site)

    # Show ALL dispatch sites but highlight ones near the handler table
    for i, site in enumerate(interesting):
        is_table = site['has_table_ref']
        tag = "*** HANDLER TABLE CANDIDATE ***" if is_table else ""
        func_str = f"func 0x{site['func_start']:08X}" if site['func_start'] else "func ???"
        print(f"\n  Dispatch #{i}: sll@0x{site['sll_addr']:08X} jalr@0x{site['jalr_addr']:08X} "
              f"({func_str}) lw_off={site['lw_off']} {tag}")

        # Disassemble context around sll
        ctx_start = site['sll_addr'] - 8 * 4
        ctx_end_count = 20 + 8
        lines = disasm_range(exe, EXE_LOAD_ADDR, ctx_start, ctx_end_count, EXE_HEADER_SIZE)
        for a, w, asm in lines:
            marker = ""
            if a == site['sll_addr']: marker = "  <-- sll *4"
            elif a == site['addu_addr']: marker = "  <-- addu"
            elif a == site['lw_addr']: marker = "  <-- lw (load handler ptr)"
            elif a == site['jalr_addr']: marker = "  <-- JALR (dispatch!)"
            elif 'lui' in asm and ('0x8004' in asm or '0x8003' in asm):
                marker = "  <-- possible table base"
            print(f"      0x{a:08X}: {asm:48s}{marker}")

    # Strategy 3: Search for references to any address in the table RANGE
    # 0x8003C1B0 to 0x8003C288 (0x8003C1B0 + 55*4 = 0x8003C28C)
    print(f"\n  --- Strategy 3: Search for ANY reference to table range 0x8003C1B0-0x8003C28C ---")
    table_end = HANDLER_TABLE + HANDLER_COUNT * 4

    # Search for lw instructions with offsets that would hit the table
    # Pattern: lui $r, 0x8004 (because 0x8003C1B0 with sign-ext: 0x8004 + (-0x3E50))
    # 0x8003C1B0 = 0x80040000 + (-0x3E50) => lui 0x8004, addiu -0x3E50 (= 0xC1B0)
    # Actually: 0xC1B0 >= 0x8000, so: lui 0x8004, addiu 0xC1B0-0x10000 = -0x3E50
    # Or: lui 0x8003, ori 0xC1B0 (no sign extension for ori)

    refs_found = []
    for addr in range(exe_start, exe_end, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F

        # Check for load/store with offset in the C1B0-C28C range
        # using base register that might hold 0x80030000 or 0x80040000
        if opcode in (0x20, 0x21, 0x23, 0x24, 0x25):  # lb, lh, lw, lbu, lhu
            simm = imm if imm < 0x8000 else imm - 0x10000
            # If base holds 0x80040000 (from lui 0x8004):
            # effective = 0x80040000 + simm => for table range, simm in [-0x3E50, -0x3D74]
            if -0x3E50 <= simm <= -0x3D74:
                # Check if there's a lui 0x8004 nearby
                for back in range(1, 20):
                    ba = addr - back * 4
                    bi = exe_idx(ba)
                    if bi < 0 or bi + 4 > len(exe):
                        continue
                    bw = struct.unpack_from('<I', exe, bi)[0]
                    bo = (bw >> 26) & 0x3F
                    brt = (bw >> 16) & 0x1F
                    bimm = bw & 0xFFFF
                    if bo == 0x0F and bimm == 0x8004 and brt == rs:
                        eff = 0x80040000 + simm
                        refs_found.append((addr, eff, rs, f"lui 0x8004 at 0x{ba:08X}"))
                        break

    if refs_found:
        print(f"  Found {len(refs_found)} references to table range:")
        for raddr, eff, reg, note in refs_found:
            idx = exe_idx(raddr)
            word = struct.unpack_from('<I', exe, idx)[0]
            asm = disasm(word, raddr)
            table_idx = (eff - HANDLER_TABLE) // 4
            print(f"    0x{raddr:08X}: {asm:48s} effective=0x{eff:08X} (table[{table_idx}]) {note}")

            # Show context
            ctx_start = raddr - 6 * 4
            lines = disasm_range(exe, EXE_LOAD_ADDR, ctx_start, 16, EXE_HEADER_SIZE)
            for a, w, asm2 in lines:
                marker = ""
                if a == raddr: marker = "  <-- TABLE ACCESS"
                elif 'jalr' in asm2: marker = "  <-- JALR"
                print(f"        0x{a:08X}: {asm2:48s}{marker}")
    else:
        print("  No direct lw references to table range found.")

    # Strategy 4: Search for ANY lw followed by jalr within 4 instructions,
    # specifically in the vicinity of the handler range functions
    print(f"\n  --- Strategy 4: lw+jalr near handler range code 0x80024000-0x8002B000 ---")
    for addr in range(0x80024000, 0x8002B000, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        funct = word & 0x3F

        if opcode == 0 and funct == 0x09:  # jalr
            rs = (word >> 21) & 0x1F
            # Look back for lw into rs
            for back in range(1, 6):
                ba = addr - back * 4
                bi = exe_idx(ba)
                if bi < 0 or bi + 4 > len(exe):
                    continue
                bw = struct.unpack_from('<I', exe, bi)[0]
                bo = (bw >> 26) & 0x3F
                brt = (bw >> 16) & 0x1F
                if bo == 0x23 and brt == rs:  # lw into jalr's rs
                    # This is a function pointer call. Check context.
                    func = find_function_start(exe, addr)
                    # Skip if this is inside one of the 55 handlers themselves
                    if HANDLER_RANGE_LO <= addr <= HANDLER_RANGE_HI:
                        continue
                    # Skip the known spell dispatch
                    if func and func == SPELL_DISPATCH:
                        continue
                    # Show it
                    lw_rs = (bw >> 21) & 0x1F
                    lw_off = bw & 0xFFFF
                    if lw_off >= 0x8000:
                        lw_off -= 0x10000
                    func_str = f"func 0x{func:08X}" if func else "???"
                    print(f"    jalr@0x{addr:08X} lw@0x{ba:08X} "
                          f"lw {REGS[rs]},{lw_off}({REGS[lw_rs]}) ({func_str})")


# ===================================================================
# SECTION 2: Analyze callers of spell dispatch 0x80024414
# ===================================================================
def section2_spell_dispatch_callers(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 2: Analyze the callers of spell dispatch wrapper 0x80024414")
    print("=" * 100)

    # Find all JAL 0x80024414
    callers = find_jal_callers(exe, SPELL_DISPATCH, EXE_LOAD_ADDR,
                                EXE_LOAD_ADDR + len(exe) - EXE_HEADER_SIZE)
    print(f"  Found {len(callers)} JAL 0x{SPELL_DISPATCH:08X} sites")

    for ci, caller_addr in enumerate(callers):
        func = find_function_start(exe, caller_addr)
        func_str = f"0x{func:08X}" if func else "???"
        print(f"\n  === Caller #{ci}: JAL at 0x{caller_addr:08X} (in function {func_str}) ===")

        # Disassemble 30 instructions BEFORE the JAL
        start = caller_addr - 30 * 4
        lines = disasm_range(exe, EXE_LOAD_ADDR, start, 35, EXE_HEADER_SIZE)
        for a, w, asm in lines:
            marker = ""
            if a == caller_addr: marker = "  <-- JAL 0x80024414"
            elif 'jal' in asm.lower() and '80024414' not in asm:
                # Extract target
                marker = "  <-- sibling call"
            elif '0x80026840' in asm:
                marker = "  <-- entity validation!"
            elif '$s3' in asm:
                marker = "  <-- entity reg"
            elif '0x2B5' in asm or '693' in asm:
                marker = "  <-- creature_type offset!"
            print(f"      0x{a:08X}: {asm:48s}{marker}")

        # Also find ALL sibling JAL calls in the same function
        if func:
            print(f"\n    Sibling function calls in 0x{func:08X}:")
            sibling_targets = set()
            for scan_addr in range(func, func + 0x2000, 4):
                si = exe_idx(scan_addr)
                if si < 0 or si + 4 > len(exe):
                    break
                sw = struct.unpack_from('<I', exe, si)[0]
                so = (sw >> 26) & 0x3F
                if so == 0x03:  # jal
                    target = (sw & 0x03FFFFFF) << 2 | (scan_addr & 0xF0000000)
                    sibling_targets.add(target)
                # Stop at jr $ra (end of function)
                if so == 0 and (sw & 0x3F) == 0x08 and ((sw >> 21) & 0x1F) == 31:
                    break

            for t in sorted(sibling_targets):
                tag = ""
                if t == SPELL_DISPATCH: tag = " (SPELL DISPATCH)"
                elif t == ENTITY_VALIDATE: tag = " (ENTITY VALIDATE)"
                elif HANDLER_RANGE_LO <= t <= HANDLER_RANGE_HI: tag = " (COMBAT HANDLER!)"
                print(f"      jal 0x{t:08X}{tag}")


# ===================================================================
# SECTION 3: Analyze state machine handlers
# ===================================================================
def section3_state_machine(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 3: Analyze 32-entry state machine at 0x{:08X}".format(STATE_TABLE))
    print("=" * 100)

    # Read state handler addresses from RAM
    state_handlers = []
    for i in range(STATE_COUNT):
        addr = STATE_TABLE + i * 4
        h = read_u32_ram(ram, addr)
        state_handlers.append(h)

    print(f"  State handler addresses:")
    for i, h in enumerate(state_handlers):
        # Check if it's in the EXE range
        in_exe = EXE_LOAD_ADDR <= h < EXE_LOAD_ADDR + len(exe) - EXE_HEADER_SIZE + 0x30000
        print(f"    state[{i:2d}] = 0x{h:08X}  {'(EXE)' if in_exe else '(overlay?)'}")

    # For each handler, disassemble first 20 instructions and check for:
    # - Calls to entity validation (0x80026840)
    # - jalr (indirect calls = dispatches)
    # - References to combat handler table
    # - Branches checking player vs monster
    print(f"\n  --- Detailed analysis of each state handler ---")

    for i, h in enumerate(state_handlers):
        if h == 0:
            continue

        # Try to read from EXE first, then RAM
        lines = disasm_range(exe, EXE_LOAD_ADDR, h, 20, EXE_HEADER_SIZE)

        # Check if we got valid data
        has_valid = any(w != 0 for _, w, _ in lines)
        if not has_valid:
            # Try from RAM
            lines = disasm_range(ram, RAM_BASE, h, 20, 0)
            has_valid = any(w != 0 for _, w, _ in lines)

        if not has_valid:
            print(f"\n  state[{i:2d}] = 0x{h:08X}: NO VALID CODE")
            continue

        # Scan for interesting patterns
        has_entity_validate = False
        has_jalr = False
        has_handler_ref = False
        jal_targets = []

        for a, w, asm in lines:
            if '0x80026840' in asm: has_entity_validate = True
            if 'jalr' in asm: has_jalr = True
            if 'jal' in asm and 'jalr' not in asm:
                # Extract target
                target = (w & 0x03FFFFFF) << 2 | (a & 0xF0000000)
                jal_targets.append(target)
                if HANDLER_RANGE_LO <= target <= HANDLER_RANGE_HI:
                    has_handler_ref = True

        # Only show detail for interesting handlers
        interesting = has_entity_validate or has_jalr or has_handler_ref
        tag = ""
        if has_entity_validate: tag += " [ENTITY_VALIDATE]"
        if has_jalr: tag += " [JALR]"
        if has_handler_ref: tag += " [HANDLER_REF]"

        print(f"\n  state[{i:2d}] = 0x{h:08X}{tag}")

        if interesting or True:  # Show all for thoroughness
            for a, w, asm in lines:
                marker = ""
                if '0x80026840' in asm: marker = "  <-- entity validate"
                elif 'jalr' in asm: marker = "  <-- INDIRECT CALL"
                elif 'jal' in asm and 'jalr' not in asm:
                    target = (w & 0x03FFFFFF) << 2 | (a & 0xF0000000)
                    if HANDLER_RANGE_LO <= target <= HANDLER_RANGE_HI:
                        marker = "  <-- COMBAT HANDLER!"
                print(f"      0x{a:08X}: {asm:48s}{marker}")

            if jal_targets:
                print(f"    Function calls: {', '.join(f'0x{t:08X}' for t in jal_targets)}")


# ===================================================================
# SECTION 4: Search overlay code for monster ability dispatch
# ===================================================================
def section4_overlay_search(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 4: Search overlay code (RAM 0x800A0000-0x800D0000) for monster dispatch")
    print("=" * 100)

    # Search for jalr preceded by lw with stride-4 pattern (function pointer table dispatch)
    overlay_start = 0x800A0000
    overlay_end = 0x800D0000

    print(f"\n  --- 4a: jalr sites in overlay ---")
    jalr_sites = find_jalr_sites(ram, overlay_start, overlay_end, RAM_BASE, 0)
    print(f"  Found {len(jalr_sites)} jalr instructions in overlay")

    # For each jalr, check if preceded by lw from a computed table address
    dispatch_candidates = []
    for jalr_addr, jalr_rs, jalr_rd in jalr_sites:
        # Look back for lw that loads into jalr_rs
        for back in range(1, 6):
            ba = jalr_addr - back * 4
            bi = ram_idx(ba)
            if bi < 0 or bi + 4 > len(ram):
                continue
            bw = struct.unpack_from('<I', ram, bi)[0]
            bo = (bw >> 26) & 0x3F
            brt = (bw >> 16) & 0x1F
            brs = (bw >> 21) & 0x1F
            if bo == 0x23 and brt == jalr_rs:  # lw into jalr's source
                # Check if there's a sll *4 before the lw
                for back2 in range(1, 10):
                    ba2 = ba - back2 * 4
                    bi2 = ram_idx(ba2)
                    if bi2 < 0 or bi2 + 4 > len(ram):
                        continue
                    bw2 = struct.unpack_from('<I', ram, bi2)[0]
                    if (bw2 >> 26) == 0 and (bw2 & 0x3F) == 0:  # sll
                        shamt = (bw2 >> 6) & 0x1F
                        if shamt == 2:
                            lw_off = bw & 0xFFFF
                            if lw_off >= 0x8000: lw_off -= 0x10000
                            dispatch_candidates.append({
                                'sll_addr': ba2,
                                'lw_addr': ba,
                                'jalr_addr': jalr_addr,
                                'lw_off': lw_off,
                                'lw_base': brs,
                            })
                            break
                break

    print(f"  Found {len(dispatch_candidates)} sll*4+lw+jalr dispatch patterns in overlay")
    for dc in dispatch_candidates:
        print(f"\n    Dispatch: sll@0x{dc['sll_addr']:08X} lw@0x{dc['lw_addr']:08X} jalr@0x{dc['jalr_addr']:08X}")
        ctx_start = dc['sll_addr'] - 4 * 4
        lines = disasm_range(ram, RAM_BASE, ctx_start, 20, 0)
        for a, w, asm in lines:
            marker = ""
            if a == dc['sll_addr']: marker = "  <-- sll *4"
            elif a == dc['lw_addr']: marker = "  <-- lw (load ptr)"
            elif a == dc['jalr_addr']: marker = "  <-- JALR"
            print(f"        0x{a:08X}: {asm:48s}{marker}")

    # 4b: Search for code that reads the 96-byte stat field +0x2A offset
    print(f"\n  --- 4b: Code reading stat fields +0x2A (42) and +0x2D (45) ---")
    # Search overlay AND exe for lbu/lhu with immediate 0x2A or 0x2D
    for search_name, s_start, s_end, buf, base, data_off in [
        ("EXE", EXE_LOAD_ADDR, EXE_LOAD_ADDR + 0x30000, exe, EXE_LOAD_ADDR, EXE_HEADER_SIZE),
        ("Overlay", overlay_start, overlay_end, ram, RAM_BASE, 0),
    ]:
        print(f"\n    Searching {search_name} for lbu/lhu with offset 0x2A or 0x2D:")
        for addr in range(s_start, s_end, 4):
            idx = (addr - base) + data_off
            if idx < 0 or idx + 4 > len(buf):
                continue
            word = struct.unpack_from('<I', buf, idx)[0]
            opcode = (word >> 26) & 0x3F
            imm = word & 0xFFFF
            simm = imm if imm < 0x8000 else imm - 0x10000

            if opcode in (0x24, 0x25, 0x20, 0x21) and simm in (0x2A, 0x2D):
                rs = (word >> 21) & 0x1F
                rt = (word >> 16) & 0x1F
                asm = disasm(word, addr)
                print(f"      0x{addr:08X}: {asm}")

    # 4c: Search for references to monster type 6-7 pointer addresses
    print(f"\n  --- 4c: References to type 6-7 data pointers ---")
    # Read type 6 and 7 pointers from the pointer array
    game_state_ptr = read_u32_ram(ram, 0x8005490C)
    ptr_array_addr = read_u32_ram(ram, game_state_ptr + 0x9C)

    type_ptrs = {}
    for t in range(8):
        type_ptrs[t] = read_u32_ram(ram, ptr_array_addr + t * 4)

    print(f"  Type pointers: {', '.join(f'type{t}=0x{type_ptrs[t]:08X}' for t in range(8))}")

    # Search for these pointer values in code
    for t in [6, 7]:
        ptr = type_ptrs[t]
        if ptr == 0:
            continue
        ptr_bytes = struct.pack('<I', ptr)
        # Search in RAM
        pos = 0
        while True:
            idx = ram.find(ptr_bytes, pos)
            if idx == -1 or idx >= len(ram):
                break
            ram_addr = idx + RAM_BASE
            # Skip if it's in the pointer array itself
            if abs(ram_addr - ptr_array_addr) < 0x200:
                pos = idx + 4
                continue
            print(f"    Type {t} ptr 0x{ptr:08X} found at RAM 0x{ram_addr:08X}")
            pos = idx + 4


# ===================================================================
# SECTION 5: Examine 96-byte stat fields +0x2A and +0x2D
# ===================================================================
def section5_stat_fields(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 5: Examine 96-byte stat fields +0x2A and +0x2D")
    print("=" * 100)

    # Read the 96-byte entries from BLAZE.ALL for Cavern F1 Area1
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())
    group_offset = 0xF7A97C
    monsters = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]

    print(f"\n  96-byte stat entries from Cavern F1 Area1 (0x{group_offset:08X}):")
    for i, name in enumerate(monsters):
        entry_off = group_offset + i * 96
        entry = blaze[entry_off:entry_off+96]

        # Stat area starts at byte 16 (after 16-byte name)
        stats_raw = entry[16:]
        # +0x2A from stat start = byte 42 of stat area = byte 58 of entry
        # Actually +0x2A from the entry start is byte 42 = stat area offset 26
        # But user says +0x2A from 96-byte entry = byte 42

        val_2A = entry[0x2A]
        val_2B = entry[0x2B]
        val_2C = entry[0x2C]
        val_2D = entry[0x2D]
        val_2E = entry[0x2E]
        val_2F = entry[0x2F]

        # Show as uint16
        hw_2A = struct.unpack_from('<H', entry, 0x2A)[0]
        hw_2C = struct.unpack_from('<H', entry, 0x2C)[0]
        hw_2E = struct.unpack_from('<H', entry, 0x2E)[0]

        # Stat index: 0x2A = byte 42 of entry, byte 26 of stat area
        # Each stat is uint16, so stat index = (42-16)/2 = 13
        stat_idx = (0x2A - 16) // 2

        name_str = entry[:16].split(b'\x00')[0].decode('ascii', errors='replace')
        print(f"\n    {name} ({name_str}):")
        print(f"      entry[0x2A]=0x{val_2A:02X} ({val_2A})  entry[0x2B]=0x{val_2B:02X} ({val_2B})")
        print(f"      entry[0x2C]=0x{val_2C:02X} ({val_2C})  entry[0x2D]=0x{val_2D:02X} ({val_2D})")
        print(f"      entry[0x2E]=0x{val_2E:02X} ({val_2E})  entry[0x2F]=0x{val_2F:02X} ({val_2F})")
        print(f"      uint16 at 0x2A={hw_2A}  0x2C={hw_2C}  0x2E={hw_2E}")
        print(f"      (stat index {stat_idx} = stats[{stat_idx}]={hw_2A})")

        # Full hex dump of bytes 0x28-0x3F
        print(f"      bytes 0x28-0x3F: [{entry[0x28:0x40].hex()}]")
        # Full hex dump of bytes 0x10-0x5F (all stats)
        print(f"      Full stats hex:  [{entry[0x10:0x60].hex()}]")

    # Search EXE for code that reads entity stat offset 0x2A or struct offset 0x2A
    print(f"\n  --- Search EXE for lbu/lhu with offset 0x2A (decimal 42) ---")
    # This catches: lbu $rt, 0x2A($rs) and lhu $rt, 0x2A($rs)
    found_2a = []
    found_2d = []
    for addr in range(EXE_LOAD_ADDR, EXE_LOAD_ADDR + 0x35000, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000

        if opcode in (0x20, 0x21, 0x23, 0x24, 0x25):  # lb, lh, lw, lbu, lhu
            if simm == 0x2A:
                found_2a.append(addr)
            elif simm == 0x2D:
                found_2d.append(addr)

    print(f"  Found {len(found_2a)} instructions with offset 0x2A:")
    for addr in found_2a:
        idx = exe_idx(addr)
        word = struct.unpack_from('<I', exe, idx)[0]
        asm = disasm(word, addr)
        func = find_function_start(exe, addr)
        func_str = f"func 0x{func:08X}" if func else "???"
        print(f"    0x{addr:08X}: {asm:48s} ({func_str})")

    print(f"\n  Found {len(found_2d)} instructions with offset 0x2D:")
    for addr in found_2d:
        idx = exe_idx(addr)
        word = struct.unpack_from('<I', exe, idx)[0]
        asm = disasm(word, addr)
        func = find_function_start(exe, addr)
        func_str = f"func 0x{func:08X}" if func else "???"
        print(f"    0x{addr:08X}: {asm:48s} ({func_str})")

    # Check: if +0x2A = 6 for Goblin, what is entry 6 in the type-6 monster catalog?
    print(f"\n  --- Cross-reference: Goblin's +0x2A=6 vs Type 6 monster catalog ---")
    game_state_ptr = read_u32_ram(ram, 0x8005490C)
    ptr_array_addr = read_u32_ram(ram, game_state_ptr + 0x9C)
    ptr6 = read_u32_ram(ram, ptr_array_addr + 6 * 4)

    if ptr6 != 0:
        # Entry 6 in type-6 catalog
        entry_addr = ptr6 + 6 * 48
        entry = bytes(ram[ram_idx(entry_addr):ram_idx(entry_addr) + 48])
        name_data = entry[:16]
        parts = []
        current = []
        for b in name_data:
            if b == 0:
                if current: parts.append(''.join(current)); current = []
            elif 32 <= b < 127: current.append(chr(b))
            else: current.append('.')
        if current: parts.append(''.join(current))
        name = parts[0] if parts else ""
        typename = parts[1] if len(parts) > 1 else ""

        handler_ref = entry[0x18]
        prob = entry[0x1D]

        print(f"  Type 6, entry [6]: \"{name}\" ({typename})  handler={handler_ref} prob={prob}")
        print(f"  Raw: [{entry.hex()}]")

        # Show a few neighboring entries for context
        for idx in range(max(0, 4), min(10, 30)):
            ea = ptr6 + idx * 48
            e = bytes(ram[ram_idx(ea):ram_idx(ea) + 48])
            if e == b'\x00' * 48: break
            n = e[:16].split(b'\x00')[0].decode('ascii', errors='ignore')
            h = e[0x18]
            p = e[0x1D]
            marker = " <-- Goblin +0x2A=6" if idx == 6 else ""
            print(f"    [{idx:2d}] \"{n}\"  handler={h} prob={p}{marker}")


# ===================================================================
# SECTION 6: Find the REAL monster AI decision function
# ===================================================================
def section6_find_monster_ai(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 6: Find functions that call entity_validate AND jalr (not spell dispatch)")
    print("=" * 100)

    # Find all callers of 0x80026840
    validate_callers = find_jal_callers(exe, ENTITY_VALIDATE, EXE_LOAD_ADDR,
                                         EXE_LOAD_ADDR + 0x35000)
    print(f"  Found {len(validate_callers)} calls to entity_validate (0x{ENTITY_VALIDATE:08X})")

    # For each caller, find the enclosing function and check if it also has jalr
    candidate_functions = {}  # func_start -> {callers, has_jalr, has_spell_dispatch, jal_targets}

    for caller in validate_callers:
        func = find_function_start(exe, caller)
        if not func:
            continue

        if func not in candidate_functions:
            # Scan the function for jalr and jal targets
            has_jalr = False
            has_spell_dispatch = False
            jal_targets = set()
            jalr_addrs = []

            for scan_addr in range(func, func + 0x2000, 4):
                si = exe_idx(scan_addr)
                if si < 0 or si + 4 > len(exe):
                    break
                sw = struct.unpack_from('<I', exe, si)[0]
                so = (sw >> 26) & 0x3F
                sf = sw & 0x3F

                if so == 0x03:  # jal
                    target = (sw & 0x03FFFFFF) << 2 | (scan_addr & 0xF0000000)
                    jal_targets.add(target)
                    if target == SPELL_DISPATCH:
                        has_spell_dispatch = True
                elif so == 0 and sf == 0x09:  # jalr
                    has_jalr = True
                    jalr_addrs.append(scan_addr)
                elif so == 0 and sf == 0x08 and ((sw >> 21) & 0x1F) == 31:
                    # jr $ra - end of function
                    break

            candidate_functions[func] = {
                'validate_callers': [caller],
                'has_jalr': has_jalr,
                'has_spell_dispatch': has_spell_dispatch,
                'jal_targets': jal_targets,
                'jalr_addrs': jalr_addrs,
            }
        else:
            candidate_functions[func]['validate_callers'].append(caller)

    # Show functions that have jalr but are NOT the spell dispatch
    print(f"\n  Functions calling entity_validate that also have jalr:")
    interesting_funcs = []
    for func, info in sorted(candidate_functions.items()):
        if info['has_jalr'] and not info['has_spell_dispatch']:
            # Skip functions that ARE one of the 55 handlers
            if HANDLER_RANGE_LO <= func <= HANDLER_RANGE_HI:
                continue
            interesting_funcs.append((func, info))
            print(f"\n    0x{func:08X}: jalr at {[f'0x{a:08X}' for a in info['jalr_addrs']]}")
            print(f"      validate calls: {[f'0x{c:08X}' for c in info['validate_callers']]}")
            print(f"      other calls: {sorted([f'0x{t:08X}' for t in info['jal_targets']])}")

    # Also show functions WITH spell dispatch for comparison
    print(f"\n  Functions calling entity_validate WITH spell dispatch:")
    for func, info in sorted(candidate_functions.items()):
        if info['has_spell_dispatch']:
            print(f"    0x{func:08X}: calls spell dispatch + validate")
            print(f"      other calls: {sorted([f'0x{t:08X}' for t in info['jal_targets']])}")

    # For the interesting functions (validate + jalr, no spell dispatch), show full disassembly
    for func, info in interesting_funcs[:5]:  # Limit to first 5
        print(f"\n  === Detailed disassembly of candidate 0x{func:08X} ===")
        lines = disasm_range(exe, EXE_LOAD_ADDR, func, 60, EXE_HEADER_SIZE)
        for a, w, asm in lines:
            marker = ""
            if '0x80026840' in asm: marker = "  <-- entity validate"
            elif 'jalr' in asm: marker = "  <-- INDIRECT DISPATCH"
            elif 'jal' in asm and 'jalr' not in asm:
                target = (w & 0x03FFFFFF) << 2 | (a & 0xF0000000)
                if HANDLER_RANGE_LO <= target <= HANDLER_RANGE_HI:
                    marker = "  <-- COMBAT HANDLER!"
            elif 'sll' in asm and ',2' in asm: marker = "  <-- *4 (table index?)"
            # Check for entity address range comparisons
            elif '0x8005' in asm or '0x800B' in asm:
                marker = "  <-- entity region ref?"
            print(f"      0x{a:08X}: {asm:48s}{marker}")


# ===================================================================
# SECTION 7: Check the "battle turn" logic
# ===================================================================
def section7_battle_turn(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 7: Battle turn management - iteration over battle entities")
    print("=" * 100)

    # The battle table is at 0x800BB93C, stride 0x9C, 12 entries
    # Search for code that references 0x800BB93C or iterates with stride 0x9C

    # Search for lui 0x800C (because 0x800BB93C = 0x800C0000 - 0x46C4)
    # Or lui 0x800B, addiu/ori 0xB93C
    # 0x800BB93C: 0xB93C >= 0x8000, so lui 0x800C, addiu -0x46C4 (0xB93C)
    # Wait: 0xB93C: lui 0x800C, addiu 0xB93C - 0x10000 = -0x46C4
    # Actually: 0x800BB93C = 0x800C0000 + (-0x46C4) = 0x800C0000 - 0x46C4
    # lui 0x800C = load 0x800C0000
    # addiu $r, $r, -0x46C4 (= 0xB93C as unsigned 16-bit)

    battle_hi = 0x800C
    battle_lo = 0xB93C  # = -0x46C4 as signed

    print(f"\n  --- 7a: Search for references to battle table 0x{BATTLE_TABLE:08X} ---")
    print(f"  Expected: lui 0x{battle_hi:04X} + addiu 0x{battle_lo:04X}")

    battle_refs = []
    for addr in range(EXE_LOAD_ADDR, EXE_LOAD_ADDR + 0x35000, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF

        if opcode == 0x0F and imm == battle_hi:  # lui 0x800C
            # Look forward for addiu/ori with battle_lo
            for fwd in range(1, 10):
                fa = addr + fwd * 4
                fi = exe_idx(fa)
                if fi < 0 or fi + 4 > len(exe):
                    break
                fw = struct.unpack_from('<I', exe, fi)[0]
                fo = (fw >> 26) & 0x3F
                fimm = fw & 0xFFFF
                frs = (fw >> 21) & 0x1F
                if fo in (0x09, 0x0D) and fimm == battle_lo and frs == rt:
                    battle_refs.append((addr, fa))
                    break

    print(f"  Found {len(battle_refs)} references to battle table address")
    for lui_addr, lo_addr in battle_refs:
        func = find_function_start(exe, lui_addr)
        func_str = f"func 0x{func:08X}" if func else "???"
        print(f"\n    lui@0x{lui_addr:08X} lo@0x{lo_addr:08X} ({func_str})")

        # Disassemble surrounding context
        ctx_start = lui_addr - 4 * 4
        lines = disasm_range(exe, EXE_LOAD_ADDR, ctx_start, 30, EXE_HEADER_SIZE)
        for a, w, asm in lines:
            marker = ""
            if a == lui_addr: marker = "  <-- lui battle_table_hi"
            elif a == lo_addr: marker = "  <-- lo battle_table_lo"
            elif 'jalr' in asm: marker = "  <-- INDIRECT CALL"
            elif 'jal' in asm and 'jalr' not in asm:
                target = (w & 0x03FFFFFF) << 2 | (a & 0xF0000000)
                if target == ENTITY_VALIDATE: marker = "  <-- entity validate"
                elif target == SPELL_DISPATCH: marker = "  <-- spell dispatch"
            elif 'addiu' in asm and '156' in asm: marker = "  <-- stride 0x9C!"
            elif 'addiu' in asm and ('0x009C' in asm.upper() or ',156' in asm):
                marker = "  <-- stride 0x9C!"
            print(f"      0x{a:08X}: {asm:48s}{marker}")

    # Search for stride 0x9C (156)
    print(f"\n  --- 7b: Search for addiu with value 0x9C (156) - battle entity stride ---")
    stride_refs = []
    for addr in range(EXE_LOAD_ADDR, EXE_LOAD_ADDR + 0x35000, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000

        if opcode == 0x09 and simm == 0x9C:  # addiu with +156
            rs = (word >> 21) & 0x1F
            rt = (word >> 16) & 0x1F
            asm = disasm(word, addr)
            func = find_function_start(exe, addr)
            func_str = f"func 0x{func:08X}" if func else "???"
            stride_refs.append((addr, func, asm))

    print(f"  Found {len(stride_refs)} addiu with stride 0x9C:")
    for addr, func, asm in stride_refs:
        func_str = f"func 0x{func:08X}" if func else "???"
        print(f"    0x{addr:08X}: {asm:48s} ({func_str})")

    # For each unique function with stride 0x9C, check if it also references battle table
    print(f"\n  --- 7c: Functions with stride 0x9C + battle table ref ---")
    stride_funcs = set(func for _, func, _ in stride_refs if func)
    for func in sorted(stride_funcs):
        # Scan function for battle table reference
        has_battle_ref = False
        has_jal_targets = []
        has_jalr = False

        for scan in range(func, func + 0x1000, 4):
            si = exe_idx(scan)
            if si < 0 or si + 4 > len(exe):
                break
            sw = struct.unpack_from('<I', exe, si)[0]
            so = (sw >> 26) & 0x3F
            sf = sw & 0x3F
            simm = sw & 0xFFFF

            if so == 0x0F and simm == battle_hi:
                has_battle_ref = True
            if so == 0x03:  # jal
                target = (sw & 0x03FFFFFF) << 2 | (scan & 0xF0000000)
                has_jal_targets.append(target)
            if so == 0 and sf == 0x09:  # jalr
                has_jalr = True
            if so == 0 and sf == 0x08 and ((sw >> 21) & 0x1F) == 31:
                break

        tag = ""
        if has_battle_ref: tag += " [BATTLE_TABLE]"
        if has_jalr: tag += " [JALR]"
        print(f"\n    func 0x{func:08X}{tag}")
        if has_jal_targets:
            for t in has_jal_targets:
                tag2 = ""
                if t == ENTITY_VALIDATE: tag2 = " (entity_validate)"
                elif t == SPELL_DISPATCH: tag2 = " (spell_dispatch)"
                elif HANDLER_RANGE_LO <= t <= HANDLER_RANGE_HI: tag2 = " (COMBAT HANDLER)"
                print(f"      calls 0x{t:08X}{tag2}")

        # If this function has both battle table ref and interesting calls, disassemble it
        if has_battle_ref:
            print(f"      Full disassembly:")
            lines = disasm_range(exe, EXE_LOAD_ADDR, func, 80, EXE_HEADER_SIZE)
            for a, w, asm in lines:
                marker = ""
                if 'jalr' in asm: marker = "  <-- INDIRECT CALL"
                elif f'0x{battle_hi:04X}' in asm: marker = "  <-- battle table ref"
                elif ',156' in asm or '0x009C' in asm.upper(): marker = "  <-- stride 0x9C"
                elif 'jal' in asm:
                    target = (w & 0x03FFFFFF) << 2 | (a & 0xF0000000)
                    if target == ENTITY_VALIDATE: marker = "  <-- entity validate"
                    elif target == SPELL_DISPATCH: marker = "  <-- spell dispatch"
                print(f"        0x{a:08X}: {asm:48s}{marker}")


# ===================================================================
# SECTION EXTRA: Search for the dispatch caller from 0x80017F2C
# ===================================================================
def section_extra_dispatch_caller(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION EXTRA: Analyze the state machine caller at 0x80017F2C")
    print("=" * 100)

    # The state machine dispatcher at 0x8003B324 is called from 0x80017F2C
    # Let's analyze this function

    func = find_function_start(exe, 0x80017F2C)
    if func:
        print(f"  Function containing 0x80017F2C starts at 0x{func:08X}")
        print(f"\n  Disassembly:")
        lines = disasm_range(exe, EXE_LOAD_ADDR, func, 80, EXE_HEADER_SIZE)
        for a, w, asm in lines:
            marker = ""
            if a == 0x80017F2C: marker = "  <-- state machine call site"
            elif 'jalr' in asm: marker = "  <-- INDIRECT CALL"
            elif '0x8003B324' in asm: marker = "  <-- state table ref"
            elif 'sll' in asm and ',2' in asm: marker = "  <-- *4 (index)"
            print(f"      0x{a:08X}: {asm:48s}{marker}")
    else:
        print("  Could not find function start!")

    # Also: find callers of the function that contains 0x80017F2C
    if func:
        print(f"\n  Callers of function 0x{func:08X}:")
        callers = find_jal_callers(exe, func, EXE_LOAD_ADDR, EXE_LOAD_ADDR + 0x35000)
        for c in callers:
            cfunc = find_function_start(exe, c)
            cfunc_str = f"func 0x{cfunc:08X}" if cfunc else "???"
            print(f"    jal at 0x{c:08X} ({cfunc_str})")

    # The 0x80017F2C region: does it load from the state table?
    # Search for lui that forms the state table address 0x8003B324
    # 0x8003B324: 0xB324 >= 0x8000, so lui 0x8004, addiu 0xB324 - 0x10000
    st_hi = 0x8004
    st_lo = 0xB324

    print(f"\n  --- Search for state table references (lui 0x{st_hi:04X} + lo 0x{st_lo:04X}) ---")
    for addr in range(EXE_LOAD_ADDR, EXE_LOAD_ADDR + 0x35000, 4):
        idx = exe_idx(addr)
        if idx < 0 or idx + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, idx)[0]
        opcode = (word >> 26) & 0x3F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF

        if opcode == 0x0F and imm == st_hi:
            for fwd in range(1, 10):
                fa = addr + fwd * 4
                fi = exe_idx(fa)
                if fi < 0 or fi + 4 > len(exe):
                    break
                fw = struct.unpack_from('<I', exe, fi)[0]
                fo = (fw >> 26) & 0x3F
                fimm = fw & 0xFFFF
                frs = (fw >> 21) & 0x1F
                if fo in (0x09, 0x0D) and fimm == st_lo and frs == rt:
                    func2 = find_function_start(exe, addr)
                    func_str = f"func 0x{func2:08X}" if func2 else "???"
                    print(f"    lui@0x{addr:08X} lo@0x{fa:08X} ({func_str})")

                    # Show context
                    ctx_start = addr - 4 * 4
                    lines = disasm_range(exe, EXE_LOAD_ADDR, ctx_start, 24, EXE_HEADER_SIZE)
                    for a2, w2, asm2 in lines:
                        marker = ""
                        if a2 == addr: marker = "  <-- lui state_table_hi"
                        elif a2 == fa: marker = "  <-- lo state_table_lo"
                        elif 'jalr' in asm2: marker = "  <-- INDIRECT CALL"
                        elif 'sll' in asm2 and ',2' in asm2: marker = "  <-- *4"
                        print(f"        0x{a2:08X}: {asm2:48s}{marker}")
                    break


# ===================================================================
# SECTION 8: Comprehensive jalr search near combat code
# ===================================================================
def section8_comprehensive_jalr(exe, ram):
    print()
    print("=" * 100)
    print("  SECTION 8: ALL jalr sites in combat code region 0x80017000-0x80028000")
    print("=" * 100)

    # This gives us a complete map of every indirect function call in the combat system
    jalr_sites = find_jalr_sites(exe, 0x80017000, 0x80028000, EXE_LOAD_ADDR, EXE_HEADER_SIZE)

    print(f"  Found {len(jalr_sites)} jalr instructions")

    # Group by enclosing function
    by_func = {}
    for jalr_addr, rs, rd in jalr_sites:
        func = find_function_start(exe, jalr_addr)
        if func:
            by_func.setdefault(func, []).append((jalr_addr, rs))

    print(f"  In {len(by_func)} unique functions:")
    for func in sorted(by_func.keys()):
        jalrs = by_func[func]
        # Skip if function is one of the 55 handlers
        if HANDLER_RANGE_LO <= func <= HANDLER_RANGE_HI:
            continue

        # For each jalr, look at what's loaded before it
        print(f"\n    func 0x{func:08X} ({len(jalrs)} jalr sites):")
        for jalr_addr, rs in jalrs:
            # Look back for the lw that feeds this jalr
            lw_info = ""
            for back in range(1, 6):
                ba = jalr_addr - back * 4
                bi = exe_idx(ba)
                if bi < 0 or bi + 4 > len(exe):
                    continue
                bw = struct.unpack_from('<I', exe, bi)[0]
                bo = (bw >> 26) & 0x3F
                brt = (bw >> 16) & 0x1F
                if bo == 0x23 and brt == rs:  # lw
                    brs = (bw >> 21) & 0x1F
                    boff = bw & 0xFFFF
                    if boff >= 0x8000: boff -= 0x10000
                    lw_info = f" <- lw {REGS[rs]},{boff}({REGS[brs]})"
                    break

            print(f"      jalr {REGS[rs]} @ 0x{jalr_addr:08X}{lw_info}")


# ===================================================================
# Main
# ===================================================================
def main():
    print("=" * 100)
    print("  BLAZE & BLADE - Find Monster Ability Dispatch Mechanism")
    print("=" * 100)
    print(f"  EXE:       {EXE_PATH}")
    print(f"  BLAZE.ALL: {BLAZE_ALL}")
    print(f"  Savestate: {SAVESTATE}")
    print()

    # Load EXE
    exe = bytearray(Path(EXE_PATH).read_bytes())
    print(f"  EXE loaded: {len(exe):,} bytes")

    # Load RAM from savestate
    raw = gzip.open(str(SAVESTATE), 'rb').read()
    ram = bytearray(raw[SAVESTATE_RAM_OFF : SAVESTATE_RAM_OFF + RAM_SIZE])
    print(f"  RAM extracted: {len(ram):,} bytes")

    # Verify EXE/RAM match
    exe_check = exe[EXE_HEADER_SIZE:EXE_HEADER_SIZE+8]
    ram_check = ram[ram_idx(EXE_LOAD_ADDR):ram_idx(EXE_LOAD_ADDR)+8]
    print(f"  EXE/RAM verify: {'MATCH' if bytes(exe_check) == bytes(ram_check) else 'MISMATCH'}")
    print()

    # Run all sections
    section1_find_handler_callers(exe, ram)
    section2_spell_dispatch_callers(exe, ram)
    section3_state_machine(exe, ram)
    section4_overlay_search(exe, ram)
    section5_stat_fields(exe, ram)
    section6_find_monster_ai(exe, ram)
    section7_battle_turn(exe, ram)
    section_extra_dispatch_caller(exe, ram)
    section8_comprehensive_jalr(exe, ram)

    print()
    print("=" * 100)
    print("  ANALYSIS COMPLETE")
    print("=" * 100)


if __name__ == '__main__':
    main()
