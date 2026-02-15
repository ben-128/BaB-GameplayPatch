# Monster Slots Addition - Research Summary

## Objectif
Ajouter 2 monster slots à Cavern of Death F1 A1 (3 → 5 monsters)

## Découvertes Critiques

### ✅ CE QUI FONCTIONNE
1. **Changer monster count de 3 à 5** (middle section byte[2])
   - Pas de crash
   - Le jeu accepte la valeur 5
   - Testé et confirmé

### ❌ CE QUI CRASH
1. **Agrandir middle section** de 44 → 48 bytes
   - Crash immédiat (erreur CD: D4:52:43 / LBA 960067)
   - La taille de 44 bytes est CRITIQUE et ne peut pas changer

2. **Ajouter les données des nouveaux slots**
   - Même en gardant middle section à 44 bytes
   - Crash avec les mêmes symptômes
   - Le jeu rejette les données additionnelles

## Structure Testée

### Version qui FONCTIONNE
```
[Anim Header 8B]
[Anim Tables 3×8 = 24B]
[Anim Records 3×8 = 24B]
[Middle Section 44B] ← byte[2] = 5
[Assignments 3×8 = 24B]
[Stats 3×96 = 288B]
[Script][Formations][Zone_spawns]
```

### Versions qui CRASHENT
```
# Version A: Middle section agrandie
[Middle Section 48B] ← CRASH!

# Version B: Nouveaux slots ajoutés
[Anim Tables 5×8 = 40B]
[Anim Records 5×8 = 40B]
[Middle Section 44B] ← byte[2] = 5
[Assignments 5×8 = 40B]
[Stats 5×96 = 480B] ← CRASH!
```

## Analyse

### Symptômes du crash
- Erreur: "Invalid/out of range seek to D4:52:43"
- MSF: D4:52:43 = LBA 960067
- LBA 960067 est bien AU-DELÀ de BLAZE.ALL (se termine à ~LBA 208331)
- Le jeu essaie de charger un fichier/ressource invalide

### Hypothèses
1. **Validation de structure**
   - Le jeu vérifie que les données correspondent à monster_count
   - Accepte count=5 mais rejette si les données ne correspondent pas

2. **Table de pointeurs cachée**
   - Il existe une table ailleurs qui référence les positions des slots
   - Cette table n'a pas été mise à jour

3. **Limitation hardcodée**
   - Cavern F1 A1 est hardcodée pour 3 slots maximum
   - Impossible d'ajouter des slots à cette area spécifique

4. **Format de middle section**
   - La middle section contient des métadonnées critiques
   - Le format pour 5 monsters est différent du format pour 3 monsters
   - On ne peut pas juste changer le count sans reconstruire toute la middle section

## Comparaison Forest vs Cavern

### Forest F1 A2 (5 monsters vanilla)
- Middle section: **48 bytes**
- Contenu complètement différent de Cavern

### Cavern F1 A1 (3 monsters vanilla)
- Middle section: **44 bytes**
- Structure apparemment incompatible avec 5 monsters

## Offsets Trouvés

### Monster Count Locations
- **0xF7A93A** (middle section byte[2]) - VÉRIFIÉ
- 0xF7A851 (header avant zone) - testé, pas critique
- 0xF7A94D, 0xF7A955, 0xF7A95A - testés, pas critiques

### Formation Start References (hardcodés)
- 0x18920CB, 0x1892133, 0x189234B, 0x18923B3
- Mis à jour avec succès

## Prochaines Étapes

### Option A: Debug avec DuckStation (RECOMMANDÉ)
1. Lancer le jeu avec version "count=5 seulement" (qui fonctionne)
2. Mettre breakpoint à 0x80021E68
3. Step through le code de chargement
4. Identifier exactement où et pourquoi l'ajout de slots cause le crash
5. Trouver la table/validation qui bloque

### Option B: Analyse exhaustive du binaire
1. Comparer BYTE PAR BYTE Forest (5m) vs Cavern (3m)
2. Identifier TOUTES les structures liées au monster count
3. Reconstruire la middle section avec le format exact de Forest
4. Tester chaque modification individuellement

### Option C: Approche alternative
1. Tester sur une AUTRE area (pas Cavern F1 A1)
2. Vérifier si certaines areas sont plus flexibles
3. Si ça marche ailleurs, comparer les structures

## Fichiers Créés

### Scripts
- `reorganize_add_slots_FIXED.py` - Version améliorée (mais crash)
- `add_slots_keep_middle_44.py` - Garde middle section 44 bytes (crash aussi)
- `test_middle_section_only.py` - Tests d'isolation
- `clone_forest_structure.py` - Tentative de clonage

### Documentation
- `DEBUG_MONSTER_SLOTS_CRASH.md` - Guide de debug
- `MONSTER_SLOTS_RESEARCH_SUMMARY.md` - Ce fichier

## Conclusion

**L'ajout de monster slots est POSSIBLE en théorie** (le jeu accepte count=5) mais **bloqué par un mécanisme inconnu**.

Sans debugging en direct, on ne peut pas identifier la cause exacte du rejet des données additionnelles.

**Recommandation:** Utiliser DuckStation debugger pour trouver le point exact du crash et identifier le mécanisme de validation.

---

**Dernière mise à jour:** 2026-02-15
**Status:** En recherche - Debug requis
