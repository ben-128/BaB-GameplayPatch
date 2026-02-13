#!/usr/bin/env python3
"""
Consolidate small formations into larger ones.
Strategy: merge nearby formations of the same type into bigger groups.

This makes encounters more interesting and challenging.
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import shutil
import math

def calculate_distance(record1, record2):
    """Calculate 3D distance between two spawn records."""
    x1, y1, z1 = record1['x'], record1['y'], record1['z']
    x2, y2, z2 = record2['x'], record2['y'], record2['z']
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

def consolidate_zone_spawns(zone_spawns: List[Dict], max_distance=2000, min_group_size=4):
    """
    Consolidate small zone spawns into larger groups.

    Strategy:
    1. Group spawns by monster slot
    2. For each slot, merge nearby small spawns into larger groups
    3. Keep large spawns as-is (already consolidated)
    """
    if not zone_spawns:
        return zone_spawns

    # Separate large spawns (already good) from small ones (need consolidation)
    large_spawns = [zs for zs in zone_spawns if zs.get('total', 0) >= min_group_size]
    small_spawns = [zs for zs in zone_spawns if zs.get('total', 0) < min_group_size]

    print(f"   - {len(large_spawns)} already large spawns (kept as-is)")
    print(f"   - {len(small_spawns)} small spawns to consolidate")

    if not small_spawns:
        return zone_spawns

    # Group small spawns by monster composition (slots used)
    groups_by_composition = defaultdict(list)
    for spawn in small_spawns:
        # Use the slot types as a key
        slots = tuple(sorted(set(rec['slot'] for rec in spawn['records'])))
        groups_by_composition[slots].append(spawn)

    # Consolidate each composition group
    consolidated = []
    for slots, spawns in groups_by_composition.items():
        print(f"   - Consolidating {len(spawns)} spawns with slots {slots}")

        # Collect all records from these spawns
        all_records = []
        for spawn in spawns:
            all_records.extend(spawn['records'])

        # Group records by slot
        records_by_slot = defaultdict(list)
        for rec in all_records:
            records_by_slot[rec['slot']].append(rec)

        # Merge records spatially: group nearby records together
        for slot, records in records_by_slot.items():
            while records:
                # Start a new group with the first record
                group = [records.pop(0)]

                # Find nearby records and add them to the group
                i = 0
                while i < len(records):
                    rec = records[i]
                    # Check distance to any record in current group
                    is_nearby = any(calculate_distance(rec, g) < max_distance for g in group)

                    if is_nearby:
                        group.append(records.pop(i))
                    else:
                        i += 1

                # If group is too small, merge with next group
                if len(group) >= 2:  # Minimum 2 to make a spawn worth it
                    # Create a new consolidated spawn
                    new_spawn = {
                        'total': len(group),
                        'composition': [{'count': len(group), 'slot': slot, 'monster': group[0].get('monster', f'Slot{slot}')}],
                        'records': group,
                        'suffix': spawns[0]['suffix'],
                        'offset': group[0]['offset']  # Use first record's offset
                    }
                    consolidated.append(new_spawn)

    print(f"   - Created {len(consolidated)} consolidated spawns")

    # Combine with large spawns
    result = large_spawns + consolidated

    # Sort by offset to maintain order
    result.sort(key=lambda x: x.get('offset', '0x0'))

    return result

def consolidate_formations(formations: List[Dict], min_size=4):
    """
    Consolidate small formations into larger ones.

    Strategy:
    1. Merge formations with similar composition
    2. Target: formations of min_size or larger
    """
    if not formations or len(formations) < 2:
        return formations

    # Group formations by monster types used
    groups_by_monsters = defaultdict(list)
    for formation in formations:
        # Use the monster slots as a key
        slots = tuple(sorted(set(s for s in formation.get('slots', []))))
        groups_by_monsters[slots].append(formation)

    consolidated = []
    for slots, group in groups_by_monsters.items():
        if len(group) == 1:
            # Single formation, keep as-is
            consolidated.append(group[0])
            continue

        # Merge small formations
        small = [f for f in group if f.get('total', 0) < min_size]
        large = [f for f in group if f.get('total', 0) >= min_size]

        # Keep large ones as-is
        consolidated.extend(large)

        # Merge small ones
        if small:
            # Combine slots from all small formations
            all_slots = []
            for f in small:
                all_slots.extend(f.get('slots', []))

            # Create a single large formation
            slot_counts = defaultdict(int)
            for slot in all_slots:
                slot_counts[slot] += 1

            composition = []
            for slot, count in sorted(slot_counts.items()):
                monster = next(
                    (comp['monster'] for f in small for comp in f.get('composition', [])
                     if comp['slot'] == slot),
                    f'Slot{slot}'
                )
                composition.append({'count': count, 'slot': slot, 'monster': monster})

            merged = {
                'total': len(all_slots),
                'composition': composition,
                'slots': all_slots,
                'suffix': small[0].get('suffix', '00000000'),
                'offset': small[0].get('offset', '0x0'),
                'slot_types': small[0].get('slot_types', [])
            }
            consolidated.append(merged)

    print(f"   - Consolidated {len(formations)} formations into {len(consolidated)}")

    return consolidated

def consolidate_file(filepath, backup=True, dry_run=False):
    """Consolidate formations in a single file."""
    print(f"\nProcessing: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    level_name = data.get('level_name', 'Unknown')
    area_name = data.get('name', 'Unknown')
    print(f"  {level_name} - {area_name}")

    # Backup original
    if backup and not dry_run:
        backup_path = str(filepath).replace('.json', '_preconsolidation.json')
        shutil.copy2(filepath, backup_path)
        print(f"  Backup created: {backup_path}")

    # Consolidate formations
    original_formations = len(data.get('formations', []))
    if original_formations > 0:
        print(f"  Consolidating {original_formations} formations...")
        data['formations'] = consolidate_formations(data['formations'])
        new_formations = len(data['formations'])
        print(f"  -> {new_formations} formations (saved {original_formations - new_formations})")

    # Consolidate zone_spawns
    original_zone_spawns = len(data.get('zone_spawns', []))
    if original_zone_spawns > 0:
        print(f"  Consolidating {original_zone_spawns} zone_spawns...")
        data['zone_spawns'] = consolidate_zone_spawns(data['zone_spawns'])
        data['zone_spawn_count'] = len(data['zone_spawns'])
        new_zone_spawns = len(data['zone_spawns'])
        print(f"  -> {new_zone_spawns} zone_spawns (saved {original_zone_spawns - new_zone_spawns})")

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
        'formations_after': len(data['formations']),
        'zone_spawns_before': original_zone_spawns,
        'zone_spawns_after': len(data['zone_spawns'])
    }

def main():
    # Candidates from analyze_formations.py
    candidates = [
        'castle_of_vamp/floor_1_area_1.json',
        'cavern_of_death/floor_1_area_2.json',
        'cavern_of_death/floor_5_area_1.json',
        'forest/floor_1_area_1.json',
        'forest/floor_1_area_3.json',
        'forest/floor_1_area_5.json',
        'forest/floor_2_area_1.json',
        'forest/floor_2_area_2.json',
        'forest/floor_2_area_4.json',
        'hall_of_demons/area_1.json',
        'hall_of_demons/area_11.json',
        'hall_of_demons/area_2.json',
        'sealed_cave/area_1.json',
        'sealed_cave/area_2.json',
        'sealed_cave/area_9.json',
    ]

    base_dir = Path('Data/formations')

    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 80)

    print(f"\nConsolidating {len(candidates)} formation files...")

    results = []
    for candidate_path in candidates:
        filepath = base_dir / candidate_path
        if filepath.exists():
            result = consolidate_file(filepath, backup=True, dry_run=dry_run)
            results.append(result)
        else:
            print(f"\nWARNING: File not found: {filepath}")

    # Summary
    print("\n" + "=" * 80)
    print("CONSOLIDATION SUMMARY")
    print("=" * 80)
    for result in results:
        path = Path(result['filepath']).relative_to(base_dir)
        f_saved = result['formations_before'] - result['formations_after']
        z_saved = result['zone_spawns_before'] - result['zone_spawns_after']
        print(f"{path}:")
        print(f"  Formations: {result['formations_before']} -> {result['formations_after']} (saved {f_saved})")
        print(f"  Zone Spawns: {result['zone_spawns_before']} -> {result['zone_spawns_after']} (saved {z_saved})")

    total_f_saved = sum(r['formations_before'] - r['formations_after'] for r in results)
    total_z_saved = sum(r['zone_spawns_before'] - r['zone_spawns_after'] for r in results)
    print()
    print(f"Total formations consolidated: {total_f_saved}")
    print(f"Total zone_spawns consolidated: {total_z_saved}")

    if dry_run:
        print("\nThis was a DRY RUN. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()
