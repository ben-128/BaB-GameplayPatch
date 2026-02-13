# 🚪 Blaze & Blade - Analyse des Portes par Niveau

## 📊 Vue d'Ensemble

**Base de données complète** des portes, clés et amulettes du jeu, organisée par zone et area.

- **Total zones**: 10
- **Total areas**: 41
- **Total types de portes**: 7
- **Total clés/amulettes**: 19

---

## 🗺️ Organisation par Zone

### 1. Cavern of Death (Caverne de la Mort)
**ID**: `cavern_of_death` | **Areas**: 8

| Area | Fichier JSON |
|------|-------------|
| Floor 1 - Area 1 | `cavern_of_death/floor_1_area_1.json` |
| Floor 1 - Area 2 | `cavern_of_death/floor_1_area_2.json` |
| Floor 2 - Area 1 | `cavern_of_death/floor_2_area_1.json` |
| Floor 3 - Area 1 | `cavern_of_death/floor_3_area_1.json` |
| Floor 4 - Area 1 | `cavern_of_death/floor_4_area_1.json` |
| Floor 5 - Area 1 | `cavern_of_death/floor_5_area_1.json` |
| Floor 7 - Area 2 | `cavern_of_death/floor_7_area_2.json` |
| Floor 7 - Area 3 | `cavern_of_death/floor_7_area_3.json` |

---

### 2. Forest of Despair (Forêt du Désespoir)
**ID**: `forest` | **Areas**: 4

| Area | Fichier JSON |
|------|-------------|
| Floor 1 - Area 1 | `forest/floor_1_area_1.json` |
| Floor 1 - Area 4 | `forest/floor_1_area_4.json` |
| Floor 2 - Area 1 | `forest/floor_2_area_1.json` |
| Floor 2 - Area 2 | `forest/floor_2_area_2.json` |

---

### 3. Castle of Vamp (Château du Vampire)
**ID**: `castle_of_vamp` | **Areas**: 5

| Area | Fichier JSON |
|------|-------------|
| Floor 2 - Area 1 | `castle_of_vamp/floor_2_area_1.json` |
| Floor 3 - Area 1 | `castle_of_vamp/floor_3_area_1.json` |
| Floor 3 - Area 2 | `castle_of_vamp/floor_3_area_2.json` |
| Floor 5 - Area 1 | `castle_of_vamp/floor_5_area_1.json` |
| Floor 5 - Area 4 | `castle_of_vamp/floor_5_area_4.json` |

---

### 4. Mountain Valley (Vallée de la Montagne)
**ID**: `valley` | **Areas**: 1

| Area | Fichier JSON |
|------|-------------|
| Floor 1 - Area 1 | `valley/floor_1_area_1.json` |

---

### 5. Ancient Ruins (Ruines Anciennes)
**ID**: `ancient_ruins` | **Areas**: 2

| Area | Fichier JSON |
|------|-------------|
| Area 1 | `ancient_ruins/area_1.json` |
| Area 2 | `ancient_ruins/area_2.json` |

---

### 6. Fire Mountain (Montagne de Feu)
**ID**: `fire_mountain` | **Areas**: 1

| Area | Fichier JSON |
|------|-------------|
| Area 1 | `fire_mountain/area_1.json` |

---

### 7. Tower (Tour)
**ID**: `tower` | **Areas**: 6

| Area | Fichier JSON |
|------|-------------|
| Area 2 | `tower/area_2.json` |
| Area 3 | `tower/area_3.json` |
| Area 6 | `tower/area_6.json` |
| Area 8 | `tower/area_8.json` |
| Area 9 | `tower/area_9.json` |
| Area 11 | `tower/area_11.json` |

---

### 8. Undersea Temple (Temple Sous-Marin)
**ID**: `undersea` | **Areas**: 2

| Area | Fichier JSON |
|------|-------------|
| Area 1 | `undersea/area_1.json` |
| Area 2 | `undersea/area_2.json` |

---

### 9. Hall of Demons (Hall des Démons)
**ID**: `hall_of_demons` | **Areas**: 7

| Area | Fichier JSON |
|------|-------------|
| Area 1 | `hall_of_demons/area_1.json` |
| Area 3 | `hall_of_demons/area_3.json` |
| Area 4 | `hall_of_demons/area_4.json` |
| Area 7 | `hall_of_demons/area_7.json` |
| Area 8 | `hall_of_demons/area_8.json` |
| Area 9 | `hall_of_demons/area_9.json` |
| Area 11 | `hall_of_demons/area_11.json` |

---

### 10. Sealed Cave (Caverne Scellée)
**ID**: `sealed_cave` | **Areas**: 5

| Area | Fichier JSON |
|------|-------------|
| Area 2 | `sealed_cave/area_2.json` |
| Area 4 | `sealed_cave/area_4.json` |
| Area 6 | `sealed_cave/area_6.json` |
| Area 7 | `sealed_cave/area_7.json` |
| Area 8 | `sealed_cave/area_8.json` |

---

## 🔑 Types de Portes

| Type | Nom FR | Objet Requis | Description |
|------|--------|--------------|-------------|
| `unlocked` | Porte ouverte | Aucun | Porte standard, toujours ouverte |
| `magic_locked` | Porte magique | **Magical Key** | Nécessite la Magical Key pour ouvrir |
| `demon_engraved` | Porte démoniaque | **Demon Amulet** | Porte avec gravure démoniaque |
| `ghost_engraved` | Porte fantôme | **Ghost Amulet** | Porte avec gravure de fantôme |
| `key_locked` | Porte verrouillée | Clé spécifique | Nécessite une clé particulière (voir liste) |
| `event_locked` | Porte événement | Event Trigger | S'ouvre après un événement spécifique |
| `boss_door` | Porte de boss | Boss Defeated | S'ouvre après avoir vaincu le boss |

---

## 🗝️ Liste Complète des Clés et Amulettes

### Amulettes Magiques (Ouvrent plusieurs portes)

| Nom | Nom FR | Ouvre |
|-----|--------|-------|
| **Magical Key** | Magical Key | Toutes les portes magiques du jeu |
| **Demon Amulet** | Amulette Démoniaque | Portes avec gravure démoniaque |
| **Ghost Amulet** | Amulette Fantôme | Portes avec gravure fantôme |

### Clés des Dragons

| Nom | Nom FR | Ouvre |
|-----|--------|-------|
| Black Dragon Key | Clé du Dragon Noir | Porte du Dragon Noir |
| Blue Dragon Key | Clé du Dragon Bleu | Porte du Dragon Bleu |
| Red Dragon Key | Clé du Dragon Rouge | Porte du Dragon Rouge |
| Dragon Key | Clé du Dragon | Coffres au trésor spéciaux |

### Clés Spéciales

| Nom | Nom FR | Ouvre | Localisation |
|-----|--------|-------|--------------|
| Cellar Key | Clé de Cave | Porte de la cave | ? |
| Cell Key | Clé de Cellule | Porte de cellule | ? |
| Clearing Key | Clé de Clairière | Porte de la clairière | ? |
| Black Key | Clé Noire | ? | Abandoned Mine - 3rd Underlevel |

### Clés Standards

| Nom | Nom FR | Notes |
|-----|--------|-------|
| Blue Key | Clé Bleue | Clé standard |
| Golden Key | Clé Dorée | Clé standard |
| Moon Key | Clé de Lune | Clé standard |
| Antique Key | Clé Antique | Clé ancienne |
| Splendid Key | Clé Splendide | Clé spéciale |
| Black Quarz Key | Clé de Quartz Noir | Clé en quartz |
| Magic Key | Clé Magique | ⚠️ Différent de Magical Key (amulette) |
| Test Founder's Key | Clé du Fondateur de Test | Clé de test |

---

## 📈 Statistiques d'Analyse (BLAZE.ALL)

D'après l'analyse du fichier BLAZE.ALL :

### Références Textuelles
- **Portes verrouillées par magie**: 61 références
- **Portes avec gravure démoniaque**: 3 références
- **Portes avec gravure fantôme**: 2 références
- **Portes nécessitant des clés**: 131 références
- **Portes génériques**: 138 références

### Portails
- **Total portails**: 50
- **Gate Crystals**: 4
- **Portails vers 1st Underlevel**: 32

---

## 📝 Utilisation

### Consulter les Portes d'une Zone

```bash
cat Data/doors/cavern_of_death/floor_1_area_1.json
```

### Voir Toutes les Clés

```bash
cat Data/doors/keys_reference.json
```

### Voir les Types de Portes

```bash
cat Data/doors/door_types_reference.json
```

### Index des Zones

```bash
cat Data/doors/zone_index.json
```

---

## 🛠️ Prochaines Étapes

1. **Exploration in-game** : Explorer chaque area et noter les portes
2. **Population des données** : Remplir les fichiers JSON avec les données réelles
3. **Création du patcher** : Script pour modifier les portes dans BLAZE.ALL
4. **Tests** : Vérifier que les modifications fonctionnent en jeu

---

## 📚 Fichiers de Référence

| Fichier | Description |
|---------|-------------|
| `zone_index.json` | Index de toutes les zones et areas |
| `door_types_reference.json` | Types de portes et objets requis |
| `keys_reference.json` | Liste complète des clés et amulettes |
| `README.md` | Documentation complète du système |
| `SUMMARY.md` | Ce fichier - résumé visuel |

---

## 🎮 Format JSON par Area

Chaque fichier area contient:

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
      "position": {"x": 100, "y": 0, "z": 200},
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

---

**Dernière mise à jour**: 2026-02-13
**Status**: Structure créée, données à peupler via exploration in-game
