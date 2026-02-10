#!/usr/bin/env python3
"""
Phase 3.1: Test trap damage modification in BLAZE.ALL overlay code.

Strategy: The stat modifier function 0x8008A3E4 is called with signed
triplets ($a1, $a2, $a3). Negative values = damage/debuff, positive = heal/buff.

This script finds ALL callers with negative args and modifies them to test
if they correspond to trap damage. The modification options are:
  - NOP: replace the JAL with NOP (no damage at all)
  - MULTIPLY: change the immediate values to multiply damage

The callers are in overlay code stored in BLAZE.ALL (0x0091-0x0096 range).
The overlay is loaded into RAM dynamically per dungeon floor.

Usage: py -3 WIP/TrapDamage/test_trap_modify.py [--mode nop|multiply] [--factor N]
"""

import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

NOP_WORD = 0x00000000

# Stat modifier functions to target
STAT_MOD_FUNCTIONS = [
    0x8008A3E4,  # main: 58 callers, takes (entity, a1, a2, a3) stat deltas
]

# Search range in BLAZE.ALL overlay code
OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000


def find_jal_callers(data, target_ram, search_start, search_end):
    target_field = (target_ram >> 2) & 0x3FFFFFF
    jal_word = (0x03 << 26) | target_field
    callers = []
    for i in range(search_start, min(search_end, len(data) - 4), 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word == jal_word:
            callers.append(i)
    return callers


def extract_arg_immediates(data, jal_offset):
    """Extract immediate values set for $a0-$a3 before a JAL call.

    Returns dict of {reg_index: (immediate_value, instruction_offset)}.
    """
    args = {}
    # Check 10 instructions before JAL
    for j in range(1, 11):
        off = jal_offset - j * 4
        if off < 0:
            break
        word = struct.unpack_from('<I', data, off)[0]
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000

        # addiu rt, $zero, imm  (li pseudo)
        if op == 0x09 and rs == 0 and 4 <= rt <= 7:
            arg_idx = rt - 4
            if arg_idx not in args:
                args[arg_idx] = (imms, off, 'addiu')

        # ori rt, $zero, imm  (li pseudo)
        elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
            arg_idx = rt - 4
            if arg_idx not in args:
                args[arg_idx] = (imm, off, 'ori')

    # Check delay slot
    ds_off = jal_offset + 4
    if ds_off + 4 <= len(data):
        word = struct.unpack_from('<I', data, ds_off)[0]
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000

        if op == 0x09 and rs == 0 and 4 <= rt <= 7:
            arg_idx = rt - 4
            if arg_idx not in args:
                args[arg_idx] = (imms, ds_off, 'addiu')
        elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
            arg_idx = rt - 4
            if arg_idx not in args:
                args[arg_idx] = (imm, ds_off, 'ori')

    return args


def make_li_instruction(reg_idx, value, use_addiu=True):
    """Create addiu $reg, $zero, value  or  ori $reg, $zero, value."""
    rt = reg_idx + 4  # $a0=4, $a1=5, etc.
    if use_addiu:
        # addiu rt, $zero, imm_signed
        if value < 0:
            imm = value & 0xFFFF
        else:
            imm = value & 0xFFFF
        return (0x09 << 26) | (0 << 21) | (rt << 16) | imm
    else:
        # ori rt, $zero, value
        return (0x0D << 26) | (0 << 21) | (rt << 16) | (value & 0xFFFF)


def main():
    mode = 'nop'
    factor = 2

    # Parse args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--mode' and i + 1 < len(args):
            mode = args[i+1]
            i += 2
        elif args[i] == '--factor' and i + 1 < len(args):
            factor = int(args[i+1])
            i += 2
        else:
            i += 1

    print("=" * 70)
    print("  Trap Damage - Phase 3.1: Test Trap Modification")
    print(f"  Mode: {mode}, Factor: {factor}")
    print("=" * 70)

    if not BLAZE_SRC.exists():
        print(f"  [ERROR] Source BLAZE.ALL not found: {BLAZE_SRC}")
        return

    # Start from source (unpatched)
    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  Source: {BLAZE_SRC.name} ({len(data):,} bytes)")

    # Find all callers
    all_callers = []
    for func in STAT_MOD_FUNCTIONS:
        callers = find_jal_callers(data, func, OVERLAY_START, min(OVERLAY_END, len(data)))
        for c in callers:
            arg_info = extract_arg_immediates(data, c)
            all_callers.append({
                'offset': c,
                'function': func,
                'args': arg_info,
            })

    print(f"  Found {len(all_callers)} stat modifier calls in overlays")

    # Classify callers
    damage_callers = []
    heal_callers = []
    other_callers = []

    for caller in all_callers:
        has_neg = False
        has_pos = False
        for idx, (val, off, typ) in caller['args'].items():
            if idx in [1, 2, 3]:  # $a1, $a2, $a3
                if val < 0:
                    has_neg = True
                elif val > 0:
                    has_pos = True

        if has_neg:
            damage_callers.append(caller)
        elif has_pos:
            heal_callers.append(caller)
        else:
            other_callers.append(caller)

    print(f"  Damage callers: {len(damage_callers)}")
    print(f"  Heal callers: {len(heal_callers)}")
    print(f"  Other callers: {len(other_callers)}")

    if not damage_callers:
        print("  [WARN] No damage callers found! Nothing to modify.")
        return

    # Show all damage callers
    print(f"\n  --- ALL DAMAGE CALLERS ---")
    for caller in damage_callers:
        args_str = []
        for idx in range(4):
            if idx in caller['args']:
                val, off, typ = caller['args'][idx]
                args_str.append(f"$a{idx}={val}")
        print(f"    BLAZE+0x{caller['offset']:08X}: {', '.join(args_str)}")

    # Apply modifications
    patched_count = 0

    if mode == 'nop':
        print(f"\n  --- APPLYING NOP to all damage JAL calls ---")
        for caller in damage_callers:
            old_word = struct.unpack_from('<I', data, caller['offset'])[0]
            struct.pack_into('<I', data, caller['offset'], NOP_WORD)
            patched_count += 1
            args_str = []
            for idx in [1, 2, 3]:
                if idx in caller['args']:
                    val, off, typ = caller['args'][idx]
                    args_str.append(f"$a{idx}={val}")
            print(f"    NOP 0x{caller['offset']:08X}: jal 0x{caller['function']:08X} ({', '.join(args_str)})")

    elif mode == 'multiply':
        print(f"\n  --- MULTIPLYING damage values by {factor} ---")
        for caller in damage_callers:
            for idx in [1, 2, 3]:
                if idx in caller['args']:
                    val, off, typ = caller['args'][idx]
                    if val < 0:
                        new_val = val * factor
                        # Clamp to int16 range
                        new_val = max(-32768, min(32767, new_val))
                        # Create new instruction
                        new_word = make_li_instruction(idx, new_val, use_addiu=(typ == 'addiu'))
                        struct.pack_into('<I', data, off, new_word)
                        print(f"    MOD 0x{off:08X}: $a{idx} {val} -> {new_val}")
                        patched_count += 1

    else:
        print(f"  [ERROR] Unknown mode: {mode}")
        return

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n  [SAVED] {BLAZE_OUT}")
    print(f"  {patched_count} modifications applied")

    print(f"\n{'='*70}")
    print(f"  TEST INSTRUCTIONS:")
    print(f"  1. Run build_gameplay_patch.bat (skip steps 1-7, just do 8-9)")
    print(f"     OR: py -3 patch_blaze_all.py")
    print(f"  2. Load the game, go to Cavern of Death")
    print(f"  3. Walk into falling rocks / traps")
    print(f"  4. Check if damage changed:")
    if mode == 'nop':
        print(f"     - Traps should deal ZERO damage if these are the right calls")
        print(f"     - Monsters should still deal normal damage (their code is different)")
    elif mode == 'multiply':
        print(f"     - Trap damage should be {factor}x the original")
    print(f"  5. Document results in WIP/TrapDamage/NOTES.md")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
