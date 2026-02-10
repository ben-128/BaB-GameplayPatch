#!/usr/bin/env python3
"""
Phase 1.2 (adapted): Map overlay code regions to dungeon areas and identify
which callers of the stat modifier function 0x8008A3E4 correspond to traps.

Strategy:
1. Each dungeon area's data starts at group_offset in BLAZE.ALL
2. The overlay code for each area is loaded nearby (before group_offset)
3. By finding which overlay region each caller falls into, we can identify
   which dungeon area contains each trap damage call

Also searches for the related functions:
  0x8008A1C4 (25 callers)
  0x8008A39C (25 callers)
  0x8008A3BC (28 callers)
  0x8008A3E4 (58 callers) - main stat modifier

Usage: py -3 WIP/TrapDamage/compare_trap_zones.py
"""

import struct
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
FORMATIONS_DIR = PROJECT_ROOT / "Data" / "formations"
OUTPUT_DIR = SCRIPT_DIR / "dumps"

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

# Target functions in the stat modifier family
STAT_MOD_FUNCTIONS = [
    0x8008A1C4,
    0x8008A39C,
    0x8008A3BC,
    0x8008A3E4,
]


def load_zones():
    zones = []
    for json_file in sorted(FORMATIONS_DIR.rglob("*.json")):
        if json_file.name == "ai_blocks_dump.json":
            continue
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                zone = json.load(f)
            zones.append({
                'level': zone.get('level_name', '?'),
                'name': zone.get('name', '?'),
                'group_offset': int(zone['group_offset'], 16),
                'num_monsters': len(zone.get('monsters', [])),
                'monsters': zone.get('monsters', []),
            })
        except (KeyError, ValueError, json.JSONDecodeError):
            pass
    # Sort by group_offset
    zones.sort(key=lambda z: z['group_offset'])
    return zones


def find_jal_callers(data, target_ram, search_start, search_end):
    target_field = (target_ram >> 2) & 0x3FFFFFF
    jal_word = (0x03 << 26) | target_field
    callers = []
    for i in range(search_start, min(search_end, len(data) - 4), 4):
        word = struct.unpack_from('<I', data, i)[0]
        if word == jal_word:
            callers.append(i)
    return callers


def extract_call_args(data, jal_offset):
    args = {}
    # Check 8 instructions before JAL
    for j in range(1, 9):
        off = jal_offset - j * 4
        if off < 0:
            break
        word = struct.unpack_from('<I', data, off)[0]
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000

        if op == 0x09 and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = imms
        elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = imm
        elif op == 0 and (word & 0x3F) == 0x21:
            rd = (word >> 11) & 0x1F
            if 4 <= rd <= 7:
                arg_name = f"$a{rd-4}"
                if arg_name not in args:
                    args[arg_name] = f"={REGS[rs]}"

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
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = imms
        elif op == 0x0D and rs == 0 and 4 <= rt <= 7:
            arg_name = f"$a{rt-4}"
            if arg_name not in args:
                args[arg_name] = imm

    return args


def map_offset_to_zone(offset, zones):
    """Map a BLAZE.ALL offset to the nearest zone (by group_offset).

    Overlay code for a zone typically precedes its group_offset.
    Find the zone whose group_offset is closest AFTER the offset.
    """
    best = None
    best_dist = float('inf')
    for z in zones:
        if z['group_offset'] > offset:
            dist = z['group_offset'] - offset
            if dist < best_dist and dist < 0x100000:  # max 1MB distance
                best_dist = dist
                best = z
    return best, best_dist


def main():
    print("=" * 70)
    print("  Trap Damage - Phase 1.2: Map Overlay Callers to Dungeon Areas")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    zones = load_zones()
    print(f"  Loaded {len(zones)} zones")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Find all callers of stat modifier functions in overlays
    overlay_start = 0x00900000
    overlay_end = min(0x02D00000, len(data))

    all_callers = []
    for func in STAT_MOD_FUNCTIONS:
        callers = find_jal_callers(data, func, overlay_start, overlay_end)
        for c in callers:
            args = extract_call_args(data, c)
            # Only include callers with explicit numeric args (not register refs)
            has_numeric = any(isinstance(v, int) for k, v in args.items()
                           if k in ['$a1', '$a2', '$a3'])
            all_callers.append({
                'offset': c,
                'function': func,
                'args': args,
                'has_numeric': has_numeric,
            })

    print(f"  Found {len(all_callers)} stat modifier calls in overlays")
    print(f"  ({sum(1 for c in all_callers if c['has_numeric'])} with numeric args)")

    # Map each caller to a zone
    zone_callers = {}
    unmapped = []

    for caller in all_callers:
        zone, dist = map_offset_to_zone(caller['offset'], zones)
        if zone:
            key = f"{zone['level']} / {zone['name']}"
            if key not in zone_callers:
                zone_callers[key] = {'zone': zone, 'callers': [], 'dist': dist}
            zone_callers[key]['callers'].append(caller)
        else:
            unmapped.append(caller)

    # Output results
    out_path = OUTPUT_DIR / "overlay_to_zone_map.txt"
    with open(out_path, 'w', encoding='cp1252') as f:
        f.write("STAT MODIFIER CALLERS -> DUNGEON ZONE MAPPING\n")
        f.write("=" * 80 + "\n\n")

        # Sort by zone name
        for key in sorted(zone_callers.keys()):
            zc = zone_callers[key]
            zone = zc['zone']
            callers = zc['callers']

            # Separate damage (negative) and heal (positive) callers
            damage_callers = []
            heal_callers = []
            other_callers = []

            for c in callers:
                a1 = c['args'].get('$a1', '?')
                a2 = c['args'].get('$a2', '?')
                a3 = c['args'].get('$a3', '?')

                has_neg = any(isinstance(v, int) and v < 0
                            for v in [a1, a2, a3])
                has_pos = any(isinstance(v, int) and v > 0
                            for v in [a1, a2, a3])

                if has_neg:
                    damage_callers.append(c)
                elif has_pos:
                    heal_callers.append(c)
                else:
                    other_callers.append(c)

            f.write(f"\n{'='*60}\n")
            f.write(f"  {key}\n")
            f.write(f"  Monsters: {', '.join(zone['monsters'])}\n")
            f.write(f"  Group offset: 0x{zone['group_offset']:X}\n")
            f.write(f"  Total callers: {len(callers)} "
                   f"(damage={len(damage_callers)}, heal={len(heal_callers)}, "
                   f"other={len(other_callers)})\n")
            f.write(f"{'='*60}\n")

            if damage_callers:
                f.write(f"\n  --- DAMAGE callers (negative values = potential traps) ---\n")
                for c in damage_callers:
                    a1 = c['args'].get('$a1', '?')
                    a2 = c['args'].get('$a2', '?')
                    a3 = c['args'].get('$a3', '?')
                    f.write(f"    BLAZE+0x{c['offset']:08X}: "
                           f"func=0x{c['function']:08X} "
                           f"a1={a1} a2={a2} a3={a3}\n")

            if heal_callers:
                f.write(f"\n  --- HEAL/BUFF callers (positive values) ---\n")
                for c in heal_callers:
                    a1 = c['args'].get('$a1', '?')
                    a2 = c['args'].get('$a2', '?')
                    a3 = c['args'].get('$a3', '?')
                    f.write(f"    BLAZE+0x{c['offset']:08X}: "
                           f"func=0x{c['function']:08X} "
                           f"a1={a1} a2={a2} a3={a3}\n")

        if unmapped:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"  UNMAPPED CALLERS ({len(unmapped)})\n")
            f.write(f"{'='*60}\n")
            for c in unmapped[:20]:
                a1 = c['args'].get('$a1', '?')
                a2 = c['args'].get('$a2', '?')
                a3 = c['args'].get('$a3', '?')
                f.write(f"    BLAZE+0x{c['offset']:08X}: "
                       f"func=0x{c['function']:08X} "
                       f"a1={a1} a2={a2} a3={a3}\n")

    print(f"\n  Output: {out_path}")

    # Also print summary to console: which zones have DAMAGE callers
    print(f"\n  --- Zones with DAMAGE callers (negative stat mods) ---")
    for key in sorted(zone_callers.keys()):
        zc = zone_callers[key]
        damage = [c for c in zc['callers']
                 if any(isinstance(c['args'].get(f'$a{i}', '?'), int) and c['args'].get(f'$a{i}', '?') < 0
                       for i in [1, 2, 3])]
        if damage:
            values = set()
            for c in damage:
                for i in [1, 2, 3]:
                    v = c['args'].get(f'$a{i}', None)
                    if isinstance(v, int) and v < 0:
                        values.add(v)
            print(f"    {key}: {len(damage)} damage calls, values: {sorted(values)}")

    print(f"\n{'='*70}")


if __name__ == '__main__':
    main()
