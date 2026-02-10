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
├── build_gameplay_patch.bat       Script principal de build
├── patch_blaze_all.py             Injection de BLAZE.ALL dans le BIN
│
├── Data/
│   ├── formations/                Formation templates & spawn points
│   │   ├── editor.html            Editeur visuel (navigateur)
│   │   ├── patch_formations.py    Patcher formations + spawns
│   │   ├── FORMATIONS.md          Documentation du systeme
│   │   ├── AI_BEHAVIOR_RESEARCH.md   Notes de recherche AI
│   │   ├── AI_SPELL_SYSTEM.md     Architecture AI + sorts
│   │   ├── cavern_of_death/       JSON par zone (69 fichiers)
│   │   ├── hall_of_demons/
│   │   └── ...
│   │
│   ├── spells/                    Systeme de sorts
│   │   ├── spell_config.json      Config sorts (definitions)
│   │   ├── patch_spell_table.py   Patcher sorts (step 7b)
│   │   └── MONSTER_SPELLS.md      Documentation systeme de sorts
│   │
│   ├── monster_stats/             Statistiques des monstres (121)
│   │   ├── patch_monster_stats.py Patcher stats
│   │   ├── normal_enemies/        101 monstres reguliers (.json)
│   │   ├── boss/                  20 boss (.json)
│   │   └── scripts/               Outils (add_spell_info.py, etc.)
│   │
│   ├── LootTimer/                 Patch timer coffres
│   │   ├── patch_loot_timer.py    Patcher (NOP decrements dans overlay)
│   │   ├── loot_timer.json        Configuration
│   │   └── RESEARCH.md            Documentation technique
│   │
│   ├── trap_damage/               Patch degats pieges/environnement
│   │   ├── patch_trap_damage.py   Patcher (110 sites dans overlay)
│   │   ├── trap_damage_config.json  Configuration (par valeur %)
│   │   └── RESEARCH.md            Documentation technique
│   │
│   ├── ai_behavior/               Config AI & overlay bitfield
│   │   ├── patch_ai_behavior.py   Patcher comportement AI (experimental, desactive)
│   │   ├── ai_behavior_config.json  Tests AI (tous desactives)
│   │   ├── patch_monster_spells.py  Patcher bitfield sorts (step 7e)
│   │   └── overlay_bitfield_config.json  Config quels sorts les monstres ont
│   │
│   ├── items/                     Base de donnees items (424)
│   ├── fate_coin_shop/            Boutique Fate Coin (23 items)
│   └── auction_prices/            Prix d'encheres
│
└── WIP/                           Recherche en cours
    ├── spells/                    Recherche systeme de sorts
    └── level_design/              Level Design & Door Modding
```

---

## Quick Start

Double-cliquez sur `build_gameplay_patch.bat`

Le script execute dans l'ordre :

| Step | Script | Description |
|------|--------|-------------|
| 1 | (copy) | Copie BLAZE.ALL clean depuis extract vers output |
| 2 | `patch_fate_coin_shop.py` | Patch les prix Fate Coin Shop |
| 3 | `patch_items_in_bin.py` | Patch les descriptions d'items (376 items) |
| 4 | `patch_auction_base_prices.py` | Met les prix d'encheres de base a 0 |
| 5 | `patch_monster_stats.py` | Patch les stats des monstres |
| 6 | `patch_spawn_groups.py` | Patch les spawns de monstres |
| 6b | `patch_formations.py` | Patch les formation templates |
| 7 | `patch_loot_timer.py` | Gele le timer des coffres (optionnel) |
| 7b | `patch_spell_table.py` | Modifie les stats des sorts (degats, MP, element) |
| 7c | `patch_ai_behavior.py` | Patch comportement AI (experimental) |
| 7d | `patch_trap_damage.py` | Modifie les degats des pieges (110 sites) |
| 7e | `patch_monster_spells.py` | Modifie quels sorts offensifs les monstres ont (ai_behavior/) |
| 8 | (copy) | Copie le BIN clean vers output |
| 9 | `patch_blaze_all.py` | Injecte BLAZE.ALL dans le BIN (2 emplacements) |
| 10 | (inline) | Met a jour la documentation |

Steps 1-7e patchent `output/BLAZE.ALL`. Steps 8-9 creent le BIN final.

---

## Modules

### Monster Spells & Abilities

Systeme complet pour modifier les sorts et capacites des monstres.

**Documentation** : `Data/spells/MONSTER_SPELLS.md`
**Config sorts** : `Data/spells/spell_config.json` (definitions: degats, MP, element, cast_time)
**Config bitfield** : `Data/ai_behavior/overlay_bitfield_config.json` (quels sorts les monstres ont)

Deux systemes distincts :
- **Sorts offensifs** (FireBullet, Blaze, etc.) : controlables via `overlay_bitfield_config.json` (zone-wide)
- **Capacites monstres** (Fire Breath, Drain, etc.) : stats modifiables, mais pas l'assignation par monstre

Voir `MONSTER_SPELLS.md` pour la reference complete des 29 sorts + 30 capacites.

### Formation Templates & Spawn Points

Systeme complet d'edition des formations de monstres et des spawn points.

**Editeur visuel** : `Data/formations/editor.html`
**Patcher** : `Data/formations/patch_formations.py`
**Documentation** : `Data/formations/FORMATIONS.md`

69 fichiers JSON couvrant 41 areas dans 9 donjons.

### Loot Chest Despawn Timer

Les coffres laches par les monstres ne disparaissent plus (duree originale : 20 secondes).

**Config** : `Data/LootTimer/loot_timer.json`
**Documentation** : `Data/LootTimer/RESEARCH.md`

Le patcher detecte et NOP les 35 patterns de decrementation dans le code overlay
(v6 avec validation de contexte pour eviter les faux positifs).

### Trap/Environmental Damage

Modifie les degats des pieges et effets environnementaux (chutes de pierres, pieges lourds).

**Config** : `Data/trap_damage/trap_damage_config.json`
**Documentation** : `Data/trap_damage/RESEARCH.md`

110 sites patches (15 appels JAL directs + 95 initialisations GPE entity) dans 28 overlays.

### AI Behavior (experimental)

Tests de modification du comportement AI via les blocs de donnees du script area.

**Status** : Tous les tests sont desactives. La recherche a montre que les blocs
cibles sont en fait des parametres de zone/camera (pas du comportement AI).
Le veritable mecanisme de comportement AI n'est pas encore decode.

Voir `Data/formations/AI_BEHAVIOR_RESEARCH.md` pour les resultats de recherche.

### Monster Stats (121 monstres)

- `normal_enemies/` : 101 monstres reguliers
- `boss/` : 20 boss
- Chaque JSON contient les stats + `spell_info` (type de lanceur, sorts disponibles)
- `patch_monster_stats.py` : patch directement BLAZE.ALL

### Items Database (424 items)

Base de donnees complete de tous les items extraits de BLAZE.ALL.
- `items/all_items_clean.json` : Base complete
- `items/patch_items_in_bin.py` : Patcher descriptions

### Fate Coin Shop (23 items)

- `fate_coin_shop.json` : Prix et items de la boutique
- `patch_fate_coin_shop.py` : Script de modification

---

## Prerequis

- Python 3.x
- `Blaze  Blade - Eternal Quest (Europe)/extract/BLAZE.ALL` (46 MB)
- `Blaze  Blade - Eternal Quest (Europe)/Blaze & Blade - Eternal Quest (Europe).bin` (703 MB)
- Emulateur PS1 pour tester

---

## Historique

- **2026-02-10** : Systeme de sorts monstres (patchers, config, docs, spell_info 121 JSONs), degats pieges v4, loot timer v6, recherche AI
- **2026-02-08** : Formation count decrease, loot chest timer patch, combat AI research
- **2026-02-06** : Formation size resize, slot_types extraction, spawn point patching
- **2026-02-04** : Level Design, Items extraction, Character classes, Monster stats
- **2026-02-03** : Fate Coin Shop, Extraction des 90 sorts, Structure binaire BLAZE.ALL

---

Repository maintenu par Ben Maurin (ben.maurin@gmail.com)

Cette analyse est fournie "as-is" a des fins de recherche et de preservation du patrimoine videoludique.

*Blaze & Blade: Eternal Quest (c) 1998 T&E Soft*









## Last Patch Build

**Date:** 2026-02-10 20:00:51

**Patches Applied:**
- Fate Coin Shop prices adjusted
- Items descriptions updated (376 items)
- Auction base prices set to 0
- Monster stats balanced
- BLAZE.ALL integrated

**Source:** Blaze & Blade - Eternal Quest (Europe).bin
**Output:** output/Blaze & Blade - Patched.bin

