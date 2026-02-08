# Blaze & Blade - Gameplay Patch & Analysis

## Description

Analyse complete et outils de modification pour **Blaze & Blade: Eternal Quest** (PlayStation, 1998).

**Blaze & Blade: Eternal Quest**
- **Plateforme** : Sony PlayStation (PSX)
- **Annee** : 1998
- **Developpeur** : T&E Soft
- **Genre** : Action-RPG
- **Region** : Europe (PAL) - SLES_008.45

---

## Structure du projet

```
GameplayPatch/
├── build_gameplay_patch.bat       Script principal de build (10 steps)
├── patch_blaze_all.py             Injection de BLAZE.ALL dans le BIN
│
├── Data/
│   ├── formations/                Formation templates & spawn points
│   │   ├── editor.html            Editeur visuel (navigateur)
│   │   ├── patch_formations.py    Patcher formations + spawns
│   │   ├── FORMATION_CRASH_ANALYSIS.md
│   │   ├── cavern_of_death/       JSON par zone (69 fichiers)
│   │   ├── hall_of_demons/
│   │   └── ...
│   │
│   ├── LootTimer/                 Patch timer coffres (SLES)
│   │   ├── patch_loot_timer.py    Patcher (NOP 2 timers dans BIN)
│   │   └── RESEARCH.md            Documentation technique
│   │
│   ├── monster_stats/             Statistiques des monstres (124)
│   ├── items/                     Base de donnees items (424)
│   ├── fate_coin_shop/            Boutique Fate Coin (23 items)
│   ├── auction_prices/            Prix d'encheres
│   ├── spells/                    Sorts (90)
│   └── character_classes/         Classes de personnages (8)
│
└── WIP/level_design/              Level Design & Door Modding
    ├── spawns/                    Spawn groups & analysis
    ├── docs/                      Research documentation
    └── ...
```

---

## Quick Start

Double-cliquez sur `build_gameplay_patch.bat`

Le script execute dans l'ordre :
1. Copie BLAZE.ALL clean depuis extract vers output
2. Patch les prix Fate Coin Shop
3. Patch les descriptions d'items (376 items)
4. Met les prix d'encheres de base a 0
5. Patch les stats des monstres
6. Patch les spawn groups
6b. Patch les formation templates (compositions, tailles, nombre)
7. (reserve - loot timer patche au step 9b)
8. Copie le BIN clean vers output
9. Injecte BLAZE.ALL dans le BIN (2 emplacements)
9b. Patch le timer de disparition des coffres (SLES dans le BIN)
10. Met a jour la documentation

---

## Modules

### Formation Templates & Spawn Points

Systeme complet d'edition des formations de monstres (groupes aleatoires) et des spawn points (positions fixes).

**Editeur visuel** : `Data/formations/editor.html` — ouvrir dans un navigateur, charger un JSON, modifier, sauvegarder.

**Patcher** : `py -3 Data\formations\patch_formations.py`

**Fonctionnalites :**
- Changer la composition des formations (quels monstres dans chaque slot)
- Redimensionner les formations (redistribuer les records entre formations)
- Reduire le nombre de formations (via duplicate offsets + filler barriers)
- Patcher les spawn points en place (slot, coordonnees, byte0, area_id)
- Patcher les zone spawns en place
- Mise a jour automatique de la table d'offsets dans le script area

**69 fichiers JSON** couvrant 41 areas dans 9 donjons.

Voir `Data/formations/FORMATION_CRASH_ANALYSIS.md` pour les details techniques.

### Loot Chest Despawn Timer

Les coffres laches par les monstres ne disparaissent plus (duree originale : 20 secondes).

Le code de decrement est dans le **SLES executable** (pas BLAZE.ALL). Deux mecanismes de timer independants sont patches (NOP) :
1. Batch timer a entity+0x80 (48 halfword timers)
2. Despawn timer a entity+0x4C (countdown → kill entity)

Voir `Data/LootTimer/RESEARCH.md` pour les details techniques.

### Monster Stats (124 monstres)

- `normal_enemies/` : 101 monstres reguliers
- `boss/` : 23 boss
- 40 statistiques par monstre (int16/uint16)
- `patch_monster_stats.py` : patch directement BLAZE.ALL

### Items Database (424 items)

Base de donnees complete de tous les items extraits de BLAZE.ALL.
- `items/all_items_clean.json` : Base complete
- `items/patch_items_in_bin.py` : Patcher descriptions

### Fate Coin Shop (23 items)

- `fate_coin_shop.json` : Prix et items de la boutique
- `patch_fate_coin_shop.py` : Script de modification

### Spells (90 sorts)

Base de donnees complete : cout MP, puissance, element, type d'effet, cible.

### Level Design & Door Modding

- 100 chests avec items et quantites
- 150 enemy spawns avec randomness et zones
- 50 doors avec types, cles, destinations
- 2,500+ coordonnees 3D (5 zones)
- Unity 3D visualization
- Door modification system (presets)

---

## Prerequis

- Python 3.x
- `Blaze  Blade - Eternal Quest (Europe)/extract/BLAZE.ALL` (46 MB)
- `Blaze  Blade - Eternal Quest (Europe)/Blaze & Blade - Eternal Quest (Europe).bin` (703 MB)
- Emulateur PS1 pour tester

---

## Historique

- **2026-02-08** : Formation count decrease (duplicate offsets + filler barriers), loot chest timer patch, combat AI/loot system research
- **2026-02-06** : Formation size resize (offset table auto-update), slot_types extraction, spawn point patching
- **2026-02-04** : Level Design : 11 niveaux, 2500+ coordonnees 3D, 5 zones mappees
- **2026-02-04** : Items : Extraction complete de 424 items
- **2026-02-04** : Character classes : Zone memoire identifiee, 8 classes
- **2026-02-04** : Decouverte table prix encheres (0x002EA500)
- **2026-02-04** : Monster stats : 124 monstres organises
- **2026-02-03** : Fate Coin Shop : modification fonctionnelle
- **2026-02-03** : Extraction complete des 90 sorts
- **2026-02-03** : Identification structure binaire BLAZE.ALL

---

Repository maintenu par Ben Maurin (ben.maurin@gmail.com)

Cette analyse est fournie "as-is" a des fins de recherche et de preservation du patrimoine videoludique.

*Blaze & Blade: Eternal Quest (c) 1998 T&E Soft*

## Last Patch Build

**Date:** 2026-02-08 23:28:38

**Patches Applied:**
- Fate Coin Shop prices adjusted
- Items descriptions updated (376 items)
- Auction base prices set to 0
- Monster stats balanced
- Formation templates patched (69 areas)
- Loot chest timer disabled
- BLAZE.ALL integrated

**Source:** Blaze & Blade - Eternal Quest (Europe).bin
**Output:** output/Blaze & Blade - Patched.bin
