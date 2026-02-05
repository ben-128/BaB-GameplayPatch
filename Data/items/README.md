# Items Database - Blaze & Blade: Eternal Quest

## Vue d'ensemble

Module complet d'extraction et documentation des items de Blaze & Blade: Eternal Quest.

**Deux fichiers JSON complémentaires:**

1. **`faq_items_reference.json`** (181 KB) - **376 items** avec descriptions, effets, stats et attributs complets du FAQ GameFAQs
2. **`all_items_clean.json`** (240 KB) - **316 items** extraits de BLAZE.ALL avec offsets mémoire (fuzzy matching)

## 📊 Statistiques

### faq_items_reference.json (Référence complète)
- **Total**: 376 items
- **Descriptions**: 318 (84%)
- **Effets**: 69 items (18%)
- **Effets spéciaux**: 124 items (32%)
- **Attributs complets**: 248 items (66%)

### all_items_clean.json (Extraction BLAZE.ALL avec fuzzy matching)
- **Total**: 316 items (84% du FAQ)
- **Avec descriptions**: 310 (98%)
- **Avec attributs**: 223 (70%)
- **Avec données complètes**: 94 items (29%)

### Couverture
- Items trouvés: 316/376 (84%)
- Items manquants: 60 (16%)

## 📁 Fichiers

### Données
- **`faq_items_reference.json`** - Référence complète du FAQ (376 items)
- **`all_items_clean.json`** - Items extraits de BLAZE.ALL (291 items)
- **`Blaze objets.txt`** - FAQ GameFAQs source (194 KB)

### Scripts
- **`build_complete_reference.py`** - Parse le FAQ complet (descriptions + effets + stats + special effects)
- **`parse_attributes.py`** - Parse les attributs (IX. Equipment Attribute) et les ajoute à la référence
- **`extract_with_fuzzy_matching.py`** - Extrait items de BLAZE.ALL avec fuzzy matching (Levenshtein, variantes)

### Documentation
- **`README.md`** - Ce fichier
- **`EXTRACTION_SUMMARY.md`** - Rapport technique détaillé
- **`INDEX.md`** - Index des fichiers

## 🗂️ Structure des données

### faq_items_reference.json

```json
{
  "name": "Elixir",
  "category": "Items",
  "location": "Legendary drops",
  "description": "Legendary medicine. (Completely restores MP and HP)",
  "effects": [
    "Restore HP & MP to full to a member"
  ],
  "special_effects": [],
  "stats": {
    "hp_restore_min": 0,
    "hp_restore_max": 999,
    "mp_restore_min": 0,
    "mp_restore_max": 999
  }
}
```

### all_items_clean.json

```json
{
  "name": "Elixir",
  "offset": "0x00AAC410",
  "offset_decimal": 11223056,
  "category": "Consumables",
  "description": "Legendary medicine.(Completely restores MP and HP)",
  "stats": {
    "0x12": 37119
  },
  "occurrences_count": 1,
  "all_offsets": ["0x00AAC410"]
}
```

## 📋 Catégories d'items

### Armes (faq_items_reference.json)
- **Swords (warrior)** - 23 items
- **Knives (rogue)** - 15 items
- **Bows (hunter)** - 14 items
- **Rapiers (elf)** - 16 items
- **Axes (dwarf)** - 20 items
- **Rods (fairy)** - 16 items
- **Priest's Wand/Hammer** - 17 items
- **Sorcerer's Wand** - 16 items

### Équipement (faq_items_reference.json)
- **Armors (warrior & dwarf)** - 15 items
- **Light Armors** - 14 items
- **Robes** - 14 items
- **Shields** - 11 items
- **Clothings** - 107 items (helmets, boots, gloves, rings, etc.)

### Consommables (faq_items_reference.json)
- **Items** - 47 items (potions, elixirs, herbs)
- **Jewels** - 18 items (magic orbs, gems)
- **Ashes** - 8 items (stat increasers)

## 🎯 Exemples d'utilisation

### Charger les données

```python
import json

# Référence FAQ complète
with open('items/faq_items_reference.json', 'r', encoding='utf-8') as f:
    faq_data = json.load(f)
    faq_items = faq_data['items']

# Items extraits de BLAZE.ALL
with open('items/all_items_clean.json', 'r', encoding='utf-8') as f:
    blaze_data = json.load(f)
    blaze_items = blaze_data['items']
```

### Rechercher un item

```python
# Trouver un item dans le FAQ
elixir_faq = next(i for i in faq_items if i['name'] == 'Elixir')
print(f"Description: {elixir_faq['description']}")
print(f"Effets: {elixir_faq['effects']}")

# Trouver son offset dans BLAZE.ALL
elixir_blaze = next(i for i in blaze_items if i['name'] == 'Elixir')
print(f"Offset: {elixir_blaze['offset']}")
```

### Filtrer par catégorie

```python
# Toutes les épées du FAQ
swords = [i for i in faq_items if i['category'] == 'Swords (warrior)']
print(f"Total swords: {len(swords)}")

# Items avec stats numériques
items_with_stats = [i for i in faq_items if i.get('stats')]
print(f"Items with numerical stats: {len(items_with_stats)}")
```

### Analyser les effets

```python
# Items qui restaurent HP
hp_restore_items = [
    i for i in faq_items
    if i.get('stats') and 'hp_restore_min' in i['stats']
]

for item in hp_restore_items:
    hp_min = item['stats']['hp_restore_min']
    hp_max = item['stats'].get('hp_restore_max', hp_min)
    print(f"{item['name']}: Restores {hp_min}-{hp_max} HP")
```

### Merger les données

```python
# Créer un item complet avec FAQ + offset BLAZE.ALL
def get_complete_item(name):
    faq_item = next((i for i in faq_items if i['name'] == name), None)
    blaze_item = next((i for i in blaze_items if i['name'] == name), None)

    if faq_item and blaze_item:
        return {
            **faq_item,
            'offset': blaze_item['offset'],
            'binary_description': blaze_item['description']
        }

    return faq_item or blaze_item

# Exemple
bloodsword = get_complete_item('Bloodsword')
print(f"Bloodsword @ {bloodsword['offset']}")
print(f"Special: {bloodsword['special_effects'][0]}")
```

## 🔍 Items spéciaux

### Items légendaires (marqués * dans le FAQ)
- Answerer (sword)
- Mistortain (sword)
- Fenris (sword)
- Calvin's Blade (sword)
- Hammer of Thor (hammer)
- Death Sickle (knife)
- Fabnihl (knife)
- Bolt of Larie (bow)
- Perseus Bow
- Charmed Wand
- Baphomet (wand)
- Angel Rod
- Alchemist's Rod
- Et plus...

### Items avec effets permanents
- **Red Ash** - STR +1~6 (permanent)
- **Blue Ash** - INT +1~6 (permanent)
- **White Ash** - WIL +1~6 (permanent)
- **Gray Ash** - AGL +1~6 (permanent)
- **Green Ash** - CON +1~6 (permanent)
- **Black Ash** - POW +1~6 (permanent)
- **Blood Extract** - Max HP +1~6 (permanent)
- **Spirit Extract** - Max MP +1~6 (permanent)

### Items avec réduction de coût MP
- **Sol Crown** - MP cost -50%
- **Moon Crown** - MP cost -25%
- **Devil's Horn** - MP cost -10%

## ❓ Items manquants

60 items du FAQ (16%) n'ont pas été trouvés dans BLAZE.ALL:

**Raisons possibles:**
- Noms légèrement différents (variantes, typos)
- Stockés dans l'exécutable SLES_008.45
- Items de développement non utilisés dans la version finale
- Erreurs dans le FAQ

**Exemples d'items manquants:**
- Dominion Dagger, Pavas Axe, Gray Arc, Seraphim Shield (marqués comme "rumored" dans le FAQ)
- Anti-magic Armor, Fata Morgana Armor
- Chainmail Shirt, Breast Plate
- Plusieurs variantes d'équipements

## 🛠️ Extraction workflow

### Pour re-générer la référence FAQ complète:
```bash
cd items
py -3 build_complete_reference.py   # Parse descriptions, effets, special effects
py -3 parse_attributes.py            # Ajoute les attributs (Str, Int, Wil, etc.)
```

### Pour re-extraire de BLAZE.ALL:
```bash
cd items
py -3 extract_with_fuzzy_matching.py  # Extraction avec fuzzy matching
```

## 📝 Notes techniques

### Format des entrées (BLAZE.ALL)
- Taille: 128 bytes (0x80) par item
- Structure:
  - +0x00: Nom (null-terminated, max 32 bytes)
  - +0x10-0x3F: Stats (uint16 values)
  - +0x40: Séparateur (0x0C)
  - +0x41: Description complète

### Stats binaires (uint16)
Les valeurs aux offsets 0x10, 0x12, 0x30, etc. sont des uint16 little-endian dont la signification exacte nécessite des tests in-game.

### Catégories FAQ vs catégories extraites
- Le FAQ utilise les catégories originales du jeu (par classe)
- L'extraction utilise des catégories génériques (Weapons, Armor, etc.)

## 📚 Crédits

- **Référence FAQ**: Sandy Saputra / holypriest @ GameFAQs
- **Version FAQ**: 2.4 (April 16, 2003)
- **Extraction**: Claude Code + scripts Python
- **Jeu**: Blaze & Blade: Eternal Quest © 1998 T&E Soft

## 🔗 Ressources

- FAQ original: GameFAQs (inclus dans `Blaze objets.txt`)
- Project GitHub: (votre repository)
- Documentation complète: `../README.md`

---

*Module items/ - Extraction complète réalisée le 2026-02-04*
