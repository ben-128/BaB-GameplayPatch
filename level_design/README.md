# Level Design Data Analysis & Modding

## 📁 Contenu du Dossier

Ce dossier contient l'analyse complète ET les outils de modification pour le level design de Blaze & Blade.

### ⭐ NOUVEAU: Modification des Portes
- ✅ Débloquer les portes
- ✅ Enlever les clés requises
- ✅ Changer les destinations
- ✅ Réinjecter dans le jeu

---

## 📊 Fichiers de Données

### Données JSON

| Fichier | Taille | Description |
|---------|--------|-------------|
| **coordinates_export.json** | 111 KB | Master file - Toutes les coordonnées 3D extraites des 5 zones |
| **level_data_analysis.json** | 61 KB | Structures détaillées autour des noms de niveaux |
| **spawn_data_analysis.json** | 47 KB | Candidats de spawns monstres et références de coffres |

### Données CSV (Coordonnées 3D)

| Fichier | Points | Range X | Range Y | Range Z | Description |
|---------|--------|---------|---------|---------|-------------|
| **coordinates_zone_1mb.csv** | 500 | 0-7966 | 0-7708 | 0-7956 | Zone géométrie niveau 1 |
| **coordinates_zone_2mb.csv** | 500 | 0-5911 | 0-5911 | 0-5911 | Zone géométrie niveau 2 |
| **coordinates_zone_3mb.csv** | 500 | -61-246 | 0-4227 | 0-3084 | Données vertex/polygones |
| **coordinates_zone_5mb.csv** | 500 | 0-4085 | -61-3084 | 0-4085 | **Géométrie floor/ceiling** ⭐ |
| **coordinates_zone_9mb.csv** | 500 | ±8192 | ±8192 | 0-1792 | Caméras/spawns |

---

## 🔬 Scripts d'Analyse

### 1. explore_level_design.py
**Premier niveau d'analyse**
- Extraction de 272,056 strings ASCII
- Recherche de keywords (level, dungeon, cave, castle, etc.)
- Détection de patterns de coordonnées basiques
- Analyse de la structure du fichier

**Usage:**
```bash
py -3 explore_level_design.py
```

### 2. analyze_level_data.py
**Analyse détaillée des noms de niveaux**
- Localisation de 11 noms de niveaux/maps uniques
- Analyse des structures binaires avant/après les noms
- Détection de patterns de map data
- Analyse des références floor/underlevel (115+ occurrences)

**Output:** `level_data_analysis.json`

**Usage:**
```bash
py -3 analyze_level_data.py
```

### 3. extract_spawn_data.py
**Détection de spawns et objets**
- Recherche de références monstres (nécessite monster_stats/_index.json)
- Extraction de 84 références chest/treasure
- Identification de 35 zones de structures répétées
- Analyse de zones 1MB-10MB

**Output:** `spawn_data_analysis.json`

**Usage:**
```bash
py -3 extract_spawn_data.py
```

### 4. deep_structure_analysis.py
**Analyse binaire approfondie**
- Extraction de 20,000+ candidats de coordonnées 3D
- Détection de tables structurées (8-64 bytes)
- Analyse multi-format (int16, uint16, int32, float)
- Recherche de structures type "monster" (40 valeurs)

**Usage:**
```bash
py -3 deep_structure_analysis.py
```

### 5. export_coordinates.py
**Export des coordonnées pour visualisation**
- Extraction des coordonnées 3D validées
- Export en CSV (Excel/Python compatible)
- Export en JSON (master file)
- Calcul des bounding boxes

**Output:** Tous les fichiers CSV + `coordinates_export.json`

**Usage:**
```bash
py -3 export_coordinates.py
```

---

## 📖 Rapports de Documentation

### LEVEL_DESIGN_REPORT.md
**Rapport initial complet**
- 11 noms de niveaux identifiés
- 672 références de rooms
- 266 références de portals
- 2,627 images TIM PSX
- Structure hiérarchique des niveaux (Floors, Underlevels)
- Objets interactifs (doors, gates, chests)
- Recommandations de recherche

### LEVEL_DESIGN_FINDINGS.md
**Analyse approfondie des découvertes**
- Données de coordonnées détaillées par zone
- Patterns structurels identifiés
- Hypothèses sur la géométrie de niveau
- Données de caméra/viewport
- Spécifications techniques PSX
- 6 zones de données identifiées (Graphics, Level Data, Game Logic, Text)

### COORDINATE_VISUALIZATION.md
**Guide de visualisation 3D**
- Instructions Python (matplotlib)
- Instructions Blender
- Instructions Unity
- Méthodes de visualisation en ligne
- Recommandations d'analyse

---

## 🎯 Découvertes Clés

### Niveaux Identifiés

1. **Castle Of Vamp** (4 variations: 02, 03, 05 BOSS, 06)
2. **CAVERN OF DEATH** (6 occurrences)
3. **The Sealed Cave** (13 occurrences)
4. **The Wood of Ruins**
5. **The Ancient Ruins** (4 occurrences)
6. **The Ruins in the Lake**
7. **The Forest**
8. **The Mountain of the Fire Dragon**
9. **VALLEY OF WHITE WIND** (3 occurrences)
10. **Map03** / **MAP10** (références multiples)

### Structure Hiérarchique

```
Dungeons Multi-Niveaux
├── Floor 1, 2, 3 (18/10/7 références)
├── Underlevel 1, 2, 3 (115 références)
├── Rooms (672 références)
│   ├── Storage Room
│   ├── Control Room
│   ├── Guest Room
│   └── Treasure Chamber
├── Portals (266 références)
├── Doors (337 références)
└── Gates (150 références)
```

### Coordonnées 3D

**Zone 5MB (0x500000) - LA PLUS PROMETTEUSE** ⭐
- Patterns très réguliers
- Ressemble à de la géométrie floor/ceiling
- Coordonnées: 0-4085 (X/Z), -61-3084 (Y)
- 500+ points exploitables

**Zone 9MB (0x900000) - Caméras/Spawns**
- Range complet PSX: ±8192
- Probablement des positions de caméra fixe
- Données de spawn possibles

---

## 🚀 Quick Start

### Visualiser les Coordonnées (Recommandé)

**Option 1: Python matplotlib**
```python
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Charger la zone la plus prometteuse
df = pd.read_csv('coordinates_zone_5mb.csv')

# Créer plot 3D
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(df['x'], df['y'], df['z'], c='blue', marker='o', s=1)
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.title('Blaze & Blade - Floor/Ceiling Geometry')
plt.show()
```

**Option 2: Excel/LibreOffice**
1. Ouvrir `coordinates_zone_5mb.csv`
2. Créer un graphique 3D scatter
3. Observer les patterns

### Re-générer les Données

Si vous modifiez `BLAZE.ALL`:
```bash
# 1. Analyser les noms de niveaux
py -3 analyze_level_data.py

# 2. Extraire les spawns
py -3 extract_spawn_data.py

# 3. Exporter les coordonnées
py -3 export_coordinates.py
```

---

## 📈 Statistiques

| Catégorie | Quantité |
|-----------|----------|
| Noms de niveaux uniques | 11 |
| Références de rooms | 672 |
| Références de portals | 266 |
| Références de doors | 337 |
| Références de gates | 150 |
| Références de chests | 84 |
| Images TIM PSX | 2,627 |
| Coordonnées 3D extraites | 2,500+ |
| Zones de données identifiées | 6 |

---

## 🔍 Prochaines Étapes

### Validation Immédiate

1. **Visualiser Zone 5MB** - Voir si ça ressemble à des niveaux
2. **Comparer avec gameplay** - Screenshots vs coordonnées
3. **Identifier patterns** - Rooms, corridors, chambers

### Recherche Avancée

4. **Cross-référencer spawns** - Utiliser monster_stats/_index.json
5. **Identifier format TMD** - Extraire modèles 3D PSX
6. **Memory watching** - Émulateur PS1 + memory viewer
7. **Décompression** - Tester LZSS/RLE sur zones identifiées

---

## 📧 Support

Pour questions ou contributions:
- Voir `../README.md` (projet principal)
- Repository: GameplayPatch/level_design/

---

## 📜 Licence

Données extraites à des fins de recherche et préservation du patrimoine vidéoludique.

*Blaze & Blade: Eternal Quest © 1998 T&E Soft*

---

**Dernière mise à jour:** 2026-02-04
