# Debug Cheat Sheet - Commandes Rapides

## Startup Rapide

### 1. Générer Breakpoints
```bash
# Tous
python Scripts/breakpoint_helper.py > Scripts/debug_sessions/current.txt

# Spells seulement
python Scripts/breakpoint_helper.py --mode spells

# Entity watchpoints (après avoir trouvé base address)
python Scripts/breakpoint_helper.py --entity-base 0x800B2100 --entity-fields timer bitmask
```

### 2. Charger Session Prédéfinie
```bash
# Ouvrir le fichier de session correspondant:
Scripts/debug_sessions/spell_research.txt
Scripts/debug_sessions/trap_damage.txt
Scripts/debug_sessions/chest_timer.txt

# Copier/coller dans DuckStation console (Ctrl+`)
```

---

## Commandes Console les Plus Utilisées

### Setup
```
break 0x80024494          # Spell dispatch
break 0x80024F90          # Damage function
watch 0x800B2260 rw       # Entity bitmask (example)
breakpoints               # Lister les BPs actifs
```

### Runtime
```
regs                      # Afficher tous les registres
reg $a0                   # Registre spécifique
dump 0x800B2100 256       # Dump 256 bytes
disasm 0x80024494 20      # Disassemble 20 instructions
```

### Stepping
```
step                      # 1 instruction (step into JAL)
next                      # 1 instruction (step over JAL)
continue                  # Reprendre (ou 'c')
```

### Cleanup
```
delete 1                  # Supprime breakpoint #1
clear                     # Supprime TOUS les breakpoints
```

---

## Addresses les Plus Courantes

### EXE (Fixed - jamais bougent)
```
0x80024F90    damage_function
0x80024494    action_dispatch
0x800244F4    level_sim_loop (bitmask)
0x80021E68    entity_init
```

### Runtime (Examples - calculer pour chaque entity)
```
0x800B1E80    entity_array_base
0x800B2100    entity[N] example
0x800B2114    entity[N]+0x14 (timer)
0x800B2260    entity[N]+0x160 (bitmask)

0x800F0000    player_0_block
0x800F014C    player_0_cur_hp
0x800F2000    player_1_block
```

---

## Workflows Ultra-Rapides

### W1: "Je veux voir quand un Shaman cast"
```
1. break 0x80024494
2. F2 (savestate avant combat)
3. Trigger combat
4. regs → noter $a0 (entity), $a1 (spell_id?)
5. dump $a0 256 → voir entity data
```

### W2: "Je veux tracer le bitmask d'une entity"
```
1. break 0x80024494
2. Trigger combat → noter $a0 (ex: 0x800B2100)
3. clear
4. watch 0x800B2260 rw (0x800B2100 + 0x160)
5. F1 (reload savestate)
6. continue → observe tous les accès au bitmask
```

### W3: "Je veux backtracer un damage call"
```
1. break 0x80024F90
2. Trigger damage
3. regs → $a3=damage%, $ra=return_address
4. disasm $ra-20 40 → voir le code appelant
5. Chercher le JAL 0x80024F90
6. Avant JAL: chercher où $a3 est chargé
```

### W4: "Je veux voir toutes les writes sur HP"
```
1. watch 0x800F014C w (player 0 cur_hp)
2. continue
3. À chaque break:
   - regs → voir qui écrit ($ra pour caller)
   - disasm $pc 5 → voir l'instruction
   - continue
```

### W5: "Je veux comparer vanilla vs patched"
```
# Vanilla
1. Charger vanilla BLAZE.ALL.cue
2. break 0x80024494
3. F2 "test_vanilla"
4. Trigger → noter $a1, dump entity+0x160
5. F4 "results_vanilla.txt"

# Patched
6. Charger patched BLAZE.ALL.cue
7. break 0x80024494
8. F2 "test_patched"
9. Trigger → noter $a1, dump entity+0x160
10. F4 "results_patched.txt"

# Diff
11. Compare results_vanilla.txt vs results_patched.txt
```

---

## Calculateurs Rapides

### Entity Field Address
```python
# Python one-liner
python -c "print(hex(0x800B2100 + 0x160))"
# → 0x800b2260 (bitmask address)
```

### Player Field Address
```python
# Player 0
python -c "print(hex(0x800F0000 + 0x14C))"
# → 0x800f014c (cur_hp)

# Player 1
python -c "print(hex(0x800F2000 + 0x14C))"
# → 0x800f214c (cur_hp)
```

---

## Registres MIPS Référence Rapide

```
$a0-$a3     Arguments 1-4
$v0-$v1     Return values
$t0-$t9     Temporaries (volatile)
$s0-$s7     Saved (persistent)
$ra         Return address
$sp         Stack pointer
$pc         Program counter
```

---

## Patterns de Code Courants

### JAL Call
```
# Avant le JAL: setup arguments
li   $a3, 10              # $a3 = 10 (immediate)
move $a2, $s0             # $a2 = $s0 (register)
lw   $a1, 0x160($s1)      # $a1 = entity+0x160 (memory)

# Le call
jal  0x80024F90           # Call fonction

# Après: return value
move $t0, $v0             # $t0 = return value
```

### Bitmask Accumulation
```
lw   $v0, <offset>($s1)   # Load un bout du bitmask
or   $v1, $v1, $v0        # Accumulate avec OR
sw   $v1, 0x160($s1)      # Store bitmask final
```

### Timer Decrement
```
lhu  $v0, 0x14($s1)       # Load timer (u16)
addiu $v0, $v0, -1        # Decrement
sh   $v0, 0x14($s1)       # Store timer
```

---

## Snippets de Log Standardisés

### Log de Breakpoint
```
=== Break @ 0x80024494 (spell_dispatch) ===
Time: 12:34:56
Registers:
  $a0 = 0x800B2100 (entity)
  $a1 = 0x05 (spell_id?)
  $a2 = 0x800B2300 (target?)
  $a3 = 0x00

Entity dump (first 32 bytes):
  0x800B2100: 47 6F 62 6C 69 6E 00 00  (name: "Goblin")
  ...

Next steps:
  - Watch entity+0x160 for bitmask changes
  - Compare with vanilla run
```

### Log de Watchpoint
```
=== Watchpoint @ 0x800B2260 (entity+0x160) ===
Access: WRITE
PC: 0x80024500
Instruction: sw $v1, 0x160($s1)
Value written: 0x00000042
Previous value: 0x00000000

Context:
  - Inside level_sim_loop (0x800244F4-0x80024510)
  - Accumulating bitmask for spell availability
```

---

## Tips Ultra-Pro

### Tip: Automatiser les Sessions
Créer un fichier `my_session.txt`:
```
break 0x80024494
break 0x800244F4
watch 0x800F014C w
```

Copier/coller tout le fichier d'un coup dans la console au startup.

### Tip: Nommage de Savestates
Convention: `<system>_<state>_<variant>.state`
```
spell_before_cast_vanilla.state
spell_before_cast_bat_suffix.state
spell_before_cast_tower_suffix.state
```

### Tip: Logging Multi-Run
```bash
# Run 1
DuckStation → log to "run1.txt"
# Run 2
DuckStation → log to "run2.txt"
# Compare
diff run1.txt run2.txt
```

### Tip: Marker Comments dans Savestates
DuckStation permet de nommer les savestates.
Utiliser des noms descriptifs:
- "CHEST_JUST_SPAWNED"
- "SHAMAN_ABOUT_TO_CAST"
- "HP_LOW_BEFORE_TRAP"

---

## See Also

- `DEBUGGING_GUIDE.md` - Guide complet
- `breakpoint_helper.py` - Générateur de commandes
- `debug_spells_workflow.md` - Workflow détaillé
- `console_commands_reference.md` - Référence complète
- `debug_sessions/*.txt` - Sessions prédéfinies
