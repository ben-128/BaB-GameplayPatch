#!/usr/bin/env python3
"""
compare_spawn_groups.py
Compare multiple spawn groups to find consistent patterns for monster type IDs.

This script analyzes several spawn groups simultaneously to identify where
the monster type IDs (that control visuals/AI/spells/loot) are stored.
"""

import struct
import json
from pathlib import Path
from collections import defaultdict

# ----- Paths -----
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

OUTPUT_FILE = SCRIPT_DIR.parent / "data" / "spawn_comparison_analysis.json"

# Test multiple groups
TEST_GROUPS = [
    {
        'name': 'Cavern Floor 1 Area 1',
        'offset': 0xF7A97C,
        'expected_monsters': ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat'],
        'expected_ids': [84, 59, 49],
    },
    {
        'name': 'Cavern Floor 1 Area 2',
        'offset': 0xF7E1A8,
        'expected_monsters': ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat', 'Goblin-Leader'],
        'expected_ids': [84, 59, 49, 58],
    },
    {
        'name': 'Forest Area',
        'offset': 0x1498278,  # Goblin-Shaman position
        'expected_monsters': ['Goblin-Shaman'],
        'expected_ids': [59],
    },
]

# Search ranges to check
SEARCH_RANGES = [
    {'name': 'Near (-64 to -16)', 'start': -64, 'end': -16},
    {'name': 'Formation region (-176 to -64)', 'start': -176, 'end': -64},
    {'name': 'Medium range (-512 to -176)', 'start': -512, 'end': -176},
    {'name': 'Far range (-2048 to -512)', 'start': -2048, 'end': -512},
]


def load_monster_index():
    """Load monster ID mapping from individual monster JSON files."""
    mapping = {}

    monster_dirs = [
        PROJECT_ROOT / "Data" / "monster_stats" / "boss",
        PROJECT_ROOT / "Data" / "monster_stats" / "normal_enemies",
    ]

    for monster_dir in monster_dirs:
        if not monster_dir.exists():
            continue

        for json_file in monster_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                name = data.get('name')
                monster_id = data.get('id')
                if name and monster_id is not None:
                    mapping[name] = monster_id
            except:
                pass

    return mapping


def search_ids_in_range(data, group_offset, monster_ids, search_start, search_end):
    """Search for monster IDs in a specific range before the group."""
    if group_offset + search_start < 0:
        search_start = -group_offset

    start_pos = group_offset + search_start
    end_pos = group_offset + search_end
    search_data = data[start_pos:end_pos]

    findings = {
        'uint8': [],
        'uint16_le': [],
        'uint32_le': [],
    }

    # Search for each monster ID
    for monster_id in monster_ids:
        # uint8
        for i in range(len(search_data)):
            if search_data[i] == monster_id:
                rel_offset = search_start + i
                findings['uint8'].append({
                    'id': monster_id,
                    'offset': rel_offset,
                    'hex_offset': f"{rel_offset:+05X}" if rel_offset < 0 else f"+0x{rel_offset:04X}",
                    'context': search_data[max(0, i-4):min(len(search_data), i+5)].hex(' '),
                })

        # uint16 LE
        target_u16 = struct.pack('<H', monster_id)
        i = 0
        while i < len(search_data) - 1:
            if search_data[i:i+2] == target_u16:
                rel_offset = search_start + i
                findings['uint16_le'].append({
                    'id': monster_id,
                    'offset': rel_offset,
                    'hex_offset': f"{rel_offset:+05X}" if rel_offset < 0 else f"+0x{rel_offset:04X}",
                    'context': search_data[max(0, i-4):min(len(search_data), i+6)].hex(' '),
                })
                i += 2
            else:
                i += 1

        # uint32 LE
        target_u32 = struct.pack('<I', monster_id)
        i = 0
        while i < len(search_data) - 3:
            if search_data[i:i+4] == target_u32:
                rel_offset = search_start + i
                findings['uint32_le'].append({
                    'id': monster_id,
                    'offset': rel_offset,
                    'hex_offset': f"{rel_offset:+05X}" if rel_offset < 0 else f"+0x{rel_offset:04X}",
                    'context': search_data[max(0, i-4):min(len(search_data), i+8)].hex(' '),
                })
                i += 4
            else:
                i += 1

    return findings


def read_spawn_group(data, offset):
    """Read a spawn group and return monster names."""
    monsters = []
    pos = offset

    for i in range(6):
        if pos + 96 > len(data):
            break

        name_field = data[pos:pos + 16]
        null_idx = name_field.find(b'\x00')
        if null_idx <= 0:
            break

        name = name_field[:null_idx].decode('ascii', errors='ignore')
        if all(name_field[i] == 0 for i in range(null_idx, 16)):
            monsters.append(name)
            pos += 96
        else:
            break

    return monsters


def main():
    print("=" * 80)
    print("  SPAWN GROUP COMPARISON ANALYSIS")
    print("=" * 80)
    print()

    # Load BLAZE.ALL
    print(f"Loading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"  Size: {len(data):,} bytes")
    print()

    # Load monster IDs
    print(f"Loading monster index...")
    monster_ids_map = load_monster_index()
    print(f"  Loaded {len(monster_ids_map)} monster IDs")
    print()

    # Analyze each test group
    all_results = []

    for test_group in TEST_GROUPS:
        print(f"Analyzing: {test_group['name']} at 0x{test_group['offset']:X}")

        # Verify the monsters at this location
        actual_monsters = read_spawn_group(data, test_group['offset'])
        print(f"  Actual monsters: {', '.join(actual_monsters)}")

        monster_ids = test_group['expected_ids']
        print(f"  Expected IDs: {monster_ids}")
        print()

        group_results = {
            'name': test_group['name'],
            'offset': f"0x{test_group['offset']:X}",
            'monsters': actual_monsters,
            'expected_ids': monster_ids,
            'findings_by_range': {},
        }

        # Search in each range
        for search_range in SEARCH_RANGES:
            range_name = search_range['name']
            findings = search_ids_in_range(
                data,
                test_group['offset'],
                monster_ids,
                search_range['start'],
                search_range['end']
            )

            total_found = len(findings['uint8']) + len(findings['uint16_le']) + len(findings['uint32_le'])

            print(f"  {range_name}: {total_found} matches")
            if total_found > 0:
                if findings['uint8']:
                    print(f"    uint8: {len(findings['uint8'])} matches")
                if findings['uint16_le']:
                    print(f"    uint16: {len(findings['uint16_le'])} matches")
                if findings['uint32_le']:
                    print(f"    uint32: {len(findings['uint32_le'])} matches")

            group_results['findings_by_range'][range_name] = findings

        print()
        all_results.append(group_results)

    # Cross-analysis: Find consistent patterns
    print("=" * 80)
    print("CROSS-GROUP PATTERN ANALYSIS")
    print("=" * 80)
    print()

    # Look for offsets that appear in multiple groups
    offset_patterns = defaultdict(list)

    for result in all_results:
        for range_name, findings in result['findings_by_range'].items():
            for format_type in ['uint8', 'uint16_le', 'uint32_le']:
                for match in findings[format_type]:
                    key = f"{range_name} | {format_type} | {match['hex_offset']}"
                    offset_patterns[key].append({
                        'group': result['name'],
                        'id': match['id'],
                        'context': match['context'],
                    })

    # Report patterns that appear in multiple groups
    print("Patterns appearing in multiple groups:")
    print()

    consistent_patterns = []
    for pattern_key, occurrences in sorted(offset_patterns.items()):
        if len(occurrences) >= 2:  # Appears in at least 2 groups
            consistent_patterns.append({
                'pattern': pattern_key,
                'count': len(occurrences),
                'occurrences': occurrences,
            })
            print(f"{pattern_key}:")
            print(f"  Appears in {len(occurrences)} groups")
            for occ in occurrences:
                print(f"    - {occ['group']}: ID {occ['id']} | {occ['context']}")
            print()

    # Save results
    print(f"Saving analysis to {OUTPUT_FILE}...")
    output_data = {
        'groups_analyzed': all_results,
        'consistent_patterns': consistent_patterns,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print(f"Found {len(consistent_patterns)} consistent patterns across multiple groups")
    print()
    print("Next steps:")
    print("1. Examine the consistent patterns to identify the monster type ID storage format")
    print("2. Look for the specific offset that reliably contains the monster type ID")
    print("3. Test patching these locations to confirm they control visual/AI/spells/loot")


if __name__ == '__main__':
    main()
