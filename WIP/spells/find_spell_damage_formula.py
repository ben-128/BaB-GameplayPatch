# -*- coding: cp1252 -*-
"""
Find the spell damage formula in the PS1 EXE (SLES_008.45).

Strategy:
1. Disassemble key combat functions
2. Search for lbu/lhu/lw with offset 0x18 (spell damage field)
3. Search for mult/multu/div/divu near those loads
4. Trace how spell entry fields combine with entity stats
5. Dump the combat action handler table at 0x8003C1B0
6. Check known combat functions called from overlay clusters

PS-X EXE offset formula: file_offset = (RAM - 0x80010000) + 0x800
"""

import struct
import os
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
EXE_PATH = os.path.join(PROJECT_DIR,
    "Blaze  Blade - Eternal Quest (Europe)", "extract", "SLES_008.45")

if not os.path.exists(EXE_PATH):
    print("ERROR: EXE not found at: %s" % EXE_PATH)
    sys.exit(1)

with open(EXE_PATH, 'rb') as f:
    exe_data = f.read()

print("EXE size: %d bytes (0x%X)" % (len(exe_data), len(exe_data)))

# ============================================================
# MIPS Disassembler (minimal, R3000A subset)
# ============================================================

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
    """Disassemble one MIPS instruction. Returns mnemonic string."""
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

    # R-type (op=0)
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
        return "R-type funct=0x%02X rd=%s rs=%s rt=%s" % (funct, REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])

    # J-type
    if op == 0x02:
        jaddr = (addr & 0xF0000000) | target
        return "j 0x%08X" % jaddr
    if op == 0x03:
        jaddr = (addr & 0xF0000000) | target
        return "jal 0x%08X" % jaddr

    # I-type
    if op == 0x04: return "beq %s, %s, 0x%08X" % (REG_NAMES[rs], REG_NAMES[rt], addr + 4 + (imms << 2))
    if op == 0x05: return "bne %s, %s, 0x%08X" % (REG_NAMES[rs], REG_NAMES[rt], addr + 4 + (imms << 2))
    if op == 0x06: return "blez %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
    if op == 0x07: return "bgtz %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
    if op == 0x01:
        if rt == 0: return "bltz %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        if rt == 1: return "bgez %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        if rt == 16: return "bltzal %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        if rt == 17: return "bgezal %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        return "REGIMM rt=%d %s, 0x%08X" % (rt, REG_NAMES[rs], addr + 4 + (imms << 2))

    if op == 0x08: return "addi %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x09: return "addiu %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0A: return "slti %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0B: return "sltiu %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0C: return "andi %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0D: return "ori %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0E: return "xori %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0F: return "lui %s, 0x%04X" % (REG_NAMES[rt], imm)

    # Load/Store
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
    if op == 0x2A: return "swl %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x2E: return "swr %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])

    # Coprocessor
    if op == 0x10: return "COP0 (0x%08X)" % word
    if op == 0x12: return "COP2/GTE (0x%08X)" % word

    return "??? op=0x%02X (0x%08X)" % (op, word)


def ram_to_file(ram_addr):
    """Convert RAM address to file offset in SLES_008.45"""
    return (ram_addr - 0x80010000) + 0x800

def file_to_ram(file_off):
    """Convert file offset to RAM address"""
    return (file_off - 0x800) + 0x80010000

def read_word(file_off):
    """Read 32-bit little-endian word from EXE data"""
    if file_off < 0 or file_off + 4 > len(exe_data):
        return None
    return struct.unpack_from('<I', exe_data, file_off)[0]

def disasm_range(ram_start, ram_end, label=""):
    """Disassemble a range of RAM addresses"""
    if label:
        print("\n" + "=" * 70)
        print("  %s  [0x%08X - 0x%08X]" % (label, ram_start, ram_end))
        print("=" * 70)
    results = []
    for addr in range(ram_start, ram_end, 4):
        foff = ram_to_file(addr)
        w = read_word(foff)
        if w is None:
            continue
        asm = disasm_one(w, addr)
        line = "  0x%08X [f:0x%06X]: %08X  %s" % (addr, foff, w, asm)
        print(line)
        results.append((addr, w, asm))
    return results


# ============================================================
# PART 1: Disassemble known combat functions
# ============================================================

print("\n" + "#" * 70)
print("#  PART 1: Key Combat Functions Disassembly")
print("#" * 70)

# Function 0x80026A90 - Spell select function (called from overlay cluster 1)
# This reads spell entry fields (+0x10, +0x11, +0x12) and calls overlay
disasm_range(0x80026A90, 0x80026B80, "0x80026A90 - Spell Select Function")

# Function 0x80024C94 - Part of dispatch/level-up loop
disasm_range(0x80024C94, 0x80024E00, "0x80024C94 - Dispatch/Stat Function")

# Function 0x80024088 - Unknown combat utility
disasm_range(0x80024088, 0x80024200, "0x80024088 - Combat Utility (unknown)")

# Function 0x80024024 - Stat scaling
disasm_range(0x80024024, 0x80024088, "0x80024024 - Stat Scaling Function")

# Function 0x80023A10 - Stat copy
disasm_range(0x80023A10, 0x80023B00, "0x80023A10 - Stat Copy Function")

# Function 0x80023C2C - Derived stat (ATK/DEF)
disasm_range(0x80023C2C, 0x80023E7C, "0x80023C2C - Derived Stat (ATK/DEF)")

# Function 0x80023E7C - Equipment/buff aggregation
disasm_range(0x80023E7C, 0x80024024, "0x80023E7C - Equipment/Buff Aggregation")


# ============================================================
# PART 2: Search for loads from spell entry offset +0x18 (damage)
# ============================================================

print("\n" + "#" * 70)
print("#  PART 2: Search for spell entry +0x18 loads (damage field)")
print("#" * 70)

# Search entire EXE for lbu/lhu/lw with offset 0x18
# lbu: op=0x24, lhu: op=0x25, lw: op=0x23
# Also check lh (op=0x21) and lb (op=0x20)
LOAD_OPS = {0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu", 0x25: "lhu"}

spell_damage_loads = []  # (file_off, ram_addr, word, mnemonic, rt, rs)

for foff in range(0x800, len(exe_data) - 4, 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    if op not in LOAD_OPS:
        continue
    imm = w & 0xFFFF
    imms = sign_extend_16(imm)
    if imms != 0x18:
        continue

    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    ram = file_to_ram(foff)
    mnem = LOAD_OPS[op]
    spell_damage_loads.append((foff, ram, w, mnem, rt, rs))

print("\nFound %d load instructions with offset +0x18:" % len(spell_damage_loads))
for foff, ram, w, mnem, rt, rs in spell_damage_loads:
    print("  0x%08X [f:0x%06X]: %s %s, 0x18(%s)" % (ram, foff, mnem, REG_NAMES[rt], REG_NAMES[rs]))

# For each +0x18 load, look for mult/div within +/- 20 instructions
print("\n--- Checking for arithmetic (mult/div) near +0x18 loads ---")

ARITH_FUNCTS = {0x18: "mult", 0x19: "multu", 0x1A: "div", 0x1B: "divu"}

for foff, ram, w, mnem, rt, rs in spell_damage_loads:
    nearby_arith = []
    for delta in range(-20, 21):
        check_off = foff + delta * 4
        if check_off < 0x800 or check_off + 4 > len(exe_data):
            continue
        cw = struct.unpack_from('<I', exe_data, check_off)[0]
        cop = (cw >> 26) & 0x3F
        cfunct = cw & 0x3F
        if cop == 0 and cfunct in ARITH_FUNCTS:
            crs = (cw >> 21) & 0x1F
            crt = (cw >> 16) & 0x1F
            cram = file_to_ram(check_off)
            nearby_arith.append((delta, cram, ARITH_FUNCTS[cfunct], crs, crt))

    if nearby_arith:
        print("\n  ** 0x%08X: %s %s, 0x18(%s)  -- has %d nearby arithmetic:" % (
            ram, mnem, REG_NAMES[rt], REG_NAMES[rs], len(nearby_arith)))
        for delta, cram, aname, ars, art in nearby_arith:
            print("      [%+3d] 0x%08X: %s %s, %s" % (
                delta, cram, aname, REG_NAMES[ars], REG_NAMES[art]))


# ============================================================
# PART 3: Search for ALL mult/multu/div/divu in combat area
# ============================================================

print("\n" + "#" * 70)
print("#  PART 3: All mult/div in combat function range (0x80023000-0x80028000)")
print("#" * 70)

combat_start_ram = 0x80023000
combat_end_ram = 0x80028000
combat_start_f = ram_to_file(combat_start_ram)
combat_end_f = ram_to_file(combat_end_ram)

arith_in_combat = []
for foff in range(combat_start_f, min(combat_end_f, len(exe_data) - 4), 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    funct = w & 0x3F
    if op == 0 and funct in ARITH_FUNCTS:
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        ram = file_to_ram(foff)
        arith_in_combat.append((ram, foff, ARITH_FUNCTS[funct], rs, rt))

print("\nFound %d mult/div instructions in combat range:" % len(arith_in_combat))
for ram, foff, aname, rs, rt in arith_in_combat:
    # Show context: 3 instructions before and after
    print("\n  0x%08X: %s %s, %s" % (ram, aname, REG_NAMES[rs], REG_NAMES[rt]))
    for d in range(-3, 4):
        cf = foff + d * 4
        if cf < 0x800 or cf + 4 > len(exe_data):
            continue
        cw = struct.unpack_from('<I', exe_data, cf)[0]
        cram = file_to_ram(cf)
        casm = disasm_one(cw, cram)
        marker = " >>>" if d == 0 else "    "
        print("    %s 0x%08X: %08X  %s" % (marker, cram, cw, casm))


# ============================================================
# PART 4: Combat Action Handler Table at 0x8003C1B0
# ============================================================

print("\n" + "#" * 70)
print("#  PART 4: Combat Action Handler Table (0x8003C1B0, 55 entries)")
print("#" * 70)

handler_table_ram = 0x8003C1B0
handler_table_foff = ram_to_file(handler_table_ram)

print("\nHandler table at 0x%08X (file 0x%06X):" % (handler_table_ram, handler_table_foff))
handlers = []
for i in range(55):
    off = handler_table_foff + i * 4
    w = read_word(off)
    if w is None:
        break
    handlers.append(w)
    print("  [%2d] 0x%08X" % (i, w))

# Count unique handlers
unique_handlers = sorted(set(handlers))
print("\n%d unique handler addresses out of %d entries:" % (len(unique_handlers), len(handlers)))
for h in unique_handlers:
    count = handlers.count(h)
    indices = [i for i, v in enumerate(h == v for v in handlers) if v]
    # Actually re-count properly
    indices = [i for i in range(len(handlers)) if handlers[i] == h]
    print("  0x%08X  (used %d times, indices: %s)" % (h, count, indices))


# ============================================================
# PART 5: Disassemble the most interesting combat action handlers
# ============================================================

print("\n" + "#" * 70)
print("#  PART 5: Disassemble unique combat action handlers")
print("#" * 70)

# For each unique handler, disassemble first 40 instructions to see what they do
for h_addr in unique_handlers:
    if h_addr < 0x80010000 or h_addr > 0x80050000:
        print("\n  Handler 0x%08X -- outside EXE range, skip" % h_addr)
        continue
    foff = ram_to_file(h_addr)
    if foff < 0 or foff + 160 > len(exe_data):
        print("\n  Handler 0x%08X -- outside file range, skip" % h_addr)
        continue

    # Disassemble until jr $ra or 60 instructions, whichever comes first
    print("\n--- Handler 0x%08X ---" % h_addr)
    for i in range(60):
        addr = h_addr + i * 4
        w = read_word(ram_to_file(addr))
        if w is None:
            break
        asm = disasm_one(w, addr)
        print("  0x%08X: %08X  %s" % (addr, w, asm))
        # Stop after jr $ra + delay slot
        if (w & 0xFC1FFFFF) == 0x03E00008:  # jr $ra
            # Print delay slot too
            addr2 = addr + 4
            w2 = read_word(ram_to_file(addr2))
            if w2 is not None:
                asm2 = disasm_one(w2, addr2)
                print("  0x%08X: %08X  %s" % (addr2, w2, asm2))
            break


# ============================================================
# PART 6: Search for OTHER spell entry field accesses
# ============================================================

print("\n" + "#" * 70)
print("#  PART 6: Search for other spell entry field loads")
print("#" * 70)

# Spell entry is 48 bytes. Key offsets:
# +0x10=spell_id, +0x11=flags, +0x12=param, +0x13=MP, +0x14=level/power
# +0x16=element, +0x17=unknown, +0x18=damage, +0x1C=target, +0x1D=cast_prob
# +0x1E=unknown_param, +0x1F=ingredient_count
# We look for loads with these specific small offsets in the combat code range

SPELL_FIELD_OFFSETS = {
    0x10: "spell_id", 0x11: "flags", 0x12: "param_0x12",
    0x13: "MP_cost", 0x14: "level_power", 0x15: "unk_0x15",
    0x16: "element", 0x17: "unk_0x17", 0x18: "damage",
    0x19: "unk_0x19", 0x1A: "unk_0x1A", 0x1B: "unk_0x1B",
    0x1C: "target_type", 0x1D: "cast_prob", 0x1E: "unk_0x1E",
    0x1F: "ingredient_count"
}

# Narrow search: only in the range around known spell-related functions
# 0x80024000-0x80027000 covers dispatch, stat functions, spell select
search_ranges = [
    (0x80024000, 0x80027000, "combat/dispatch area"),
    (0x80017B00, 0x80018000, "ai_run_bytecode entry"),
]

for range_start, range_end, range_name in search_ranges:
    print("\n--- Searching %s (0x%08X-0x%08X) ---" % (range_name, range_start, range_end))
    for foff in range(ram_to_file(range_start), min(ram_to_file(range_end), len(exe_data) - 4), 4):
        w = struct.unpack_from('<I', exe_data, foff)[0]
        op = (w >> 26) & 0x3F
        if op not in LOAD_OPS:
            continue
        imm = w & 0xFFFF
        imms = sign_extend_16(imm)
        if imms not in SPELL_FIELD_OFFSETS:
            continue
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        ram = file_to_ram(foff)
        field_name = SPELL_FIELD_OFFSETS[imms]
        mnem = LOAD_OPS[op]
        print("  0x%08X: %s %s, 0x%02X(%s)  ; %s" % (
            ram, mnem, REG_NAMES[rt], imms, REG_NAMES[rs], field_name))


# ============================================================
# PART 7: Deep analysis of 0x80024494 dispatch function
# ============================================================

print("\n" + "#" * 70)
print("#  PART 7: Full Dispatch Function 0x80024494 (~2.7KB)")
print("#" * 70)

# The dispatch function is ~2.7KB = ~680 instructions
# From 0x80024494 to about 0x80024F04 + some tail
disasm_range(0x80024494, 0x80025000, "0x80024494 - Full Dispatch Function")


# ============================================================
# PART 8: Search for specific patterns indicating damage formula
# ============================================================

print("\n" + "#" * 70)
print("#  PART 8: Targeted patterns - damage formula indicators")
print("#" * 70)

# Pattern 1: lbu with offset 0x18 followed within 10 instr by mult
# Pattern 2: lhu with offset 0x120-0x140 (entity stat region) near mult
# Pattern 3: mflo/mfhi (read mult result) near stores to entity HP area

# Search entity stat loads (0x120-0x140 range, entity stat area)
print("\n--- Entity stat loads (offset 0x0120-0x015F) in combat area ---")
for foff in range(ram_to_file(0x80023000), min(ram_to_file(0x80028000), len(exe_data) - 4), 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    if op not in LOAD_OPS:
        continue
    imm = w & 0xFFFF
    imms = sign_extend_16(imm)
    if 0x0120 <= imms <= 0x015F:
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        ram = file_to_ram(foff)
        mnem = LOAD_OPS[op]
        print("  0x%08X: %s %s, 0x%04X(%s)" % (ram, mnem, REG_NAMES[rt], imms, REG_NAMES[rs]))

# Also search for entity+0x154 area (other stats)
print("\n--- Entity extended stat loads (offset 0x0150-0x019F) in combat area ---")
for foff in range(ram_to_file(0x80023000), min(ram_to_file(0x80028000), len(exe_data) - 4), 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    if op not in LOAD_OPS:
        continue
    imm = w & 0xFFFF
    imms = sign_extend_16(imm)
    if 0x0150 <= imms <= 0x019F:
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        ram = file_to_ram(foff)
        mnem = LOAD_OPS[op]
        print("  0x%08X: %s %s, 0x%04X(%s)" % (ram, mnem, REG_NAMES[rt], imms, REG_NAMES[rs]))


# ============================================================
# PART 9: Trace the trap damage function for comparison
# ============================================================

print("\n" + "#" * 70)
print("#  PART 9: Trap Damage Function 0x80024F90 (known formula)")
print("#" * 70)

# This function has known formula: damage = (maxHP * param%) / 100
# Disassemble it for comparison
disasm_range(0x80024F90, 0x80025100, "0x80024F90 - Trap Damage (maxHP * param / 100)")


# ============================================================
# PART 10: Search entire EXE for 0x18 loads near entity stat loads
# ============================================================

print("\n" + "#" * 70)
print("#  PART 10: Cross-reference: +0x18 loads near entity stat loads")
print("#" * 70)

# For each +0x18 load, check if there's an entity stat load (0x120-0x160)
# within +/- 15 instructions, suggesting they're in the same function

ENTITY_STAT_RANGE = range(0x0120, 0x0200)

for foff, ram, w, mnem, rt, rs in spell_damage_loads:
    nearby_stat_loads = []
    for delta in range(-15, 16):
        check_off = foff + delta * 4
        if check_off < 0x800 or check_off + 4 > len(exe_data):
            continue
        cw = struct.unpack_from('<I', exe_data, check_off)[0]
        cop = (cw >> 26) & 0x3F
        if cop not in LOAD_OPS:
            continue
        cimm = sign_extend_16(cw & 0xFFFF)
        if cimm in ENTITY_STAT_RANGE:
            crs = (cw >> 21) & 0x1F
            crt = (cw >> 16) & 0x1F
            cram = file_to_ram(check_off)
            nearby_stat_loads.append((delta, cram, LOAD_OPS[cop], crt, crs, cimm))

    if nearby_stat_loads:
        print("\n  ** 0x%08X: %s %s, 0x18(%s)  -- NEAR entity stat loads:" % (
            ram, mnem, REG_NAMES[rt], REG_NAMES[rs]))
        for delta, cram, cmnem, crt, crs, cimm in nearby_stat_loads:
            print("      [%+3d] 0x%08X: %s %s, 0x%04X(%s)" % (
                delta, cram, cmnem, REG_NAMES[crt], cimm, REG_NAMES[crs]))


# ============================================================
# PART 11: Look at 0x80024F04 (dispatch function tail)
# ============================================================

print("\n" + "#" * 70)
print("#  PART 11: Dispatch function tail (0x80024E00 - 0x80025100)")
print("#" * 70)

disasm_range(0x80024E00, 0x80025100, "0x80024E00 - Dispatch tail + trap damage")


# ============================================================
# PART 12: Check JAL callers of 0x80024F90 in EXE
# ============================================================

print("\n" + "#" * 70)
print("#  PART 12: JAL callers of spell-related EXE functions")
print("#" * 70)

# Check who calls 0x80024C94, 0x80026A90, 0x80024F90
target_functions = [
    (0x80024C94, "dispatch_stat_function"),
    (0x80026A90, "spell_select"),
    (0x80024F90, "trap_damage"),
    (0x80024494, "main_dispatch"),
    (0x80024024, "stat_scaling"),
    (0x80023C2C, "derived_stats"),
    (0x80024088, "combat_utility"),
]

for target_ram, name in target_functions:
    jal_word = (0x03 << 26) | ((target_ram >> 2) & 0x3FFFFFF)
    callers = []
    for foff in range(0x800, len(exe_data) - 4, 4):
        w = struct.unpack_from('<I', exe_data, foff)[0]
        if w == jal_word:
            callers.append(file_to_ram(foff))

    print("\n  jal 0x%08X (%s): %d callers in EXE" % (target_ram, name, len(callers)))
    for c in callers:
        print("    0x%08X" % c)

print("\n" + "#" * 70)
print("#  ANALYSIS COMPLETE")
print("#" * 70)
