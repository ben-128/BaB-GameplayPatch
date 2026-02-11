# Hypothèse R Field = Spell List Index (2026-02-11)

## Contexte

**Problème initial** : Vanilla Shaman lance Sleep, patched Shaman lance FireBullet.

**Découvertes précédentes** :
1. L field (byte[1]) contrôle le comportement casting (L=1 = caster)
2. R field (byte[5]) : fonction inconnue
3. Vanilla n'a PAS d'assignment entries (pas de flag 0x40)
4. R varie par zone pour le même monstre (zone-specific, pas monster-specific)

## Nouvelle hypothèse : R = spell_list_index

### Listes de sorts (entity+0x2B5)

```
0 = Offensive  (FireBullet, IceBullet, ThunderBolt, etc.)
1 = Support    (Heal, Protect, Speed Up, etc.)
2 = Status     (Sleep, Poison, Paralyze, etc.)
3 = Herbs      (Antidote, Medical, etc.)
4 = Wave       (spells Wave)
5 = Arrow      (spells Arrow)
6 = Stardust   (spells Stardust)
7 = Monster-only (30 sorts exclusifs monstres)
```

### Observation clé : Goblin-Shaman

**Vanilla** :
- Lance Sleep (liste 2 = Status)
- R=0 dans vanilla bytes (mais pas de structure valide)

**Patched actuel** :
- Lance FireBullet (liste 0 = Offensive)
- R=0 dans nos JSONs

**Si R = spell_list_index** :
- R=0 → liste 0 (Offensive) → FireBullet ✓ (matches!)
- R=2 → liste 2 (Status) → Sleep (devrait restaurer vanilla)

### Analyse statistique (patched JSONs)

**Distribution R** (109 monstres) :
```
R=0 (Offensive):   12 occurrences (11.0%)
R=1 (Support):     13 occurrences (11.9%)
R=2 (Status):      18 occurrences (16.5%)
R=3 (Herbs):       19 occurrences (17.4%)
R=4 (Wave):        14 occurrences (12.8%)
R=5 (Arrow):       13 occurrences (11.9%)
R=6 (Stardust):     8 occurrences (7.3%)
R=7 (Monster-only): 4 occurrences (3.7%)
R=9+: rares
```

→ Distribution quasi-uniforme sur 0-7 (les 8 listes de sorts!)

**Casters connus vs R attendu** :
- Matches: 2/21 (9.5%) - Ghost R=2, Chimera R=0
- Mismatches: 19/21 (90.5%)

→ Corrélation faible MAIS valeurs R restent dans range 0-12 (pas aléatoires 0-255)

### Variations par zone (même monstre)

**Goblin-Shaman** :
```
Cavern F1 A1:  L=1, R=0  (Offensive)
Cavern F1 A2:  L=1, R=5  (Arrow)
Cavern F2 A1:  L=1, R=3  (Herbs)
```

**Ghost** :
```
Castle F1 A2:  L=1, R=2  (Status) <- MATCH attendu!
Castle F2 A1:  L=1, R=6  (Stardust)
Castle F3 A1:  L=1, R=1  (Support)
```

→ Même monstre peut avoir différentes listes selon la zone
→ Cohérent avec un système "spell list par zone"

### Vanilla vs Patched : comment ça marchait ?

**Vanilla** (sans assignment entries) :
- Probablement hardcodé dans overlay code par zone/monster type
- OU table de mapping ailleurs dans BLAZE.ALL
- Shaman → toujours liste 2 (Status/Sleep)

**Patched** (avec assignment entries) :
- R field stocke l'index explicite
- Nos patches ont créé les structures avec R=0 par défaut
- D'où le passage Sleep → FireBullet !

## Test expérimental

**Modification** : `Data/formations/cavern_of_death/floor_1_area_1.json`
```json
{
  "slot": 1,
  "L": 1,
  "R": 2,    // Changed from 0 to 2
  "offset": "0xF7A96C"
}
```

**Prédiction** :
- Si R contrôle spell_list_index : Shaman lancera Sleep (liste 2)
- Si R ne contrôle rien : Shaman lancera toujours FireBullet

**Procédure** :
1. Patch BLAZE.ALL avec R=2
2. Rebuild BIN
3. Test in-game Cavern F1
4. Observer les sorts du Shaman

**Résultat** : TEST ANNULÉ - Reverted to vanilla R values

**Décision finale** (2026-02-11) :
- Restauré TOUS les R aux bytes vanilla (98 changements)
- Goblin-Shaman Cavern F1 : R=0 (vanilla bytes)
- Permet de tester si vanilla bytes ont un effet vs valeurs extraites du BLAZE mystérieux

## Implications si confirmé

### Pour restaurer vanilla behavior

Tous les monstres qui lançaient des sorts Status/Support devront avoir leur R corrigé :
```
Goblin-Shaman → R=2 (Status/Sleep)
Ghost → R=2 (Status/Fear,Curse)
Etc.
```

### Pour modifier les sorts

Changer R permet de donner n'importe quelle liste à n'importe quel monstre :
```
R=0 → Offensive (FireBullet, IceBullet, etc.)
R=1 → Support (Heal, Protect, etc.)
R=2 → Status (Sleep, Poison, Paralyze, etc.)
```

### Limitation

Le bitfield (entity+0x160) contrôle QUELS sorts sont disponibles dans la liste.
R contrôle QUELLE liste, mais pas quels sorts individuels.

Pour control complet :
- R = quelle liste (0-7)
- Bitfield = quels sorts dans cette liste (bits 0-29)

## Scripts d'analyse

**Créés aujourd'hui** :
- `check_vanilla_R_values.py` : Analyse R dans vanilla (4 zones)
- `analyze_all_vanilla_R.py` : Analyse R dans vanilla (toutes zones)
- `check_R_vs_casters.py` : Corrélation R / spell casters
- `check_monster_R_variations.py` : Variations R par zone
- `test_R_as_spell_list_index.py` : Test hypothèse R=spell_list_index

**Documentation** :
- `R_FIELD_INVESTIGATION.md` : Investigation complète R field
- `L_FIELD_DISCOVERY.md` : Découverte L field = casting behavior
- `SPELL_LIST_HYPOTHESIS.md` : Ce document

## Historique

- **2026-02-09** : Commit e4cc1c2 ajoute assignment_entries avec R=2,3,4
- **2026-02-11** : Découverte L=1 active casting
- **2026-02-11** : Comparaison vanilla vs patched → vanilla n'a pas d'entries
- **2026-02-11** : Analyse 109 monstres → R varie par zone (0-255)
- **2026-02-11** : Corrélation R / casters → 72% casters ont R≠0
- **2026-02-11** : Distribution R dans patched → quasi-uniforme 0-7
- **2026-02-11** : **Hypothèse R = spell_list_index** formulée
- **2026-02-11** : Test Shaman R=0→2 préparé

## Prochaines étapes

1. **Test in-game** avec Shaman R=2
2. Si confirmé : **Extraire vanilla spell lists** pour tous les monstres
3. Créer **patcher automatique** pour restaurer vanilla spell behavior
4. Documenter **mapping complet** monster → spell_list par zone

## Références

- `Data/spells/MONSTER_SPELLS.md` : Documentation système de sorts
- `Data/spells/spell_config.json` : Configuration sorts (stats, damage)
- `Data/ai_behavior/overlay_bitfield_config.json` : Configuration bitfield par zone
