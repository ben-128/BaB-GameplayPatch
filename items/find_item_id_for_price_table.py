"""
find_item_id_for_price_table.py
Trouve l'ID/index des items qui correspond à leur position dans la table de prix

La table de prix à 0x002EA49A contient 32 prix.
Chaque item doit avoir un ID qui pointe vers sa position dans cette table.

Usage: py -3 find_item_id_for_price_table.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ORIGINAL = SCRIPT_DIR / "BLAZE_ORIGINAL.ALL"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"

ITEM_ENTRY_SIZE = 128
PRICE_TABLE_OFFSET = 0x002EA49A

# Prix connus depuis auction_prices/README.md
# Format: item_name -> (price, expected_index_in_table)
KNOWN_ITEMS = {
    "Healing Potion": (10, 0),
    "Shortsword": (22, 2),
    "Normal Sword": (24, 7),
    "Tomahawk": (26, 9),
    "Dagger": (28, 11),
    "Leather Armor": (36, 13),
    "Leather Shield": (46, 15),
    "Robe": (47, 18)
}

def read_price_table(data):
    """Lit la table de prix complète"""
    prices = []
    for i in range(32):
        offset = PRICE_TABLE_OFFSET + (i * 2)
        price = struct.unpack_from('<H', data, offset)[0]
        prices.append(price)
    return prices

def analyze_item_for_id(data, item_name, item_offset, expected_index):
    """Cherche l'index attendu dans les bytes de l'item"""

    print(f"\n{'='*70}")
    print(f"  {item_name}")
    print(f"{'='*70}")
    print(f"Offset: 0x{item_offset:08X}")
    print(f"Index attendu dans table: {expected_index} (0x{expected_index:02X})")

    # Lire l'entrée item
    item_data = data[item_offset:item_offset + ITEM_ENTRY_SIZE]

    # Chercher l'index comme byte simple
    byte_positions = [i for i, b in enumerate(item_data) if b == expected_index]

    if byte_positions:
        print(f"Index {expected_index} trouvé comme byte aux positions:")
        for pos in byte_positions:
            # Afficher le contexte
            start = max(0, pos - 4)
            end = min(len(item_data), pos + 5)
            context = item_data[start:end]
            hex_str = ' '.join(f'{b:02X}' for b in context)
            print(f"  +0x{pos:02X}: [{hex_str}]")
    else:
        print(f"Index {expected_index} NON trouvé comme byte")

    # Chercher comme word (16-bit)
    word_value = struct.pack('<H', expected_index)
    word_positions = []
    for i in range(len(item_data) - 1):
        if item_data[i:i+2] == word_value:
            word_positions.append(i)

    if word_positions:
        print(f"Index {expected_index} trouvé comme word (16-bit LE) aux positions:")
        for pos in word_positions:
            context = item_data[max(0, pos-4):min(len(item_data), pos+6)]
            hex_str = ' '.join(f'{b:02X}' for b in context)
            print(f"  +0x{pos:02X}: [{hex_str}]")

    # Afficher les premiers bytes de l'item (hors nom)
    print(f"\nPremiers bytes (hors nom):")
    print(f"  +0x10-0x1F: {' '.join(f'{b:02X}' for b in item_data[0x10:0x20])}")
    print(f"  +0x20-0x2F: {' '.join(f'{b:02X}' for b in item_data[0x20:0x30])}")
    print(f"  +0x30-0x3F: {' '.join(f'{b:02X}' for b in item_data[0x30:0x40])}")

    return byte_positions

def find_common_id_offset(results):
    """Trouve l'offset commun pour l'ID"""

    print(f"\n{'='*70}")
    print("  ANALYSE DES OFFSETS COMMUNS POUR L'ID")
    print(f"{'='*70}\n")

    from collections import Counter
    all_offsets = []

    for item_name, offsets in results.items():
        if offsets:
            all_offsets.extend(offsets)
            print(f"{item_name:20s}: offsets {offsets}")
        else:
            print(f"{item_name:20s}: AUCUN offset trouvé")

    if not all_offsets:
        print("\n[X] Aucun offset commun trouvé!")
        return None

    offset_counts = Counter(all_offsets)

    print(f"\nOffsets (triés par fréquence):")
    for offset, count in offset_counts.most_common():
        print(f"  +0x{offset:02X} (byte {offset:3d}): {count} occurrences")

    most_common = offset_counts.most_common(1)[0]
    print(f"\n[OK] Offset le plus probable: +0x{most_common[0]:02X} ({most_common[1]} items)")

    return most_common[0]

def extract_all_items_with_prices(data, items, id_offset, prices):
    """Extrait tous les items avec leur prix basé sur l'ID"""

    print(f"\n{'='*70}")
    print(f"  EXTRACTION AVEC ID À L'OFFSET +0x{id_offset:02X}")
    print(f"{'='*70}\n")

    items_with_prices = []

    for item in items:
        offset = int(item['offset'], 16)
        item_data = data[offset:offset + ITEM_ENTRY_SIZE]

        if len(item_data) < id_offset + 1:
            continue

        # Lire l'ID
        item_id = item_data[id_offset]

        # Vérifier si l'ID est valide (0-31)
        if 0 <= item_id < 32:
            price = prices[item_id]

            if price > 0:
                items_with_prices.append({
                    'name': item['name'],
                    'id': item_id,
                    'price': price,
                    'offset': item['offset'],
                    'category': item.get('category', 'Unknown')
                })

    # Trier par prix
    items_with_prices.sort(key=lambda x: x['price'])

    print(f"Items avec prix: {len(items_with_prices)}")
    print()

    # Grouper par prix pour voir les patterns
    from collections import defaultdict
    by_price = defaultdict(list)
    for item in items_with_prices:
        by_price[item['price']].append(item)

    print("Items groupés par prix:")
    for price in sorted(by_price.keys()):
        items_at_price = by_price[price]
        print(f"\n  {price:3d} gold ({len(items_at_price)} items):")
        for item in items_at_price[:10]:  # Limiter à 10 par prix
            print(f"    [ID {item['id']:2d}] {item['name']:30s} ({item['category']})")
        if len(items_at_price) > 10:
            print(f"    ... et {len(items_at_price) - 10} autres")

    return items_with_prices

def main():
    print("="*70)
    print("  RECHERCHE DE L'ID ITEM POUR LA TABLE DE PRIX")
    print("="*70)

    # Charger BLAZE.ALL
    print(f"\nChargement de {BLAZE_ORIGINAL}...")
    if not BLAZE_ORIGINAL.exists():
        print("ERREUR: Exécutez d'abord: py -3 extract_blaze_from_bin.py")
        return 1

    data = BLAZE_ORIGINAL.read_bytes()
    print(f"  {len(data):,} bytes")

    # Lire la table de prix
    print(f"\nLecture de la table de prix @ 0x{PRICE_TABLE_OFFSET:08X}...")
    prices = read_price_table(data)
    print(f"  {len(prices)} prix extraits")

    # Vérifier quelques prix connus
    print(f"\nVérification des prix connus:")
    for item_name, (expected_price, index) in KNOWN_ITEMS.items():
        actual_price = prices[index]
        match = "[OK]" if actual_price == expected_price else f"[X] attendu {expected_price}"
        print(f"  [{index:2d}] {item_name:20s}: {actual_price:3d} gold {match}")

    # Charger items
    print(f"\nChargement de {ALL_ITEMS_JSON}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)

    items = items_data['items']
    print(f"  {len(items)} items")

    # Analyser chaque item connu
    results = {}

    for item_name, (expected_price, expected_index) in KNOWN_ITEMS.items():
        # Trouver l'item
        item = next((i for i in items if i['name'] == item_name), None)

        if not item:
            print(f"\n[X] Item '{item_name}' non trouvé")
            continue

        item_offset = int(item['offset'], 16)
        offsets = analyze_item_for_id(data, item_name, item_offset, expected_index)
        results[item_name] = offsets

    # Trouver l'offset commun
    id_offset = find_common_id_offset(results)

    if id_offset is not None:
        # Extraire tous les items
        all_items_with_prices = extract_all_items_with_prices(data, items, id_offset, prices)

        # Sauvegarder
        output = {
            'metadata': {
                'id_offset': id_offset,
                'id_offset_hex': f'0x{id_offset:02X}',
                'price_table_offset': PRICE_TABLE_OFFSET,
                'price_table_offset_hex': f'0x{PRICE_TABLE_OFFSET:08X}',
                'items_with_prices': len(all_items_with_prices),
                'total_items': len(items),
                'extraction_date': '2026-02-04'
            },
            'items': all_items_with_prices
        }

        output_file = SCRIPT_DIR / "items_with_real_prices.json"
        print(f"\nSauvegarde dans {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print("  TERMINÉ!")
        print(f"{'='*70}\n")
        print(f"ID offset trouvé: +0x{id_offset:02X}")
        print(f"Items avec prix: {len(all_items_with_prices)}/{len(items)}")
        print()

        return 0
    else:
        print(f"\n[X] Impossible de trouver l'offset de l'ID")
        return 1

if __name__ == '__main__':
    try:
        import sys
        sys.exit(main())
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
