# 🚪 Analyse Complète des Portes - Blaze & Blade

**Date**: 2026-02-13
**Status**: Structure créée, données textuelles extraites, prêt pour exploration

---

## 📊 Ce Qui A Été Fait

### 1. ✅ Analyse de BLAZE.ALL (Fichier Binaire)

**Méthode**: Analyse textuelle du fichier BLAZE.ALL (44.1 MB)

**Résultats trouvés** (références textuelles) :
- **61 références** à "doors locked by magic" → Magical Key
- **3 références** à "demon engravings" → Demon Amulet
- **2 références** à "ghost engravings" → Ghost Amulet
- **131 références** à portes nécessitant des clés spécifiques
- **138 références** à portes génériques/ouvertes
- **200+ occurrences** du mot "door" dans le jeu

**19 Clés/Amulettes Identifiées**:
- 3 Amulettes magiques (Magical Key, Demon Amulet, Ghost Amulet)
- 4 Clés de Dragon (Black, Blue, Red, Dragon Key)
- 3 Clés spéciales (Cell, Cellar, Clearing)
- 9 Clés standards (Blue, Golden, Moon, Black, Antique, etc.)

### 2. ✅ Structure de Base de Données Créée

**41 Fichiers JSON** organisés par zone:
```
Data/doors/
├── cavern_of_death/ (8 areas)
├── forest/ (4 areas)
├── castle_of_vamp/ (5 areas)
├── valley/ (1 area)
├── ancient_ruins/ (2 areas)
├── fire_mountain/ (1 area)
├── tower/ (6 areas)
├── undersea/ (2 areas)
├── hall_of_demons/ (7 areas)
└── sealed_cave/ (5 areas)
```

Chaque fichier JSON contient:
- Informations de zone/area
- Section `"doors": []` **vide** (à remplir)
- Statistiques connues du jeu entier
- Notes d'exploration

### 3. ✅ Fichiers de Référence

| Fichier | Contenu |
|---------|---------|
| `zone_index.json` | Index des 10 zones, 41 areas |
| `door_types_reference.json` | 7 types de portes définis |
| `keys_reference.json` | 19 clés cataloguées |
| `EXPLORATION_GUIDE.md` | **Guide complet d'exploration** |
| `EXAMPLE_area_with_doors.json` | Exemple de JSON rempli |
| `SUMMARY.md` | Résumé visuel complet |
| `README.md` | Documentation technique |

---

## ⚠️ Pourquoi L'Analyse Binaire N'a Pas Fonctionné

**Tentatives effectuées**:
1. **Recherche de structures binaires** → 107,000+ faux positifs trouvés
2. **Filtres stricts appliqués** → 27,000+ faux positifs restants
3. **Analyse des données WIP** → Seulement 50 "portes" à (0,0,0), artefacts

**Conclusion**: Les portes dans Blaze & Blade ne sont **PAS stockées comme structures binaires simples** (x,y,z,type,key_id,etc.)

**Raisons probables**:
- Les portes sont des **scripts/events** attachés au level geometry
- Les données sont dans le **code overlay** chargé dynamiquement
- Les portes sont des **triggers de zone** (polygones invisibles)
- Les données sont **compilées** dans le code PS1

Les données textuelles (descriptions des clés, types de portes) sont fiables et ont été extraites.

---

## 📋 État Actuel de la Base de Données

### Données Disponibles

✅ **Structure complète** : 41 fichiers JSON créés
✅ **Types de portes** : 7 types identifiés et documentés
✅ **Clés/Amulettes** : 19 objets catalogués
✅ **Statistiques globales** : Nombre de portes par type dans tout le jeu
✅ **Guide d'exploration** : Checklist complète pour exploration in-game

### Données Manquantes (À Collecter In-Game)

❌ **Portes spécifiques par area** : Liste vide `"doors": []`
❌ **Positions exactes** : Coordonnées 3D
❌ **Destinations** : Où mène chaque porte
❌ **Correspondance clé-porte** : Quelle clé ouvre quelle porte exactement

---

## 🎯 Prochaines Étapes

### Option A: Exploration Manuelle (Recommandée)

1. **Lire le guide** : `Data/doors/EXPLORATION_GUIDE.md`
2. **Lancer le jeu** : Mode exploration
3. **Noter les portes** : Pour chaque area
   - Nombre de portes
   - Type (ouverte, verrouillée, magique, etc.)
   - Position approximative
   - Objet requis
   - Destination
4. **Remplir les JSON** : Éditer `Data/doors/[zone]/[area].json`
5. **Utiliser l'exemple** : `EXAMPLE_area_with_doors.json` comme modèle

### Option B: Utiliser un Émulateur avec Debug

1. **DuckStation/PCSX-Redux** : Émulateur avec debugger
2. **Breakpoints** : Sur les fonctions de portes (si identifiées)
3. **Memory watch** : Observer la RAM pendant les interactions
4. **Extraction** : Capturer les données lors du gameplay

### Option C: Reverse Engineering Avancé

1. **Disassembler les overlays** : Ghidra/IDA Pro
2. **Identifier les fonctions de portes** : Dans le code MIPS
3. **Tracer les appels** : Trouver où les portes sont initialisées
4. **Extraire les tables** : Si elles existent dans les overlays

---

## 📁 Fichiers à Consulter

### Pour Commencer
1. **`EXPLORATION_GUIDE.md`** ← **LIRE EN PREMIER**
2. **`EXAMPLE_area_with_doors.json`** ← Format à suivre
3. **`keys_reference.json`** ← Liste des clés

### Pour Référence
- **`SUMMARY.md`** : Vue d'ensemble complète
- **`door_types_reference.json`** : Types de portes
- **`zone_index.json`** : Index des zones

### Pour Remplir
- **`[zone]/[area].json`** : 41 fichiers à compléter

---

## 🔍 Informations Extraites de BLAZE.ALL

### Types de Portes Confirmés

| Type | Quantité | Objet Requis |
|------|----------|--------------|
| Magic Locked | 61 références | Magical Key |
| Demon Engraved | 3 références | Demon Amulet |
| Ghost Engraved | 2 références | Ghost Amulet |
| Key Locked | 131 références | Clés spécifiques |
| Generic/Unlocked | 138 références | Aucun |

### Zones avec Clés Connues

- **Castle of Vamp** : Golden Key, Cell Key
- **Tower** : Blue Key, Red Crystal
- **Hall of Demons** : Demon Amulet
- **Sealed Cave** : Ghost Amulet
- **Ancient Ruins** : Antique Key
- **Abandoned Mine** : Black Key (3rd Underlevel)

---

## 💡 Conseils

### Pour l'Exploration
- Sauvegardez souvent
- Prenez des screenshots des portes
- Notez les noms exacts affichés dans le jeu
- Testez chaque clé sur chaque porte
- Cartographiez si nécessaire

### Pour le Remplissage
- Utilisez le format de `EXAMPLE_area_with_doors.json`
- ID des portes : `door_001`, `door_002`, etc.
- Types : utiliser les valeurs de `door_types_reference.json`
- Position : approximative suffit si pas de coordonnées exactes
- Notes : toute information utile

---

## 📊 Statistiques Finales

```
Structure créée:
  ✓ 10 zones
  ✓ 41 areas
  ✓ 41 fichiers JSON (templates)
  ✓ 7 types de portes
  ✓ 19 clés/amulettes
  ✓ 6 fichiers de référence
  ✓ 1 guide d'exploration

Analyse BLAZE.ALL:
  ✓ 44.1 MB analysés
  ✓ 200+ références textuelles "door"
  ✓ 335 portes totales (types identifiés)
  ✓ 19 clés extraites

À faire:
  ✗ Exploration in-game des 41 areas
  ✗ Catalogage précis des portes par zone
  ✗ Correspondance clé-porte exacte
```

---

**Conclusion** : La base de données est **prête** et **structurée**. Les données textuelles de BLAZE.ALL ont été **extraites avec succès**. L'exploration in-game est maintenant nécessaire pour remplir les détails spécifiques de chaque porte par area.

**Fichier principal** : **`EXPLORATION_GUIDE.md`** → Commencez par là ! 🚀
