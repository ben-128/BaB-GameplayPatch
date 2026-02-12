#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Extract vanilla formation bytes based on regenerated JSON structure.
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
VANILLA_BLAZE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"


def extract_formation_bytes(blaze_data, formation):
    """Extract raw bytes for a formation from vanilla binary."""
    offset = int(formation['offset'], 16)
    num_records = formation['total']
    suffix_hex = formation['suffix']

    # Read formation records (32 bytes each)
    records = []
    for i in range(num_records):
        rec_offset = offset + i * 32
        rec_bytes = blaze_data[rec_offset:rec_offset + 32]
        records.append(rec_bytes.hex())

    return {
        'records': records,
        'suffix': suffix_hex,
        'slots': formation['slots'],
    }


def process_area_json(area_json_path, blaze_data):
    """Process one area JSON and extract vanilla bytes for all formations."""

    with open(area_json_path, 'r', encoding='utf-8') as f:
        area = json.load(f)

    formations_data = area.get('formations', [])
    if not formations_data:
        return None

    # Extract vanilla bytes for each formation
    vanilla_formations = []
    for formation in formations_data:
        vanilla_formation = extract_formation_bytes(blaze_data, formation)
        vanilla_formations.append(vanilla_formation)

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
            # Skip _vanilla.json and _user_backup.json files
            if '_vanilla' in json_file.stem or '_user_backup' in json_file.stem:
                continue
            results.append(json_file)
    return results


def main():
    print("=" * 70)
    print("  Extract Vanilla Formation Bytes (v2)")
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
                print(f"  SKIP: {relative_path} (no formations)")
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
            import traceback
            traceback.print_exc()
            skipped_count += 1

    print()
    print("=" * 70)
    print(f"  Extracted: {extracted_count} areas")
    print(f"  Skipped: {skipped_count} areas")
    print("=" * 70)
    print()

    return 0


if __name__ == '__main__':
    exit(main())
