#!/usr/bin/env python3
"""
With overlay base = 0x80039000, the stat_mod function at RAM 0x8008A3E4
is at BLAZE+0x009513E4.

Step 1: Dump and verify this function
Step 2: Get its signature (first N unique instructions)
Step 3: Search ALL overlay regions for the same function
Step 4: For each match, find what JAL encoding callers would use
Step 5: Search for those callers with negative args
"""

import struct
from pathlib import Path
from collections import defaultdict

BLAZE_ALL = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377"
                 r"\GameplayPatch\output\BLAZE.ALL")

BASE_ADDR = 0x80039000
REGION_START = 0x00900000
STAT_MOD_RAM = 0x8008A3E4
FUNC_BLAZE = REGION_START + (STAT_MOD_RAM - BASE_ADDR)  # 0x009513E4

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def disasm(word):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    func = word & 0x3F
    imm = word & 0xFFFF
    imms = imm if imm < 0x8000 else imm - 0x10000

    if word == 0:
        return "nop"
    if word == 0x03E00008:
        return "jr $ra"
    if op == 0:
        ops = {0x20: 'add', 0x21: 'addu', 0x23: 'subu', 0x24: 'and',
               0x25: 'or', 0x2A: 'slt', 0x2B: 'sltu', 0x00: 'sll',
               0x02: 'srl', 0x08: 'jr', 0x09: 'jalr', 0x10: 'mfhi',
               0x12: 'mflo', 0x18: 'mult', 0x1A: 'div'}
        name = ops.get(func, f'R{func:02X}')
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
    if op == 0x03:
        target = ((word & 0x3FFFFFF) << 2) | 0x80000000
        return f"jal 0x{target:08X}"
    if op == 0x04:
        return f"beq {REGS[rs]}, {REGS[rt]}, {imms}"
    if op == 0x05:
        return f"bne {REGS[rs]}, {REGS[rt]}, {imms}"
    return f"[{op:02X} {REGS[rs]} {REGS[rt]} {imms}]"


def extract_args_before_jal(data, jal_off, start):
    """Extract immediate args ($a1-$a3) from instructions before JAL."""
    args = {}
    for j in range(1, 13):
        off = jal_off - j * 4
        if off < start:
            break
        w = struct.unpack_from('<I', data, off)[0]
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000
        if op == 0x09 and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imms
        elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imm
        elif (w >> 26) == 0x03:  # Another JAL = stop
            break

    # Delay slot
    ds_off = jal_off + 4
    if ds_off + 4 <= len(data):
        w = struct.unpack_from('<I', data, ds_off)[0]
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000
        if op == 0x09 and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imms
        elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imm

    return args


def main():
    print("=" * 70)
    print("  Prove Stat_Mod Function Exists in Multiple Dungeons")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()
    print(f"  Overlay base: 0x{BASE_ADDR:08X}")
    print(f"  stat_mod RAM: 0x{STAT_MOD_RAM:08X}")
    print(f"  stat_mod BLAZE: 0x{FUNC_BLAZE:08X}")

    # Step 1: Dump the function
    print(f"\n{'='*70}")
    print(f"  STEP 1: Function at BLAZE+0x{FUNC_BLAZE:08X}")
    print(f"{'='*70}")

    for i in range(40):
        off = FUNC_BLAZE + i * 4
        if off + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, off)[0]
        ram = BASE_ADDR + (off - REGION_START)
        d = disasm(w)
        marker = ""
        if w == 0x03E00008:
            marker = " <-- RETURN"
        print(f"    0x{ram:08X}: {w:08X}  {d}{marker}")
        if w == 0x03E00008 and i > 2:
            # Show delay slot
            off2 = off + 4
            if off2 + 4 <= len(data):
                w2 = struct.unpack_from('<I', data, off2)[0]
                ram2 = BASE_ADDR + (off2 - REGION_START)
                print(f"    0x{ram2:08X}: {w2:08X}  {disasm(w2)}  (delay slot)")
            break

    # Step 2: Extract signature - use the first unique non-trivial words
    # Skip common instructions (nop, stack save) and use body instructions
    print(f"\n{'='*70}")
    print(f"  STEP 2: Function signature extraction")
    print(f"{'='*70}")

    # Read first 20 words
    func_words = []
    for i in range(30):
        off = FUNC_BLAZE + i * 4
        if off + 4 > len(data):
            break
        func_words.append(struct.unpack_from('<I', data, off)[0])

    # The signature is the BODY of the function (after prologue)
    # Find the first instruction after the sw chain
    body_start = 0
    for i, w in enumerate(func_words):
        if (w >> 26) == 0x2B:  # sw
            continue
        if (w >> 16) == 0x27BD:  # addiu $sp
            continue
        if w == 0:  # nop
            if i > 0:
                body_start = i
                break
            continue
        body_start = i
        break

    signature = func_words[body_start:body_start + 8]
    print(f"  Signature (from word {body_start}, 8 words):")
    for i, w in enumerate(signature):
        off = FUNC_BLAZE + (body_start + i) * 4
        print(f"    [{i}] 0x{w:08X}  {disasm(w)}")

    # Also try: match on the first 3 distinct body instructions
    # that are NOT common patterns (nop, common branch)

    # Step 3: Search all of BLAZE.ALL for this signature
    print(f"\n{'='*70}")
    print(f"  STEP 3: Search for function signature in ALL overlays")
    print(f"{'='*70}")

    # Search with first 4 words of signature
    sig4 = signature[:4]
    matches = []
    search_end = min(0x02D00000, len(data) - len(sig4) * 4)

    for off in range(0x00900000, search_end, 4):
        match = True
        for i, sw in enumerate(sig4):
            w = struct.unpack_from('<I', data, off + i * 4)[0]
            if w != sw:
                match = False
                break
        if match:
            # Count total matching words
            total_match = 4
            for i in range(4, min(8, len(signature))):
                w = struct.unpack_from('<I', data, off + i * 4)[0]
                if w == signature[i]:
                    total_match += 1
            matches.append((off, total_match))

    print(f"  Found {len(matches)} signature matches (4+ words)")
    for off, score in matches[:30]:
        region_mb = off >> 20
        # Calculate what the function's RAM address would be in this region
        # We need to know this region's overlay base to calculate
        # For now, just show the offset
        print(f"    BLAZE+0x{off:08X} (region 0x{region_mb:03X}): "
              f"{score}/{len(signature)} words match")

    if len(matches) <= 1:
        # Try with fewer words
        print(f"\n  Trying with only first 2 signature words...")
        sig2 = signature[:2]
        matches2 = []
        for off in range(0x00900000, search_end, 4):
            w0 = struct.unpack_from('<I', data, off)[0]
            w1 = struct.unpack_from('<I', data, off + 4)[0]
            if w0 == sig2[0] and w1 == sig2[1]:
                matches2.append(off)
        print(f"  Found {len(matches2)} matches with 2 words")
        for off in matches2[:20]:
            region_mb = off >> 20
            print(f"    BLAZE+0x{off:08X} (region 0x{region_mb:03X})")

    # Step 4: Search for the function based on its prologue pattern
    # The prologue is addiu $sp + chain of sw instructions
    print(f"\n{'='*70}")
    print(f"  STEP 4: Search by function structure (prologue + body pattern)")
    print(f"{'='*70}")

    # Get the full function signature including prologue
    prologue = func_words[0]  # Should be addiu $sp or start of function
    print(f"  First word: 0x{prologue:08X} = {disasm(prologue)}")

    # The stat_mod function modifies entity stats via $a0+offset reads and writes
    # Key pattern: it reads from entity ($a0/saved reg), adds $a1/$a2/$a3, writes back
    # Look for: lh/lhu from entity offset, addu with arg reg, sh to same offset

    # Let me search for the EXACT full function (first 16 words)
    full_sig = func_words[:16]
    print(f"  Searching with full 16-word signature...")

    full_matches = []
    for off in range(0x00900000, search_end, 4):
        if struct.unpack_from('<I', data, off)[0] != full_sig[0]:
            continue
        match_count = 1
        for i in range(1, len(full_sig)):
            w = struct.unpack_from('<I', data, off + i * 4)[0]
            if w == full_sig[i]:
                match_count += 1
        if match_count >= 12:  # At least 12/16 match
            full_matches.append((off, match_count))

    print(f"  Found {len(full_matches)} matches (12+ of 16 words)")
    for off, score in full_matches[:30]:
        region_mb = off >> 20
        print(f"    BLAZE+0x{off:08X} (region 0x{region_mb:03X}): {score}/16")

    # Step 5: If the function exists in multiple regions, find callers
    print(f"\n{'='*70}")
    print(f"  STEP 5: If function found in other regions, find damage callers")
    print(f"{'='*70}")

    if len(full_matches) > 1 or len(matches) > 1:
        all_matches_offsets = set()
        for off, _ in full_matches:
            all_matches_offsets.add(off)
        for off, _ in matches:
            all_matches_offsets.add(off)

        for func_off in sorted(all_matches_offsets):
            if func_off == FUNC_BLAZE:
                continue  # Skip the original

            # This function at BLAZE+func_off would be at a different RAM address
            # in that region's overlay. We need to compute the JAL encoding.

            # The region containing this function has its own overlay base.
            # We don't know it, but we can compute the RAM address of this function
            # relative to the original.

            # Actually, each overlay has its own base. Without knowing it,
            # we can't compute the JAL target. But we CAN search for JAL
            # instructions near the function that target the same relative offset.

            # Alternative: the function might be at the SAME RAM address if the
            # overlay is loaded at the same base. Let's check.
            same_jal = 0x0C0228F9  # jal 0x8008A3E4
            # Search the region around this function for callers
            region_start = (func_off >> 20) << 20  # Align to 1MB
            region_end = min(region_start + 0x100000, len(data) - 4)

            count = 0
            damage_callers = []
            for off in range(region_start, region_end, 4):
                w = struct.unpack_from('<I', data, off)[0]
                if w == same_jal:
                    args = extract_args_before_jal(data, off, region_start)
                    has_neg = any(v < 0 for r, v in args.items() if r in (5, 6, 7))
                    count += 1
                    if has_neg:
                        damage_callers.append((off, args))

            print(f"\n  Function at BLAZE+0x{func_off:08X}: "
                  f"{count} JAL callers, {len(damage_callers)} with damage args")
            for off, args in damage_callers[:5]:
                args_str = ', '.join(f"$a{r-4}={v}" for r, v in sorted(args.items()))
                print(f"    0x{off:08X}: {args_str}")
            if len(damage_callers) > 5:
                print(f"    ... and {len(damage_callers)-5} more")
    else:
        print(f"  Function only found in Region_00. Other regions have DIFFERENT code.")
        print(f"\n  Let's look for structurally similar functions instead...")

        # Search for ANY function that does: lh from entity, add delta, sh back
        # Pattern: lh $reg, offset($s0/$s1) ... addu $reg, $reg, $a1 ... sh $reg, offset($s0/$s1)
        # This is a "stat modify" pattern

        # Actually, let's just search for the JAL to 0x8008A3E4 across
        # the ENTIRE file (not just overlay region)
        print(f"\n  Exhaustive search for jal 0x8008A3E4 across entire BLAZE.ALL...")
        jal_word = 0x0C0228F9
        all_jals = []
        for off in range(0, len(data) - 4, 4):
            if struct.unpack_from('<I', data, off)[0] == jal_word:
                all_jals.append(off)
        print(f"  Total: {len(all_jals)} matches")
        by_region = defaultdict(list)
        for off in all_jals:
            by_region[off >> 20].append(off)
        for region, offs in sorted(by_region.items()):
            print(f"    Region 0x{region:03X}: {len(offs)} ({offs[0]:08X} - {offs[-1]:08X})")


if __name__ == "__main__":
    main()
