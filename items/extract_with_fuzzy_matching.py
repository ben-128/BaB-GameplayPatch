"""
extract_with_fuzzy_matching.py
Extraction avec matching amélioré pour trouver plus d'items

Stratégies:
1. Exact match
2. Match sans espaces/apostrophes
3. Match avec variantes (The, of, etc.)
4. Match par sous-chaînes
5. Levenshtein distance

Usage: py -3 extract_with_fuzzy_matching.py
"""

import json
import struct
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
FAQ_FILE = SCRIPT_DIR / "faq_items_reference.json"
BLAZE_ALL = SCRIPT_DIR.parent / "work" / "BLAZE.ALL"
OUTPUT_JSON = SCRIPT_DIR / "all_items_clean.json"

ITEM_ENTRY_SIZE = 128


def normalize_name(name):
    """Normalise un nom pour le matching"""
    name = name.lower()
    name = name.replace("'", "").replace("-", "").replace(" ", "")
    name = name.replace("the", "").replace("of", "")
    return name


def generate_variants(name):
    """Génère des variantes d'un nom"""
    variants = [name]

    # Sans espaces
    variants.append(name.replace(" ", ""))

    # Sans apostrophes
    variants.append(name.replace("'", ""))

    # Sans "of", "the", etc.
    for word in [" of ", " the ", "The "]:
        if word in name:
            variants.append(name.replace(word, " ").strip())

    # Abréviations
    replacements = {
        "Hammer": "Hmr",
        "Wand": "Wnd",
        "Sword": "Swd",
        "Dagger": "Dgr",
        "Blade": "Bld"
    }

    for full, abbr in replacements.items():
        if full in name:
            variants.append(name.replace(full, abbr))

    # Inversions (Bolt of Larie -> Larie Bolt)
    if " of " in name:
        parts = name.split(" of ")
        if len(parts) == 2:
            variants.append(f"{parts[1]} {parts[0]}")

    return list(set(variants))


def levenshtein_distance(s1, s2):
    """Calcule la distance de Levenshtein entre deux chaînes"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_item_fuzzy(data, faq_name):
    """Cherche un item avec fuzzy matching"""
    # 1. Exact match
    search_bytes = faq_name.encode('ascii', errors='ignore')
    if data.find(search_bytes) != -1:
        return find_all_offsets(data, faq_name)

    # 2. Variantes
    variants = generate_variants(faq_name)
    for variant in variants:
        search_bytes = variant.encode('ascii', errors='ignore')
        if data.find(search_bytes) != -1:
            return find_all_offsets(data, variant)

    # 3. Sous-chaînes significatives (mots de 5+ caractères)
    words = [w for w in faq_name.split() if len(w) >= 5]
    for word in words:
        search_bytes = word.encode('ascii', errors='ignore')
        offsets = find_all_offsets(data, word)
        if offsets:
            # Vérifier que c'est bien un item (pas au milieu d'un autre mot)
            for offset in offsets:
                # Lire autour pour voir si c'est un nom d'item valide
                if offset > 0 and offset < len(data) - 50:
                    context = data[offset-5:offset+40]
                    # Si précédé de null bytes (début d'entrée)
                    if context[:5].count(0) >= 3:
                        return [offset]

    # 4. Levenshtein pour noms très similaires
    # Scanner le fichier pour trouver des noms similaires
    normalized_faq = normalize_name(faq_name)
    best_match = None
    best_distance = float('inf')

    # Scanner des positions potentielles d'items (tous les 128 bytes)
    for offset in range(0, len(data) - 128, 128):
        # Lire potentiel nom d'item
        name_bytes = bytearray()
        for i in range(offset, min(offset + 40, len(data))):
            if data[i] == 0:
                break
            if 32 <= data[i] <= 126:
                name_bytes.append(data[i])
            else:
                break

        if len(name_bytes) >= 3:
            try:
                candidate = name_bytes.decode('ascii', errors='ignore')
                normalized_candidate = normalize_name(candidate)

                distance = levenshtein_distance(normalized_faq, normalized_candidate)

                # Si très similaire (distance <= 2)
                if distance <= 2 and distance < best_distance:
                    best_distance = distance
                    best_match = offset

            except:
                pass

    if best_match and best_distance <= 2:
        return [best_match]

    return []


def find_all_offsets(data, item_name):
    """Trouve tous les offsets d'un item"""
    search_bytes = item_name.encode('ascii', errors='ignore')
    offsets = []

    pos = 0
    while True:
        pos = data.find(search_bytes, pos)
        if pos == -1:
            break

        # Vérifier null byte après
        if pos + len(search_bytes) < len(data):
            if data[pos + len(search_bytes)] == 0:
                offsets.append(pos)

        pos += 1

    return offsets


def extract_item_entry(data, offset, item_name):
    """Extrait l'entrée complète d'un item"""
    # Aligner sur 128 bytes
    alignments = [offset, (offset // 128) * 128, offset - 16, offset - 32]

    for test_offset in alignments:
        if test_offset < 0 or test_offset + ITEM_ENTRY_SIZE > len(data):
            continue

        entry = data[test_offset:test_offset + ITEM_ENTRY_SIZE]

        # Vérifier que le nom est là
        if item_name.lower() in entry[:50].decode('ascii', errors='ignore').lower():
            # Extraire stats
            stats = {}
            for stat_offset in [0x10, 0x12, 0x14, 0x16, 0x30, 0x32, 0x36]:
                if stat_offset + 2 <= len(entry):
                    val = struct.unpack_from('<H', entry, stat_offset)[0]
                    if val != 0:
                        stats[f'0x{stat_offset:02X}'] = val

            # Description
            description = ""
            if len(entry) > 0x40 and entry[0x40] == 0x0C:
                desc_bytes = bytearray()
                for i in range(0x41, len(entry)):
                    if entry[i] == 0:
                        break
                    if 32 <= entry[i] <= 126:
                        desc_bytes.append(entry[i])

                if desc_bytes:
                    desc_text = desc_bytes.decode('ascii', errors='ignore')
                    if '/' in desc_text:
                        parts = desc_text.split('/', 1)
                        if len(parts) == 2:
                            description = parts[1].strip()

            return {
                'offset': f'0x{test_offset:08X}',
                'stats': stats,
                'description': description
            }

    return None


def main():
    print("=" * 70)
    print("  Extraction avec Fuzzy Matching amélioré")
    print("=" * 70)
    print()

    # Charger FAQ
    print(f"Chargement de {FAQ_FILE}...")
    with open(FAQ_FILE, 'r', encoding='utf-8') as f:
        faq_data = json.load(f)

    faq_items = faq_data['items']
    print(f"  {len(faq_items)} items dans le FAQ")

    # Charger BLAZE.ALL
    print(f"\nChargement de {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"  {len(data):,} bytes")

    # Extraire avec fuzzy matching
    print("\nExtraction avec fuzzy matching...")
    found_items = []
    not_found = []

    for i, faq_item in enumerate(faq_items, 1):
        if i % 50 == 0:
            print(f"  Progrès: {i}/{len(faq_items)} ({i*100//len(faq_items)}%)")

        name = faq_item['name']
        offsets = find_item_fuzzy(data, name)

        if offsets:
            entry = extract_item_entry(data, offsets[0], name)

            if entry:
                item = {
                    'name': name,
                    'offset': entry['offset'],
                    'offset_decimal': int(entry['offset'], 16),
                    'category': faq_item.get('category', 'Unknown'),
                    'description': entry['description'],
                    'faq_description': faq_item.get('description', ''),
                    'stats': entry['stats'],
                    'effects': faq_item.get('effects', []),
                    'special_effects': faq_item.get('special_effects', []),
                    'attributes': faq_item.get('attributes', {}),
                    'occurrences_count': len(offsets),
                    'all_offsets': [f'0x{o:08X}' for o in offsets[:10]]
                }

                found_items.append(item)
            else:
                not_found.append(name)
        else:
            not_found.append(name)

    # Trier
    found_items.sort(key=lambda x: x['offset_decimal'])

    print()
    print(f"Items trouvés: {len(found_items)}/{len(faq_items)} ({len(found_items)*100//len(faq_items)}%)")
    print(f"Items manquants: {len(not_found)}")

    # Créer output
    output = {
        'metadata': {
            'source': 'BLAZE.ALL + FAQ Reference (fuzzy matching)',
            'game': 'Blaze & Blade: Eternal Quest',
            'total_items': len(found_items),
            'faq_items_total': len(faq_items),
            'extraction_date': '2026-02-04',
            'note': 'Extraction avec fuzzy matching pour trouver plus d\'items'
        },
        'items': found_items
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
    print(f"Total: {len(found_items)} items extraits")
    print()

    if not_found:
        print(f"Items manquants ({len(not_found)}):")
        for name in not_found[:20]:
            print(f"  - {name}")
        if len(not_found) > 20:
            print(f"  ... et {len(not_found) - 20} autres")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
