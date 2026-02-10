#!/usr/bin/env python3
"""
Determine the overlay load base address for Region_00 (0x009-0x009C).

Strategy: The overlay code calls both EXE functions (known RAM addr)
and its own internal functions (stat_mod at 0x8008A3E4 etc.).

If we know the overlay loads at base B, then:
  - BLAZE offset 0x00900000 maps to RAM address B
  - BLAZE offset 0x00900000 + X maps to RAM address B + X
  - Function at RAM 0x8008A3E4 is at BLAZE offset 0x00900000 + (0x8008A3E4 - B)

We try candidate bases and verify by checking if the computed function
offset in BLAZE.ALL looks like valid MIPS function code.

Also: look for the function's JR $RA (return) instruction to find its boundaries.
"""

import struct
from pathlib import Path

BLAZE_ALL = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377"
                 r"\GameplayPatch\output\BLAZE.ALL")

REGION_START = 0x00900000  # Region_00 start in BLAZE.ALL

# Known overlay functions
STAT_MOD_FUNCS = [0x8008A1C4, 0x8008A39C, 0x8008A3BC, 0x8008A3E4]

# MIPS helper
def is_jr_ra(word):
    return word == 0x03E00008

def is_addiu_sp(word):
    """addiu $sp, $sp, imm (function prologue/epilogue)"""
    return (word >> 16) == 0x27BD

def disasm_basic(word):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    imms = imm if imm < 0x8000 else imm - 0x10000
    func = word & 0x3F

    if word == 0:
        return "nop"
    if word == 0x03E00008:
        return "jr $ra"
    if op == 0:  # R-type
        return f"R-type rd=${rd} rs=${rs} rt=${rt} func=0x{func:02X}"
    if op == 0x09:
        return f"addiu ${rt}, ${rs}, {imms}"
    if op == 0x0D:
        return f"ori ${rt}, ${rs}, 0x{imm:04X}"
    if op == 0x23:
        return f"lw ${rt}, {imms}(${rs})"
    if op == 0x2B:
        return f"sw ${rt}, {imms}(${rs})"
    if op == 0x21:
        return f"lh ${rt}, {imms}(${rs})"
    if op == 0x29:
        return f"sh ${rt}, {imms}(${rs})"
    if op == 0x0F:
        return f"lui ${rt}, 0x{imm:04X}"
    if op == 0x03:
        target = ((word & 0x3FFFFFF) << 2) | 0x80000000
        return f"jal 0x{target:08X}"
    if op == 0x04:
        return f"beq ${rs}, ${rt}, {imms}"
    if op == 0x05:
        return f"bne ${rs}, ${rt}, {imms}"
    return f"op=0x{op:02X} rs=${rs} rt=${rt} imm={imms}"


def check_candidate_base(data, base):
    """Check if base address makes sense for the overlay."""
    results = {}
    all_valid = True

    for func_addr in STAT_MOD_FUNCS:
        blaze_off = REGION_START + (func_addr - base)

        if blaze_off < REGION_START or blaze_off >= REGION_START + 0xC0000:
            results[func_addr] = "OUT OF RANGE"
            all_valid = False
            continue

        if blaze_off + 64 > len(data):
            results[func_addr] = "PAST EOF"
            all_valid = False
            continue

        # Read 8 words starting at the function
        words = [struct.unpack_from('<I', data, blaze_off + i*4)[0] for i in range(8)]

        # Check: does it look like a function entry?
        # Typical prologue: addiu $sp, $sp, -N (where N > 0, so imm is negative)
        w0 = words[0]
        looks_like_code = False
        desc = ""

        if is_addiu_sp(w0):
            imm = w0 & 0xFFFF
            imms = imm if imm < 0x8000 else imm - 0x10000
            if imms < 0:  # Prologue (allocating stack)
                looks_like_code = True
                desc = f"prologue: addiu $sp, $sp, {imms}"
        elif is_jr_ra(w0):
            desc = "jr $ra (tail of previous func?)"
        elif w0 == 0:
            desc = "NOP (could be alignment)"
        elif (w0 >> 26) == 0x03:
            target = ((w0 & 0x3FFFFFF) << 2) | 0x80000000
            desc = f"jal 0x{target:08X}"
            looks_like_code = True
        else:
            desc = disasm_basic(w0)
            # Check if it's reasonable MIPS
            op = (w0 >> 26) & 0x3F
            if op in [0, 0x04, 0x05, 0x08, 0x09, 0x0D, 0x0F, 0x21, 0x23, 0x25, 0x29, 0x2B, 0x03]:
                looks_like_code = True

        if not looks_like_code:
            all_valid = False

        results[func_addr] = {
            'blaze_off': blaze_off,
            'looks_like_code': looks_like_code,
            'desc': desc,
            'words': words,
        }

    return results, all_valid


def main():
    print("=" * 70)
    print("  Determine Overlay Load Base Address")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()

    # Candidate base addresses
    candidates = [
        0x80080000,  # Nice round address in BSS
        0x80078000,
        0x80070000,
        0x80088000,
        0x80090000,
        0x800A0000,
        0x800B0000,
        0x800C0000,
    ]

    best_base = None
    best_score = -1

    for base in candidates:
        results, all_valid = check_candidate_base(data, base)
        score = sum(1 for r in results.values() if isinstance(r, dict) and r['looks_like_code'])

        print(f"\n  Base 0x{base:08X}: score={score}/4, all_valid={all_valid}")
        for func_addr, r in sorted(results.items()):
            if isinstance(r, str):
                print(f"    0x{func_addr:08X}: {r}")
            else:
                off = r['blaze_off']
                words_hex = ' '.join(f'{w:08X}' for w in r['words'][:4])
                print(f"    0x{func_addr:08X} -> BLAZE+0x{off:08X}: "
                      f"{'OK' if r['looks_like_code'] else 'BAD'} "
                      f"[{r['desc']}]")
                print(f"      Words: {words_hex}")

        if score > best_score:
            best_score = score
            best_base = base

    # Try more granular search around best candidate
    print(f"\n  Refining around 0x{best_base:08X}...")
    for delta in range(-0x10000, 0x10000, 0x1000):
        base = best_base + delta
        results, all_valid = check_candidate_base(data, base)
        score = sum(1 for r in results.values() if isinstance(r, dict) and r['looks_like_code'])
        if score >= 3:
            print(f"\n  Base 0x{base:08X}: score={score}/4")
            for func_addr, r in sorted(results.items()):
                if isinstance(r, dict):
                    off = r['blaze_off']
                    words_hex = ' '.join(f'{w:08X}' for w in r['words'][:4])
                    print(f"    0x{func_addr:08X} -> BLAZE+0x{off:08X}: "
                          f"{'OK' if r['looks_like_code'] else '--'} "
                          f"[{r['desc']}]  {words_hex}")

    # Also: look for addiu $sp, $sp patterns that could be function prologues
    # near the expected offsets for different bases
    print(f"\n  Searching Region_00 for stat_mod function signature...")
    print(f"  (function at RAM 0x8008A3E4, looking for prologue)")

    # The 4 functions are within 576 bytes of each other
    # Search all of Region_00 for clusters of 4 function prologues with the right spacing
    region_end = min(REGION_START + 0xC0000, len(data))
    spacing = [
        STAT_MOD_FUNCS[1] - STAT_MOD_FUNCS[0],  # 0x1D8
        STAT_MOD_FUNCS[2] - STAT_MOD_FUNCS[1],  # 0x20
        STAT_MOD_FUNCS[3] - STAT_MOD_FUNCS[2],  # 0x28
    ]
    print(f"  Expected spacing: {', '.join(f'0x{s:X}' for s in spacing)}")

    found_clusters = []
    for off in range(REGION_START, region_end - 0x300, 4):
        # Check if all 4 positions have function-like code
        offsets = [off]
        for s in spacing:
            offsets.append(offsets[-1] + s)

        if offsets[-1] + 4 > len(data):
            continue

        all_func = True
        details = []
        for o in offsets:
            w = struct.unpack_from('<I', data, o)[0]
            if is_addiu_sp(w):
                imm = w & 0xFFFF
                imms = imm if imm < 0x8000 else imm - 0x10000
                if imms < 0:
                    details.append(f"prologue({imms})")
                    continue
            # Also accept: jr $ra could be end of previous function
            # The function might not start with addiu $sp
            all_func = False
            break

        if all_func:
            base = STAT_MOD_FUNCS[0] - (offsets[0] - REGION_START)
            found_clusters.append((offsets[0], base, details))

    if found_clusters:
        print(f"  Found {len(found_clusters)} matching clusters:")
        for off, base, details in found_clusters[:10]:
            print(f"    BLAZE+0x{off:08X}: base=0x{base:08X} [{', '.join(details)}]")

            # Verify: dump the 4 function prologues
            for i, func_addr in enumerate(STAT_MOD_FUNCS):
                func_blaze = REGION_START + (func_addr - base)
                words = [struct.unpack_from('<I', data, func_blaze + j*4)[0] for j in range(4)]
                disasm = [disasm_basic(w) for w in words]
                print(f"      0x{func_addr:08X} at BLAZE+0x{func_blaze:08X}: "
                      f"{' | '.join(disasm[:3])}")
    else:
        print("  No clusters found with exact spacing match.")
        print("  Trying relaxed search (any 2 prologues with first spacing)...")
        for off in range(REGION_START, region_end - spacing[0] - 4, 4):
            w1 = struct.unpack_from('<I', data, off)[0]
            w2 = struct.unpack_from('<I', data, off + spacing[0])[0]
            if is_addiu_sp(w1) and is_addiu_sp(w2):
                imm1 = (w1 & 0xFFFF)
                imm1 = imm1 if imm1 < 0x8000 else imm1 - 0x10000
                imm2 = (w2 & 0xFFFF)
                imm2 = imm2 if imm2 < 0x8000 else imm2 - 0x10000
                if imm1 < 0 and imm2 < 0:
                    base = STAT_MOD_FUNCS[0] - (off - REGION_START)
                    # Check 3rd and 4th
                    off3 = off + spacing[0] + spacing[1]
                    off4 = off + spacing[0] + spacing[1] + spacing[2]
                    if off4 + 4 < len(data):
                        w3 = struct.unpack_from('<I', data, off3)[0]
                        w4 = struct.unpack_from('<I', data, off4)[0]
                        score = 2
                        if is_addiu_sp(w3):
                            score += 1
                        if is_addiu_sp(w4):
                            score += 1
                        if score >= 3:
                            print(f"    BLAZE+0x{off:08X}: base=0x{base:08X} "
                                  f"score={score}/4 "
                                  f"sp_deltas=[{imm1},{imm2}]")


if __name__ == "__main__":
    main()
