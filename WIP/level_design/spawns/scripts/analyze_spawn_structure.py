#!/usr/bin/env python3
"""
analyze_spawn_structure.py
Deep analysis of the structure BEFORE spawn groups to find monster type IDs
that control visuals, AI, spells, and loot.

This script examines the pre-group headers (~176 bytes) to find patterns
that might link spawned monsters to their behavior/visual data.
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

MONSTER_INDEX = PROJECT_ROOT / "Data" / "monster_stats" / "_index.json"
OUTPUT_FILE = SCRIPT_DIR.parent / "data" / "spawn_structure_analysis.json"

# Test case: Cavern of Death Floor 1 Area 1
# Expected: Lv20.Goblin (ID 84), Goblin-Shaman (ID 59), Giant-Bat (ID 49)
TEST_GROUP_OFFSET = 0xF7A97C

# Size to scan before each group
PRE_GROUP_SIZE = 512


def load_monster_index():
    """Load monster ID mapping from individual monster JSON files."""
    mapping = {}

    # Load from boss and normal_enemies folders
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
            except Exception as e:
                print(f"    Warning: Could not load {json_file.name}: {e}")

    return mapping


def read_spawn_group(data, offset):
    """Read a spawn group and return monster names."""
    monsters = []
    pos = offset

    # Read up to 6 monsters (96 bytes each)
    for i in range(6):
        if pos + 96 > len(data):
            break

        # Read name field (16 bytes)
        name_field = data[pos:pos + 16]
        null_idx = name_field.find(b'\x00')
        if null_idx <= 0:
            break

        name = name_field[:null_idx].decode('ascii', errors='ignore')

        # Check if all bytes after null are zero
        if all(name_field[i] == 0 for i in range(null_idx, 16)):
            monsters.append(name)
            pos += 96
        else:
            break

    return monsters


def analyze_pre_group(data, group_offset, monster_names, monster_ids):
    """Analyze the data before a spawn group."""

    if group_offset < PRE_GROUP_SIZE:
        return None

    start = group_offset - PRE_GROUP_SIZE
    end = group_offset
    pre_data = data[start:end]

    analysis = {
        'group_offset': f"0x{group_offset:X}",
        'monsters': monster_names,
        'monster_ids': [monster_ids.get(name, -1) for name in monster_names],
        'findings': {},
    }

    # Look for monster IDs in various formats
    findings = {}

    # 1. Search for monster IDs as uint8
    findings['uint8_matches'] = []
    for name in monster_names:
        monster_id = monster_ids.get(name, -1)
        if monster_id >= 0:
            # Find all occurrences of this ID as uint8
            matches = []
            for i in range(len(pre_data)):
                if pre_data[i] == monster_id:
                    matches.append({
                        'offset': f"-0x{group_offset - start - i:X}",
                        'byte_offset': i,
                        'context_before': pre_data[max(0, i-4):i].hex(' '),
                        'value': pre_data[i],
                        'context_after': pre_data[i+1:min(len(pre_data), i+5)].hex(' '),
                    })
            if matches:
                findings['uint8_matches'].append({
                    'monster': name,
                    'id': monster_id,
                    'matches': matches,
                })

    # 2. Search for monster IDs as uint16 LE
    findings['uint16_matches'] = []
    for name in monster_names:
        monster_id = monster_ids.get(name, -1)
        if monster_id >= 0:
            matches = []
            target = struct.pack('<H', monster_id)
            i = 0
            while i < len(pre_data) - 1:
                if pre_data[i:i+2] == target:
                    matches.append({
                        'offset': f"-0x{group_offset - start - i:X}",
                        'byte_offset': i,
                        'context_before': pre_data[max(0, i-4):i].hex(' '),
                        'value': monster_id,
                        'context_after': pre_data[i+2:min(len(pre_data), i+6)].hex(' '),
                    })
                    i += 2
                else:
                    i += 1
            if matches:
                findings['uint16_matches'].append({
                    'monster': name,
                    'id': monster_id,
                    'matches': matches,
                })

    # 3. Look for formation pairs (8-byte records ending ~48 bytes before group)
    # Format: [slot_index, param_L, 0x00, 0x00] [slot_index, param_R, 0x00, 0x40]
    findings['formation_pairs'] = []
    formation_start = len(pre_data) - 48
    if formation_start > 0:
        for i in range(formation_start, len(pre_data) - 8, 8):
            pair = pre_data[i:i+8]
            if len(pair) == 8:
                slot1, param_l, b2, b3 = pair[0], pair[1], pair[2], pair[3]
                slot2, param_r, b6, b7 = pair[4], pair[5], pair[6], pair[7]

                # Check if it looks like a formation pair
                if slot1 == slot2 and b7 == 0x40:
                    findings['formation_pairs'].append({
                        'offset': f"-0x{group_offset - start - i:X}",
                        'slot_index': slot1,
                        'param_L': param_l,
                        'param_R': param_r,
                        'hex': pair.hex(' '),
                    })

    # 4. Look for sequential index table (~160 bytes before group)
    findings['index_table'] = []
    index_start = len(pre_data) - 160
    index_end = len(pre_data) - 128
    if index_start > 0:
        index_region = pre_data[index_start:index_end]
        findings['index_table'] = {
            'offset': f"-0x{160:X} to -0x{128:X}",
            'hex': index_region.hex(' '),
            'bytes': list(index_region),
        }

    # 5. Look for descriptor entries (~96 to ~80 bytes before group)
    findings['descriptors'] = []
    desc_start = len(pre_data) - 96
    desc_end = len(pre_data) - 80
    if desc_start > 0:
        desc_region = pre_data[desc_start:desc_end]
        findings['descriptors'] = {
            'offset': f"-0x{96:X} to -0x{80:X}",
            'hex': desc_region.hex(' '),
            'as_uint32': [struct.unpack('<I', desc_region[i:i+4])[0]
                         for i in range(0, len(desc_region) - 3, 4)],
        }

    # 6. Scan for repeating patterns
    findings['repeating_bytes'] = {}
    byte_counts = defaultdict(list)
    for i, byte in enumerate(pre_data):
        byte_counts[byte].append(i)

    # Report bytes that appear multiple times in significant positions
    for byte_val, positions in byte_counts.items():
        if len(positions) >= len(monster_names) and byte_val != 0:
            findings['repeating_bytes'][f"0x{byte_val:02X}"] = {
                'count': len(positions),
                'positions': [f"-0x{group_offset - start - p:X}" for p in positions[:10]],
            }

    analysis['findings'] = findings
    return analysis


def main():
    print("=" * 80)
    print("  SPAWN STRUCTURE DEEP ANALYSIS")
    print("=" * 80)
    print()

    # Load BLAZE.ALL
    print(f"Loading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"  Size: {len(data):,} bytes")
    print()

    # Load monster ID mapping
    print(f"Loading monster index...")
    monster_ids = load_monster_index()
    print(f"  Loaded {len(monster_ids)} monster IDs")
    print()

    # Analyze test group
    print(f"Analyzing test group at 0x{TEST_GROUP_OFFSET:X}...")
    monsters = read_spawn_group(data, TEST_GROUP_OFFSET)
    print(f"  Found {len(monsters)} monsters: {', '.join(monsters)}")

    for name in monsters:
        m_id = monster_ids.get(name, -1)
        print(f"    {name}: ID {m_id} (0x{m_id:02X})" if m_id >= 0 else f"    {name}: ID not found")
    print()

    # Run analysis
    print(f"Analyzing {PRE_GROUP_SIZE} bytes before group...")
    analysis = analyze_pre_group(data, TEST_GROUP_OFFSET, monsters, monster_ids)

    if not analysis:
        print("[ERROR] Could not analyze pre-group data")
        return

    # Display findings
    print()
    print("=" * 80)
    print("FINDINGS")
    print("=" * 80)
    print()

    findings = analysis['findings']

    # uint8 matches
    if findings['uint8_matches']:
        print("1. MONSTER IDs AS UINT8:")
        for match_group in findings['uint8_matches']:
            print(f"\n   {match_group['monster']} (ID {match_group['id']}):")
            for m in match_group['matches'][:5]:  # Show first 5
                print(f"     At {m['offset']}: [{m['context_before']}] {m['value']:02X} [{m['context_after']}]")
        print()
    else:
        print("1. MONSTER IDs AS UINT8: None found")
        print()

    # uint16 matches
    if findings['uint16_matches']:
        print("2. MONSTER IDs AS UINT16 LE:")
        for match_group in findings['uint16_matches']:
            print(f"\n   {match_group['monster']} (ID {match_group['id']}):")
            for m in match_group['matches'][:5]:
                print(f"     At {m['offset']}: [{m['context_before']}] {m['value']:04X} [{m['context_after']}]")
        print()
    else:
        print("2. MONSTER IDs AS UINT16 LE: None found")
        print()

    # Formation pairs
    if findings['formation_pairs']:
        print("3. FORMATION PAIRS (last ~48 bytes):")
        for pair in findings['formation_pairs']:
            print(f"   At {pair['offset']}: Slot {pair['slot_index']:02d} | "
                  f"param_L=0x{pair['param_L']:02X} param_R=0x{pair['param_R']:02X} | "
                  f"{pair['hex']}")
        print()
    else:
        print("3. FORMATION PAIRS: None found")
        print()

    # Index table
    if findings['index_table']:
        print("4. INDEX TABLE (-160 to -128):")
        idx_data = findings['index_table']
        print(f"   Hex: {idx_data['hex']}")
        print(f"   Bytes: {idx_data['bytes']}")
        print()

    # Descriptors
    if findings['descriptors']:
        print("5. DESCRIPTOR REGION (-96 to -80):")
        desc_data = findings['descriptors']
        print(f"   Hex: {desc_data['hex']}")
        print(f"   As uint32: {desc_data['as_uint32']}")
        print()

    # Repeating bytes
    if findings['repeating_bytes']:
        print("6. REPEATING BYTES (potential type IDs):")
        for byte_val, info in sorted(findings['repeating_bytes'].items()):
            print(f"   {byte_val}: appears {info['count']} times at {', '.join(info['positions'][:5])}")
        print()

    # Save to JSON
    print(f"Saving analysis to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(analysis, f, indent=2)

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Look for patterns in formation_pairs params that match monster IDs")
    print("2. Check if descriptor region contains pointers to behavior/visual data")
    print("3. Search wider area (1KB+ before group) for monster type references")
    print("4. Compare multiple groups to find consistent patterns")


if __name__ == '__main__':
    main()
