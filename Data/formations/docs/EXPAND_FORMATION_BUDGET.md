# Expansion du budget formations (A TESTER)

**Statut : Implementation terminee, en attente de test in-game**

## Principe

Chaque area a un budget fixe `formation_area_bytes` qui limite le nombre de
monstres dans les encounters. Les zone spawns ont souvent des milliers de
bytes libres en fin de region.

Le script `expand_formation_budget.py` deplace le gap + les donnees ZS vers
la droite dans cet espace libre, ce qui agrandit `formation_area_bytes` sans
changer la taille du fichier.

```
Avant:  [SCRIPT][SP][FM         ][gap][ZS_used ... ZS_free    ]
Apres:  [SCRIPT'][SP][FM ... +N  ][gap decale][ZS_used ...] (N bytes free en moins)
```

Les offsets dans les tables du script area (relatifs a script_start) qui
pointent au-dela de FM_end sont incrementes de N.

## Utilisation

### Dry-run (voir les changements sans rien modifier)

```
py -3 Data/formations/Scripts/expand_formation_budget.py
```

Ajouter `--verbose` pour voir le detail des tables d'offsets scannees.

### Appliquer les changements

```
py -3 Data/formations/Scripts/expand_formation_budget.py --apply
```

Cela modifie :
- `output/BLAZE.ALL` (shift binaire + patch offsets)
- Les JSON de chaque area expandee (formation_area_bytes, zone_spawns offsets, etc.)

### Pipeline build

Le script est integre dans `build_gameplay_patch.bat` en tant que **Step 6a**,
juste avant `patch_formations.py` (Step 6b). L'ordre est important :

1. Step 6a : expand_formation_budget.py (agrandit le budget dans le binaire ET les JSON)
2. Step 6b : patch_formations.py (lit les JSON mis a jour, remplit le budget elargi)

### Configuration

Dans le script, trois variables de configuration :

| Variable | Default | Description |
|----------|---------|-------------|
| `AREA_EXPANSIONS` | `{}` | Dict area_key -> bytes. Ex: `"cavern_of_death/floor_1_area_1": 360` |
| `DEFAULT_EXPANSION` | `None` | `None` = max dispo, un entier = N bytes fixe, `0` = skip sauf AREA_EXPANSIONS |
| `SAFETY_MARGIN` | `256` | Garde au moins N bytes libres dans la region ZS |

Exemple : tester sur une seule area :
```python
AREA_EXPANSIONS = {"cavern_of_death/floor_1_area_1": 360}
DEFAULT_EXPANSION = 0  # skip les autres
```

## Resultats dry-run (2026-03-22)

23 areas expandables sur 37 (10 overlap skippees, 4 sans frontiere).

| Donjon | Area | Gain budget | Gain slots | Offsets patches |
|--------|------|-------------|------------|-----------------|
| Ancient Ruins | Area 1 | +7,376 B | +230 | 112 |
| Castle of Vamp | Floor 2 A1 | +11,828 B | +369 | 270 |
| Castle of Vamp | Floor 3 A1 | +3,604 B | +112 | 80 |
| Castle of Vamp | Floor 3 A2 | +416 B | +13 | 38 |
| Castle of Vamp | Floor 5 A4 | +6,392 B | +199 | 187 |
| Cavern of Death | Floor 1 A1 | +5,728 B | +179 | 90 |
| Cavern of Death | Floor 1 A2 | +7,596 B | +237 | 140 |
| Cavern of Death | Floor 2 A1 | +9,524 B | +297 | 177 |
| Cavern of Death | Floor 3 A1 | +524 B | +16 | 4 |
| Cavern of Death | Floor 4 A1 | +192 B | +6 | 10 |
| Cavern of Death | Floor 5 A1 | +492 B | +15 | 29 |
| Cavern of Death | Floor 7 A2 | +2,052 B | +64 | 43 |
| Forest | Floor 1 A1 | +7,312 B | +228 | 194 |
| Forest | Floor 1 A4 | +10,248 B | +320 | 128 |
| Forest | Floor 2 A2 | +8,236 B | +257 | 170 |
| Hall of Demons | Area 3 | +5,440 B | +170 | 141 |
| Hall of Demons | Area 4 | +3,784 B | +118 | 76 |
| Hall of Demons | Area 8 | +7,112 B | +222 | 103 |
| Hall of Demons | Area 9 | +9,508 B | +297 | 202 |
| Tower | Area 2 | +7,524 B | +235 | 138 |
| Tower | Area 3 | +5,404 B | +168 | 7 |
| Tower | Area 6 | +4,776 B | +149 | 100 |
| Tower | Area 9 | +5,564 B | +174 | 93 |

**Total : +130,632 bytes, +4,079 slots potentiels**

## Areas skippees

### Overlap FM/ZS (10 areas)
Ces areas ont `formation_area_bytes` qui deborde dans la region zone_spawns.
Necessitent une analyse specifique.

- sealed_cave/area_8, area_6, area_7, area_2
- hall_of_demons/area_1, area_7
- castle_of_vamp/floor_5_area_1
- cavern_of_death/floor_7_area_3
- tower/area_8
- forest/floor_2_area_1

### Dernieres areas par donjon (4 areas)
Pas de frontiere connue (pas de next area pour calculer l'espace libre).

- ancient_ruins/area_2
- hall_of_demons/area_11
- tower/area_11
- undersea/area_2

## Comment ca marche (technique)

### Detection de script_start
Le script scanne depuis `group_offset` par pas de 96 bytes (taille d'une stat
entry) pour trouver le debut de la root table (petits uint32 < 0x10000).
Cela gere les areas avec des stat entries "cachees" non listees dans le JSON.

### Scan des offsets
1. **Root table** : premiers ~12 uint32 LE, termines par deux zeros consecutifs
2. **Sous-tables** : chaque root entry non-nulle pointe vers un bloc. Si le
   premier uint32 du bloc est < 0x10000, c'est une sous-table d'offsets.
   Sinon c'est un bloc bytecode/config (ignore).
3. Seuls les offsets >= `shift_point` (FM_end - script_start) sont patches.

### Validation post-expansion
Apres le shift, le script re-scanne les tables. Aucun offset ne doit pointer
dans la zone liberee [old_shift_point, new_shift_point).

## Plan de test

1. **Test minimal** : configurer `AREA_EXPANSIONS = {"cavern_of_death/floor_1_area_1": 360}`
   et `DEFAULT_EXPANSION = 0`. Builder, lancer le jeu, entrer dans Cavern F1 A1.
2. **Verifier** : combats normaux, zone spawns fonctionnels, pas de crash.
3. **Test elargi** : remettre `DEFAULT_EXPANSION = None`, builder, tester
   plusieurs donjons (Cavern, Forest, Tower).
4. **Si OK** : la feature est validee, les formations editees peuvent
   utiliser le budget elargi.
