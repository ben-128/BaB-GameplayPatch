# Formation Space Investigation (2026-03-21)

## Objectif

Trouver de l'espace supplémentaire pour les formations en récupérant des bytes
depuis les zone spawns ou les spawn points.

## Contexte

Chaque area a un budget fixe `formation_area_bytes`. La formule :
```
32 * total_slots + 4 * num_formations = formation_area_bytes
```
Ce budget limite le nombre total de monstres dans les formations.

## Layout mémoire par area

```
[STATS 96B*N] [SCRIPT/OFFSET TABLE] [SPAWN POINTS] [FORMATIONS] [gap] [ZONE SPAWNS]
```

- SP → FM : souvent **0 bytes** de gap (63% des areas, adjacents)
- FM → ZS : toujours un **gap de 172 à 3268 bytes**

## Piste 1 : Récupérer l'espace dans le gap FM→ZS

### Résultat : IMPASSE

Le gap entre formations et zone spawns (22,028 bytes au total sur 27 areas)
est **entièrement occupé par des données structurées** :

- Commence par `00000000 FFFFFFFF` (même pattern que les records)
- Dense en marqueurs `FFFFFFFF` et terminateurs `FFFFFFFFFFFF`
- Ratio non-zero : 35-50% (densité typique de records valides)
- **Trailing zeros récupérables : 6 bytes au total** (négligeable)

Ce n'est PAS du padding — c'est probablement des spawn points ou de la
configuration de zone que l'extracteur ne capture pas dans les JSON.

### Détail par donjon

| Donjon           | Areas | Gap total | Récupérable |
|------------------|-------|-----------|-------------|
| ancient_ruins    | 2     | 908 B     | 2 B         |
| castle_of_vamp   | 4     | 2,216 B   | 2 B         |
| cavern_of_death  | 7     | 6,732 B   | 0 B         |
| forest           | 3     | 3,708 B   | 0 B         |
| hall_of_demons   | 5     | 3,376 B   | 0 B         |
| tower            | 5     | 4,756 B   | 0 B         |
| undersea         | 1     | 332 B     | 2 B         |

### 10 areas avec chevauchement (FM > ZS start)

Certaines areas ont `formation_area_bytes` qui s'étend AU-DELA de
`zone_spawns_area_start` — les deux régions se chevauchent :

- sealed_cave/area_8 : 2,660 B overlap
- hall_of_demons/area_1 : 2,312 B overlap
- sealed_cave/area_6 : 2,160 B overlap
- hall_of_demons/area_7 : 1,364 B overlap
- sealed_cave/area_7 : 1,356 B overlap
- sealed_cave/area_2 : 1,192 B overlap
- castle_of_vamp/floor_5_area_1 : 728 B overlap
- cavern_of_death/floor_7_area_3 : 660 B overlap
- tower/area_8 : 468 B overlap
- forest/floor_2_area_1 : 268 B overlap

## Piste 2 : Compacter les Spawn Points

### Résultat : IMPASSE

SP et FM sont adjacents (0-gap) dans 63% des areas. En théorie, réduire
la région SP permettrait de déplacer FM_start plus tôt.

Mais :

1. **L'espace SP est déjà 100% utilisé** — pas de padding interne
2. **L'extracteur rate des groupes SP** — le gap entre SP et FM contient
   en fait des SP groups "cachés" (confirmé par les offset tables)
   - Hall of Demons A1 : 14 SP groups dans la table, 11 dans le JSON
   - Sealed Cave A2 : 33 entrées table vs 11 JSON
   - Castle of Vamp F5A4 : 61 vs 41
3. **Seules 2 areas ont de l'espace récupérable** :
   - Castle of Vamp F2A1 : 32 bytes (1 record)
   - Tower A8 : 32 bytes (1 record)
4. **Total récupérable : 64 bytes** (pas exploitable)

### FM_start est piloté par la offset table

Le moteur localise les formations via des offsets dans la table du script area :
```
[header, 0, SP_off_0, SP_off_1, ..., FM_off_0, FM_off_1, ..., 0, 0]
```

FM_start n'est pas hardcodé — il est calculé par le moteur depuis la table.
En principe, modifier ces offsets permettrait de déplacer FM_start. Mais il
faut d'abord avoir de l'espace libre, ce qui n'est pas le cas.

## Alternative : Supprimer des Spawn Points

La seule option viable pour gagner de l'espace formation serait de
**supprimer délibérément des groupes de spawn points** :

- Chaque SP group = 32-132 bytes libérés
- Il faudrait aussi mettre à jour la offset table
- Impact gameplay : moins de points d'apparition fixes pour les monstres

C'est un trade-off : on perd des spawn locations pour gagner des
formation slots.

## Alternative : Merger des formations

Sans toucher au layout binaire, on peut mieux utiliser le budget existant :

- Fusionner 2 formations de 3 slots en 1 formation de 6 slots
- Économise 1 suffix (4 bytes) + 1 filler entry par merge
- Le gain est modeste mais ne casse rien

## Piste 3 : Décaler gap + ZS records dans l'espace libre ZS

### Idée

Les zone spawns ont souvent des milliers de bytes libres en fin de région.
Si on décale le gap data + les ZS records vers la droite de N bytes, les
formations gagnent N bytes :

```
Avant:  [SP][FM         ][gap][ZS_records ... ZS_free_space     ]
Après:  [SP][FM ... +N bytes ][gap décalé][ZS_records ... moins libre]
```

### Espace libre ZS disponible (top areas)

| Area                     | FM actuel | ZS libre | Gain théorique |
|--------------------------|-----------|----------|----------------|
| forest/floor_2_area_1    | 232 B     | 20,312 B | +626 slots     |
| hall_of_demons/area_11   | 336 B     | 18,456 B | +614 slots     |
| forest/floor_2_area_2    | 664 B     | 8,984 B  | +317 slots     |
| sealed_cave/area_6       | 396 B     | 8,680 B  | +271 slots     |
| castle_of_vamp/floor_5_area_1 | 332 B | 7,884 B | +246 slots    |
| tower/area_2             | 304 B     | 5,940 B  | +227 slots     |

35 areas sur 41 ont un potentiel d'expansion théorique.
Total théorique : ~138,860 bytes (4,339 slots).

### Résultat : NON FAISABLE (sans désassembleur de script)

**Le gap et les ZS records sont référencés par des offsets dans le bytecode
du script area.** Ces références sont le BLOCKER principal :

1. **Le gap contient 3 types de données** :
   - Config de spawn additionnelle (~40 bytes, pas des records 32B)
   - Sous-table de pointeurs/offsets (paires uint16 offset + uint16 flags)
   - Records spawn valides (byte9=0x0B ou 0xFF) non capturés par l'extracteur

2. **Le script bytecode référence ces positions par offset absolu** :
   - Ex: tower/area_2 → TABLE[41]=3072 pointe dans le gap
   - Ex: cavern/floor_7_area_2 → **24 références** dans le gap
   - Ex: hall_of_demons/area_11 → 8 références dans le gap
   - Ces offsets sont dispersés dans le bytecode, pas dans une table structurée

3. **Les ZS records sont aussi référencés par le bytecode** :
   - Chaque area a des dizaines de TABLE entries pointant dans la zone ZS
   - Le moteur utilise ET le scan (terminateurs FFFFFF) ET des offsets bytecode
   - `patch_placed_records()` patche les ZS in-place via offsets absolus

4. **Déplacer quoi que ce soit casserait le scripting de l'area** :
   - Trouver tous les offsets nécessite un désassembleur complet du bytecode
   - Le format du bytecode n'est pas documenté
   - Risque de crashs ou monstres invisibles

### Ce qu'il faudrait pour que ça marche

1. Reverse-engineer le format complet du script bytecode
2. Écrire un désassembleur capable de trouver TOUS les offsets
3. Incrémenter chaque offset de N bytes (le shift)
4. Réécrire le bytecode modifié
5. Déplacer gap data + ZS records de N bytes vers la droite
6. Étendre formation_area_bytes de N bytes

C'est un projet de reverse-engineering majeur, pas un simple patch.

## Conclusion

**L'espace est saturé et verrouillé par le bytecode.** Les zone spawns ont
bien de l'espace libre (jusqu'à 20 KB par area), mais cet espace ne peut
pas être redistribué aux formations sans reverse-engineer le format complet
du script bytecode qui référence les positions par offsets absolus.

Les seules pistes pour augmenter le budget formations sont :
1. Supprimer des spawn points (trade-off gameplay)
2. Merger des formations existantes (gain modeste, ~4 bytes par merge)
3. Reverse-engineer le script bytecode (projet majeur mais gain massif)
4. Slot expansion N=3→N=4 (déjà implémenté, en attente de test)
