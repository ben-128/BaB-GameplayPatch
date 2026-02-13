#!/usr/bin/env python3
"""
Check if consolidation accidentally merged boss spawns with regular monsters.
Boss indicators: King, Lord, Master, Elder, unique names, or formations with only 1-2 total monsters
"""
import json
from pathlib import Path

# Common boss/elite keywords
BOSS_KEYWORDS = [
    'King', 'Lord', 'Master', 'Elder', 'Boss', 'Dragon', 'Demon', 'Ancient',
    'Great', 'Supreme', 'Dark', 'Shadow', 'Death', 'Blood', 'Chaos'
]

# Additional boss patterns
UNIQUE_NAMES = [
    'Minotaur', 'Cerberus', 'Hydra', 'Phoenix', 'Leviathan', 'Behemoth',
    'Chimera', 'Griffin', 'Wyvern', 'Golem'
]

def is_potential_boss(monster_name):
    """Check if monster name suggests it's a boss."""
    for keyword in BOSS_KEYWORDS + UNIQUE_NAMES:
        if keyword.lower() in monster_name.lower():
            return True
    return False

def check_file(filepath):
    """Check a single formation file for boss consolidation issues."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    issues = []
    warnings = []

    # Check formations
    for i, formation in enumerate(data.get('formations', [])):
        total = formation.get('total', 0)
        composition = formation.get('composition', [])

        # Check if formation has boss + other monsters
        boss_monsters = []
        regular_monsters = []

        for comp in composition:
            monster = comp.get('monster', '')
            count = comp.get('count', 0)

            if is_potential_boss(monster):
                boss_monsters.append(f"{monster} (x{count})")
            else:
                regular_monsters.append(f"{monster} (x{count})")

        # Issue: Boss mixed with regular monsters
        if boss_monsters and regular_monsters:
            issues.append({
                'type': 'formation',
                'index': i,
                'total': total,
                'boss': boss_monsters,
                'regular': regular_monsters,
                'severity': 'HIGH'
            })

        # Warning: Multiple bosses in same formation
        if len(boss_monsters) > 1:
            warnings.append({
                'type': 'formation',
                'index': i,
                'total': total,
                'bosses': boss_monsters,
                'severity': 'MEDIUM'
            })

    # Check zone_spawns
    for i, spawn in enumerate(data.get('zone_spawns', [])):
        total = spawn.get('total', 0)
        composition = spawn.get('composition', [])

        boss_monsters = []
        regular_monsters = []

        for comp in composition:
            monster = comp.get('monster', '')
            count = comp.get('count', 0)

            if is_potential_boss(monster):
                boss_monsters.append(f"{monster} (x{count})")
            else:
                regular_monsters.append(f"{monster} (x{count})")

        # Issue: Boss mixed with regular monsters
        if boss_monsters and regular_monsters:
            issues.append({
                'type': 'zone_spawn',
                'index': i,
                'total': total,
                'boss': boss_monsters,
                'regular': regular_monsters,
                'severity': 'HIGH'
            })

        # Warning: Multiple bosses
        if len(boss_monsters) > 1:
            warnings.append({
                'type': 'zone_spawn',
                'index': i,
                'total': total,
                'bosses': boss_monsters,
                'severity': 'MEDIUM'
            })

    return {
        'filepath': filepath,
        'level': data.get('level_name', 'Unknown'),
        'area': data.get('name', 'Unknown'),
        'issues': issues,
        'warnings': warnings
    }

def main():
    # Check all modified files
    modified_files = [
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

    print("=" * 80)
    print("BOSS CONSOLIDATION CHECK")
    print("=" * 80)
    print()

    all_issues = []
    all_warnings = []

    for filepath in modified_files:
        full_path = base_dir / filepath
        if not full_path.exists():
            print(f"WARNING: File not found: {filepath}")
            continue

        result = check_file(full_path)

        if result['issues']:
            all_issues.extend(result['issues'])
            print(f"[!] {result['level']} - {result['area']}")
            print(f"    File: {filepath}")
            for issue in result['issues']:
                print(f"    ISSUE: {issue['type']}[{issue['index']}] - {issue['total']} total")
                print(f"           Boss: {', '.join(issue['boss'])}")
                print(f"           Regular: {', '.join(issue['regular'])}")
            print()

        if result['warnings']:
            all_warnings.extend(result['warnings'])
            print(f"[?] {result['level']} - {result['area']}")
            print(f"    File: {filepath}")
            for warning in result['warnings']:
                print(f"    WARNING: {warning['type']}[{warning['index']}] - {warning['total']} total")
                print(f"             Multiple bosses: {', '.join(warning['bosses'])}")
            print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files checked: {len(modified_files)}")
    print(f"HIGH severity issues: {len(all_issues)}")
    print(f"MEDIUM severity warnings: {len(all_warnings)}")
    print()

    if not all_issues and not all_warnings:
        print("[OK] No boss consolidation issues found!")
    else:
        if all_issues:
            print("HIGH ISSUES: Boss monsters merged with regular monsters")
            print("  -> This could create unbalanced encounters")
            print("  -> Recommend: Split these formations manually")
            print()
        if all_warnings:
            print("MEDIUM WARNINGS: Multiple bosses in same formation")
            print("  -> May be intentional (elite packs)")
            print("  -> Review to ensure intended design")

if __name__ == '__main__':
    main()
