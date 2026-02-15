# Debug Guide: Monster Slots Crash

## Problème
Le jeu crash au chargement de Cavern F1 A1 après ajout de 2 monster slots (3 → 5).

## Ce qui a été tenté
1. ✅ Zone reorganisée (anim tables, records, assignments, stats)
2. ✅ 4 offsets hardcodés mis à jour
3. ✅ Middle section agrandie (44 → 48 bytes)
4. ❌ Plusieurs patches du monster count (0xF7A851, 0xF7A94D, etc.)
5. ❌ Structure comparée avec Forest F1 A2 (5 monsters vanilla)

## Hypothèses
- Le crash se produit AVANT que les spawns se déclenchent
- Le jeu lit probablement un header/count quelque part et trouve une incohérence
- La middle section contient des données critiques dont on ne comprend pas la structure

## Solution: Debug avec DuckStation

### Étape 1: Lancer avec console debug

1. Ouvrir DuckStation
2. Charger le BIN patché
3. Ouvrir la console debug (View → Debug Console)
4. Charger une sauvegarde juste avant Cavern F1

### Étape 2: Breakpoints critiques

```
# Break sur chargement de zone
break 0x800XXXXX  # À déterminer - fonction de load area

# Break sur lecture de monster count
# Chercher les lectures autour de 0xF7A851 (candidat monster count header)
watch r 0x800YYYYY

# Break sur crash (si on peut l'identifier)
```

### Étape 3: Identifier la cause

1. **Step through** le code de chargement de l'area
2. **Observer** quelles données sont lues depuis BLAZE.ALL
3. **Noter** où le crash se produit exactement
4. **Identifier** quel registre/variable contient le monster count

### Étape 4: Trouver tous les monster count

Une fois qu'on sait comment le jeu lit le count:
1. Chercher TOUTES les occurrences de ce pattern dans BLAZE.ALL
2. Patcher systématiquement 3 → 5
3. Retester

## Information utile pour le debug

**Offsets Cavern F1 A1:**
- Animation header: 0xF7A900
- Monster count candidat: 0xF7A851  (175 bytes avant anim)
- Stats start: 0xF7A9AC (après reorganisation)
- Script start: 0xF7AB8C
- Formation start: 0xF7B0EC

**Taille des sections (5 monsters):**
- Anim header: 8 bytes
- Anim tables: 40 bytes (5×8)
- Anim records: 40 bytes (5×8)
- Middle section: 48 bytes ← **CRITIQUE mais contenu inconnu**
- Assignments: 40 bytes (5×8)
- Stats: 480 bytes (5×96)

**Middle section pattern (Forest vs Cavern):**
- Forest (vanilla 5m): `000000002c000000340000003c00000044000000...`
- Cavern (modifié 5m): `000003001400000000000000004004001c000000...`
- **COMPLÈTEMENT DIFFÉRENTS** - c'est probablement ici que le problème se trouve!

## Next Steps

1. User: Lance DuckStation avec debug
2. User: Identifie où le crash se produit
3. User: Rapporte l'adresse RAM + registres + contexte
4. Claude: Analyse et trouve la solution finale

## Alternative si debug impossible

Si le debugging en direct est impossible, on peut:
1. Comparer systématiquement TOUTES les données entre Forest (5m vanilla) et Cavern (3m vanilla)
2. Identifier TOUTES les différences
3. Adapter chaque différence pour passer de 3m à 5m
4. Tester itérativement

Mais cette approche est beaucoup plus lente et risquée.
