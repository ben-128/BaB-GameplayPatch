# Guide: Changer les Spell Sets des Monstres

## Outil en Ligne de Commande (Recommandé)

### Utilisation

```bash
cd Data/formations/Scripts
py -3 change_spell_sets.py
```

### Interface Interactive

L'outil vous guide à travers:

1. **Sélection de l'area**
   - Liste toutes les areas disponibles par level
   - Affiche les spell sets actuels

2. **Modification des spell sets**
   - Sélectionner quels monstres modifier (par slot number)
   - Choisir le nouveau spell set dans la liste
   - Option "all" pour modifier tous les monstres

3. **Sauvegarde**
   - Crée un backup automatique (_user_backup.json)
   - Sauvegarde les changements dans le JSON

### Exemple de Session

```
Available Areas
======================================================================

cavern_of_death:
  1. Floor 1 Area 1
  2. Floor 1 Area 2
  ...

Select area number: 1

Current Spell Sets:
----------------------------------------------------------------------
  Slot 0: Lv20.Goblin
    slot_types: 00000000 (Base/Goblin)
    Spells: (varies by entity) / Magic Missile / Stone Bullet

  Slot 1: Goblin-Shaman
    slot_types: 02000000 (Vanilla Shaman)
    Spells: Sleep / Magic Missile / Stone Bullet

  Slot 2: Giant-Bat
    slot_types: 00000a00 (Bat/Flying)
    Spells: FireBullet / Magic Missile / Stone Bullet

Modify Spell Sets
======================================================================
Slots to modify (or 'done' to finish): 1

Selected monsters:
  Slot 1: Goblin-Shaman

Available Spell Sets
======================================================================
1. Vanilla Shaman (02000000)
   Spells: Sleep / Magic Missile / Stone Bullet
   Default Shaman spells

2. Tower Variant (03000000)
   Spells: Sleep / Magic Missile / Heal
   Support variant with Heal

3. Bat/Flying (00000a00)
   Spells: FireBullet / Magic Missile / Stone Bullet
   Aggressive flying spell set

4. Base/Goblin (00000000)
   Spells: (varies by entity) / Magic Missile / Stone Bullet
   Base spell set (no spells for melee monsters)

5. Rare Variant (00000100)
   Spells: (untested) / (untested) / (untested)
   Rare variant (Arch-Magi)

Select spell set number: 3

  Slot 1 (Goblin-Shaman): Vanilla Shaman -> Bat/Flying

Changes applied! Continue modifying or type 'done'.

Slots to modify: done

Summary of Changes
======================================================================
  Slot 0: Lv20.Goblin
    Base/Goblin - (varies by entity) / Magic Missile / Stone Bullet
  Slot 1: Goblin-Shaman
    Bat/Flying - FireBullet / Magic Missile / Stone Bullet
  Slot 2: Giant-Bat
    Bat/Flying - FireBullet / Magic Missile / Stone Bullet

Save changes to JSON? (y/n): y

  Backup created: floor_1_area_1_user_backup.json

======================================================================
  Changes Saved!
======================================================================

Next steps:
  1. Run formation patcher: py -3 Data/formations/Scripts/patch_formations.py
  2. Build full patch: build_gameplay_patch.bat
  3. Test in-game!
```

---

## Spell Sets Disponibles

### 1. Vanilla Shaman (02000000)
- **Spell 1:** Sleep
- **Spell 2:** Magic Missile
- **Spell 3:** Stone Bullet
- **Description:** Spell set par défaut du Goblin-Shaman

### 2. Tower Variant (03000000) ✅ Confirmé
- **Spell 1:** Sleep
- **Spell 2:** Magic Missile
- **Spell 3:** **Heal**
- **Description:** Variant support avec sort de soin

### 3. Bat/Flying (00000a00) ✅ Confirmé
- **Spell 1:** **FireBullet**
- **Spell 2:** Magic Missile
- **Spell 3:** Stone Bullet
- **Description:** Spell set agressif (vole + attaque feu)

### 4. Base/Goblin (00000000) ✅ Confirmé
- **Spell 1:** (varie selon l'entité)
- **Spell 2:** Magic Missile
- **Spell 3:** Stone Bullet
- **Description:** Spell set de base
- **Note:** Sur Shaman donne **FireBullet**, sur Goblin = pas de sorts

### 5. Rare Variant (00000100) ❓ Non testé
- **Spells:** Inconnus
- **Description:** Trouvé sur Arch-Magi (Tower A11)
- **À tester!**

---

## Important: Limitations

### ✅ Fonctionne
- Changer spell sets sur **monsters casters** (Shaman, Bat, Ghost, Trent, etc.)
- Mélanger spell sets entre différents monsters casters
- Utiliser slot_types custom sur formations différentes (même area)

### ❌ Ne fonctionne PAS
- Donner des sorts à des **monsters melee** (Goblin, Lizard, etc.)
  - Le monster doit avoir une capacité de base pour lancer des sorts
  - slot_types ne peut PAS transformer un melee en caster

### ⚠️ Prudence
- Toujours **tester in-game** après modification
- Garder le **backup JSON** au cas où
- Certaines valeurs non testées peuvent causer des bugs

---

## Workflow Complet

### 1. Modifier Spell Sets
```bash
cd Data/formations/Scripts
py -3 change_spell_sets.py
```
- Sélectionner area
- Modifier spell sets désirés
- Sauvegarder

### 2. Patcher Formations
```bash
py -3 patch_formations.py
```
- Le patcher utilise les nouveaux slot_types
- Génère les formations avec spell sets modifiés

### 3. Build Complet
```bash
cd ../../..
build_gameplay_patch.bat
```
- Build le patch complet
- Injecte dans le BIN

### 4. Test In-Game
- Charger le BIN patché
- Aller dans l'area modifiée
- Vérifier spell lists en combat

---

## Exemples d'Utilisation

### Exemple 1: Shamans Agressifs
**Objectif:** Transformer tous les Shamans en attackers agressifs

```
Area: Cavern F1 A1
Modifier: Slot 1 (Goblin-Shaman)
Nouveau spell set: Bat/Flying (00000a00)

Résultat:
  Shamans lancent FireBullet au lieu de Sleep
  Mais gardent leur visuel/stats de Shaman
```

### Exemple 2: Shamans Support
**Objectif:** Créer des Shamans healers

```
Area: Cavern F1 A1
Modifier: Slot 1 (Goblin-Shaman)
Nouveau spell set: Tower Variant (03000000)

Résultat:
  Shamans lancent Heal au lieu de Stone Bullet
  Deviennent des supports pour autres monsters
```

### Exemple 3: Mix dans Même Area
**Objectif:** Différents types de Shamans dans différentes formations

**Solution:** Créer plusieurs formations avec compositions différentes
- Formation 1: Shamans slot 1 (vanilla 02000000)
- Formation 2: Shamans slot 2 (avec slot_types 03000000)

Impossible directement car slot_types s'applique à TOUT le slot dans l'area.

**Workaround:** Utiliser plusieurs areas ou créer variants dans monsters list:
```json
"monsters": [
  "Lv20.Goblin",
  "Goblin-Shaman",      // Vanilla (Sleep)
  "Goblin-Shaman",      // Copie pour Tower variant
  "Giant-Bat"
],
"slot_types": [
  "00000000",
  "02000000",           // Vanilla Shaman
  "03000000",           // Tower Shaman
  "00000a00"
]
```

Puis dans formations:
- Formation avec slot 1 → Sleep
- Formation avec slot 2 → Heal

---

## Dépannage

### "No monsters in this area"
- L'area n'a pas de liste monsters
- Utiliser une area avec formations (pas juste spawn points)

### "Backup already exists"
- Un backup existe déjà (floor_X_area_Y_user_backup.json)
- C'est normal, le backup n'est créé qu'une fois
- Pour reset: supprimer le backup et restaurer depuis vanilla

### Changements ne s'appliquent pas in-game
1. Vérifier que le patcher a tourné sans erreur
2. Vérifier que build_gameplay_patch.bat a réussi
3. Vérifier que le bon BIN est chargé
4. Tester dans la bonne area/formation

### Crash au spawn
- Vérifier que vous modifiez seulement slot_types
- Ne pas modifier la structure des formations
- Laisser le patcher générer les bytes

---

## Références

- **Documentation complète:** `SPELL_SYSTEM_CONFIRMED.md`
- **Recherche originale:** `SPELL_MODIFIER_RESEARCH.md`
- **Formation patcher:** `Scripts/patch_formations.py`
- **Memory notes:** `memory/MEMORY.md`
