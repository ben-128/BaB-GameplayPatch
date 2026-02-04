"""
extract_all_auction_prices.py
Extrait TOUS les prix d'enchères (32 entrées) et essaie de les mapper à tous les items

Stratégie:
1. Extraire les 32 prix depuis le BIN original (non patché)
2. Utiliser les mappings connus comme ancres
3. Analyser les patterns pour mapper les prix inconnus aux items
4. Utiliser des heuristiques (catégories, puissance des items, etc.)

Usage: py -3 extract_all_auction_prices.py
"""

import json
import struct
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
BIN_ORIGINAL = SCRIPT_DIR.parent.parent / "Blaze and Blade - Eternal Quest (E).bin"
BLAZE_ALL = SCRIPT_DIR.parent / "work" / "BLAZE.ALL"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"
OUTPUT_JSON = SCRIPT_DIR / "all_items_with_all_prices.json"

# Info depuis auction_prices/README.md
PRICE_TABLE_OFFSET_IN_BLAZE = 0x002EA49A
BLAZE_ALL_LBA = 185765
SECTOR_SIZE = 2048
PRICE_TABLE_SIZE = 32

# Mappings connus (indices -> items)
KNOWN_MAPPINGS = {
    0: "Healing Potion",
    2: "Shortsword",
    7: "Normal Sword",  # ou Wooden Wand
    9: "Tomahawk",
    11: "Dagger",
    13: "Leather Armor",
    15: "Leather Shield",
    18: "Robe"
}

# Catégories d'items pour aider au mapping
CATEGORY_KEYWORDS = {
    "weapon": ["sword", "dagger", "axe", "hammer", "wand", "staff", "bow", "spear"],
    "armor": ["armor", "mail", "plate"],
    "shield": ["shield", "buckler"],
    "helmet": ["helmet", "cap", "hat"],
    "potion": ["potion", "elixir"],
    "accessory": ["ring", "amulet", "necklace", "bracelet"],
    "robe": ["robe", "cloak"]
}


def extract_prices_from_bin(bin_path):
    """Extrait les 32 prix depuis le BIN original"""
    print(f"Extraction depuis BIN original: {bin_path.name}")

    if not bin_path.exists():
        print(f"  ERREUR: {bin_path} n'existe pas")
        return None

    # Calculer l'offset dans le BIN
    offset_in_bin = (BLAZE_ALL_LBA * SECTOR_SIZE) + PRICE_TABLE_OFFSET_IN_BLAZE

    prices = []
    with open(bin_path, 'rb') as f:
        f.seek(offset_in_bin)
        for i in range(PRICE_TABLE_SIZE):
            price_bytes = f.read(2)
            if len(price_bytes) == 2:
                price = struct.unpack('<H', price_bytes)[0]
                prices.append(price)
            else:
                prices.append(None)

    return prices


def extract_prices_from_blaze(blaze_path):
    """Extrait les 32 prix depuis BLAZE.ALL"""
    print(f"Extraction depuis BLAZE.ALL: {blaze_path.name}")

    if not blaze_path.exists():
        print(f"  ERREUR: {blaze_path} n'existe pas")
        return None

    data = blaze_path.read_bytes()
    prices = []

    for i in range(PRICE_TABLE_SIZE):
        offset = PRICE_TABLE_OFFSET_IN_BLAZE + (i * 2)
        if offset + 2 <= len(data):
            price = struct.unpack_from('<H', data, offset)[0]
            prices.append(price)
        else:
            prices.append(None)

    return prices


def categorize_item(item_name):
    """Détermine la catégorie d'un item basée sur son nom"""
    name_lower = item_name.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category

    return "unknown"


def estimate_item_power(item):
    """Estime la puissance d'un item basée sur ses stats"""
    stats = item.get('stats', {})

    # Calculer un score basé sur les stats
    power_score = 0

    # Stats d'attaque/défense
    if '0x30' in stats:  # Souvent AT
        power_score += stats['0x30'] * 10
    if '0x32' in stats:  # Souvent DEF
        power_score += stats['0x32'] * 10
    if '0x12' in stats:
        power_score += stats['0x12']

    # Attributs
    attrs = item.get('attributes', {})
    for attr_val in attrs.values():
        if isinstance(attr_val, (int, float)):
            power_score += abs(attr_val) * 5

    return power_score


def smart_price_mapping(prices, items):
    """
    Mapping intelligent des prix aux items

    Stratégie:
    1. Commencer avec les mappings connus
    2. Grouper les items par catégorie
    3. Trier les items par puissance estimée
    4. Trier les prix disponibles
    5. Mapper en associant prix bas -> items faibles, prix hauts -> items forts
    """

    # Créer une copie des mappings connus
    price_to_item = {}
    used_items = set()

    # Mapper les items connus
    for price_idx, item_name in KNOWN_MAPPINGS.items():
        if price_idx < len(prices) and prices[price_idx]:
            # Trouver l'item dans la liste
            for item in items:
                if item['name'].lower() == item_name.lower():
                    price_to_item[price_idx] = {
                        'item': item,
                        'price': prices[price_idx],
                        'confidence': 'known'
                    }
                    used_items.add(item['name'])
                    break

    print(f"\nMappings connus: {len(price_to_item)}")

    # Grouper les items restants par catégorie
    items_by_category = defaultdict(list)
    for item in items:
        if item['name'] not in used_items:
            category = categorize_item(item['name'])
            items_by_category[category].append(item)

    # Trier chaque catégorie par puissance estimée
    for category in items_by_category:
        items_by_category[category].sort(key=estimate_item_power)

    # Trouver les prix disponibles (non utilisés)
    available_prices = []
    for idx, price in enumerate(prices):
        if idx not in price_to_item and price and price > 0 and price != 999:
            available_prices.append((idx, price))

    # Trier les prix disponibles
    available_prices.sort(key=lambda x: x[1])

    print(f"Prix disponibles pour mapping: {len(available_prices)}")
    print(f"Items sans prix: {sum(len(items) for items in items_by_category.values())}")

    # Mapper intelligemment
    # Pour l'instant, on va mapper uniquement les items qui semblent être des items de base
    # (potions, équipement léger, etc.)

    basic_items_candidates = []

    # Chercher des potions, équipements de base, etc.
    for item in items:
        if item['name'] in used_items:
            continue

        name_lower = item['name'].lower()

        # Potions et consommables
        if any(word in name_lower for word in ['potion', 'elixir', 'herb', 'medicine']):
            basic_items_candidates.append(('potion', item))

        # Armes de base
        elif any(word in name_lower for word in ['short', 'wooden', 'bronze', 'iron', 'basic']):
            if 'sword' in name_lower or 'dagger' in name_lower or 'axe' in name_lower:
                basic_items_candidates.append(('basic_weapon', item))

        # Armures légères
        elif any(word in name_lower for word in ['leather', 'cloth', 'light']):
            if 'armor' in name_lower or 'vest' in name_lower or 'robe' in name_lower:
                basic_items_candidates.append(('light_armor', item))

    print(f"\nCandidats pour mapping automatique: {len(basic_items_candidates)}")

    # Trier les candidats par puissance
    basic_items_candidates.sort(key=lambda x: estimate_item_power(x[1]))

    # Mapper les candidats aux prix disponibles (en commençant par les moins chers)
    for i, (item_type, item) in enumerate(basic_items_candidates):
        if i < len(available_prices):
            price_idx, price = available_prices[i]
            price_to_item[price_idx] = {
                'item': item,
                'price': price,
                'confidence': 'estimated',
                'item_type': item_type
            }
            used_items.add(item['name'])

    return price_to_item, available_prices[len(basic_items_candidates):]


def main():
    print("=" * 70)
    print("  Extraction COMPLÈTE des prix d'enchères")
    print("=" * 70)
    print()

    # Essayer d'extraire depuis le BIN original
    prices = None

    if BIN_ORIGINAL.exists():
        prices = extract_prices_from_bin(BIN_ORIGINAL)

    # Fallback: extraire depuis BLAZE.ALL
    if not prices or all(p == 999 for p in prices if p):
        print("\nBIN original introuvable ou patché, essai depuis BLAZE.ALL...")
        prices = extract_prices_from_blaze(BLAZE_ALL)

    # Si tout est à 999, utiliser les valeurs connues
    if all(p == 999 for p in prices if p):
        print("\n⚠️  ATTENTION: Tous les prix sont à 999 (valeurs de test)")
        print("    Utilisation des prix connus documentés seulement.\n")

        # Utiliser seulement les prix connus
        prices_display = ["?" for _ in range(PRICE_TABLE_SIZE)]
        for idx, item_name in KNOWN_MAPPINGS.items():
            # Utiliser les prix originaux connus
            known_prices = {
                0: 10, 2: 22, 7: 24, 9: 26, 11: 28, 13: 36, 15: 46, 18: 72
            }
            if idx in known_prices:
                prices[idx] = known_prices[idx]
                prices_display[idx] = str(known_prices[idx])
    else:
        prices_display = [str(p) if p else "?" for p in prices]

    # Afficher la table de prix
    print("\nTable de prix complète:")
    for i in range(0, PRICE_TABLE_SIZE, 8):
        row = [f"{j:2d}:{prices_display[j]:>4s}" for j in range(i, min(i+8, PRICE_TABLE_SIZE))]
        print(f"  {' | '.join(row)}")

    # Compter les prix valides
    valid_prices = [p for p in prices if p and p > 0 and p != 999]
    print(f"\nPrix valides trouvés: {len(valid_prices)}/{PRICE_TABLE_SIZE}")

    # Charger les items
    print(f"\nChargement de {ALL_ITEMS_JSON}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)

    items = items_data['items']
    print(f"  {len(items)} items chargés")

    # Mapping intelligent
    print("\n" + "=" * 70)
    print("  Mapping intelligent prix <-> items")
    print("=" * 70)

    price_to_item, unmapped_prices = smart_price_mapping(prices, items)

    # Appliquer les mappings aux items
    for price_idx, mapping in price_to_item.items():
        item = mapping['item']
        item['auction_price'] = mapping['price']
        item['auction_price_index'] = price_idx
        item['auction_price_confidence'] = mapping['confidence']
        if 'item_type' in mapping:
            item['auction_price_type'] = mapping['item_type']

    # Statistiques
    items_with_price = [i for i in items if 'auction_price' in i]
    items_known = [i for i in items_with_price if i.get('auction_price_confidence') == 'known']
    items_estimated = [i for i in items_with_price if i.get('auction_price_confidence') == 'estimated']

    print("\n" + "=" * 70)
    print("  Résultats")
    print("=" * 70)
    print(f"\nTotal items avec prix: {len(items_with_price)}/{len(items)}")
    print(f"  - Prix connus (documentés): {len(items_known)}")
    print(f"  - Prix estimés (heuristiques): {len(items_estimated)}")
    print(f"\nPrix non mappés: {len(unmapped_prices)}")

    # Afficher les mappings
    print("\nItems avec prix CONNUS:")
    for item in sorted(items_known, key=lambda x: x['auction_price']):
        print(f"  [{item['auction_price_index']:2d}] {item['name']:30s} = {item['auction_price']:3d} gold")

    if items_estimated:
        print("\nItems avec prix ESTIMÉS:")
        for item in sorted(items_estimated, key=lambda x: x['auction_price']):
            item_type = item.get('auction_price_type', 'unknown')
            print(f"  [{item['auction_price_index']:2d}] {item['name']:30s} = {item['auction_price']:3d} gold ({item_type})")

    # Mettre à jour les métadonnées
    items_data['metadata']['auction_prices_extraction_complete'] = True
    items_data['metadata']['auction_prices_total_mapped'] = len(items_with_price)
    items_data['metadata']['auction_prices_known'] = len(items_known)
    items_data['metadata']['auction_prices_estimated'] = len(items_estimated)
    items_data['metadata']['auction_prices_unmapped'] = len(unmapped_prices)

    # Sauvegarder
    print(f"\nSauvegarde dans {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(items_data, f, indent=2, ensure_ascii=False)

    # Aussi mettre à jour all_items_clean.json
    print(f"Mise à jour de {ALL_ITEMS_JSON}...")
    with open(ALL_ITEMS_JSON, 'w', encoding='utf-8') as f:
        json.dump(items_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("  Terminé!")
    print("=" * 70)
    print()

    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
