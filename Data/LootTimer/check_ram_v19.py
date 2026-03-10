#!/usr/bin/env python3
"""
v19: Deep investigation of the DIRECT parent flag check at 0x80087C74.

v18 confirmed ALL v17 patches are in RAM. But chests still die.
CHECK 6 found a code path at 0x80087C74 that loads PARENT entity flags
via $s1 (entity+0x74 loaded at function entry 0x8008763C) and checks
the 0x02000000 dead flag DIRECTLY - bypassing check_kill entirely.

This script:
1. Dumps the full chest_update function from entry to return
2. Identifies ALL direct parent flag checks (not through check_kill)
3. Traces what happens when parent dead flag is detected
4. Looks for alternative kill mechanisms (sw to entity+0x0000, etc.)
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
    print("  v19: Deep investigation of direct parent flag checks")
    print("=" * 80)

    # =========================================================================
    # PART 1: Full dump of the critical function around 0x80087C74
    # This is inside a sub-function that checks parent flags DIRECTLY
    # =========================================================================
    print("\n  --- PART 1: Full code around 0x80087C74 (parent dead flag check) ---")
    print("  $s1 = entity+0x74 (parent entity pointer)")
    print()

    # Find the function start by searching backwards for stack frame setup
    start = 0x80087C00
    for a in range(0x80087C74, 0x80087A00, -4):
        w = read_word(a)
        # Look for addiu $sp, $sp, -N (stack frame setup)
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        simm = (w & 0xFFFF)
        if simm >= 0x8000:
            simm -= 0x10000
        if op == 0x09 and rs == 29 and rt == 29 and simm < 0:  # addiu $sp, $sp, -N
            start = a
            break

    print(f"  Function likely starts at 0x{start:08X}")
    print()

    for k in range(80):
        a = start + k * 4
        w = read_word(a)
        d = disasm(w)

        # Annotate interesting instructions
        note = ""
        if a == 0x80087C74:
            note = " <<< PARENT FLAGS LOAD"
        elif a == 0x80087C78:
            note = " <<< DEAD FLAG MASK"
        elif a == 0x80087C80:
            note = " <<< BRANCH IF PARENT NOT DEAD"

        # Detect sw to entity base (killing entity)
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        rt = (w >> 16) & 0x1F
        if op == 0x2B and imm == 0x0000 and rt == 0:  # sw $zero, 0x0000($base)
            note = " <<< ZERO ENTITY FLAGS (KILL!)"
        if op == 0x2B and imm == 0x0000 and rt != 0:
            rs = (w >> 21) & 0x1F
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
            note = f" <<< sw to {regs[rs]}+0x0000"
        # Detect or with 0x0200 mask (set dead flag)
        if op == 0x00 and (w & 0x3F) == 0x25:  # or
            note2 = " (or)"
            if not note:
                note = note2

        print(f"    0x{a:08X}: 0x{w:08X}  {d}{note}")

        # Stop at function return
        if w == 0x03E00008:  # jr $ra
            # Print delay slot too
            a2 = a + 4
            w2 = read_word(a2)
            print(f"    0x{a2:08X}: 0x{w2:08X}  {disasm(w2)}")
            break

    # =========================================================================
    # PART 2: Full chest_update function - trace ALL paths that modify entity+0x0000
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 2: ALL 'sw' to entity+0x0000 in chest_update region")
    print("  These are ALL possible paths that modify entity flags")
    print("=" * 80)

    for addr in range(0x80087624, 0x80089000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        rt = (w >> 16) & 0x1F
        rs = (w >> 21) & 0x1F
        imm = w & 0xFFFF

        # sw $ANY, 0x0000($s0) or sw $ANY, 0x0000($s1) -- entity flag stores
        if op == 0x2B and imm == 0x0000 and rs in [16, 17]:  # $s0=16, $s1=17
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

            what = ""
            if rt == 0:
                what = "ZERO (entity destruction!)"
            elif rt == 2:
                what = "modified flags"

            print(f"\n  0x{addr:08X}: sw {regs[rt]}, 0x0000({regs[rs]})  [{what}]")
            # Show context
            for k in range(-6, 4):
                a = addr + k * 4
                w2 = read_word(a)
                m = " <<<" if k == 0 else ""
                print(f"    0x{a:08X}: 0x{w2:08X}  {disasm(w2)}{m}")

    # =========================================================================
    # PART 3: Trace the SPECIFIC flow at 0x80087C80 (parent dead check)
    # What code executes when parent IS dead?
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 3: What happens when parent dead flag is detected at 0x80087C80?")
    print("  beq $v0, $zero, +15 means: if parent NOT dead, skip +15")
    print("  If parent IS dead, falls through...")
    print("=" * 80)

    # beq at 0x80087C80 branches +15 if parent NOT dead
    # Fall-through (parent IS dead) starts at 0x80087C84
    # Let's trace what happens
    print("\n  Fall-through path when parent IS dead:")
    for k in range(40):
        a = 0x80087C84 + k * 4
        w = read_word(a)
        d = disasm(w)
        note = ""
        op = (w >> 26) & 0x3F
        rt = (w >> 16) & 0x1F
        rs = (w >> 21) & 0x1F
        imm = w & 0xFFFF

        if op == 0x2B and imm == 0x0000:
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
            if rt == 0:
                note = " !!! KILL (zero entity flags)"
            else:
                note = f" !!! STORE to {regs[rs]}+0x0000"

        # Check for or with 0x0200xxxx (dead flag set)
        if op == 0x00 and (w & 0x3F) == 0x25:
            rd = (w >> 11) & 0x1F
            note = " (or - possible dead flag set)"

        print(f"    0x{a:08X}: 0x{w:08X}  {d}{note}")

    # =========================================================================
    # PART 4: Search for ALL lw from entity+0x74 (parent load) in chest region
    # This finds every place that accesses the parent pointer
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 4: ALL loads from entity+0x0074 (parent) in chest region")
    print("  Any of these could lead to direct parent flag checks")
    print("=" * 80)

    for addr in range(0x80087624, 0x80089000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x23 and imm == 0x0074:  # lw $reg, 0x0074($base)
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
            print(f"\n  0x{addr:08X}: lw {regs[rt]}, 0x0074({regs[rs]})")
            for k in range(-2, 12):
                a = addr + k * 4
                w2 = read_word(a)
                m = " <<<" if k == 0 else ""
                print(f"    0x{a:08X}: 0x{w2:08X}  {disasm(w2)}{m}")

    # =========================================================================
    # PART 5: Check the main chest_update entry and all state transitions
    # The function at 0x80087624 is chest_update handler
    # =========================================================================
    print("\n" + "=" * 80)
    print("  PART 5: Full chest_update from 0x80087624 (first 200 instructions)")
    print("=" * 80)

    for k in range(200):
        a = 0x80087624 + k * 4
        w = read_word(a)
        d = disasm(w)

        note = ""
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF

        # Mark key locations
        if a == 0x8008763C: note = " [load parent ptr -> $s1]"
        if a == 0x80087640: note = " [check own dead flag]"
        if a == 0x80087650: note = " [check entity+0x10 state]"
        if a == 0x800877F8: note = " [store timer]"
        if a == 0x80087800: note = " [timer==0 check]"
        if a == 0x80087818: note = " [PATCHED: was jal check_kill]"
        if a == 0x80087C74: note = " [PARENT flags load]"
        if a == 0x80087C78: note = " [PARENT dead mask]"
        if a == 0x80087C80: note = " [BRANCH if parent NOT dead]"

        # Mark sw to +0x0000
        if op == 0x2B and imm == 0x0000:
            rt_i = (w >> 16) & 0x1F
            if rt_i == 0:
                note = " *** ZERO ENTITY ***"

        # Mark or with dead flag potential
        if op == 0x0F and imm == 0x0200:
            note = " [dead flag 0x0200xxxx mask]"

        print(f"    0x{a:08X}: 0x{w:08X}  {d}{note}")


if __name__ == '__main__':
    main()
