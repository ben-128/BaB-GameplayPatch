# -*- coding: cp1252 -*-
"""
Spell damage formula search v3 - Final deep dives.

CRITICAL FINDINGS from v2:
- Handler [10] (0x800276B0) is a SPELL DAMAGE handler
- It loads from action_struct+0x06 (spell_list_idx) and +0x07 (spell_id)
- Computes: $a1 = spell_table[list_idx][spell_id * 48]
- Then: lhu $v0, 24($a1) = spell entry +0x18 = DAMAGE VALUE
- Combines with: entity INT stat / 3 + 40 (approx)
- Final damage = (INT_stat / 3) + spell_entry_0x18 value

Need to verify:
1. What does 0x80023698 do? (target selection / hit check)
2. What do entity offsets 0x38 and 0x2A represent? (loaded from target entity)
3. How is the handler dispatched (what sets the action type byte?)
4. Are handlers [11]-[13] identical patterns with different target offsets?
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
    if word == 0: return "nop"
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
        if funct == 0x10: return "mfhi %s" % REG_NAMES[rd]
        if funct == 0x11: return "mthi %s" % REG_NAMES[rs]
        if funct == 0x12: return "mflo %s" % REG_NAMES[rd]
        if funct == 0x13: return "mtlo %s" % REG_NAMES[rs]
        if funct == 0x18: return "mult %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x19: return "multu %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x1A: return "div %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x1B: return "divu %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        return "R-type funct=0x%02X" % funct
    if op == 0x02: return "j 0x%08X" % ((addr & 0xF0000000) | target)
    if op == 0x03: return "jal 0x%08X" % ((addr & 0xF0000000) | target)
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
# SECTION 1: Function 0x80023698 (called by spell handlers)
# ============================================================

print("=" * 70)
print("SECTION 1: Function 0x80023698 (target selection/hit check)")
print("  Called as: jal 0x80023698")
print("  Args: $a0=action_struct, $a1=target_entity, $a2=&local, $a3=&local")
print("  Returns: 0=success, nonzero=miss/fail")
print("=" * 70)
disasm_range(0x80023698, 0x80023A10, "0x80023698")


# ============================================================
# SECTION 2: Annotated handler [10] reconstruction
# ============================================================

print("\n" + "=" * 70)
print("SECTION 2: Handler [10] = 0x800276B0 ANNOTATED")
print("=" * 70)
print("""
PSEUDOCODE RECONSTRUCTION of handler [10]:

handler_10(action_struct *$a0, entity_caster *$a1, some_param $a2):
    $s0 = $a0   // action_struct pointer
    sp[0x10] = 3  // target_type? (single target)
    sp[0x14] = $a2

    ret = target_select_0x80023698($a0, $a1, &sp[0x18], &sp[0x1C])
    // sp[0x18] = caster_entity_ptr
    // sp[0x1C] = target_entity_ptr
    if (ret != 0) goto exit  // miss/fail

    spell_list_idx = lbu action_struct[7]   // +0x07 = spell list index
    spell_id       = lbu action_struct[6]   // +0x06 = spell slot in list

    // Compute spell entry pointer:
    data_ptr = *(0x8005490C)                // global data pointer
    pointer_table = *(data_ptr + 0x9C)      // spell pointer table
    list_base = pointer_table[spell_list_idx]

    // spell_id * 48: (id << 1 + id) << 4 = id * 3 * 16 = id * 48
    spell_entry = list_base + spell_id * 48
    $a1 = spell_entry

    // Load caster entity from sp[0x18]
    caster = sp[0x18]

    // Load caster stat at entity+0x38 (INT? WIL?)
    stat_raw = lhu caster[0x38]             // entity+0x38 (half-word, unsigned)
    stat_div2 = (int16)(stat_raw) >> 3      // signed right shift by 3 = /8
    stat_val = stat_div2 + 40               // base offset of 40

    // Load caster stat at entity+0x2A
    stat2_raw = lhu caster[0x2A]            // entity+0x2A (another stat)
    stat2 = (int16)(stat2_raw)

    // Division by 3:  multiply by 0x2AAAAAAB, take hi, shift right 2
    // This is compiler-generated division by 3
    stat2_div3 = stat2 / 3

    // The SPELL DAMAGE from entry:
    spell_dmg = lhu spell_entry[0x18]       // +0x18 = damage halfword!

    damage = stat2_div3 + spell_dmg         // stat/3 + spell_base_damage

    // Load target entity from sp[0x1C]
    target = sp[0x1C]

    // Check target+0x86 (some threshold/resistance)
    threshold = lhu target[0x86]
    if (threshold >= stat_val) goto exit

    // Apply damage:
    sh stat_val, target[0x86]               // update threshold
    sh damage, target[0xE4]                 // store final damage to target+0xE4

exit:
    return
""")


# ============================================================
# SECTION 3: Verify handler [11], [12], [13] patterns
# ============================================================

print("\n" + "=" * 70)
print("SECTION 3: Compare handlers [10]-[13] key differences")
print("=" * 70)

handlers = [
    (10, 0x800276B0, 0x800277A8),
    (11, 0x800277A8, 0x800278A0),
    (12, 0x800278A0, 0x80027998),
    (13, 0x80027998, 0x80027A90),
]

for idx, start, end in handlers:
    foff = ram_to_file(start)
    # Read the target_type value (4th instruction after prologue: ori $v0, $zero, N)
    w4 = read_word(foff + 4*4)  # 5th instruction (0-indexed: 4)
    target_type = w4 & 0xFFFF if w4 else 0

    # Find the specific store offsets (sh $a2/sh $a0 near end)
    # These tell us WHICH entity field gets written
    stores = []
    for addr in range(start, end, 4):
        fo = ram_to_file(addr)
        w = read_word(fo)
        if w is None:
            continue
        op = (w >> 26) & 0x3F
        if op == 0x29:  # sh
            rt = (w >> 16) & 0x1F
            rs = (w >> 21) & 0x1F
            imm = sign_extend_16(w & 0xFFFF)
            if rs != 29:  # skip stack stores
                stores.append("sh %s, 0x%04X(%s)" % (REG_NAMES[rt], imm & 0xFFFF, REG_NAMES[rs]))

    print("  Handler [%d] @ 0x%08X:" % (idx, start))
    print("    target_type = %d" % target_type)
    print("    stores: %s" % stores)


# ============================================================
# SECTION 4: What is entity+0x38? entity+0x2A?
# These are the stat offsets used in damage calculation
# ============================================================

print("\n" + "=" * 70)
print("SECTION 4: Entity struct field analysis")
print("  Handler [10] uses:")
print("    entity+0x38 (halfword) -> divided by 8, +40 -> 'power level'")
print("    entity+0x2A (halfword) -> divided by 3 -> 'stat contribution'")
print("    spell_entry+0x18 (halfword) -> base damage")
print("    target+0x86 -> threshold check, target+0xE4 -> damage output")
print("=" * 70)

# Search for other accesses to entity+0x38 and entity+0x2A in the combat code
# These are probably INT or WIL stats used for magic
print("\n--- Searching for lhu/lh with offset 0x38 in combat area ---")
for foff in range(ram_to_file(0x80023000), min(ram_to_file(0x80030000), len(exe_data) - 4), 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    if op not in (0x21, 0x25):  # lh, lhu
        continue
    imm = sign_extend_16(w & 0xFFFF)
    if imm == 0x38:
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        ram = (foff - 0x800) + 0x80010000
        mnem = "lh" if op == 0x21 else "lhu"
        print("  0x%08X: %s %s, 0x38(%s)" % (ram, mnem, REG_NAMES[rt], REG_NAMES[rs]))

print("\n--- Searching for lhu/lh with offset 0x2A in combat area ---")
for foff in range(ram_to_file(0x80023000), min(ram_to_file(0x80030000), len(exe_data) - 4), 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    if op not in (0x21, 0x25):
        continue
    imm = sign_extend_16(w & 0xFFFF)
    if imm == 0x2A:
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        ram = (foff - 0x800) + 0x80010000
        mnem = "lh" if op == 0x21 else "lhu"
        print("  0x%08X: %s %s, 0x2A(%s)" % (ram, mnem, REG_NAMES[rt], REG_NAMES[rs]))


# ============================================================
# SECTION 5: Function at 0x80025F00 (the one with div + lbu 0x1E)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 5: Function near 0x80025F00-0x80026200")
print("  Contains div $s6,$v0 where $v0 = lbu 0x1E($fp)")
print("  0x1E could be spell entry +0x1E field")
print("=" * 70)
disasm_range(0x80025E80, 0x80026200, "0x80025E80 - possible damage function")


# ============================================================
# SECTION 6: How are handlers dispatched? Find the jalr that
# uses the 0x8003C1B0 table
# ============================================================

print("\n" + "=" * 70)
print("SECTION 6: Find jalr dispatch for combat action handlers")
print("  Looking for: sll (index*4), addu (base+offset), lw (handler), jalr")
print("=" * 70)

# Search for jalr in the dispatch function range (0x80024494-0x80025000)
for addr in range(0x80024494, 0x80025000, 4):
    foff = ram_to_file(addr)
    w = read_word(foff)
    if w is None:
        continue
    op = (w >> 26) & 0x3F
    funct = w & 0x3F
    if op == 0 and funct == 0x09:  # jalr
        rs = (w >> 21) & 0x1F
        rd = (w >> 11) & 0x1F
        print("  jalr at 0x%08X: jalr %s, %s" % (addr, REG_NAMES[rd], REG_NAMES[rs]))
        # Print context
        for d in range(-10, 5):
            cf = foff + d * 4
            if cf < 0x800:
                continue
            cw = read_word(cf)
            if cw is None:
                continue
            cram = (cf - 0x800) + 0x80010000
            casm = disasm_one(cw, cram)
            marker = " >>>" if d == 0 else "    "
            print("    %s 0x%08X: %08X  %s" % (marker, cram, cw, casm))

# Also check the broader area
print("\n--- Searching whole EXE for lui + table access pattern ---")
# 0x8003C1B0 = table address
# Different ways to form it:
# Option 1: lui 0x8004 + addiu 0xC1B0
# But 0xC1B0 as signed = -15952, wait:
# 0x80040000 + (-15952) = 0x80040000 - 0x3E50 = 0x8003C1B0 YES
# So: lui $r, 0x8004; addiu $r, $r, -15952 OR lw from there

# Actually more likely: lui $r, 0x8004; then lw $r, -0x3E50($r)
# -0x3E50 = 0xC1B0 as signed 16-bit? No: -0x3E50 = 0xFFFFC1B0, and 0xC1B0 > 0x7FFF
# so as signed 16-bit: 0xC1B0 = -15952 + 65536? No.
# 0xC1B0 as unsigned = 49584. As signed: 49584 - 65536 = -15952
# So yes, signed representation of 0xC1B0 is -15952
# But the assembler would encode lw $r, 0xC1B0($base) as:
#   if base has 0x8004 -> effective = 0x80040000 + 0xC1B0 (unsigned)
# Wait, MIPS sign-extends the immediate. So:
#   lw $r, 0xC1B0($base) where base=0x80040000:
#   effective = 0x80040000 + sign_extend(0xC1B0) = 0x80040000 + (-15952) = 0x8003C1B0
# But 0xC1B0 = -15952 as signed? Let me check: 0xC1B0 = 49584.
# 49584 > 32767, so sign-extended = 49584 - 65536 = -15952
# 0x80040000 + (-15952) = 0x80040000 - 0x3E50 = 0x8003C1B0. Correct!

# So pattern: lui $r1, 0x8004 somewhere before lw $r2, -0x3E50($r1)
# -0x3E50 as 16-bit unsigned = 0xC1B0
# But we might also use it with an index: base + index*4
# More complex pattern: table_base = 0x8003C1B0
# handler = *(table_base + action_type * 4)
# So: sll $idx, $action_type, 2; lui $base, 0x8004; addu $addr, $base, $idx; lw $func, 0xC1B0($addr)

for foff in range(0x800, len(exe_data) - 4, 4):
    w = struct.unpack_from('<I', exe_data, foff)[0]
    op = (w >> 26) & 0x3F
    if op == 0x23:  # lw
        imm = w & 0xFFFF
        if imm == 0xC1B0:
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            ram = (foff - 0x800) + 0x80010000
            print("  *** lw %s, 0xC1B0(%s) at 0x%08X" % (REG_NAMES[rt], REG_NAMES[rs], ram))
            for d in range(-10, 10):
                cf = foff + d * 4
                if cf < 0x800 or cf + 4 > len(exe_data):
                    continue
                cw = read_word(cf)
                if cw is None:
                    continue
                cram = (cf - 0x800) + 0x80010000
                casm = disasm_one(cw, cram)
                marker = " >>>" if d == 0 else "    "
                print("    %s 0x%08X: %08X  %s" % (marker, cram, cw, casm))


# ============================================================
# SECTION 7: Check what sp+0x18/sp+0x1C are in context
# The handler loads entities from these stack slots (filled by 0x80023698)
# ============================================================

print("\n" + "=" * 70)
print("SECTION 7: ENTITY STRUCT LOW-OFFSET FIELDS")
print("  Handler [10] loads from entity+0x38 and entity+0x2A")
print("  These are NOT in the stat block (0x120+)")
print("  They could be in a combat-specific header area")
print("  Note: entity+0x08 = model slot (lbu 8($s0) in handlers [0],[1])")
print("=" * 70)

# Actually, the handler loads from sp[0x18] which is set by 0x80023698
# Let's look at what 0x80023698 stores there
# Also: entity+0x38 at halfword - in the entity struct this is at
# a very low offset, which in the 0x2000+ entity struct suggests
# it's a COMBAT ACTION STRUCT field, not the main entity struct

# The real question: what does sp[0x18] point to?
# It's filled by jal 0x80023698($a0=action_struct, $a1=target, $a2=&sp[0x18], $a3=&sp[0x1C])
# So &sp[0x18] and &sp[0x1C] are output pointers

# Wait - re-reading the handler more carefully:
# $a0 = action_struct ($s0)
# Then after 0x80023698 returns:
# lhu $v0, 56($v1) where $v1 = sp[0x18]
# 56 = 0x38
# lhu $v1, 42($v1) where $v1 = same sp[0x18]
# 42 = 0x2A
# Then later:
# lhu $v0, 134($v1) where $v1 = sp[0x1C]
# 134 = 0x86
# sh $a2, 134($v1) -> target[0x86]
# sh $a0, 228($v1) -> target[0xE4]
# 228 = 0xE4

# So sp[0x18] = CASTER entity ptr, sp[0x1C] = TARGET entity ptr
# Entity offsets: +0x38, +0x2A (caster), +0x86, +0xE4 (target)

# Wait, these are NOT main entity offsets like +0x120. These are
# much lower. If the entity struct starts at 0x800E0000-ish,
# these low offsets could be entirely different fields.

# Actually looking at handler [0]:
# It loads lbu 8($s0) and lbu 8($s2) where $s0/$s2 = entity ptrs
# offset 8 = entity+0x08 which the MEMORY file says is model_slot
# Then: sll $s0, $s0, 13 -> index * 8192
# 0x800F0000 + index * 8192 + 0x0126 -> lhu at offset 0x126
# This is the entity LARGE STRUCT indexed by entity_index
# So entity+0x08 is an INDEX, not a direct pointer field

# That means entity+0x38, +0x2A are fields in the SMALL entity
# struct that the action struct points to... OR they could be
# fields indexed differently. Let me re-examine.

# Looking at handler [10] more carefully:
# After 0x80023698 returns, sp[0x18] and sp[0x1C] are filled
# Then: $v1 = sp[0x18]  (some ptr)
#        lhu $v0, 56($v1)  -> field at ptr+0x38
# This could be the entity ptr, and +0x38 is a LOW field in the
# large entity struct (the 8KB one at 0x800E_xxxx)

# Let's check: entity struct starts at base + index*0x2000
# +0x38 would be in the header area. Common RPG usage:
# low offsets = basic identity, high offsets = combat stats

print("\n  Entity field cross-reference:")
print("  +0x08 = entity_index (used to compute large struct offset)")
print("  +0x2A = caster stat used in spell damage (divided by 3)")
print("  +0x38 = caster stat used in spell 'power level' (divided by 8 + 40)")
print("  +0x86 = target 'resistance/defense threshold'")
print("  +0xE4 = target 'damage received' output")
print("  +0x126/+0x14C/+0x14E = large struct stats (handlers [0],[1])")


# ============================================================
# SECTION 8: Complete mapping of all 55 handler patterns
# ============================================================

print("\n" + "=" * 70)
print("SECTION 8: Handler classification - which use spell entry +0x18?")
print("=" * 70)

handler_table_foff = ram_to_file(0x8003C1B0)
handler_addrs = []
for i in range(55):
    w = read_word(handler_table_foff + i * 4)
    handler_addrs.append(w)

for i, h_addr in enumerate(handler_addrs):
    if h_addr < 0x80010000 or h_addr > 0x80050000:
        continue

    # Scan first 60 instructions for lhu with offset 0x18
    has_0x18 = False
    has_mult = False
    has_div3 = False
    calls = []
    store_offsets = []
    target_type = None

    for j in range(60):
        addr = h_addr + j * 4
        foff = ram_to_file(addr)
        w = read_word(foff)
        if w is None:
            break
        op = (w >> 26) & 0x3F
        funct = w & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        imms = sign_extend_16(imm)

        # Check for lhu offset 0x18 (not from $sp)
        if op in (0x25, 0x21) and imms == 0x18 and rs != 29:
            has_0x18 = True

        # Check for lhu offset 0x18 from $a1
        if op == 0x25 and imms == 0x18 and rs == 5:
            has_0x18 = True

        # Check for mult/div
        if op == 0 and funct in (0x18, 0x19):
            has_mult = True
        if op == 0 and funct in (0x1A, 0x1B):
            has_div3 = True

        # Check for 0x2AAAAAAB (divide by 3 magic number)
        if op == 0x0D and imm == 0xAAAB:
            has_div3 = True

        # JAL calls
        if op == 0x03:
            target = ((addr & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
            if target not in calls:
                calls.append(target)

        # Store offsets to non-stack (sh)
        if op == 0x29 and rs != 29:
            store_offsets.append(imms)

        # Target type (ori $v0, $zero, N early in function)
        if op == 0x0D and rs == 0 and rt == 2 and j < 8 and target_type is None:
            target_type = imm

        # Stop at jr $ra
        if op == 0 and funct == 0x08 and rs == 31:
            break

    flags = []
    if has_0x18: flags.append("SPELL_DMG")
    if has_mult: flags.append("mult")
    if has_div3: flags.append("div/3")

    print("  [%2d] 0x%08X ttype=%s %s stores=%s calls=%s" % (
        i, h_addr,
        str(target_type) if target_type is not None else "?",
        " ".join(flags),
        [("0x%X" % (s & 0xFFFF)) for s in store_offsets[:6]],
        ["0x%08X" % c for c in calls[:4]]
    ))


print("\n" + "=" * 70)
print("ANALYSIS V3 COMPLETE")
print("=" * 70)
