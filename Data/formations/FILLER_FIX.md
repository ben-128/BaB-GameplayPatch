# Fix: Fillers Synthétiques au lieu de Vanilla Round-Robin

## Problème découvert

**Erreur lors de l'injection:** "BLAZE.ALL size (46206896) not multiple of 2048"
- Fichier trop petit de 80 bytes
- BLAZE.ALL doit être un multiple de 2048 (secteur CD)

## Cause

Les fillers étaient créés en copiant les **vanilla bytes en round-robin**, qui sont trop gros:
- Formations custom: 716 bytes (F0: 228B, F1: 260B, F2: 228B)
- Remaining: 896 - 716 = 180 bytes
- Filler 0 (vanilla F0): 100 bytes ✓ ajouté
- Filler 1 (vanilla F1): 100 bytes ✗ ne rentre pas (100+100 > 180)
- Résultat: seulement 100 bytes de fillers, **80 bytes manquants!**

## Solution

Retour à la stratégie originale: **fillers synthétiques de 1 record**
- Chaque filler: 1 record (32 bytes) + suffix (4 bytes) = 36 bytes minimum
- 5 fillers: 5 * 36 = 180 bytes
- **Rentre toujours dans l'espace disponible!**

## Code corrigé

### Avant (vanilla round-robin)
```python
# Strategy 1: Use vanilla bytes (round-robin copy of available formations)
if vanilla_formations:
    print("    [INFO] Building {} fillers using VANILLA bytes (round-robin)")
    # Copie vanilla F0, F1, F2... en round-robin
    # Problème: formations vanilla trop grosses, ne rentrent pas
```

### Après (synthetic)
```python
# Strategy: Always use synthetic fillers (1 record each)
# This ensures they always fit in the remaining space.
# The offset table will point to user formations (duplicate offsets),
# so these fillers are never actually selected by the game.

# Strategy 2: Synthetic generation (fallback)
min_bytes = filler_count * (RECORD_SIZE + SUFFIX_SIZE)  # 5 * 36 = 180
```

## Pourquoi ça fonctionne

### Fillers jamais sélectionnés
L'offset table utilise des **duplicate offsets** qui pointent vers les formations utilisateur:
```
Offset table entries [4..11]:
  [4] → F0 (user formation)
  [5] → F1 (user formation)
  [6] → F2 (user formation)
  [7] → F0 (duplicate, pointe vers F0 user)
  [8] → F1 (duplicate, pointe vers F1 user)
  [9] → F2 (duplicate, pointe vers F2 user)
  [10] → F0 (duplicate, pointe vers F0 user)
  [11] → F1 (duplicate, pointe vers F1 user)
```

Les 5 fillers synthétiques sont dans la formation area mais **jamais sélectionnés** car les offsets [7-11] pointent vers les formations user [0-2].

### Contenu des fillers sans importance
Comme les fillers ne sont jamais choisis par le jeu, leur contenu n'a aucune importance. Les synthétiques de 1 record (slot 0, Goblin) sont parfaits:
- Simples à générer
- Taille minimale (36 bytes)
- Garantis de rentrer dans l'espace disponible

## Budget calculation

**Avant (vanilla round-robin):**
```
User formations: 716 bytes
Fillers (vanilla): 100 bytes (1 seul au lieu de 5!)
Padding: 80 bytes (pour combler)
Total: 896 bytes ✓
Mais: fichier réduit de 80 bytes → erreur injection
```

**Après (synthetic):**
```
User formations: 716 bytes (F0: 228, F1: 260, F2: 228)
Fillers (synthetic): 180 bytes (5 fillers * 36 bytes)
Total: 896 bytes ✓
Fichier: 46206976 bytes (multiple de 2048) ✓
```

## Résultat

✅ **Formations custom fonctionnent**
- F0: 7 slots (5xGoblin + 2xShaman) - SYNTHETIC bytes
- F1: 8 slots (8xBat) - SYNTHETIC bytes
- F2: 7 slots (2xGoblin + 5xShaman) - SYNTHETIC bytes

✅ **Fillers corrects**
- 5 fillers synthétiques de 1 record chacun
- Jamais sélectionnés (duplicate offsets)
- Remplissent le budget parfaitement

✅ **Build réussi**
- BLAZE.ALL: 46206976 bytes (multiple de 2048)
- Injection: succès
- BIN patché: 703M créé

## Leçon apprise

Pour les fillers, **toujours utiliser synthetic** (1 record minimum):
- Garantit que ça rentre dans l'espace disponible
- Simple et prévisible
- Le contenu n'a pas d'importance (jamais sélectionné)

Les vanilla bytes sont parfaits pour:
- Formations utilisateur identiques à vanilla (reproduction exacte)
- Mais PAS pour les fillers (trop variables en taille)
