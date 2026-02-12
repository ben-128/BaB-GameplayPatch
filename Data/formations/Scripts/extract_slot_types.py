#!/usr/bin/env python3
"""
Extract slot_types from vanilla formations.

slot_types are the 4-byte type values used in byte[0:4] prefix and suffix.
We extract them by looking at the suffixes of vanilla formations.
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def extract_slot_types_from_vanilla(vanilla_json_path):
    """Extract slot_types by analyzing vanilla formation suffixes."""

    with open(vanilla_json_path, 'r', encoding='utf-8') as f:
        vanilla_data = json.load(f)

    formations = vanilla_data.get('formations', [])
    if not formations:
        return None

    # Map slot index to type value
    slot_types_map = {}

    for formation in formations:
        slots = formation.get('slots', [])
        suffix = formation.get('suffix', '00000000')

        if not slots:
            continue

        # The suffix is the type value of the LAST slot
        last_slot = slots[-1]
        slot_types_map[last_slot] = suffix

    # Convert to ordered list
    if not slot_types_map:
        return None

    max_slot = max(slot_types_map.keys())
    slot_types = []
    for i in range(max_slot + 1):
        slot_types.append(slot_types_map.get(i, '00000000'))

    return slot_types


def main():
    print("=" * 70)
    print("  Extract slot_types from vanilla formations")
    print("=" * 70)
    print()

    # Process Cavern F1 A1 as example
    area_dir = SCRIPT_DIR.parent / "cavern_of_death"
    vanilla_path = area_dir / "floor_1_area_1_vanilla.json"
    area_path = area_dir / "floor_1_area_1.json"

    if not vanilla_path.exists():
        print(f"ERROR: {vanilla_path} not found")
        return 1

    slot_types = extract_slot_types_from_vanilla(vanilla_path)
    if slot_types is None:
        print("ERROR: Could not extract slot_types")
        return 1

    print(f"Extracted slot_types for Cavern F1 A1:")
    for i, st in enumerate(slot_types):
        print(f"  slot {i}: {st}")
    print()

    # Update area JSON
    with open(area_path, 'r', encoding='utf-8') as f:
        area_data = json.load(f)

    area_data['slot_types'] = slot_types

    with open(area_path, 'w', encoding='utf-8') as f:
        json.dump(area_data, f, indent=2, ensure_ascii=False)

    print(f"Updated {area_path.name} with correct slot_types")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
