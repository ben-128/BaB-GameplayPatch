"""
Detailed analysis of the pre-group header region for spawn groups.

Goal: Understand the 8-byte records and other structures that exist
between the formation pairs and the data further back.

We now know:
- L value in formation pairs controls AI/BEHAVIOR (not visual)
- Something else controls the 3D model/visual
- Candidates: 8-byte records, offset table, or other pre-group data
"""

import struct
import json
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
SPAWN_DIR = SCRIPT_DIR.parent / "data" / "spawn_groups"


def hex_dump(data, base_offset, bytes_per_line=16):
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
        # Group in 4-byte chunks
        hex_grouped = ' '.join(hex_parts[:4]) + '  ' + ' '.join(hex_parts[4:8]) + '  ' + ' '.join(hex_parts[8:12]) + '  ' + ' '.join(hex_parts[12:16])
        ascii_str = ''.join(ascii_parts)
        lines.append(f'  {addr:08X}  {hex_grouped}  |{ascii_str}|')
    return '\n'.join(lines)


def find_formation_pairs_end(blaze_data, group_offset, num_monsters):
    """Find formation pairs scanning backward from group_offset."""
    pairs = []
    pos = group_offset - 8

    while pos >= group_offset - 128 and len(pairs) < num_monsters + 2:
        right_entry = blaze_data[pos+4:pos+8]
        left_entry = blaze_data[pos:pos+4]

        if len(right_entry) < 4 or len(left_entry) < 4:
            break

        r_slot, r_param, r_extra, r_flag = right_entry[0], right_entry[1], right_entry[2], right_entry[3]
        l_slot, l_param, l_extra, l_flag = left_entry[0], left_entry[1], left_entry[2], left_entry[3]

        if r_flag == 0x40 and r_extra == 0x00 and l_flag == 0x00 and l_extra == 0x00:
            if l_slot < 16 and r_slot < 16:
                pairs.insert(0, {
                    'offset': pos,
                    'l_slot': l_slot, 'l_param': l_param,
                    'r_slot': r_slot, 'r_param': r_param,
                    'hex': blaze_data[pos:pos+8].hex()
                })
                pos -= 8
                continue
        break

    return pairs, pos + 8 if pairs else group_offset


def load_all_spawn_groups():
    groups = []
    for fname in sorted(os.listdir(SPAWN_DIR)):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(SPAWN_DIR, fname), 'r') as f:
            data = json.load(f)
        level = data.get('level_name', fname)
        for g in data['groups']:
            groups.append({
                'level': level,
                'name': g['name'],
                'offset': int(g['offset'], 16),
                'monsters': g['monsters'],
                'num_monsters': len(g['monsters'])
            })
    return groups


def analyze_group(blaze_data, group, verbose=True):
    offset = group['offset']
    num = group['num_monsters']

    # Verify monster names
    names = []
    for i in range(num):
        name_off = offset + i * 96
        name = blaze_data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii', errors='replace')
        names.append(name)

    # Find formation pairs
    pairs, pairs_start = find_formation_pairs_end(blaze_data, offset, num)

    if verbose:
        print(f"\n{'=' * 90}")
        print(f"  {group['level']} / {group['name']}")
        print(f"  Offset: 0x{offset:X} | Monsters: {num} | {', '.join(names)}")
        print(f"{'=' * 90}")

        # Formation pairs
        print(f"\n  --- FORMATION PAIRS (0x{pairs_start:X} to 0x{offset:X}, {len(pairs)} pairs) ---")
        for p in pairs:
            print(f"    0x{p['offset']:08X}: [{p['hex'][:8]}] [{p['hex'][8:]}]"
                  f"  slot={p['l_slot']} L={p['l_param']:2d} (AI) | slot={p['r_slot']} R={p['r_param']:2d}")

        # Dump 512 bytes before formation pairs
        dump_size = 512
        dump_start = max(0, pairs_start - dump_size)
        pre_data = blaze_data[dump_start:pairs_start]

        print(f"\n  --- RAW HEX: 0x{dump_start:X} to 0x{pairs_start:X} ({len(pre_data)} bytes before pairs) ---")
        print(hex_dump(pre_data, dump_start))

        # Now try to identify structures working backward from formation pairs
        print(f"\n  --- STRUCTURE ANALYSIS (backward from formation pairs) ---")

        # Region 1: Just before formation pairs - look for offset table (uint32 values)
        # These should be small-ish values like 0x24, 0x2C, 0x34, etc.
        scan_start = max(0, pairs_start - 128)
        scan_data = blaze_data[scan_start:pairs_start]

        # Find the offset table: consecutive uint32 values with small increments
        print(f"\n  [Scanning for uint32 offset table before pairs]")
        for back in range(0, len(scan_data) - 4, 4):
            pos = len(scan_data) - 4 - back
            if pos < 0:
                break
            val = struct.unpack_from('<I', scan_data, pos)[0]
            abs_addr = scan_start + pos
            if val == 0:
                # Zero - could be terminator
                print(f"    0x{abs_addr:08X}: uint32 = 0x{val:08X} (zero/terminator?)")
            elif val < 0x1000:
                # Small value - likely an offset
                print(f"    0x{abs_addr:08X}: uint32 = 0x{val:08X} ({val})")
            else:
                # Large value - not an offset, stop
                print(f"    0x{abs_addr:08X}: uint32 = 0x{val:08X} (large - end of offset table)")
                break

        # Region 2: Look for 8-byte records
        # Try to find repeating 8-byte structures
        print(f"\n  [Scanning for 8-byte record patterns]")

        # Work backward from the offset table area
        # The 8-byte records should be before the offset table
        # Pattern: [4 bytes][4 bytes] where second 4 bytes has specific structure

        # Let's just do a thorough uint32 pair dump for 256 bytes before the offset table
        deeper_start = max(0, pairs_start - 384)
        deeper_data = blaze_data[deeper_start:pairs_start]

        print(f"\n  [uint32 pair view: 0x{deeper_start:X} to 0x{pairs_start:X}]")
        for i in range(0, len(deeper_data), 8):
            abs_addr = deeper_start + i
            if i + 8 <= len(deeper_data):
                w1 = struct.unpack_from('<I', deeper_data, i)[0]
                w2 = struct.unpack_from('<I', deeper_data, i + 4)[0]
                b = list(deeper_data[i:i+8])
                # Also show as byte view
                print(f"    0x{abs_addr:08X}: [{w1:08X}] [{w2:08X}]  bytes={b}")

    return {
        'names': names,
        'pairs': pairs,
        'pairs_start': pairs_start
    }


def main():
    print("=" * 90)
    print("  PRE-GROUP STRUCTURE ANALYSIS")
    print("  Goal: Find the 8-byte records that may control monster visuals")
    print("=" * 90)

    blaze_data = BLAZE_ALL.read_bytes()
    print(f"  BLAZE.ALL: {len(blaze_data):,} bytes")

    groups = load_all_spawn_groups()
    print(f"  Spawn groups: {len(groups)}")

    # Analyze a selection of groups from different zones with different monster counts
    selected = []
    # Cavern Floor 1 Area 1 (3 monsters) - our test target
    selected.extend([g for g in groups if g['level'] == 'Cavern of Death' and 'Floor 1 - Area 1' in g['name']][:1])
    # Cavern Floor 7 Area 1 (4 monsters, has Ogre) - reference for L=14
    selected.extend([g for g in groups if g['level'] == 'Cavern of Death' and 'Floor 7 - Area 1' in g['name']][:1])
    # Forest Floor 1 Area 1 (3 monsters)
    selected.extend([g for g in groups if g['level'] == 'The Forest' and 'Floor 1 - Area 1' in g['name']][:1])
    # Castle Floor 1 Area 1 (3 monsters)
    selected.extend([g for g in groups if g['level'] == 'Castle of Vamp' and 'Floor 1 - Area 1' in g['name']][:1])
    # A group with more monsters
    selected.extend([g for g in groups if g['level'] == 'The Forest' and 'Area 4' in g['name']][:1])

    for group in selected:
        analyze_group(blaze_data, group)

    # CROSS-GROUP COMPARISON
    print("\n" + "=" * 90)
    print("  CROSS-GROUP: Compare relative offsets of offset-table entries")
    print("=" * 90)

    for group in selected:
        offset = group['offset']
        num = group['num_monsters']
        pairs, pairs_start = find_formation_pairs_end(blaze_data, offset, num)

        # Read 64 bytes before pairs, show as uint32
        pre = blaze_data[pairs_start - 64:pairs_start]
        vals = []
        for i in range(0, len(pre), 4):
            vals.append(struct.unpack_from('<I', pre, i)[0])

        names_str = ', '.join(group['monsters'][:3])
        print(f"\n  {group['level']:20s} {group['name']:20s} ({num} mon: {names_str})")
        print(f"    Pairs at: 0x{pairs_start:X}  Group at: 0x{offset:X}")
        print(f"    64 bytes before pairs as uint32:")
        for i, v in enumerate(vals):
            abs_off = pairs_start - 64 + i * 4
            rel = abs_off - offset
            print(f"      0x{abs_off:08X} (rel {rel:#06x}): 0x{v:08X} ({v:10d})  bytes={list(blaze_data[abs_off:abs_off+4])}")


if __name__ == '__main__':
    main()
