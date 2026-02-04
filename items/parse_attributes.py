"""
parse_attributes.py
Parse la section IX. Equipment Attribute pour extraire les stats complètes

Usage: py -3 parse_attributes.py
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FAQ_FILE = SCRIPT_DIR / "Blaze objets.txt"
REF_FILE = SCRIPT_DIR / "faq_items_reference.json"
OUTPUT_FILE = SCRIPT_DIR / "faq_items_reference.json"


def parse_attributes_section(content):
    """Parse la section IX. Equipment Attribute"""
    lines = content.split('\n')

    # Trouver la section
    start_idx = None
    for i, line in enumerate(lines):
        if 'IX. Equipment Attribute' in line or 'IX.Equipment Attribute' in line:
            start_idx = i
            break

    if not start_idx:
        return {}

    attributes = {}

    # Parser les lignes avec format:
    # "Normal Sword  0    0    0    0     0    0    0  -   7    0     0      0"
    pattern = re.compile(r'^([A-Za-z][A-Za-z\'\-\.\(\) ]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+-\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)')

    for line in lines[start_idx:start_idx+500]:  # Scanner 500 lignes
        match = pattern.match(line)
        if match:
            name = match.group(1).strip()

            # Nettoyer le nom (enlever abréviations)
            name = name.replace('Bld.', 'Blade')
            name = name.replace('Hmr.', 'Hammer')
            name = name.replace('Swd.', 'Sword')
            name = name.replace('Dgr.', 'Dagger')
            name = name.replace('Wnd.', 'Wand')
            name = name.replace('Orichal.', 'Orichalca')

            attributes[name] = {
                'str': int(match.group(2)),
                'int': int(match.group(3)),
                'wil': int(match.group(4)),
                'agl': int(match.group(5)),
                'con': int(match.group(6)),
                'pow': int(match.group(7)),
                'luk': int(match.group(8)),
                'at': int(match.group(9)),
                'mat': int(match.group(10)),
                'def': int(match.group(11)),
                'mdef': int(match.group(12))
            }

    return attributes


def merge_attributes(ref_data, attributes):
    """Merge les attributs dans la référence"""
    updated = 0

    for item in ref_data['items']:
        name = item['name']

        # Chercher l'item dans les attributs (exact match)
        if name in attributes:
            if 'attributes' not in item:
                item['attributes'] = {}
            item['attributes'].update(attributes[name])
            updated += 1
        else:
            # Chercher avec variantes
            for attr_name, attr_vals in attributes.items():
                if name.lower() in attr_name.lower() or attr_name.lower() in name.lower():
                    if 'attributes' not in item:
                        item['attributes'] = {}
                    item['attributes'].update(attr_vals)
                    updated += 1
                    break

    return ref_data, updated


def main():
    print("=" * 70)
    print("  Parse de la section Attributes")
    print("=" * 70)
    print()

    # Lire le FAQ
    print(f"Lecture de {FAQ_FILE}...")
    content = FAQ_FILE.read_text(encoding='utf-8', errors='ignore')

    # Parser les attributs
    print("Parse de la section IX. Equipment Attribute...")
    attributes = parse_attributes_section(content)
    print(f"  {len(attributes)} items avec attributs trouvés")

    # Charger la référence existante
    print(f"\nChargement de {REF_FILE}...")
    with open(REF_FILE, 'r', encoding='utf-8') as f:
        ref_data = json.load(f)

    # Merger
    print("Fusion des attributs...")
    ref_data, updated = merge_attributes(ref_data, attributes)
    print(f"  {updated} items mis à jour avec attributs")

    # Sauvegarder
    print(f"\nSauvegarde dans {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(ref_data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 70)
    print("  Terminé!")
    print("=" * 70)
    print()

    # Exemples
    print("Exemples d'items avec attributs complets:")
    print("-" * 70)

    examples = ['Normal Sword', 'Bloodsword', 'Elixir', 'Sol Crown']
    for name in examples:
        item = next((i for i in ref_data['items'] if i['name'] == name), None)
        if item and item.get('attributes'):
            print(f"\n{name}:")
            attrs = item['attributes']
            print(f"  AT: {attrs.get('at', 0)}, DEF: {attrs.get('def', 0)}, MDEF: {attrs.get('mdef', 0)}")
            if attrs.get('str'):
                print(f"  STR: +{attrs['str']}")
            if attrs.get('int'):
                print(f"  INT: +{attrs['int']}")
            if attrs.get('pow'):
                print(f"  POW: +{attrs['pow']}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
