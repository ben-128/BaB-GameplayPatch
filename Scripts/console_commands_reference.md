# Console Commands Reference - PSX Debugging

## DuckStation Dev Console (Ctrl+`)

### Breakpoints & Watchpoints

```bash
# Breakpoint d'exécution
break <address>                    # Break when PC reaches address
break 0x80024494                   # Exemple

# Watchpoints (memory access)
watch <address> r                  # Break on READ
watch <address> w                  # Break on WRITE
watch <address> rw                 # Break on READ or WRITE
watch 0x800B2260 rw               # Exemple

# Gestion
breakpoints                        # Liste tous les breakpoints
delete <id>                        # Supprime breakpoint par ID
clear                             # Supprime TOUS les breakpoints

# Logging (sans break)
break <addr> log "message"        # Log au lieu de break
```

### Execution Control

```bash
# Step
step                              # Execute 1 instruction (step INTO)
next                              # Execute 1 instruction (step OVER JAL)
continue                          # Reprendre l'exécution normale
c                                 # Alias pour continue

# Jump
jump <address>                    # Force PC to address (DANGEROUS!)
```

### Inspection

```bash
# Registres
regs                              # Afficher tous les registres
reg <name>                        # Afficher un registre spécifique
reg $a0                           # Exemple

# Mémoire
dump <address> <length>           # Dump memory (hex)
dump 0x800B2100 256              # Dump 256 bytes

# Disassembly
disasm <address> <count>          # Disassemble N instructions
disasm 0x80024494 20             # Disassemble 20 instructions
```

### Registers Reference

```
# Arguments (caller → callee)
$a0 - $a3      # Function arguments 1-4

# Return values
$v0 - $v1      # Function return values

# Temporaries (volatile)
$t0 - $t9      # Temporary registers (lost after JAL)

# Saved (persistent)
$s0 - $s7      # Saved registers (preserved across calls)

# Special
$sp            # Stack pointer
$ra            # Return address (for JAL/JR)
$gp            # Global pointer
$pc            # Program counter
```

---

## PCSX-Redux GUI Debugger

### Breakpoints Window

```
1. Debug → Show Debug Window
2. Onglet "Breakpoints"
3. Clic droit → Add Breakpoint
   - Address: 0x80024494
   - Type: Execute / Read / Write
   - Condition: (optional) $a3 == 10
   - Action: Break / Log / Both
```

### Disassembly View

```
- Clic droit sur une instruction → Toggle Breakpoint
- Double-clic sur instruction → Jump to address
- Ctrl+G → Go to address
```

### Memory Editor

```
1. Onglet "Memory"
2. Address: 0x800B2100
3. Format: Hex / ASCII / Int / Float
4. Cocher "Auto Update" pour live view
5. Clic droit → Add Watchpoint
```

### CPU State

```
Visible en permanence:
- Registres (mise à jour live)
- Flags
- PC (program counter)
- Disassembly window suit automatiquement
```

---

## Workflow Patterns

### Pattern 1: Trouver un Appel de Fonction

```bash
# 1. Poser BP sur la fonction
break 0x80024F90

# 2. Trigger in-game
# (game breaks)

# 3. Inspecter les arguments
regs
# $a0 = arg1, $a1 = arg2, etc.

# 4. Backtracer l'appelant
# Regarder $ra (return address)
reg $ra
# → 0x8007????

# 5. Disassemble l'appelant
disasm 0x8007???? 20
# Trouver le JAL qui a appelé 0x80024F90
```

### Pattern 2: Tracer une Variable

```bash
# 1. Poser watchpoint sur l'adresse
watch 0x800B2260 rw

# 2. Trigger in-game
# (breaks à chaque accès)

# 3. Pour chaque break, noter:
regs                              # Qui accède? ($s1, $a0?)
disasm $pc 5                      # Quelle instruction?
continue                          # Next break

# 4. Créer un log manuel:
# Access 1: lhu at 0x800244F8, entity=$s1
# Access 2: sw at 0x80024500, entity=$s1
```

### Pattern 3: Comparer Deux Runs

```bash
# Setup
1. Sauvegarder savestate "test_vanilla"
2. Poser breakpoint
3. Trigger → noter les valeurs
4. Charger patch modifié
5. Sauvegarder savestate "test_modded"
6. Reposer MEMES breakpoints
7. Trigger → noter les valeurs
8. Comparer

# Exemple log:
# Vanilla run:
#   BP @ 0x80024494: $a0=0x800B2100, $a1=0x05 (Sleep?)
#   entity+0x160 = 0x00000042 (bitmask)
#
# Modded run (suffix=00000a00):
#   BP @ 0x80024494: $a0=0x800B2100, $a1=0x03 (FireBullet?)
#   entity+0x160 = 0x0000008A (bitmask DIFFERENT!)
```

### Pattern 4: Tracer un Calcul

```bash
# Exemple: Tracer damage calculation

# 1. BP sur damage function
break 0x80024F90

# 2. Quand ça break:
regs
# $a3 = damage_param (10 = 10%)

# 3. Step through pour voir le calcul
step
regs     # après chaque instruction
step
regs
# ...

# 4. Noter les étapes:
# mult $a1, $a3        → $a1=100, $a3=10 → HI/LO = 1000
# mflo $a1            → $a1 = 1000
# mult $a1, $v0       → $a1=1000, $v0=0x51EB851F (magic /100)
# mfhi $t0            → $t0 = 10 (result of /100)
```

---

## Advanced: Conditional Breakpoints (PCSX-Redux)

### Syntax

```
Condition field examples:

# Registre equals
$a3 == 10

# Registre comparison
$v0 > 0

# Memory comparison
*(u32*)0x800B2260 == 0x00000042

# Complex
($a3 == 10) && ($a0 == 0x800B2100)
```

### Use Cases

```
# Break seulement pour falling rock damage (10%)
Address: 0x80024F90
Condition: $a3 == 10
Action: Break

# Break seulement quand Shaman cast
Address: 0x80024494
Condition: *(u16*)($a0+0x12) == 3  # entity+0x12 = identity (3=Shaman)
Action: Break

# Log toutes les HP changes mais break seulement si HP < 50
Address: 0x800F014C (player HP)
Condition: *(u16*)0x800F014C < 50
Action: Log + Break
```

---

## Tips & Tricks

### Tip 1: Sauvegarder les Sessions de Debug
```
# Créer un fichier texte avec les commandes:
debug_session_spells.txt:
  break 0x80024494
  break 0x800244f4
  watch 0x800B2260 rw

# Copier/coller tout le contenu dans la console au startup
```

### Tip 2: Calculer des Adresses
```
# Python quick calc
python -c "print(hex(0x800B1E80 + 0x160))"
# → 0x800b1fe0

# Ou dans la console DuckStation (si supporté)
# calc 0x800B1E80 + 0x160
```

### Tip 3: Identifier les Fonctions
```
# Quand vous trouvez une fonction intéressante:
1. Noter l'adresse: 0x800244F4
2. Nommer dans vos notes: "level_sim_loop"
3. Créer un alias dans breakpoint_helper.py
4. Documenter dans WIP/*/CODE_LOCATIONS.md
```

### Tip 4: Watch Large Ranges
```
# Si vous ne savez pas QUELLE entité est touchée:
# Poser un watchpoint sur TOUTE la zone entity array

watch 0x800B1E80 rw   # Start of entity array
# → va break SOUVENT mais catchera tout

# Puis affiner avec:
watch 0x800B2100 rw   # Entité spécifique
```

### Tip 5: Use Savestates Agressivement
```
# Créer des savestates à des points clés:
- "before_combat_shaman"
- "shaman_just_spawned"
- "shaman_about_to_cast"
- "spell_missile_midair"

# Permet de replay exactement le même événement
```

---

## Common Addresses (Blaze & Blade)

### EXE (Fixed)
```
0x80024F90    damage_function
0x80024494    action_dispatch
0x800244F4    level_sim_loop
0x80021E68    entity_init
```

### Runtime (Examples)
```
0x800B1E80    entity_array base
0x800F0000    player_0_block
0x800F014C    player_0_cur_hp
0x800F0148    player_0_max_hp
```

### BLAZE.ALL Offsets (add 0x80000000 for RAM if loaded there)
```
0x908E68      spell_table_type0
0x009ECFEC    falling_rock_descriptor
```

---

## See Also

- `DEBUGGING_GUIDE.md` - Setup complet
- `breakpoint_helper.py` - Générateur de commandes
- `debug_spells_workflow.md` - Workflow exemple complet
- `memory/MEMORY.md` - Addresses confirmées par testing
