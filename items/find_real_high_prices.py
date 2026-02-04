"""
find_real_high_prices.py
Cherche les VRAIS prix dans toute la structure des items
Les prix doivent être beaucoup plus élevés (centaines de gold)

Usage: py -3 find_real_high_prices.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ORIGINAL = SCRIPT_DIR / "BLAZE_ORIGINAL.ALL"
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"

ITEM_ENTRY_SIZE = 128

def scan_item_for_prices(item_data, item_name):
    """Scanne toute la structure d'un item pour trouver des valeurs qui pourraient être des prix"""

    candidates = []

    # Chercher tous les words (16-bit) dans l'item
    for offset in range(0, len(item_data) - 1, 2):
        # Lire comme 16-bit little-endian
        value = struct.unpack_from('<H', item_data, offset)[0]

        # Filtrer les valeurs qui pourraient être des prix (entre 10 et 9999)
        if 10 <= value <= 9999:
            # Vérifier que ce n'est pas juste des caractères ASCII
            byte1 = item_data[offset]
            byte2 = item_data[offset + 1]

            # Éviter les valeurs qui sont clairement du texte
            if byte1 < 32 or byte1 > 126 or byte2 < 32 or byte2 > 126:
                candidates.append((offset, value))

    return candidates

def analyze_all_items(data, items):
    """Analyse tous les items pour trouver les patterns de prix"""

    print("="*70)
    print("  ANALYSE DE TOUS LES ITEMS POUR TROUVER LES VRAIS PRIX")
    print("="*70)
    print()

    all_candidates = []

    for item in items[:50]:  # Analyser les 50 premiers items
        offset = int(item['offset'], 16)
        item_data = data[offset:offset + ITEM_ENTRY_SIZE]

        candidates = scan_item_for_prices(item_data, item['name'])

        if candidates:
            # Garder seulement les plus grandes valeurs
            max_value = max(c[1] for c in candidates)
            if max_value >= 50:
                all_candidates.append({
                    'name': item['name'],
                    'max_value': max_value,
                    'candidates': candidates
                })

    # Trier par valeur max décroissante
    all_candidates.sort(key=lambda x: x['max_value'], reverse=True)

    print(f"Items analysés: 50")
    print(f"Items avec valeurs >= 50: {len(all_candidates)}")
    print()

    # Afficher les top 20
    print("TOP 20 ITEMS PAR VALEUR MAXIMALE TROUVÉE:")
    print()

    for i, item_data in enumerate(all_candidates[:20], 1):
        print(f"{i:2d}. {item_data['name']:30s} - max value: {item_data['max_value']:5d}")

        # Afficher les candidats pour cet item
        print(f"    Valeurs trouvées:")
        for offset, value in sorted(item_data['candidates'], key=lambda x: x[1], reverse=True)[:5]:
            print(f"      +0x{offset:02X}: {value:5d}")
        print()

    return all_candidates

def find_common_price_offset(data, items):
    """Essaie de trouver l'offset commun pour le prix en analysant les patterns"""

    print("="*70)
    print("  RECHERCHE DE L'OFFSET COMMUN DU PRIX")
    print("="*70)
    print()

    # Analyser tous les items et collecter les offsets
    from collections import Counter
    offset_values = {}  # offset -> [values]

    for item in items[:100]:
        offset = int(item['offset'], 16)
        item_data = data[offset:offset + ITEM_ENTRY_SIZE]

        for off in range(0x10, 0x40, 2):  # Scanner les offsets 0x10 à 0x3F
            if off + 2 <= len(item_data):
                value = struct.unpack_from('<H', item_data, off)[0]

                if value > 0 and value < 10000:
                    if off not in offset_values:
                        offset_values[off] = []
                    offset_values[off].append(value)

    # Trouver l'offset avec les valeurs les plus variées et raisonnables
    print("Analyse des offsets (statistiques):")
    print()

    candidates = []

    for offset in sorted(offset_values.keys()):
        values = offset_values[offset]

        if len(values) >= 50:
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            unique_vals = len(set(values))

            # Critères pour un bon offset de prix:
            # - Valeurs variées (unique_vals > 10)
            # - Maximum raisonnable (< 5000)
            # - Minimum pas trop bas (> 5)

            if unique_vals > 10 and max_val < 5000 and min_val > 5:
                candidates.append({
                    'offset': offset,
                    'min': min_val,
                    'max': max_val,
                    'avg': avg_val,
                    'unique': unique_vals
                })

                print(f"  +0x{offset:02X}: min={min_val:4d} max={max_val:4d} avg={avg_val:6.1f} unique={unique_vals:3d}")

    print()

    if candidates:
        # Trier par nombre de valeurs uniques (plus de variété = plus probable)
        candidates.sort(key=lambda x: x['unique'], reverse=True)

        best = candidates[0]
        print(f"[OK] Meilleur candidat: +0x{best['offset']:02X}")
        print(f"     Range: {best['min']}-{best['max']} gold")
        print(f"     Unique values: {best['unique']}")

        return best['offset']
    else:
        print("[X] Aucun offset candidat trouvé")
        return None

def extract_all_prices_at_offset(data, items, price_offset):
    """Extrait les prix de tous les items à l'offset donné"""

    print()
    print("="*70)
    print(f"  EXTRACTION DES PRIX À L'OFFSET +0x{price_offset:02X}")
    print("="*70)
    print()

    items_with_prices = []

    for item in items:
        offset = int(item['offset'], 16)
        item_data = data[offset:offset + ITEM_ENTRY_SIZE]

        if price_offset + 2 <= len(item_data):
            price = struct.unpack_from('<H', item_data, price_offset)[0]

            if 10 <= price <= 9999:
                items_with_prices.append({
                    'name': item['name'],
                    'price': price,
                    'category': item.get('category', 'Unknown'),
                    'offset': item['offset']
                })

    # Trier par prix décroissant
    items_with_prices.sort(key=lambda x: x['price'], reverse=True)

    print(f"Items avec prix valide: {len(items_with_prices)}/316")
    print()

    print("TOP 10 ITEMS LES PLUS CHERS:")
    for i, item in enumerate(items_with_prices[:10], 1):
        print(f"  {i:2d}. {item['price']:5d} gold - {item['name']:30s} ({item['category']})")

    print()
    print("TOP 10 ITEMS LES MOINS CHERS:")
    items_with_prices.sort(key=lambda x: x['price'])
    for i, item in enumerate(items_with_prices[:10], 1):
        print(f"  {i:2d}. {item['price']:5d} gold - {item['name']:30s} ({item['category']})")

    # Re-trier par prix décroissant pour le retour
    items_with_prices.sort(key=lambda x: x['price'], reverse=True)

    return items_with_prices

def main():
    print("="*70)
    print("  RECHERCHE DES VRAIS PRIX (CENTAINES DE GOLD)")
    print("="*70)
    print()

    # Charger BLAZE.ALL
    if not BLAZE_ORIGINAL.exists():
        print("ERREUR: BLAZE_ORIGINAL.ALL n'existe pas")
        return 1

    data = BLAZE_ORIGINAL.read_bytes()
    print(f"BLAZE.ALL chargé: {len(data):,} bytes")

    # Charger items
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        items_data = json.load(f)

    items = items_data['items']
    print(f"Items chargés: {len(items)}")
    print()

    # Analyser quelques items pour voir les patterns
    analyze_all_items(data, items)

    # Trouver l'offset commun du prix
    price_offset = find_common_price_offset(data, items)

    if price_offset is not None:
        # Extraire tous les prix
        all_prices = extract_all_prices_at_offset(data, items, price_offset)

        # Sauvegarder
        output = {
            'metadata': {
                'price_offset': price_offset,
                'price_offset_hex': f'0x{price_offset:02X}',
                'items_with_prices': len(all_prices),
                'method': 'direct_value_in_item_structure'
            },
            'items': all_prices
        }

        output_file = SCRIPT_DIR / "real_high_prices.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print()
        print(f"Sauvegardé dans: {output_file}")
        print()

    print("="*70)
    print("  TERMINÉ")
    print("="*70)

    return 0

if __name__ == '__main__':
    try:
        import sys
        sys.exit(main())
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
