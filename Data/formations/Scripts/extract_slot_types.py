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

    formations_dir = SCRIPT_DIR.parent

    # Find all area directories
    area_dirs = [d for d in formations_dir.iterdir()
                 if d.is_dir() and not d.name.startswith('.')
                 and d.name not in ['Scripts', 'docs']]

    processed = 0
    skipped = 0
    errors = 0

    for area_dir in sorted(area_dirs):
        # Find all _vanilla.json files in this directory
        vanilla_files = list(area_dir.glob("*_vanilla.json"))

        for vanilla_path in sorted(vanilla_files):
            # Corresponding area JSON (remove _vanilla suffix)
            area_name = vanilla_path.stem.replace('_vanilla', '')
            area_path = area_dir / f"{area_name}.json"

            if not area_path.exists():
                print(f"SKIP: {area_path.name} (no corresponding area JSON)")
                skipped += 1
                continue

            # Extract slot_types
            slot_types = extract_slot_types_from_vanilla(vanilla_path)
            if slot_types is None:
                print(f"SKIP: {area_path.name} (no formations in vanilla)")
                skipped += 1
                continue

            # Update area JSON
            try:
                with open(area_path, 'r', encoding='utf-8') as f:
                    area_data = json.load(f)

                area_data['slot_types'] = slot_types

                with open(area_path, 'w', encoding='utf-8') as f:
                    json.dump(area_data, f, indent=2, ensure_ascii=False)

                print(f"[OK] {area_dir.name}/{area_path.name}: {slot_types}")
                processed += 1

            except Exception as e:
                print(f"ERROR: {area_path.name}: {e}")
                errors += 1

    print()
    print("=" * 70)
    print(f"Processed: {processed} areas")
    print(f"Skipped:   {skipped} areas")
    print(f"Errors:    {errors} areas")
    print("=" * 70)

    return 0 if errors == 0 else 1


if __name__ == '__main__':
    exit(main())
