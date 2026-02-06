#!/usr/bin/env python3
"""
analyze_room_script.py
Analyze the "room script" area AFTER spawn groups to find monster type references.

According to SPAWN_MODDING_RESEARCH.md, there are 5-18KB gaps between spawn groups
containing bytecode (0x2C, 0x2D, 0x0D, 0x04, 0xFF delimiters), text strings,
and 3D coordinates. This script searches these areas for monster type IDs.
"""

import struct
import json
from pathlib import Path

# ----- Paths -----
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

OUTPUT_FILE = SCRIPT_DIR.parent / "data" / "room_script_analysis.txt"

# Test case: Cavern of Death Floor 1 Area 1
# Monsters: Lv20.Goblin (ID 84/0x54), Goblin-Shaman (ID 59/0x3B), Giant-Bat (ID 49/0x31)
GROUP_OFFSET = 0xF7A97C
GROUP_SIZE = 3 * 96  # 3 monsters
SCRIPT_SCAN_SIZE = 10000  # Scan 10KB after the group

TARGET_IDS = [
    {'name': 'Lv20.Goblin', 'id': 84, 'hex': 0x54},
    {'name': 'Goblin-Shaman', 'id': 59, 'hex': 0x3B},
    {'name': 'Giant-Bat', 'id': 49, 'hex': 0x31},
]


def search_patterns(data, start_pos, end_pos, target_ids):
    """Search for various patterns that might be monster type IDs."""
    search_data = data[start_pos:end_pos]

    results = []

    # Pattern 1: Single uint8
    for target in target_ids:
        monster_id = target['id']
        positions = []
        for i in range(len(search_data)):
            if search_data[i] == monster_id:
                positions.append(start_pos + i)

        if positions:
            results.append({
                'pattern': 'uint8',
                'monster': target['name'],
                'id': monster_id,
                'hex': f"0x{monster_id:02X}",
                'count': len(positions),
                'positions': positions[:20],  # First 20
            })

    # Pattern 2: uint16 LE
    for target in target_ids:
        monster_id = target['id']
        target_bytes = struct.pack('<H', monster_id)
        positions = []
        i = 0
        while i < len(search_data) - 1:
            if search_data[i:i+2] == target_bytes:
                positions.append(start_pos + i)
                i += 2
            else:
                i += 1

        if positions:
            results.append({
                'pattern': 'uint16_le',
                'monster': target['name'],
                'id': monster_id,
                'hex': f"0x{monster_id:04X}",
                'count': len(positions),
                'positions': positions[:20],
            })

    # Pattern 3: Sequences of all 3 IDs (uint8) within 32 bytes
    id_sequence = [t['id'] for t in target_ids]
    for i in range(len(search_data) - 32):
        window = search_data[i:i+32]
        if all(monster_id in window for monster_id in id_sequence):
            # Found all 3 IDs within 32 bytes!
            results.append({
                'pattern': 'sequence_uint8_window32',
                'monster': 'ALL',
                'ids': id_sequence,
                'hex': ' '.join(f"{x:02X}" for x in id_sequence),
                'position': start_pos + i,
                'window_hex': window.hex(' '),
            })

    # Pattern 4: Look for opcode patterns near IDs
    # Common PSX opcodes: 0x2C, 0x2D, 0x0D, 0x04, 0xFF
    opcodes = [0x2C, 0x2D, 0x0D, 0x04, 0xFF]
    for target in target_ids:
        monster_id = target['id']
        for i in range(len(search_data)):
            if search_data[i] == monster_id:
                # Check nearby bytes for opcodes
                context_start = max(0, i - 16)
                context_end = min(len(search_data), i + 16)
                context = search_data[context_start:context_end]

                opcode_count = sum(1 for b in context if b in opcodes)
                if opcode_count >= 3:  # At least 3 opcodes nearby
                    results.append({
                        'pattern': 'uint8_with_opcodes',
                        'monster': target['name'],
                        'id': monster_id,
                        'position': start_pos + i,
                        'opcode_count': opcode_count,
                        'context': context.hex(' '),
                    })

    return results


def analyze_hex_dump(data, offset, size=256):
    """Create a hex dump with ASCII representation."""
    lines = []
    for i in range(0, min(size, len(data) - offset), 16):
        addr = offset + i
        chunk = data[addr:addr+16]

        hex_part = ' '.join(f"{b:02X}" for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

        lines.append(f"{addr:08X}  {hex_part:<48}  {ascii_part}")

    return '\n'.join(lines)


def main():
    print("=" * 80)
    print("  ROOM SCRIPT ANALYSIS")
    print("=" * 80)
    print()

    # Load BLAZE.ALL
    print(f"Loading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"  Size: {len(data):,} bytes")
    print()

    # Define search area
    script_start = GROUP_OFFSET + GROUP_SIZE
    script_end = script_start + SCRIPT_SCAN_SIZE

    print(f"Analyzing room script area:")
    print(f"  Group at: 0x{GROUP_OFFSET:X}")
    print(f"  Script starts at: 0x{script_start:X}")
    print(f"  Script ends at: 0x{script_end:X}")
    print(f"  Scan size: {SCRIPT_SCAN_SIZE:,} bytes")
    print()

    print(f"Searching for monster type IDs:")
    for target in TARGET_IDS:
        print(f"  {target['name']}: ID {target['id']} (0x{target['id']:02X})")
    print()

    # Search for patterns
    print("Searching for patterns...")
    results = search_patterns(data, script_start, script_end, TARGET_IDS)
    print(f"  Found {len(results)} pattern matches")
    print()

    # Generate report
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("ROOM SCRIPT ANALYSIS RESULTS")
    output_lines.append("=" * 80)
    output_lines.append("")
    output_lines.append(f"Group offset: 0x{GROUP_OFFSET:X}")
    output_lines.append(f"Script area: 0x{script_start:X} - 0x{script_end:X}")
    output_lines.append("")

    # Group results by pattern type
    by_pattern = {}
    for r in results:
        pattern = r['pattern']
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(r)

    for pattern, matches in sorted(by_pattern.items()):
        output_lines.append(f"\nPattern: {pattern.upper()}")
        output_lines.append("-" * 80)

        for match in matches:
            if pattern == 'sequence_uint8_window32':
                output_lines.append(f"\n  ALL MONSTER IDS FOUND IN WINDOW:")
                output_lines.append(f"    Position: 0x{match['position']:X}")
                output_lines.append(f"    IDs: {match['hex']}")
                output_lines.append(f"    Window (32 bytes):")
                output_lines.append(f"      {match['window_hex']}")

            elif pattern == 'uint8_with_opcodes':
                output_lines.append(f"\n  {match['monster']} (ID {match['id']}):")
                output_lines.append(f"    Position: 0x{match['position']:X}")
                output_lines.append(f"    Opcodes nearby: {match['opcode_count']}")
                output_lines.append(f"    Context (32 bytes):")
                output_lines.append(f"      {match['context']}")

            else:
                output_lines.append(f"\n  {match['monster']} (ID {match['id']}):")
                output_lines.append(f"    Count: {match['count']}")
                if 'positions' in match:
                    pos_hex = [f"0x{p:X}" for p in match['positions'][:10]]
                    output_lines.append(f"    Positions: {', '.join(pos_hex)}")
                    if match['count'] > 10:
                        output_lines.append(f"    (... and {match['count'] - 10} more)")

    # Hex dumps for interesting areas
    if any(r['pattern'] == 'sequence_uint8_window32' for r in results):
        output_lines.append("\n\n" + "=" * 80)
        output_lines.append("HEX DUMPS OF SEQUENCE MATCHES")
        output_lines.append("=" * 80)

        for r in results:
            if r['pattern'] == 'sequence_uint8_window32':
                output_lines.append(f"\n\nContext around 0x{r['position']:X} (ALL IDs found):")
                output_lines.append("-" * 80)
                dump_start = max(script_start, r['position'] - 128)
                output_lines.append(analyze_hex_dump(data, dump_start, 512))

    # Save report
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"Report saved to {OUTPUT_FILE}")
    print()

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    for pattern, matches in sorted(by_pattern.items()):
        total = len(matches)
        print(f"{pattern}: {total} match(es)")

    print()
    print("Check the output file for detailed results and hex dumps.")
    print()


if __name__ == '__main__':
    main()
