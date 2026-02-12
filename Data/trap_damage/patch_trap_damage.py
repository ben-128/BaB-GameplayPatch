#!/usr/bin/env python3
"""
Patch trap/environmental damage in BLAZE.ALL overlay code (v6).

Four passes:

Pass 1 - Direct callers: Find `jal 0x80024F90` where $a1 is an immediate.
  Catches: static traps (2%, 3%, 5%, 10%, 20%) that call damage function directly.
  15 sites across 7+ overlay regions.

Pass 2 - DISABLED (was GPE entity init, but entity+0x14 is a STATE MACHINE
  variable, not damage%. See RESEARCH.md.)

Pass 3 - Entity init data: Patch known halfword offsets in entity configuration
  data blocks. These are read by overlay handlers and passed to the damage
  function via register arguments. Catches falling rocks, heavy traps etc.
  Offsets found via reverse engineering of Template A/B functions.

Pass 4 - Falling rocks (NEW 2026-02-13): Pattern-based search for hardcoded
  damage% in overlay code. Pattern: `addiu a1, zero, 10` + `addu a2, zero, zero`.
  21 sites across all dungeons. Found via in-game debugging with DuckStation.
  See Data/trap_damage/FALLING_ROCK_SOLUTION.md for full details.

Config format (overlay_patches.values):
  {"2": 10, "5": 25, "10": 50, "20": 50}

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

# Known entity init data offsets containing damage% halfwords.
# Format: (blaze_offset, description)
# These are halfwords in entity configuration data blocks that precede
# Template A/B overlay functions. The handler reads the value from the
# entity struct and passes it to jal 0x80024F90 via sll/sra sign-extension.
#
# NOTE: 0x009ECE8A was tested in-game (2026-02-10) and confirmed to be
# collision/hitbox size, NOT damage%. It has been REMOVED.
# The actual damage% location for falling rocks is still unknown.
# See RESEARCH.md "Entity Descriptor System" section.
ENTITY_INIT_OFFSETS = [
    # No confirmed offsets yet — all candidates need in-game testing
]


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
        })

    return callers


def find_entity_init_data(data, value_map):
    """Pass 3: Check known entity init data offsets for patchable values."""
    results = []

    for offset, desc in ENTITY_INIT_OFFSETS:
        if offset + 2 > len(data):
            print(f"  [WARN] Offset 0x{offset:08X} out of range ({desc})")
            continue

        val = struct.unpack_from('<H', data, offset)[0]
        if val not in value_map:
            print(f"  [SKIP] 0x{offset:08X}: value {val} not in value_map ({desc})")
            continue

        results.append({
            'param_value': val,
            'param_offset': offset,
            'description': desc,
        })

    return results


def apply_patches_pass1(data, entries, value_map):
    """Apply Pass 1 patches (MIPS instruction immediates)."""
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

        if old_rs != 0:
            print(f"  [WARN] 0x{param_off:08X}: unexpected rs={old_rs}")
            continue

        target_rt = old_rt
        if param_type == 'addiu':
            new_word = (0x09 << 26) | (0 << 21) | (target_rt << 16) | (new_val & 0xFFFF)
        else:
            new_word = (0x0D << 26) | (0 << 21) | (target_rt << 16) | (new_val & 0xFFFF)

        struct.pack_into('<I', data, param_off, new_word)
        print(f"  [JAL] 0x{param_off:08X}: {old_val}% -> {new_val}%")
        patched += 1

    return patched, skipped


def apply_patches_pass3(data, entries, value_map):
    """Apply Pass 3 patches (halfwords in entity init data)."""
    patched = 0
    skipped = 0

    for c in entries:
        old_val = c['param_value']
        new_val = value_map.get(old_val)
        desc = c.get('description', '')

        if new_val is None or new_val == old_val:
            skipped += 1
            continue

        new_val = max(1, min(99, new_val))
        param_off = c['param_offset']

        struct.pack_into('<H', data, param_off, new_val)
        print(f"  [ENT] 0x{param_off:08X}: {old_val}% -> {new_val}% ({desc})")
        patched += 1

    return patched, skipped


def find_falling_rocks(data):
    """
    Pass 4: Find trap damage via code pattern.

    Pattern (verified in-game 2026-02-13):
        addiu a1, zero, X      # XX 00 05 24  (X = damage%)
        addu a2, zero, zero    # 21 30 00 00

    Searches for reasonable damage% values (1-50).
    Values >50% are likely false positives (random code matching pattern).
    Returns list of {'offset': blaze_offset, 'damage': damage_percent}
    """
    results = []

    # Search for reasonable trap damage% values (1-50)
    # Values >50% are almost certainly false positives
    for dmg_val in range(1, 51):
        pattern = bytes([dmg_val, 0x00, 0x05, 0x24, 0x21, 0x30, 0x00, 0x00])
        offset = 0

        while True:
            pos = data.find(pattern, offset)
            if pos == -1:
                break

            results.append({
                'offset': pos,
                'damage': dmg_val,
            })

            offset = pos + 1

    # Sort by offset for cleaner output
    results.sort(key=lambda x: x['offset'])

    return results


def apply_patches_pass4(data, entries, value_map):
    """Apply Pass 4 patches (falling rock code patterns)."""
    patched = 0
    skipped = 0

    for entry in entries:
        old_val = entry['damage']
        new_val = value_map.get(old_val)
        offset = entry['offset']

        if new_val is None or new_val == old_val:
            skipped += 1
            continue

        new_val = max(1, min(99, new_val))

        # Patch first byte (damage% immediate value)
        data[offset] = new_val
        print(f"  [ROCK] 0x{offset:08X}: {old_val}% -> {new_val}%")
        patched += 1

    return patched, skipped


def main():
    print("  Trap Damage Patcher v6 (jal + entity + falling rocks)")
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

    p1, s1 = apply_patches_pass1(data, jal_callers, value_map)

    # Pass 2: DISABLED — entity+0x14 is a state machine variable, NOT damage%.
    print(f"\n  Pass 2: DISABLED (GPE state machine, not damage)")

    # Pass 3: Entity init data halfwords (known offsets)
    entity_inits = find_entity_init_data(data, value_map)
    print(f"\n  Pass 3: {len(entity_inits)} entity init data sites")

    p3, s3 = apply_patches_pass3(data, entity_inits, value_map)

    # Pass 4: Falling rock code patterns (NEW 2026-02-13)
    falling_rocks = find_falling_rocks(data)
    print(f"\n  Pass 4: {len(falling_rocks)} falling rock sites")

    by_value_rocks = {}
    for r in falling_rocks:
        v = r['damage']
        by_value_rocks[v] = by_value_rocks.get(v, 0) + 1
    for v in sorted(by_value_rocks):
        new_v = value_map.get(v)
        status = f"-> {new_v}%" if new_v is not None else "(skip)"
        print(f"    {by_value_rocks[v]:>3}x {v}% {status}")

    p4, s4 = apply_patches_pass4(data, falling_rocks, value_map)

    total_patched = p1 + p3 + p4
    total_skipped = s1 + s3 + s4

    if total_patched > 0:
        BLAZE_ALL.write_bytes(data)

    print(f"\n  Total: {total_patched} patched ({p1} jal + {p3} entity + {p4} rocks), "
          f"{total_skipped} unchanged")


if __name__ == "__main__":
    main()
