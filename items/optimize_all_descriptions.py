"""
optimize_all_descriptions.py
Optimise CHAQUE item pour faire rentrer:
1. Description de base (raccourcie)
2. Effets spéciaux (reformulés)
3. Attributs

Usage: py -3 optimize_all_descriptions.py
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ALL_ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"

def abbreviate_text(text):
    """Applique des abréviations pour gagner de l'espace"""

    replacements = {
        # Stats communes
        'Attack': 'Atk',
        'attack': 'atk',
        'Defense': 'Def',
        'defense': 'def',
        'Magic Attack': 'MAtk',
        'magic attack': 'matk',
        'Magic Defense': 'MDef',
        'magic defense': 'mdef',
        'Critical': 'Crit',
        'critical': 'crit',
        'Elemental': 'Elem',
        'elemental': 'elem',
        'damage': 'dmg',
        'Damage': 'Dmg',
        'increases': 'boosts',
        'decreases': 'lowers',
        'ratio': 'rate',

        # Éléments
        'fire, water, wind, earth': 'fire/water/wind/earth',
        'fire,water,wind,earth': 'fire/water/wind/earth',

        # Formulations longues
        'that increase': 'boost',
        'that increases': 'boosts',
        'that decrease': 'lower',
        'that decreases': 'lowers',
        'the wearer\'s': '',
        'the wearer': 'wearer',
        'its wielder': 'wielder',

        # Mots communs
        'against': 'vs',
        'percentage': '%',
        'percent': '%',
        'equipped': 'worn',
        'extremely': 'very',
        'powerful': 'strong',
        'Powerful': 'Strong',
        'magical': 'magic',
        'Magical': 'Magic',
        'mysterious': 'mystic',
        'Mysterious': 'Mystic',

        # Articles et mots de liaison
        'Made of': 'Of',
        'made of': 'of',
        'Created of': 'Of',
        'created of': 'of',
        'Crafted from': 'Of',
        'A rather': 'An',
        'favored by': 'from',
        ' the ': ' ',
        ' a ': ' ',
        ' an ': ' ',
    }

    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Nettoyer les espaces multiples
    result = re.sub(r'\s+', ' ', result).strip()

    return result

def shorten_description(desc, max_length):
    """Raccourcit une description intelligemment"""

    if not desc or len(desc) <= max_length:
        return desc

    # Appliquer les abréviations d'abord
    shortened = abbreviate_text(desc)

    if len(shortened) <= max_length:
        return shortened

    # Supprimer les parenthèses et leur contenu
    shortened = re.sub(r'\s*\([^)]*\)\s*', ' ', shortened)
    shortened = re.sub(r'\s+', ' ', shortened).strip()

    if len(shortened) <= max_length:
        return shortened

    # Supprimer les phrases après un point si c'est trop long
    if '. ' in shortened:
        sentences = shortened.split('. ')
        # Garder seulement la première phrase si elle fait au moins 60% de la longueur cible
        if len(sentences[0]) >= max_length * 0.6:
            return sentences[0] + '.'

    # Couper au dernier mot complet avant la limite
    if len(shortened) > max_length:
        cutoff = max_length - 3
        shortened = shortened[:cutoff].rsplit(' ', 1)[0] + '...'

    return shortened

def format_attributes(attributes):
    """Formate les attributs de manière compacte"""

    if not attributes:
        return ""

    # Filtrer les attributs non nuls
    non_zero = {k: v for k, v in attributes.items() if v != 0}

    if not non_zero:
        return ""

    # Ordre de priorité pour l'affichage
    order = ['at', 'mat', 'def', 'mdef', 'str', 'int', 'wil', 'agl', 'con', 'pow', 'luk']

    parts = []
    for key in order:
        if key in non_zero:
            val = non_zero[key]
            # Format compact: AT+7 au lieu de at: 7
            parts.append(f"{key.upper()}+{val}")

    # Ajouter les attributs non listés
    for key, val in non_zero.items():
        if key not in order:
            parts.append(f"{key.upper()}+{val}")

    return ', '.join(parts)

def format_special_effects(effects):
    """Formate les effets spéciaux de manière compacte"""

    if not effects:
        return ""

    formatted = []

    for effect in effects:
        # Abréger l'effet
        short = abbreviate_text(effect)

        # Simplifications supplémentaires pour les effets
        short = short.replace('Immune to', 'Immune:')
        short = short.replace('Restores', 'Restore')
        short = short.replace('Protects', 'Protect')
        short = short.replace('Increases', 'Boost')
        short = short.replace('Decreases', 'Lower')

        formatted.append(short)

    return ' | '.join(formatted)

def build_optimized_description(item, max_chars):
    """Construit la description optimale pour un item"""

    # Extraire les composants
    base_desc = item.get('description', '').strip()
    special_effects = item.get('special_effects', [])
    attributes = item.get('attributes', {})

    # Formater chaque partie
    effects_str = format_special_effects(special_effects)
    attrs_str = format_attributes(attributes)

    # Calculer l'espace disponible pour la description de base
    # Format: "Base desc. Effects. Attrs"

    parts = []
    space_used = 0

    # Commencer par les effets et attributs pour savoir combien de place reste
    if effects_str:
        space_used += len(effects_str)
        parts.append(effects_str)

    if attrs_str:
        space_used += len(attrs_str)
        parts.append(attrs_str)

    # Ajouter des séparateurs
    if len(parts) > 0:
        space_used += len(' | ') * (len(parts) - 1)  # Séparateurs entre effets et attrs

    if base_desc and space_used > 0:
        space_used += 2  # Pour ". " entre description et le reste

    # Espace disponible pour la description de base
    space_for_desc = max_chars - space_used

    if base_desc and space_for_desc >= 10:
        short_desc = shorten_description(base_desc, space_for_desc)

        # Construire la description finale
        if parts:
            # Description + effets/attrs
            result = f"{short_desc}. {' | '.join(parts)}"
        else:
            result = short_desc
    else:
        # Pas assez de place pour la description, juste les effets/attrs
        result = ' | '.join(parts) if parts else base_desc

    # Vérifier la longueur finale
    if len(result) > max_chars:
        # Réduire encore plus agressivement
        result = result[:max_chars-3] + '...'

    return result.strip()

def optimize_all_items(items):
    """Optimise tous les items"""

    updated_count = 0
    improvements = []

    for item in items:
        max_chars = item.get('max_chars', 0)

        if max_chars == 0:
            continue

        old_desc = item.get('new_description', '')

        # Construire la nouvelle description optimisée
        new_desc = build_optimized_description(item, max_chars)

        # Mettre à jour si différent et valide
        if new_desc and new_desc != old_desc:
            old_len = len(old_desc)
            new_len = len(new_desc)

            item['new_description'] = new_desc
            item['current_chars'] = new_len

            updated_count += 1

            # Garder les exemples où on a beaucoup amélioré
            if new_len > old_len:
                improvements.append({
                    'name': item['name'],
                    'old': old_desc,
                    'new': new_desc,
                    'old_len': old_len,
                    'new_len': new_len,
                    'gain': new_len - old_len
                })

    return updated_count, improvements

def main():
    print("="*70)
    print("  OPTIMISATION COMPLÈTE DES DESCRIPTIONS")
    print("  (Description + Effets + Stats)")
    print("="*70)
    print()

    # Charger les items
    print(f"Chargement de {ALL_ITEMS_JSON.name}...")
    with open(ALL_ITEMS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data['items']
    print(f"  {len(items)} items chargés")
    print()

    # Optimiser tous les items
    print("Optimisation en cours...")
    updated_count, improvements = optimize_all_items(items)

    print(f"  {updated_count} items optimisés")
    print()

    # Trier par gain d'espace décroissant
    improvements.sort(key=lambda x: x['gain'], reverse=True)

    # Afficher les meilleures améliorations
    print("TOP 20 AMÉLIORATIONS (gain d'espace):")
    print("="*70)
    print()

    for i, imp in enumerate(improvements[:20], 1):
        print(f"{i:2d}. {imp['name']} (+{imp['gain']} chars: {imp['old_len']}->{imp['new_len']})")
        print(f"    Avant: {imp['old'][:60]}...")
        print(f"    Après: {imp['new'][:60]}...")
        print()

    # Statistiques finales
    print("="*70)
    print("STATISTIQUES FINALES")
    print("="*70)
    print()

    total_chars_used = sum(item.get('current_chars', 0) for item in items)
    total_chars_max = sum(item.get('max_chars', 0) for item in items)

    print(f"Caractères utilisés: {total_chars_used}/{total_chars_max}")
    print(f"Utilisation: {total_chars_used*100//total_chars_max}%")
    print()

    # Sauvegarder
    print(f"Sauvegarde dans {ALL_ITEMS_JSON.name}...")
    with open(ALL_ITEMS_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print()
    print("="*70)
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
