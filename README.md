# Blaze & Blade - Gameplay Patch & Analysis

## 📖 Description

Ce repository contient une analyse complète et des outils de modification pour le jeu **Blaze & Blade: Eternal Quest** (PlayStation, 1998).

## 🎮 À propos du jeu

**Blaze & Blade: Eternal Quest**
- **Plateforme** : Sony PlayStation (PSX)
- **Année** : 1998
- **Développeur** : T&E Soft
- **Genre** : Action-RPG
- **Région** : Europe (PAL) - SLES_008.45

---

## 📊 Structure du projet

```
GameplayPatch/
├── build_gameplay_patch.bat    ⭐ Script principal de build
├── patch_blaze_all.py          Injection de BLAZE.ALL dans le BIN
├── work/                       Fichiers de travail
│   ├── BLAZE.ALL               Données du jeu (46 MB)
│   └── Blaze & Blade - Patched.bin  Image disque patchée
│
├── monster_stats/              🐉 Statistiques des monstres (124 monstres)
│   ├── normal_enemies/         101 monstres normaux
│   ├── boss/                   23 boss
│   ├── _index.json             Index complet
│   ├── patch_monster_stats_bin.py  Patcher de stats
│   └── update_index.py         Mise à jour de l'index
│
├── items/                      🎒 Base de données des items (291 items)
│   ├── all_items_clean.json    Base complète des items authentiques
│   ├── extract_with_faq_reference.py  Extracteur avec FAQ référence
│   ├── Blaze objets.txt        FAQ GameFAQs (référence 346 items)
│   └── README.md               Documentation
│
├── fate_coin_shop/             💰 Boutique Fate Coin
│   ├── fate_coin_shop.json     Données de la boutique (23 items)
│   └── patch_fate_coin_shop.py Script de modification
│
├── auction_prices/             🏛️ Prix d'enchères (EN COURS)
│   ├── test_auction_prices.bat Test des modifications
│   ├── test_modify_16bit_prices.py  Modification des prix
│   ├── restore_original.bat    Restauration
│   └── AUCTION_PRICE_SOLUTION.md  Documentation technique
│
├── spells/                     ✨ Base de données des sorts (90 sorts)
│   ├── *.json                  Fichiers individuels par sort
│   ├── INDEX.json              Vue d'ensemble
│   └── README.md               Documentation
│
├── character_classes/          🎭 Statistiques des classes (EN RECHERCHE)
│   ├── *.json                  Templates par classe (8 classes)
│   ├── _index.json             Index des classes
│   ├── explore_class_stats.py  Analyse de la zone mémoire
│   ├── DISCOVERY_REPORT.md     Découvertes détaillées
│   └── RESEARCH_GUIDE.md       Guide de recherche
│
└── level_design/               🗺️ Level Design Analysis & Door Modding
    ├── Data Extraction
    │   ├── 100 chests with items/quantities (JSON + CSV)
    │   ├── 150 enemy spawns with randomness (JSON + CSV)
    │   ├── 50 doors with types/keys/destinations (JSON + CSV)
    │   └── 2,500+ 3D coordinates from 5 zones (CSV)
    ├── Door Modification System
    │   ├── patch_doors.py - Binary patching system
    │   ├── *.bat - Automation scripts (unlock, remove keys, etc.)
    │   └── door_presets/ - Preset configurations
    ├── Unity Visualization
    │   ├── CompleteVisualizationV2.cs - Main script
    │   └── 3D display of geometry, chests, spawns, doors
    └── README.md - Complete documentation

```

---

## 🚀 Quick Start

### Option 1: Build complet (recommandé)

Double-cliquez sur `build_gameplay_patch.bat`

Ce script va :
1. Patcher les prix de la boutique Fate Coin
2. Injecter BLAZE.ALL dans le BIN
3. Patcher les statistiques des monstres

### Option 2: Modification spécifique

- **Monster stats** : `py -3 monster_stats\patch_monster_stats_bin.py`
- **Fate Coin Shop** : `py -3 fate_coin_shop\patch_fate_coin_shop.py`
- **Auction prices** : `cd auction_prices && test_auction_prices.bat`
- **Door modding** : `cd level_design && unlock_all_doors.bat` (ou autres presets)

---

## 📁 Modules détaillés

### 🐉 Monster Stats (124 monstres)

**Organisation :**
- `normal_enemies/` : 101 monstres réguliers
- `boss/` : 23 boss

**Structure des données :**
- 40 statistiques par monstre (int16/uint16)
- HP, EXP, Dégâts, Armure, Éléments, etc.

**Fichiers :**
- `_index.json` : Index complet avec tous les monstres
- `patch_monster_stats_bin.py` : Patch directement le BIN
- `update_index.py` : Régénère l'index

**Utilisation :**
```python
import json

# Charger un monstre
with open('monster_stats/boss/Red-Dragon.json', 'r') as f:
    dragon = json.load(f)

# Modifier HP
dragon['stats']['hp'] = 9999
with open('monster_stats/boss/Red-Dragon.json', 'w') as f:
    json.dump(dragon, f, indent=2)

# Appliquer au jeu
# py -3 monster_stats\patch_monster_stats_bin.py
```

---

### 🎒 Items Database (424 items)

**Base de données complète** de tous les items du jeu extraits de BLAZE.ALL :
- Armes : épées, haches, arcs, bâtons, etc.
- Armures : armures lourdes, robes, vêtements
- Boucliers et casques
- Accessoires : anneaux, amulettes, bottes, gants
- Consommables : potions, élixirs, poudres
- Matériaux magiques
- Objets de quête

**Structure des données :**
- Nom de l'item
- Description (quand disponible)
- Offset dans BLAZE.ALL
- Statistiques binaires (valeurs uint16)
- Catégorie (Weapons, Armor, Consumables, etc.)
- Nombre d'occurrences dans le jeu

**Fichiers :**
- `items/all_items_clean.json` : Base complète (424 items)
- `items/extract_complete_database.py` : Extracteur
- `items/README.md` : Documentation complète

**Exemples d'items :**
```json
{
  "name": "Healing Potion",
  "description": "Common potion.(Restores HP to single unit)",
  "offset": "0x006C6F80",
  "category": "Consumables",
  "stats": {
    "0x10": 5,
    "0x12": 37119
  }
}
```

**Usage :**
```python
import json
with open('items/all_items_clean.json', 'r') as f:
    data = json.load(f)
    weapons = [i for i in data['items'] if i['category'] == 'Weapons']
```

---

### 💰 Fate Coin Shop (23 items)

**Location dans BLAZE.ALL :** 10 copies aux offsets :
- 0x00B1443C, 0x00B14C3C, 0x00B1EC24, etc.

**Fichiers :**
- `fate_coin_shop.json` : Prix et items de la boutique
- `patch_fate_coin_shop.py` : Script de modification

**Modification des prix :**
```json
{
  "items": [
    {
      "index": 0,
      "price": 0,           ← Modifier ici (0-255)
      "default_price": 1,
      "item": "Rope of Return"
    }
  ]
}
```

Puis : `py -3 fate_coin_shop\patch_fate_coin_shop.py`

---

### 🏛️ Auction Prices (EN RECHERCHE)

**Statut :** Solution trouvée mais nécessite test in-game

**Location découverte :** `0x002EA500` dans BLAZE.ALL
**Format :** Mots 16-bit little-endian

**Prix confirmés :**
- Word[0] = 10 (Healing Potion)
- Word[2] = 22 (Shortsword)
- Word[13] = 36 (Leather Armor)

**Test :**
```bash
cd auction_prices
test_auction_prices.bat
```

Voir `auction_prices/AUCTION_PRICE_SOLUTION.md` pour détails complets.

---

### ✨ Spells (90 sorts)

**Base de données complète** de tous les sorts du jeu :
- Coût en MP
- Puissance/Dégâts
- Élément (Neutre, Feu, Glace, Foudre, Sacré)
- Type d'effet (Damage, AOE, Buff)
- Cible (Single, Group, All)

Voir `spells/README.md` pour documentation complète.

---

### 🎭 Character Classes (EN RECHERCHE)

**Statut :** Structure identifiée, tests in-game requis

**8 classes découvertes** avec versions Male/Female :
- Warrior, Priest, Rogue, Sorcerer, Hunter, Elf, Dwarf, Fairy

**Zone mémoire :** `0x0090B6E8 - 0x0090B7BC` dans BLAZE.ALL
**Pattern trouvé :** `0B 01 D9 00` après chaque nom de classe

**Données manquantes :**
- Stats de base (HP, MP, Strength, Defense, etc.)
- Progression par niveau
- Mapping avec les 7 listes de sorts

**Fichiers :**
- Templates JSON pour chaque classe
- Scripts d'analyse mémoire
- Guide de recherche complet

Voir `character_classes/RESEARCH_GUIDE.md` pour participer à la recherche.

---

### 🗺️ Level Design Analysis & Door Modding

**Système complet d'extraction et modification des niveaux**

**Données extraites :**
- **100 chests** avec items et quantités (JSON + CSV)
- **150 enemy spawns** avec randomness et zones (JSON + CSV)
- **50 doors** avec types, clés, destinations (JSON + CSV)
- **2,500+ coordonnées 3D** de géométrie de niveaux (5 zones CSV)

**🚪 Door Modification System (NOUVEAU)**

Système de modification binaire avec backup automatique :
```batch
cd level_design

# Débloquer toutes les portes
unlock_all_doors.bat

# Enlever les clés requises
remove_keys.bat

# Verrouiller les portes (test)
lock_all_doors_test.bat
```

**Types de portes modifiables :**
- 0 = UNLOCKED (toujours ouverte)
- 1 = KEY_LOCKED (nécessite clé)
- 2 = MAGIC_LOCKED (sort magique)
- 3-7 = Autres types (demon, ghost, event, boss, one-way)

**🎮 Unity Visualization**

Script complet pour visualiser les niveaux en 3D :
- Géométrie des niveaux (coordonnées 3D)
- Chests (cubes jaunes) avec labels d'items
- Enemy spawns (sphères rouges/magenta) avec stats
- Doors (cylindres bleus) avec conditions d'ouverture

Usage :
1. Créer projet Unity 3D
2. Copier les CSV dans `Assets/Data/`
3. Ajouter `CompleteVisualizationV2.cs` à un GameObject
4. Play!

**Scripts d'analyse :**
- `analyze_chests.py` : Extraction des coffres
- `analyze_enemy_spawns.py` : Extraction des spawns
- `analyze_doors.py` : Extraction des portes
- `patch_doors.py` : Modification des portes (binary patching)
- `export_coordinates.py` : Export coordonnées 3D
- `generate_door_presets.py` : Génération de presets

**Fichiers de configuration :**
- `door_modifications.json` : Vos modifications personnalisées
- `door_presets/*.json` : Presets prêts à l'emploi

**Documentation :**
- `level_design/README.md` : Documentation principale
- `DOOR_MODDING_QUICKSTART.md` : Guide rapide (5 min)
- `DOOR_PATCHING_GUIDE.md` : Guide complet
- `unity/COMPLETE_VISUALIZATION_GUIDE.md` : Guide Unity

---

## 🔬 Méthodologie

Toutes les données ont été extraites par **reverse engineering** du fichier `BLAZE.ALL` (46 MB) :

1. Analyse de la structure binaire
2. Identification des patterns répétitifs
3. Validation avec les valeurs connues du jeu
4. Création d'outils de modification
5. Tests in-game

---

## 🛠️ Build Process

Le script `build_gameplay_patch.bat` exécute dans l'ordre :

1. **Fate Coin Shop** → `fate_coin_shop\patch_fate_coin_shop.py`
   - Lit `fate_coin_shop.json`
   - Patch `work\BLAZE.ALL`

2. **BLAZE.ALL injection** → `patch_blaze_all.py`
   - Inject `work\BLAZE.ALL` dans `work\Blaze & Blade - Patched.bin`
   - Patch les 2 copies (LBA 163167 et 185765)

3. **Monster Stats** → `monster_stats\patch_monster_stats_bin.py`
   - Lit tous les JSON dans `monster_stats/`
   - Patch directement le BIN
   - Trouve automatiquement toutes les occurrences de chaque monstre

---

## 📈 Statistiques

- **Items** : 424 (armes, armures, consommables, etc.)
- **Monstres** : 124 (101 normaux + 23 boss)
- **Sorts** : 90
- **Items Fate Coin** : 23
- **Classes de personnages** : 8 (+ versions M/F)
- **Auction Prices** : 8 confirmés (recherche en cours)
- **Chests extraits** : 100 (avec items et quantités)
- **Enemy Spawns** : 150 (avec randomness et zones)
- **Doors modifiables** : 50 (types, clés, destinations)
- **Coordonnées 3D extraites** : 2,500+ points (5 zones)
- **Door Presets** : 3 configurations prêtes à l'emploi

---

## 🎯 Applications

- **Modding** : Modification complète du gameplay
- **Balance patches** : Rééquilibrage des difficultés
- **Documentation** : Guides complets du jeu
- **Traduction** : Base pour localisation
- **Analyse** : Étude du game design

---

## ⚠️ Prérequis

- Python 3.x
- `work\BLAZE.ALL` (46 MB)
- `work\Blaze & Blade - Patched.bin` (703 MB)
- Émulateur PS1 pour tester

---

## 📅 Historique

- **2026-02-04** : **Level Design** : 11 niveaux identifiés, 2500+ coordonnées 3D extraites, 5 zones mappées
- **2026-02-04** : **Items** : Extraction complète de 424 items du jeu
- **2026-02-04** : Character classes : Zone mémoire identifiée, 8 classes découvertes
- **2026-02-04** : Organisation en sous-dossiers modulaires
- **2026-02-04** : Découverte table prix enchères (0x002EA500)
- **2026-02-04** : Monster stats : 124 monstres organisés
- **2026-02-03** : Fate Coin Shop : modification fonctionnelle
- **2026-02-03** : Extraction complète des 90 sorts
- **2026-02-03** : Identification structure binaire BLAZE.ALL

---

## 📧 Contact

Repository maintenu par Ben Maurin (ben.maurin@gmail.com)

## 📜 Licence

Cette analyse est fournie "as-is" à des fins de recherche et de préservation du patrimoine vidéoludique.

---

*Blaze & Blade: Eternal Quest © 1998 T&E Soft*









## Last Patch Build

**Date:** 2026-02-05 14:03:00

**Patches Applied:**
- Fate Coin Shop prices adjusted
- Items descriptions updated (376 items)
- Monster stats balanced
- BLAZE.ALL integrated

**Source:** Blaze & Blade - Eternal Quest (Europe).bin
**Output:** output/Blaze & Blade - Patched.bin

