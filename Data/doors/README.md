# Blaze & Blade - Door Database

Base de données des portes, organisée par zone et area.

## Structure

```
Data/doors/
  ├── zone_index.json          # Index de toutes les zones
  ├── door_types_reference.json # Types de portes et requis
  ├── keys_reference.json       # Liste de toutes les clés
  └── [zone_name]/             # Un dossier par zone
      └── [area_id].json        # Un fichier par area
```

## Zones

### Cavern of Death (Caverne de la Mort)
- **ID**: `cavern_of_death`
- **Areas**: 8
  - `floor_1_area_1.json`
  - `floor_1_area_2.json`
  - `floor_2_area_1.json`
  - `floor_3_area_1.json`
  - `floor_4_area_1.json`
  - `floor_5_area_1.json`
  - `floor_7_area_2.json`
  - `floor_7_area_3.json`

### Forest of Despair (Forêt du Désespoir)
- **ID**: `forest`
- **Areas**: 4
  - `floor_1_area_1.json`
  - `floor_1_area_4.json`
  - `floor_2_area_1.json`
  - `floor_2_area_2.json`

### Castle of Vamp (Château du Vampire)
- **ID**: `castle_of_vamp`
- **Areas**: 5
  - `floor_2_area_1.json`
  - `floor_3_area_1.json`
  - `floor_3_area_2.json`
  - `floor_5_area_1.json`
  - `floor_5_area_4.json`

### Mountain Valley (Vallée de la Montagne)
- **ID**: `valley`
- **Areas**: 1
  - `floor_1_area_1.json`

### Ancient Ruins (Ruines Anciennes)
- **ID**: `ancient_ruins`
- **Areas**: 2
  - `area_1.json`
  - `area_2.json`

### Fire Mountain (Montagne de Feu)
- **ID**: `fire_mountain`
- **Areas**: 1
  - `area_1.json`

### Tower (Tour)
- **ID**: `tower`
- **Areas**: 6
  - `area_2.json`
  - `area_3.json`
  - `area_6.json`
  - `area_8.json`
  - `area_9.json`
  - `area_11.json`

### Undersea Temple (Temple Sous-Marin)
- **ID**: `undersea`
- **Areas**: 2
  - `area_1.json`
  - `area_2.json`

### Hall of Demons (Hall des Démons)
- **ID**: `hall_of_demons`
- **Areas**: 7
  - `area_1.json`
  - `area_3.json`
  - `area_4.json`
  - `area_7.json`
  - `area_8.json`
  - `area_9.json`
  - `area_11.json`

### Sealed Cave (Caverne Scellée)
- **ID**: `sealed_cave`
- **Areas**: 5
  - `area_2.json`
  - `area_4.json`
  - `area_6.json`
  - `area_7.json`
  - `area_8.json`

## Types de Portes

### Porte ouverte (Unlocked)
- **Type ID**: `unlocked`
- **Description**: Porte standard, toujours ouverte

### Porte magique (Magic Locked)
- **Type ID**: `magic_locked`
- **Requis**: Magical Key
- **Description**: Nécessite la Magical Key pour ouvrir

### Porte démoniaque (Demon Engraved)
- **Type ID**: `demon_engraved`
- **Requis**: Demon Amulet
- **Description**: Porte avec gravure démoniaque, nécessite Demon Amulet

### Porte fantôme (Ghost Engraved)
- **Type ID**: `ghost_engraved`
- **Requis**: Ghost Amulet
- **Description**: Porte avec gravure de fantôme, nécessite Ghost Amulet

### Porte verrouillée (Key Locked)
- **Type ID**: `key_locked`
- **Requis**: Specific Key
- **Description**: Nécessite une clé spécifique (voir liste des clés)

### Porte événement (Event Locked)
- **Type ID**: `event_locked`
- **Requis**: Event Trigger
- **Description**: S'ouvre après un événement spécifique

### Porte de boss (Boss Door)
- **Type ID**: `boss_door`
- **Requis**: Boss Defeated
- **Description**: S'ouvre après avoir vaincu le boss

## Clés et Amulettes

| Nom (EN) | Nom (FR) | Ouvre | Notes |
|----------|----------|-------|-------|
| Black Key | Clé Noire | - |  |
| Dragon Key | Clé du Dragon | Treasure Chest |  |
| Cellar Key | Clé de Cave | Cellar Door |  |
| Clearing Key | Clé de Clairière | Clearing Door |  |
| Splendid Key | Clé Splendide | - |  |
| Test Founder's Key | Clé du Fondateur de Test | - |  |
| Blue Key | Clé Bleue | - |  |
| Black Quarz Key | Clé de Quartz Noir | - |  |
| Golden Key | Clé Dorée | - |  |
| Moon Key | Clé de Lune | - |  |
| Cell Key | Clé de Cellule | Cell Door |  |
| Black Dragon Key | Clé du Dragon Noir | Black Dragon Door |  |
| Blue Dragon Key | Clé du Dragon Bleu | Blue Dragon Door |  |
| Red Dragon Key | Clé du Dragon Rouge | Red Dragon Door |  |
| Antique Key | Clé Antique | - |  |
| Magic Key | Clé Magique | - | Different from Magical Key (amulet) |
| Magical Key | Magical Key | Magic Locked Doors |  |
| Demon Amulet | Amulette Démoniaque | Demon Engraved Doors |  |
| Ghost Amulet | Amulette Fantôme | Ghost Engraved Doors |  |

## Utilisation

Pour patcher les portes dans le jeu:
1. Éditer les fichiers JSON par area
2. Exécuter le patcher: `py -3 patch_doors.py`
3. Rebuild le jeu avec `build.bat`

## Format JSON (area)

```json
{
  "zone": {
    "id": "cavern_of_death",
    "name_en": "Cavern of Death",
    "name_fr": "Caverne de la Mort"
  },
  "area": {
    "id": "floor_1_area_1"
  },
  "doors": [
    {
      "id": "door_001",
      "type": "magic_locked",
      "position": {
        "x": 100,
        "y": 0,
        "z": 200
      },
      "required_item": "Magical Key",
      "destination": "Next Area",
      "notes": "Porte principale"
    }
  ],
  "summary": {
    "total_doors": 1,
    "by_type": {
      "magic_locked": 1
    }
  }
}
```
