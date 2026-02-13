#!/usr/bin/env python3
"""
Smart density increase using convex hull placement.

Instead of random offsets, new enemies are placed INSIDE the convex hull
formed by existing enemies in the same spawn group. This creates more
natural and cohesive enemy placement.
"""
import json
import sys
import random
from pathlib import Path
from typing import List, Dict, Tuple
import shutil
import math

def convex_hull_2d(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Compute convex hull using Graham scan algorithm.
    Returns vertices in counter-clockwise order.
    """
    if len(points) < 3:
        return points

    # Remove duplicate points
    unique_points = list(set(points))
    if len(unique_points) < 3:
        return unique_points

    # Find the lowest point (tie-break by leftmost)
    start = min(unique_points, key=lambda p: (p[1], p[0]))

    # Sort points by polar angle with respect to start
    def polar_angle(p):
        dx = p[0] - start[0]
        dy = p[1] - start[1]
        return math.atan2(dy, dx)

    sorted_points = sorted([p for p in unique_points if p != start], key=polar_angle)

    if len(sorted_points) == 0:
        return [start]

    # Graham scan
    hull = [start, sorted_points[0]]

    for point in sorted_points[1:]:
        # Remove points that create clockwise turn
        while len(hull) > 1:
            # Cross product to determine turn direction
            o = hull[-2]
            a = hull[-1]
            b = point

            cross = (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

            if cross <= 0:  # Clockwise or collinear
                hull.pop()
            else:
                break

        hull.append(point)

    return hull

def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Check if point is inside polygon using ray casting."""
    x, y = point
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside

def generate_point_in_hull(hull: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Generate a random point inside the convex hull using rejection sampling.
    """
    if len(hull) < 3:
        # Degenerate case: return random point near existing points
        if len(hull) == 1:
            return (hull[0][0] + random.uniform(-50, 50), hull[0][1] + random.uniform(-50, 50))
        else:
            # Between two points
            t = random.random()
            return (
                hull[0][0] + t * (hull[1][0] - hull[0][0]),
                hull[0][1] + t * (hull[1][1] - hull[0][1])
            )

    # Find bounding box
    min_x = min(p[0] for p in hull)
    max_x = max(p[0] for p in hull)
    min_y = min(p[1] for p in hull)
    max_y = max(p[1] for p in hull)

    # Rejection sampling: generate random point in bounding box until it's inside hull
    max_attempts = 100
    for _ in range(max_attempts):
        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)

        if point_in_polygon((x, y), hull):
            return (x, y)

    # Fallback: return centroid
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    return (cx, cy)

def interpolate_y(x: float, z: float, records: List[Dict]) -> float:
    """
    Interpolate Y coordinate based on nearby points using inverse distance weighting.
    """
    if not records:
        return 0

    # Calculate distances to all existing points
    distances = []
    for rec in records:
        dx = rec['x'] - x
        dz = rec['z'] - z
        dist = math.sqrt(dx*dx + dz*dz)
        distances.append((dist, rec['y']))

    # If very close to an existing point, use its Y
    if distances[0][0] < 1:
        return distances[0][1]

    # Inverse distance weighting (use 3 nearest neighbors)
    distances.sort()
    nearest = distances[:min(3, len(distances))]

    weighted_sum = 0
    weight_sum = 0

    for dist, y in nearest:
        weight = 1.0 / (dist + 1)  # +1 to avoid division by zero
        weighted_sum += weight * y
        weight_sum += weight

    return int(weighted_sum / weight_sum) if weight_sum > 0 else records[0]['y']

def multiply_zone_spawn_smart(spawn: Dict, multiplier: float) -> Dict:
    """
    Multiply spawn intelligently by placing new enemies inside convex hull.
    """
    original_records = spawn.get('records', [])
    original_total = len(original_records)

    target_total = int(original_total * multiplier)
    extra_needed = target_total - original_total

    if extra_needed <= 0 or original_total == 0:
        return spawn

    # Extract 2D positions (x, z) for convex hull
    points_2d = [(rec['x'], rec['z']) for rec in original_records]

    # Compute convex hull
    hull = convex_hull_2d(points_2d)

    # Generate new records
    new_records = list(original_records)

    for i in range(extra_needed):
        # Pick a random source record to copy attributes from
        source = random.choice(original_records)

        # Generate position inside convex hull
        x, z = generate_point_in_hull(hull)

        # Interpolate Y coordinate
        y = interpolate_y(x, z, original_records)

        # Create new record
        new_record = source.copy()
        new_record['x'] = int(x)
        new_record['y'] = int(y)
        new_record['z'] = int(z)

        new_records.append(new_record)

    # Update spawn
    new_spawn = spawn.copy()
    new_spawn['records'] = new_records
    new_spawn['total'] = len(new_records)

    # Update composition
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

def increase_zone_spawn_density_smart(filepath, multiplier=2.0, exclude_large=True,
                                      large_threshold=8, dry_run=False):
    """Smart density increase using convex hull placement."""
    RECORD_SIZE = 32

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
        backup_path = str(filepath).replace('.json', '_predensity_smart.json')
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

        # Skip single-enemy spawns (no hull possible)
        if original_size < 2:
            new_zone_spawns.append(zs)
            continue

        # Multiply spawn
        new_zs = multiply_zone_spawn_smart(zs, multiplier)
        new_zone_spawns.append(new_zs)

        if new_zs['total'] > original_size:
            modified_count += 1

    new_total = sum(zs.get('total', 0) for zs in new_zone_spawns)

    print(f"  Zone spawns: {len(zone_spawns)} groups")
    print(f"  Modified: {modified_count} groups")
    print(f"  Total enemies: {original_total} -> {new_total} (+{new_total - original_total})")

    # SAFETY CHECK
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

        print(f"  Space used: {new_bytes_used}/{zone_spawns_area_bytes} bytes ({usage_percent:.1f}%)")

        if usage_percent > 80:
            print(f"  [WARNING] High space usage!")

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

    parser = argparse.ArgumentParser(description='Smart density increase using convex hull')
    parser.add_argument('--multiplier', type=float, default=2.0,
                       help='Density multiplier (default=2.0)')
    parser.add_argument('--include-large', action='store_true',
                       help='Also multiply large spawns (>=8 enemies)')
    parser.add_argument('--zones', nargs='+',
                       help='Specific zones to modify')
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
    print(f"  Placement: INSIDE convex hull (smart)")
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
                    if not file.name.endswith('_vanilla.json') and not file.name.endswith('_preconsolidation.json') and not file.name.endswith('_predensity.json') and not file.name.endswith('_predensity_smart.json'):
                        files_to_process.append(file)
    else:
        print("\nERROR: Must specify --zones or --all")
        print("Examples:")
        print("  py -3 increase_density_smart.py --zones sealed_cave/area_1.json --multiplier 2.0")
        print("  py -3 increase_density_smart.py --all --multiplier 2.0 --dry-run")
        return

    print(f"\nProcessing {len(files_to_process)} files...")

    results = []
    for filepath in sorted(files_to_process):
        result = increase_zone_spawn_density_smart(
            filepath,
            multiplier=args.multiplier,
            exclude_large=not args.include_large,
            dry_run=args.dry_run
        )
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SMART DENSITY INCREASE SUMMARY")
    print("=" * 80)

    if results:
        total_before = sum(r['enemies_before'] for r in results)
        total_after = sum(r['enemies_after'] for r in results)
        total_added = total_after - total_before

        print(f"Files modified: {len(results)}")
        print(f"Total enemies: {total_before} -> {total_after} (+{total_added})")
        print(f"Average increase: {(total_after/total_before - 1)*100:.1f}%")

        # Top 5
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
