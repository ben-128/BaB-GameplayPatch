#!/usr/bin/env python3
"""
analyze_spawn_commands.py
Analyze the bytecode structures that contain monster type IDs.

Based on room_script_analysis, monster type IDs appear in specific bytecode
structures with opcodes nearby. This script examines these structures in detail
to understand the spawn command format.
"""

import struct
from pathlib import Path

# ----- Paths -----
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

OUTPUT_FILE = SCRIPT_DIR.parent / "data" / "spawn_commands_analysis.txt"

# Positions found in room_script_analysis with monster IDs
INTERESTING_POSITIONS = [
    {'name': 'Goblin-Shaman', 'id': 59, 'offset': 0xF7AECC, 'context': '00 0b 09 00 e2 05 29 ff d2 f6 00 00 00 00 00 00 3b 02 ff ff ff ff ff ff 00 00 00 00 00 00 00 00'},
    {'name': 'Giant-Bat #1', 'id': 49, 'offset': 0xF7B4D0, 'context': '00 00 00 00 00 00 04 00 02 ff 00 00 d6 00 f2 fb 31 01 00 00 d0 07 00 00 ff ff ff ff ff ff ff ff'},
    {'name': 'Lv20.Goblin #1', 'id': 84, 'offset': 0xF7B5EC, 'context': 'ff ff ff ff 00 00 00 00 11 00 05 00 82 ff 00 00 54 f4 ec ff 44 ef 00 00 00 0e 00 00 92 01 ff ff'},
    {'name': 'Lv20.Goblin #2', 'id': 84, 'offset': 0xF7C474, 'context': '00 00 00 00 05 00 02 00 82 ff 00 00 60 13 24 ff 54 fe 00 00 00 08 00 00 8e 03 ff ff ff ff ff ff'},
]


def hex_dump(data, offset, size=256, highlight_byte=None):
    """Create a detailed hex dump with ASCII."""
    lines = []
    for i in range(0, min(size, len(data) - offset), 16):
        addr = offset + i
        chunk = data[addr:addr+16]

        # Hex part
        hex_bytes = []
        for j, b in enumerate(chunk):
            if highlight_byte is not None and addr + j == highlight_byte:
                hex_bytes.append(f"[{b:02X}]")
            else:
                hex_bytes.append(f"{b:02X}")
        hex_part = ' '.join(hex_bytes)

        # ASCII part
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

        lines.append(f"{addr:08X}  {hex_part:<60}  {ascii_part}")

    return '\n'.join(lines)


def analyze_structure(data, id_offset, monster_id):
    """Analyze the structure containing a monster ID."""
    # Read 64 bytes before and after the ID
    start = max(0, id_offset - 64)
    end = min(len(data), id_offset + 64)
    region = data[start:end]

    id_pos_in_region = id_offset - start

    analysis = {
        'offset': f"0x{id_offset:X}",
        'monster_id': monster_id,
        'hex_dump': None,
        'structure_guess': None,
    }

    # Try to identify the structure
    # Look for patterns like:
    # [header bytes] [monster_id] [params...] [0xFF terminators]

    # Check if there are 0xFF bytes after the ID (common terminator)
    ff_count_after = 0
    for i in range(id_pos_in_region + 1, min(len(region), id_pos_in_region + 20)):
        if region[i] == 0xFF:
            ff_count_after += 1
        else:
            break

    # Check bytes immediately after ID
    if id_pos_in_region + 8 < len(region):
        next_bytes = region[id_pos_in_region:id_pos_in_region+8]

        # Pattern check
        if len(next_bytes) >= 4:
            byte1 = next_bytes[1]  # Byte right after monster ID
            byte2 = next_bytes[2]
            byte3 = next_bytes[3]

            # Common pattern: [monster_id] [count?] [00] [00]
            if byte2 == 0x00 and byte3 == 0x00:
                analysis['structure_guess'] = {
                    'format': '[ID] [param] [00] [00] ...',
                    'monster_id': monster_id,
                    'param1': byte1,
                    'param1_hex': f"0x{byte1:02X}",
                }

            # Pattern: [monster_id] [00] [00] [00]
            elif byte1 == 0x00 and byte2 == 0x00 and byte3 == 0x00:
                analysis['structure_guess'] = {
                    'format': '[ID] [00] [00] [00] ...',
                    'monster_id': monster_id,
                }

    # Look for potential coordinates (int16 values)
    coords = []
    for i in range(max(0, id_pos_in_region - 16), min(len(region) - 1, id_pos_in_region)):
        if i + 1 < len(region):
            value = struct.unpack('<h', region[i:i+2])[0]  # signed int16
            if -10000 < value < 10000:  # Reasonable coordinate range
                coords.append({'offset': start + i, 'value': value})

    if coords:
        analysis['nearby_coordinates'] = coords

    analysis['hex_dump'] = hex_dump(data, start, 128, id_offset)
    analysis['ff_terminators_after'] = ff_count_after

    return analysis


def find_all_occurrences_in_area(data, area_start, area_end, monster_ids):
    """Find all occurrences of monster IDs in an area and group by distance."""
    occurrences = []

    for monster_id in monster_ids:
        pos = area_start
        while pos < area_end:
            pos = data.find(bytes([monster_id]), pos, area_end)
            if pos == -1:
                break

            occurrences.append({
                'offset': pos,
                'monster_id': monster_id,
            })
            pos += 1

    # Sort by offset
    occurrences.sort(key=lambda x: x['offset'])

    # Group occurrences that are close together (within 128 bytes = potential spawn table)
    groups = []
    current_group = []

    for occ in occurrences:
        if not current_group:
            current_group.append(occ)
        elif occ['offset'] - current_group[-1]['offset'] <= 128:
            current_group.append(occ)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [occ]

    if current_group:
        groups.append(current_group)

    return groups


def main():
    print("=" * 80)
    print("  SPAWN COMMAND STRUCTURE ANALYSIS")
    print("=" * 80)
    print()

    # Load BLAZE.ALL
    print(f"Loading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"  Size: {len(data):,} bytes")
    print()

    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("SPAWN COMMAND STRUCTURE ANALYSIS")
    output_lines.append("=" * 80)
    output_lines.append("")

    # Analyze each interesting position
    for pos_info in INTERESTING_POSITIONS:
        print(f"Analyzing {pos_info['name']} at 0x{pos_info['offset']:X}...")

        analysis = analyze_structure(data, pos_info['offset'], pos_info['id'])

        output_lines.append(f"\n{pos_info['name']} (ID {pos_info['id']}) at {analysis['offset']}")
        output_lines.append("-" * 80)

        if analysis['structure_guess']:
            output_lines.append(f"\nStructure Pattern: {analysis['structure_guess']['format']}")
            for key, value in analysis['structure_guess'].items():
                if key != 'format':
                    output_lines.append(f"  {key}: {value}")

        if 'nearby_coordinates' in analysis:
            output_lines.append(f"\nNearby potential coordinates (int16):")
            for coord in analysis['nearby_coordinates'][:10]:
                output_lines.append(f"  0x{coord['offset']:X}: {coord['value']}")

        output_lines.append(f"\nFF terminators after ID: {analysis['ff_terminators_after']}")

        output_lines.append(f"\nHex dump (128 bytes, ID byte in brackets):")
        output_lines.append(analysis['hex_dump'])
        output_lines.append("")

    # Find clustered occurrences
    print("\nSearching for clustered monster ID occurrences...")
    script_start = 0xF7AA9C
    script_end = 0xF7D1AC
    monster_ids = [84, 59, 49]

    groups = find_all_occurrences_in_area(data, script_start, script_end, monster_ids)

    output_lines.append("\n" + "=" * 80)
    output_lines.append("CLUSTERED OCCURRENCES (within 128 bytes)")
    output_lines.append("=" * 80)
    output_lines.append("")

    for i, group in enumerate(groups):
        if len(group) >= 2:  # Only show groups with 2+ IDs
            output_lines.append(f"\nCluster #{i+1}: {len(group)} IDs")
            output_lines.append(f"  Range: 0x{group[0]['offset']:X} - 0x{group[-1]['offset']:X}")
            output_lines.append(f"  IDs: {', '.join(str(x['monster_id']) for x in group)}")

            # Show hex dump of the cluster
            cluster_start = group[0]['offset'] - 16
            cluster_end = group[-1]['offset'] + 32
            output_lines.append(f"\n  Hex dump:")
            dump = hex_dump(data, cluster_start, cluster_end - cluster_start)
            for line in dump.split('\n'):
                output_lines.append(f"  {line}")
            output_lines.append("")

    # Save report
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"\nReport saved to {OUTPUT_FILE}")
    print()
    print("=" * 80)
    print("KEY FINDINGS TO CHECK:")
    print("=" * 80)
    print()
    print("1. Look for consistent structure patterns across all positions")
    print("2. Check if clustered IDs represent spawn group definitions")
    print("3. Identify the command format (opcode + monster_id + params)")
    print("4. Test patching these positions to confirm they control spawn behavior")
    print()


if __name__ == '__main__':
    main()
