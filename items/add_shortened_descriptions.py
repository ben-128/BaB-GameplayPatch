"""
add_shortened_descriptions.py
Ajoute les descriptions de base (raccourcies ~50%) aux items qui ont de la place

Usage: py -3 add_shortened_descriptions.py
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"

def shorten_description(desc, target_length):
    """Raccourcit une description en gardant l'essentiel"""

    if not desc or len(desc) <= target_length:
        return desc

    # Stratégies de raccourcissement
    shortened = desc

    # 1. Supprimer les phrases redondantes
    shortened = re.sub(r'\s*\(.*?\)\s*', ' ', shortened)  # Enlever les parenthèses

    # 2. Simplifier les formulations longues
    replacements = {
        'increases the wearer\'s': '+',
        'increase the wearer\'s': '+',
        'that increase': 'boost',
        'that increases': 'boosts',
        'Made of': 'Of',
        'made of': 'of',
        'Created of': 'Of',
        'created of': 'of',
        'A rather': 'An',
        'Powerfully protective.': '',
        'Magically': '',
        'is protected by': 'has',
        'brings the wearer': 'brings',
        'its wielder': 'wielder',
        'favored by': 'from',
        ' the ': ' ',
    }

    for old, new in replacements.items():
        shortened = shortened.replace(old, new)

    # 3. Nettoyer les espaces multiples
    shortened = re.sub(r'\s+', ' ', shortened).strip()

    # 4. Si encore trop long, couper intelligemment
    if len(shortened) > target_length:
        # Chercher un point ou une virgule proche de la limite
        cutoff = target_length - 3  # Laisser place pour "..."

        # Chercher le dernier espace, point ou virgule avant cutoff
        for sep in ['. ', ', ', ' ']:
            pos = shortened[:cutoff].rfind(sep)
            if pos > target_length * 0.6:  # Au moins 60% de la longueur cible
                return shortened[:pos].strip() + '...'

        # Sinon, couper au mot
        shortened = shortened[:cutoff].rsplit(' ', 1)[0] + '...'

    return shortened

def combine_description(attributes, base_desc, available_space):
    """Combine les attributs avec la description de base raccourcie"""

    # Garder les attributs (ex: "MAT+2")
    attr_part = attributes

    # Calculer l'espace restant pour la description
    # Format: "MAT+2. Description."
    separator = ". " if attr_part and base_desc else ""
    space_for_desc = available_space - len(attr_part) - len(separator)

    if space_for_desc < 10:  # Pas assez de place pour une description utile
        return attr_part

    # Raccourcir la description de base
    short_desc = shorten_description(base_desc, space_for_desc)

    if attr_part and short_desc:
        return f"{attr_part}. {short_desc}"
    elif attr_part:
        return attr_part
    else:
        return short_desc

def update_items_with_descriptions(items):
    """Met à jour les items avec descriptions raccourcies"""

    updated_count = 0

    for item in items:
        max_chars = item.get('max_chars', 0)
        current_chars = item.get('current_chars', 0)
        new_desc = item.get('new_description', '')
        base_desc = item.get('description', '')

        # Vérifier s'il y a de la place et si la description de base n'est pas déjà là
        if max_chars > current_chars and base_desc and base_desc not in new_desc:
            available = max_chars - current_chars

            # Extraire les attributs actuels (ex: "MAT+2")
            current_attrs = new_desc.strip()

            # Combiner avec description raccourcie
            new_combined = combine_description(current_attrs, base_desc, max_chars)

            # Mettre à jour si c'est différent et que ça rentre
            if new_combined != new_desc and len(new_combined) <= max_chars:
                item['new_description'] = new_combined
                item['current_chars'] = len(new_combined)
                updated_count += 1

    return updated_count

def main():
    print("="*70)
    print("  AJOUT DES DESCRIPTIONS DE BASE RACCOURCIES")
    print("="*70)
    print()

    # Charger les items
    print(f"Chargement de {ALL_ITEMS_JSON.name}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data['items']
    print(f"  {len(items)} items chargés")
    print()

    # Analyser combien ont de la place
    items_with_space = sum(1 for item in items
                          if item.get('max_chars', 0) > item.get('current_chars', 0)
                          and item.get('description', '')
                          and item.get('description', '') not in item.get('new_description', ''))

    print(f"Items avec espace disponible: {items_with_space}")
    print()

    # Mettre à jour
    print("Mise à jour des descriptions...")
    updated = update_items_with_descriptions(items)
    print(f"  {updated} items mis à jour")
    print()

    # Afficher quelques exemples
    print("Exemples de mises à jour:")
    print("-"*70)

    count = 0
    for item in items:
        if item.get('description', '') and len(item.get('new_description', '')) > 10:
            # Vérifier si ça a été mis à jour (contient maintenant du texte au-delà des attributs)
            new_desc = item.get('new_description', '')
            if '. ' in new_desc or len(new_desc) > 20:
                count += 1
                if count <= 10:
                    print(f"\n{item['name']}:")
                    print(f"  Avant: {item.get('description', '')[:50]}...")
                    print(f"  Après: {new_desc}")
                    print(f"  Chars: {item.get('current_chars')}/{item.get('max_chars')}")

    # Sauvegarder
    print()
    print("="*70)
    print(f"Sauvegarde dans {ALL_ITEMS_JSON.name}...")
    with open(ALL_ITEMS_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print()
    print("="*70)
    print("  TERMINÉ!")
    print("="*70)
    print()
    print(f"Items mis à jour: {updated}")
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
