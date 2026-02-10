#!/usr/bin/env python3
"""
Phase 2.2: Analyze the suspected damage function at 0x8008A3E4
and trace ALL callers across overlays.

From the Phase 2.1 search, the pattern at BLAZE 0x0095713C is:
  addu $a0, $s1, $zero    ; entity pointer
  addiu $a1, $zero, 30    ; param1 = 30
  addiu $a2, $zero, 30    ; param2 = 30
  jal 0x8008A3E4          ; call damage function?
  addiu $a3, $zero, 30    ; param3 = 30 (delay slot)
  lhu $v0, 0x9A($s1)      ; load entity+0x9A
  lhu $v1, 0x5C($s1)      ; load entity+0x5C
  subu $v0, $v0, $v1      ; subtract
  sh $v0, 0x9A($s1)       ; store back

This looks like: call_damage($entity, 30, 30, 30) then subtract entity.field_5C from entity.field_9A

Let's find ALL callers of 0x8008A3E4 and related functions across all overlays,
and identify which overlay regions correspond to which dungeon areas.

Usage: py -3 WIP/TrapDamage/analyze_damage_function.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
SLES_PATH = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def disasm_simple(word, addr=0):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    imms = imm if imm < 0x8000 else imm - 0x10000
    tgt = word & 0x3FFFFFF

    if word == 0: return "nop"
    if op == 0:
        if funct == 0x21: return f"addu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x23: return f"subu {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x25: return f"or {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        if funct == 0x09: return f"jalr {REGS[rd]},{REGS[rs]}"
        if funct == 0x08: return f"jr {REGS[rs]}"
        if funct == 0x00:
            sa = (word >> 6) & 0x1F
            return f"sll {REGS[rd]},{REGS[rt]},{sa}"
        if funct == 0x03:
            sa = (word >> 6) & 0x1F
            return f"sra {REGS[rd]},{REGS[rt]},{sa}"
        return f"R-type funct=0x{funct:02X}"
    if op == 0x09: return f"addiu {REGS[rt]},{REGS[rs]},{imms}"
    if op == 0x0D: return f"ori {REGS[rt]},{REGS[rs]},0x{imm:04X}"
    if op == 0x0F: return f"lui {REGS[rt]},0x{imm:04X}"
    if op == 0x23: return f"lw {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x21: return f"lh {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x25: return f"lhu {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x20: return f"lb {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x24: return f"lbu {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x2B: return f"sw {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x29: return f"sh {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x28: return f"sb {REGS[rt]},0x{imm:04X}({REGS[rs]})"
    if op == 0x04: return f"beq {REGS[rs]},{REGS[rt]},0x{addr+4+imms*4:08X}"
    if op == 0x05: return f"bne {REGS[rs]},{REGS[rt]},0x{addr+4+imms*4:08X}"
    if op == 0x0A: return f"slti {REGS[rt]},{REGS[rs]},{imms}"
    if op == 0x0B: return f"sltiu {REGS[rt]},{REGS[rs]},{imms}"
    if op == 0x03: return f"jal 0x{(tgt << 2) | (addr & 0xF0000000):08X}"
    if op == 0x02: return f"j 0x{(tgt << 2) | (addr & 0xF0000000):08X}"
    if op == 0x01:
        if rt == 0: return f"bltz {REGS[rs]},0x{addr+4+imms*4:08X}"
        if rt == 1: return f"bgez {REGS[rs]},0x{addr+4+imms*4:08X}"
    return f"op=0x{op:02X} rs={REGS[rs]} rt={REGS[rt]} imm=0x{imm:04X}"


def find_jal_callers(data, target_ram, search_start, search_end):
    """Find all JAL instructions calling a specific RAM address."""
    # JAL encoding: opcode=0x03, target = (addr >> 2) & 0x3FFFFFF
    target_field = (target_ram >> 2) & 0x3FFFFFF
    jal_word = (0x03 << 26) | target_field

    callers = []
    for i in range(search_start, min(search_end, len(data) - 4), 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word == jal_word:
            callers.append(i)
    return callers


def extract_call_args(data, jal_offset, num_before=8):
    """Extract the arguments set up before a JAL call.

    Look backwards from the JAL for addiu/ori $a0-$a3 instructions.
    """
    args = {}
    for j in range(1, num_before + 1):
        off = jal_offset - j * 4
        if off < 0:
            break
        word = struct.unpack_from('<I', data, off)[0]
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000

        # addiu $aX, $zero, imm  (li)
        if op == 0x09 and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = {'value': imms, 'instr': f"addiu {REGS[rt]},$zero,{imms}"}

        # ori $aX, $zero, imm (li)
        elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = {'value': imm, 'instr': f"ori {REGS[rt]},$zero,0x{imm:04X}"}

        # addu $aX, $sY, $zero  (move from saved reg - entity pointer usually)
        elif op == 0 and (word & 0x3F) == 0x21 and 4 <= ((word >> 11) & 0x1F) <= 7:
            rd = (word >> 11) & 0x1F
            arg_name = f"$a{rd-4}"
            if arg_name not in args:
                args[arg_name] = {'value': f"={REGS[rs]}", 'instr': f"addu {REGS[rd]},{REGS[rs]},{REGS[rt]}"}

    # Also check delay slot (instruction AFTER jal)
    ds_off = jal_offset + 4
    if ds_off + 4 <= len(data):
        word = struct.unpack_from('<I', data, ds_off)[0]
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000

        if op == 0x09 and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = {'value': imms, 'instr': f"addiu {REGS[rt]},$zero,{imms} (delay)"}
        elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = {'value': imm, 'instr': f"ori {REGS[rt]},$zero,0x{imm:04X} (delay)"}

    return args


def identify_overlay_region(offset, data):
    """Try to identify which dungeon area an overlay offset belongs to.

    Overlay regions in BLAZE.ALL correspond to dungeon floor code.
    We can estimate by offset ranges.
    """
    # Known approximate ranges from previous research:
    ranges = [
        (0x0091_0000, 0x0097_0000, "Cavern overlays (early)"),
        (0x0097_0000, 0x009F_0000, "Cavern overlays (mid)"),
        (0x009F_0000, 0x00A0_0000, "Cavern overlays (late)"),
        (0x00A0_0000, 0x00B0_0000, "Spell tables / data"),
        (0x00BC_0000, 0x00BD_0000, "Unknown overlay B"),
        (0x00D0_0000, 0x00D1_0000, "Unknown overlay D"),
        (0x00DE_0000, 0x00DF_0000, "Unknown overlay DE"),
        (0x0148_0000, 0x014A_0000, "Forest overlays"),
        (0x0151_0000, 0x0152_0000, "Sealed Cave overlays"),
        (0x0196_0000, 0x0198_0000, "Tower overlays"),
        (0x01E8_0000, 0x01EA_0000, "Unknown overlay 1E8"),
        (0x0218_0000, 0x021A_0000, "Unknown overlay 218"),
        (0x023F_0000, 0x0244_0000, "Castle overlays"),
        (0x0251_0000, 0x0258_0000, "Hall/Ruins overlays"),
    ]
    for rstart, rend, name in ranges:
        if rstart <= offset < rend:
            return name
    return f"unknown region"


def main():
    print("=" * 70)
    print("  Trap Damage - Phase 2.2: Damage Function Analysis")
    print("=" * 70)

    if not BLAZE_ALL.exists():
        print(f"  [ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        return

    data = BLAZE_ALL.read_bytes()
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    # Target functions to trace
    target_functions = [
        0x8008A3E4,  # suspected damage/effect function (called with 30,30,30)
    ]

    # Also search for the common "100" patterns since they dominated the overlay results
    # First let's find ALL jal targets that are called with immediate damage-like args

    overlay_start = 0x00900000
    overlay_end = min(0x02D00000, len(data))

    print(f"\n{'='*70}")
    print(f"  SECTION 1: Callers of 0x8008A3E4 (suspected damage function)")
    print(f"{'='*70}")

    for target in target_functions:
        callers = find_jal_callers(data, target, overlay_start, overlay_end)
        print(f"\n  Function 0x{target:08X}: {len(callers)} callers in overlays")

        for c in callers:
            args = extract_call_args(data, c)
            region = identify_overlay_region(c, data)
            arg_str = ', '.join(f"{k}={v['value']}" for k, v in sorted(args.items()))
            print(f"    BLAZE+0x{c:08X} [{region}]: {arg_str}")

    # SECTION 2: Find the actual function body at the RAM address
    # 0x8008A3E4 is in OVERLAY code, not the main EXE
    # In overlay, the RAM base depends on which overlay is loaded
    # But the JAL target is absolute - let's search for it
    print(f"\n{'='*70}")
    print(f"  SECTION 2: Identify unique 'deal damage' JAL targets")
    print(f"{'='*70}")

    # Find all JAL instructions in overlays and count by target
    jal_targets = {}
    for i in range(overlay_start, overlay_end - 4, 4):
        word = struct.unpack_from('<I', data, i)[0]
        op = (word >> 26) & 0x3F
        if op == 0x03:  # jal
            target_field = word & 0x3FFFFFF
            ram_target = (target_field << 2) | 0x80000000
            if ram_target not in jal_targets:
                jal_targets[ram_target] = []
            jal_targets[ram_target].append(i)

    # Show the most-called functions (likely core engine functions)
    by_count = sorted(jal_targets.items(), key=lambda x: -len(x[1]))
    print(f"\n  Top 20 most-called functions from overlays:")
    for target, callers_list in by_count[:20]:
        print(f"    0x{target:08X}: {len(callers_list)} callers")

    # Focus on 0x8008A3E4 and nearby functions
    print(f"\n  Functions near 0x8008A3E4:")
    for target in sorted(jal_targets.keys()):
        if 0x8008A000 <= target <= 0x8008B000:
            print(f"    0x{target:08X}: {len(jal_targets[target])} callers")

    # SECTION 3: Analyze all callers that pass small integer args to suspected functions
    print(f"\n{'='*70}")
    print(f"  SECTION 3: JAL calls with small integer damage-like arguments")
    print(f"{'='*70}")

    # Focus on functions that are called with explicit small integers (1-200)
    # in $a1/$a2/$a3 (damage parameters)
    damage_calls = []
    for i in range(overlay_start, overlay_end - 4, 4):
        word = struct.unpack_from('<I', data, i)[0]
        op = (word >> 26) & 0x3F
        if op != 0x03:  # not jal
            continue

        target_field = word & 0x3FFFFFF
        ram_target = (target_field << 2) | 0x80000000

        args = extract_call_args(data, i)

        # Look for calls where $a1, $a2, or $a3 are small integers (damage candidates)
        has_damage_arg = False
        for arg_name in ['$a1', '$a2', '$a3']:
            if arg_name in args:
                val = args[arg_name]['value']
                if isinstance(val, int) and 1 <= val <= 200:
                    has_damage_arg = True
                    break

        if has_damage_arg:
            damage_calls.append({
                'offset': i,
                'target': ram_target,
                'args': args,
            })

    print(f"  Found {len(damage_calls)} JAL calls with small int args in $a1-$a3")

    # Group by target function
    by_target = {}
    for dc in damage_calls:
        t = dc['target']
        if t not in by_target:
            by_target[t] = []
        by_target[t].append(dc)

    print(f"  Across {len(by_target)} unique target functions\n")

    # Show functions called with damage-like args, sorted by caller count
    for target, calls in sorted(by_target.items(), key=lambda x: -len(x[1])):
        if len(calls) < 2:
            continue
        # Collect unique arg values
        arg_values = set()
        for c in calls:
            for aname in ['$a1', '$a2', '$a3']:
                if aname in c['args'] and isinstance(c['args'][aname]['value'], int):
                    arg_values.add(c['args'][aname]['value'])

        # Only show if has reasonable damage values
        if any(1 <= v <= 200 for v in arg_values):
            print(f"  0x{target:08X} ({len(calls)} callers) - arg values: {sorted(arg_values)}")
            for c in calls[:8]:
                region = identify_overlay_region(c['offset'], data)
                arg_str = ', '.join(f"{k}={v['value']}" for k, v in sorted(c['args'].items()))
                print(f"    BLAZE+0x{c['offset']:08X} [{region}]: {arg_str}")
            if len(calls) > 8:
                print(f"    ... and {len(calls)-8} more")
            print()

    print(f"{'='*70}")
    print("  Analysis complete.")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
