# R Field Investigation - Vanilla vs Patched (2026-02-11)

## Question initiale

**Utilisateur** : "Vanilla Shaman lance Sleep (liste 2), patched Shaman lance FireBullet (liste 0). Pourquoi ?"

**Hypothèse** : Le R field dans assignment entries contrôle spell_list_index (entity+0x2B5).

## Investigation complète

### Vanilla vs Patched Comparison

**Extraction vanilla BLAZE.ALL** du BIN source (LBA 163167).

**Résultats** :

```
Assignment entries Cavern F1:

              byte[0] byte[1] byte[2] byte[3] byte[4] byte[5] byte[6] byte[7]
                       (L)                              (R)            (flag)

Goblin   V:     00      00      00      00      00      00      00      00
Goblin   P:     00      00      00      00      00      02      00      40
         DIFF:                                           R=0->2         +0x40

Shaman   V:     00      00      00      00      0F      00      00      00
Shaman   P:     01      01      00      00      01      03      00      40
         DIFF:   [0]     L=0->1           [4]    R=0->3         +0x40

Bat      V:     00      00      00      00      00      00      00      00
Bat      P:     02      03      00      00      02      04      00      40
         DIFF:   [0]     L=0->3           [4]    R=0->4         +0x40
```

### 🔥 Découverte majeure

**EN VANILLA, LES ASSIGNMENT ENTRIES N'EXISTENT PAS !**

- ❌ Pas de flag 0x40 au byte[7]
- ❌ Pas de structure complète
- ❌ R field = 0 (ou inexistant)
- ❌ L field = 0 (sauf Shaman qui a quelques bytes non-zéro)

**NOS PATCHES ONT CRÉÉ CES STRUCTURES !**

### Chaîne de responsabilité

**Qui modifie le R field ?**

#### 1. extract_monster_db.py (EXTRACTION)
```python
# Ligne 379
entry_data["R"] = assign_entries[i]["R"]
```
- **Rôle** : EXTRAIT R depuis BLAZE.ALL → écrit dans JSONs
- **Fonction** : `find_assignment_entries()` cherche entries avec flag 0x40
- **Problème** : Vanilla n'a PAS 0x40 ! Extraction impossible sur vanilla pur

#### 2. patch_formations.py (PATCHING)
```python
# Ligne 717-721
if "R" in floor_data:
    new_R = floor_data["R"]
    data[assign_off + 5] = new_R
```
- **Rôle** : LIT R depuis JSONs → ÉCRIT dans BLAZE.ALL byte[5]
- **Fonction** : `_find_assign_entry_offset()` cherche entries avec flag 0x40
- **Limitation** : Ne peut écrire QUE si entries 0x40 existent déjà

#### 3. patch_assignment_entries.py (NOUVEAU - 2026-02-11)
```python
# Ligne 157-158
blaze_data[offset + 1] = L
blaze_data[offset + 5] = R
```
- **Rôle** : Écrit directement L/R aux offsets spécifiés
- **Créé** : Pendant investigation L field
- **Usage** : Tests de swap L/R

### Origine mystérieuse des valeurs R

**Commit e4cc1c2** (2026-02-09) : Première apparition de assignment_entries dans JSONs

```json
{
  "slot": 0, "L": 0, "R": 2,  // Goblin
  "slot": 1, "L": 1, "R": 3,  // Shaman
  "slot": 2, "L": 3, "R": 4   // Bat
}
```

**Problème** : Ces valeurs ont été **EXTRAITES** d'un BLAZE.ALL qui avait déjà les entries avec 0x40 !

**Mais vanilla n'a PAS ces entries !**

**Conclusion** : L'extraction a été faite sur un **BLAZE.ALL INTERMÉDIAIRE** déjà modifié par :
1. Un script temporaire (supprimé depuis) ?
2. Édition manuelle (hex editor) ?
3. Output réutilisé (`output/BLAZE.ALL` au lieu de source) ?

**Origine des valeurs R=2,3,4 = INCONNUE**

### Scripts qui CRÉENT le flag 0x40

**Recherche exhaustive** : AUCUN script ne crée le flag 0x40 !

Tous les scripts CHERCHENT 0x40, aucun ne le CRÉE :
- `extract_monster_db.py` : cherche 0x40 (ligne 78)
- `patch_formations.py` : cherche 0x40 (ligne 867)
- `patch_assignment_entries.py` : écrit aux offsets donnés (pas de recherche)

**Question sans réponse** : Qui a créé les entries avec 0x40 initialement ?

### Test R field = spell_list_index ?

**Hypothèse** : R field contrôle spell_list_index (entity+0x2B5)

Si vrai :
- R=0 → liste 0 (Offensive/FireBullet)
- R=1 → liste 1 (Support/Heal)
- R=2 → liste 2 (Status/Sleep)
- R=3 → liste 3 (Herbs)

**Problème** : Vanilla Shaman avec R=0 lançait **Sleep** (liste 2), pas FireBullet !

Donc R=0 devrait donner liste 0, mais vanilla donnait liste 2. **Contradiction !**

**Conclusion** : **R ne contrôle PAS spell_list_index** de manière simple.

### Retour à vanilla (R=0)

**Action prise** (2026-02-11) :
- Modifié `Data/formations/cavern_of_death/floor_1_area_1.json`
- Tous les R → 0 (valeur vanilla)
- Patché et testé

**But** :
1. Voir si R=0 restaure le comportement vanilla (Sleep au lieu de FireBullet)
2. Éliminer une variable inconnue de l'équation

**Résultat test** : À TESTER IN-GAME

### Comment vanilla fonctionnait ?

**Mystère non résolu** : Sans assignment entries (pas de 0x40, pas de L/R), comment vanilla déterminait :
1. **L field** (comportement AI/animations) ?
2. **spell_list_index** (quelle liste de sorts) ?

**Hypothèses** :
1. **Dérivé à runtime** depuis d'autres données (monster stats, zone data)
2. **Hardcodé dans overlay** code par zone/monster type
3. **Table ailleurs** dans BLAZE.ALL (pas aux mêmes offsets)
4. **Structure différente** en vanilla (pas de flag 0x40, autre format)

**Recherche suggérée** :
- Comparer monster_stats vanilla vs patched
- Chercher tables de configuration dans vanilla BLAZE.ALL
- Analyser code overlay vanilla pour hardcoded values

## Conclusions

### Ce qu'on sait ✅

1. **Vanilla n'a PAS d'assignment entries avec 0x40**
2. **Nos patches ont CRÉÉ ces structures** (origine inconnue)
3. **R values actuelles** (2,3,4) viennent d'un BLAZE.ALL mystérieux
4. **L field contrôle casting behavior** (L=1 active spell casting)
5. **R field ne contrôle PAS spell_list_index** (ou pas de manière simple)

### Ce qu'on ne sait PAS ❌

1. **Qui a créé les entries 0x40** initialement ?
2. **Pourquoi R=2,3,4** spécifiquement ?
3. **Comment vanilla déterminait spell_list_index** ?
4. **Pourquoi vanilla Shaman = Sleep**, patched = FireBullet ?

### Prochaines étapes

#### Test immédiat
- **Tester R=0** in-game : Shaman lance-t-il Sleep maintenant ?
- Si oui : R contrôle spell_list (mais de manière inverse/complexe)
- Si non : Chercher ailleurs

#### Investigation longue
1. **Comparer monster_stats** vanilla vs patched (byte-à-byte)
2. **Chercher spell_list tables** dans vanilla BLAZE.ALL
3. **Analyser overlay code** pour hardcoded spell_list assignments
4. **Runtime debugging** (PCSX-Redux) pour voir entity+0x2B5 au spawn

## Fichiers modifiés

**Revert à vanilla** :
- `Data/formations/cavern_of_death/floor_1_area_1.json` : R=2,3,4 → R=0,0,0

**Scripts impliqués** :
- `Data/formations/extract_monster_db.py` : EXTRAIT R
- `Data/formations/patch_formations.py` : ÉCRIT R (si entries existent)
- `Data/formations/patch_assignment_entries.py` : ÉCRIT R (direct)

**Documentation** :
- `Data/formations/R_FIELD_INVESTIGATION.md` : Ce document
- `Data/formations/L_FIELD_DISCOVERY.md` : Découverte L field
- `compare_vanilla_patched.py` : Outil de comparaison
- `extract_vanilla_blaze.py` : Extraction vanilla

## Test multi-zones : R=0 général ou spécifique ? (2026-02-11)

**Question** : Le R=0 de vanilla est-il général ou juste pour Cavern F1 ?

**Script** : `check_vanilla_R_values.py` - vérifie 4 zones

**Résultats vanilla** :

```
Zone          R values        0x40 flags?
-----------------------------------------
Cavern F1     R=[ 0, 0, 0]    NO
Forest F1     R=[ 0,63, 0]    NO
Castle F1     R=[210, 0,87]   NO
Valley F1     R=[ 0,50, 0]    NO
```

**Découverte majeure** :

1. ❌ **AUCUN flag 0x40** dans vanilla (4 zones testées)
2. ❌ **Données aléatoires** aux offsets d'assignment entries
3. ❌ **R varie** (0, 63, 210, 87, 50) mais ce ne sont PAS des valeurs R réelles
4. ✅ **Conclusion** : Les offsets vanilla ne contiennent PAS d'assignment entries

**Interprétation** :

Les "valeurs R" dans vanilla sont juste des données aléatoires/non-liées qui se trouvent aux offsets où NOS PATCHES ont créé les assignment entries.

En vanilla :
- Pas de structure assignment entry
- Pas de flag 0x40
- Les offsets contiennent autre chose (code overlay, données de zone, etc.)

**Réponse à la question** : **GÉNÉRAL** - Vanilla n'a aucune assignment entry nulle part.

## Historique

- **2026-02-09** : Commit e4cc1c2 ajoute assignment_entries (R=2,3,4)
- **2026-02-11** : Découverte L field (L=1 active casting)
- **2026-02-11** : Comparaison vanilla vs patched
- **2026-02-11** : Découverte : vanilla n'a PAS d'entries 0x40 (Cavern F1)
- **2026-02-11** : Test multi-zones : confirmé GÉNÉRAL (4 zones)
- **2026-02-11** : Revert R → 0 (valeur arbitraire, vanilla n'a pas d'entries)
- **2026-02-11** : Documentation complète

## Voir aussi

- `Data/formations/L_FIELD_DISCOVERY.md` - L field et casting behavior
- `Data/ai_behavior/FAILED_ATTEMPTS.md` - 7 tentatives spell bitfield
- `Data/character_classes/TIER_THRESHOLD_FAILURE.md` - Échec tier thresholds
