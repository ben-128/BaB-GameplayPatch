# Blaze & Blade - Base de données des sorts

## 📁 Structure du dossier

Ce dossier contient **90 fichiers JSON** extraits du fichier BLAZE.ALL, chacun représentant un sort du jeu avec ses statistiques complètes.

## 📊 Fichiers principaux

- **INDEX.json** : Vue d'ensemble de tous les sorts avec statistiques résumées
- **[Nom_du_sort].json** : Fichier individuel pour chaque sort

## 🔍 Structure d'un fichier de sort

Chaque fichier JSON contient :

```json
{
  "name": "Nom du sort",
  "type": "Type (fire/ice/lightning/healing/poison/status/buff/unknown)",
  "offset": "Position hexadécimale dans BLAZE.ALL",
  "stats": {
    "mp_cost": "Coût en points de magie (MP)",
    "power_damage": "Puissance/Dégâts du sort",
    "hit_chance": "Chance de toucher en %",
    "effect_type": "Type d'effet",
    "level_requirement": "Niveau requis",
    "casting_time": "Temps d'incantation",
    "range": "Portée du sort",
    "area_of_effect": "Zone d'effet"
  },
  "raw_data": {
    "hex_offset": "Offset hexadécimal",
    "structure_size": "Taille de la structure en bytes",
    "raw_values": [...]
  }
}
```

## 📈 Statistiques globales

- **Total** : 90 sorts uniques
- **Types identifiés** :
  - Fire (Feu) : 2 sorts
  - Ice (Glace) : 3 sorts
  - Lightning (Foudre) : 2 sorts
  - Healing (Soin) : 3 sorts
  - Poison : 2 sorts
  - Status (Altération d'état) : 4 sorts
  - Buff (Amélioration) : 4 sorts
  - Unknown (Non catégorisé) : 70 sorts

## 🎯 Sorts les plus puissants

| Sort | Puissance | Coût MP | Type |
|------|-----------|---------|------|
| Call | 100 | 110 | unknown |
| Turn | 100 | 28 | unknown |
| Meteor | 96 | 26 | unknown |
| Resurrection | 86 | 49 | unknown |
| Fusion | 82 | 27 | unknown |

## 💎 Sorts les plus coûteux en MP

| Sort | Coût MP | Puissance | Type |
|------|---------|-----------|------|
| Lavender | 179 | 50 | unknown |
| Summon | 178 | 50 | unknown |
| Heavy | 171 | 12 | unknown |
| Shield | 170 | 30 | buff |
| Levitate | 169 | 12 | unknown |

## ⚡ Exemples de sorts

### Blaze (Feu)
- **Coût MP** : 9
- **Puissance** : 15
- **Niveau requis** : 116
- **Type** : Attaque feu

### Thunderbolt (Foudre)
- **Coût MP** : 20
- **Puissance** : 45
- **Chance de toucher** : 70%
- **Niveau requis** : 110
- **Type** : Attaque foudre

### Healing (Soin)
- **Coût MP** : 30
- **Puissance** : 8 (montant de soin)
- **Chance de toucher** : 100%
- **Niveau requis** : 100
- **Type** : Soin

## 🔬 Méthodologie d'extraction

Les données ont été extraites du fichier binaire **BLAZE.ALL** (44 MB) du jeu PlayStation "Blaze & Blade: Eternal Quest".

### Zones mémoire analysées
- **Zone des sorts** : 0x00909000 - 0x0090A000
- **Structure** : 48 bytes avant chaque nom de sort
- **Format** : int16 little-endian

### Pattern identifié
Les statistiques sont encodées dans une structure de données précédant le nom du sort :
- Position 0-7 : Métadonnées
- Position 8 : Coût MP (typiquement)
- Position 10-12 : Puissance/Dégâts
- Position 4-6 : Niveau requis
- Position 12-14 : Chance de toucher

## ⚠️ Notes importantes

1. Certaines valeurs peuvent être approximatives car la structure exacte n'est pas complètement documentée
2. Les sorts de type "unknown" nécessitent une analyse plus approfondie pour déterminer leur catégorie
3. Certains champs (casting_time, range, area_of_effect) sont actuellement null car non identifiés dans la structure binaire

## 📝 Utilisation

Pour utiliser ces données dans votre projet :

```python
import json

# Charger un sort spécifique
with open('spells/Blaze.json', 'r', encoding='utf-8') as f:
    blaze = json.load(f)
    print(f"MP Cost: {blaze['stats']['mp_cost']}")

# Charger l'index complet
with open('spells/INDEX.json', 'r', encoding='utf-8') as f:
    all_spells = json.load(f)
    print(f"Total spells: {all_spells['total_spells']}")
```

## 📅 Date d'extraction

Février 2026

## 🎮 Source

Blaze & Blade: Eternal Quest (PlayStation, 1998)
Fichier: BLAZE.ALL (46,206,976 bytes)
