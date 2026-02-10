#!/usr/bin/env python3
"""
Diagnostic script: analyze loot timer v5 pattern matches in BLAZE.ALL.

Reads the ORIGINAL (unmodified) BLAZE.ALL by extracting from the source BIN,
then finds all 68 v5 patterns and classifies them by surrounding context
to identify which are REAL chest timers vs false positives (animation timers etc).
"""

import struct
import sys
from pathlib import Path

# --- Constants ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

# Source BIN (original, unmodified)
SOURCE_BIN = PROJECT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"

# Fallback: output BLAZE.ALL (may be patched)
OUTPUT_BLAZE = PROJECT_DIR / "output" / "BLAZE.ALL"

# BIN format
SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048
BLAZE_LBA = 163167
BLAZE_SECTORS = 22566  # 46206976 / 2048

# Overlay code search region
OVERLAY_START = 0x00900000
OVERLAY_END = 0x02D00000

# MIPS registers
REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def extract_blaze_from_bin(bin_path):
    """Extract BLAZE.ALL from source BIN file (RAW sector format)."""
    print(f"Extracting BLAZE.ALL from: {bin_path}")
    raw = bin_path.read_bytes()
    total_sectors = len(raw) // SECTOR_RAW
    print(f"  BIN size: {len(raw):,} bytes ({total_sectors} sectors)")

    chunks = []
    for i in range(BLAZE_SECTORS):
        sector = BLAZE_LBA + i
        offset = sector * SECTOR_RAW + USER_OFF
        if offset + USER_SIZE > len(raw):
            print(f"  [WARN] Sector {sector} out of bounds, stopping at {i} sectors")
            break
        chunks.append(raw[offset:offset + USER_SIZE])

    data = b''.join(chunks)
    print(f"  Extracted: {len(data):,} bytes ({len(chunks)} sectors)")
    return bytearray(data)


def load_blaze_all():
    """Load BLAZE.ALL - prefer extracting original from BIN."""
    if SOURCE_BIN.exists():
        return extract_blaze_from_bin(SOURCE_BIN), "SOURCE BIN (original)"
    elif OUTPUT_BLAZE.exists():
        print(f"Reading output BLAZE.ALL: {OUTPUT_BLAZE}")
        data = bytearray(OUTPUT_BLAZE.read_bytes())
        print(f"  Size: {len(data):,} bytes")
        return data, "output/BLAZE.ALL (may be patched)"
    else:
        print("[ERROR] No BLAZE.ALL source found!")
        sys.exit(1)


def decode_instr(word):
    """Decode a MIPS instruction word into a human-readable string."""
    if word == 0x00000000:
        return "nop"

    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    imm_s = imm if imm < 0x8000 else imm - 0x10000

    if opcode == 0x00:  # R-type
        if funct == 0x00:  # sll
            if word == 0:
                return "nop"
            return f"sll {REGS[rd]},{REGS[rt]},{shamt}"
        elif funct == 0x02:  # srl
            return f"srl {REGS[rd]},{REGS[rt]},{shamt}"
        elif funct == 0x03:  # sra
            return f"sra {REGS[rd]},{REGS[rt]},{shamt}"
        elif funct == 0x08:  # jr
            return f"jr {REGS[rs]}"
        elif funct == 0x09:  # jalr
            return f"jalr {REGS[rd]},{REGS[rs]}"
        elif funct == 0x21:  # addu
            return f"addu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x23:  # subu
            return f"subu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x24:  # and
            return f"and {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x25:  # or
            return f"or {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x2A:  # slt
            return f"slt {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x2B:  # sltu
            return f"sltu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        else:
            return f"R-type funct=0x{funct:02X} {REGS[rd]},{REGS[rs]},{REGS[rt]}"
    elif opcode == 0x01:  # REGIMM (bgez, bltz, etc.)
        if rt == 0x01:
            target = imm_s * 4
            return f"bgez {REGS[rs]},PC{target:+d}"
        elif rt == 0x00:
            target = imm_s * 4
            return f"bltz {REGS[rs]},PC{target:+d}"
        elif rt == 0x11:
            target = imm_s * 4
            return f"bgezal {REGS[rs]},PC{target:+d}"
        else:
            target = imm_s * 4
            return f"REGIMM rt={rt} {REGS[rs]},PC{target:+d}"
    elif opcode == 0x02:  # j
        target = (word & 0x03FFFFFF) << 2
        return f"j 0x{target:08X}"
    elif opcode == 0x03:  # jal
        target = (word & 0x03FFFFFF) << 2
        return f"jal 0x{target:08X}"
    elif opcode == 0x04:  # beq
        target = imm_s * 4
        return f"beq {REGS[rs]},{REGS[rt]},PC{target:+d}"
    elif opcode == 0x05:  # bne
        target = imm_s * 4
        return f"bne {REGS[rs]},{REGS[rt]},PC{target:+d}"
    elif opcode == 0x06:  # blez
        target = imm_s * 4
        return f"blez {REGS[rs]},PC{target:+d}"
    elif opcode == 0x07:  # bgtz
        target = imm_s * 4
        return f"bgtz {REGS[rs]},PC{target:+d}"
    elif opcode == 0x08:  # addi
        return f"addi {REGS[rt]},{REGS[rs]},{imm_s}"
    elif opcode == 0x09:  # addiu
        return f"addiu {REGS[rt]},{REGS[rs]},{imm_s}"
    elif opcode == 0x0A:  # slti
        return f"slti {REGS[rt]},{REGS[rs]},{imm_s}"
    elif opcode == 0x0B:  # sltiu
        return f"sltiu {REGS[rt]},{REGS[rs]},{imm_s}"
    elif opcode == 0x0C:  # andi
        return f"andi {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0x0D:  # ori
        return f"ori {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif opcode == 0x0F:  # lui
        return f"lui {REGS[rt]},0x{imm:04X}"
    elif opcode == 0x20:  # lb
        return f"lb {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x21:  # lh
        return f"lh {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x23:  # lw
        return f"lw {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x24:  # lbu
        return f"lbu {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x25:  # lhu
        return f"lhu {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x28:  # sb
        return f"sb {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x29:  # sh
        return f"sh {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif opcode == 0x2B:  # sw
        return f"sw {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    else:
        return f"[op=0x{opcode:02X}] {REGS[rt]},{REGS[rs]},0x{imm:04X}"

    return f"??? 0x{word:08X}"


def find_all_v5_patterns(data):
    """
    Replicate the v5 patcher's pattern search:
      addiu rt, rs, -1  (opcode=0x09, imm=0xFFFF)
      ... (0-1 instructions gap)
      sh rt2, 0x14(base)  (opcode=0x29, imm=0x14)
    """
    matches = []
    search_start = max(0, OVERLAY_START)
    search_end = min(len(data) - 12, OVERLAY_END)

    for i in range(search_start, search_end, 4):
        w = struct.unpack_from('<I', data, i)[0]
        opcode = (w >> 26) & 0x3F
        imm = w & 0xFFFF

        if opcode == 0x09 and imm == 0xFFFF:  # addiu with -1
            rt = (w >> 16) & 0x1F
            rs = (w >> 21) & 0x1F

            for j in range(1, 3):  # next 1-2 instructions
                if i + j * 4 + 4 > len(data):
                    break
                w_sh = struct.unpack_from('<I', data, i + j * 4)[0]
                op_sh = (w_sh >> 26) & 0x3F
                imm_sh = w_sh & 0xFFFF

                if op_sh == 0x29 and imm_sh == 0x0014:
                    rt_sh = (w_sh >> 16) & 0x1F
                    rs_sh = (w_sh >> 21) & 0x1F

                    matches.append({
                        'addiu_pos': i,
                        'sh_pos': i + j * 4,
                        'gap': j,
                        'addiu_dst': rt,
                        'addiu_src': rs,
                        'sh_src': rt_sh,
                        'sh_base': rs_sh,
                    })
                    break

    return matches


def is_lhu_0x14(word):
    """Check if instruction is: lhu <any>, 0x14(<any>)"""
    opcode = (word >> 26) & 0x3F
    imm = word & 0xFFFF
    return opcode == 0x25 and imm == 0x0014


def is_sll_16(word):
    """Check if instruction is: sll <any>, <any>, 16"""
    opcode = (word >> 26) & 0x3F
    funct = word & 0x3F
    shamt = (word >> 6) & 0x1F
    return opcode == 0x00 and funct == 0x00 and shamt == 16 and word != 0


def is_addiu_zero_3(word):
    """Check if instruction is: addiu <any>, $zero, 3"""
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    imm = word & 0xFFFF
    return opcode == 0x09 and rs == 0 and imm == 0x0003


def is_sh_0x10(word):
    """Check if instruction is: sh <any>, 0x10(<any>)"""
    opcode = (word >> 26) & 0x3F
    imm = word & 0xFFFF
    return opcode == 0x29 and imm == 0x0010


def is_bgez(word):
    """Check if instruction is: bgez <any>, <offset>"""
    opcode = (word >> 26) & 0x3F
    rt = (word >> 16) & 0x1F
    return opcode == 0x01 and rt == 0x01


def classify_match(data, match):
    """Classify a match by examining surrounding instructions."""
    addiu_pos = match['addiu_pos']
    sh_pos = match['sh_pos']

    result = {
        'HAS_LHU_BEFORE': False,
        'HAS_SLL16_AFTER': False,
        'HAS_STATE3': False,
        'HAS_SH_0x10': False,
        'HAS_BGEZ_AFTER': False,
    }

    # Check 4 instructions BEFORE the addiu for lhu 0x14
    for k in range(1, 5):
        pos = addiu_pos - k * 4
        if pos < 0:
            break
        w = struct.unpack_from('<I', data, pos)[0]
        if is_lhu_0x14(w):
            result['HAS_LHU_BEFORE'] = True
            break

    # Check 4 instructions AFTER the sh for sll <any>, <any>, 16
    for k in range(1, 5):
        pos = sh_pos + k * 4
        if pos + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, pos)[0]
        if is_sll_16(w):
            result['HAS_SLL16_AFTER'] = True
            break

    # Check 8 instructions AFTER the sh for addiu <any>, $zero, 3
    for k in range(1, 9):
        pos = sh_pos + k * 4
        if pos + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, pos)[0]
        if is_addiu_zero_3(w):
            result['HAS_STATE3'] = True
            break

    # Check 8 instructions AFTER the sh for sh <any>, 0x10(<any>)
    for k in range(1, 9):
        pos = sh_pos + k * 4
        if pos + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, pos)[0]
        if is_sh_0x10(w):
            result['HAS_SH_0x10'] = True
            break

    # Check 6 instructions AFTER the sh for bgez
    for k in range(1, 7):
        pos = sh_pos + k * 4
        if pos + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, pos)[0]
        if is_bgez(w):
            result['HAS_BGEZ_AFTER'] = True
            break

    return result


def main():
    print("=" * 72)
    print("  Loot Timer v5 Diagnostic: Pattern Classification")
    print("=" * 72)
    print()

    # Load BLAZE.ALL
    data, source_desc = load_blaze_all()
    print(f"  Source: {source_desc}")
    print()

    # Find all v5 patterns
    print("Searching for v5 patterns (addiu -1 -> sh 0x14)...")
    matches = find_all_v5_patterns(data)
    print(f"  Found {len(matches)} matches")
    print()

    # Classify each match
    classifications = []
    for m in matches:
        c = classify_match(data, m)
        classifications.append(c)

    # Print detailed results
    CONTEXT_BEFORE = 8
    CONTEXT_AFTER = 8

    for idx, (m, c) in enumerate(zip(matches, classifications)):
        addiu_pos = m['addiu_pos']
        sh_pos = m['sh_pos']

        # Build tags
        tags = []
        for key, val in c.items():
            if val:
                tags.append(key)

        # Determine if this looks like a real chest timer
        is_chest = c['HAS_LHU_BEFORE'] and c['HAS_SLL16_AFTER']
        chest_label = "CHEST-LIKE" if is_chest else "OTHER"

        tag_str = ", ".join(tags) if tags else "(none)"

        print(f"--- Match {idx+1:3d}/{len(matches)} @ addiu=0x{addiu_pos:08X}  "
              f"sh=0x{sh_pos:08X}  [{chest_label}] ---")
        print(f"  Registers: addiu {REGS[m['addiu_dst']]},{REGS[m['addiu_src']]},-1  |  "
              f"sh {REGS[m['sh_src']]},0x14({REGS[m['sh_base']]})")
        print(f"  Tags: {tag_str}")
        print(f"  Context:")

        # Print context window
        first_pos = addiu_pos - CONTEXT_BEFORE * 4
        last_pos = sh_pos + CONTEXT_AFTER * 4

        for pos in range(first_pos, last_pos + 4, 4):
            if pos < 0 or pos + 4 > len(data):
                continue
            w = struct.unpack_from('<I', data, pos)[0]
            disasm = decode_instr(w)

            marker = "  "
            if pos == addiu_pos:
                marker = ">>"
            elif pos == sh_pos:
                marker = ">>"

            print(f"    {marker} 0x{pos:08X}: {w:08X}  {disasm}")

        print()

    # --- Summary ---
    print("=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    print()
    print(f"Total v5 matches: {len(matches)}")
    print()

    # Count each classification
    keys = ['HAS_LHU_BEFORE', 'HAS_SLL16_AFTER', 'HAS_STATE3', 'HAS_SH_0x10', 'HAS_BGEZ_AFTER']
    for key in keys:
        count = sum(1 for c in classifications if c[key])
        print(f"  {key:20s}: {count:3d} / {len(matches)}")

    print()

    # Combination analysis
    combos = {}
    for c in classifications:
        combo = tuple(sorted(k for k in keys if c[k]))
        if not combo:
            combo = ("(none)",)
        combos[combo] = combos.get(combo, 0) + 1

    print("Combination breakdown:")
    for combo, count in sorted(combos.items(), key=lambda x: -x[1]):
        label = " + ".join(combo)
        print(f"  {count:3d}x  {label}")

    print()

    # "Chest-like" = has LHU before + SLL16 after
    chest_count = sum(1 for c in classifications
                      if c['HAS_LHU_BEFORE'] and c['HAS_SLL16_AFTER'])
    other_count = len(matches) - chest_count

    print(f"Chest-like (LHU_BEFORE + SLL16_AFTER): {chest_count}")
    print(f"Other (likely false positives):         {other_count}")
    print()

    # More refined: chest = LHU + SLL16 + BGEZ
    refined = sum(1 for c in classifications
                  if c['HAS_LHU_BEFORE'] and c['HAS_SLL16_AFTER'] and c['HAS_BGEZ_AFTER'])
    print(f"Refined chest (LHU + SLL16 + BGEZ):    {refined}")
    print()

    # Full pattern: LHU + SLL16 + BGEZ + STATE3
    full = sum(1 for c in classifications
               if c['HAS_LHU_BEFORE'] and c['HAS_SLL16_AFTER']
               and c['HAS_BGEZ_AFTER'] and c['HAS_STATE3'])
    print(f"Full pattern (LHU+SLL16+BGEZ+STATE3):  {full}")
    print()

    # List the "OTHER" matches for investigation
    print("-" * 72)
    print("  FALSE POSITIVE candidates (no LHU before or no SLL16 after):")
    print("-" * 72)
    for idx, (m, c) in enumerate(zip(matches, classifications)):
        if not (c['HAS_LHU_BEFORE'] and c['HAS_SLL16_AFTER']):
            tags = [k for k in keys if c[k]]
            tag_str = ", ".join(tags) if tags else "(none)"
            print(f"  #{idx+1:3d}  0x{m['addiu_pos']:08X}  "
                  f"addiu {REGS[m['addiu_dst']]},{REGS[m['addiu_src']]},-1  |  "
                  f"sh {REGS[m['sh_src']]},0x14({REGS[m['sh_base']]})  "
                  f"[{tag_str}]")

    print()
    print("-" * 72)
    print("  CHEST-LIKE matches (LHU before + SLL16 after):")
    print("-" * 72)
    for idx, (m, c) in enumerate(zip(matches, classifications)):
        if c['HAS_LHU_BEFORE'] and c['HAS_SLL16_AFTER']:
            tags = [k for k in keys if c[k]]
            tag_str = ", ".join(tags) if tags else "(none)"
            print(f"  #{idx+1:3d}  0x{m['addiu_pos']:08X}  "
                  f"addiu {REGS[m['addiu_dst']]},{REGS[m['addiu_src']]},-1  |  "
                  f"sh {REGS[m['sh_src']]},0x14({REGS[m['sh_base']]})  "
                  f"[{tag_str}]")

    print()
    print("=" * 72)
    print("  RECOMMENDATION")
    print("=" * 72)
    print()
    print("To reduce false positives, the v5 patcher should add additional checks:")
    print("  1. Require lhu <any>, 0x14(<base>) within 4 instructions BEFORE addiu")
    print("  2. Require sll <any>, <any>, 16 within 4 instructions AFTER sh")
    print("  3. Optionally require bgez within 6 instructions AFTER sh")
    print()
    print(f"This would reduce matches from {len(matches)} -> ~{chest_count} "
          f"(removing {other_count} likely false positives)")
    print()


if __name__ == '__main__':
    main()
