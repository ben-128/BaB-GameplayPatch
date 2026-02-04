"""
organize_spawns_by_level.py
Organize monster spawns by level/zone

Usage: py -3 organize_spawns_by_level.py
"""

from pathlib import Path
import json

SCRIPT_DIR = Path(__file__).parent

def load_spawn_data():
    """Load spawn analysis results"""
    spawn_file = SCRIPT_DIR / "spawn_analysis.json"

    if not spawn_file.exists():
        print("ERROR: spawn_analysis.json not found!")
        print("Please run: py -3 analyze_enemy_spawns.py")
        return None

    with open(spawn_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def organize_by_level(spawn_data):
    """Organize spawns by level zones"""
    spawns = spawn_data.get('spawn_structures', [])
    zones = spawn_data.get('level_zones', {})

    # Group by zone
    by_zone = {}
    for spawn in spawns:
        zone = spawn.get('zone', 'Unknown')
        if zone not in by_zone:
            by_zone[zone] = []
        by_zone[zone].append(spawn)

    return by_zone

def organize_by_monster(spawn_data):
    """Organize spawns by monster type"""
    spawns = spawn_data.get('spawn_structures', [])

    by_monster = {}
    for spawn in spawns:
        monster_name = spawn.get('monster_name', 'Unknown')
        if monster_name not in by_monster:
            by_monster[monster_name] = []
        by_monster[monster_name].append(spawn)

    return by_monster

def generate_level_report(by_zone):
    """Generate readable report of spawns by level"""
    report = []

    report.append("=" * 70)
    report.append("  MONSTER SPAWNS BY LEVEL")
    report.append("=" * 70)
    report.append("")

    for zone, spawns in sorted(by_zone.items()):
        report.append(f"\n## {zone}")
        report.append("-" * 70)
        report.append(f"Total spawns: {len(spawns)}")
        report.append("")

        # Group by monster in this zone
        monsters_in_zone = {}
        for spawn in spawns:
            monster = spawn['monster_name']
            if monster not in monsters_in_zone:
                monsters_in_zone[monster] = []
            monsters_in_zone[monster].append(spawn)

        # Display each monster
        for monster, monster_spawns in sorted(monsters_in_zone.items()):
            report.append(f"\n### {monster} ({monster_spawns[0]['monster_type']})")

            # Calculate stats
            total_spawns = len(monster_spawns)
            avg_chance = sum(s['spawn_chance'] for s in monster_spawns) / total_spawns if total_spawns > 0 else 0
            avg_count = sum(s['spawn_count'] for s in monster_spawns) / total_spawns if total_spawns > 0 else 0

            report.append(f"  Spawn points: {total_spawns}")
            report.append(f"  Avg spawn chance: {avg_chance:.1f}%")
            report.append(f"  Avg spawn count: {avg_count:.1f}")

            # Show first 3 positions
            report.append("  Positions:")
            for i, spawn in enumerate(monster_spawns[:3]):
                pos = spawn['position']
                report.append(f"    {i+1}. ({pos['x']}, {pos['y']}, {pos['z']}) - {spawn['spawn_chance']}% chance, count {spawn['spawn_count']}")

            if len(monster_spawns) > 3:
                report.append(f"    ... and {len(monster_spawns)-3} more")

    return "\n".join(report)

def create_unity_spawn_list(by_zone):
    """Create Unity-friendly spawn list"""
    unity_data = []

    for zone, spawns in sorted(by_zone.items()):
        zone_data = {
            'zone_name': zone,
            'total_spawns': len(spawns),
            'monsters': []
        }

        # Group by monster
        monsters_in_zone = {}
        for spawn in spawns:
            monster = spawn['monster_name']
            if monster not in monsters_in_zone:
                monsters_in_zone[monster] = {
                    'name': monster,
                    'type': spawn['monster_type'],
                    'spawn_points': []
                }

            monsters_in_zone[monster]['spawn_points'].append({
                'position': spawn['position'],
                'chance': spawn['spawn_chance'],
                'count': spawn['spawn_count'],
                'offset': spawn['offset']
            })

        zone_data['monsters'] = list(monsters_in_zone.values())
        unity_data.append(zone_data)

    return unity_data

def main():
    print("=" * 70)
    print("  ORGANIZING SPAWNS BY LEVEL")
    print("=" * 70)
    print()

    # Load data
    spawn_data = load_spawn_data()
    if not spawn_data:
        return

    total_spawns = len(spawn_data.get('spawn_structures', []))
    print(f"Total spawns loaded: {total_spawns}")

    if total_spawns == 0:
        print("\nNo spawns found!")
        print("This might be normal if structures weren't detected.")
        return

    # Organize by zone
    print("\n[1] Organizing by zone...")
    by_zone = organize_by_level(spawn_data)
    print(f"Found {len(by_zone)} zones")

    # Organize by monster
    print("\n[2] Organizing by monster...")
    by_monster = organize_by_monster(spawn_data)
    print(f"Found {len(by_monster)} unique monsters")

    # Generate report
    print("\n[3] Generating report...")
    report = generate_level_report(by_zone)

    # Save report
    report_file = SCRIPT_DIR / "SPAWNS_BY_LEVEL.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report saved to: {report_file.name}")

    # Create Unity data
    print("\n[4] Creating Unity spawn data...")
    unity_data = create_unity_spawn_list(by_zone)

    unity_file = SCRIPT_DIR / "spawns_by_level.json"
    with open(unity_file, 'w', encoding='utf-8') as f:
        json.dump(unity_data, f, indent=2)

    print(f"Unity data saved to: {unity_file.name}")

    # Statistics
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total spawns: {total_spawns}")
    print(f"Zones: {len(by_zone)}")
    print(f"Unique monsters: {len(by_monster)}")
    print(f"\nZones breakdown:")
    for zone, spawns in sorted(by_zone.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {zone}: {len(spawns)} spawns")

    print(f"\nFiles created:")
    print(f"  - SPAWNS_BY_LEVEL.md (human-readable)")
    print(f"  - spawns_by_level.json (Unity data)")
    print("="*70)

if __name__ == '__main__':
    main()
