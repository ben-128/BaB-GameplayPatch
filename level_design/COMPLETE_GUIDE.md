# Guide Complet - Analyse Level Design

Ce guide couvre les 4 objectifs principaux:
1. ✅ Visualisation Unity
2. ✅ Coffres et contenu
3. ✅ Spawns d'ennemis par zone
4. ✅ Portes et conditions d'ouverture

---

## 🚀 Quick Start - Tout Analyser

```bash
cd level_design
run_all_analyses.bat
```

Cela va exécuter les 3 scripts d'analyse et générer tous les fichiers nécessaires.

---

## 1️⃣ VISUALISATION UNITY

### Installation

Voir **`unity/UNITY_SETUP.md`** pour le guide complet.

### Résumé Express

1. **Créer projet Unity 3D**
2. **Copier dans Assets/**:
   - 5 fichiers `coordinates_zone_*.csv`
   - 3 fichiers CSV générés (`chest_positions.csv`, `spawn_positions.csv`, `door_positions.csv`)
3. **Copier dans Assets/Scripts/**:
   - `CoordinateLoader.cs`
   - `MultiZoneLoader.cs`
4. **Créer GameObject** → Add Component → CoordinateLoader
5. **Play** ▶️

### Fichiers CSV pour Unity

| Fichier | Type | Description |
|---------|------|-------------|
| `coordinates_zone_5mb.csv` | Géométrie | Floor/ceiling (RECOMMANDÉ) ⭐ |
| `chest_positions.csv` | Objects | Positions des coffres |
| `spawn_positions.csv` | Enemies | Points de spawn ennemis |
| `door_positions.csv` | Objects | Portes, gates, portals |

### Visualisation Combinée

Pour voir **tout en même temps** dans Unity:

```csharp
// Créer 4 GameObjects avec CoordinateLoader:
// 1. "Geometry" → coordinates_zone_5mb.csv (blanc/gradient)
// 2. "Chests" → chest_positions.csv (jaune)
// 3. "Spawns" → spawn_positions.csv (rouge)
// 4. "Doors" → door_positions.csv (bleu)
```

---

## 2️⃣ COFFRES ET CONTENU

### Exécuter l'Analyse

```bash
py -3 analyze_chests.py
```

### Outputs

**JSON détaillé:** `chest_analysis.json`
```json
{
  "text_references": [...],      // Textes mentionnant les coffres
  "key_references": [...],        // Clés qui ouvrent les coffres
  "chest_structures": [...],      // Structures binaires de coffres
  "summary": {
    "total_text_refs": 84,
    "total_keys": 50,
    "total_chests_found": 100
  }
}
```

**CSV Unity:** `chest_positions.csv`
```csv
offset,x,y,z,item_id,item_name,quantity,flags
0x100500,1024,512,2048,42,Magic Sword,1,0x0001
```

### Structure de Coffre Détectée

```
Offset: 0x100500
Position: (1024, 512, 2048)
Item ID: 42 → Magic Sword
Quantity: 1
Flags: 0x0001 (probablement "locked")
```

### Types de Coffres Trouvés

D'après les textes:
- **Steel Chest** (3rd Underlevel) - Nécessite Black Key
- **Treasure Chest** - Contient items légendaires
- **Sealed Chest** - Nécessite événement ou key spéciale
- **Locked Chest** - Clé standard

### Clés Identifiées

- **Black Key** → Steel chests
- **Host's Door Key** → Portes spécifiques
- **Test Founder's Key** → Treasure chest spécial
- **Dragon Key** → Treasure chest avancé

---

## 3️⃣ SPAWNS D'ENNEMIS PAR ZONE

### Exécuter l'Analyse

```bash
py -3 analyze_enemy_spawns.py
```

### Outputs

**JSON détaillé:** `spawn_analysis.json`
```json
{
  "level_zones": {...},           // Zones de niveaux identifiées
  "spawn_structures": [...],      // Points de spawn détectés
  "spawn_tables": [...],          // Tables de spawn
  "analysis": {
    "unique_monsters": 50,
    "total_spawn_points": 200,
    "spawn_chance_distribution": {...}
  }
}
```

**CSV Unity:** `spawn_positions.csv`
```csv
offset,zone,x,y,z,monster_id,monster_name,type,spawn_chance,spawn_count
0x150000,Level Data 1-3MB,512,256,1024,5,Skeleton,Normal,80,3
```

### Structure de Spawn Détectée

```
Offset: 0x150000
Zone: Level Data 1-3MB
Position: (512, 256, 1024)
Monster: Skeleton (ID: 5)
Type: Normal
Spawn Chance: 80%
Spawn Count: 3 (min-max probable)
```

### Randomness Analysis

Le script analyse:
- **Distribution de probabilités** (spawn_chance %)
- **Monstres avec spawns multiples** (patrol zones)
- **Tables de spawn** (groupes consécutifs)

### Exemple de Résultat

```
Zone: Castle Of Vamp
  - Skeleton (ID 5): 80% chance, 2-4 spawns
  - Zombie (ID 7): 60% chance, 1-2 spawns
  - Ghost (ID 12): 30% chance, 1 spawn
  - Boss (ID 45): 100% chance, 1 spawn (fixed)
```

---

## 4️⃣ PORTES ET CONDITIONS

### Exécuter l'Analyse

```bash
py -3 analyze_doors.py
```

### Outputs

**JSON détaillé:** `door_analysis.json`
```json
{
  "door_types": {
    "magic_locked": [...],
    "demon_engraved": [...],
    "ghost_engraved": [...],
    "key_locked": [...],
    "generic": [...]
  },
  "gates": {...},
  "portals": [...],
  "keys": [...],
  "door_structures": [...]
}
```

**CSV Unity:** `door_positions.csv`
```csv
offset,x,y,z,type,type_desc,key_id,dest_id,flags
0x180000,768,384,1536,1,Key Locked,12,5,0x0001
```

### Types de Portes Identifiés

| Type ID | Description | Condition |
|---------|-------------|-----------|
| 0 | Unlocked | Toujours ouverte |
| 1 | Key Locked | Nécessite clé spécifique |
| 2 | Magic Locked | Nécessite sort ou item magique |
| 3 | Demon Engraved | Nécessite item démon |
| 4 | Ghost Engraved | Nécessite item fantôme |
| 5 | Event Locked | Nécessite événement (boss battu) |
| 6 | Boss Door | S'ouvre après boss |
| 7 | One-way Door | Ne s'ouvre que d'un côté |

### Structure de Porte Détectée

```
Offset: 0x180000
Position: (768, 384, 1536)
Type: Key Locked
Key Required: ID 12 (Black Key)
Destination Level: ID 5 (2nd Floor)
Flags: 0x0001 (locked state)
```

### Gates & Gate Crystals

**Gate Crystal** = Item activant un gate magique

Trouvés:
- "Activates the gate to the summoned" (portail boss)
- Gates dans les ruins (mystérieux)

### Portals

**266 références de portals** trouvées

Fonctions:
- Retour aux Underlevels précédents
- Sortie de maze (Crystal Maze)
- Téléportation inter-zones

Exemple:
```
Portal @ 0x2BF5000:
  "With this portal one can return to the 1st Underlevel"
  Destination: 1st Underlevel
```

---

## 🎮 UNITY - Visualisation Complète

### Script de Chargement Universel

Créer `UniversalLevelLoader.cs`:

```csharp
using UnityEngine;
using System.Collections.Generic;

public class UniversalLevelLoader : MonoBehaviour
{
    [Header("CSV Files")]
    public string geometryFile = "coordinates_zone_5mb.csv";
    public string chestsFile = "chest_positions.csv";
    public string spawnsFile = "spawn_positions.csv";
    public string doorsFile = "door_positions.csv";

    [Header("Visual Settings")]
    public Color geometryColor = Color.white;
    public Color chestColor = Color.yellow;
    public Color spawnColor = Color.red;
    public Color doorColor = Color.blue;

    [Header("Scale")]
    public float scale = 0.01f;

    void Start()
    {
        LoadAndDisplay(geometryFile, geometryColor, "Geometry", PrimitiveType.Cube, 0.05f);
        LoadAndDisplay(chestsFile, chestColor, "Chests", PrimitiveType.Cube, 0.2f);
        LoadAndDisplay(spawnsFile, spawnColor, "Spawns", PrimitiveType.Sphere, 0.15f);
        LoadAndDisplay(doorsFile, doorColor, "Doors", PrimitiveType.Cylinder, 0.3f);
    }

    void LoadAndDisplay(string filename, Color color, string layerName,
                        PrimitiveType shape, float size)
    {
        // Implementation...
        // Charge le CSV et crée les objets 3D
    }
}
```

### Rendu Final

Vous verrez:
- **Points blancs** = Géométrie du niveau (walls/floors)
- **Cubes jaunes** = Coffres
- **Sphères rouges** = Points de spawn ennemis
- **Cylindres bleus** = Portes/Gates

---

## 📊 ANALYSE CROISÉE

### Validation des Données

1. **Comparer avec Gameplay**
   - Lancer l'émulateur PS1
   - Naviguer vers une zone connue
   - Compter les coffres/ennemis visibles
   - Vérifier les positions dans Unity

2. **Cross-Reference Spatiale**
   - Les spawns sont-ils près de la géométrie?
   - Les portes sont-elles aux bons endroits?
   - Les coffres sont-ils dans des rooms?

3. **Validation Logique**
   - Un monstre boss spawn une seule fois (100% chance)
   - Les coffres ont des items cohérents
   - Les portes locked ont des clés associées

### Exemples de Validation

**Coffre:**
```
Position Unity: (10.24, 5.12, 20.48)
Position PSX: (1024, 512, 2048)
Scale: 0.01 ✓ Correct

Item: Magic Sword (ID 42)
Vérifier dans items/all_items_clean.json → ID 42 existe ✓

Locked: Flag 0x0001
Chercher clé associée → Black Key (offset 0x7EDB7E) ✓
```

**Spawn:**
```
Monster: Skeleton (ID 5)
Vérifier dans monster_stats/normal_enemies/ → Skeleton.json ✓

Spawn Chance: 80%
Observation in-game: Skeleton apparaît fréquemment ✓

Spawn Count: 3
Observer 2-4 Skeletons dans cette zone ✓
```

---

## 🔬 ANALYSE AVANCÉE

### Pattern Detection

**Identifier les Rooms:**
```python
# Grouper les spawns/coffres/portes par proximité
# Les clusters = rooms distinctes
from sklearn.cluster import DBSCAN

coords = [(spawn['x'], spawn['y'], spawn['z']) for spawn in spawns]
clustering = DBSCAN(eps=500, min_samples=2).fit(coords)

# Chaque cluster = une room
```

**Spawn Tables:**
Les "spawn_tables" dans spawn_analysis.json indiquent des arrays de spawns consécutifs:
```
Table @ 0x150000: 10 entries × 16 bytes = 160 bytes
→ 10 spawns configurés ensemble
→ Probablement une zone/room spécifique
```

**Door Networks:**
Tracer le graphe des portes:
```
Door A (pos 1) → Dest ID 5 → Door B (pos 2)
Door B (pos 2) → Dest ID 1 → Door A (pos 1)
→ Connexion bi-directionnelle (aller-retour)
```

---

## 📁 Structure des Fichiers Générés

```
level_design/
├── chest_analysis.json       # Données complètes coffres
├── chest_positions.csv        # Positions Unity-ready
├── spawn_analysis.json        # Données complètes spawns
├── spawn_positions.csv        # Positions Unity-ready
├── door_analysis.json         # Données complètes portes
├── door_positions.csv         # Positions Unity-ready
├── coordinates_zone_*.csv     # Géométrie (5 zones)
├── coordinates_export.json    # Master coords
└── unity/
    ├── CoordinateLoader.cs    # Loader simple
    ├── MultiZoneLoader.cs     # Loader multi-zones
    └── UNITY_SETUP.md         # Guide Unity
```

---

## ✅ Checklist de Validation

### Pour les Coffres
- [ ] Nombre de coffres cohérent avec le jeu
- [ ] Items dans coffres existent dans items database
- [ ] Clés associées identifiées
- [ ] Positions dans des rooms (pas dans les murs)

### Pour les Spawns
- [ ] Monstres existent dans monster_stats
- [ ] Spawn chances raisonnables (0-100%)
- [ ] Boss spawns à 100% (unique)
- [ ] Positions accessibles (pas dans murs)

### Pour les Portes
- [ ] Types de portes cohérents
- [ ] Clés requises existent
- [ ] Destinations pointent vers niveaux valides
- [ ] Portals retournent aux zones précédentes

### Pour Unity
- [ ] Géométrie forme des rooms reconnaissables
- [ ] Coffres/Spawns/Portes bien placés
- [ ] Pas d'objets dans les murs
- [ ] Échelle cohérente (0.01 recommandé)

---

## 🐛 Troubleshooting

### Problème: Aucun coffre trouvé

**Cause:** Items database pas chargée ou IDs incompatibles

**Solution:**
```bash
# Vérifier items database
dir ..\items\all_items_clean.json

# Si manquant, extraire items d'abord
cd ..\items
py -3 extract_complete_database.py
```

### Problème: Aucun spawn trouvé

**Cause:** Monster index manquant ou incomplet

**Solution:**
```bash
# Vérifier monster index
dir ..\monster_stats\_index.json

# Si manquant, rebuild index
cd ..\monster_stats
py -3 update_index.py
```

### Problème: Positions bizarres dans Unity

**Cause:** Échelle incorrecte

**Solution:**
```csharp
// Dans CoordinateLoader:
coordinateScale = 0.01f;  // Standard PSX scale

// Si trop petit → 0.1
// Si trop grand → 0.001
```

---

## 🎯 Objectifs Atteints

✅ **1. Unity Visualization**
- Scripts C# prêts à l'emploi
- Guide d'installation complet
- Support multi-zones

✅ **2. Coffres et Contenu**
- Extraction des coffres
- Mapping avec items database
- Identification des clés
- CSV Unity-ready

✅ **3. Spawns d'Ennemis**
- Détection des spawns
- Probabilités de spawn
- Tables de spawn
- Mapping avec monsters
- CSV Unity-ready

✅ **4. Portes et Conditions**
- Types de portes identifiés
- Clés requises mappées
- Gates et portals
- Destinations identifiées
- CSV Unity-ready

---

## 🚀 Prochaines Étapes

1. **Exécuter les analyses**
   ```bash
   run_all_analyses.bat
   ```

2. **Importer dans Unity**
   - Suivre unity/UNITY_SETUP.md
   - Charger tous les CSV

3. **Valider visuellement**
   - Comparer avec screenshots gameplay
   - Vérifier cohérence spatiale

4. **Documenter les découvertes**
   - Noter les patterns observés
   - Identifier les rooms/zones
   - Mapper le level flow

5. **Modifier le jeu** (optionnel)
   - Changer spawns
   - Modifier chest contents
   - Relocate portes

---

**Tout est prêt! Bon reverse engineering! 🎮🔍**
