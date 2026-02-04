"""
add_auction_prices.py
Ajoute les prix d'enchères aux items dans all_items_clean.json

La table de prix se trouve à 0x002EA49A dans BLAZE.ALL
Format: 32 words de 16-bit little-endian

Prix connus (selon auction_prices/README.md):
- Word 0: 10 (Healing Potion)
- Word 2: 22 (Shortsword)
- Word 7: 24 (Wooden Wand/Normal Sword)
- Word 9: 26 (Tomahawk)
- Word 11: 28 (Dagger)
- Word 13: 36 (Leather Armor)
- Word 15: 46 (Leather Shield)
- Word 18: 72 (Robe)

Usage: py -3 add_auction_prices.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent / "work" / "BLAZE.ALL"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"
OUTPUT_JSON = SCRIPT_DIR / "all_items_clean.json"

PRICE_TABLE_OFFSET = 0x002EA49A
PRICE_TABLE_SIZE = 32  # 32 words (16-bit)

# Mapping connu entre les indices de la table et les noms d'items
# Avec les prix originaux (avant les tests à 999)
KNOWN_PRICES = {
    0: (10, "Healing Potion"),
    2: (22, "Shortsword"),
    7: (24, ["Wooden Wand", "Normal Sword"]),  # Plusieurs items possibles
    9: (26, "Tomahawk"),
    11: (28, "Dagger"),
    13: (36, "Leather Armor"),
    15: (46, "Leather Shield"),
    18: (72, "Robe")
}


def extract_price_table(data):
    """Extrait la table de prix depuis BLAZE.ALL"""
    prices = []

    for i in range(PRICE_TABLE_SIZE):
        offset = PRICE_TABLE_OFFSET + (i * 2)
        if offset + 2 <= len(data):
            price = struct.unpack_from('<H', data, offset)[0]
            prices.append(price)
        else:
            prices.append(None)

    return prices


def normalize_name(name):
    """Normalise un nom pour le matching"""
    return name.lower().strip()


def find_item_by_name(items, target_name):
    """Trouve un item par son nom"""
    target_normalized = normalize_name(target_name)

    for item in items:
        if normalize_name(item['name']) == target_normalized:
            return item

    return None


def main():
    print("=" * 70)
    print("  Ajout des prix d'enchères aux items")
    print("=" * 70)
    print()

    # Charger BLAZE.ALL
    print(f"Chargement de {BLAZE_ALL}...")
    if not BLAZE_ALL.exists():
        print(f"ERREUR: {BLAZE_ALL} n'existe pas")
        return 1

    data = BLAZE_ALL.read_bytes()
    print(f"  {len(data):,} bytes chargés")

    # Note: BLAZE.ALL actuel contient des prix patchés à 999 pour les tests
    # Nous utilisons les prix originaux documentés dans auction_prices/README.md
    print(f"\nUtilisation des prix originaux documentés:")
    print("(Note: BLAZE.ALL actuel contient des valeurs de test à 999)\n")

    for price_index, (price, item_names) in KNOWN_PRICES.items():
        if isinstance(item_names, list):
            items_str = " ou ".join(item_names)
        else:
            items_str = item_names
        print(f"  Word[{price_index:2d}] = {price:3d} gold ({items_str})")

    # Charger all_items_clean.json
    print(f"\nChargement de {ALL_ITEMS_JSON}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)

    items = items_data['items']
    print(f"  {len(items)} items chargés")

    # Mapper les prix connus aux items
    print("\nMapping des prix connus aux items...")
    mapped_count = 0

    for price_index, (price, item_names) in KNOWN_PRICES.items():
        if not isinstance(item_names, list):
            item_names = [item_names]

        for item_name in item_names:
            item = find_item_by_name(items, item_name)

            if item:
                item['auction_price'] = price
                item['auction_price_index'] = price_index
                mapped_count += 1
                print(f"  [OK] {item_name}: {price} gold (index {price_index})")
            else:
                print(f"  [X] {item_name}: NOT FOUND in all_items_clean.json")

    print(f"\nTotal mappé: {mapped_count} items")

    # Mettre à jour les métadonnées
    items_data['metadata']['auction_prices_added'] = True
    items_data['metadata']['auction_prices_count'] = mapped_count
    items_data['metadata']['auction_prices_source'] = f'BLAZE.ALL offset 0x{PRICE_TABLE_OFFSET:08X}'
    items_data['metadata']['auction_prices_note'] = 'Prix connus mappés selon auction_prices/README.md'

    # Sauvegarder
    print(f"\nSauvegarde dans {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(items_data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 70)
    print("  Terminé!")
    print("=" * 70)
    print()
    print(f"Prix d'enchères ajoutés: {mapped_count} items")
    print(f"Items sans prix: {len(items) - mapped_count} items")
    print()
    print("Note: Seuls les prix connus documentés ont été mappés.")
    print("Les autres prix de la table (indices non connus) n'ont pas été assignés.")

    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
