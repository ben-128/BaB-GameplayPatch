#!/usr/bin/env python3
"""
Phase 2.1: Search the PSX executable for trap damage patterns.

Trap damage could be hardcoded in the MIPS code (like the loot timer was).
This script searches for:
1. MIPS 'li' (addiu/ori) instructions with common damage values
2. HP subtraction patterns near collision/entity handlers
3. References to the combat handler table / state machine
4. Overlay code in BLAZE.ALL that may contain per-area trap logic

Known addresses (from combat handler research):
  - Combat handler table: 0x8003C1B0 (55 entries)
  - State machine: 0x8003B324 (32 entries)
  - Creature type dispatch: 0x80024494
  - EXE base RAM: 0x80010000

Usage: py -3 WIP/TrapDamage/search_exe_damage.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# SLES extracted file
SLES_PATH = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# MIPS register names
REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

# EXE loads at RAM 0x80010000, file header is 0x800 bytes
EXE_RAM_BASE = 0x80010000
EXE_FILE_HEADER = 0x800


def file_to_ram(file_off):
    """Convert SLES file offset to RAM address."""
    return EXE_RAM_BASE + file_off - EXE_FILE_HEADER


def ram_to_file(ram_addr):
    """Convert RAM address to SLES file offset."""
    return ram_addr - EXE_RAM_BASE + EXE_FILE_HEADER


def decode_mips(word):
    """Decode a MIPS instruction word into components."""
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    imm_signed = imm if imm < 0x8000 else imm - 0x10000
    target = word & 0x3FFFFFF
    return {
        'opcode': opcode, 'rs': rs, 'rt': rt, 'rd': rd,
        'shamt': shamt, 'funct': funct,
        'imm': imm, 'imm_signed': imm_signed, 'target': target,
        'word': word
    }


def disasm_simple(word, addr=0):
    """Simple MIPS disassembler for common instructions."""
    d = decode_mips(word)
    op = d['opcode']
    rs, rt, rd = d['rs'], d['rt'], d['rd']
    imm = d['imm']
    imms = d['imm_signed']
    funct = d['funct']

    if word == 0:
        return "nop"
    elif op == 0:  # R-type
        if funct == 0x21: return f"addu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x23: return f"subu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x25: return f"or {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x09: return f"jalr {REGS[rd]},{REGS[rs]}"
        elif funct == 0x08: return f"jr {REGS[rs]}"
        elif funct == 0x2A: return f"slt {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif funct == 0x2B: return f"sltu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        else: return f"R-type funct=0x{funct:02X} rd={REGS[rd]} rs={REGS[rs]} rt={REGS[rt]}"
    elif op == 0x09: return f"addiu {REGS[rt]},{REGS[rs]},{imms}"
    elif op == 0x0D: return f"ori {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    elif op == 0x0F: return f"lui {REGS[rt]},0x{imm:04X}"
    elif op == 0x23: return f"lw {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x21: return f"lh {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x25: return f"lhu {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x20: return f"lb {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x24: return f"lbu {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x2B: return f"sw {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x29: return f"sh {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x28: return f"sb {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    elif op == 0x04: return f"beq {REGS[rs]},{REGS[rt]},0x{addr + 4 + imms*4:08X}"
    elif op == 0x05: return f"bne {REGS[rs]},{REGS[rt]},0x{addr + 4 + imms*4:08X}"
    elif op == 0x0A: return f"slti {REGS[rt]},{REGS[rs]},{imms}"
    elif op == 0x0B: return f"sltiu {REGS[rt]},{REGS[rs]},{imms}"
    elif op == 0x03: return f"jal 0x{(d['target'] << 2) | (addr & 0xF0000000):08X}"
    elif op == 0x02: return f"j 0x{(d['target'] << 2) | (addr & 0xF0000000):08X}"
    else: return f"op=0x{op:02X} rs={REGS[rs]} rt={REGS[rt]} imm=0x{imm:04X}"

    return f"unknown 0x{word:08X}"


def search_damage_immediates(data, file_start=0):
    """Search for MIPS instructions that load common damage values.

    Trap damage candidates: 5, 10, 15, 20, 25, 30, 40, 50, 100, 150, 200
    Look for: addiu $reg, $zero, value  OR  ori $reg, $zero, value
    """
    # Common trap damage values to search for
    damage_values = [5, 8, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200]

    results = {}
    for val in damage_values:
        results[val] = []

    for i in range(0, len(data) - 4, 4):
        word = struct.unpack_from('<I', data, i)[0]
        d = decode_mips(word)

        # addiu rt, $zero, value  (opcode=0x09, rs=0)
        if d['opcode'] == 0x09 and d['rs'] == 0 and d['imm_signed'] in damage_values:
            val = d['imm_signed']
            ram = file_to_ram(file_start + i)
            results[val].append({
                'offset': file_start + i,
                'ram': ram,
                'instr': f"addiu {REGS[d['rt']]},$zero,{val}",
                'word': word,
                'type': 'addiu'
            })

        # ori rt, $zero, value  (opcode=0x0D, rs=0)
        elif d['opcode'] == 0x0D and d['rs'] == 0 and d['imm'] in damage_values:
            val = d['imm']
            ram = file_to_ram(file_start + i)
            results[val].append({
                'offset': file_start + i,
                'ram': ram,
                'instr': f"ori {REGS[d['rt']]},$zero,{val}",
                'word': word,
                'type': 'ori'
            })

    return results


def search_hp_subtract_patterns(data, file_start=0):
    """Search for patterns that subtract from entity HP.

    HP is typically at entity+0x136 (current HP, uint16) or similar offsets.
    Look for:
      lh/lhu $reg, offset($base)  ; load HP
      ...
      subu $reg, $reg, $damage    ; subtract damage
      ...
      sh $reg, offset($base)      ; store HP

    Also look for direct: addiu $reg, $reg, -N (small negative = fixed damage)
    """
    matches = []

    # Known HP-related offsets from entity structure
    hp_offsets = [0x136, 0x138, 0x13A, 0x13C, 0x140, 0x142, 0x144, 0x146]

    for i in range(0, len(data) - 16, 4):
        # Pattern 1: subu followed by sh to HP offset
        word = struct.unpack_from('<I', data, i)[0]
        d = decode_mips(word)

        # R-type subu (opcode=0, funct=0x23)
        if d['opcode'] == 0 and d['funct'] == 0x23:
            # Check next 4 instructions for sh to HP offset
            for j in range(1, 5):
                if i + j*4 + 4 > len(data):
                    break
                w2 = struct.unpack_from('<I', data, i + j*4)[0]
                d2 = decode_mips(w2)
                if d2['opcode'] == 0x29 and d2['imm'] in hp_offsets:  # sh
                    ram = file_to_ram(file_start + i)
                    matches.append({
                        'offset': file_start + i,
                        'ram': ram,
                        'pattern': f"subu {REGS[d['rd']]},{REGS[d['rs']]},{REGS[d['rt']]} -> sh to +0x{d2['imm']:X}",
                        'gap': j,
                        'hp_offset': d2['imm'],
                    })
                    break

        # Pattern 2: addiu $reg, $reg, -N (small negative, direct damage)
        if d['opcode'] == 0x09 and d['imm_signed'] < 0 and d['imm_signed'] >= -500:
            neg_val = -d['imm_signed']
            # Check nearby for sh to HP offset
            for j in range(1, 5):
                if i + j*4 + 4 > len(data):
                    break
                w2 = struct.unpack_from('<I', data, i + j*4)[0]
                d2 = decode_mips(w2)
                if d2['opcode'] == 0x29 and d2['imm'] in hp_offsets:  # sh
                    ram = file_to_ram(file_start + i)
                    matches.append({
                        'offset': file_start + i,
                        'ram': ram,
                        'pattern': f"addiu {REGS[d['rt']]},{REGS[d['rs']]},-{neg_val} -> sh to +0x{d2['imm']:X}",
                        'gap': j,
                        'hp_offset': d2['imm'],
                    })
                    break

    return matches


def search_collision_damage_in_overlays(data):
    """Search BLAZE.ALL overlay code for trap-related damage patterns.

    Overlay code regions are at 0x009xxxxx - 0x02Cxxxxx in BLAZE.ALL.
    These contain per-dungeon gameplay code including chest timers.
    Trap damage logic may also be here.
    """
    # Same strategy as loot timer: search overlay regions
    overlay_start = 0x00900000
    overlay_end = min(0x02D00000, len(data))

    if overlay_start >= len(data):
        return []

    results = []
    damage_candidates = [5, 8, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100]

    for i in range(overlay_start, overlay_end - 16, 4):
        word = struct.unpack_from('<I', data, i)[0]
        d = decode_mips(word)

        # Look for: addiu/ori $reg, $zero, damage_value
        # followed within 4 instructions by: sh to offset 0x136-0x146 (HP area)
        is_li = False
        li_val = 0

        if d['opcode'] == 0x09 and d['rs'] == 0 and d['imm_signed'] in damage_candidates:
            is_li = True
            li_val = d['imm_signed']
        elif d['opcode'] == 0x0D and d['rs'] == 0 and d['imm'] in damage_candidates:
            is_li = True
            li_val = d['imm']

        if is_li:
            # Check context: is there a subu or sh nearby?
            for j in range(1, 8):
                if i + j*4 + 4 > overlay_end:
                    break
                w2 = struct.unpack_from('<I', data, i + j*4)[0]
                d2 = decode_mips(w2)

                # subu (R-type funct=0x23)
                if d2['opcode'] == 0 and d2['funct'] == 0x23:
                    results.append({
                        'offset': i,
                        'value': li_val,
                        'pattern': f"li {li_val} -> subu at +{j*4}",
                        'context_word': w2,
                    })
                    break

    return results


def context_dump(data, offset, count=8, file_start=0):
    """Dump instructions around an offset for context."""
    lines = []
    start = max(0, offset - count * 4)
    end = min(len(data), offset + count * 4)
    for i in range(start, end, 4):
        word = struct.unpack_from('<I', data, i)[0]
        ram = file_to_ram(file_start + i)
        marker = " >>>" if i == offset else "    "
        asm = disasm_simple(word, ram)
        lines.append(f"  {marker} 0x{ram:08X} (file+0x{file_start+i:06X}): {word:08X}  {asm}")
    return '\n'.join(lines)


def main():
    print("=" * 70)
    print("  Trap Damage Research - Phase 2.1: EXE Damage Pattern Search")
    print("=" * 70)

    # --- SECTION 1: Search SLES executable ---
    if SLES_PATH.exists():
        sles = SLES_PATH.read_bytes()
        print(f"\n  SLES: {SLES_PATH.name} ({len(sles):,} bytes)")

        print(f"\n  --- Damage immediate values in EXE ---")
        imm_results = search_damage_immediates(sles, 0)

        for val in sorted(imm_results.keys()):
            hits = imm_results[val]
            if hits:
                print(f"\n  Value {val}: {len(hits)} hits")
                for h in hits[:5]:
                    print(f"    0x{h['ram']:08X} (file 0x{h['offset']:06X}): {h['instr']}")
                if len(hits) > 5:
                    print(f"    ... and {len(hits)-5} more")

        print(f"\n  --- HP subtract patterns in EXE ---")
        hp_hits = search_hp_subtract_patterns(sles, 0)
        print(f"  Found {len(hp_hits)} subu/addiu-neg -> sh HP patterns")
        for h in hp_hits[:20]:
            print(f"    0x{h['ram']:08X}: {h['pattern']}")
        if len(hp_hits) > 20:
            print(f"    ... and {len(hp_hits)-20} more")

        # Show context around the most interesting HP subtract patterns
        if hp_hits:
            print(f"\n  --- Context for first 3 HP subtract patterns ---")
            for h in hp_hits[:3]:
                print(f"\n  At 0x{h['ram']:08X}:")
                print(context_dump(sles, h['offset'], 6, 0))

    else:
        print(f"  [SKIP] SLES not found: {SLES_PATH}")

    # --- SECTION 2: Search overlay code in BLAZE.ALL ---
    if BLAZE_ALL.exists():
        blaze = BLAZE_ALL.read_bytes()
        print(f"\n\n{'='*70}")
        print(f"  --- Overlay code damage patterns in BLAZE.ALL ---")
        print(f"  Searching overlays (0x00900000 - 0x02D00000)...")

        overlay_hits = search_collision_damage_in_overlays(blaze)
        print(f"  Found {len(overlay_hits)} 'li damage -> subu' patterns")

        # Group by value
        by_value = {}
        for h in overlay_hits:
            v = h['value']
            if v not in by_value:
                by_value[v] = []
            by_value[v].append(h)

        for val in sorted(by_value.keys()):
            hits = by_value[val]
            print(f"\n  Value {val}: {len(hits)} hits in overlays")
            for h in hits[:5]:
                print(f"    BLAZE 0x{h['offset']:08X}: {h['pattern']}")
            if len(hits) > 5:
                print(f"    ... and {len(hits)-5} more")

        # Show context for small number of hits (more likely to be actual damage)
        for val in sorted(by_value.keys()):
            hits = by_value[val]
            if 1 <= len(hits) <= 10:
                print(f"\n  --- Context for value {val} ({len(hits)} hits) ---")
                for h in hits[:3]:
                    print(f"\n  At BLAZE 0x{h['offset']:08X}:")
                    start = max(0, h['offset'] - 24)
                    end = min(len(blaze), h['offset'] + 32)
                    for off in range(start, end, 4):
                        w = struct.unpack_from('<I', blaze, off)[0]
                        marker = " >>>" if off == h['offset'] else "    "
                        asm = disasm_simple(w, 0x80010000 + off)  # fake RAM addr
                        print(f"  {marker} BLAZE+0x{off:08X}: {w:08X}  {asm}")
    else:
        print(f"  [SKIP] BLAZE.ALL not found: {BLAZE_ALL}")

    print(f"\n{'='*70}")
    print("  Search complete.")
    print("  NOTE: These are CANDIDATES - need in-game testing to confirm which")
    print("  values are actually trap damage vs other game mechanics.")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
