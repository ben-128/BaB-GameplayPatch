#!/usr/bin/env python3
"""
Phase 1: Verify overlay base = 0x80068000 by dumping the stat_mod function
Phase 2: Extract function signature and search ALL overlay regions for it
Phase 3: If found elsewhere, find callers with negative args in those regions
"""

import struct
from pathlib import Path
from collections import defaultdict

BLAZE_ALL = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377"
                 r"\GameplayPatch\output\BLAZE.ALL")

BASE_ADDR = 0x80068000  # Candidate overlay base
REGION_START = 0x00900000
STAT_MOD_ADDR = 0x8008A3E4

# Calculate function's BLAZE.ALL offset
FUNC_BLAZE_OFF = REGION_START + (STAT_MOD_ADDR - BASE_ADDR)  # 0x009223E4

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def disasm(word, pc=0):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    sa = (word >> 6) & 0x1F
    func = word & 0x3F
    imm = word & 0xFFFF
    imms = imm if imm < 0x8000 else imm - 0x10000

    if word == 0:
        return "nop"
    if word == 0x03E00008:
        return "jr $ra"
    if op == 0:
        ops = {0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu',
               0x24: 'and', 0x25: 'or', 0x26: 'xor', 0x27: 'nor',
               0x2A: 'slt', 0x2B: 'sltu', 0x00: 'sll', 0x02: 'srl',
               0x03: 'sra', 0x08: 'jr', 0x09: 'jalr', 0x18: 'mult',
               0x19: 'multu', 0x1A: 'div', 0x1B: 'divu',
               0x10: 'mfhi', 0x12: 'mflo'}
        name = ops.get(func, f'R{func:02X}')
        if func in (0x00, 0x02, 0x03):
            return f"{name} {REGS[rd]}, {REGS[rt]}, {sa}"
        return f"{name} {REGS[rd]}, {REGS[rs]}, {REGS[rt]}"
    if op == 0x09:
        return f"addiu {REGS[rt]}, {REGS[rs]}, {imms}"
    if op == 0x0D:
        return f"ori {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    if op == 0x0C:
        return f"andi {REGS[rt]}, {REGS[rs]}, 0x{imm:04X}"
    if op == 0x0F:
        return f"lui {REGS[rt]}, 0x{imm:04X}"
    if op == 0x23:
        return f"lw {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x2B:
        return f"sw {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x21:
        return f"lh {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x25:
        return f"lhu {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x29:
        return f"sh {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x20:
        return f"lb {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x24:
        return f"lbu {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x28:
        return f"sb {REGS[rt]}, {imms}({REGS[rs]})"
    if op == 0x03:
        target = ((word & 0x3FFFFFF) << 2) | 0x80000000
        return f"jal 0x{target:08X}"
    if op == 0x02:
        target = ((word & 0x3FFFFFF) << 2) | 0x80000000
        return f"j 0x{target:08X}"
    if op == 0x04:
        return f"beq {REGS[rs]}, {REGS[rt]}, {imms}"
    if op == 0x05:
        return f"bne {REGS[rs]}, {REGS[rt]}, {imms}"
    if op == 0x06:
        return f"blez {REGS[rs]}, {imms}"
    if op == 0x07:
        return f"bgtz {REGS[rs]}, {imms}"
    if op == 0x01:
        if rt == 0:
            return f"bltz {REGS[rs]}, {imms}"
        if rt == 1:
            return f"bgez {REGS[rs]}, {imms}"
    return f"[op=0x{op:02X} {REGS[rs]} {REGS[rt]} imm={imms}]"


def dump_function(data, blaze_off, base, num_words=80):
    """Dump and disassemble a function from BLAZE.ALL."""
    print(f"\n  Function disassembly at BLAZE+0x{blaze_off:08X} "
          f"(RAM 0x{base + (blaze_off - REGION_START):08X}):")

    for i in range(num_words):
        off = blaze_off + i * 4
        if off + 4 > len(data):
            break
        word = struct.unpack_from('<I', data, off)[0]
        ram = base + (off - REGION_START)
        inst = disasm(word, ram)
        marker = ""
        if word == 0x03E00008:
            marker = "  <-- RETURN"
        print(f"    0x{ram:08X} [{off:08X}]: {word:08X}  {inst}{marker}")
        if word == 0x03E00008 and i > 2:
            # Print delay slot and stop
            off2 = off + 4
            if off2 + 4 <= len(data):
                w2 = struct.unpack_from('<I', data, off2)[0]
                ram2 = base + (off2 - REGION_START)
                print(f"    0x{ram2:08X} [{off2:08X}]: {w2:08X}  {disasm(w2)}  <-- delay slot")
            print(f"    --- function end ---")
            return off2 + 4 - blaze_off  # Return function size
    return num_words * 4


def main():
    print("=" * 70)
    print("  Verify Overlay Base & Search for Damage Function")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()
    print(f"  BLAZE.ALL: {len(data):,} bytes")
    print(f"  Overlay base (candidate): 0x{BASE_ADDR:08X}")
    print(f"  stat_mod function: RAM 0x{STAT_MOD_ADDR:08X} -> BLAZE+0x{FUNC_BLAZE_OFF:08X}")

    # Phase 1: Dump the stat_mod function
    print(f"\n{'='*70}")
    print(f"  PHASE 1: Dump stat_mod function at 0x{STAT_MOD_ADDR:08X}")
    print(f"{'='*70}")

    func_size = dump_function(data, FUNC_BLAZE_OFF, BASE_ADDR)

    # Get the function signature (first 8 words, skipping leading NOP)
    sig_start = FUNC_BLAZE_OFF
    first_word = struct.unpack_from('<I', data, sig_start)[0]
    if first_word == 0:  # Skip leading NOP
        sig_start += 4

    signature = []
    for i in range(8):
        w = struct.unpack_from('<I', data, sig_start + i * 4)[0]
        signature.append(w)

    print(f"\n  Function signature (first 8 words from prologue):")
    for i, w in enumerate(signature):
        print(f"    [{i}] 0x{w:08X}  {disasm(w)}")

    # Phase 2: Search ALL overlay regions for this signature
    print(f"\n{'='*70}")
    print(f"  PHASE 2: Search ALL of BLAZE.ALL for function signature")
    print(f"{'='*70}")

    # Search using first 3-4 unique words of the signature
    # The prologue (addiu $sp + sw $ra + sw $fp) is too common
    # Use a combination of prologue + first unique instructions

    # Actually, let's search for the prologue pattern and then verify
    # by checking the rest of the function
    prologue = signature[0]  # addiu $sp, $sp, -72
    save_ra = signature[1]   # sw $ra, 68($sp)
    save_fp = signature[2]   # sw $fp, 64($sp)

    print(f"  Searching for prologue: {prologue:08X} {save_ra:08X} {save_fp:08X}")

    matches = []
    search_end = min(0x02D00000, len(data) - 12)
    for off in range(0x00900000, search_end, 4):
        w0 = struct.unpack_from('<I', data, off)[0]
        if w0 != prologue:
            continue
        w1 = struct.unpack_from('<I', data, off + 4)[0]
        w2 = struct.unpack_from('<I', data, off + 8)[0]
        if w1 == save_ra and w2 == save_fp:
            # Check more words
            match_count = 3
            for i in range(3, min(8, len(signature))):
                wi = struct.unpack_from('<I', data, off + i * 4)[0]
                if wi == signature[i]:
                    match_count += 1
            matches.append((off, match_count))

    print(f"  Found {len(matches)} prologue matches")

    # Also search for a longer signature (5+ matching words)
    strong_matches = [m for m in matches if m[1] >= 5]
    print(f"  Strong matches (5+ words): {len(strong_matches)}")

    for off, score in matches:
        # What region is this in?
        region_mb = off >> 20
        print(f"    BLAZE+0x{off:08X} (region 0x{region_mb:03X}): "
              f"{score}/{len(signature)} words match")

        # Calculate what base would put this at 0x8008A3E4
        # (off - NOP) corresponds to function start
        # If there's a NOP before, adjust
        candidate_base = STAT_MOD_ADDR - (off - REGION_START)
        if off > REGION_START:
            prev = struct.unpack_from('<I', data, off - 4)[0]
            if prev == 0:  # NOP before prologue
                candidate_base = STAT_MOD_ADDR - (off - 4 - REGION_START)

        # Show a few instructions
        for i in range(4):
            w = struct.unpack_from('<I', data, off + i*4)[0]
            print(f"      +{i*4:2d}: {w:08X}  {disasm(w)}")

    # Phase 3: Alternative approach - search for the JAL encoding itself
    # but with different target addresses (for different overlay bases)
    print(f"\n{'='*70}")
    print(f"  PHASE 3: Search for stat_mod JAL callers across all regions")
    print(f"{'='*70}")

    # The JAL to 0x8008A3E4 is: 0x0C0228F9
    jal_word = 0x0C0228F9
    all_jals = []
    for off in range(0x00900000, min(0x02D00000, len(data) - 4), 4):
        w = struct.unpack_from('<I', data, off)[0]
        if w == jal_word:
            all_jals.append(off)

    print(f"  JAL 0x8008A3E4 (0x{jal_word:08X}): found at {len(all_jals)} locations")

    # Group by region
    by_region = defaultdict(list)
    for off in all_jals:
        region = off >> 20
        by_region[region].append(off)

    for region, offs in sorted(by_region.items()):
        print(f"    Region 0x{region:03X}: {len(offs)} callers "
              f"(0x{offs[0]:08X} - 0x{offs[-1]:08X})")

    # Phase 4: What if different regions use different JAL targets
    # for the SAME function (loaded at different base)?
    print(f"\n{'='*70}")
    print(f"  PHASE 4: Check if function exists at different RAM addresses")
    print(f"{'='*70}")

    # If we find the exact same function code at different BLAZE offsets,
    # those would use different JAL encodings
    if strong_matches:
        print(f"\n  Strong signature matches suggest the function exists at:")
        for off, score in strong_matches:
            # Different regions would load at different bases
            # Calculate what JAL encoding callers in that region would use
            # We don't know the base for other regions, but we can check
            # if there are JALs targeting a plausible address
            print(f"    BLAZE+0x{off:08X}: {score} words match")

            # Find the function relative offset within its region
            # Assuming same structure, the relative offset from region start
            func_rel = off - FUNC_BLAZE_OFF  # Shift from Region_00

            # Look for callers of this function nearby
            # The callers in Region_00 are at ~0x0095-0x0096
            # Corresponding callers in other regions would be at similar relative offsets
            caller_zone_start = off + (0x00951D30 - FUNC_BLAZE_OFF)
            caller_zone_end = off + (0x00960DE4 - FUNC_BLAZE_OFF)
            if caller_zone_start < len(data) and caller_zone_end < len(data):
                # Count JAL instructions in this zone
                jal_count = 0
                for coff in range(int(caller_zone_start), int(min(caller_zone_end, len(data) - 4)), 4):
                    w = struct.unpack_from('<I', data, coff)[0]
                    if (w >> 26) == 0x03:
                        target = ((w & 0x3FFFFFF) << 2) | 0x80000000
                        jal_count += 1
                print(f"      Caller zone: 0x{caller_zone_start:08X}-0x{caller_zone_end:08X} "
                      f"({jal_count} JALs)")


if __name__ == "__main__":
    main()
