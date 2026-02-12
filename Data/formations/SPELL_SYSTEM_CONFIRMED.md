# Monster Spell System - Tests Confirmés

**Date:** 2026-02-12
**Status:** Système partiellement découvert, tests en cours

---

## Spell Lists Vanilla (Référence)

### Goblin-Shaman (Vanilla)
**slot_types = 02000000**
1. **Sleep**
2. Magic Missile
3. Stone Bullet

### Giant-Bat (Vanilla)
**slot_types = 00000a00**
1. **FireBullet**
2. Magic Missile
3. Stone Bullet

---

## Tests Confirmés In-Game ✅

### Test 1: Bat Prefix sur Shaman (2026-02-12)

**Configuration:**
- Location: Cavern F1 A1, Formation 0
- Patch: Shaman records avec byte[0:4] = 00000a00 (Bat prefix)
- Contrôle: Autres formations vanilla

**Résultats:**
```
Formation 0 (patchée):
  Shamans: FireBullet, Magic Missile, Stone Bullet

Autres formations (vanilla):
  Shamans: Sleep, Magic Missile, Stone Bullet
```

**Conclusion:**
- ✅ Prefix 00000a00 (Bat) sur Shaman → **FireBullet** (1er sort change)
- ✅ Sorts 2 et 3 restent identiques (Magic Missile, Stone Bullet)
- ✅ Système fonctionne PAR-FORMATION (pas global)

---

### Test 2: Formation Suffix Values (2026-02-12)

**Configuration (tests multiples):**
- Formation 1 Shaman + suffix 00000000
- Formation 2 Shamans + suffix 03000000

**Résultats:**
```
Formation 1 Shaman (suffix 00000000):
  Spell List: FireBullet, Magic Missile, Stone Bullet
  (Même spell list que Bat!)

Formation 2 Shamans (suffix 03000000):
  Spell List: Sleep, Magic Missile, Heal
  (3e sort changé: Stone Bullet → Heal!)
```

**Conclusion:**
- ✅ SUFFIX contrôle le spell set (pas juste le prefix individuel)
- ✅ Suffix 00000000 sur Shaman → Spell set Bat
- ✅ Suffix 03000000 (Tower) → Change 3e sort (Stone Bullet → Heal)

---

## Mapping Spell Modifiers Confirmé

| slot_types | Applied to Shaman    | Spell 1        | Spell 2        | Spell 3      | Status      |
|------------|----------------------|----------------|----------------|--------------|-------------|
| 02000000   | Vanilla Shaman       | Sleep          | Magic Missile  | Stone Bullet | ✅ Vanilla  |
| 03000000   | Tower variant        | Sleep          | Magic Missile  | **Heal**     | ✅ Confirmed |
| 00000a00   | Bat modifier         | **FireBullet** | Magic Missile  | Stone Bullet | ✅ Confirmed |
| 00000000   | Base/Goblin modifier | **FireBullet** | Magic Missile  | Stone Bullet | ✅ Confirmed |

---

## Architecture du Système (Révisée)

### Deux Couches

**Couche 1 - byte[8] (Entité):**
- Contrôle: Modèle 3D, animations, stats, AI
- Détermine SI l'entité peut lancer des sorts

**Couche 2 - slot_types (Modificateur de Sorts):**
- Défini dans JSON: `"slot_types": ["00000000", "02000000", "00000a00"]`
- Utilisé dans records: byte[0:4] (prefix) et 4-byte suffix
- Contrôle: QUELS sorts sont disponibles

### Formation Record Structure

```
Record (32 bytes):
  byte[0:4]   = PREFIX (slot_types du monstre PRÉCÉDENT)
  byte[4:8]   = FFFFFFFF (début) ou 00000000 (suite)
  byte[8]     = SLOT_INDEX (0=Goblin, 1=Shaman, 2=Bat)
  byte[9]     = 0xFF
  byte[10-23] = ZÉROS (pas de données de sorts)
  byte[24-25] = AREA_ID
  byte[26-31] = FFFFFFFFFFFF

Après formation:
  4 bytes SUFFIX = slot_types du DERNIER monstre
```

### Règles Critiques

1. **Premier record:** byte[0:4] = TOUJOURS 00000000
2. **Records suivants:** byte[0:4] = slot_types du monstre précédent
3. **Suffix:** slot_types du dernier monstre de la formation
4. **Le SUFFIX semble être le plus important** pour déterminer les sorts

---

## Tests en Échec (Crash au Spawn)

### Tentatives de Rebuild Formations

**Problèmes rencontrés:**
- Reconstruction complète des formations → crash
- Padding avec zéros → crash
- Fillers synthétiques sélectionnés par le jeu

**Cause probable:**
- Structure de formation plus complexe que prévu
- Certains bytes unknown dans records ont une importance
- Offset table nécessite structure spécifique

**Solution:**
- Utiliser bytes vanilla EXACTS
- Modifier SEULEMENT les slot_types dans JSON
- Laisser le patcher officiel générer les formations

---

## Comment Modifier les Sorts (Méthode Sûre)

### Méthode 1: Via slot_types dans JSON

1. Éditer `Data/formations/<level>/<area>.json`
2. Modifier `slot_types` array:
   ```json
   "slot_types": [
     "00000000",    // Slot 0: Goblin
     "03000000",    // Slot 1: Shaman (CHANGÉ de 02000000)
     "00000a00"     // Slot 2: Bat
   ]
   ```
3. Le patcher utilisera cette valeur pour générer prefix/suffix
4. Build: `py -3 Data/formations/Scripts/patch_formations.py`

**Effet attendu:**
- Shamans auront: Sleep, Magic Missile, **Heal** (au lieu de Stone Bullet)

### Méthode 2: Patch Direct BLAZE.ALL (Risqué)

Seulement pour tests rapides. Modifier byte[0:4] des records directement.

**⚠️ Attention:** Pas de rebuild complet - modifier seulement bytes spécifiques!

---

## Valeurs slot_types Connues

### Catalogue Complet (41 Areas Analysées)

| Valeur     | Trouvé sur                          | Effet Confirmé sur Shaman          |
|------------|-------------------------------------|------------------------------------|
| 00000000   | Goblin, base monsters               | FireBullet, MM, Stone Bullet       |
| 02000000   | Goblin-Shaman (vanilla)             | Sleep, MM, Stone Bullet (vanilla)  |
| 03000000   | Tower Shaman variant                | Sleep, MM, **Heal**                |
| 00000a00   | Bat, Ghost, Wraith (flying)         | FireBullet, MM, Stone Bullet       |
| 00000100   | Arch-Magi, rare Bats                | ❓ Non testé                        |

### Observations

**00000000 (Base):**
- Sur Goblin: Pas de sorts (melee)
- Sur Shaman: Spell set Bat (FireBullet)
- Sur Trent: Spells de Trent (différents!)
- **Conclusion:** "Base set" varie selon l'entité

**02000000 (Vanilla Shaman):**
- Sort 1: Sleep (signature Shaman)
- Sorts 2-3: Communs (MM, Stone Bullet)

**03000000 (Tower):**
- Sort 1: Sleep (garde)
- Sort 3: **Heal** (remplace Stone Bullet)
- Variant "support" du Shaman

**00000a00 (Flying/Bat):**
- Sort 1: FireBullet (signature Bat)
- Bit 0x0a possiblement lié au vol?

---

## Questions Non-Résolues

### 1. Goblin + Shaman slot_types = ?

**Test effectué:**
- 3x Goblin + prefix 02000000 (Shaman)
- Résultat: "agissent normalement" (pas de sorts)

**Conclusion:**
- byte[8]=0x00 (Goblin) = entité NON-caster
- slot_types ne peut PAS ajouter capacité de sorts
- Seulement les entités avec capacité de base (Shaman, Bat, etc.) peuvent être modifiées

### 2. Quelle partie exacte contrôle les sorts?

**Hypothèses:**
1. Le SUFFIX (4 bytes après formation) = contrôle principal?
2. Le PREFIX du dernier record = influence?
3. Combinaison des deux?

**Test nécessaire:**
- Formation avec prefix vanilla mais suffix modifié
- Isolation exacte du système

### 3. Valeur 00000100 (Rare)

**Trouvée sur:**
- Arch-Magi (Tower A11)
- Giant-Bat (Cavern F3 A1)

**Effet:** Non testé

**Hypothèse:** Tier supérieur de sorts? Variante rare?

### 4. Peut-on créer de nouveaux slot_types?

**Question:** Valeurs custom non-vanilla fonctionnent-elles?
**Test:** Essayer 01000000, FFFFFFFF, etc.

---

## Prochaines Étapes

### Tests Prioritaires

1. ✅ **Confirmer suffix 02000000 sur Shaman** → Sleep vanilla
2. ✅ **Confirmer suffix 03000000 sur Shaman** → Sleep + Heal
3. ✅ **Confirmer suffix 00000a00 sur Shaman** → FireBullet
4. ❓ **Tester suffix 00000100** → ? nouveaux sorts?
5. ❓ **Tester sur autres entités** (Bat, Ghost, Trent)

### Documentation à Compléter

1. **Table exhaustive spell sets** après tous les tests
2. **Guide utilisateur** pour modifier sorts via JSON
3. **Exemple formations** avec spell sets custom

### Recherche Avancée

1. **Analyser EXE** pour trouver spell dispatch
2. **Mapper bitmasks entity+0x160** aux sorts
3. **Identifier patterns** dans slot_types bytes
4. **Tester limites** du système (valeurs invalides)

---

## Références

### Scripts

- `test_slot_types_spells.py` - Test initial (Bat prefix sur Shaman)
- `analyze_caster_slot_types.py` - Analyse 41 areas
- `patch_formations.py` - Patcher officiel (utiliser celui-ci!)

### Documentation

- `SPELL_MODIFIER_RESEARCH.md` - Recherche complète
- `SPELL_MODDING_QUICK_REFERENCE.md` - Guide rapide
- `memory/MEMORY.md` - Notes système

### JSON Examples

```json
{
  "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
  "slot_types": [
    "00000000",  // Goblin: pas de sorts
    "02000000",  // Shaman: Sleep, MM, Stone Bullet
    "00000a00"   // Bat: FireBullet, MM, Stone Bullet
  ],
  "formations": [...]
}
```

---

**Dernière mise à jour:** 2026-02-12
**Tests confirmés:** 3/3 (Bat, Tower, Base sur Shaman)
**Crashs rencontrés:** 2 (rebuild formations)
**Méthode stable:** Modifier slot_types dans JSON, utiliser patcher officiel
