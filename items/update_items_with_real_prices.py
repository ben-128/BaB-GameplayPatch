"""
update_items_with_real_prices.py
Met à jour all_items_clean.json avec les VRAIS prix extraits

Usage: py -3 update_items_with_real_prices.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REAL_PRICES_JSON = SCRIPT_DIR / "items_with_real_prices.json"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"

def main():
    print("="*70)
    print("  MISE À JOUR AVEC LES VRAIS PRIX")
    print("="*70)
    print()

    # Charger les vrais prix
    print(f"Chargement de {REAL_PRICES_JSON.name}...")
    with open(REAL_PRICES_JSON, 'r', encoding='utf-8') as f:
        real_prices_data = json.load(f)

    real_prices = real_prices_data['items']
    metadata = real_prices_data['metadata']

    print(f"  {len(real_prices)} items avec prix réels")
    print(f"  ID offset: {metadata['id_offset_hex']}")
    print(f"  Table de prix: {metadata['price_table_offset_hex']}")

    # Créer un index par nom
    price_by_name = {item['name']: item for item in real_prices}

    # Charger all_items_clean.json
    print(f"\nChargement de {ALL_ITEMS_JSON.name}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        all_items_data = json.load(f)

    items = all_items_data['items']
    print(f"  {len(items)} items totaux")

    # Nettoyer les anciens prix (estimés/devinés)
    print("\nNettoyage des anciens prix...")
    for item in items:
        # Supprimer tous les champs liés aux prix
        for key in list(item.keys()):
            if 'auction_price' in key or 'price' in key.lower():
                del item[key]

    # Appliquer les vrais prix
    print("Application des vrais prix...")
    count = 0

    for item in items:
        if item['name'] in price_by_name:
            price_data = price_by_name[item['name']]

            item['auction_price'] = price_data['price']
            item['auction_price_id'] = price_data['id']
            item['auction_price_source'] = 'extracted_from_item_structure'

            count += 1

    print(f"  {count} items mis à jour avec leur prix")

    # Mettre à jour les métadonnées
    all_items_data['metadata']['auction_prices_real'] = True
    all_items_data['metadata']['auction_prices_count'] = count
    all_items_data['metadata']['auction_prices_id_offset'] = metadata['id_offset_hex']
    all_items_data['metadata']['auction_prices_table_offset'] = metadata['price_table_offset_hex']
    all_items_data['metadata']['auction_prices_method'] = 'Item structure at +0x30 points to price table'
    all_items_data['metadata']['auction_prices_note'] = 'Real prices extracted from item structure, not estimated'

    # Supprimer les anciennes clés de métadonnées estimées
    for key in list(all_items_data['metadata'].keys()):
        if 'estimated' in key or 'unmapped' in key or 'complete' in key:
            if 'auction' in key:
                del all_items_data['metadata'][key]

    # Sauvegarder
    print(f"\nSauvegarde dans {ALL_ITEMS_JSON}...")
    with open(ALL_ITEMS_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_items_data, f, indent=2, ensure_ascii=False)

    # Statistiques finales
    print("\n" + "="*70)
    print("  STATISTIQUES FINALES")
    print("="*70)
    print()
    print(f"Items avec prix: {count}/{len(items)} ({count*100//len(items)}%)")
    print(f"Items sans prix: {len(items) - count}")
    print()

    # Afficher quelques exemples
    print("Exemples (10 items les moins chers):")
    items_with_prices = [i for i in items if 'auction_price' in i]
    items_with_prices.sort(key=lambda x: x['auction_price'])

    for item in items_with_prices[:10]:
        print(f"  [ID {item['auction_price_id']:2d}] {item['name']:30s} = {item['auction_price']:3d} gold")

    print("\n" + "="*70)
    print("  TERMINÉ!")
    print("="*70)
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
