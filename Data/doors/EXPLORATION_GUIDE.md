# Guide d'Exploration pour Cataloguer les Portes

Ce guide vous aide à explorer le jeu pour cataloguer toutes les portes.

## 🎯 Objectif

Explorer chaque zone/area et noter:
1. Nombre de portes
2. Type de chaque porte (ouverte, verrouillée, magique, etc.)
3. Position approximative
4. Objet requis pour ouvrir
5. Destination

## 📋 Checklist d'Exploration

Pour chaque area, notez:

```
Zone: [nom]
Area: [id]

Porte 1:
  - Type: [unlocked/key_locked/magic_locked/etc.]
  - Position: [description/coordonnées]
  - Objet requis: [None/Magical Key/Blue Key/etc.]
  - Destination: [area suivante]
  - Notes: [observations]
```

## 🗝️ Types de Portes à Identifier

### magic_locked
- **Description**: Portes verrouillées par magie trouvées dans le jeu
- **Objet requis**: Magical Key
- **Occurrences connues**: 61 références dans BLAZE.ALL

### demon_engraved
- **Description**: Portes avec gravure démoniaque
- **Objet requis**: Demon Amulet
- **Occurrences connues**: 3 références dans BLAZE.ALL

### ghost_engraved
- **Description**: Portes avec gravure fantôme
- **Objet requis**: Ghost Amulet
- **Occurrences connues**: 2 références dans BLAZE.ALL

### key_locked
- **Description**: Portes nécessitant des clés spécifiques
- **Objet requis**: Various Keys
- **Occurrences connues**: 131 références dans BLAZE.ALL

### generic
- **Description**: Portes génériques/ouvertes
- **Occurrences connues**: 138 références dans BLAZE.ALL

## 📍 Zones à Explorer

### Caverne de la Mort (Cavern of Death)
**Areas à explorer**: 8

**Checklist**:
- [ ] floor_1_area_1
- [ ] floor_1_area_2
- [ ] floor_2_area_1
- [ ] floor_3_area_1
- [ ] floor_4_area_1
- [ ] floor_5_area_1
- [ ] floor_7_area_2
- [ ] floor_7_area_3

### Forêt du Désespoir (Forest of Despair)
**Areas à explorer**: 4

**Checklist**:
- [ ] floor_1_area_1
- [ ] floor_1_area_4
- [ ] floor_2_area_1
- [ ] floor_2_area_2

### Château du Vampire (Castle of Vamp)
**Areas à explorer**: 5

**Clés trouvables dans cette zone**:
- Golden Key → Ouvre: Castle doors
- Cell Key → Ouvre: Prison cell

**Checklist**:
- [ ] floor_2_area_1
- [ ] floor_3_area_1
- [ ] floor_3_area_2
- [ ] floor_5_area_1
- [ ] floor_5_area_4

### Vallée de la Montagne (Mountain Valley)
**Areas à explorer**: 1

**Checklist**:
- [ ] floor_1_area_1

### Ruines Anciennes (Ancient Ruins)
**Areas à explorer**: 2

**Clés trouvables dans cette zone**:
- Antique Key → Ouvre: Ancient doors

**Checklist**:
- [ ] area_1
- [ ] area_2

### Montagne de Feu (Fire Mountain)
**Areas à explorer**: 1

**Checklist**:
- [ ] area_1

### Tour (Tower)
**Areas à explorer**: 6

**Clés trouvables dans cette zone**:
- Blue Key → Ouvre: Tower doors
- Red Crystal → Ouvre: Special door

**Checklist**:
- [ ] area_2
- [ ] area_3
- [ ] area_6
- [ ] area_8
- [ ] area_9
- [ ] area_11

### Temple Sous-Marin (Undersea Temple)
**Areas à explorer**: 2

**Checklist**:
- [ ] area_1
- [ ] area_2

### Hall des Démons (Hall of Demons)
**Areas à explorer**: 7

**Clés trouvables dans cette zone**:
- Demon Amulet → Ouvre: Demon engraved doors

**Checklist**:
- [ ] area_1
- [ ] area_3
- [ ] area_4
- [ ] area_7
- [ ] area_8
- [ ] area_9
- [ ] area_11

### Caverne Scellée (Sealed Cave)
**Areas à explorer**: 5

**Clés trouvables dans cette zone**:
- Ghost Amulet → Ouvre: Ghost engraved doors

**Checklist**:
- [ ] area_2
- [ ] area_4
- [ ] area_6
- [ ] area_7
- [ ] area_8

## 💡 Conseils

1. **Sauvegardez souvent** pendant l'exploration
2. **Prenez des screenshots** des portes intéressantes
3. **Notez les coordonnées** si possible (menu debug?)
4. **Testez les clés** : vérifiez quelle clé ouvre quelle porte
5. **Cartographiez** : dessinez une petite carte si nécessaire

## 📝 Remplir les JSON Après Exploration

Une fois une area explorée:

1. Ouvrir `Data/doors/[zone]/[area].json`
2. Remplir la section `"doors": []` avec vos découvertes
3. Utiliser le format du fichier EXAMPLE_area_with_doors.json

Exemple:
```json
{
  "id": "door_001",
  "type": "magic_locked",
  "type_name": "Porte magique",
  "position": {
    "x": 150,
    "y": 0,
    "z": 200
  },
  "required_item": "Magical Key",
  "destination": "next_area",
  "notes": "Porte principale au nord"
}
```
