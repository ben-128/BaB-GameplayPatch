#!/usr/bin/env python3
"""
v18: Check what's ACTUALLY in RAM at runtime via savestate.

The fundamental question: are our patches present in RAM, or does the game
overwrite them? If the savestate shows original (unpatched) code at 0x80075060,
it means the game loads STUB code from somewhere OTHER than our patched BLAZE.ALL.

Also: find the chest entity in RAM and trace what code acts on it.
"""

import struct
import gzip
from pathlib import Path


def disasm(word):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
            '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
            '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
            '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
    if word == 0: return "nop"
    if word == 0x03E00008: return "jr $ra"
    if op == 0x23: return f"lw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x09: return f"addiu {regs[rt]}, {regs[rs]}, {simm}"
    if op == 0x0F: return f"lui {regs[rt]}, 0x{imm:04X}"
    if op == 0x0D: return f"ori {regs[rt]}, {regs[rs]}, 0x{imm:04X}"
    if op == 0x03: return f"jal 0x{(word & 0x03FFFFFF) << 2:08X}"
    if op == 0x04: return f"beq {regs[rs]}, {regs[rt]}, {simm}"
    if op == 0x05: return f"bne {regs[rs]}, {regs[rt]}, {simm}"
    if op == 0x25: return f"lhu {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x29: return f"sh {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x2B: return f"sw {regs[rt]}, 0x{imm:04X}({regs[rs]})"
    if op == 0x0C: return f"andi {regs[rt]}, {regs[rs]}, 0x{imm:04X}"
    if op == 0x00:
        func = word & 0x3F
        if func == 0x21: return f"addu {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x24: return f"and {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x25: return f"or {regs[rd]}, {regs[rs]}, {regs[rt]}"
        if func == 0x08: return f"jr {regs[rs]}"
    return f"0x{word:08X}"


def main():
    script_dir = Path(__file__).parent
    # Use new savestate from patched game
    savestate_path = Path(r'C:\Perso\BabLangue\other\ePSXe2018\sstates') / 'SLES_008.45.000'

    if not savestate_path.exists():
        print(f"[ERROR] Savestate not found: {savestate_path}")
        return

    # Decompress savestate
    with open(savestate_path, 'rb') as f:
        compressed = f.read()

    try:
        decompressed = gzip.decompress(compressed)
    except Exception:
        decompressed = compressed

    RAM_OFFSET = 0x1BA
    RAM_BASE = 0x80000000
    RAM_SIZE = 2 * 1024 * 1024

    if len(decompressed) < RAM_OFFSET + RAM_SIZE:
        print(f"WARNING: Decompressed size ({len(decompressed):,}) < expected")
        RAM_OFFSET = 0

    def read_word(addr):
        off = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= off + 3 < len(decompressed):
            return struct.unpack_from('<I', decompressed, off)[0]
        return 0

    def read_halfword(addr):
        off = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= off + 1 < len(decompressed):
            return struct.unpack_from('<H', decompressed, off)[0]
        return 0

    def read_byte(addr):
        off = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= off < len(decompressed):
            return decompressed[off]
        return 0

    print("=" * 80)
    print("  v18: Check if patches are in RAM (from savestate)")
    print("=" * 80)

    # =========================================================================
    # CHECK 1: Is check_kill function patched in RAM?
    # =========================================================================
    print("\n  --- CHECK 1: Function check_kill at RAM 0x80075060 ---")

    func_addr = 0x80075060
    w1 = read_word(func_addr)
    w2 = read_word(func_addr + 4)

    print(f"  RAM 0x{func_addr:08X}: 0x{w1:08X} ({disasm(w1)})")
    print(f"  RAM 0x{func_addr + 4:08X}: 0x{w2:08X} ({disasm(w2)})")

    if w1 == 0x03E00008 and w2 == 0x00001021:
        print("  -> PATCHED (v16/v17 Layer 1)")
    elif w1 == 0x8C840074:
        print("  -> NOT PATCHED (original code!)")
        print("  *** This means the game loads STUB from UNPATCHED source! ***")
    else:
        print(f"  -> UNKNOWN state")

    # Show more instructions
    print(f"\n  Full function disassembly:")
    for k in range(20):
        a = func_addr + k * 4
        w = read_word(a)
        print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}")

    # =========================================================================
    # CHECK 2: Are JAL callers patched in RAM?
    # =========================================================================
    print("\n  --- CHECK 2: JAL caller sites in RAM ---")

    # STUB callers (RAM addresses)
    stub_callers_ram = [
        0x80079E54,  # BLAZE 0x009406FC
        0x8007C5B8,  # BLAZE 0x00942E60
        0x8007CEE0,  # BLAZE 0x00943788
        0x8007D414,  # BLAZE 0x00943CBC
        0x8007DBF8,  # BLAZE 0x009444A0
        0x8007E584,  # BLAZE 0x00944E2C
        0x8007EF50,  # BLAZE 0x009457F8
        0x8007F90C,  # BLAZE 0x009461B4
    ]

    for ram in stub_callers_ram:
        w = read_word(ram)
        status = ""
        if w == 0x0C01D418:
            status = "NOT PATCHED (original jal)"
        elif w == 0x24020000:
            status = "PATCHED (addiu $v0,$zero,0)"
        else:
            status = f"UNKNOWN"
        print(f"  RAM 0x{ram:08X}: 0x{w:08X} -> {status}")

    # MAIN callers (Cavern F1 - might be different zone in savestate)
    print("\n  MAIN callers (Cavern F1 specific):")
    main_callers_ram = [
        0x800805F4,  # BLAZE 0x00946E9C
        0x8008224C,  # BLAZE 0x00948AF4
        0x800861D0,  # BLAZE 0x0094CA78
        0x80086AA0,  # BLAZE 0x0094D348
        0x80087818,  # BLAZE 0x0094E0C0 (chest_update caller)
        0x80087BCC,  # BLAZE 0x0094E474
        0x800888D4,  # BLAZE 0x0094F17C
        0x80088B4C,  # BLAZE 0x0094F3F4
        0x80088DC4,  # BLAZE 0x0094F66C
    ]

    for ram in main_callers_ram:
        w = read_word(ram)
        status = ""
        if w == 0x0C01D418:
            status = "NOT PATCHED (original jal)"
        elif w == 0x24020000:
            status = "PATCHED (addiu $v0,$zero,0)"
        else:
            status = f"DIFFERENT ZONE CODE"
        print(f"  RAM 0x{ram:08X}: 0x{w:08X} -> {status}")

    # =========================================================================
    # CHECK 3: What zone is loaded? Check chest_update handler address
    # =========================================================================
    print("\n  --- CHECK 3: Which zone is loaded? ---")

    # Entity handler table at 0x8005A800 (if it exists)
    # Handler index 41 = chest handler
    handler_table = 0x8005A800
    # Each entry is a function pointer (4 bytes)
    handler_41 = read_word(handler_table + 41 * 4)
    print(f"  Handler table[41] (chest): 0x{handler_41:08X}")
    if handler_41 == 0x80087624:
        print("  -> Cavern F1 (expected)")
    elif handler_41 != 0:
        print(f"  -> Different zone (handler at 0x{handler_41:08X})")
    else:
        print("  -> Not loaded or wrong table address")

    # =========================================================================
    # CHECK 4: Find chest entities in RAM
    # =========================================================================
    print("\n  --- CHECK 4: Search for chest entities ---")

    # Search for entities with parent pointer (non-zero at +0x74)
    # that look like chest entities
    chest_entities = []
    for addr in range(0x800A0000, 0x800F0000, 4):
        flags = read_word(addr)
        if flags == 0:
            continue
        # Check for bit 31 set (alive) and bit 23 set (overlay-managed)
        if not (flags & 0x80000000):
            continue
        if not (flags & 0x00800000):
            continue

        # Check entity+0x74 for parent pointer
        parent = read_word(addr + 0x74)
        if parent == 0 or parent < 0x80000000 or parent > 0x80200000:
            continue

        # Check timer at +0x14
        timer = read_halfword(addr + 0x14)

        # Check parent flags
        parent_flags = read_word(parent)

        chest_entities.append((addr, flags, parent, parent_flags, timer))

    print(f"  Found {len(chest_entities)} entities with valid parent pointer")
    for addr, flags, parent, pf, timer in chest_entities[:10]:
        dead = "DEAD" if (flags & 0x02000000) else "ALIVE"
        parent_alive = "alive" if (pf & 0x80000000) else "dead/free"
        print(f"  0x{addr:08X}: flags=0x{flags:08X} ({dead}) "
              f"parent=0x{parent:08X} (pflags=0x{pf:08X} {parent_alive}) "
              f"timer={timer}")

    # =========================================================================
    # CHECK 5: Disassemble chest_update around the jal check_kill call
    # =========================================================================
    print("\n  --- CHECK 5: Disassemble chest_update around check_kill call ---")
    chest_update_addr = 0x80087818  # The jal check_kill location
    print(f"  Around RAM 0x{chest_update_addr:08X} (jal check_kill site):")
    for k in range(-8, 20):
        a = chest_update_addr + k * 4
        w = read_word(a)
        marker = " <<<" if k == 0 else ""
        print(f"    0x{a:08X}: 0x{w:08X}  {disasm(w)}{marker}")

    # =========================================================================
    # CHECK 6: Search for ALL dead flag setters near chest code
    # =========================================================================
    print("\n  --- CHECK 6: ALL 'lui $reg, 0x0200' in chest_update region ---")
    # chest_update likely spans RAM 0x80087624 to about 0x80088F00
    for addr in range(0x80087624, 0x80089000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x0F and imm == 0x0200:
            rt = (w >> 16) & 0x1F
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
            print(f"  0x{addr:08X}: lui {regs[rt]}, 0x0200")
            # Show surrounding context
            for k in range(-3, 8):
                a = addr + k * 4
                w2 = read_word(a)
                m = " <<<" if k == 0 else ""
                print(f"    0x{a:08X}: 0x{w2:08X}  {disasm(w2)}{m}")
            print()

    # =========================================================================
    # CHECK 7: Search for sw $zero, 0x0000 (kill by zeroing) near chest code
    # =========================================================================
    print("\n  --- CHECK 7: 'sw $zero, 0x0000($reg)' in chest region ---")
    for addr in range(0x80087624, 0x80089000, 4):
        w = read_word(addr)
        # sw $zero = opcode 0x2B, rt=0, imm=0x0000
        if w == 0xAC000000 or (w & 0xFFE0FFFF) == 0xAC000000:
            rs = (w >> 21) & 0x1F
            regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                    '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                    '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                    '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
            print(f"  0x{addr:08X}: sw $zero, 0x0000({regs[rs]})")

    # =========================================================================
    # CHECK 8: Search for AND 0x7FFFFFFF (kill by clearing bit 31)
    # =========================================================================
    print("\n  --- CHECK 8: 'lui $reg, 0x7FFF' + 'ori 0xFFFF' pattern ---")
    for addr in range(0x80087624, 0x80089000, 4):
        w = read_word(addr)
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x0F and imm == 0x7FFF:
            print(f"  0x{addr:08X}: lui -> 0x7FFF (clear bit 31 mask?)")
            for k in range(-2, 6):
                a = addr + k * 4
                w2 = read_word(a)
                print(f"    0x{a:08X}: 0x{w2:08X}  {disasm(w2)}")
            print()


if __name__ == '__main__':
    main()
