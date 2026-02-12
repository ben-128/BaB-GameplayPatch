# Workflow: Débugger le Système de Sorts

## Objectif
Comprendre comment byte[0:4] (prefix/suffix) modifie la spell list d'une entité.

## Setup

### 1. Préparer le Patch
```bash
# Modifier une formation pour tester
cd Data/formations/cavern_of_death
# Editer floor_1_area_1.json - Formation 0, changer suffix du Shaman
```

### 2. Builder le Patch
```bash
build_gameplay_patch.bat
# Vérifie que output/BLAZE.ALL existe
```

### 3. Lancer DuckStation
```
1. Ouvrir DuckStation
2. Settings → Console → Enable Dev Console
3. Charger output/BLAZE.ALL.cue
4. Ctrl+` pour ouvrir la console
```

## Phase 1: Poser les Breakpoints

### Générer les Commandes
```bash
python Scripts/breakpoint_helper.py --mode spells
```

### Copier dans DuckStation Console
```
break 0x80024494  # Spell dispatch
break 0x800244f4  # Bitmask accumulation
```

### Vérifier
```
breakpoints
# Doit afficher les 2 breakpoints actifs
```

## Phase 2: Setup du Test In-Game

### 1. Aller à Cavern F1 Area 1
```
- Créer nouveau personnage (ou charger save)
- Naviguer jusqu'à Cavern of Death
- Entrer Floor 1
```

### 2. Sauvegarder AVANT le Combat
```
Dans DuckStation:
- F2 (Quick Save) → Nommer "shaman_test_before_combat"
- Positionner le perso juste avant la zone de spawn
```

## Phase 3: Déclencher et Observer

### 1. Entrer en Combat
```
- Avancer pour trigger la formation
- Le breakpoint à 0x80024494 doit s'activer quand le Shaman cast
```

### 2. Quand ça Break - Inspecter les Registres
```
regs
```

**Registres importants:**
- `$a0` = entity pointer (ex: 0x800B2100)
- `$a1` = action_id ou spell_id?
- `$a2` = target?
- `$a3` = param?

### 3. Sauvegarder les Valeurs
```
# Noter dans un fichier texte:
Entity pointer: $a0 = 0x800B2100
Spell ID?: $a1 = 0x??
```

### 4. Inspecter l'Entity Structure
```
# Dump entity data (256 bytes)
dump 0x800B2100 256

# Vérifier les champs clés:
# +0x00 = name (16 bytes ASCII)
# +0x144 = level (u16)
# +0x160 = bitmask (u32)
# +0x2B5 = creature_type (u8)
```

### 5. Tracer le Bitmask
```
# Le deuxième breakpoint (0x800244f4) s'active pendant level-up sim
# C'est là que le bitmask est calculé

step  # Execute 1 instruction à la fois
regs  # Voir comment le bitmask évolue

# Chercher les instructions:
# lw (load bitmask piece)
# or (accumulate into bitmask)
# sw (store final bitmask)
```

## Phase 4: Watchpoints Dynamiques

### 1. Calculer Adresses des Champs
```
# Entity base = $a0 du breakpoint précédent (ex: 0x800B2100)
python Scripts/breakpoint_helper.py \
  --entity-base 0x800B2100 \
  --entity-fields bitmask level
```

### 2. Appliquer les Watchpoints
```
# Output du script:
watch 0x800B2260 rw  # entity+0x160 (bitmask)
watch 0x800B2244 rw  # entity+0x144 (level)
```

### 3. Recharger et Réessayer
```
F1 (Quick Load) → "shaman_test_before_combat"
continue  # Reprendre l'exécution

# Maintenant les watchpoints vont break à CHAQUE accès au bitmask!
```

## Phase 5: Comparer Vanilla vs Modifié

### Test 1: Vanilla (suffix = 02000000)
```
1. Charger vanilla BLAZE.ALL
2. Répéter Phase 2-4
3. Noter: bitmask value, spell cast
```

### Test 2: Bat Suffix (suffix = 00000a00)
```
1. Modifier floor_1_area_1.json:
   "suffix": "00000a00"  # Bat spell modifier
2. build_gameplay_patch.bat
3. Répéter Phase 2-4
4. Noter: bitmask value, spell cast (devrait être FireBullet)
```

### Test 3: Tower Suffix (suffix = 03000000)
```
1. Modifier suffix = 03000000
2. Rebuild + test
3. Noter: spell cast (devrait inclure Heal)
```

### Comparer les Résultats
```
| Suffix     | Bitmask   | Spells Cast            |
|------------|-----------|------------------------|
| 02000000   | 0x????    | Sleep, Magic Missile   |
| 00000a00   | 0x????    | FireBullet, Stone Bul. |
| 03000000   | 0x????    | Sleep, Heal            |
```

## Phase 6: Tracer le Code de Lookup

### Trouver où le Suffix est Lu
```
# Hypothèse: le dispatch lit le suffix depuis formation data
# Pour trouver où:

1. Poser watchpoint sur l'adresse du suffix dans BLAZE.ALL
   - Cavern F1 A1 formation 0 suffix @ offset ??
   - Calculer RAM address (0x800????? + offset)

2. watch <suffix_ram_addr> r  # Read watchpoint

3. Trigger combat → doit break quand le jeu lit le suffix

4. Backtrace avec "step out" pour trouver la fonction parent
```

### Alternative: Pattern Search
```
# Chercher dans le disassembly pour:
# - Load depuis formation area (LW from 0xF7A???)
# - Compare/switch sur la valeur 02000000/00000a00/03000000
# - JAL vers spell list setup
```

## Phase 7: Documentation

### Créer un Mapping
```
Data/formations/SUFFIX_TO_SPELLS_MAP.md:

| Suffix   | Spell Set Name | Spells                    |
|----------|----------------|---------------------------|
| 00000000 | Base/Goblin    | None (melee only)         |
| 02000000 | Shaman/Caster  | Sleep, MM, Stone Bullet   |
| 03000000 | Tower Variant  | Sleep, Heal, MM           |
| 00000a00 | Flying/Bat     | FireBullet, Stone Bullet  |
| 00000100 | Rare/Magi      | (unknown - needs testing) |
```

### Code Location Log
```
WIP/spell_sets_and_ai/CODE_LOCATIONS.md:

## Dispatch Function
- Address: 0x80024494
- Purpose: Route spell/action based on entity state
- Registers: $a0=entity, $a1=action_id

## Level-up Sim Loop
- Address: 0x800244f4
- Purpose: Accumulate spell bitmask based on level
- Pattern: lw/or/sw loop, sentinel=9999

## Suffix Lookup (FOUND)
- Address: 0x???????? (TODO)
- Purpose: Read suffix from formation data
- Maps: suffix value → spell_list_index
```

---

## Commandes de Référence Rapide

### DuckStation Console
```
# Setup
break <addr>              # Breakpoint d'exécution
watch <addr> rw           # Watchpoint lecture/écriture
breakpoints               # Liste les BPs actifs
clear                     # Supprime tous les BPs

# Runtime
regs                      # Afficher registres
dump <addr> <len>         # Dump mémoire
step                      # 1 instruction
next                      # Step over JAL
continue                  # Reprendre
```

### Breakpoint Helper
```bash
# Tous les breakpoints
python Scripts/breakpoint_helper.py

# Mode spécifique
python Scripts/breakpoint_helper.py --mode spells

# Entity watchpoints
python Scripts/breakpoint_helper.py \
  --entity-base 0x800B2100 \
  --entity-fields bitmask level timer

# Player watchpoints
python Scripts/breakpoint_helper.py \
  --player 0 \
  --player-fields cur_hp max_hp level
```

---

## Troubleshooting

### Breakpoint ne s'active jamais
```
- Vérifier que l'adresse est correcte (EXE vs overlay)
- Vérifier que l'événement est bien triggeré (savestate avant)
- Essayer un watchpoint large zone (watch 0x800B0000 rw)
```

### Trop de Breaks (watchpoint trop actif)
```
- Utiliser des breakpoints conditionnels (PCSX-Redux)
- Ou poser le watchpoint APRÈS l'init (quand entity existe)
```

### Confusion Registres
```
- $a0-$a3 = arguments de fonction
- $v0-$v1 = return values
- $s0-$s7 = saved registers (persistent entre appels)
- $t0-$t9 = temporary (perdus entre appels)
```

### Watchpoint sur Mauvaise Entité
```
# Si plusieurs entities du même type:
1. Calculer l'adresse exacte avec entity array index
2. Ou ajouter un check manuel quand ça break:
   regs → vérifier que $s1 (ou autre) = entity attendue
```
