#!/usr/bin/env python3
"""
Patch trap/environmental damage in BLAZE.ALL overlay code (v2).

The game uses function 0x80024F90 (in EXE) for percentage-based HP damage:
  damage = (max_HP * damage_param) / 100

Overlay code calls this function with small hardcoded percentage values:
  - 2% = falling rocks, environmental hits
  - 5% = poison/periodic damage with timer

This patcher finds all `jal 0x80024F90` callers in overlay code where $a1
(the damage_param) is set to a small immediate value, and multiplies it.

Data-driven callers (combat, using register values for $a1) are automatically
skipped since they have no immediate value to patch.

Configuration: trap_damage_config.json
  - enabled: true/false
  - damage_multiplier: float, e.g. 5.0 = multiply trap percentages by 5
  - max_original_param: int, only patch callers with param <= this (default 20)

Runs at build step 7d (patches output/BLAZE.ALL before BIN injection).
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

# Real damage function: 0x80024F90
# Formula: damage = (max_HP * param%) / 100
# JAL encoding: jal 0x80024F90 = 0x0C0093E4
DAMAGE_FUNC_RAM = 0x80024F90
DAMAGE_FUNC_JAL = (0x03 << 26) | ((DAMAGE_FUNC_RAM >> 2) & 0x3FFFFFF)

# Search range in BLAZE.ALL overlay code
OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000

# Sanity check bounds
EXPECTED_MIN = 3
EXPECTED_MAX = 300


def find_trap_damage_callers(data, max_param=20):
    """Find all calls to the damage function with small immediate $a1 values.

    Searches for jal 0x80024F90 in overlay code, then checks if $a1 is set
    to a small immediate value (1 to max_param) in the instructions before
    the JAL or in its delay slot.

    Data-driven callers (where $a1 comes from a register or memory) are
    automatically skipped since no immediate value is found.

    Returns list of {jal_offset, param_value, param_offset, param_type}.
    """
    callers = []
    end = min(OVERLAY_END, len(data) - 4)

    for i in range(OVERLAY_START, end, 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word != DAMAGE_FUNC_JAL:
            continue

        # Found a JAL to the damage function.
        # Look for immediate $a1 ($5) setup within 10 instructions before.
        a1_info = None

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

            # addiu $a1, $zero, imm
            if op == 0x09 and rs == 0 and rt == 5:
                a1_info = (imms, off, 'addiu')
                break
            # ori $a1, $zero, imm
            elif op == 0x0D and rs == 0 and rt == 5:
                a1_info = (imm, off, 'ori')
                break
            # Stop at another JAL/JR (function boundary)
            elif (w >> 26) == 0x03 or w == 0x03E00008:
                break
            # Stop if $a1 is set from a non-zero register (data-driven)
            elif ((op == 0x09 or op == 0x0D) and rt == 5 and rs != 0):
                break
            # R-type writing to $a1 (move, addu, etc.)
            elif op == 0x00 and ((w >> 11) & 0x1F) == 5:
                break

        # Check delay slot if not found yet
        if a1_info is None:
            ds_off = i + 4
            if ds_off + 4 <= len(data):
                w = struct.unpack_from('<I', data, ds_off)[0]
                op = (w >> 26) & 0x3F
                rs = (w >> 21) & 0x1F
                rt = (w >> 16) & 0x1F
                imm = w & 0xFFFF
                imms = imm if imm < 0x8000 else imm - 0x10000

                if op == 0x09 and rs == 0 and rt == 5:
                    a1_info = (imms, ds_off, 'addiu')
                elif op == 0x0D and rs == 0 and rt == 5:
                    a1_info = (imm, ds_off, 'ori')

        if a1_info is None:
            continue

        value, param_off, param_type = a1_info

        # Filter: only small positive percentages (trap damage)
        if value < 1 or value > max_param:
            continue

        callers.append({
            'jal_offset': i,
            'param_value': value,
            'param_offset': param_off,
            'param_type': param_type,
        })

    return callers


def main():
    print("  Trap Damage Patcher v2 (real damage function)")
    print("  " + "-" * 50)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    if not config.get("enabled", False):
        print("  [SKIP] Trap damage patching disabled in config")
        return

    multiplier = config.get("damage_multiplier", 5.0)
    max_param = config.get("max_original_param", 20)

    print(f"  Damage function: 0x{DAMAGE_FUNC_RAM:08X} (EXE)")
    print(f"  JAL word: 0x{DAMAGE_FUNC_JAL:08X}")
    print(f"  Multiplier: {multiplier}x")
    print(f"  Max original param: {max_param}%")

    if not BLAZE_ALL.exists():
        print(f"  [ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    # Count total JAL matches first (for diagnostics)
    total_jals = 0
    end = min(OVERLAY_END, len(data) - 4)
    for i in range(OVERLAY_START, end, 4):
        if struct.unpack_from('<I', data, i)[0] == DAMAGE_FUNC_JAL:
            total_jals += 1
    print(f"  Total jal 0x{DAMAGE_FUNC_RAM:08X} in overlays: {total_jals}")

    # Find trap damage callers (with immediate $a1)
    callers = find_trap_damage_callers(data, max_param)
    print(f"  Trap callers (immediate $a1, param 1-{max_param}%): {len(callers)}")

    if not callers:
        print("  [SKIP] No trap damage callers found")
        return

    if len(callers) < EXPECTED_MIN:
        print(f"  [WARNING] Only {len(callers)} callers (expected >= {EXPECTED_MIN})")

    if len(callers) > EXPECTED_MAX:
        print(f"  [ERROR] Too many callers ({len(callers)} > {EXPECTED_MAX}) - aborting")
        sys.exit(1)

    # Show summary by original value
    by_value = {}
    for c in callers:
        v = c['param_value']
        by_value[v] = by_value.get(v, 0) + 1

    print()
    for v in sorted(by_value):
        new_v = min(99, int(v * multiplier))
        print(f"    {by_value[v]:>3}x callers with param={v}% -> {new_v}%")

    # Apply patches
    patched = 0
    print()

    for c in callers:
        old_val = c['param_value']
        new_val = int(old_val * multiplier)
        new_val = max(1, min(99, new_val))  # Clamp to valid percentage

        param_off = c['param_offset']
        param_type = c['param_type']

        # Verify instruction is still what we expect
        old_word = struct.unpack_from('<I', data, param_off)[0]
        old_rs = (old_word >> 21) & 0x1F
        old_rt = (old_word >> 16) & 0x1F

        if old_rs != 0 or old_rt != 5:
            print(f"  [WARN] 0x{param_off:08X}: unexpected registers "
                  f"(rs={REGS[old_rs]}, rt={REGS[old_rt]})")
            continue

        # Build new instruction with updated immediate
        if param_type == 'addiu':
            new_word = (0x09 << 26) | (0 << 21) | (5 << 16) | (new_val & 0xFFFF)
        else:  # ori
            new_word = (0x0D << 26) | (0 << 21) | (5 << 16) | (new_val & 0xFFFF)

        struct.pack_into('<I', data, param_off, new_word)
        print(f"  [PATCH] 0x{param_off:08X}: $a1 = {old_val}% -> {new_val}% "
              f"(jal at 0x{c['jal_offset']:08X})")
        patched += 1

    if patched > 0:
        BLAZE_ALL.write_bytes(data)

    print()
    print(f"  {'='*50}")
    print(f"  {patched} trap damage patch(es) applied")
    print(f"  Formula: damage = (maxHP * param%) / 100")
    print(f"  {'='*50}")


if __name__ == "__main__":
    main()
