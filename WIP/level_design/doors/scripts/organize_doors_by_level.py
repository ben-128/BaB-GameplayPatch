"""
organize_doors_by_level.py
Create organized list of doors by level/area with conditions

Usage: py -3 organize_doors_by_level.py
"""

from pathlib import Path
import json
import re

SCRIPT_DIR = Path(__file__).parent.parent
OUTPUT_FILE = SCRIPT_DIR / "data" / "doors_by_level.json"
ANALYSIS_FILE = SCRIPT_DIR / "data" / "door_analysis.json"

# Define game levels/zones structure
GAME_ZONES = {
    "cavern_of_death": {
        "name": "Caverne de la Mort",
        "areas": ["floor_1", "floor_2", "floor_3"]
    },
    "forest_of_despair": {
        "name": "Forêt du Désespoir",
        "areas": ["area_1", "area_2", "area_3"]
    },
    "castle_of_vamp": {
        "name": "Château du Vampire",
        "areas": ["floor_1_area_1", "floor_1_area_2", "floor_2_area_1",
                  "floor_3_area_1", "floor_3_area_2", "floor_3_area_3",
                  "floor_4_area_1", "floor_5_area_1", "floor_5_area_2",
                  "floor_5_area_3", "floor_5_area_4"]
    },
    "mountain_valley": {
        "name": "Vallée de la Montagne",
        "areas": ["area_1", "area_2"]
    },
    "ancient_ruins": {
        "name": "Ruines Anciennes",
        "areas": ["area_1", "area_2", "area_3"]
    },
    "abandoned_mine": {
        "name": "Mine Abandonnée",
        "areas": ["1st_underlevel", "2nd_underlevel", "3rd_underlevel"]
    },
    "tower": {
        "name": "Tour",
        "areas": ["floor_1", "floor_2", "floor_3", "floor_4"]
    }
}

def extract_key_info(key_data):
    """Extract key name and what it opens"""
    keys = []

    for key in key_data:
        key_entry = {
            'name': None,
            'opens': None,
            'description': key.get('description', ''),
            'context': key.get('full_context', '')
        }

        # Extract key name from context
        name = key.get('name', '').strip()
        if name:
            # Clean up the name
            name = name.replace('*', '').replace('You have the', '').replace('You get the', '')
            name = name.replace('You hold the', '').replace("You've found the", '')
            name = name.strip()
            key_entry['name'] = name

        # Try to extract what it opens
        context = key_entry['context'].lower()
        if 'treasure chest' in context:
            key_entry['opens'] = 'Coffre au trésor'
        elif 'door' in context or 'lock' in context:
            key_entry['opens'] = 'Porte'

            # Try to find specific door description
            if 'cellar' in context:
                key_entry['opens'] = 'Porte de la cave'
            elif 'clearing' in context:
                key_entry['opens'] = 'Porte de la clairière'
            elif 'cell' in context:
                key_entry['opens'] = 'Porte de cellule'
            elif 'dragon' in context:
                if 'black dragon' in context:
                    key_entry['opens'] = 'Porte du Dragon Noir'
                elif 'blue dragon' in context:
                    key_entry['opens'] = 'Porte du Dragon Bleu'
                elif 'red dragon' in context:
                    key_entry['opens'] = 'Porte du Dragon Rouge'
                else:
                    key_entry['opens'] = 'Porte du Dragon'

        if key_entry['name']:
            keys.append(key_entry)

    return keys

def categorize_doors_by_type(door_types_data):
    """Categorize all doors by their type"""
    doors_by_type = {
        'magic_locked': [],
        'demon_engraved': [],
        'ghost_engraved': [],
        'key_locked': [],
        'generic': []
    }

    for dtype, doors in door_types_data.items():
        for door in doors:
            context = door.get('context', '')
            doors_by_type[dtype].append({
                'offset': door.get('offset'),
                'description': context[:100]
            })

    return doors_by_type

def extract_door_requirements(door_types_data, keys_data):
    """Extract what's needed to open each type of door"""
    requirements = {
        'Magical Key': {
            'type': 'Porte verrouillée par magie',
            'item_required': 'Magical Key',
            'description': 'Opens doors locked by magic',
            'count': len(door_types_data.get('magic_locked', []))
        },
        'Demon Amulet': {
            'type': 'Porte avec gravure démoniaque',
            'item_required': 'Demon Amulet',
            'description': 'Opens doors with demon engravings',
            'count': len(door_types_data.get('demon_engraved', []))
        },
        'Ghost Amulet': {
            'type': 'Porte avec gravure fantôme',
            'item_required': 'Ghost Amulet',
            'description': 'Opens doors with ghost engravings',
            'count': len(door_types_data.get('ghost_engraved', []))
        },
        'Various Keys': {
            'type': 'Portes nécessitant des clés spécifiques',
            'item_required': 'Specific keys (voir liste des clés)',
            'description': 'Various doors requiring specific keys',
            'count': len(door_types_data.get('key_locked', []))
        }
    }

    return requirements

def analyze_portal_destinations(portals_data):
    """Analyze portal destinations"""
    destinations = {}

    for portal in portals_data:
        dest = portal.get('destination')
        if dest:
            if dest not in destinations:
                destinations[dest] = []
            destinations[dest].append(portal.get('offset'))

    return destinations

def main():
    print("=" * 70)
    print("  ORGANISATION DES PORTES PAR NIVEAU")
    print("=" * 70)

    # Load analysis data
    print(f"\nChargement de {ANALYSIS_FILE.name}...")
    with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    # Extract information
    print("\nExtraction des informations...")

    keys = extract_key_info(analysis['keys'])
    print(f"  Clés trouvées: {len(keys)}")

    doors_by_type = categorize_doors_by_type(analysis['door_types'])
    total_doors = sum(len(v) for v in doors_by_type.values())
    print(f"  Portes totales: {total_doors}")

    requirements = extract_door_requirements(analysis['door_types'], analysis['keys'])
    print(f"  Types de portes: {len(requirements)}")

    portal_destinations = analyze_portal_destinations(analysis['portals'])
    print(f"  Destinations de portails: {len(portal_destinations)}")

    # Organize by level
    organized = {
        'zones': GAME_ZONES,
        'door_types': {
            'magic_locked': {
                'name': 'Portes verrouillées par magie',
                'count': len(doors_by_type['magic_locked']),
                'required_item': 'Magical Key',
                'description': 'Opens doors locked by magic'
            },
            'demon_engraved': {
                'name': 'Portes avec gravure démoniaque',
                'count': len(doors_by_type['demon_engraved']),
                'required_item': 'Demon Amulet',
                'description': 'Opens doors with demon engravings'
            },
            'ghost_engraved': {
                'name': 'Portes avec gravure fantôme',
                'count': len(doors_by_type['ghost_engraved']),
                'required_item': 'Ghost Amulet',
                'description': 'Opens doors with ghost engravings'
            },
            'key_locked': {
                'name': 'Portes nécessitant des clés',
                'count': len(doors_by_type['key_locked']),
                'required_item': 'Specific keys (voir liste ci-dessous)',
                'description': 'Various doors requiring specific keys'
            },
            'generic': {
                'name': 'Portes génériques',
                'count': len(doors_by_type['generic']),
                'required_item': 'None (unlocked)',
                'description': 'Standard unlocked doors'
            }
        },
        'keys': keys,
        'portals': {
            'total': len(analysis['portals']),
            'destinations': portal_destinations,
            'gate_crystals': len(analysis['gates']['gate_crystals'])
        },
        'door_structures': {
            'total': len(analysis.get('door_structures', [])),
            'sample_positions': analysis.get('door_structures', [])[:10]
        }
    }

    # Save organized data
    print(f"\nSauvegarde dans {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(organized, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 70)
    print("RÉSUMÉ PAR TYPE DE PORTE")
    print("=" * 70)

    for dtype, info in organized['door_types'].items():
        print(f"\n{info['name']}:")
        print(f"  Quantité: {info['count']}")
        print(f"  Objet requis: {info['required_item']}")
        print(f"  Description: {info['description']}")

    print("\n" + "=" * 70)
    print("LISTE DES CLÉS")
    print("=" * 70)

    for i, key in enumerate(keys, 1):
        print(f"\n{i}. {key['name']}")
        if key['opens']:
            print(f"   Ouvre: {key['opens']}")

    print("\n" + "=" * 70)
    print("PORTAILS")
    print("=" * 70)
    print(f"Total portails: {organized['portals']['total']}")
    print(f"Gate Crystals: {organized['portals']['gate_crystals']}")
    print("\nDestinations connues:")
    for dest, offsets in portal_destinations.items():
        print(f"  {dest}: {len(offsets)} portail(s)")

    print("\n" + "=" * 70)
    print(f"\nFichier créé: {OUTPUT_FILE.name}")
    print("=" * 70)

if __name__ == '__main__':
    main()
