#!/usr/bin/env python3
"""
Patch trap/environmental damage in BLAZE.ALL overlay code.

The game uses function 0x8008A3E4(entity, a1, a2, a3) in overlay code
to apply stat modifications. Negative values = damage/debuff.

This patcher finds all calls to 0x8008A3E4 with negative immediate args
and applies a damage multiplier to increase (or decrease) trap damage.

Configuration: trap_damage_config.json
  - enabled: true/false
  - mode: "multiply" (scale damage) or "nop" (disable damage)
  - damage_multiplier: float, e.g. 2.0 = double damage

Runs at build step 7d (patches output/BLAZE.ALL before BIN injection).

Usage (standalone):  py -3 Data/trap_damage/patch_trap_damage.py
Usage (in build):    Called from build_gameplay_patch.bat
"""

import struct
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "trap_damage_config.json"
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

NOP_WORD = 0x00000000

# Stat modifier function: jal 0x8008A3E4
STAT_MOD_RAM = 0x8008A3E4
STAT_MOD_JAL = (0x03 << 26) | ((STAT_MOD_RAM >> 2) & 0x3FFFFFF)

# Search range in BLAZE.ALL overlay code
OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000


def find_all_damage_callers(data):
    """Find all calls to 0x8008A3E4 with negative immediate args.

    Returns list of {jal_offset, args: {idx: (value, instr_offset, type)}}.
    """
    callers = []
    end = min(OVERLAY_END, len(data) - 4)

    for i in range(OVERLAY_START, end, 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word != STAT_MOD_JAL:
            continue

        # Found a JAL to stat_mod. Extract arg immediates.
        args = {}

        # Check 10 instructions before
        for j in range(1, 11):
            off = i - j * 4
            if off < OVERLAY_START:
                break
            w = struct.unpack_from('<I', data, off)[0]
            op = (w >> 26) & 0x3F
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            imm = w & 0xFFFF
            imms = imm if imm < 0x8000 else imm - 0x10000

            if op == 0x09 and rs == 0 and 4 <= rt <= 7:  # addiu $aX, $zero, imm
                idx = rt - 4
                if idx not in args:
                    args[idx] = (imms, off, 'addiu')
            elif op == 0x0D and rs == 0 and 4 <= rt <= 7:  # ori $aX, $zero, imm
                idx = rt - 4
                if idx not in args:
                    args[idx] = (imm, off, 'ori')

        # Check delay slot
        ds_off = i + 4
        if ds_off + 4 <= len(data):
            w = struct.unpack_from('<I', data, ds_off)[0]
            op = (w >> 26) & 0x3F
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            imm = w & 0xFFFF
            imms = imm if imm < 0x8000 else imm - 0x10000

            if op == 0x09 and rs == 0 and 4 <= rt <= 7:
                idx = rt - 4
                if idx not in args:
                    args[idx] = (imms, ds_off, 'addiu')
            elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
                idx = rt - 4
                if idx not in args:
                    args[idx] = (imm, ds_off, 'ori')

        # Check if any of $a1/$a2/$a3 are negative
        has_neg = any(isinstance(args.get(idx, (None,))[0], int) and args.get(idx, (0,))[0] < 0
                     for idx in [1, 2, 3])

        if has_neg:
            callers.append({
                'jal_offset': i,
                'args': args,
            })

    return callers


def make_li_instruction(reg_idx, value, use_addiu=True):
    """Create addiu $aX, $zero, value."""
    rt = reg_idx + 4  # $a0=4, $a1=5, etc.
    if use_addiu:
        imm = value & 0xFFFF
        return (0x09 << 26) | (0 << 21) | (rt << 16) | imm
    else:
        return (0x0D << 26) | (0 << 21) | (rt << 16) | (value & 0xFFFF)


def main():
    print("  Trap Damage Patcher (BLAZE.ALL overlay code)")
    print("  " + "-" * 45)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    if not config.get("enabled", False):
        print("  [SKIP] Trap damage patching disabled in config")
        return

    mode = config.get("mode", "multiply")
    multiplier = config.get("damage_multiplier", 2.0)

    print(f"  Mode: {mode}")
    if mode == "multiply":
        print(f"  Multiplier: {multiplier}x")

    if not BLAZE_ALL.exists():
        print(f"  [ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())

    # Find all damage callers dynamically
    callers = find_all_damage_callers(data)
    print(f"  Found {len(callers)} damage calls to 0x{STAT_MOD_RAM:08X}")

    if not callers:
        print("  [SKIP] No damage callers found (may already be patched)")
        return

    patched = 0

    if mode == "nop":
        # NOP all damage JAL calls
        for caller in callers:
            off = caller['jal_offset']
            old_word = struct.unpack_from('<I', data, off)[0]

            if old_word == NOP_WORD:
                continue  # Already NOPed

            if old_word != STAT_MOD_JAL:
                print(f"  [WARN] 0x{off:08X}: expected JAL, got 0x{old_word:08X}")
                continue

            struct.pack_into('<I', data, off, NOP_WORD)

            args_str = ', '.join(
                f"$a{idx}={caller['args'][idx][0]}"
                for idx in [1, 2, 3]
                if idx in caller['args'] and isinstance(caller['args'][idx][0], int)
            )
            print(f"  [PATCH] NOP 0x{off:08X}: ({args_str})")
            patched += 1

    elif mode == "multiply":
        # Multiply all negative arg values
        for caller in callers:
            for idx in [1, 2, 3]:
                if idx not in caller['args']:
                    continue
                val, instr_off, instr_type = caller['args'][idx]
                if not isinstance(val, int) or val >= 0:
                    continue

                new_val = int(val * multiplier)
                new_val = max(-32768, min(-1, new_val))

                # Verify the instruction is still what we expect
                old_word = struct.unpack_from('<I', data, instr_off)[0]
                old_op = (old_word >> 26) & 0x3F
                old_rs = (old_word >> 21) & 0x1F
                old_rt = (old_word >> 16) & 0x1F

                if old_rs != 0 or old_rt != idx + 4:
                    print(f"  [WARN] 0x{instr_off:08X}: instruction doesn't match expected pattern")
                    continue

                new_word = make_li_instruction(idx, new_val, use_addiu=(instr_type == 'addiu'))
                struct.pack_into('<I', data, instr_off, new_word)
                print(f"  [PATCH] 0x{instr_off:08X}: $a{idx} {val} -> {new_val}")
                patched += 1

    else:
        print(f"  [ERROR] Unknown mode: {mode}")
        sys.exit(1)

    if patched > 0:
        BLAZE_ALL.write_bytes(data)
        print(f"  [OK] {patched} trap damage patch(es) applied to BLAZE.ALL")
    else:
        print("  [SKIP] No trap damage patches applied")


if __name__ == "__main__":
    main()
