#!/usr/bin/env python3
"""
Consolidate ONLY formations (templates), NOT zone_spawns (placed spawns).

This script merges small formation templates into larger ones for more
interesting random encounters, but leaves all placed spawns untouched.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import shutil

def consolidate_formations(formations: List[Dict], min_size=4, max_size=10):
    """
    Consolidate small formations into larger ones.

    Strategy:
    - Group formations by monster types used
    - Merge small formations (<min_size) of same type
    - Keep formations already >=min_size
    - Limit merged formations to max_size
    """
    if not formations or len(formations) < 2:
        return formations

    # Group formations by monster slot composition
    groups_by_slots = defaultdict(list)
    for formation in formations:
        slots = tuple(sorted(set(s for s in formation.get('slots', []))))
        groups_by_slots[slots].append(formation)

    consolidated = []

    for slots, group in groups_by_slots.items():
        # Single formation, keep as-is
        if len(group) == 1:
            consolidated.append(group[0])
            continue

        # Separate small and large formations
        small = [f for f in group if f.get('total', 0) < min_size]
        large = [f for f in group if f.get('total', 0) >= min_size]

        # Keep large formations as-is
        consolidated.extend(large)

        # Merge small formations
        if small:
            # Combine all slots from small formations
            all_slots = []
            for f in small:
                all_slots.extend(f.get('slots', []))

            # Don't create mega-formations
            if len(all_slots) <= max_size:
                # Count monsters per slot
                slot_counts = defaultdict(int)
                for slot in all_slots:
                    slot_counts[slot] += 1

                # Build composition
                composition = []
                for slot, count in sorted(slot_counts.items()):
                    # Find monster name from original formations
                    monster = next(
                        (comp['monster'] for f in small for comp in f.get('composition', [])
                         if comp['slot'] == slot),
                        f'Slot{slot}'
                    )
                    composition.append({'count': count, 'slot': slot, 'monster': monster})

                # Create merged formation
                merged = {
                    'total': len(all_slots),
                    'composition': composition,
                    'slots': all_slots,
                    'suffix': small[0].get('suffix', '00000000'),
                    'offset': small[0].get('offset', '0x0'),
                    'slot_types': small[0].get('slot_types', [])
                }
                consolidated.append(merged)
            else:
                # Too large, split into chunks
                chunk_size = max_size
                for i in range(0, len(all_slots), chunk_size):
                    chunk_slots = all_slots[i:i+chunk_size]

                    slot_counts = defaultdict(int)
                    for slot in chunk_slots:
                        slot_counts[slot] += 1

                    composition = []
                    for slot, count in sorted(slot_counts.items()):
                        monster = next(
                            (comp['monster'] for f in small for comp in f.get('composition', [])
                             if comp['slot'] == slot),
                            f'Slot{slot}'
                        )
                        composition.append({'count': count, 'slot': slot, 'monster': monster})

                    chunk = {
                        'total': len(chunk_slots),
                        'composition': composition,
                        'slots': chunk_slots,
                        'suffix': small[0].get('suffix', '00000000'),
                        'offset': small[0].get('offset', '0x0'),
                        'slot_types': small[0].get('slot_types', [])
                    }
                    consolidated.append(chunk)

    return consolidated

def consolidate_file(filepath, dry_run=False):
    """Consolidate ONLY formations in a single file."""
    print(f"\nProcessing: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    level_name = data.get('level_name', 'Unknown')
    area_name = data.get('name', 'Unknown')
    print(f"  {level_name} - {area_name}")

    original_formations = len(data.get('formations', []))
    original_zone_spawns = len(data.get('zone_spawns', []))

    if original_formations == 0:
        print(f"  No formations to consolidate (has {original_zone_spawns} zone_spawns)")
        return None

    # Consolidate ONLY formations
    print(f"  Consolidating {original_formations} formations...")
    data['formations'] = consolidate_formations(data['formations'])
    new_formations = len(data['formations'])
    print(f"  -> {new_formations} formations (saved {original_formations - new_formations})")

    # IMPORTANT: Do NOT touch zone_spawns
    print(f"  Zone spawns: {original_zone_spawns} (UNCHANGED)")

    # Save
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"  [OK] Saved")
    else:
        print(f"  (DRY RUN - not saved)")

    return {
        'filepath': filepath,
        'formations_before': original_formations,
        'formations_after': new_formations,
        'zone_spawns': original_zone_spawns
    }

def main():
    base_dir = Path('Data/formations')

    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 80)

    # Find all formation files with formations (not just zone_spawns)
    print("\nScanning for files with formations...")

    all_files = []
    for zone_dir in base_dir.iterdir():
        if zone_dir.is_dir() and zone_dir.name not in ['archive', 'Scripts', 'docs', '__pycache__']:
            for file in zone_dir.glob('*.json'):
                if not file.name.endswith('_vanilla.json') and not file.name.endswith('_preconsolidation.json'):
                    # Check if file has formations
                    try:
                        with open(file) as f:
                            data = json.load(f)
                        if data.get('formations') and len(data['formations']) >= 3:
                            all_files.append(file)
                    except:
                        pass

    print(f"Found {len(all_files)} files with formations (3+)")
    print()

    results = []
    for filepath in sorted(all_files):
        result = consolidate_file(filepath, dry_run=dry_run)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("CONSOLIDATION SUMMARY (FORMATIONS ONLY)")
    print("=" * 80)

    if not results:
        print("No formations were consolidated.")
    else:
        for result in results:
            path = Path(result['filepath']).relative_to(base_dir)
            saved = result['formations_before'] - result['formations_after']
            if saved > 0:
                print(f"{path}:")
                print(f"  Formations: {result['formations_before']} -> {result['formations_after']} (-{saved})")
                print(f"  Zone spawns: {result['zone_spawns']} (unchanged)")

        total_saved = sum(r['formations_before'] - r['formations_after'] for r in results)
        print()
        print(f"Total formations consolidated: {total_saved}")
        print(f"Zone spawns: ALL UNCHANGED (as requested)")

    if dry_run:
        print("\nThis was a DRY RUN. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()
