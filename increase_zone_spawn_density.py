#!/usr/bin/env python3
"""
Increase enemy density in zone_spawns by duplicating spawn records
with slightly offset positions.

Strategy:
- For each zone_spawn, duplicate records around original positions
- Add positional offset (±50-150 units) to avoid exact overlaps
- Configurable multiplier (1.5x, 2x, 3x)
"""
import json
import sys
import random
from pathlib import Path
from typing import List, Dict
import shutil

def generate_offset_position(x, y, z, offset_range=100):
    """Generate a new position near the original with random offset."""
    return (
        x + random.randint(-offset_range, offset_range),
        y + random.randint(-20, 20),  # Less Y variation (height)
        z + random.randint(-offset_range, offset_range)
    )

def multiply_zone_spawn(spawn: Dict, multiplier: float, offset_range=100) -> Dict:
    """
    Multiply a zone_spawn by duplicating its records with offset positions.

    Args:
        spawn: Original zone_spawn dict
        multiplier: How many times to multiply (1.5 = +50%, 2.0 = double, etc.)
        offset_range: Max distance offset for new spawns

    Returns:
        Modified spawn with duplicated records
    """
    original_records = spawn.get('records', [])
    original_total = spawn.get('total', len(original_records))

    # Calculate how many extra records to add
    target_total = int(original_total * multiplier)
    extra_needed = target_total - original_total

    if extra_needed <= 0:
        return spawn  # No multiplication needed

    # Duplicate records with offset positions
    new_records = list(original_records)  # Start with originals

    for i in range(extra_needed):
        # Pick a random original record to duplicate
        source_record = random.choice(original_records)

        # Create new record with offset position
        new_record = source_record.copy()
        new_x, new_y, new_z = generate_offset_position(
            source_record['x'],
            source_record['y'],
            source_record['z'],
            offset_range
        )

        new_record['x'] = new_x
        new_record['y'] = new_y
        new_record['z'] = new_z
        # Keep same slot, area_id, byte0, byte10_11
        # Note: offset will be wrong but gets recalculated when patched

        new_records.append(new_record)

    # Update spawn
    new_spawn = spawn.copy()
    new_spawn['records'] = new_records
    new_spawn['total'] = len(new_records)

    # Update composition counts
    if 'composition' in new_spawn:
        slot_counts = {}
        for rec in new_records:
            slot = rec['slot']
            slot_counts[slot] = slot_counts.get(slot, 0) + 1

        new_composition = []
        for comp in new_spawn['composition']:
            slot = comp['slot']
            new_comp = comp.copy()
            new_comp['count'] = slot_counts.get(slot, comp['count'])
            new_composition.append(new_comp)

        new_spawn['composition'] = new_composition

    return new_spawn

def increase_zone_spawn_density(filepath, multiplier=1.5, offset_range=100,
                                 exclude_large=True, large_threshold=8,
                                 dry_run=False):
    """
    Increase zone_spawn density for a single file.

    Args:
        filepath: Path to formation JSON
        multiplier: Density multiplier (1.5 = +50%, 2.0 = double)
        offset_range: Max position offset for duplicated spawns
        exclude_large: Don't multiply already-large spawns
        large_threshold: Size considered "large" if exclude_large=True
        dry_run: Don't save changes
    """
    RECORD_SIZE = 32  # Each spawn record = 32 bytes

    print(f"\nProcessing: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    level_name = data.get('level_name', 'Unknown')
    area_name = data.get('name', 'Unknown')
    print(f"  {level_name} - {area_name}")

    zone_spawns = data.get('zone_spawns', [])
    if not zone_spawns:
        print(f"  No zone_spawns to modify")
        return None

    # Backup
    if not dry_run:
        backup_path = str(filepath).replace('.json', '_predensity.json')
        shutil.copy2(filepath, backup_path)
        print(f"  Backup: {Path(backup_path).name}")

    # Process each zone_spawn
    original_total = sum(zs.get('total', 0) for zs in zone_spawns)
    modified_count = 0

    new_zone_spawns = []
    for zs in zone_spawns:
        original_size = zs.get('total', 0)

        # Skip large spawns if requested
        if exclude_large and original_size >= large_threshold:
            new_zone_spawns.append(zs)
            continue

        # Multiply spawn
        new_zs = multiply_zone_spawn(zs, multiplier, offset_range)
        new_zone_spawns.append(new_zs)

        if new_zs['total'] > original_size:
            modified_count += 1

    new_total = sum(zs.get('total', 0) for zs in new_zone_spawns)

    # SAFETY CHECK: Verify we don't exceed available space
    zone_spawns_area_bytes = data.get('zone_spawns_area_bytes', 0)
    new_record_count = sum(len(zs.get('records', [])) for zs in new_zone_spawns)
    new_bytes_used = new_record_count * RECORD_SIZE

    if zone_spawns_area_bytes > 0:
        usage_percent = (new_bytes_used / zone_spawns_area_bytes) * 100

        if new_bytes_used > zone_spawns_area_bytes:
            print(f"  [ERROR] SPACE OVERFLOW!")
            print(f"  Need {new_bytes_used} bytes, only {zone_spawns_area_bytes} available")
            print(f"  Aborting changes for this zone.")
            return None

        print(f"  Zone spawns: {len(zone_spawns)} groups")
        print(f"  Modified: {modified_count} groups")
        print(f"  Total enemies: {original_total} -> {new_total} (+{new_total - original_total})")
        print(f"  Space used: {new_bytes_used}/{zone_spawns_area_bytes} bytes ({usage_percent:.1f}%)")

        if usage_percent > 80:
            print(f"  [WARNING] High space usage! Consider lower multiplier.")
    else:
        print(f"  Zone spawns: {len(zone_spawns)} groups")
        print(f"  Modified: {modified_count} groups")
        print(f"  Total enemies: {original_total} -> {new_total} (+{new_total - original_total})")
        print(f"  [WARNING] No zone_spawns_area_bytes info - cannot verify space!")

    # Update data
    data['zone_spawns'] = new_zone_spawns
    data['zone_spawn_count'] = len(new_zone_spawns)

    # Save
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"  [OK] Saved")
    else:
        print(f"  (DRY RUN - not saved)")

    return {
        'filepath': filepath,
        'spawns': len(zone_spawns),
        'modified': modified_count,
        'enemies_before': original_total,
        'enemies_after': new_total
    }

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Increase zone_spawn density')
    parser.add_argument('--multiplier', type=float, default=1.5,
                       help='Density multiplier (1.5=+50%%, 2.0=double, default=1.5)')
    parser.add_argument('--offset', type=int, default=100,
                       help='Max position offset (default=100)')
    parser.add_argument('--include-large', action='store_true',
                       help='Also multiply large spawns (>=8 enemies)')
    parser.add_argument('--zones', nargs='+',
                       help='Specific zones to modify (e.g., cavern_of_death/floor_1_area_1.json)')
    parser.add_argument('--all', action='store_true',
                       help='Apply to all zones')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without saving')

    args = parser.parse_args()

    base_dir = Path('Data/formations')

    if args.dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 80)

    print(f"\nSettings:")
    print(f"  Multiplier: {args.multiplier}x")
    print(f"  Position offset: ±{args.offset} units")
    print(f"  Exclude large (>=8): {not args.include_large}")

    # Find files to process
    files_to_process = []

    if args.zones:
        for zone in args.zones:
            filepath = base_dir / zone
            if filepath.exists():
                files_to_process.append(filepath)
            else:
                print(f"WARNING: File not found: {zone}")
    elif args.all:
        for zone_dir in base_dir.iterdir():
            if zone_dir.is_dir() and zone_dir.name not in ['archive', 'Scripts', 'docs', '__pycache__']:
                for file in zone_dir.glob('*.json'):
                    if not file.name.endswith('_vanilla.json') and not file.name.endswith('_preconsolidation.json') and not file.name.endswith('_predensity.json'):
                        files_to_process.append(file)
    else:
        print("\nERROR: Must specify --zones or --all")
        print("Examples:")
        print("  py -3 increase_zone_spawn_density.py --zones sealed_cave/area_1.json --multiplier 2.0")
        print("  py -3 increase_zone_spawn_density.py --all --multiplier 1.5 --dry-run")
        return

    print(f"\nProcessing {len(files_to_process)} files...")

    results = []
    for filepath in sorted(files_to_process):
        result = increase_zone_spawn_density(
            filepath,
            multiplier=args.multiplier,
            offset_range=args.offset,
            exclude_large=not args.include_large,
            dry_run=args.dry_run
        )
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("DENSITY INCREASE SUMMARY")
    print("=" * 80)

    if results:
        total_before = sum(r['enemies_before'] for r in results)
        total_after = sum(r['enemies_after'] for r in results)
        total_added = total_after - total_before

        print(f"Files modified: {len(results)}")
        print(f"Total enemies: {total_before} -> {total_after} (+{total_added})")
        print(f"Average increase: {(total_after/total_before - 1)*100:.1f}%")

        # Top 5 biggest increases
        print("\nTop 5 biggest increases:")
        sorted_results = sorted(results, key=lambda r: r['enemies_after'] - r['enemies_before'], reverse=True)
        for r in sorted_results[:5]:
            rel_path = Path(r['filepath']).relative_to(base_dir)
            added = r['enemies_after'] - r['enemies_before']
            print(f"  {rel_path}: +{added} enemies ({r['enemies_before']} -> {r['enemies_after']})")

    if args.dry_run:
        print("\nThis was a DRY RUN. Run without --dry-run to apply changes.")

if __name__ == '__main__':
    main()
