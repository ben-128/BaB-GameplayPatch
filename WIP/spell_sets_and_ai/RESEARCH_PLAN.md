# Spell Sets & AI System - Research Plan

## Objectifs

### 1. Trouver où les spell sets sont définis
**Question:** Où les slot_types (02000000, 03000000, 00000a00) sont-ils mappés vers des bitmasks de sorts?

**Ce qu'on sait:**
- `entity+0x160` = bitmask 32-bit qui contrôle quels sorts sont disponibles
- Le bitmask est initialisé via un level-up simulation loop (OR-accumulate)
- Les slot_types dans formation records (byte[0:4]) modifient les sorts disponibles
- Test confirmé: Shaman avec 02000000 = Sleep, avec 00000a00 = FireBullet

**Ce qu'on cherche:**
- Table de lookup: `slot_type → initial_bitmask`
- Code qui lit byte[0:4] depuis formation records
- Code qui initialise entity+0x160 à partir du slot_type
- Emplacement probable: overlay de spawn de formations (pas dans EXE)

**Hypothèse:**
```
Formation spawn code:
1. Read formation record → byte[0:4] = slot_type (ex: 02000000)
2. Lookup: slot_type_table[02000000] → bitmask (ex: 0x00000107)
3. Write: entity+0x160 = bitmask
4. Level-up sim runs and OR-accumulates more bits based on entity+0x144 (level)
```

### 2. Comment rendre un non-caster capable de caster

**Question:** Comment donner des sorts à un monstre qui n'en a pas normalement (ex: Goblin)?

**Ce qu'on sait:**
- **L field (flag 0x00)** = AI Behavior Index
  - L=0 (Goblin) → melee AI
  - L=1 (Shaman) → caster AI
  - Changer L d'un Goblin vers L=1 → goblin essaie de cast mais disparaît (glitch animation)
- **creature_type à entity+0x2B5** = toujours 0 (Type 0 = 28 Mage spells)
- **entity+0x160** = bitmask qui gate les sorts disponibles

**Problèmes connus:**
1. Changer L → change AI ET animations attendues (incompatibilité)
2. Goblin n'a pas d'animations de cast → glitches visuels
3. L et animations sont couplés

**Approches possibles:**

#### A. Modifier le bitmask directement (sans changer L)
- Trouver où entity+0x160 est initialisé
- Forcer un bitmask de caster pour un Goblin (slot_type spécial)
- **Problème:** Si l'AI reste melee (L=0), le monstre ne décidera jamais de caster

#### B. Créer un AI hybride (melee + cast)
- Trouver les AI behavior handlers
- Modifier l'AI L=0 (Goblin) pour inclure des décisions de cast
- **Problème:** Complexe, nécessite de comprendre le système AI complet

#### C. Utiliser un monstre qui cast déjà
- Remplacer le Goblin par un Shaman visuellement modifié (texture + mesh)
- Ou utiliser un monstre vanilla qui cast mais ressemble à un melee (Trent? Wisp?)

#### D. Trouver un L spécial qui fait melee+cast
- Tester différentes valeurs de L pour trouver un AI hybride
- Certains boss pourraient avoir un AI hybride existant

## Actions de recherche

### Phase 1: Trouver la table de spell sets

#### Action 1.1: Chercher les valeurs slot_types dans BLAZE.ALL
```bash
# Chercher 02000000, 03000000, 00000a00 dans le binaire
hexdump -C BLAZE.ALL | grep "02 00 00 00"
hexdump -C BLAZE.ALL | grep "03 00 00 00"
hexdump -C BLAZE.ALL | grep "00 0a 00 00"
```

#### Action 1.2: Identifier l'overlay de formation spawn
- Les formations sont gérées par le système de random encounters
- L'overlay qui charge/spawn les formations doit lire les records
- Chercher les références à `formation_area_start` offsets

#### Action 1.3: Disassembler le code d'init d'entité
- Trouver où entity+0x160 est écrit (première fois, pas le level-up loop)
- Tracer backwards pour trouver d'où vient la valeur
- Chercher une table de lookup ou un switch statement

#### Action 1.4: Tester des slot_types custom
- Essayer des valeurs non-vanilla (ex: 01000000, 04000000, FF000000)
- Observer les effets en jeu (crash? sorts différents? aucun effet?)
- Mapper empiriquement: slot_type → spell list

### Phase 2: Comprendre le système AI

#### Action 2.1: Cataloguer tous les L values
- Scanner toutes les areas (41 areas)
- Lister toutes les valeurs L uniques et leurs monstres associés
- Identifier les patterns (ex: tous les casters ont L >= X?)

#### Action 2.2: Tester les L values sur différents monstres
```python
# test_ai_swap.py
# Goblin avec différents L: 0, 1, 2, 3, 4, 5...
# Observer: comportement, animations, crash?
```

#### Action 2.3: Chercher les AI behavior handlers
- L est un index vers une table de handlers
- Chercher dans les overlays pour des jump tables ou switch statements
- Identifier combien de AI behaviors existent (max L value)

#### Action 2.4: Test empirique: Goblin caster
**Test 1: Forcer bitmask sans changer L**
```json
{
  "slots": [0],
  "slot_types": ["00000a00"]  // Bat spells pour Goblin
}
```
Résultat attendu: Goblin avec sorts dans son menu, mais ne les utilise jamais (AI melee)

**Test 2: Changer L sans changer slot_type**
```json
Modifier L dans assignment entries:
Goblin: L=0 → L=1 (Shaman AI)
```
Résultat attendu: Goblin essaie de cast, glitches visuels (déjà testé)

**Test 3: Forcer bitmask + changer L**
```json
{
  "slots": [0],
  "slot_types": ["00000a00"]
}
+ Goblin L=1
```
Résultat attendu: Goblin avec Shaman AI + Bat spells? Ou crash?

### Phase 3: Trouver un monstre vanilla melee+cast

#### Action 3.1: Tester les monstres suspects
- Trent (casts avec 00000000 slot_type selon notes)
- Wisp (casts avec 00000000)
- Mini-boss/boss (peuvent avoir AI hybrides)

#### Action 3.2: Observer leur L value et slot_type
- Si un monstre melee cast avec L=X, alors L=X est un AI hybride
- Appliquer ce L à d'autres monstres pour voir si ça marche

## Priorités

1. **URGENT:** Trouver la table slot_type → bitmask (nécessaire pour tout le reste)
2. **HIGH:** Cataloguer toutes les valeurs L et identifier les AI types
3. **MEDIUM:** Tester Goblin avec différents slot_types + L combinations
4. **LOW:** Reverse engineer le système AI complet (très complexe)

## Fichiers à créer

- `slot_type_search.py` - Cherche les slot_types dans BLAZE.ALL
- `test_custom_slot_types.py` - Teste des valeurs non-vanilla
- `catalog_L_values.py` - Extrait tous les L values de toutes les areas
- `test_goblin_caster.py` - Teste différentes combinaisons pour rendre Goblin caster
- `SLOT_TYPE_MAPPING.md` - Documentation du mapping slot_type → spell list
- `AI_SYSTEM.md` - Documentation du système AI (L field)
