#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Extract vanilla formation BYTES (not interpreted) for all areas.

For each area JSON, creates a corresponding _vanilla.json containing:
  - Raw 32-byte hex strings for each formation record
  - 4-byte suffix hex strings

This allows the patcher to use exact vanilla bytes instead of synthetic generation.
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
VANILLA_BLAZE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

def extract_vanilla_formation_bytes(blaze_data, formation_start, num_records):
    """Extract raw bytes for a formation.

    Returns (records, suffix) where:
      - records: list of 32-byte hex strings
      - suffix: 4-byte hex string
    """
    offset = formation_start
    records = []

    for _ in range(num_records):
        rec = blaze_data[offset:offset+32]
        records.append(rec.hex())
        offset += 32

    suffix = blaze_data[offset:offset+4].hex()

    return records, suffix


def read_offset_table(blaze_data, script_start, formation_count):
    """Read formation offsets from the offset table in script area.

    Returns list of (relative_offset, absolute_offset) tuples.
    """
    # Read offset table entries
    # Table structure: [entry0, 0, SP_offsets..., FM_offsets..., 0, 0]
    # We need to find where FM offsets start

    # Read up to 32 entries
    entries = []
    for i in range(32):
        offset = script_start + i * 4
        val = struct.unpack_from('<I', blaze_data, offset)[0]
        if val >= 0x10000:  # Sanity check
            break
        entries.append(val)
        if val == 0 and i > 0 and entries[i-1] == 0:
            break

    # Find formation offsets (usually after spawn point offsets)
    # Heuristic: formation offsets are typically larger and form a sequence
    # For Cavern F1 A1: entries are [60, 0, 80, 244, 408, 508, 608, 676, 808, 940, 1040, 1172, 0, 0]
    # FM offsets start around index 4-5

    # Strategy: find the first sequence of 'formation_count' increasing values
    fm_offsets = []
    for start_idx in range(2, len(entries) - formation_count):
        sequence = entries[start_idx:start_idx + formation_count]
        if 0 in sequence:
            continue
        # Check if mostly increasing (allowing some duplicates)
        if all(sequence[i] <= sequence[i+1] + 100 for i in range(len(sequence)-1)):
            fm_offsets = sequence
            break

    return fm_offsets


def parse_vanilla_formations(blaze_data, group_offset, num_monsters,
                            formation_start, formation_bytes, formation_count):
    """Parse formations using offset table.

    Returns list of (num_records, offset) tuples.
    """
    script_start = group_offset + num_monsters * 96

    # Read formation offsets from offset table
    fm_offsets = read_offset_table(blaze_data, script_start, formation_count)

    if not fm_offsets or len(fm_offsets) != formation_count:
        # Fallback: divide formation area equally
        bytes_per_formation = formation_bytes // formation_count
        fm_offsets = [i * bytes_per_formation for i in range(formation_count)]

    # Calculate absolute offsets and sizes
    # Offsets in table are relative to START of script area, but we need to
    # find where in the formation area each formation is
    formations = []

    # First, find the base offset (where formations actually start)
    # This is typically formation_start
    base_offset = formation_start

    for i, rel_offset in enumerate(fm_offsets):
        # Absolute offset from script_start
        abs_offset_from_script = script_start + rel_offset

        # Check if this is within formation area
        if abs_offset_from_script < formation_start:
            continue
        if abs_offset_from_script >= formation_start + formation_bytes:
            continue

        abs_offset = abs_offset_from_script

        # Calculate size: distance to next formation (or end of area)
        if i + 1 < len(fm_offsets):
            next_abs = script_start + fm_offsets[i+1]
            size_bytes = next_abs - abs_offset
        else:
            size_bytes = (formation_start + formation_bytes) - abs_offset

        # Calculate number of records (size - 4 suffix) / 32
        if size_bytes >= 36:  # At least 1 record + suffix
            num_records = (size_bytes - 4) // 32
            formations.append((num_records, abs_offset))

    return formations


def process_area_json(area_json_path, blaze_data):
    """Process one area JSON and create corresponding _vanilla.json.

    Extracts ALL formations from vanilla binary using offset table.
    """

    with open(area_json_path, 'r', encoding='utf-8') as f:
        area = json.load(f)

    formation_start_hex = area.get('formation_area_start')
    formation_bytes = area.get('formation_area_bytes')
    formation_count = area.get('formation_count')
    group_offset_hex = area.get('group_offset')
    num_monsters = len(area.get('monsters', []))

    if not formation_start_hex or not formation_bytes or not formation_count:
        return None
    if not group_offset_hex or not num_monsters:
        return None

    formation_start = int(formation_start_hex, 16)
    group_offset = int(group_offset_hex, 16)

    # Parse ALL formations from vanilla binary using offset table
    parsed_formations = parse_vanilla_formations(
        blaze_data, group_offset, num_monsters,
        formation_start, formation_bytes, formation_count)

    if not parsed_formations:
        return None

    # Extract vanilla bytes for each formation
    vanilla_formations = []

    for num_records, offset in parsed_formations:
        records, suffix = extract_vanilla_formation_bytes(
            blaze_data, offset, num_records)

        # Try to extract vanilla slots by reading byte[8] from each record
        # (This is an approximation - may not be accurate)
        vanilla_slots = []
        for rec_hex in records:
            rec_bytes = bytes.fromhex(rec_hex)
            slot = rec_bytes[8]
            vanilla_slots.append(slot)

        vanilla_formations.append({
            'records': records,
            'suffix': suffix,
            'offset': hex(offset),
            'vanilla_slots': vanilla_slots,
        })

    # Create vanilla JSON structure
    vanilla_data = {
        'level_name': area['level_name'],
        'name': area['name'],
        'formation_area_start': area['formation_area_start'],
        'formation_area_bytes': area['formation_area_bytes'],
        'original_total_slots': area['original_total_slots'],
        'formation_count': area['formation_count'],
        'area_id': area['area_id'],
        'formations': vanilla_formations,
    }

    return vanilla_data


def find_all_area_jsons():
    """Find all area JSONs in level subdirectories."""
    results = []
    for level_dir in sorted(SCRIPT_DIR.iterdir()):
        if not level_dir.is_dir():
            continue
        for json_file in sorted(level_dir.glob('*.json')):
            # Skip _vanilla.json files
            if json_file.stem.endswith('_vanilla'):
                continue
            results.append(json_file)
    return results


def main():
    print("=" * 70)
    print("  Extract Vanilla Formation Bytes")
    print("=" * 70)
    print()

    if not VANILLA_BLAZE.exists():
        print(f"ERROR: Vanilla BLAZE.ALL not found at:")
        print(f"  {VANILLA_BLAZE}")
        return 1

    print(f"Reading vanilla BLAZE.ALL...")
    print(f"  {VANILLA_BLAZE}")
    with open(VANILLA_BLAZE, 'rb') as f:
        blaze_data = f.read()
    print(f"  Size: {len(blaze_data):,} bytes")
    print()

    area_jsons = find_all_area_jsons()
    print(f"Found {len(area_jsons)} area JSON files")
    print()

    extracted_count = 0
    skipped_count = 0

    for area_json_path in area_jsons:
        relative_path = area_json_path.relative_to(SCRIPT_DIR)

        try:
            vanilla_data = process_area_json(area_json_path, blaze_data)

            if vanilla_data is None:
                skipped_count += 1
                continue

            # Write _vanilla.json
            vanilla_json_path = area_json_path.with_stem(
                area_json_path.stem + '_vanilla')

            with open(vanilla_json_path, 'w', encoding='utf-8') as f:
                json.dump(vanilla_data, f, indent=2, ensure_ascii=False)

            num_formations = len(vanilla_data['formations'])
            total_records = sum(len(f['records']) for f in vanilla_data['formations'])

            print(f"  {relative_path}")
            print(f"    -> {vanilla_json_path.name}")
            print(f"       {num_formations} formations, {total_records} records")

            extracted_count += 1

        except Exception as e:
            print(f"  ERROR processing {relative_path}: {e}")
            skipped_count += 1

    print()
    print("=" * 70)
    print(f"  Extracted: {extracted_count} areas")
    print(f"  Skipped: {skipped_count} areas")
    print("=" * 70)
    print()
    print("Next step: Modify patch_formations.py to use these vanilla bytes")

    return 0


if __name__ == '__main__':
    exit(main())
