"""
Catalog all L (AI behavior index) and R values from all 41 areas.

Output: CSV showing which monsters have which L/R values across all areas.
Goal: Identify patterns and find potential hybrid AI values.
"""
import json
import sys
from pathlib import Path
import csv

FORMATIONS_DIR = Path(__file__).parent.parent.parent / "Data" / "formations"

def catalog_L_values():
    # Find all area JSONs (exclude vanilla backups)
    area_files = []
    for json_file in FORMATIONS_DIR.rglob("*.json"):
        if "_vanilla" in json_file.name or "_backup" in json_file.name:
            continue
        if json_file.parent.name in ["Scripts", "docs", "archive"]:
            continue
        area_files.append(json_file)

    print(f"[INFO] Found {len(area_files)} area JSON files")
    print(f"[INFO] Extracting L and R values...\n")

    # Collect all data
    all_data = []

    for json_file in sorted(area_files):
        try:
            data = json.loads(json_file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[WARN] Failed to read {json_file.name}: {e}")
            continue

        level_name = data.get("level_name", "Unknown")
        area_name = data.get("name", json_file.stem)
        monsters = data.get("monsters", [])
        assignments = data.get("assignment_entries", [])

        for assignment in assignments:
            slot = assignment.get("slot")
            L = assignment.get("L")
            R = assignment.get("R")

            monster_name = monsters[slot] if slot < len(monsters) else f"Slot{slot}"

            all_data.append({
                "level": level_name,
                "area": area_name,
                "slot": slot,
                "monster": monster_name,
                "L": L,
                "R": R
            })

    print(f"[INFO] Collected {len(all_data)} monster entries")

    # Write CSV
    csv_path = Path(__file__).parent / "L_values_catalog.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["level", "area", "slot", "monster", "L", "R"])
        writer.writeheader()
        writer.writerows(all_data)

    print(f"[OK] Wrote {csv_path.name}")

    # Analyze patterns
    print(f"\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}\n")

    # Unique L values
    L_values = sorted(set(row["L"] for row in all_data if row["L"] is not None))
    print(f"Unique L values: {L_values}")
    print(f"  Range: {min(L_values)} to {max(L_values)}")
    print(f"  Count: {len(L_values)}\n")

    # L value distribution
    from collections import Counter
    L_counts = Counter(row["L"] for row in all_data if row["L"] is not None)
    print("L value frequency:")
    for L in sorted(L_counts.keys()):
        print(f"  L={L}: {L_counts[L]} monsters")

    # Find monsters that use each L
    print(f"\n{'='*70}")
    print("MONSTERS BY L VALUE")
    print(f"{'='*70}\n")

    for L in sorted(L_values)[:10]:  # First 10 L values
        monsters_with_L = set(row["monster"] for row in all_data if row["L"] == L)
        print(f"L={L}: {', '.join(sorted(monsters_with_L)[:10])}")
        if len(monsters_with_L) > 10:
            print(f"  ... and {len(monsters_with_L) - 10} more")

    # Find non-self-referencing L (interesting cases)
    print(f"\n{'='*70}")
    print("NON-SELF-REFERENCING L (slot != L)")
    print(f"{'='*70}\n")

    non_self_ref = [row for row in all_data if row["slot"] != row["L"]]
    print(f"Found {len(non_self_ref)} cases:\n")

    for row in non_self_ref[:20]:
        print(f"  {row['level']} / {row['area']}")
        print(f"    Slot {row['slot']} ({row['monster']}): L={row['L']}, R={row['R']}")

    # Find potential hybrid AI (monsters with unusual L patterns)
    print(f"\n{'='*70}")
    print("POTENTIAL HYBRID AI CANDIDATES")
    print(f"{'='*70}\n")

    # Find monsters that appear with multiple different L values
    from collections import defaultdict
    monster_L_map = defaultdict(set)
    for row in all_data:
        monster_L_map[row["monster"]].add(row["L"])

    multi_L_monsters = {m: Ls for m, Ls in monster_L_map.items() if len(Ls) > 1}

    if multi_L_monsters:
        print(f"Monsters with multiple L values (may indicate AI variants):\n")
        for monster, Ls in sorted(multi_L_monsters.items())[:10]:
            print(f"  {monster}: {sorted(Ls)}")
    else:
        print("  (None found - each monster type uses consistent L)")

    return 0

if __name__ == '__main__':
    sys.exit(catalog_L_values())
