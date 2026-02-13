#!/usr/bin/env python3
"""
Analyze all formation files to identify zones with many small formations
that should be consolidated (like Cavern Death Floor 1 Area 1).
"""
import json
import os
from pathlib import Path
from collections import defaultdict

def analyze_formation_file(filepath):
    """Analyze a single formation JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    level_name = data.get('level_name', 'Unknown')
    area_name = data.get('name', 'Unknown')

    # Analyze formations
    formations = data.get('formations', [])
    formation_sizes = [f.get('total', 0) for f in formations]

    # Analyze zone_spawns
    zone_spawns = data.get('zone_spawns', [])
    zone_spawn_sizes = [zs.get('total', 0) for zs in zone_spawns]

    # Analyze spawn_points
    spawn_points = data.get('spawn_points', [])
    spawn_point_sizes = [sp.get('total', 0) for sp in spawn_points]

    # Calculate stats
    small_formations = len([s for s in formation_sizes if 1 <= s <= 3])
    small_zone_spawns = len([s for s in zone_spawn_sizes if 1 <= s <= 3])
    small_spawn_points = len([s for s in spawn_point_sizes if 1 <= s <= 3])

    total_formations = len(formations)
    total_zone_spawns = len(zone_spawns)
    total_spawn_points = len(spawn_points)

    avg_formation_size = sum(formation_sizes) / len(formation_sizes) if formation_sizes else 0
    avg_zone_spawn_size = sum(zone_spawn_sizes) / len(zone_spawn_sizes) if zone_spawn_sizes else 0
    avg_spawn_point_size = sum(spawn_point_sizes) / len(spawn_point_sizes) if spawn_point_sizes else 0

    return {
        'filepath': filepath,
        'level': level_name,
        'area': area_name,
        'formations': {
            'total': total_formations,
            'small_count': small_formations,
            'sizes': formation_sizes,
            'avg_size': avg_formation_size,
        },
        'zone_spawns': {
            'total': total_zone_spawns,
            'small_count': small_zone_spawns,
            'sizes': zone_spawn_sizes,
            'avg_size': avg_zone_spawn_size,
        },
        'spawn_points': {
            'total': total_spawn_points,
            'small_count': small_spawn_points,
            'sizes': spawn_point_sizes,
            'avg_size': avg_spawn_point_size,
        }
    }

def find_candidates_for_consolidation(stats_list):
    """Find zones that need consolidation (6+ formations with avg size <= 3)."""
    candidates = []

    for stats in stats_list:
        # Criteria: 6+ formations with average size <= 3
        # OR: 6+ zone_spawns with average size <= 3
        formations = stats['formations']
        zone_spawns = stats['zone_spawns']

        needs_consolidation = False
        reason = []

        if formations['total'] >= 6 and formations['avg_size'] <= 3.5:
            needs_consolidation = True
            reason.append(f"{formations['total']} formations (avg {formations['avg_size']:.1f})")

        if zone_spawns['total'] >= 6 and zone_spawns['avg_size'] <= 3.5:
            needs_consolidation = True
            reason.append(f"{zone_spawns['total']} zone_spawns (avg {zone_spawns['avg_size']:.1f})")

        if needs_consolidation:
            candidates.append({
                'stats': stats,
                'reason': ', '.join(reason)
            })

    return candidates

def main():
    base_dir = Path('Data/formations')

    # Find all JSON files (excluding vanilla backups)
    all_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_vanilla.json'):
                all_files.append(Path(root) / file)

    print(f"Found {len(all_files)} formation files\n")

    # Analyze all files
    all_stats = []
    for filepath in sorted(all_files):
        try:
            stats = analyze_formation_file(filepath)
            all_stats.append(stats)
        except Exception as e:
            print(f"ERROR analyzing {filepath}: {e}")

    # Find consolidation candidates
    candidates = find_candidates_for_consolidation(all_stats)

    print("=" * 80)
    print(f"CONSOLIDATION CANDIDATES ({len(candidates)} found)")
    print("=" * 80)
    print()

    for i, candidate in enumerate(candidates, 1):
        stats = candidate['stats']
        print(f"{i}. {stats['level']} - {stats['area']}")
        print(f"   File: {Path(stats['filepath']).relative_to(base_dir)}")
        print(f"   Reason: {candidate['reason']}")
        print(f"   Formations: {stats['formations']['sizes']}")
        if stats['zone_spawns']['total'] > 0:
            print(f"   Zone Spawns: {stats['zone_spawns']['sizes']}")
        print()

    # Also print reference: Cavern Death Floor 1 Area 1
    print("=" * 80)
    print("REFERENCE (already consolidated - Cavern Death Floor 1 Area 1)")
    print("=" * 80)
    reference = next((s for s in all_stats if 'floor_1_area_1.json' in s['filepath']
                      and 'cavern_of_death' in s['filepath']), None)
    if reference:
        print(f"Formations ({reference['formations']['total']}): {reference['formations']['sizes']}")
        print(f"Zone Spawns ({reference['zone_spawns']['total']}): {reference['zone_spawns']['sizes']}")
        print(f"Avg formation size: {reference['formations']['avg_size']:.1f}")
        print(f"Avg zone spawn size: {reference['zone_spawns']['avg_size']:.1f}")

    print()
    print("=" * 80)
    print(f"SUMMARY: {len(candidates)} zones need consolidation")
    print("=" * 80)

if __name__ == '__main__':
    main()
