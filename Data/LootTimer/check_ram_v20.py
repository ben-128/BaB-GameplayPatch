#!/usr/bin/env python3
"""
v20: Find the EXTERNAL kill mechanism.

v18-v19 proved ALL patches are in RAM and both kill paths inside chest_update
are disabled. But chests still die. The dead flag (0x02000000) must be set by
code OUTSIDE of chest_update.

Hypotheses:
1. EXE entity manager cascades death from parent to children
2. Function 0x80028D4C (called in chest init) registers a parent-child link
3. When parent monster dies, entity manager sets dead flag on all children

This script:
1. Dumps function 0x80028D4C (chest init check)
2. Searches EXE for patterns that iterate entities and set dead flag
3. Searches for "set 0x02000000 on child" patterns
4. Looks at the entity manager's main loop
"""

import struct
import gzip
from pathlib import Path


def disasm(word):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    sa = (word >> 6) & 0x1F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    func = word & 0x3F
    regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
            '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
            '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
            '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
    if word == 0: return "nop"
    if word == 0x03E00008: return "jr $ra"
    if op == 0x00:
        if func == 0x08: return f"jr {regs[rs]}"
        if func == 0x09: return f"jalr {regs[rd]}, {regs[rs]}"
        if func == 0x21: return f"addu {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x23: return f"subu {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x24: return f"and {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x25: return f"or {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x2A: return f"slt {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x2B: return f"sltu {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x00: return f"sll {regs[rd]}, {regs[rt]}, {sa}"
        if func == 0x02: return f"srl {regs[rd]}, {regs[rt]}, {sa}"
        if func == 0x03: return f"sra {regs[rd]}, {regs[rt]}, {sa}"
        if func == 0x18: return f"mult {regs[rs]}, {regs[rt]}"
        if func == 0x19: return f"multu {regs[rs]}, {regs[rt]}"
        if func == 0x10: return f"mfhi {regs[rd]}"
        if func == 0x12: return f"mflo {regs[rd]}"
        return f"special.{func:02X} {regs[rd]},{regs[rs]},{regs[rt]}"
    if op == 0x02: return f"j 0x{(word & 0x03FFFFFF) << 2:08X}"
    if op == 0x03: return f"jal 0x{(word & 0x03FFFFFF) << 2:08X}"
    if op == 0x04: return f"beq {regs[rs]}, {regs[rt]}, {simm}"
    if op == 0x05: return f"bne {regs[rs]}, {regs[rt]}, {simm}"
    if op == 0x06: return f"blez {regs[rs]}, {simm}"
    if op == 0x07: return f"bgtz {regs[rs]}, {simm}"
    if op == 0x08: return f"addi {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x09: return f"addiu {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x0A: return f"slti {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x0B: return f"sltiu {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x0C: return f"andi {regs[rt]}, {regs[rs]}, 0x{imm:04X}"
    if op == 0x0D: return f"ori {regs[rt]}, {regs[rs]}, 0x{imm:04X}"
    if op == 0x0F: return f"lui {regs[rt]}, 0x{imm:04X}"
    if op == 0x01:
        if rt == 0: return f"bltz {regs[rs]}, {simm}"
        if rt == 1: return f"bgez {regs[rs]}, {simm}"
    if op == 0x20: return f"lb {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x21: return f"lh {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x23: return f"lw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x24: return f"lbu {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x25: return f"lhu {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x28: return f"sb {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x29: return f"sh {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x2B: return f"sw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    return f"0x{word:08X}"


def main():
    savestate_path = Path(r'C:\Perso\BabLangue\other\ePSXe2018\sstates') / 'SLES_008.45.000'
    if not savestate_path.exists():
        print(f"[ERROR] Savestate not found: {savestate_path}")
        return

    with open(savestate_path, 'rb') as f:
        compressed = f.read()
    try:
        decompressed = gzip.decompress(compressed)
    except Exception:
        decompressed = compressed

    RAM_OFFSET = 0x1BA
    RAM_BASE = 0x80000000

    def read_word(addr):
        off = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= off + 3 < len(decompressed):
            return struct.unpack_from('<I', decompressed, off)[0]
        return 0

    print("=" * 80)
    print("  v20: Find external kill mechanism")
    print("=" * 80)

    # =========================================================================
    # PART 1: Dump function 0x80028D4C (called in chest init state 0)
    # This function decides if the chest should be destroyed at creation
    # =========================================================================
    print("\n  --- PART 1: Function at 0x80028D4C ---")
    print("  Called with ($a0=parent, $a1=parent, $a2=0)")
    print("  Returns non-zero -> chest destroyed immediately")
    print()

    for k in range(60):
        a = 0x80028D4C + k * 4
        w = read_word(a)
        d = disasm(w)
        note = ""
        if a == 0x80028D4C: note = " <- ENTRY"
        if w == 0x03E00008:
            note = " <- RETURN"
        print(f"    0x{a:08X}: 0x{w:08X}  {d}{note}")
        if w == 0x03E00008:
            # Print delay slot
            a2 = a + 4
            w2 = read_word(a2)
            print(f"    0x{a2:08X}: 0x{w2:08X}  {disasm(w2)}")
            break

    # =========================================================================
    # PART 2: Search EXE for "lui $reg, 0x0200" + "or" + "sw" pattern
    # These are places that SET the dead flag (0x02000000)
    # Focus on EXE code (0x80010000-0x80050000) since overlay is already patched
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 2: ALL places in EXE that SET dead flag (lui 0x0200 + or + sw)")
    print("  Range: 0x80010000-0x80050000 (EXE code)")
    print("=" * 80)

    dead_flag_setters = []
    for addr in range(0x80010000, 0x80050000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x0F and imm == 0x0200:  # lui $reg, 0x0200
            # Check within next 8 instructions for or + sw pattern
            for i in range(1, 8):
                w2 = read_word(addr + i * 4)
                op2 = (w2 >> 26) & 0x3F
                func2 = w2 & 0x3F
                if op2 == 0x00 and func2 == 0x25:  # or
                    # Check next 1-2 instructions for sw
                    for j in range(1, 3):
                        w3 = read_word(addr + (i + j) * 4)
                        op3 = (w3 >> 26) & 0x3F
                        imm3 = w3 & 0xFFFF
                        if op3 == 0x2B and imm3 == 0x0000:  # sw $reg, 0x0000($base)
                            dead_flag_setters.append(addr)
                            break
                    break

    print(f"  Found {len(dead_flag_setters)} dead flag set patterns in EXE")
    for addr in dead_flag_setters:
        print(f"\n  Dead flag setter at 0x{addr:08X}:")
        for k in range(-4, 12):
            a = addr + k * 4
            w = read_word(a)
            m = " <<<" if k == 0 else ""
            print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}{m}")

    # =========================================================================
    # PART 3: Search EXE for "sw $zero, 0x0000($reg)" pattern near entity access
    # This is entity destruction (zeroing flags)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 3: 'sw $zero, 0x0000($reg)' in EXE code")
    print("  These destroy entities by zeroing their flags")
    print("=" * 80)

    entity_zeros = []
    for addr in range(0x80010000, 0x80050000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        rt = (w >> 16) & 0x1F
        rs = (w >> 21) & 0x1F
        imm = w & 0xFFFF
        # sw $zero, 0x0000($reg) where reg is NOT $sp/$fp/$gp
        if op == 0x2B and rt == 0 and imm == 0x0000 and rs not in [0, 29, 28, 30]:
            # Check surrounding context for entity-related access
            # Look for lw $reg, 0x0074 (parent) or lui 0x0200 (dead flag)
            has_entity_context = False
            for k in range(-8, 8):
                if k == 0:
                    continue
                wc = read_word(addr + k * 4)
                opc = (wc >> 26) & 0x3F
                immc = wc & 0xFFFF
                if opc == 0x23 and immc == 0x0074:  # lw $reg, 0x0074
                    has_entity_context = True
                if opc == 0x0F and immc == 0x0200:  # lui 0x0200
                    has_entity_context = True
                if opc == 0x0F and immc == 0x0080:  # lui 0x0080 (alive flag)
                    has_entity_context = True
            if has_entity_context:
                entity_zeros.append(addr)

    print(f"  Found {len(entity_zeros)} entity zeroing patterns in EXE")
    for addr in entity_zeros[:10]:
        print(f"\n  Entity zero at 0x{addr:08X}:")
        for k in range(-6, 6):
            a = addr + k * 4
            w = read_word(a)
            m = " <<<" if k == 0 else ""
            print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}{m}")

    # =========================================================================
    # PART 4: Search EXE for lw $reg, 0x0074($reg) (parent pointer access)
    # These are functions that access parent entities
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 4: EXE functions that access entity+0x0074 (parent ptr)")
    print("=" * 80)

    parent_access = []
    for addr in range(0x80010000, 0x80050000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x23 and imm == 0x0074:  # lw $reg, 0x0074($base)
            parent_access.append(addr)

    print(f"  Found {len(parent_access)} lw 0x0074 in EXE")
    for addr in parent_access:
        rs = (read_word(addr) >> 21) & 0x1F
        rt = (read_word(addr) >> 16) & 0x1F
        regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
        print(f"  0x{addr:08X}: lw {regs[rt]}, 0x0074({regs[rs]})")

    # =========================================================================
    # PART 5: Dump check_kill function more carefully and its CALLERS in EXE
    # check_kill is at 0x80075060 - but is it also called from EXE?
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 5: JAL 0x80075060 (check_kill) in EXE range")
    print("  If EXE calls check_kill, those callers are NOT patched!")
    print("=" * 80)

    jal_check_kill = 0x0C01D418  # jal 0x80075060
    exe_callers = []
    for addr in range(0x80010000, 0x80050000, 4):
        w = read_word(addr)
        if w == jal_check_kill:
            exe_callers.append(addr)

    print(f"  Found {len(exe_callers)} jal check_kill in EXE")
    for addr in exe_callers:
        print(f"\n  EXE caller at 0x{addr:08X}:")
        for k in range(-6, 10):
            a = addr + k * 4
            w = read_word(a)
            m = " <<<" if k == 0 else ""
            print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}{m}")

    # =========================================================================
    # PART 6: Look at the entity update loop in EXE
    # Search for patterns that iterate entity arrays and call handlers
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 6: Entity handler dispatch (jalr patterns in EXE)")
    print("  How does the game call entity update handlers?")
    print("=" * 80)

    # Search for jalr (indirect call) patterns in the 0x80010000-0x80030000 range
    jalr_count = 0
    for addr in range(0x80010000, 0x80030000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        func = w & 0x3F
        if op == 0x00 and func == 0x09:  # jalr
            rs = (w >> 21) & 0x1F
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
            # Check if nearby code accesses entity+0x0074 or entity flags
            has_entity = False
            for k in range(-20, 20):
                wc = read_word(addr + k * 4)
                opc = (wc >> 26) & 0x3F
                immc = wc & 0xFFFF
                if opc == 0x23 and immc == 0x0074:
                    has_entity = True
                if opc == 0x0F and immc == 0x0200:
                    has_entity = True
            if has_entity:
                jalr_count += 1
                if jalr_count <= 5:
                    print(f"\n  Entity-related jalr at 0x{addr:08X}: jalr {regs[rs]}")
                    for k in range(-8, 8):
                        a = addr + k * 4
                        w2 = read_word(a)
                        m = " <<<" if k == 0 else ""
                        print(f"    0x{a:08X}: 0x{w2:08X}  {disasm(w2)}{m}")

    print(f"\n  Total entity-related jalr in EXE: {jalr_count}")

    # =========================================================================
    # PART 7: The STUB entity update functions near our patched callers
    # Do these functions have ADDITIONAL kill paths besides check_kill?
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 7: STUB function around 0x80079E54 (first patched caller)")
    print("  Is there another kill path besides check_kill?")
    print("=" * 80)

    # Find function start for 0x80079E54
    func_start = 0x80079E54
    for a in range(0x80079E54, 0x80079000, -4):
        w = read_word(a)
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        simm = (w & 0xFFFF)
        if simm >= 0x8000:
            simm -= 0x10000
        if op == 0x09 and rs == 29 and rt == 29 and simm < 0:
            func_start = a
            break

    print(f"  Function starts at 0x{func_start:08X}")
    for k in range(100):
        a = func_start + k * 4
        w = read_word(a)
        d = disasm(w)
        note = ""
        if a == 0x80079E54: note = " <<< PATCHED jal site"
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        rt = (w >> 16) & 0x1F
        if op == 0x2B and imm == 0x0000 and rt == 0:
            note = " *** ZERO ENTITY ***"
        if op == 0x0F and imm == 0x0200:
            note = " [dead flag mask]"
        print(f"    0x{a:08X}: 0x{w:08X}  {d}{note}")
        if w == 0x03E00008:
            a2 = a + 4
            w2 = read_word(a2)
            print(f"    0x{a2:08X}: 0x{w2:08X}  {disasm(w2)}")
            break


if __name__ == '__main__':
    main()
