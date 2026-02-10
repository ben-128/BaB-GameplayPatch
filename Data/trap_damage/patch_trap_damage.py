#!/usr/bin/env python3
"""
Patch trap/environmental damage in BLAZE.ALL overlay code (v3).

The game uses function 0x80024F90 (in EXE) for percentage-based HP damage:
  damage = (max_HP * damage_param) / 100

Overlay code calls this function with small hardcoded percentage values.
This patcher finds all `jal 0x80024F90` callers where $a1 is set to an
immediate value, and replaces it with the value from the config JSON.

Config format (overlay_patches.values):
  {"2": 10, "5": 25}  means: callers with original 2% -> 10%, 5% -> 25%
  Any value not in the map stays unchanged.

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
DAMAGE_FUNC_RAM = 0x80024F90
DAMAGE_FUNC_JAL = (0x03 << 26) | ((DAMAGE_FUNC_RAM >> 2) & 0x3FFFFFF)

# Search range in BLAZE.ALL overlay code
OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000


def find_immediate_callers(data):
    """Find all jal 0x80024F90 callers where $a1 is set via immediate.

    Returns list of {jal_offset, param_value, param_offset, param_type}.
    """
    callers = []
    end = min(OVERLAY_END, len(data) - 4)

    for i in range(OVERLAY_START, end, 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word != DAMAGE_FUNC_JAL:
            continue

        a1_info = None

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

            if op == 0x09 and rs == 0 and rt == 5:  # addiu $a1, $zero, imm
                a1_info = (imms, off, 'addiu')
                break
            elif op == 0x0D and rs == 0 and rt == 5:  # ori $a1, $zero, imm
                a1_info = (imm, off, 'ori')
                break
            elif (w >> 26) == 0x03 or w == 0x03E00008:  # JAL/JR boundary
                break
            elif ((op == 0x09 or op == 0x0D) and rt == 5 and rs != 0):
                break  # $a1 set from register
            elif op == 0x00 and ((w >> 11) & 0x1F) == 5:
                break  # R-type writing to $a1

        # Check delay slot
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
        if value < 1 or value > 99:
            continue

        callers.append({
            'jal_offset': i,
            'param_value': value,
            'param_offset': param_off,
            'param_type': param_type,
        })

    return callers


def main():
    print("  Trap Damage Patcher v3 (overlay, per-value overrides)")
    print("  " + "-" * 50)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    overlay_cfg = config.get("overlay_patches", {})

    if not overlay_cfg.get("enabled", False):
        print("  [SKIP] Overlay patches disabled in config")
        return

    # Parse value map: {"2": 10, "5": 25} -> {2: 10, 5: 25}
    value_map = {}
    for k, v in overlay_cfg.get("values", {}).items():
        value_map[int(k)] = int(v)

    if not value_map:
        print("  [SKIP] No values defined in overlay_patches.values")
        return

    print(f"  Damage function: 0x{DAMAGE_FUNC_RAM:08X}")
    print(f"  Value map: {', '.join(f'{k}%->{v}%' for k, v in sorted(value_map.items()))}")

    if not BLAZE_ALL.exists():
        print(f"  [ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())

    callers = find_immediate_callers(data)
    print(f"  Found {len(callers)} immediate callers in overlay code")

    if not callers:
        print("  [SKIP] No callers found")
        return

    # Show summary
    by_value = {}
    for c in callers:
        v = c['param_value']
        by_value[v] = by_value.get(v, 0) + 1

    for v in sorted(by_value):
        new_v = value_map.get(v)
        status = f"-> {new_v}%" if new_v is not None else "(no override)"
        print(f"    {by_value[v]:>3}x param={v}% {status}")

    # Apply patches
    patched = 0
    skipped = 0

    for c in callers:
        old_val = c['param_value']
        new_val = value_map.get(old_val)

        if new_val is None:
            skipped += 1
            continue

        if new_val == old_val:
            skipped += 1
            continue

        new_val = max(1, min(99, new_val))
        param_off = c['param_offset']
        param_type = c['param_type']

        # Verify instruction
        old_word = struct.unpack_from('<I', data, param_off)[0]
        old_rs = (old_word >> 21) & 0x1F
        old_rt = (old_word >> 16) & 0x1F

        if old_rs != 0 or old_rt != 5:
            print(f"  [WARN] 0x{param_off:08X}: unexpected registers")
            continue

        if param_type == 'addiu':
            new_word = (0x09 << 26) | (0 << 21) | (5 << 16) | (new_val & 0xFFFF)
        else:
            new_word = (0x0D << 26) | (0 << 21) | (5 << 16) | (new_val & 0xFFFF)

        struct.pack_into('<I', data, param_off, new_word)
        print(f"  [PATCH] 0x{param_off:08X}: $a1 = {old_val}% -> {new_val}%")
        patched += 1

    if patched > 0:
        BLAZE_ALL.write_bytes(data)

    print(f"\n  {patched} patched, {skipped} unchanged")


if __name__ == "__main__":
    main()
