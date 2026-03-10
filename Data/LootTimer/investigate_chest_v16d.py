#!/usr/bin/env python3
"""
v16d: Deep investigation of chest timer mechanisms.

DISCOVERY from v16c:
1. Normal table at 0x800B1E80 + type*288 + 0xB2 has ALL ZEROS for monster types
2. Alternative table at 0x800F0100 + type*8192 + 0xB2 used when parent flag 0x00800000 is set
3. SECOND kill mechanism: jal 0x80075060 after timer check

This script investigates:
- Alternative table values in savestate RAM
- The function at 0x80075060 (might be the REAL despawn mechanism)
- Entity+0x14 values for actual entities in the savestate
- The entity that looks like an active chest
"""

import struct
import gzip
from pathlib import Path

REG = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
       '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
       '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
       '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def disasm(word, addr=0):
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    target = (word & 0x03FFFFFF) << 2

    if word == 0: return "nop"
    if opcode == 0x00:
        if funct == 0x00: return f"sll {REG[rd]}, {REG[rt]}, {shamt}"
        if funct == 0x02: return f"srl {REG[rd]}, {REG[rt]}, {shamt}"
        if funct == 0x03: return f"sra {REG[rd]}, {REG[rt]}, {shamt}"
        if funct == 0x08: return f"jr {REG[rs]}"
        if funct == 0x09: return f"jalr {REG[rd]}, {REG[rs]}"
        if funct == 0x10: return f"mfhi {REG[rd]}"
        if funct == 0x12: return f"mflo {REG[rd]}"
        if funct == 0x18: return f"mult {REG[rs]}, {REG[rt]}"
        if funct == 0x19: return f"multu {REG[rs]}, {REG[rt]}"
        if funct == 0x1A: return f"div {REG[rs]}, {REG[rt]}"
        if funct == 0x1B: return f"divu {REG[rs]}, {REG[rt]}"
        if funct == 0x21: return f"addu {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x23: return f"subu {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x24: return f"and {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x25: return f"or {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x2A: return f"slt {REG[rd]}, {REG[rs]}, {REG[rt]}"
        if funct == 0x2B: return f"sltu {REG[rd]}, {REG[rs]}, {REG[rt]}"
        return f"R:0x{word:08X}"
    if opcode == 0x02: return f"j 0x{(addr & 0xF0000000) | target:08X}"
    if opcode == 0x03: return f"jal 0x{(addr & 0xF0000000) | target:08X}"
    if opcode == 0x04: return f"beq {REG[rs]}, {REG[rt]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x05: return f"bne {REG[rs]}, {REG[rt]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x06: return f"blez {REG[rs]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x07: return f"bgtz {REG[rs]}, 0x{(addr + 4 + simm*4) & 0xFFFFFFFF:08X}"
    if opcode == 0x09: return f"addiu {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x0A: return f"slti {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x0B: return f"sltiu {REG[rt]}, {REG[rs]}, {simm}"
    if opcode == 0x0C: return f"andi {REG[rt]}, {REG[rs]}, 0x{imm:04X}"
    if opcode == 0x0D: return f"ori {REG[rt]}, {REG[rs]}, 0x{imm:04X}"
    if opcode == 0x0F: return f"lui {REG[rt]}, 0x{imm:04X}"
    if opcode == 0x20: return f"lb {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x21: return f"lh {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x23: return f"lw {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x24: return f"lbu {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x25: return f"lhu {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x28: return f"sb {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x29: return f"sh {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    if opcode == 0x2B: return f"sw {REG[rt]}, 0x{imm:04X}({REG[rs]})"
    return f"?:0x{word:08X}"


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    savestate_path = script_dir / 'coffre_avec_argent.gpz'
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    # Load savestate
    with open(savestate_path, 'rb') as f:
        compressed = f.read()
    ram_data = gzip.decompress(compressed)
    RAM_OFFSET = 0x1BA
    RAM_BASE = 0x80000000

    def read_ram(addr, size=4):
        off = (addr - RAM_BASE) + RAM_OFFSET
        if off < 0 or off + size > len(ram_data):
            return b'\x00' * size
        return ram_data[off:off+size]

    def r8(addr): return read_ram(addr, 1)[0]
    def r16(addr): return struct.unpack('<H', read_ram(addr, 2))[0]
    def r32(addr): return struct.unpack('<I', read_ram(addr, 4))[0]

    # Load BLAZE.ALL
    blaze = blaze_path.read_bytes()

    def blaze_to_ram(off):
        if off >= 0x009468A8: return (off - 0x009468A8) + 0x80080000
        if off >= 0x0091D80C: return (off - 0x0091D80C) + 0x80056F64
        return 0

    def ram_to_blaze(addr):
        if addr >= 0x80080000: return (addr - 0x80080000) + 0x009468A8
        if addr >= 0x80056F64: return (addr - 0x80056F64) + 0x0091D80C
        return 0

    print("=" * 80)
    print("  v16d: Deep chest timer investigation")
    print("=" * 80)

    # =========================================================================
    # PART 1: Read alternative table at 0x800F0100
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 1: Alternative table at 0x800F0100 (8192-byte records)")
    print(f"  Field at +0xB2 (same as normal table)")
    print(f"{'#'*80}")

    alt_table_base = 0x800F0100
    alt_record_size = 8192  # type << 13

    for type_idx in range(8):  # Check first 8 types
        rec_addr = alt_table_base + type_idx * alt_record_size
        timer_val = r16(rec_addr + 0xB2)
        # Also check nearby fields for context
        f00 = r32(rec_addr)
        f04 = r32(rec_addr + 4)
        f08 = r16(rec_addr + 8)

        time_sec = timer_val * 20 / 50 if timer_val > 0 else 0
        marker = ""
        if 18 <= time_sec <= 22:
            marker = " *** ~20s CHEST TIMER! ***"
        elif timer_val == 50:
            marker = " *** 50 decrements! ***"

        print(f"  Type {type_idx}: addr=0x{rec_addr:08X} timer=0x{timer_val:04X} ({timer_val}) = {time_sec:.1f}s"
              f"  [0x00]=0x{f00:08X} [0x04]=0x{f04:08X}{marker}")

        # Dump +0xB0-0xBF for context
        print(f"    +0xB0:", end="")
        for b in range(16):
            print(f" {r8(rec_addr + 0xB0 + b):02X}", end="")
        print()

    # =========================================================================
    # PART 2: Disassemble function 0x80075060 (second kill check)
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 2: Function 0x80075060 (second kill mechanism)")
    print(f"{'#'*80}")

    func_addr = 0x80075060
    blaze_off = ram_to_blaze(func_addr)
    print(f"  RAM: 0x{func_addr:08X}")
    print(f"  BLAZE: 0x{blaze_off:08X}")

    # Disassemble first 60 instructions
    for i in range(60):
        off = blaze_off + i * 4
        if off + 4 > len(blaze):
            break
        word = struct.unpack_from('<I', blaze, off)[0]
        ram = blaze_to_ram(off)
        d = disasm(word, ram)
        marker = ""
        if "jr $ra" in d:
            marker = "  <-- RETURN"
        elif "0x0014" in d:
            marker = "  <-- entity+0x14?"
        elif "0x0012" in d:
            marker = "  <-- entity+0x12?"
        elif "0x3E8" in d or "1000" in d:
            marker = "  <-- VALUE 1000!"
        print(f"  0x{off:08X}  0x{ram:08X}:  {d}{marker}")
        if "jr $ra" in d and i > 3:
            # Found return, print one more (delay slot)
            off2 = off + 4
            if off2 + 4 <= len(blaze):
                w2 = struct.unpack_from('<I', blaze, off2)[0]
                d2 = disasm(w2, blaze_to_ram(off2))
                print(f"  0x{off2:08X}  0x{blaze_to_ram(off2):08X}:  {d2}  (delay slot)")
            break

    # =========================================================================
    # PART 3: Check entity+0x12 store patterns more carefully
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 3: entity+0x12 in chest_update - what does it store?")
    print(f"{'#'*80}")

    # The chest_update stores two values to entity+0x12:
    # 1) ori $v1, $zero, 0x1000 → sh $v1, 0x0012 (in state < 8 path)
    # 2) ori $v0, $zero, 0x0C00 → sh $v0, 0x0012 (in state 4-7 path)
    # Let's check what entity+0x12 is in real entity structures
    print("  In chest_update code:")
    print("    State < 8 path: entity+0x12 = 0x1000 (4096)")
    print("    State 4-7 path: entity+0x12 = 0x0C00 (3072)")
    print("    Neither matches 0x3E8 (1000)!")

    # =========================================================================
    # PART 4: Search for chest entities in savestate more intelligently
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 4: Find chest entities in savestate RAM")
    print(f"  The savestate 'coffre_avec_argent' should have a visible chest")
    print(f"{'#'*80}")

    # Strategy: look for entities where:
    # - entity+0x74 is a valid pointer (to parent entity)
    # - entity+0x10 >= 16 (past init phase)
    # - entity+0x14 > 0 (timer active)
    # Entity pools are typically in 0x800B0000+ range

    candidates = []
    # Search in a wider range, stepping by likely entity sizes
    for scan_base in range(0x800B0000, 0x80200000, 4):
        # Quick check: does entity+0x74 look like a RAM pointer?
        ptr74 = r32(scan_base + 0x74)
        if not (0x800B0000 <= ptr74 < 0x80200000):
            continue

        # Check entity+0x10 >= 16
        state = r16(scan_base + 0x10)
        if state < 16 or state > 5000:
            continue

        # Check entity+0x14 (timer)
        timer = r16(scan_base + 0x14)
        if timer == 0 or timer > 1000:
            continue

        # Check entity+0x00 (flags) - should NOT have dead flag
        flags = r32(scan_base)
        if flags & 0x02000000:
            continue

        # This looks like a candidate!
        f12 = r16(scan_base + 0x12)
        candidates.append((scan_base, flags, state, f12, timer, ptr74))

    print(f"  Found {len(candidates)} candidate chest entities")
    for addr, flags, state, f12, timer, ptr74 in candidates[:30]:
        time_sec = timer * 20 / 50
        # Read parent type
        parent_type = r8(ptr74 + 0x08) if 0x800B0000 <= ptr74 < 0x80200000 else -1
        parent_flags = r32(ptr74) if 0x800B0000 <= ptr74 < 0x80200000 else 0
        has_alt_flag = "ALT" if parent_flags & 0x00800000 else "NRM"

        print(f"  0x{addr:08X}: flags=0x{flags:08X} state={state:4d} +0x12=0x{f12:04X} "
              f"timer={timer:4d}({time_sec:.1f}s) parent=0x{ptr74:08X} "
              f"ptype={parent_type} pflag={has_alt_flag}")

    # =========================================================================
    # PART 5: Search for entities with entity+0x12 = 0x1000 or 0x0C00
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 5: Entities with entity+0x12 = 0x1000 or 0x0C00")
    print(f"{'#'*80}")

    for scan_base in range(0x800B0000, 0x80200000, 4):
        f12 = r16(scan_base + 0x12)
        if f12 not in (0x1000, 0x0C00):
            continue

        state = r16(scan_base + 0x10)
        timer = r16(scan_base + 0x14)
        flags = r32(scan_base)

        if flags == 0:
            continue

        # Could be a chest entity
        ptr74 = r32(scan_base + 0x74)
        parent_valid = 0x800B0000 <= ptr74 < 0x80200000

        if state > 0 and state < 10000:
            print(f"  0x{scan_base:08X}: +0x12=0x{f12:04X} state={state:4d} "
                  f"timer={timer:4d} flags=0x{flags:08X} "
                  f"parent={'0x{:08X}'.format(ptr74) if parent_valid else 'invalid'}")

    # =========================================================================
    # PART 6: What if entity+0x14 is NOT the timer at all?
    # Let's check if 0x80075060 uses entity+0x12 or something else
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 6: What does entity+0x14 actually store?")
    print(f"  Code says: lhu from table+0xB2 → sh to entity+0x14")
    print(f"  But table+0xB2 = 0 for all monster types!")
    print(f"  So entity+0x14 = 0 at init, then decremented = 0xFFFF (wraps)")
    print(f"  Timer wraps = chest lasts ~7 hours, NOT 20 seconds")
    print(f"{'#'*80}")

    # If entity+0x14 wraps to 0xFFFF, the REAL despawn must be from
    # function 0x80075060. Let's look at it more carefully.

    print(f"\n  Checking: does 0x80075060 reference any timer constant?")
    func_blaze = ram_to_blaze(0x80075060)
    # Search for constants in this function
    for i in range(100):
        off = func_blaze + i * 4
        if off + 4 > len(blaze):
            break
        word = struct.unpack_from('<I', blaze, off)[0]
        ram = blaze_to_ram(off)
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000

        # Look for interesting immediate values
        interesting = False
        if opcode == 0x0D and imm in (0x03E8, 0x0032, 0x07D0, 0x1388, 0x0014):
            interesting = True
        if opcode == 0x09 and simm in (50, 1000, 2000, 5000, 20, -1, -50):
            interesting = True
        if opcode == 0x0A and abs(simm) in (50, 1000, 20, 100):  # slti
            interesting = True

        if interesting:
            d = disasm(word, ram)
            print(f"    0x{ram:08X}: {d}  *** INTERESTING ***")

        # Stop at jr $ra
        if opcode == 0 and (word & 0x3F) == 0x08:
            break

    # =========================================================================
    # PART 7: Read the handler function pointer table
    # =========================================================================
    print(f"\n{'#'*80}")
    print(f"  PART 7: Handler function table at 0x8005A800")
    print(f"  Handler 41 = chest handler, pointer should be 0x80087624")
    print(f"{'#'*80}")

    handler_table = 0x8005A800
    # Each entry might be 4 bytes (function pointer) or larger
    # Let's read around handler 41
    for idx in range(38, 48):
        ptr = r32(handler_table + idx * 4)
        print(f"  Handler {idx:3d}: 0x{ptr:08X}")

    # Also check if handler table has different structure
    print(f"\n  Handler table first entries:")
    for idx in range(10):
        ptr = r32(handler_table + idx * 4)
        print(f"  Handler {idx:3d}: 0x{ptr:08X}")


if __name__ == '__main__':
    main()
