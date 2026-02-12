# Guide de Debugging PSX - Breakpoints

## Configuration de l'Émulateur

### Option 1: DuckStation (Recommandé)
**Avantages:** GUI moderne, debugger intégré, savestate rapides
**Installation:**
1. Télécharger DuckStation (dev build avec debugger)
2. Settings → Console → Enable Dev Console
3. Ctrl+` pour ouvrir la console

**Breakpoints dans DuckStation:**
```
# Breakpoint d'exécution
break 0x80024F90

# Breakpoint lecture/écriture (watchpoint)
watch 0x800B1E80 r    # lecture
watch 0x800B1E80 w    # écriture
watch 0x800B1E80 rw   # les deux

# Lister les breakpoints
breakpoints

# Supprimer
delete 1              # supprime breakpoint #1
clear                 # supprime tous

# Stepping
step                  # step into (execute 1 instruction)
next                  # step over (skip JAL)
continue              # reprend l'exécution
```

### Option 2: PCSX-Redux (Pour debugging avancé)
**Avantages:** Meilleur désassembleur, memory editor puissant
**Installation:**
1. Télécharger PCSX-Redux
2. Debug → Show Debug Window
3. Memory Editor + CPU State visible en permanence

**Breakpoints dans PCSX-Redux:**
```
# Dans l'onglet Breakpoints
- Clic droit dans disassembly → Add Breakpoint
- Ou utiliser la fenêtre Breakpoints directement
```

---

## Breakpoints Utiles pour Blaze & Blade

### Combat / Damage System
```bash
# Fonction de dégâts principale (EXE)
break 0x80024F90         # damage calculation
watch 0x800F014C w       # Player HP write (player 0)

# Combat action dispatch
break 0x80024494         # spell/action dispatch
watch 0x800B1E80 rw      # Entity array access
```

### Formation System
```bash
# Formation loading (Cavern F1 - exemple)
break 0xF7AA9C           # Script area start (per-area)
watch 0xF7A964 r         # Assignment table read

# Entity initialization
break 0x80021E68         # Entity descriptor init
watch 0x800B1E80 w       # Entity array write
```

### Spell Casting
```bash
# Shaman spell research
break 0x800244F4         # Level-up sim loop (bitmask accumulation)
watch 0x???????? w       # entity+0x160 (bitmask write - remplacer par adresse runtime)

# Spell list loading
break 0x908E68           # Type 0 spell table (28 Mage spells)
```

### Loot & Timers
```bash
# Chest despawn timer
break 0x800877F4         # Timer decrement (Cavern F1)
watch 0x???????? rw      # entity+0x14 (timer field - runtime address)

# Loot drop rate
break 0x????????         # drop_rate table lookup (remplacer par adresse trouvée)
```

### Trap Damage
```bash
# Trap damage paths
break 0x80024F90         # Damage function (catch all traps)

# Falling rock research (UNSOLVED)
break 0x80021E68         # Entity descriptor init
watch 0x800BF7EC r       # Falling rock descriptor read
```

---

## Techniques de Debugging

### 1. Conditional Breakpoints (PCSX-Redux uniquement)
```
Breakpoint avec condition:
- Address: 0x80024F90
- Condition: $a3 == 10      # Si damage_param == 10%
- Action: Log + Break
```

### 2. Logging sans Break
```
# DuckStation console
break 0x80024F90 log "Damage function called, param=$a3"
```

### 3. Workflow Typique
```
1. Charger le jeu + patch
2. Poser breakpoint AVANT l'événement
3. Sauvegarder un savestate juste avant
4. Trigger l'événement (combat, coffre, trap)
5. Inspecter registres + mémoire
6. Recharger savestate et réessayer
```

### 4. Memory Inspection
```bash
# DuckStation console
dump 0x800B1E80 256      # dump 256 bytes depuis entity array

# PCSX-Redux
# Utiliser Memory Editor GUI avec:
# - Address: 0x800B1E80
# - Format: Hex + ASCII
# - Live update activé
```

### 5. Trouver des Adresses Dynamiques
```
Problème: entity+0x14 est un offset relatif, pas une adresse absolue

Solution:
1. Poser breakpoint sur l'accès (ex: lhu $v0, 0x14($s1))
2. Quand ça break, lire $s1 pour avoir l'adresse de base
3. Ajouter +0x14 pour avoir l'adresse complète
4. Poser watchpoint sur l'adresse complète

Exemple:
- Break at 0x800877F0
- $s1 = 0x800B2000 (base de l'entité coffre)
- entity+0x14 = 0x800B2014
- watch 0x800B2014 w
```

---

## Script d'Aide aux Breakpoints

### breakpoint_helper.py
```python
#!/usr/bin/env python3
"""Helper pour générer des commandes de breakpoints."""

# Addresses importantes (Blaze & Blade)
ADDRESSES = {
    # EXE (fixed)
    "damage_function": 0x80024F90,
    "action_dispatch": 0x80024494,
    "level_sim_loop": 0x800244F4,
    "entity_init": 0x80021E68,

    # Entity runtime (base address examples)
    "entity_array": 0x800B1E80,
    "player_0_block": 0x800F0000,

    # Tables (BLAZE.ALL offsets)
    "spell_table_type0": 0x908E68,
    "falling_rock_desc": 0x009ECFEC,

    # Cavern F1 Area 1 (example)
    "cav_f1a1_assignments": 0xF7A964,
    "cav_f1a1_stats": 0xF7A97C,
    "cav_f1a1_script": 0xF7AA9C,
    "cav_f1a1_chest_timer": 0x800877F4,
}

def generate_duckstation_script():
    """Génère un script de breakpoints pour DuckStation."""
    print("# DuckStation Breakpoint Script")
    print("# Copier/coller dans la console (Ctrl+`)\n")

    print("# === Combat System ===")
    print(f"break {ADDRESSES['damage_function']:#010x}")
    print(f"break {ADDRESSES['action_dispatch']:#010x}")

    print("\n# === Entity System ===")
    print(f"break {ADDRESSES['entity_init']:#010x}")
    print(f"watch {ADDRESSES['entity_array']:#010x} rw")

    print("\n# === Player Data ===")
    print(f"watch {ADDRESSES['player_0_block'] + 0x14C:#010x} w  # HP")

    print("\n# === Cavern F1 Area 1 ===")
    print(f"break {ADDRESSES['cav_f1a1_script']:#010x}")

def entity_offset(base: int, offset: int) -> int:
    """Calcule adresse absolue pour watchpoint entity."""
    return base + offset

if __name__ == "__main__":
    generate_duckstation_script()

    print("\n# === Entity Field Calculator ===")
    print("# Utiliser après avoir trouvé l'adresse de base avec un breakpoint")
    example_base = 0x800B2000
    print(f"\nExemple: entity @ {example_base:#010x}")
    print(f"  +0x14 (timer)  → watch {entity_offset(example_base, 0x14):#010x} rw")
    print(f"  +0x160 (mask)  → watch {entity_offset(example_base, 0x160):#010x} w")
```

Sauvegarder comme `Scripts/breakpoint_helper.py` et exécuter:
```bash
python Scripts/breakpoint_helper.py
```

---

## Workflow pour Votre Recherche Actuelle

### Spell System Testing (spell_sets_and_ai)
```bash
# 1. Charger le patch avec formations modifiées
# 2. Poser breakpoints AVANT le combat
break 0x80024494         # Spell dispatch
break 0x800244F4         # Bitmask accumulation

# 3. Sauvegarder savestate
# 4. Entrer en combat avec Shaman
# 5. Observer:
#    - $a3 (damage_param ou spell_id?)
#    - entity+0x160 (bitmask)
#    - entity+0x144 (level)
```

### Trap Damage (falling rock 10%)
```bash
# 1. Charger la zone avec falling rocks
# 2. Sauvegarder AVANT de déclencher
break 0x80024F90         # Damage function (attrape TOUS les dégâts)

# 3. Déclencher le rocher
# 4. Quand ça break, inspecter $a3 (damage_param)
# 5. Si $a3 == 10, backtracer avec "step out" pour trouver l'appelant
```

---

## Conseils Pro

1. **Toujours sauvegarder un savestate** juste avant de tester
2. **Logs dans un fichier** pour comparer plusieurs runs
3. **Step over (next)** pour les JAL que vous connaissez
4. **Step into (step)** pour explorer du code inconnu
5. **Watch les structures entières** avec plusieurs watchpoints adjacents
6. **Nommer vos savestates** : `chest_just_spawned.state`, `shaman_casting.state`

---

## Ressources

- DuckStation docs: https://github.com/stenzek/duckstation
- PCSX-Redux: https://github.com/grumpycoders/pcsx-redux
- PSX MIPS reference: https://psx-spx.consoledev.net/cpuspecifications/

---

## Notes du Projet

### Addresses Confirmées (à jour 2026-02-12)
Voir `memory/MEMORY.md` pour la liste complète des offsets confirmés par testing in-game.

### TODO Debugging
- [ ] Trouver dispatch pour entity+0x3C descriptors (trap damage)
- [ ] Mapper spell_list_index → spell bitmask relationship
- [ ] Confirmer lien entre byte[0:4] prefix et spell modifier
