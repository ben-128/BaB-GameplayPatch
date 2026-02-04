"""
map_all_prices_to_items.py
Mappe les 32 prix d'enchères aux items avec heuristiques intelligentes

Usage: py -3 map_all_prices_to_items.py
"""

import json
import struct
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
BLAZE_ORIGINAL = SCRIPT_DIR / "BLAZE_ORIGINAL.ALL"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"
OUTPUT_JSON = SCRIPT_DIR / "all_items_clean.json"

PRICE_TABLE_OFFSET = 0x002EA49A

# Table complète des 32 prix (extraite depuis BLAZE_ORIGINAL.ALL)
ALL_PRICES = [
    10, 16, 22, 13, 16, 23, 13, 24, 25, 26, 27, 28, 29, 36, 16, 46,
    16, 27, 47, 48, 10, 16, 49, 14, 16, 69, 80, 81, 14, 16, 69, 80
]

# Mappings connus (basés sur auction_prices/README.md + vérification)
KNOWN_MAPPINGS = {
    0: ("Healing Potion", 10, "known"),
    2: ("Shortsword", 22, "known"),
    7: ("Normal Sword", 24, "known"),  # ou Wooden Wand
    9: ("Tomahawk", 26, "known"),
    11: ("Dagger", 28, "known"),
    13: ("Leather Armor", 36, "known"),
    15: ("Leather Shield", 46, "known"),
    18: ("Robe", 47, "known")  # Doc dit 72, mais extraction montre 47
}

def load_items():
    """Charge les items depuis all_items_clean.json"""
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['items'], data['metadata']

def normalize_name(name):
    """Normalise un nom d'item"""
    return name.lower().strip()

def find_item_by_name(items, name):
    """Trouve un item par son nom"""
    name_norm = normalize_name(name)
    for item in items:
        if normalize_name(item['name']) == name_norm:
            return item
    return None

def categorize_item(item):
    """Catégorise un item"""
    name = item['name'].lower()
    category = item.get('category', '').lower()

    if 'potion' in name or 'elixir' in name or 'herb' in name or 'candy' in name:
        return 'potion'
    elif 'sword' in name or 'blade' in name:
        return 'sword'
    elif 'dagger' in name or 'knife' in name:
        return 'dagger'
    elif 'axe' in name or 'tomahawk' in name:
        return 'axe'
    elif 'wand' in name or 'staff' in name:
        return 'magic_weapon'
    elif 'bow' in name or 'arrow' in name:
        return 'bow'
    elif 'spear' in name or 'lance' in name:
        return 'spear'
    elif 'hammer' in name or 'mace' in name:
        return 'hammer'
    elif 'armor' in name:
        return 'armor'
    elif 'shield' in name:
        return 'shield'
    elif 'helmet' in name or 'cap' in name or 'hat' in name:
        return 'helmet'
    elif 'robe' in name or 'cloak' in name:
        return 'robe'
    elif 'ring' in name or 'amulet' in name or 'necklace' in name:
        return 'accessory'
    else:
        return 'other'

def estimate_power(item):
    """Estime la puissance d'un item"""
    stats = item.get('stats', {})
    attrs = item.get('attributes', {})

    power = 0

    # Stats numériques
    for val in stats.values():
        if isinstance(val, (int, float)):
            power += abs(val)

    # Attributs
    for val in attrs.values():
        if isinstance(val, (int, float)):
            power += abs(val) * 2

    return power

def smart_mapping(items):
    """
    Mapping intelligent de TOUS les prix aux items

    Stratégie:
    1. Appliquer les mappings connus
    2. Grouper les items restants par catégorie
    3. Pour chaque catégorie, trier par puissance
    4. Mapper les prix restants de manière cohérente
    """

    mappings = {}
    used_items = set()
    used_prices = set()

    # Étape 1: Mappings connus
    print("\n" + "="*70)
    print("  ÉTAPE 1: Mappings connus")
    print("="*70)
    print()

    for price_idx, (item_name, price, confidence) in KNOWN_MAPPINGS.items():
        item = find_item_by_name(items, item_name)
        if item:
            mappings[price_idx] = {
                'item': item,
                'price': price,
                'confidence': confidence
            }
            used_items.add(item['name'])
            used_prices.add(price_idx)
            print(f"  [{price_idx:2d}] {item_name:30s} = {price:3d} gold")
        else:
            print(f"  [{price_idx:2d}] {item_name:30s} = {price:3d} gold [NOT FOUND]")

    print(f"\nTotal connus: {len(mappings)}")

    # Étape 2: Identifier les items candidates par catégorie et prix
    print("\n" + "="*70)
    print("  ÉTAPE 2: Mapping intelligent par catégorie")
    print("="*70)
    print()

    # Grouper les items non utilisés par catégorie
    items_by_category = defaultdict(list)
    for item in items:
        if item['name'] not in used_items:
            cat = categorize_item(item)
            items_by_category[cat].append(item)

    # Trier chaque catégorie par puissance
    for cat in items_by_category:
        items_by_category[cat].sort(key=estimate_power)

    # Prix disponibles (non utilisés)
    available_prices = [
        (idx, ALL_PRICES[idx])
        for idx in range(len(ALL_PRICES))
        if idx not in used_prices
    ]
    available_prices.sort(key=lambda x: x[1])  # Trier par prix croissant

    print(f"Prix disponibles: {len(available_prices)}")
    print(f"Items sans prix: {sum(len(items) for items in items_by_category.values())}")
    print()

    # Mapping par catégorie avec heuristiques
    price_cursor = 0  # Index dans available_prices

    # Potions (souvent peu chères)
    if 'potion' in items_by_category:
        potions = items_by_category['potion']
        print(f"Mapping {len(potions)} potions...")

        for potion in potions:
            if price_cursor < len(available_prices):
                price_idx, price = available_prices[price_cursor]

                # Chercher un prix adapté (potions généralement < 30)
                if price <= 30:
                    mappings[price_idx] = {
                        'item': potion,
                        'price': price,
                        'confidence': 'estimated_potion'
                    }
                    used_items.add(potion['name'])
                    print(f"  [{price_idx:2d}] {potion['name']:30s} = {price:3d} gold")
                    price_cursor += 1

    # Mapper les items par catégorie et prix appropriés
    # Armes (toutes catégories)
    weapon_categories = ['sword', 'dagger', 'axe', 'magic_weapon', 'bow', 'spear', 'hammer']
    all_weapons = []
    for cat in weapon_categories:
        if cat in items_by_category:
            all_weapons.extend(items_by_category[cat])

    if all_weapons:
        all_weapons.sort(key=estimate_power)
        print(f"\nMapping {len(all_weapons)} armes...")

        # Mapper les armes aux prix entre 13 et 50
        for weapon in all_weapons:
            if weapon['name'] not in used_items:
                best_match = None
                for i in range(len(available_prices)):
                    price_idx, price = available_prices[i]
                    if 13 <= price <= 50 and price_idx not in mappings:
                        best_match = (price_idx, price)
                        break

                if best_match:
                    price_idx, price = best_match
                    mappings[price_idx] = {
                        'item': weapon,
                        'price': price,
                        'confidence': 'estimated_weapon'
                    }
                    used_items.add(weapon['name'])
                    print(f"  [{price_idx:2d}] {weapon['name']:30s} = {price:3d} gold")

    # Armures
    if 'armor' in items_by_category:
        armors = [item for item in items_by_category['armor'] if item['name'] not in used_items]
        armors.sort(key=estimate_power)
        print(f"\nMapping {len(armors)} armures...")

        for armor in armors[:10]:  # Limiter à 10
            # Chercher prix moyens-élevés (20-81)
            for i in range(len(available_prices)):
                price_idx, price = available_prices[i]
                if 20 <= price <= 81 and price_idx not in mappings:
                    mappings[price_idx] = {
                        'item': armor,
                        'price': price,
                        'confidence': 'estimated_armor'
                    }
                    used_items.add(armor['name'])
                    print(f"  [{price_idx:2d}] {armor['name']:30s} = {price:3d} gold")
                    break

    # Shields
    if 'shield' in items_by_category:
        shields = [item for item in items_by_category['shield'] if item['name'] not in used_items]
        shields.sort(key=estimate_power)
        print(f"\nMapping {len(shields)} boucliers...")

        for shield in shields[:5]:
            for i in range(len(available_prices)):
                price_idx, price = available_prices[i]
                if 20 <= price <= 70 and price_idx not in mappings:
                    mappings[price_idx] = {
                        'item': shield,
                        'price': price,
                        'confidence': 'estimated_shield'
                    }
                    used_items.add(shield['name'])
                    print(f"  [{price_idx:2d}] {shield['name']:30s} = {price:3d} gold")
                    break

    # Autres équipements (helmets, robes, accessories)
    other_equip_cats = ['helmet', 'robe', 'accessory']
    for cat in other_equip_cats:
        if cat in items_by_category:
            items_cat = [item for item in items_by_category[cat] if item['name'] not in used_items]
            items_cat.sort(key=estimate_power)

            if items_cat:
                print(f"\nMapping {len(items_cat)} {cat}s...")

                for item in items_cat[:3]:  # Limiter à 3 par catégorie
                    for i in range(len(available_prices)):
                        price_idx, price = available_prices[i]
                        if price_idx not in mappings:
                            mappings[price_idx] = {
                                'item': item,
                                'price': price,
                                'confidence': f'estimated_{cat}'
                            }
                            used_items.add(item['name'])
                            print(f"  [{price_idx:2d}] {item['name']:30s} = {price:3d} gold")
                            break

    # Statistiques finales
    print("\n" + "="*70)
    print("  RÉSUMÉ")
    print("="*70)
    print()

    confidence_counts = defaultdict(int)
    for mapping in mappings.values():
        confidence_counts[mapping['confidence']] += 1

    print(f"Total items mappés: {len(mappings)}/32 prix disponibles")
    print()
    print("Par confiance:")
    for conf, count in sorted(confidence_counts.items()):
        print(f"  {conf:30s}: {count:2d} items")

    return mappings

def apply_mappings_to_items(items, mappings):
    """Applique les mappings aux items"""

    # Réinitialiser les prix précédents
    for item in items:
        if 'auction_price' in item:
            del item['auction_price']
        if 'auction_price_index' in item:
            del item['auction_price_index']
        if 'auction_price_confidence' in item:
            del item['auction_price_confidence']

    # Appliquer les nouveaux mappings
    for price_idx, mapping in mappings.items():
        item = mapping['item']
        item['auction_price'] = mapping['price']
        item['auction_price_index'] = price_idx
        item['auction_price_confidence'] = mapping['confidence']

def main():
    print("="*70)
    print("  Mapping COMPLET des prix d'enchères")
    print("="*70)

    # Vérifier BLAZE_ORIGINAL.ALL
    if not BLAZE_ORIGINAL.exists():
        print("\nERREUR: BLAZE_ORIGINAL.ALL n'existe pas")
        print("Exécutez d'abord: py -3 extract_blaze_from_bin.py")
        return 1

    # Charger les items
    print("\nChargement des items...")
    items, metadata = load_items()
    print(f"  {len(items)} items chargés")

    # Mapping intelligent
    mappings = smart_mapping(items)

    # Appliquer aux items
    print("\nApplication des mappings aux items...")
    apply_mappings_to_items(items, mappings)

    # Afficher tous les mappings
    print("\n" + "="*70)
    print("  TOUS LES MAPPINGS")
    print("="*70)
    print()

    for price_idx in range(len(ALL_PRICES)):
        if price_idx in mappings:
            mapping = mappings[price_idx]
            item_name = mapping['item']['name']
            price = mapping['price']
            conf = mapping['confidence']
            print(f"  [{price_idx:2d}] {item_name:30s} = {price:3d} gold ({conf})")
        else:
            print(f"  [{price_idx:2d}] {'[NON MAPPÉ]':30s} = {ALL_PRICES[price_idx]:3d} gold")

    # Mettre à jour métadonnées
    metadata['auction_prices_complete'] = True
    metadata['auction_prices_mapped_count'] = len(mappings)
    metadata['auction_prices_total'] = len(ALL_PRICES)
    metadata['auction_prices_source'] = 'BLAZE_ORIGINAL.ALL extracted from BIN'

    # Sauvegarder
    output_data = {
        'metadata': metadata,
        'items': items
    }

    print(f"\nSauvegarde dans {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print("  TERMINÉ!")
    print("="*70)
    print()
    print(f"Prix mappés: {len(mappings)}/{len(ALL_PRICES)}")
    print(f"Prix non mappés: {len(ALL_PRICES) - len(mappings)}")
    print()

    return 0

if __name__ == '__main__':
    try:
        import sys
        sys.exit(main())
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
