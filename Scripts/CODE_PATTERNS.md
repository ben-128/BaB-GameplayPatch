# MIPS Code Patterns - Reconnaissance Rapide

Guide visuel pour reconnaître rapidement les patterns de code dans le disassembly PSX.

---

## 1. Function Call Patterns

### Standard JAL Call
```mips
# Setup arguments
li   $a0, 1                    # arg1 = immediate
move $a1, $s0                  # arg2 = from saved reg
lw   $a2, 0x100($s1)          # arg3 = from memory
addiu $a3, $zero, 10          # arg4 = immediate (10)

# Call
jal  0x80024F90               # Jump And Link

# After call
nop                           # Branch delay slot
move $t0, $v0                 # Save return value
```

**Identification:**
- Séquence de `li/move/lw` vers `$a0-$a3` juste avant `jal`
- `$v0-$v1` utilisés juste après le `jal`

### Indirect Call (Function Pointer)
```mips
lw   $t0, 0x20($s1)           # Load function pointer
nop
jalr $t0                      # Call via register
nop                           # Delay slot
```

**Identification:**
- `jalr $reg` au lieu de `jal address`
- Souvent utilisé pour callbacks, vtables, dispatch tables

---

## 2. Entity/Structure Access Patterns

### Simple Field Read
```mips
lw   $a0, 0x00($s1)           # Load 32-bit field
lhu  $a1, 0x14($s1)           # Load 16-bit field (unsigned)
lbu  $a2, 0x2B5($s1)          # Load 8-bit field (unsigned)
```

**Offsets Connus (Blaze & Blade):**
- `+0x00` = name (16 bytes)
- `+0x14` = timer (u16)
- `+0x3C` = descriptor_ptr (u32)
- `+0x144` = level (u16)
- `+0x160` = bitmask (u32)
- `+0x2B5` = creature_type (u8)

### Simple Field Write
```mips
li   $v0, 1000                # Value to write
sh   $v0, 0x14($s1)           # Store 16-bit (timer)
```

### Pointer Dereference Chain
```mips
lw   $v0, 0x3C($s1)           # Load entity->descriptor_ptr
nop
lw   $v1, 0x20($v0)           # Load descriptor->function_ptr
nop
jalr $v1                      # Call descriptor->function
nop
```

**Pattern:** `entity+0x3C → descriptor+0x20 → function call`
**Utilisé pour:** Entity behavior dispatch (traps, etc.)

---

## 3. Table Lookup Patterns

### Direct Index Lookup
```mips
sll  $v0, $a0, 2              # index * 4 (array of u32)
lui  $v1, 0x800E              # Table base (high)
ori  $v1, $v1, 0x27E4         # Table base (low) → 0x800E27E4
addu $v0, $v0, $v1            # table_base + offset
lw   $v0, 0x00($v0)           # Load table[index]
```

**Identification:**
- `sll` pour multiplier l'index (x2/x4/x8 = stride 2/4/8 bytes)
- `lui + ori` pour charger adresse de table 32-bit
- `addu + lw` pour accéder à l'entrée

### Computed Offset Lookup
```mips
lbu  $a0, 0x04($s1)           # Load entity_type (u8)
sll  $v0, $a0, 5              # entity_type * 32 (descriptor stride)
lui  $at, 0x8005
lw   $v1, 0x4914($at)         # Load template_array_base
addu $v0, $v0, $v1            # template_array + offset
addiu $v0, $v0, 0x38          # +0x38 offset in template
sw   $v0, 0x3C($s1)           # Store to entity->descriptor_ptr
```

**Pattern:** `type → multiply by stride → add to base → store pointer`
**Blaze & Blade:** Entity descriptor system @ `0x80021E68`

---

## 4. Loop Patterns

### Simple Counter Loop
```mips
li   $t0, 0                   # i = 0
li   $t1, 10                  # limit = 10

loop_start:
  # Loop body
  addiu $t0, $t0, 1           # i++
  bne  $t0, $t1, loop_start   # if (i != limit) goto loop_start
  nop
```

### Level-Up Simulation Loop (Spell Bitmask)
```mips
li   $v0, 0                   # bitmask = 0
li   $t0, 5                   # start_level = 5

loop:
  lw   $v1, <offset>($s1)     # Load spell bits for this level
  or   $v0, $v0, $v1          # bitmask |= bits
  addiu $t0, $t0, 5           # level += 5
  li   $at, 9999
  bne  $t0, $at, loop         # if (level != 9999) continue
  nop

sw   $v0, 0x160($s1)          # Store final bitmask to entity
```

**Pattern:** Accumulate avec `or`, sentinel = 9999
**Location:** `0x800244F4` (spell availability calculation)

### Pointer Walk Loop
```mips
move $t0, $s0                 # ptr = list_head

walk_loop:
  beqz $t0, loop_end          # if (ptr == NULL) break
  nop
  lw   $a0, 0x00($t0)         # data = ptr->value
  # Process data
  lw   $t0, 0x04($t0)         # ptr = ptr->next
  j    walk_loop
  nop

loop_end:
```

---

## 5. Conditional Patterns

### Simple If Statement
```mips
lw   $v0, 0x14($s1)           # Load timer
blez $v0, skip                # if (timer <= 0) skip
nop

# Then block
addiu $v0, $v0, -1            # timer--
sh   $v0, 0x14($s1)           # Store timer

skip:
```

### If-Else
```mips
lw   $v0, 0x14($s1)
blez $v0, else_block
nop

# Then block
addiu $v0, $v0, -1
j    end_if
nop

else_block:
  li   $v0, 1000              # Reset timer
  sh   $v0, 0x14($s1)

end_if:
```

### Switch/Jump Table
```mips
lw   $v0, 0x00($s1)           # Load switch value
sll  $v0, $v0, 2              # value * 4 (ptr size)
lui  $at, 0x8001
addiu $at, $at, <offset>      # Jump table base
addu $v0, $v0, $at            # table + offset
lw   $v0, 0x00($v0)           # Load jump address
jr   $v0                      # Jump
nop

# Jump table data:
# .word case_0
# .word case_1
# .word case_2
```

---

## 6. Arithmetic Patterns

### Division by 100 (Fixed-Point)
```mips
mult $a1, $a3                 # a * b
mflo $a1                      # result = a * b
lui  $v0, 0x51EB              # Magic constant
ori  $v0, 0x851F              # 0x51EB851F for /100
mult $a1, $v0                 # multiply by magic
mfhi $t0                      # Get high word
sra  $v1, $t0, 5              # Shift right 5
```

**Pattern:** Magic constant + shift = fast division
**Blaze & Blade:** Damage calculation @ `0x80024FF4`

### Percentage Calculation
```mips
lh   $a1, 0x148($s0)          # Load max_HP
li   $a3, 10                  # damage_percent = 10
mult $a1, $a3                 # max_HP * 10
mflo $a1                      # result
# ... then divide by 100 (see above)
```

**Formula:** `damage = (max_HP * percent) / 100`

---

## 7. Bitmask Patterns

### Set Bit
```mips
li   $v0, 0x00000001          # Bit 0
sll  $v0, $v0, 5              # Shift to bit 5
lw   $v1, 0x160($s1)          # Load current bitmask
or   $v1, $v1, $v0            # Set bit
sw   $v1, 0x160($s1)          # Store
```

### Clear Bit
```mips
li   $v0, 0x00000001
sll  $v0, $v0, 5              # Create bit mask
nor  $v0, $v0, $zero          # Invert mask
lw   $v1, 0x160($s1)
and  $v1, $v1, $v0            # Clear bit
sw   $v1, 0x160($s1)
```

### Test Bit
```mips
li   $v0, 0x00000001
sll  $v0, $v0, 5              # Bit to test
lw   $v1, 0x160($s1)          # Load bitmask
and  $v0, $v1, $v0            # Test
beqz $v0, bit_not_set         # Branch if not set
nop
```

### Accumulate Bits (Level-Up Loop)
```mips
lw   $v0, 0x160($s1)          # Load current bitmask
lw   $v1, <table>($t0)        # Load new bits for this level
or   $v0, $v0, $v1            # Accumulate
sw   $v0, 0x160($s1)          # Store
```

**Pattern:** `bitmask |= new_bits` in loop
**Blaze & Blade:** Spell availability @ `0x800244F4`

---

## 8. String/Memory Patterns

### String Copy
```mips
move $t0, $a0                 # dest
move $t1, $a1                 # src

copy_loop:
  lbu  $v0, 0x00($t1)         # Load byte
  sb   $v0, 0x00($t0)         # Store byte
  beqz $v0, copy_done         # If null terminator, done
  addiu $t0, $t0, 1           # dest++
  j    copy_loop
  addiu $t1, $t1, 1           # src++

copy_done:
```

### Memory Clear (memset 0)
```mips
move $t0, $a0                 # ptr
move $t1, $a1                 # size

clear_loop:
  sb   $zero, 0x00($t0)       # *ptr = 0
  addiu $t0, $t0, 1           # ptr++
  addiu $t1, $t1, -1          # size--
  bgtz $t1, clear_loop        # if (size > 0) continue
  nop
```

---

## 9. Patterns Spécifiques Blaze & Blade

### Damage Function Call
```mips
# Pattern recherché pour modifier damage%
li   $a3, 10                  # damage_percent = 10%
jal  0x80024F90               # damage_function
nop
```

**OR (register variant):**
```mips
lw   $a3, <offset>($base)     # Load damage% from table
jal  0x80024F90
nop
```

### Entity Descriptor Dispatch
```mips
lw   $v0, 0x3C($s1)           # Load entity->descriptor_ptr
nop
lw   $v1, 0x20($v0)           # Load descriptor->update_func
nop
jalr $v1                      # Call update_func
move $a0, $s1                 # Pass entity as arg (delay slot)
```

**Pattern:** `entity+0x3C → descriptor+0x20 → jalr`
**Utilisé pour:** Trap behaviors, entity updates

### Formation Record Read
```mips
lui  $v0, 0x800F              # Formation area base
ori  $v0, $v0, 0x7A96
addiu $v0, $v0, 0x04          # Skip header
lbu  $v1, 0x08($v0)           # byte[8] = slot_index
```

**Pattern:** Load from formation area + parse record bytes
**Byte[8]:** Monster type (0=Goblin, 1=Shaman, 2=Bat)

---

## 10. Comment Chercher un Pattern

### Méthode 1: Breakpoint + Backtrace
```
1. break <known_function>     # Ex: 0x80024F90 (damage)
2. Trigger in-game
3. regs → noter $ra
4. disasm $ra-20 40 → voir le code appelant
5. Chercher le pattern (JAL + setup)
```

### Méthode 2: Memory Watchpoint
```
1. watch <address> rw         # Ex: entity+0x160
2. Trigger in-game
3. À chaque break:
   - disasm $pc 5 → voir l'instruction qui accède
   - Remonter pour voir le contexte (disasm $pc-20 40)
```

### Méthode 3: Value Search
```
1. Chercher une valeur connue (ex: 10 pour 10% damage)
2. Breakpoint sur l'utilisation de cette valeur
3. Observer le pattern autour
```

### Méthode 4: Pattern Scanning (Python)
```python
# Chercher tous les JAL vers 0x80024F90
with open("BLAZE.ALL", "rb") as f:
    data = f.read()

jal_opcode = 0x0C0093E4  # JAL 0x80024F90
for i in range(0, len(data)-4, 4):
    word = int.from_bytes(data[i:i+4], 'little')
    if word == jal_opcode:
        print(f"Found at offset {i:#010x}")
```

---

## 11. Registres Conventions

### Calling Convention
```
$a0-$a3     Arguments 1-4 (caller → callee)
$v0-$v1     Return values (callee → caller)
$t0-$t9     Temporaries (caller-saved, volatile)
$s0-$s7     Saved registers (callee-saved, must preserve)
$ra         Return address (set by JAL, used by JR)
$sp         Stack pointer (callee must preserve)
```

### Common Usage Patterns
```
$s0         Loop counter / persistent value
$s1         Entity pointer (très courant!)
$s2         Secondary pointer (target, table, etc.)
$t0-$t2     Temporary calculations
$v0         Function return / loaded value
$a0         First arg / "this" pointer
```

---

## 12. Anti-Patterns (Faux Positifs)

### Dead Code
```mips
# Fonction jamais appelée (pas de JAL vers ici)
some_function:
  # ... code ...
  jr   $ra
  nop
```

**Comment détecter:**
- Chercher les JAL vers cette adresse dans tout le binaire
- Si aucun → dead code

### Debug/Development Code
```mips
# Strings de debug
.ascii "ERROR: Invalid spell_id %d\n"

# Printf calls (jamais exécutés en release)
jal  printf
nop
```

### Padding/Alignment
```mips
nop
nop
nop
nop
# ... longue séquence de NOPs
```

**Raison:** Aligner les fonctions sur des boundaries (16 bytes, etc.)

---

## See Also

- `DEBUGGING_GUIDE.md` - Setup debugging
- `console_commands_reference.md` - Commandes console
- `breakpoint_helper.py` - Générateur de breakpoints
- `memory/MEMORY.md` - Addresses confirmées
