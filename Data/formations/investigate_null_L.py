#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Investigate NULL L entries in the script area root offset tables.

Questions:
1. When L=1 is NULL, what does the engine do?
2. Is L=1 ALWAYS NULL for Goblin-Shaman across all areas?
3. How does the bytecode interpreter handle NULL root table entries?
4. Are there OTHER monsters with NULL L entries?

Reads:
- BLAZE.ALL for script area root offset tables
- All spawn group JSONs for area definitions
- All formation JSONs for assignment_entries (L values)
- PSX executable (SLES_008.45) from BIN for bytecode interpreter code
"""

import struct
import json
import os
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SPAWN_GROUPS_DIR = PROJECT_ROOT / "WIP" / "level_design" / "spawns" / "data" / "spawn_groups"

BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = (PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)"
                 / "extract" / "BLAZE.ALL")

# BIN file for extracting PSX executable
BIN_FILE = (PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)"
            / "Blaze & Blade - Eternal Quest (Europe).bin")

# PSX executable location
SLES_LBA = 295081
SECTOR_SIZE = 2352
SECTOR_HEADER = 24
SECTOR_DATA = 2048

# Bytecode interpreter address
INTERPRETER_ADDR = 0x8001A03C
# PSX RAM base for executables
PSX_RAM_BASE = 0x80010000
# File offset in EXE = addr - PSX_RAM_BASE
# But we also need to extract from BIN first

SEP = "=" * 78
SEP2 = "-" * 78


def r32(d, o):
    """Read uint32 LE."""
    if o + 4 <= len(d):
        return struct.unpack_from('<I', d, o)[0]
    return None


def r16(d, o):
    """Read uint16 LE."""
    if o + 2 <= len(d):
        return struct.unpack_from('<H', d, o)[0]
    return None


def extract_sles_from_bin():
    """Extract SLES_008.45 from the BIN file."""
    if not BIN_FILE.exists():
        print("  WARNING: BIN file not found at %s" % BIN_FILE)
        return None

    exe_data = bytearray()
    # Read sectors starting at SLES_LBA
    # SLES_008.45 is ~824KB = ~413 sectors
    num_sectors = 420  # a bit more than needed
    with open(BIN_FILE, 'rb') as f:
        for i in range(num_sectors):
            sector_pos = (SLES_LBA + i) * SECTOR_SIZE
            f.seek(sector_pos + SECTOR_HEADER)
            exe_data.extend(f.read(SECTOR_DATA))

    print("  Extracted %d bytes from BIN (LBA %d, %d sectors)" %
          (len(exe_data), SLES_LBA, num_sectors))
    return bytes(exe_data)


def disasm_mips_basic(word):
    """Very basic MIPS disassembly for common instructions."""
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000

    regs = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
            "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
            "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
            "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]

    if word == 0:
        return "nop"

    if op == 0:  # SPECIAL
        funct = word & 0x3F
        sa = (word >> 6) & 0x1F
        if funct == 0x21:
            return "addu   $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x20:
            return "add    $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x25:
            return "or     $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x00:
            return "sll    $%s, $%s, %d" % (regs[rd], regs[rt], sa)
        elif funct == 0x02:
            return "srl    $%s, $%s, %d" % (regs[rd], regs[rt], sa)
        elif funct == 0x08:
            return "jr     $%s" % regs[rs]
        elif funct == 0x09:
            return "jalr   $%s" % regs[rs]
        elif funct == 0x2A:
            return "slt    $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x2B:
            return "sltu   $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x24:
            return "and    $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x23:
            return "subu   $%s, $%s, $%s" % (regs[rd], regs[rs], regs[rt])
        elif funct == 0x03:
            return "sra    $%s, $%s, %d" % (regs[rd], regs[rt], sa)
        elif funct == 0x04:
            return "sllv   $%s, $%s, $%s" % (regs[rd], regs[rt], regs[rs])
        else:
            return "special func=0x%02X  $%s,$%s,$%s" % (funct, regs[rd], regs[rs], regs[rt])
    elif op == 0x09:
        return "addiu  $%s, $%s, %d" % (regs[rt], regs[rs], simm)
    elif op == 0x0C:
        return "andi   $%s, $%s, 0x%X" % (regs[rt], regs[rs], imm)
    elif op == 0x0D:
        return "ori    $%s, $%s, 0x%X" % (regs[rt], regs[rs], imm)
    elif op == 0x0F:
        return "lui    $%s, 0x%04X" % (regs[rt], imm)
    elif op == 0x23:
        return "lw     $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x2B:
        return "sw     $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x20:
        return "lb     $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x24:
        return "lbu    $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x21:
        return "lh     $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x25:
        return "lhu    $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x28:
        return "sb     $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x29:
        return "sh     $%s, %d($%s)" % (regs[rt], simm, regs[rs])
    elif op == 0x04:
        target = simm  # branch offset
        return "beq    $%s, $%s, %+d" % (regs[rs], regs[rt], simm)
    elif op == 0x05:
        return "bne    $%s, $%s, %+d" % (regs[rs], regs[rt], simm)
    elif op == 0x06:
        return "blez   $%s, %+d" % (regs[rs], simm)
    elif op == 0x07:
        return "bgtz   $%s, %+d" % (regs[rs], simm)
    elif op == 0x0A:
        return "slti   $%s, $%s, %d" % (regs[rt], regs[rs], simm)
    elif op == 0x0B:
        return "sltiu  $%s, $%s, %d" % (regs[rt], regs[rs], simm)
    elif op == 0x03:
        return "jal    0x%08X" % ((word & 0x03FFFFFF) << 2 | 0x80000000)
    elif op == 0x02:
        return "j      0x%08X" % ((word & 0x03FFFFFF) << 2 | 0x80000000)
    elif op == 0x01:
        if rt == 0:
            return "bltz   $%s, %+d" % (regs[rs], simm)
        elif rt == 1:
            return "bgez   $%s, %+d" % (regs[rs], simm)
        else:
            return "regimm rt=%d $%s, %+d" % (rt, regs[rs], simm)
    else:
        return "op=0x%02X rt=$%s rs=$%s imm=0x%04X" % (op, regs[rt], regs[rs], imm)


def parse_root_table(chunk, script_size):
    """Parse root offset table from start of script area chunk.

    The table is a sequence of uint32 LE values, terminated by 2+ consecutive zeros.
    Returns (entries, table_end_offset).
    """
    entries = []
    consecutive_zeros = 0
    for i in range(0, min(script_size, 256), 4):  # Max 64 entries
        v = r32(chunk, i)
        if v is None:
            break
        if v == 0:
            consecutive_zeros += 1
            entries.append(v)
            if consecutive_zeros >= 2:
                # Remove trailing zeros
                while entries and entries[-1] == 0:
                    entries.pop()
                break
        else:
            consecutive_zeros = 0
            # Sanity check: offsets should be within the script chunk
            if v > script_size + 0x1000:
                # Probably past the table
                break
            entries.append(v)
    table_end = (len(entries) + consecutive_zeros) * 4
    return entries, table_end


def load_spawn_groups():
    """Load all spawn group JSONs."""
    levels = {}
    for fname in sorted(os.listdir(SPAWN_GROUPS_DIR)):
        if not fname.endswith('.json'):
            continue
        with open(SPAWN_GROUPS_DIR / fname, 'r') as f:
            data = json.load(f)
        level_name = data.get('level_name', fname.replace('.json', ''))
        level_key = fname.replace('.json', '')
        groups = []
        for g in data['groups']:
            groups.append({
                'name': g['name'],
                'offset': int(g['offset'], 16),
                'monsters': g['monsters'],
            })
        groups.sort(key=lambda x: x['offset'])
        levels[level_key] = {
            'level_name': level_name,
            'groups': groups,
        }
    return levels


def load_assignment_entries():
    """Load assignment_entries (L values) from all formation JSONs."""
    assignments = {}  # key = group_offset_hex -> list of {slot, L, R}
    formations_dir = SCRIPT_DIR

    for dirpath, dirnames, filenames in os.walk(formations_dir):
        for fname in filenames:
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, 'r') as f:
                data = json.load(f)
            if 'assignment_entries' not in data:
                continue
            group_off = data.get('group_offset', '')
            if group_off:
                assignments[group_off] = {
                    'monsters': data.get('monsters', []),
                    'entries': data['assignment_entries'],
                    'level_name': data.get('level_name', ''),
                    'area_name': data.get('name', ''),
                }
    return assignments


def main():
    print(SEP)
    print("INVESTIGATION: NULL L Entries in Script Area Root Offset Tables")
    print(SEP)
    print()

    # ================================================================
    # PART 1: Load all data
    # ================================================================
    print("--- Loading data ---")
    print()

    blaze_data = BLAZE_ALL.read_bytes()
    print("  BLAZE.ALL: %d bytes from %s" % (len(blaze_data), BLAZE_ALL))

    levels = load_spawn_groups()
    total_areas = sum(len(v['groups']) for v in levels.values())
    print("  Spawn groups: %d levels, %d areas" % (len(levels), total_areas))

    assignments = load_assignment_entries()
    print("  Assignment entries loaded for %d areas" % len(assignments))
    print()

    # ================================================================
    # PART 2: Scan all areas for root offset tables
    # ================================================================
    print(SEP)
    print("PART 2: Root Offset Table Scan - All Areas")
    print(SEP)
    print()

    # Collect results for cross-referencing
    all_results = []

    # Track NULL L values by monster name
    null_by_monster = defaultdict(list)    # monster_name -> [area descriptions]
    valid_by_monster = defaultdict(list)   # monster_name -> [area descriptions]
    null_L_by_value = defaultdict(list)    # L_value -> [area descriptions]

    for level_key, level_data in sorted(levels.items()):
        level_name = level_data['level_name']
        groups = level_data['groups']

        for i, group in enumerate(groups):
            offset = group['offset']
            num_monsters = len(group['monsters'])
            monsters = group['monsters']

            # Get assignment entries (L values) from formation JSONs
            group_hex = "0x%X" % offset
            assign_data = assignments.get(group_hex, None)

            if assign_data is None:
                # Try to find by scanning
                for k, v in assignments.items():
                    if int(k, 16) == offset:
                        assign_data = v
                        break

            # Compute script area bounds
            script_start = offset + num_monsters * 96
            # Estimate script area end (use next group or +16KB)
            if i + 1 < len(groups):
                next_offset = groups[i + 1]['offset']
                # Script area is between entries end and the next group's start
                # But we need to find the actual end
                scan_end = next_offset
            else:
                scan_end = script_start + 16384  # generous upper bound

            if scan_end > len(blaze_data):
                scan_end = len(blaze_data)

            chunk = blaze_data[script_start:scan_end]
            script_size = len(chunk)

            if script_size < 16:
                continue

            # Parse root offset table
            root_entries, table_end = parse_root_table(chunk, script_size)

            if not root_entries:
                continue

            # Get L values from assignment entries
            l_values = {}  # slot -> L value
            l_to_monster = {}  # L -> monster name
            if assign_data:
                for entry in assign_data['entries']:
                    slot = entry['slot']
                    L = entry['L']
                    l_values[slot] = L
                    if slot < len(monsters):
                        l_to_monster[L] = monsters[slot]

            # Determine which L values are NULL vs valid in root table
            max_L = max(l_values.values()) if l_values else (len(root_entries) - 1)

            area_desc = "%s / %s" % (level_name, group['name'])

            area_result = {
                'level': level_name,
                'area': group['name'],
                'area_desc': area_desc,
                'offset': offset,
                'num_monsters': num_monsters,
                'monsters': monsters,
                'root_entries': root_entries,
                'l_values': l_values,
                'l_to_monster': l_to_monster,
                'null_L': [],
                'valid_L': [],
            }

            for slot_idx in range(num_monsters):
                L = l_values.get(slot_idx, slot_idx)
                monster = monsters[slot_idx] if slot_idx < len(monsters) else "?"

                if L < len(root_entries):
                    val = root_entries[L]
                    if val == 0:
                        area_result['null_L'].append((L, slot_idx, monster))
                        null_by_monster[monster].append(area_desc)
                        null_L_by_value[L].append(area_desc)
                    else:
                        area_result['valid_L'].append((L, slot_idx, monster, val))
                        valid_by_monster[monster].append(area_desc)
                else:
                    # L value exceeds root table size - treat as implicit NULL
                    area_result['null_L'].append((L, slot_idx, monster))
                    null_by_monster[monster].append(area_desc + " (L>table)")
                    null_L_by_value[L].append(area_desc + " (L>table)")

            all_results.append(area_result)

    # ================================================================
    # PART 3: Print detailed results per area
    # ================================================================
    print(SEP)
    print("PART 3: Detailed Results - Areas with NULL L entries")
    print(SEP)
    print()

    areas_with_null = [r for r in all_results if r['null_L']]
    areas_without_null = [r for r in all_results if not r['null_L']]

    print("Areas with NULL L entries: %d / %d total" %
          (len(areas_with_null), len(all_results)))
    print("Areas without NULL L entries: %d / %d total" %
          (len(areas_without_null), len(all_results)))
    print()

    for r in areas_with_null:
        print("  %s" % r['area_desc'])
        print("    Monsters: %s" % ', '.join(r['monsters']))
        print("    Root table (%d entries): %s" % (
            len(r['root_entries']),
            ', '.join('0x%X' % v for v in r['root_entries'])))

        for L, slot, monster in r['null_L']:
            print("    ** NULL ** L=%d  slot=%d  monster=%s" % (L, slot, monster))
        for L, slot, monster, val in r['valid_L']:
            print("       VALID  L=%d  slot=%d  monster=%-20s -> offset=+0x%X" %
                  (L, slot, monster, val))
        print()

    # ================================================================
    # PART 4: Cross-reference by monster name
    # ================================================================
    print(SEP)
    print("PART 4: NULL L Cross-Reference by Monster Name")
    print(SEP)
    print()

    # Find monsters that appear in BOTH null and valid
    all_monster_names = sorted(set(list(null_by_monster.keys()) +
                                   list(valid_by_monster.keys())))

    for monster in all_monster_names:
        null_count = len(null_by_monster.get(monster, []))
        valid_count = len(valid_by_monster.get(monster, []))

        if null_count == 0:
            continue

        if valid_count == 0:
            status = "ALWAYS NULL"
        else:
            status = "MIXED (%d null, %d valid)" % (null_count, valid_count)

        print("  %-25s %s" % (monster, status))
        if null_count > 0:
            for desc in null_by_monster[monster][:5]:
                print("    NULL in: %s" % desc)
            if null_count > 5:
                print("    ... and %d more" % (null_count - 5))
        if valid_count > 0:
            for desc in valid_by_monster[monster][:3]:
                print("    VALID in: %s" % desc)
            if valid_count > 3:
                print("    ... and %d more" % (valid_count - 3))
        print()

    # ================================================================
    # PART 5: NULL L by value
    # ================================================================
    print(SEP)
    print("PART 5: NULL L Cross-Reference by L Value")
    print(SEP)
    print()

    for L_val in sorted(null_L_by_value.keys()):
        areas = null_L_by_value[L_val]
        print("  L=%d: NULL in %d areas" % (L_val, len(areas)))
        for desc in areas[:8]:
            print("    - %s" % desc)
        if len(areas) > 8:
            print("    ... and %d more" % (len(areas) - 8))
        print()

    # ================================================================
    # PART 6: Examine specific Cavern F1 Area 1 root table in detail
    # ================================================================
    print(SEP)
    print("PART 6: Detailed Hex Dump - Cavern F1 Area 1 Script Area Root")
    print(SEP)
    print()

    # Cavern F1 Area 1: script starts at 0xF7A97C + 3*96 = 0xF7AA9C
    cav_script = 0xF7AA9C
    chunk = blaze_data[cav_script:cav_script + 256]
    print("  Script area at 0x%08X:" % cav_script)
    print("  Root table entries (uint32 LE):")
    for i in range(0, 64, 4):
        v = r32(chunk, i)
        print("    [%2d] +0x%03X = 0x%08X  (%d)" % (i // 4, i, v, v))
        # Stop if we hit two consecutive zeros
        if i >= 4 and v == 0 and r32(chunk, i - 4) == 0:
            break
    print()

    # Also do Cavern F1 Area 2 for comparison
    cav2_script = 0xF7E1A8 + 4 * 96  # 0xF7E318
    chunk2 = blaze_data[cav2_script:cav2_script + 256]
    print("  Cavern F1 Area 2 - Script area at 0x%08X:" % cav2_script)
    print("  Root table entries (uint32 LE):")
    for i in range(0, 80, 4):
        v = r32(chunk2, i)
        print("    [%2d] +0x%03X = 0x%08X  (%d)" % (i // 4, i, v, v))
        if i >= 4 and v == 0 and r32(chunk2, i - 4) == 0:
            break
    print()

    # ================================================================
    # PART 7: PSX Executable Analysis - Bytecode interpreter NULL handler
    # ================================================================
    print(SEP)
    print("PART 7: PSX Executable Analysis - How NULL L Entries Are Handled")
    print(SEP)
    print()

    exe_data = extract_sles_from_bin()
    if exe_data:
        # The bytecode interpreter is at 0x8001A03C
        # PSX RAM: executable loads at 0x80010000
        # But the EXE file has an 0x800 header before the code
        # Actually, SLES EXE format: header at offset 0, code starts after header
        # Standard PS1 EXE header: 0x800 bytes
        # Load address is at offset 0x18 in the header
        # Usually 0x80010000

        # Check the header
        magic = exe_data[0:8]
        print("  EXE magic: %s" % magic[:8])

        # Find the load address
        if len(exe_data) > 0x20:
            load_addr = r32(exe_data, 0x18)
            print("  Load address: 0x%08X" % load_addr)
            exe_size = r32(exe_data, 0x1C)
            print("  EXE size: 0x%X (%d bytes)" % (exe_size, exe_size))

            # Code offset in file = addr - load_addr + 0x800 (header)
            header_size = 0x800

            # Now look for the code that loads from the root offset table
            # The root table is indexed by L value. The engine would do:
            #   offset = root_table[L]   (lw from base + L*4)
            #   if offset == 0: <handle NULL>
            #   else: <use offset>
            #
            # We want to find the "beq $reg, $zero" or similar after loading
            # from the table.

            # Look around the bytecode interpreter at 0x8001A03C
            interp_file_off = INTERPRETER_ADDR - load_addr + header_size
            print("  Bytecode interpreter at 0x%08X -> file offset 0x%X" %
                  (INTERPRETER_ADDR, interp_file_off))
            print()

            # Disassemble a wide region around the interpreter
            # to find root table loading code
            print("  Disassembly around bytecode interpreter (0x8001A03C):")
            print()

            start_off = interp_file_off
            # Show 128 instructions (512 bytes)
            for j in range(128):
                off = start_off + j * 4
                if off + 4 > len(exe_data):
                    break
                word = r32(exe_data, off)
                addr = INTERPRETER_ADDR + j * 4
                asm = disasm_mips_basic(word)
                print("    0x%08X: %08X  %s" % (addr, word, asm))
            print()

            # Now search for patterns related to root table NULL check.
            # The engine likely does something like:
            #   lw reg, offset(base)   ; load root_table[L]
            #   beq reg, zero, skip    ; if NULL, skip/fallback
            #
            # Or it might add the offset to a base and jump unconditionally,
            # which would crash/do nothing if offset=0 (jumps to base+0).
            #
            # Search more broadly for "beq $xx, $zero" after an "sll" (L*4) + "addu" + "lw"
            print("  Searching for root table load + NULL check patterns...")
            print()

            # Search in a wide range around the interpreter and its callers
            search_start = header_size
            search_end = min(len(exe_data), header_size + 0x40000)

            # Find patterns: sll $X, $Y, 2  (multiply by 4 for table index)
            # followed within 4 instructions by lw + beq
            hits = []
            for off in range(search_start, search_end - 32, 4):
                w = r32(exe_data, off)
                if w is None:
                    continue

                # Check for sll $rd, $rt, 2 (shift left by 2 = multiply by 4)
                op = (w >> 26) & 0x3F
                if op != 0:
                    continue
                funct = w & 0x3F
                sa = (w >> 6) & 0x1F
                if funct != 0 or sa != 2:
                    continue

                rd = (w >> 11) & 0x1F
                rt = (w >> 16) & 0x1F

                # Look at the next 8 instructions for: addu + lw + beq/bne with zero
                for k in range(1, 9):
                    w2 = r32(exe_data, off + k * 4)
                    if w2 is None:
                        break
                    op2 = (w2 >> 26) & 0x3F
                    # Check for beq $X, $zero
                    if op2 == 0x04:
                        rs2 = (w2 >> 21) & 0x1F
                        rt2 = (w2 >> 16) & 0x1F
                        if rt2 == 0:  # beq $rs, $zero
                            # Found a potential pattern
                            addr_sll = load_addr + (off - header_size)
                            addr_beq = load_addr + (off + k * 4 - header_size)
                            # Check if there's a lw between sll and beq
                            has_lw = False
                            for m in range(1, k):
                                wm = r32(exe_data, off + m * 4)
                                if wm and (wm >> 26) & 0x3F == 0x23:  # lw
                                    has_lw = True
                                    break
                            if has_lw:
                                hits.append((off, k, addr_sll, addr_beq))

            print("  Found %d sll-by-2 + lw + beq-zero patterns" % len(hits))
            # Show the most interesting ones (near the interpreter or in known AI code)
            interesting = []
            for off, k, addr_sll, addr_beq in hits:
                # Filter to be near known AI code regions
                if (0x8001A000 <= addr_sll <= 0x8002C000 or
                    0x80030000 <= addr_sll <= 0x80040000):
                    interesting.append((off, k, addr_sll, addr_beq))

            if interesting:
                print("  Interesting hits (near AI code):")
                for off, k, addr_sll, addr_beq in interesting[:20]:
                    print()
                    print("    Pattern at 0x%08X:" % addr_sll)
                    for j in range(-1, k + 3):
                        fo = off + j * 4
                        if 0 <= fo < len(exe_data) - 4:
                            w = r32(exe_data, fo)
                            a = load_addr + (fo - header_size)
                            asm = disasm_mips_basic(w)
                            marker = " <--" if j == 0 else (" <-- NULL check" if j == k else "")
                            print("      0x%08X: %08X  %s%s" % (a, w, asm, marker))
            else:
                print("  No interesting hits near AI code region.")

            print()

            # Also look at how the script area is first loaded/parsed
            # The script area offset table is probably loaded by the area
            # initialization code. Search for references to known script area
            # addresses or patterns.

            # Search for code that branches on zero after loading from
            # a pointer + index*4 pattern (the root table access pattern)
            print("  --- Additional search: lw + beq zero sequences ---")
            print()

            # Look specifically at the opcode dispatch area and the init code
            # mentioned in MEMORY.md: 0x8002B630 and 0x8002A788
            for label, addr_to_check in [
                ("Init code 0x8002B630", 0x8002B630),
                ("Init code 0x8002A788", 0x8002A788),
                ("Opcode 0x18 handler", 0x8001C218),
            ]:
                fo = addr_to_check - load_addr + header_size
                if 0 <= fo < len(exe_data) - 128:
                    print("  %s (0x%08X):" % (label, addr_to_check))
                    for j in range(32):
                        off2 = fo + j * 4
                        if off2 + 4 > len(exe_data):
                            break
                        w = r32(exe_data, off2)
                        a = addr_to_check + j * 4
                        asm = disasm_mips_basic(w)
                        print("    0x%08X: %08X  %s" % (a, w, asm))
                    print()

    # ================================================================
    # PART 8: What happens when L entry is NULL - Trace the data flow
    # ================================================================
    print(SEP)
    print("PART 8: Analysis - What Happens When Root Table[L] = 0")
    print(SEP)
    print()

    # Look at the actual bytes around NULL entries in the root table
    # to understand what data they would point to (offset 0 = start of script chunk)
    for r in areas_with_null[:5]:
        area_desc = r['area_desc']
        offset = r['offset']
        num_monsters = r['num_monsters']
        script_start = offset + num_monsters * 96
        root = r['root_entries']

        print("  %s (script at 0x%08X):" % (area_desc, script_start))
        print("    Root table: %s" % ', '.join(
            'NULL' if v == 0 else '0x%X' % v for v in root))

        # For NULL entries, the bytecode would potentially load offset 0
        # which points to... the start of the root table itself!
        # OR the engine checks for NULL and skips.
        #
        # Let's see what the FIRST valid entry points to, and whether
        # offset 0 (which would be the root table) is meaningful.

        chunk = blaze_data[script_start:script_start + 512]

        print("    First 32 bytes of script area (= what offset 0 points to):")
        hexdump = ' '.join('%02X' % b for b in chunk[:32])
        print("      %s" % hexdump)

        # Show what each valid entry points to
        for L, slot, monster, val in r['valid_L']:
            data_at_offset = blaze_data[script_start + val:script_start + val + 16]
            hexdump = ' '.join('%02X' % b for b in data_at_offset)
            print("    L=%d (%s) -> +0x%X: %s" % (L, monster, val, hexdump))

        print()

    # ================================================================
    # PART 9: Summary and Conclusions
    # ================================================================
    print(SEP)
    print("PART 9: Summary and Conclusions")
    print(SEP)
    print()

    # Count statistics
    total_null = sum(len(r['null_L']) for r in all_results)
    total_valid = sum(len(r['valid_L']) for r in all_results)

    print("  Total NULL L entries across all areas: %d" % total_null)
    print("  Total valid L entries across all areas: %d" % total_valid)
    print()

    print("  Monsters that ALWAYS have NULL L entries:")
    for monster in sorted(null_by_monster.keys()):
        if monster not in valid_by_monster:
            print("    - %s (NULL in %d areas)" %
                  (monster, len(null_by_monster[monster])))

    print()
    print("  Monsters that SOMETIMES have NULL L entries:")
    for monster in sorted(null_by_monster.keys()):
        if monster in valid_by_monster:
            print("    - %s (NULL in %d areas, valid in %d areas)" %
                  (monster, len(null_by_monster[monster]),
                   len(valid_by_monster[monster])))

    print()
    print("  Monsters that NEVER have NULL L entries:")
    for monster in sorted(valid_by_monster.keys()):
        if monster not in null_by_monster:
            print("    - %s (valid in %d areas)" %
                  (monster, len(valid_by_monster[monster])))

    print()
    print("Done.")


if __name__ == '__main__':
    main()
