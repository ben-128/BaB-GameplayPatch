# Monster Spell Modifier System - Research Complete

**Date:** 2026-02-12
**Status:** System discovered, tests in progress

---

## Table des Matières

1. [Découverte du Bug FireBullet](#découverte-du-bug-firebullet)
2. [Architecture du Système](#architecture-du-système)
3. [Tests In-Game - Résultats Confirmés](#tests-in-game---résultats-confirmés)
4. [Analyse des slot_types Existants](#analyse-des-slot_types-existants)
5. [Tests en Cours](#tests-en-cours)
6. [Comment Utiliser le Système](#comment-utiliser-le-système)

---

## Découverte du Bug FireBullet

### Le Bug Original

**Symptôme:** Goblin-Shaman lançait **FireBullet** au lieu de **Sleep** dans les formations custom.

**Observation Critique (2026-02-12):**
> "le shaman avait tout du shaman (stat, visuel, lanceur de sorts avec plusieurs sorts),
> avec juste en changement un de ses sorts différent"

- ✅ Visuel correct (modèle 3D Shaman)
- ✅ Stats correctes (HP, attaque, défense Shaman)
- ✅ AI correct (comportement Shaman)
- ❌ **UN sort différent** (FireBullet au lieu de Sleep)

### Investigation Git

**Commit avec bug:** 8ad1717 (area rewrite patcher)
```python
def build_record(slot_index, is_formation_start, area_id_bytes):
    rec = bytearray(RECORD_SIZE)
    # byte[0:4] = flags (zeros)  ← HARDCODÉ À ZÉROS!
    rec[8] = slot_index  # ✓ Correct
```

**Commit fixed:** 07c094a (2026-02-12)
```python
def build_record(slot_index, is_formation_start, area_id_bytes,
                  prefix=b'\x00\x00\x00\x00'):
    rec = bytearray(RECORD_SIZE)
    rec[0:4] = prefix  # ✓ Utilise slot_types correct
    rec[8] = slot_index
```

### Conclusion

**Root Cause:** Le patcher générait `byte[0:4] = 00000000` pour TOUS les monstres.
- Shaman avec byte[8]=0x01 (entité correcte) + byte[0:4]=00000000 (modificateur Goblin)
- Résultat: Entité Shaman avec modificateur de sorts Goblin → FireBullet

---

## Architecture du Système

### Format de Record (32 bytes)

```
Offset  | Description
--------|----------------------------------------------------------
[0:4]   | PREFIX - slot_types du monstre PRÉCÉDENT (modificateur)
[4:8]   | FFFFFFFF (début formation) ou 00000000 (continuation)
[8]     | SLOT_INDEX - quel monstre (0=Goblin, 1=Shaman, 2=Bat)
[9]     | 0xFF (formation) ou 0x0B (spawn direct)
[10:23] | TOUS ZÉROS (pas de données de sorts/stats ici)
[24:25] | AREA_ID (ex: dc01 pour Cavern F1 A1)
[26:31] | FFFFFFFFFFFF (terminateur)

Après formation: 4-byte SUFFIX (slot_types du DERNIER monstre)
```

### Système à Deux Couches

**Couche 1: Entité de Base (byte[8])**
- Contrôle: Modèle 3D, animations, textures, stats de base, AI
- Exemple: byte[8]=0x01 → Entité Goblin-Shaman

**Couche 2: Modificateur de Sorts (byte[0:4])**
- Modifie: Liste de sorts disponibles
- Exemples:
  - byte[0:4]=02000000 → Modificateur Shaman
  - byte[0:4]=00000000 → Modificateur base
  - byte[0:4]=00000a00 → Modificateur volant
  - byte[0:4]=03000000 → Modificateur Tower variant

**Combinaisons:**
```
byte[8]=0x01 + byte[0:4]=02000000 → Shaman complet (Sleep)
byte[8]=0x01 + byte[0:4]=00000a00 → Shaman + sorts Bat (FireBullet)
byte[8]=0x01 + byte[0:4]=00000000 → Shaman + base set (?)
byte[8]=0x00 + byte[0:4]=02000000 → Goblin + sorts Shaman (?)
```

---

## Tests In-Game - Résultats Confirmés

### Test 1: Bat Prefix sur Shaman (2026-02-12)

**Configuration:**
- Location: Cavern F1 A1, Formation 0
- Patch: Shaman byte[0:4] = 00000a00 (prefix Bat)
- Contrôle: Autres formations même area (vanilla)

**Résultats:**
```
✅ Formation 0 (patchée):
   - 3x Shaman visuels/stats/AI corrects
   - Lancent FIREBULLET au lieu de Sleep

✅ Autres formations (vanilla):
   - Shamans gardent SLEEP
   - Comportement vanilla normal
```

**DÉCOUVERTE CRITIQUE:**

> **Le système fonctionne PAR-FORMATION, pas globalement!**

Même monstre, même area, même session → sorts différents selon la formation!

**Preuve:**
```
Formation 0:
  Record Shaman: byte[0:4]=00000a00 + byte[8]=0x01
  → Entité Shaman avec modificateur Bat
  → Résultat: FireBullet ✅

Formation X (vanilla):
  Record Shaman: byte[0:4]=02000000 + byte[8]=0x01
  → Entité Shaman avec modificateur Shaman
  → Résultat: Sleep ✅
```

---

## Analyse des slot_types Existants

### Catalogue Complet (41 Areas Analysées)

**Goblin-Shaman:**
- `02000000` (majorité) - Cavern, Forest → Sleep
- `03000000` (Tower A2) - Variant Tower
- `00000000` (Forest F1 A4) - Base set

**Giant-Bat:**
- `00000a00` (majorité) - Cavern F1 A1, F2 A1 → FireBullet
- `00000000` (Cavern F1 A2) - Base set
- `00000100` (Cavern F3 A1) - Rare variant

**Ghost:**
- `00000000` (Castle F2 A1, F3 A1)
- `00000a00` (Castle F3 A2)

**Wraith:**
- `00000000` (Sealed Cave A6)
- `00000a00` (Sealed Cave A4)

**Trent:**
- `00000000` (Forest F2 A2)

**Will-O-The-Wisp:**
- `00000000` (Forest F2 A2)

**Arch-Magi:**
- `00000000` (Tower A9)
- `00000100` (Tower A11)

### Valeurs Uniques Découvertes

| slot_types | Trouvé sur                          | Hypothèse                    |
|------------|-------------------------------------|------------------------------|
| 00000000   | Goblin, Shaman, Bat, Trent, Wisp   | Base set (varie par entité)  |
| 02000000   | Goblin-Shaman                       | Sleep spell set              |
| 03000000   | Goblin-Shaman (Tower)               | Variant Tower                |
| 00000a00   | Bat, Ghost, Wraith                  | Flying + spell set           |
| 00000100   | Bat, Arch-Magi                      | Rare variant                 |

### Révision de l'Hypothèse

❌ **FAUX:** `00000000` = pas de sorts
✅ **VRAI:** `00000000` = set de sorts BASE (différent selon l'entité)

**Preuve:**
- Trent a `00000000` mais lance des sorts
- Will-O-The-Wisp a `00000000` mais lance des sorts
- Goblin-Shaman peut avoir `00000000` ET `02000000`

**Système Révisé:**
```
Sorts Finaux = Sorts de Base (entité) + Modificateur (slot_types)

Même entité + différents modificateurs = différents spell sets

Exemples:
  Shaman (byte[8]=1) + 02000000 → Sleep
  Shaman (byte[8]=1) + 00000a00 → FireBullet (confirmé)
  Shaman (byte[8]=1) + 00000000 → ? (à tester)
  Shaman (byte[8]=1) + 03000000 → ? (à tester)
```

---

## Tests en Cours

### Configuration Actuelle (Cavern F1 A1)

**Formation 0 @ 0xF7AFFC:**
- 3x Shaman (byte[8]=0x01)
- Prefix: `00000000` (Goblin base set)
- **Test:** Est-ce que Shamans perdent leurs sorts? Ou ont un set différent?

**Formation 1 @ 0xF7B060:**
- 3x Shaman (byte[8]=0x01)
- Prefix: `03000000` (Tower variant)
- **Test:** Quel spell set donne cette valeur rare?

**Formation 2 @ 0xF7B0C4:**
- 3x Goblin (byte[8]=0x00)
- Prefix: `02000000` (Shaman set)
- **Test:** Est-ce que les Goblins peuvent lancer Sleep?!

### Procédure de Test In-Game

1. **Charger le BIN patché:**
   - `output\Blaze & Blade - Patched.bin`

2. **Aller à Cavern Floor 1 Area 1**

3. **Déclencher chaque formation:**
   - Formation 0: Vérifier sorts Shamans (expect base set)
   - Formation 1: Vérifier sorts Shamans (expect Tower variant)
   - Formation 2: Vérifier si Goblins lancent des sorts!

4. **Pour chaque test:**
   - Entrer en combat
   - Ouvrir menu sorts/actions
   - Noter TOUS les sorts disponibles
   - Comparer avec vanilla

5. **Documenter:**
   - Slot_types testé
   - Entité (byte[8])
   - Liste complète des sorts
   - Changements visuels/AI (devrait être aucun si byte[8] correct)

---

## Comment Utiliser le Système

### Pour Modifier les Sorts d'un Monstre

**Méthode 1: Via Formations Custom (JSON)**

1. Éditer `Data/formations/<level>/floor_X_area_Y.json`
2. Modifier `formations[N]["slots"]` avec les monstres désirés
3. **SUPPRIMER** le champ `vanilla_records` (force génération synthétique)
4. Lancer `extract_slot_types.py` pour mettre à jour les slot_types
5. **Modifier manuellement** les slot_types pour les spell sets désirés
6. Build et test

**Exemple: Donner FireBullet aux Shamans**
```json
{
  "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
  "slot_types": ["00000000", "00000a00", "00000a00"],
                                     ^^^ Changer de 02000000 à 00000a00
  "formations": [
    {
      "total": 3,
      "slots": [1, 1, 1]  // 3x Shaman
    }
  ]
}
```

**Méthode 2: Patch Direct BLAZE.ALL**

Utiliser les scripts de test:
- `test_slot_types_spells.py` - Test simple (3 options)
- `test_slot_types_comprehensive.py` - Test multi-formations

**Méthode 3: Modifier le Patcher**

Dans `patch_formations.py`, fonction `build_record()`:
```python
# Au lieu de:
rec[0:4] = prefix

# Utiliser:
rec[0:4] = custom_spell_set_table[desired_spell_set]
```

### Créer une Table de Modificateurs

**Étape 1:** Tester tous les slot_types sur plusieurs entités
**Étape 2:** Documenter quel slot_types donne quels sorts
**Étape 3:** Créer mapping:
```python
SPELL_SETS = {
    "sleep": bytes.fromhex("02000000"),
    "firebullet": bytes.fromhex("00000a00"),
    "tower_variant": bytes.fromhex("03000000"),
    "base": bytes.fromhex("00000000"),
}
```

**Étape 4:** Appliquer dans formations custom

### Possibilités Créatives

1. **Goblins lanceurs de sorts** (slot 0 + prefix 02000000)
2. **Shamans volants avec FireBullet** (slot 1 + prefix 00000a00) ✅ confirmé
3. **Mélanger spell sets** entre différentes entités
4. **Créer des variants d'ennemis** dans la même area
5. **Boss fights uniques** avec spell sets custom

---

## Prochaines Étapes

### Tests Immédiats (En Attente de Résultats)

- [ ] Formation 0: Shamans + 00000000 → ? sorts
- [ ] Formation 1: Shamans + 03000000 → ? sorts
- [ ] Formation 2: Goblins + 02000000 → Peuvent lancer Sleep?

### Tests Futurs

1. **Tester toutes les valeurs uniques:**
   - 00000100 (Arch-Magi variant)
   - Autres valeurs rares trouvées dans l'analyse

2. **Tester sur d'autres entités:**
   - Bats avec différents prefixes
   - Goblins avec tous les spell sets
   - Monsters non-casters avec spell sets casters

3. **Mapper spell sets complets:**
   - Créer table exhaustive slot_types → sorts
   - Identifier patterns dans les bytes

4. **Tests de limites:**
   - Valeurs invalides/custom (ex: FFFFFFFF)
   - Comportement avec prefix non-matché à l'entité

### Documentation à Compléter

1. **Table complète des spell sets** après tous les tests
2. **Guide utilisateur** pour créer formations avec sorts custom
3. **Patcher étendu** avec support spell set override
4. **Exemples de formations** avec builds créatifs

---

## Références

### Scripts

- `test_slot_types_spells.py` - Test simple (3 valeurs sur Shaman)
- `test_slot_types_comprehensive.py` - Test multi-formations actuel
- `analyze_caster_slot_types.py` - Analyse des 41 areas
- `extract_slot_types.py` - Extraction slot_types vanilla

### Documentation

- `SPELL_SYSTEM_DISCOVERY.md` - Découverte initiale et protocole
- `FORMATIONS_PATCHER_FIX.md` - Fix du bug original
- `CUSTOM_FORMATIONS_WORKING.md` - Guide formations custom

### Commits Git

- `8ad1717` - Patcher avec bug (byte[0:4] hardcodé)
- `07c094a` - Fix complet (utilise slot_types corrects)

### Memory

- `memory/MEMORY.md` - Section "Formation Patcher"
- Résultats tests confirmés documentés

---

## Notes de Recherche

### Observations Non-Résolues

1. **byte[10:23] = tous zéros**
   - Confirmé sur TOUS les spell casters vanilla
   - Pas de données de sorts dans les records
   - Sorts doivent être dans EXE ou référencés indirectement

2. **Valeur 00000100 rare**
   - Trouvée sur Arch-Magi et certains Bats
   - Possiblement: tier supérieur de sorts?
   - À tester

3. **Pattern dans les bytes**
   - byte[0] = 00/02/03 → type de sorts?
   - byte[2] = 00/0a/01 → flags (vol, tier)?
   - Hypothèse à vérifier avec plus de tests

### Questions Ouvertes

1. Le système permet-il des valeurs custom non-vanilla?
2. Y a-t-il une limite au nombre de spell sets différents?
3. Les slot_types affectent-ils autre chose que les sorts?
4. Peut-on créer de NOUVEAUX spell sets en modifiant l'EXE?

---

**Dernière mise à jour:** 2026-02-12
**Tests en cours:** Formation 0, 1, 2 (Cavern F1 A1)
**Résultats confirmés:** 1/3 (Bat prefix sur Shaman → FireBullet ✅)
