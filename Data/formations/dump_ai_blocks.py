#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Dump AI behavior blocks from the script area for reverse engineering.

This tool extracts and compares the per-monster behavior data structures
to identify fields controlling timing, aggression, roaming, attack speed, etc.

The script area structure:
  [Root offset table] - uint32 LE array, indexed by L value (from assignment entries)
                        Each entry points to a behavior block, or 0x00000000 if NULL
  [Behavior blocks]   - Variable-length structures containing:
                        - Header/timers
                        - Stats
                        - Spawn records (FFFF-separated)
                        - Bytecode program references
  [Formation templates] - 32-byte records for encounter composition
  [Spawn points]       - Coordinate data for placed spawns
  [Zone spawns]        - Coordinate data for zone spawns
  [Dialogue text]      - ASCII strings

Usage:
  py -3 Data/formations/dump_ai_blocks.py

This is purely for analysis - it does NOT modify any game data.
"""

import struct
import json
from pathlib import Path

# ===========================================================================
# Configuration
# ===========================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# Areas to analyze - diverse monster types for comparison
AREAS = [
    {
        "name": "Cavern F1 Area1",
        "group_offset": 0xF7A97C,
        "num_monsters": 3,
        "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
        "L_values": [0, 1, 3],
        "notes": "Ground melee + caster + flying"
    },
    {
        "name": "Cavern F7 Area1",
        "group_offset": 0xF8E9A0,
        "num_monsters": 4,
        "monsters": ["Cave-Bear", "Blue-Slime", "Spirit-Ball", "Ogre"],
        "L_values": [11, 7, 8, 14],
        "notes": "Aggressive bear, passive slime, floating ball, large ogre"
    },
    {
        "name": "Castle F1 Area1",
        "group_offset": 0x23FF1B4,
        "num_monsters": 3,
        "monsters": ["Zombie", "Harpy", "Wolf"],
        "L_values": [2, 3, 4],
        "notes": "Slow zombie, flying harpy, fast wolf"
    },
]

# ===========================================================================
# Data reading utilities
# ===========================================================================

def hex_dump(data, base_offset, bytes_per_line=16):
    """Generate hex dump with ASCII view."""
    lines = []
    for i in range(0, len(data), bytes_per_line):
        addr = base_offset + i
        hex_parts = []
        ascii_parts = []
        for j in range(bytes_per_line):
            if i + j < len(data):
                b = data[i + j]
                hex_parts.append(f'{b:02X}')
                ascii_parts.append(chr(b) if 32 <= b < 127 else '.')
            else:
                hex_parts.append('  ')
                ascii_parts.append(' ')

        # Group by 4 bytes for readability
        hex_grouped = ' '.join(hex_parts[:4]) + '  ' + ' '.join(hex_parts[4:8]) + '  ' + \
                      ' '.join(hex_parts[8:12]) + '  ' + ' '.join(hex_parts[12:16])
        ascii_str = ''.join(ascii_parts)
        lines.append(f'  {addr:08X}: {hex_grouped}  |{ascii_str}|')
    return '\n'.join(lines)


def read_uint32_array(data, offset, max_count=64):
    """Read uint32 LE array until 0 or max_count."""
    result = []
    for i in range(max_count):
        pos = offset + i * 4
        if pos + 4 > len(data):
            break
        val = struct.unpack_from('<I', data, pos)[0]
        result.append(val)
        # Stop at three consecutive zeros (end of table)
        if i >= 2 and result[-1] == 0 and result[-2] == 0 and result[-3] == 0:
            break
    return result


def read_assignment_entries(blaze, group_offset, num_monsters):
    """Read the 8-byte assignment entries before the group."""
    assign_start = group_offset - num_monsters * 8
    entries = []
    for i in range(num_monsters):
        off = assign_start + i * 8
        data = blaze[off:off+8]
        L = data[1]
        R = data[5]
        entries.append({
            'slot': i,
            'L': L,
            'R': R,
            'raw': data.hex(),
            'offset': off
        })
    return entries


def analyze_behavior_block(blaze, script_start, offset, L_value, monster_name):
    """Analyze a single behavior block."""
    abs_addr = script_start + offset
    data = blaze[abs_addr:abs_addr + 512]

    result = {
        'L': L_value,
        'monster': monster_name,
        'abs_offset': abs_addr,
        'rel_offset': offset,
    }

    # Parse the 32-byte header section
    # Based on analysis, this contains behavioral parameters
    result['params'] = {}

    # Read as uint16 LE values
    for i in range(0, 32, 2):
        val = struct.unpack_from('<H', data, i)[0]
        result['params'][f'param_{i:02X}'] = val

    # Named fields (tentative meanings based on observation)
    result['behavior'] = {
        'unk_00': struct.unpack_from('<H', data, 0)[0],    # Often 0, sometimes large value
        'flags_02': struct.unpack_from('<H', data, 2)[0],   # Type flags?
        'timer_04': struct.unpack_from('<H', data, 4)[0],   # Timer value 1
        'timer_06': struct.unpack_from('<H', data, 6)[0],   # Timer value 2
        'timer_08': struct.unpack_from('<H', data, 8)[0],   # Timer value 3
        'timer_0A': struct.unpack_from('<H', data, 10)[0],  # Timer value 4
        'dist_0C': struct.unpack_from('<H', data, 12)[0],   # Distance/range?
        'dist_0E': struct.unpack_from('<H', data, 14)[0],   # Distance/range?
        'val_10': struct.unpack_from('<H', data, 16)[0],    # Unknown
        'val_12': struct.unpack_from('<H', data, 18)[0],    # Unknown
        'val_14': struct.unpack_from('<H', data, 20)[0],    # Unknown
        'val_16': struct.unpack_from('<H', data, 22)[0],    # Unknown
        'val_18': struct.unpack_from('<H', data, 24)[0],    # Unknown
        'val_1A': struct.unpack_from('<H', data, 26)[0],    # Unknown
        'val_1C': struct.unpack_from('<H', data, 28)[0],    # Unknown
        'val_1E': struct.unpack_from('<H', data, 30)[0],    # Unknown
    }

    # Scan for resource definition entries (type 5, 7, 14, etc.)
    result['resources'] = []
    i = 0x20
    while i < min(len(data), 0x100):
        if i + 8 > len(data):
            break

        res_offset = struct.unpack_from('<I', data, i)[0]
        type_byte = data[i+4]
        idx = data[i+5]
        slot = data[i+6]
        flag = data[i+7]

        # Terminator check
        if res_offset == 0 and type_byte == 0 and idx == 0:
            break

        # Known resource types
        if type_byte in [4, 5, 6, 7, 14]:
            result['resources'].append({
                'offset_in_block': i,
                'resource_offset': res_offset,
                'type': type_byte,
                'idx': idx,
                'slot': slot,
                'flag': flag
            })

        i += 8

    return result


# ===========================================================================
# Main analysis
# ===========================================================================

def main():
    print("=" * 90)
    print("  AI BEHAVIOR BLOCK ANALYSIS")
    print("  Blaze & Blade: Eternal Quest - Reverse Engineering Tool")
    print("=" * 90)
    print()

    # Load BLAZE.ALL
    print(f"Loading {BLAZE_ALL}...")
    blaze = bytearray(BLAZE_ALL.read_bytes())
    print(f"Loaded {len(blaze):,} bytes\n")

    all_results = []

    for area in AREAS:
        print("=" * 90)
        print(f"  {area['name']}")
        print("=" * 90)
        print(f"  Group offset: 0x{area['group_offset']:X}")
        print(f"  Monsters: {', '.join(area['monsters'])}")
        print(f"  L values: {area['L_values']}")
        print()

        # Calculate script area start
        script_start = area['group_offset'] + area['num_monsters'] * 96
        print(f"Script area starts at: 0x{script_start:X}\n")

        # Read assignment entries
        assignments = read_assignment_entries(blaze, area['group_offset'], area['num_monsters'])
        print("Assignment entries:")
        for a in assignments:
            monster = area['monsters'][a['slot']]
            print(f"  Slot {a['slot']} ({monster:20s}): L={a['L']:2d} R={a['R']:2d} [{a['raw']}]")
        print()

        # Read root offset table
        script_data = blaze[script_start:script_start + 4096]
        root_table = read_uint32_array(script_data, 0)

        print(f"Root offset table ({len(root_table)} entries):")
        for i, offset in enumerate(root_table[:20]):  # Show first 20
            if offset == 0:
                print(f"  root[{i:2d}] = NULL")
            else:
                abs_addr = script_start + offset
                print(f"  root[{i:2d}] = 0x{offset:04X} (abs: 0x{abs_addr:X})")
        print()

        # Analyze behavior blocks for each monster
        area_results = {
            'area': area['name'],
            'script_start': script_start,
            'assignments': assignments,
            'behaviors': []
        }

        for slot, L in enumerate(area['L_values']):
            monster = area['monsters'][slot]

            print("-" * 90)
            print(f"  Behavior block for L={L} ({monster})")
            print("-" * 90)

            if L >= len(root_table) or root_table[L] == 0:
                print(f"  root[{L}] is NULL - no unique behavior block")
                print()
                area_results['behaviors'].append({
                    'L': L,
                    'monster': monster,
                    'is_null': True
                })
                continue

            offset = root_table[L]
            behavior = analyze_behavior_block(blaze, script_start, offset, L, monster)
            area_results['behaviors'].append(behavior)

            # Print analysis
            print(f"  Absolute offset: 0x{behavior['abs_offset']:X}")
            print(f"  Relative offset: 0x{behavior['rel_offset']:04X}")
            print()

            print("  Behavior parameters (32-byte header):")
            b = behavior['behavior']
            print(f"    [00] unk_00   = {b['unk_00']:6d} (0x{b['unk_00']:04X})")
            print(f"    [02] flags_02 = {b['flags_02']:6d}")
            print(f"    [04] timer_04 = {b['timer_04']:6d} (0x{b['timer_04']:04X})")
            print(f"    [06] timer_06 = {b['timer_06']:6d} (0x{b['timer_06']:04X})")
            print(f"    [08] timer_08 = {b['timer_08']:6d} (0x{b['timer_08']:04X})")
            print(f"    [0A] timer_0A = {b['timer_0A']:6d} (0x{b['timer_0A']:04X})")
            print(f"    [0C] dist_0C  = {b['dist_0C']:6d} (0x{b['dist_0C']:04X})")
            print(f"    [0E] dist_0E  = {b['dist_0E']:6d} (0x{b['dist_0E']:04X})")
            print(f"    [10] val_10   = {b['val_10']:6d}")
            print(f"    [12] val_12   = {b['val_12']:6d}")
            print(f"    [14-1F] = {b['val_14']}, {b['val_16']}, {b['val_18']}, {b['val_1A']}, {b['val_1C']}, {b['val_1E']}")
            print()

            print("  Resource definitions:")
            if behavior['resources']:
                for r in behavior['resources'][:10]:
                    type_names = {4: 'type4', 5: 'bytecode', 6: 'type6', 7: 'per-slot', 14: 'type14'}
                    type_name = type_names.get(r['type'], f"type{r['type']}")
                    print(f"    [0x{r['offset_in_block']:02X}] off=0x{r['resource_offset']:04X} {type_name:10s} idx=0x{r['idx']:02X} slot={r['slot']}")
            else:
                print("    (none found)")
            print()

            # Hex dump first 96 bytes (header + start of resource table)
            print("  Hex dump (first 96 bytes):")
            abs_addr = behavior['abs_offset']
            data = blaze[abs_addr:abs_addr + 96]
            print(hex_dump(data, abs_addr))
            print()

        all_results.append(area_results)

    # Comparative analysis
    print("\n")
    print("=" * 90)
    print("  COMPARATIVE ANALYSIS")
    print("=" * 90)
    print()

    print("Side-by-side comparison of behavior blocks:")
    print()

    for area_result in all_results:
        print(f"\n{area_result['area']}:")
        print("-" * 90)

        behaviors = [b for b in area_result['behaviors'] if not b.get('is_null', False)]

        if not behaviors:
            print("  No behavior blocks in this area")
            continue

        # Compare behavior parameters
        print("\nBehavior parameters comparison:")
        print(f"  {'Monster':20s} | flags | timer_04 | timer_06 | timer_08 | timer_0A | dist_0C | dist_0E | val_10")
        print(f"  {'-'*20}-+-------+----------+----------+----------+----------+---------+---------+-------")

        for b in behaviors:
            monster = b['monster'][:20].ljust(20)
            beh = b['behavior']
            print(f"  {monster} | {beh['flags_02']:5d} | {beh['timer_04']:8d} | {beh['timer_06']:8d} | "
                  f"{beh['timer_08']:8d} | {beh['timer_0A']:8d} | {beh['dist_0C']:7d} | {beh['dist_0E']:7d} | {beh['val_10']:6d}")

        # Show resource counts
        print("\nResource definitions per monster:")
        for b in behaviors:
            monster = b['monster'][:20]
            res_count = len(b['resources'])
            print(f"  {monster:20s}: {res_count} resources")

    print("\n")
    print("=" * 90)
    print("  ANALYSIS COMPLETE")
    print("=" * 90)
    print()
    print("Key observations to investigate:")
    print("  1. Header fields at bytes 0-11: likely timer or state values")
    print("  2. Uint16 clusters: may represent stats, timers, or distances")
    print("  3. FFFF markers: indicate spawn record boundaries")
    print("  4. Compare similar monster types across areas for patterns")
    print("  5. Compare aggressive vs. passive monsters for aggression flags")
    print()

    # Save results to JSON for detailed analysis
    output_file = SCRIPT_DIR / "ai_blocks_dump.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    print(f"Detailed results saved to: {output_file}")
    print()


if __name__ == '__main__':
    main()
