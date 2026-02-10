#!/usr/bin/env python3
"""
Patch trap/environmental damage in BLAZE.ALL overlay code (v4).

Two search passes:

Pass 1 - Direct callers: Find `jal 0x80024F90` where $a1 is an immediate.
  Catches: static traps (2%, 3%, 5%, 10%, 20%) that call damage function directly.

Pass 2 - GPE entity init: Find `li $v0, N` + `sh $v0, 0x14($s5)` (adjacent).
  Catches: falling rocks, heavy traps etc. that store damage% to entity+0x14
  and later pass it to the damage function via register (data-driven callers).
  Only $s5 confirmed as damage% register. Other registers are camera shake.

Config format (overlay_patches.values):
  {"2": 10, "5": 25, "10": 40, "20": 60}
  means: original 2% -> 10%, original 5% -> 25%, etc.

Runs at build step 7d (patches output/BLAZE.ALL before BIN injection).
"""

import struct
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "trap_damage_config.json"
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

# Real damage function: 0x80024F90
DAMAGE_FUNC_RAM = 0x80024F90
DAMAGE_FUNC_JAL = (0x03 << 26) | ((DAMAGE_FUNC_RAM >> 2) & 0x3FFFFFF)

# Search range in BLAZE.ALL overlay code
OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000

# GPE entity init: sh $v0, 0x14($s5) — only $s5 is confirmed as damage%
# Other registers ($s0/$s1/$s2/$s6) store camera shake intensity, NOT damage.
SH_V0_014_S5 = (0x29 << 26) | (21 << 21) | (2 << 16) | 0x0014  # 0xA6A20014


def find_immediate_callers(data):
    """Pass 1: jal 0x80024F90 callers where $a1 is set via immediate."""
    callers = []
    end = min(OVERLAY_END, len(data) - 4)

    for i in range(OVERLAY_START, end, 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word != DAMAGE_FUNC_JAL:
            continue

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

            if op == 0x09 and rs == 0 and rt == 5:
                a1_info = (imms, off, 'addiu')
                break
            elif op == 0x0D and rs == 0 and rt == 5:
                a1_info = (imm, off, 'ori')
                break
            elif (w >> 26) == 0x03 or w == 0x03E00008:
                break
            elif ((op == 0x09 or op == 0x0D) and rt == 5 and rs != 0):
                break
            elif op == 0x00 and ((w >> 11) & 0x1F) == 5:
                break

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
            'param_value': value,
            'param_offset': param_off,
            'param_type': param_type,
            'source': 'jal_caller',
        })

    return callers


def find_gpe_entity_init(data):
    """Pass 2: GPE entity damage init (li $v0, N + sh $v0, 0x14($s5), adjacent).

    The GPE entity state handler stores damage% to entity+0x14.
    Pattern: ori/addiu $v0, $zero, N immediately followed by sh $v0, 0x14($s5).
    Only $s5 is confirmed as damage%. Other registers are camera shake / other fields.
    """
    results = []
    end = min(OVERLAY_END, len(data) - 8)

    for i in range(OVERLAY_START, end, 4):
        w1 = struct.unpack_from('<I', data, i)[0]
        w2 = struct.unpack_from('<I', data, i + 4)[0]

        # w2 must be sh $v0, 0x14($s5)
        if w2 != SH_V0_014_S5:
            continue

        # w1 must be ori $v0, $zero, N or addiu $v0, $zero, N
        op = (w1 >> 26) & 0x3F
        rs = (w1 >> 21) & 0x1F
        rt = (w1 >> 16) & 0x1F
        imm = w1 & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000

        is_ori = (op == 0x0D and rs == 0 and rt == 2)
        is_addiu = (op == 0x09 and rs == 0 and rt == 2)
        if not (is_ori or is_addiu):
            continue

        val = imm if is_ori else imms
        if val < 1 or val > 99:
            continue

        results.append({
            'param_value': val,
            'param_offset': i,
            'param_type': 'ori' if is_ori else 'addiu',
            'source': 'gpe_entity',
        })

    return results


def apply_patches(data, entries, value_map, label):
    """Apply value_map patches to a list of entries. Returns (patched, skipped)."""
    patched = 0
    skipped = 0

    for c in entries:
        old_val = c['param_value']
        new_val = value_map.get(old_val)

        if new_val is None or new_val == old_val:
            skipped += 1
            continue

        new_val = max(1, min(99, new_val))
        param_off = c['param_offset']
        param_type = c['param_type']

        old_word = struct.unpack_from('<I', data, param_off)[0]
        old_rs = (old_word >> 21) & 0x1F
        old_rt = (old_word >> 16) & 0x1F

        # Verify source register is $zero
        if old_rs != 0:
            print(f"  [WARN] 0x{param_off:08X}: unexpected rs={old_rs}")
            continue

        # Build patched instruction (same opcode, new immediate)
        target_rt = old_rt  # keep original target register ($a1 or $v0)
        if param_type == 'addiu':
            new_word = (0x09 << 26) | (0 << 21) | (target_rt << 16) | (new_val & 0xFFFF)
        else:
            new_word = (0x0D << 26) | (0 << 21) | (target_rt << 16) | (new_val & 0xFFFF)

        struct.pack_into('<I', data, param_off, new_word)
        print(f"  [{label}] 0x{param_off:08X}: {old_val}% -> {new_val}%")
        patched += 1

    return patched, skipped


def main():
    print("  Trap Damage Patcher v4 (jal callers + GPE entity init)")
    print("  " + "-" * 50)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    overlay_cfg = config.get("overlay_patches", {})

    if not overlay_cfg.get("enabled", False):
        print("  [SKIP] Overlay patches disabled in config")
        return

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

    # Pass 1: jal callers with immediate $a1
    jal_callers = find_immediate_callers(data)
    print(f"\n  Pass 1: {len(jal_callers)} jal callers with immediate $a1")

    by_value = {}
    for c in jal_callers:
        v = c['param_value']
        by_value[v] = by_value.get(v, 0) + 1
    for v in sorted(by_value):
        new_v = value_map.get(v)
        status = f"-> {new_v}%" if new_v is not None else "(skip)"
        print(f"    {by_value[v]:>3}x {v}% {status}")

    p1, s1 = apply_patches(data, jal_callers, value_map, "JAL")

    # Pass 2: GPE entity init (li + sh 0x14($s5))
    gpe_inits = find_gpe_entity_init(data)
    print(f"\n  Pass 2: {len(gpe_inits)} GPE entity init sites (sh $v0, 0x14($s5))")

    by_value = {}
    for c in gpe_inits:
        v = c['param_value']
        by_value[v] = by_value.get(v, 0) + 1
    for v in sorted(by_value):
        new_v = value_map.get(v)
        status = f"-> {new_v}%" if new_v is not None else "(skip)"
        print(f"    {by_value[v]:>3}x {v}% {status}")

    p2, s2 = apply_patches(data, gpe_inits, value_map, "GPE")

    total_patched = p1 + p2
    total_skipped = s1 + s2

    if total_patched > 0:
        BLAZE_ALL.write_bytes(data)

    print(f"\n  Total: {total_patched} patched ({p1} jal + {p2} gpe), "
          f"{total_skipped} unchanged")


if __name__ == "__main__":
    main()
