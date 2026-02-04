"""
build_complete_reference.py
Construit la référence complète des items à partir du FAQ

Stratégie simple:
1. Extraire tous les items avec leurs noms et locations (section Item Location)
2. Ajouter les descriptions (section Item Description)
3. Ajouter les effets et stats (section Item Potential + Special Effects)

Usage: py -3 build_complete_reference.py
"""

import json
import re
from pathlib import Path
from collections import OrderedDict

SCRIPT_DIR = Path(__file__).parent
FAQ_FILE = SCRIPT_DIR / "Blaze objets.txt"
OUTPUT_JSON = SCRIPT_DIR / "faq_items_reference.json"


def extract_all_items():
    """Extrait tous les items du FAQ"""

    with open(FAQ_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    items = OrderedDict()
    current_category = None
    in_item_location_section = False
    in_item_description_section = False
    in_item_potential_section = False
    in_special_effects_section = False

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Détecter les sections principales
        if 'II.Item Location' in line or 'II. Item Location' in line:
            in_item_location_section = True
            continue
        elif 'III. Chests' in line or 'III.Chests' in line:
            in_item_location_section = False
        elif 'VI.  Item Description' in line or 'VI. Item Description' in line:
            in_item_description_section = True
            continue
        elif 'VII. Item Potential' in line or 'VII.Item Potential' in line:
            in_item_description_section = False
            in_item_potential_section = True
            continue
        elif 'VIII. Special Effects' in line or 'VIII.Special Effects' in line:
            in_item_potential_section = False
            in_special_effects_section = True
            continue
        elif 'IX.' in line:
            in_special_effects_section = False

        # Section Item Location - extraire noms et catégories
        if in_item_location_section:
            # Détecter les catégories (ligne entre deux -*-*-*-)
            if line_stripped.startswith('-*-') and i+1 < len(lines):
                next_line = lines[i+1].strip()
                # Vérifier que c'est bien une catégorie (pas -*-*)
                if next_line and not next_line.startswith('-') and i+2 < len(lines):
                    third_line = lines[i+2].strip()
                    if third_line.startswith('-*-'):
                        # C'est une catégorie!
                        current_category = next_line
                        continue

            # Extraire les items (format: Nom = Location)
            if '=' in line_stripped and current_category:
                # Pattern flexible
                match = re.match(r'^([A-Z][A-Za-z\'\-\.\(\) ]+?)\s*(?:\*)?(?:\([^)]*\))?\s*=\s*(.+)$', line_stripped)
                if match:
                    name = match.group(1).strip().rstrip('*').strip()
                    location = match.group(2).strip()

                    # Nettoyer les variantes (ver1), (ver2)
                    base_name = re.sub(r'\s*\([vV]er\s*\d+\)', '', name).strip()

                    if base_name and len(base_name) >= 3:
                        if base_name not in items:
                            items[base_name] = {
                                'name': base_name,
                                'category': current_category,
                                'location': location,
                                'description': '',
                                'effects': [],
                                'special_effects': [],
                                'stats': {}
                            }

        # Section Item Description
        if in_item_description_section:
            # Format: Nom : Description
            match = re.match(r'^([A-Z][A-Za-z\'\-\.\(\) ]+?)\s*(?:\([^)]*\))?\s*:\s*(.+)$', line_stripped)
            if match:
                name = match.group(1).strip()
                description = match.group(2).strip()

                base_name = re.sub(r'\s*\([vV]er\s*\d+\)', '', name).strip()

                if base_name in items:
                    items[base_name]['description'] = description

        # Section Item Potential
        if in_item_potential_section:
            # Format: Nom : Effect description
            match = re.match(r'^([A-Z][A-Za-z\'\-\.\(\) ]+?)\s*:\s*(.+)$', line_stripped)
            if match:
                name = match.group(1).strip()
                effect = match.group(2).strip()

                base_name = re.sub(r'\s*\([vV]er\s*\d+\)', '', name).strip()

                if base_name in items:
                    items[base_name]['effects'].append(effect)

                    # Extraire les stats numériques
                    # HP restoration
                    hp_match = re.search(r'HP by\s+(\d+)\s*-?\s*(\d+)?', effect)
                    if hp_match:
                        items[base_name]['stats']['hp_restore_min'] = int(hp_match.group(1))
                        if hp_match.group(2):
                            items[base_name]['stats']['hp_restore_max'] = int(hp_match.group(2))

                    # MP restoration
                    mp_match = re.search(r'MP by\s+(\d+)\s*-?\s*(\d+)?', effect)
                    if mp_match:
                        items[base_name]['stats']['mp_restore_min'] = int(mp_match.group(1))
                        if mp_match.group(2):
                            items[base_name]['stats']['mp_restore_max'] = int(mp_match.group(2))

                    # Stat increases (permanent)
                    if '+' in effect and ('Permanent' in effect or '~' in effect):
                        stat_match = re.search(r'(\w+)\s+\+\s*(\d+)~(\d+)', effect)
                        if stat_match:
                            stat_name = stat_match.group(1).lower().replace(' ', '_')
                            items[base_name]['stats'][f'{stat_name}_min'] = int(stat_match.group(2))
                            items[base_name]['stats'][f'{stat_name}_max'] = int(stat_match.group(3))

        # Section Special Effects
        if in_special_effects_section:
            # Format: Nom : Special effect
            match = re.match(r'^([A-Z][A-Za-z\'\-\.\(\) ]+?)\s*:\s*(.+)$', line_stripped)
            if match:
                name = match.group(1).strip()
                effect = match.group(2).strip()

                base_name = re.sub(r'\s*\([vV]er\s*\d+\)', '', name).strip()

                if base_name in items:
                    items[base_name]['special_effects'].append(effect)

                    # Extraire les stats des effets spéciaux
                    # Attack bonus
                    atk = re.search(r'At\s*\+\s*(\d+)', effect)
                    if atk:
                        items[base_name]['stats']['attack_bonus'] = int(atk.group(1))

                    # Critical rate
                    crit = re.search(r'Critical.*?(\d+)%', effect)
                    if crit:
                        items[base_name]['stats']['critical_rate'] = int(crit.group(1))

                    # MP cost reduction
                    mp_cost = re.search(r'MP consumption\s*-\s*(\d+)%', effect)
                    if mp_cost:
                        items[base_name]['stats']['mp_cost_reduction'] = int(mp_cost.group(1))

                    # HP regeneration
                    hp_regen = re.search(r'Regenerate HP by\s*(-?\d+)', effect)
                    if hp_regen:
                        items[base_name]['stats']['hp_regen'] = int(hp_regen.group(1))

                    # MP regeneration
                    mp_regen = re.search(r'MP regeneration\s*\+\s*(\d+)', effect)
                    if mp_regen:
                        items[base_name]['stats']['mp_regen_bonus'] = int(mp_regen.group(1))

    return list(items.values())


def main():
    print("=" * 70)
    print("  Construction de la référence complète des items")
    print("=" * 70)
    print()

    print("Extraction des items du FAQ...")
    items = extract_all_items()

    print(f"Total items extraits: {len(items)}")
    print()

    # Stats
    by_category = {}
    for item in items:
        cat = item.get('category', 'Unknown')
        by_category[cat] = by_category.get(cat, 0) + 1

    print("Par catégorie:")
    for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {cat:<30} {count:>3} items")

    with_desc = sum(1 for i in items if i.get('description'))
    with_effects = sum(1 for i in items if i.get('effects'))
    with_special = sum(1 for i in items if i.get('special_effects'))
    with_stats = sum(1 for i in items if i.get('stats'))

    print(f"\nAvec descriptions: {with_desc} ({with_desc*100//len(items)}%)")
    print(f"Avec effets: {with_effects} ({with_effects*100//len(items)}%)")
    print(f"Avec effets spéciaux: {with_special} ({with_special*100//len(items)}%)")
    print(f"Avec stats numériques: {with_stats} ({with_stats*100//len(items)}%)")

    # Créer l'output
    output = {
        'metadata': {
            'source': 'Blaze objets.txt (GameFAQs)',
            'author': 'Sandy Saputra / holypriest',
            'version': '2.4',
            'total_items': len(items),
            'extraction_date': '2026-02-04',
            'note': 'Référence complète avec descriptions, effets et stats'
        },
        'items': items,
        'item_names': sorted([i['name'] for i in items])
    }

    # Sauvegarder
    print(f"\nSauvegarde dans {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 70)
    print("  Extraction terminée!")
    print("=" * 70)
    print()
    print(f"Output: {OUTPUT_JSON}")
    print()

    # Exemples
    print("Exemples d'items complets (avec toutes les données):")
    print("-" * 70)

    examples = ['Elixir', 'Bloodsword', 'Sol Crown', 'Red Ash', 'Healing Potion']
    for name in examples:
        item = next((i for i in items if i['name'] == name), None)
        if item:
            print(f"\n{name}:")
            print(f"  Catégorie: {item.get('category', 'N/A')}")
            if item.get('description'):
                print(f"  Description: {item['description'][:60]}")
            if item.get('effects'):
                print(f"  Effets: {'; '.join(item['effects'][:2])[:80]}")
            if item.get('special_effects'):
                print(f"  Spécial: {item['special_effects'][0][:60]}")
            if item.get('stats'):
                print(f"  Stats: {item['stats']}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
