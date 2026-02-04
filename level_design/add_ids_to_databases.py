"""
add_ids_to_databases.py
Add numeric IDs to items and monsters databases

Usage: py -3 add_ids_to_databases.py
"""

from pathlib import Path
import json

SCRIPT_DIR = Path(__file__).parent.parent

def add_ids_to_items():
    """Add numeric IDs to items database"""
    items_file = SCRIPT_DIR / "items" / "all_items_clean.json"

    if not items_file.exists():
        print("ERROR: Items database not found!")
        return False

    print("Loading items database...")
    with open(items_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('items', [])
    print(f"Found {len(items)} items")

    # Add IDs based on index
    for i, item in enumerate(items):
        item['id'] = i

    print(f"Added IDs 0-{len(items)-1} to items")

    # Save updated database
    with open(items_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Items database updated: {items_file}")
    return True

def add_ids_to_monsters():
    """Add numeric IDs to monsters in individual files"""

    # Load from boss and normal_enemies folders
    monster_dirs = [
        SCRIPT_DIR / "monster_stats" / "boss",
        SCRIPT_DIR / "monster_stats" / "normal_enemies"
    ]

    all_monsters = []

    for directory in monster_dirs:
        if not directory.exists():
            continue

        for json_file in sorted(directory.glob("*.json")):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    monster = json.load(f)
                    all_monsters.append((json_file, monster))
            except Exception as e:
                print(f"Warning: Could not read {json_file.name}: {e}")

    print(f"\nFound {len(all_monsters)} monster files")

    # Add IDs
    for i, (filepath, monster) in enumerate(all_monsters):
        monster['id'] = i

        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(monster, f, indent=2, ensure_ascii=False)

    print(f"Added IDs 0-{len(all_monsters)-1} to monsters")
    print(f"[OK] Monster files updated")

    # Update index file if it exists
    index_file = SCRIPT_DIR / "monster_stats" / "_index.json"
    if index_file.exists():
        print("\nUpdating monster index...")
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        # Update monsters in index
        for i, monster_entry in enumerate(index_data.get('monsters', [])):
            monster_entry['id'] = i

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Monster index updated: {index_file}")

    return True

def main():
    print("=" * 70)
    print("  ADDING IDs TO DATABASES")
    print("=" * 70)
    print()

    # Add IDs to items
    print("[1] ITEMS DATABASE")
    print("-" * 70)
    items_ok = add_ids_to_items()

    print()

    # Add IDs to monsters
    print("[2] MONSTERS DATABASE")
    print("-" * 70)
    monsters_ok = add_ids_to_monsters()

    print()
    print("=" * 70)

    if items_ok and monsters_ok:
        print("[OK] SUCCESS - All databases updated with IDs!")
        print()
        print("Next steps:")
        print("  1. Re-run: py -3 analyze_chests.py")
        print("  2. Re-run: py -3 analyze_enemy_spawns.py")
        print("=" * 70)
    else:
        print("[ERROR] ERROR - Some databases could not be updated")
        print("=" * 70)

if __name__ == '__main__':
    main()
