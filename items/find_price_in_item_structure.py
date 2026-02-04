"""
find_price_in_item_structure.py
Trouve où est stocké le prix d'enchère dans la structure d'un item

On sait que certains items ont des prix connus:
- Healing Potion: 10 gold
- Shortsword: 22 gold
- Normal Sword: 24 gold
- Tomahawk: 26 gold
- Dagger: 28 gold
- Leather Armor: 36 gold
- Leather Shield: 46 gold
- Robe: 47 gold (ou 72)

On va analyser leurs données pour trouver où est stocké ce prix.

Usage: py -3 find_price_in_item_structure.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ORIGINAL = SCRIPT_DIR / "BLAZE_ORIGINAL.ALL"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"

ITEM_ENTRY_SIZE = 128

# Prix connus depuis auction_prices/README.md
KNOWN_PRICES = {
    "Healing Potion": 10,
    "Shortsword": 22,
    "Normal Sword": 24,
    "Tomahawk": 26,
    "Dagger": 28,
    "Leather Armor": 36,
    "Leather Shield": 46,
    "Robe": [47, 72]  # Deux valeurs possibles
}

def hex_dump(data, offset, length=128):
    """Affiche un hex dump"""
    print(f"\nHex dump @ 0x{offset:08X}:")
    for i in range(0, length, 16):
        if i >= len(data):
            break
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {offset+i:08X}: {hex_str:48s} {ascii_str}")

def find_value_in_bytes(data, value, fmt='<H'):
    """Trouve toutes les positions d'une valeur dans les données"""
    positions = []
    value_bytes = struct.pack(fmt, value)

    for i in range(len(data) - len(value_bytes) + 1):
        if data[i:i+len(value_bytes)] == value_bytes:
            positions.append(i)

    return positions

def analyze_item(data, item_name, item_offset, expected_price):
    """Analyse un item pour trouver son prix"""

    print("\n" + "="*70)
    print(f"  {item_name}")
    print("="*70)
    print(f"Offset: 0x{item_offset:08X}")
    print(f"Prix attendu: {expected_price}")

    # Lire 128 bytes (taille d'une entrée item)
    item_data = data[item_offset:item_offset + ITEM_ENTRY_SIZE]

    # Afficher hex dump
    hex_dump(item_data, item_offset, 128)

    # Chercher le prix comme 16-bit little-endian
    if isinstance(expected_price, list):
        for price in expected_price:
            positions = find_value_in_bytes(item_data, price, '<H')
            if positions:
                print(f"\nPrix {price} trouvé comme word (16-bit LE) aux offsets:")
                for pos in positions:
                    print(f"  +0x{pos:02X} (byte {pos})")
    else:
        positions = find_value_in_bytes(item_data, expected_price, '<H')
        print(f"\nPrix {expected_price} trouvé comme word (16-bit LE) aux offsets:")
        if positions:
            for pos in positions:
                print(f"  +0x{pos:02X} (byte {pos})")
        else:
            print("  Aucune occurrence!")

            # Chercher comme byte simple
            if expected_price < 256:
                byte_positions = [i for i, b in enumerate(item_data) if b == expected_price]
                if byte_positions:
                    print(f"\nPrix {expected_price} trouvé comme byte aux offsets:")
                    for pos in byte_positions:
                        print(f"  +0x{pos:02X} (byte {pos})")

    return positions if not isinstance(expected_price, list) else []

def find_common_offset(results):
    """Trouve l'offset commun dans tous les items"""

    print("\n" + "="*70)
    print("  ANALYSE DES OFFSETS COMMUNS")
    print("="*70)
    print()

    # Compter les occurrences de chaque offset
    from collections import Counter
    all_offsets = []

    for item_name, offsets in results.items():
        if offsets:
            all_offsets.extend(offsets)

    if not all_offsets:
        print("Aucun offset trouvé!")
        return None

    offset_counts = Counter(all_offsets)

    print("Offsets trouvés (triés par fréquence):")
    for offset, count in offset_counts.most_common():
        print(f"  +0x{offset:02X} (byte {offset:3d}): {count} occurrences")

    # L'offset le plus fréquent est probablement le bon
    most_common_offset = offset_counts.most_common(1)[0][0]

    print()
    print(f"Offset le plus probable: +0x{most_common_offset:02X}")

    return most_common_offset

def extract_all_prices(data, items, price_offset):
    """Extrait les prix de tous les items à l'offset trouvé"""

    print("\n" + "="*70)
    print(f"  EXTRACTION DE TOUS LES PRIX (offset +0x{price_offset:02X})")
    print("="*70)
    print()

    items_with_prices = []

    for item in items:
        offset = int(item['offset'], 16)

        # Lire le prix à l'offset trouvé
        if offset + price_offset + 2 <= len(data):
            price = struct.unpack_from('<H', data, offset + price_offset)[0]

            if price > 0 and price < 1000:  # Filtre de sanity
                items_with_prices.append({
                    'name': item['name'],
                    'price': price,
                    'offset': item['offset']
                })

    # Trier par prix
    items_with_prices.sort(key=lambda x: x['price'])

    print(f"Items avec prix valide (0 < prix < 1000): {len(items_with_prices)}")
    print()

    # Afficher les premiers et derniers
    print("Premiers 20 items (moins chers):")
    for item in items_with_prices[:20]:
        print(f"  {item['name']:30s} = {item['price']:3d} gold")

    if len(items_with_prices) > 20:
        print(f"\n... {len(items_with_prices) - 20} autres items ...")

    return items_with_prices

def main():
    print("="*70)
    print("  RECHERCHE DU PRIX DANS LA STRUCTURE DES ITEMS")
    print("="*70)

    # Charger BLAZE.ALL
    print(f"\nChargement de {BLAZE_ORIGINAL}...")
    if not BLAZE_ORIGINAL.exists():
        print("ERREUR: BLAZE_ORIGINAL.ALL n'existe pas")
        print("Exécutez d'abord: py -3 extract_blaze_from_bin.py")
        return 1

    data = BLAZE_ORIGINAL.read_bytes()
    print(f"  {len(data):,} bytes chargés")

    # Charger items
    print(f"\nChargement de {ALL_ITEMS_JSON}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)

    items = items_data['items']
    print(f"  {len(items)} items chargés")

    # Analyser chaque item connu
    results = {}

    for item_name, expected_price in KNOWN_PRICES.items():
        # Trouver l'item dans la liste
        item = None
        for i in items:
            if i['name'] == item_name:
                item = i
                break

        if not item:
            print(f"\nWARNING: Item '{item_name}' non trouvé dans all_items_clean.json")
            continue

        item_offset = int(item['offset'], 16)
        offsets = analyze_item(data, item_name, item_offset, expected_price)
        results[item_name] = offsets

    # Trouver l'offset commun
    common_offset = find_common_offset(results)

    if common_offset is not None:
        # Extraire tous les prix
        all_prices = extract_all_prices(data, items, common_offset)

        # Sauvegarder
        output = {
            'metadata': {
                'price_offset': common_offset,
                'price_offset_hex': f'0x{common_offset:02X}',
                'items_with_prices': len(all_prices),
                'extraction_date': '2026-02-04'
            },
            'items': all_prices
        }

        output_file = SCRIPT_DIR / "all_prices_extracted.json"
        print(f"\nSauvegarde dans {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print("\n" + "="*70)
        print("  TERMINÉ!")
        print("="*70)
        print()
        print(f"Offset du prix trouvé: +0x{common_offset:02X} (byte {common_offset})")
        print(f"Items avec prix: {len(all_prices)}")
        print()

        return 0
    else:
        print("\nERREUR: Impossible de trouver un offset commun")
        return 1

if __name__ == '__main__':
    try:
        import sys
        sys.exit(main())
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
