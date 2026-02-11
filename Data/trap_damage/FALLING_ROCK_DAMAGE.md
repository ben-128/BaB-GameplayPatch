# Falling Rock Damage (10%) — Research Summary

> Status: **UNSOLVED** (2026-02-10)
> Goal: Change the falling rock damage from 10% to a custom value (e.g. 50%).

---

## What We Know

### The damage function
All trap/environmental damage goes through a single function:
```
0x80024F90: damage = (maxHP * damage%) / 100     (minimum 1 HP)
```
The `damage%` parameter arrives in register `$a1`. The question is: **where does 10 come from** for falling rocks?

### The calling chain (confirmed)
```
EXE engine                            (iterates entities, calls handlers via jalr)
  -> Overlay handler function          (reads damage% from entity struct/data)
    -> Template A or Template B        (overlay functions, checks proximity)
      -> jal 0x80024F90               (applies damage to player HP)
```

### Template A — "Proximity/range check" (3 sites in Cavern)
| BLAZE offset | RAM equivalent |
|-------------|---------------|
| 0x009ED00C  | Block 1 (Template A1) |
| 0x009F34A8  | Block 2 (Template A2) |
| 0x009FBD2C  | Block 3 (Template A3) |

- Signature: `func(x_pos, y_pos, z_pos, radius, damage%, element)`
- Damage% read from **5th stack arg** (halfword): `lhu $s7, 0x0048($sp)`
- Loops 4 players, checks 3D distance vs radius, applies damage if in range
- 60-frame cooldown at entity+0x96 after hit

### Template B — "Entity-based / bitmask guard" (3 sites in Cavern)
| BLAZE offset | RAM equivalent |
|-------------|---------------|
| 0x009ED648  | Block 1 (Template B1) |
| 0x009F3AE4  | Block 2 (Template B2) |
| 0x009FC368  | Block 3 (Template B3) |

- Signature: `func(entity_ptr, damage%, ???, timeout, ???)`
- Damage% read from **$a1** (2nd register arg), saved to $s6
- Per-entity damage with bitmask guards (0x10000000, 0x40000000 flags)

**Key fact:** Both templates receive damage% as a pass-through argument. They never hardcode it. The value 10 comes from the **caller** (an overlay handler function).

---

## What We Tried and Failed

### 1. BLAZE 0x009ECE8A — COLLISION/HITBOX, NOT DAMAGE (in-game test)
- Halfword at entity data block +0x06 contains value 10 (0x000A)
- **Patched to 50** and tested in-game
- **Result:** Collision/hitbox behavior changed (harder to get hit by falling rock)
- **Result:** Damage amount UNCHANGED (still 10% of max HP)
- **Conclusion:** This field controls collision radius, not damage%

Entity data block layout at BLAZE 0x009ECE84:
```
Offset  Value   What it is
+0x00   0x0000  (unknown)
+0x02   0x0003  (unknown, count?)
+0x04   0x0008  (unknown)
+0x06   0x000A  = 10 -> COLLISION/HITBOX SIZE (confirmed)
+0x08   0x0010  = 16 (unknown)
+0x0A   0x020C  = 524 (unknown, large)
```

### 2. entity+0x14 via $s5 — STATE MACHINE ID, NOT DAMAGE
- 95 sites across 39 overlay regions write state IDs (10, 20, 200, 201, 206, 211) to entity+0x14
- Values 10 and 20 happen to coincide with damage% values but are state codes
- Patching changes state transitions, not damage

### 3. entity+0x14 via $s1 — CAMERA SHAKE INTENSITY
- Different entity struct, patching increased screen shake, not damage

### 4. All 6 `li $reg, 10` in overlay 0x009E0000-0x00A00000
All are state machine variables, not damage:
- 0x009EE44C: state machine comparison
- 0x009EF0D4: state/timer value stored to entity+0x14
- 0x009F1048: sound/VFX parameter ($a0=10, not $a1)
- 0x009F4D2C: state value stored to entity+0x14
- 0x009F5FBC: loop counter ($a0=10, iterates entities)
- 0x009FA048: stored to global 0x800D2904, counter/index

### 5. EXE "10" at 0x80025364 — EFFECT ID, NOT DAMAGE
- Effect/action type ID system (2,12), (3,13), ..., (10,20)
- Bit 23 of entity+0x00 selects between paired IDs
- Confirmed NOT related to damage values

### 6. Script bytecode (opcode 0x1F) — NOT USED BY CAVERN
- Per-area bytecode format: `[0x1F, damage%, element]`
- All matches in Cavern F1 script area were false positives (spawn table data)
- Falling rocks do NOT use the script system for damage

---

## Entity Descriptor System (discovered 2026-02-10)

The most promising lead. Falling rock entities use a **descriptor pointer** system.

### How entity+0x3C gets loaded (EXE at 0x80021E68)
```mips
lui   $v1, 0x8005
lw    $v1, 0x4914($v1)     ; v1 = *(0x80054914) = global struct
lbu   $v0, 0x0004($s0)     ; v0 = entity+0x04 (entity type byte)
lw    $v1, 0x0038($v1)     ; v1 = global+0x38 (template array base)
sll   $v0, $v0, 2          ; v0 = type_index * 4
addu  $v0, $v0, $v1        ; v0 = &template_array[type_index]
lw    $v0, 0x0000($v0)     ; v0 = template_array[type_index]
sw    $v0, 0x003C($s0)     ; entity+0x3C = descriptor pointer
```

**Formula:** `entity+0x3C = template_array[entity+0x04]`

### Falling rock descriptor
| What | RAM address | BLAZE offset |
|------|-----------|-------------|
| Descriptor (32 bytes) | 0x800BF7EC | 0x009ECFEC |
| Template A1 function  | 0x800BF80C | 0x009ED00C |

The descriptor is exactly **0x20 bytes before** Template A1. This means descriptor+0x20 = Template A1 code address.

### Descriptor raw data at BLAZE 0x009ECFEC
```
009ECFEC: 20 00 18 00 48 00 XX XX  00 10 02 01 XX XX XX XX
009ECFFC: XX XX XX XX XX XX XX XX  XX XX XX XX XX XX XX XX
```
Some of these 32 bytes likely encode the damage% value (10). **Which byte(s) is still unknown.**

### Why the dispatch is hard to find
- Searched entire EXE for pattern `lw $reg, 0x3C($reg)` -> 55 hits
- **NONE** follow with `addiu $reg, +0x20` then `jalr` (the descriptor dispatch pattern)
- **The dispatch happens inside overlay code**, not the EXE
- Overlay code is loaded from BLAZE.ALL to RAM at runtime (addresses like 0x80073xxx)
- Only 1 `jalr` found in the overlay CODE section (unrelated to damage)

---

## What Works for Other Traps (but not falling rocks)

### Pass 1 patcher — 15 sites, WORKING
Other traps (blades, spikes, floor traps) hardcode damage% as a MIPS immediate:
```mips
addiu $a1, $zero, 5       ; $a1 = 5%
jal   0x80024F90           ; call damage function
```
The patcher finds and patches these 15 sites. Distribution: 2% (x2), 3% (x3), 5% (x6), 10% (x3), 20% (x1).

**But falling rocks in the Cavern don't use this pattern.** They pass damage% via registers loaded from entity data at runtime.

### 3 other dungeons DO hardcode 10% for falling rocks
These are caught by Pass 1:
| BLAZE offset | Context |
|-------------|---------|
| 0x01787E90  | distance < 50, element=9 |
| 0x028985FC  | distance < 300, element=0 |
| 0x0296780C  | distance < 300, element=0 |

Only the **Cavern** (and possibly other dungeons using the Template A/B approach) remains unsolved.

---

## Next Steps to Solve

### Option A: Find the overlay dispatch (recommended)
1. **Find the overlay handler function** that calls Template A1/B1
   - It lives somewhere in 0x009EDA80 - 0x009F34A8 (between Template B1 end and Template A2 start)
   - It receives entity pointer from EXE, reads damage% from entity struct, then calls Template A or B
   - Look for `sw $reg, 0x10($sp)` (storing 5th arg for Template A) or `addu $a1, $sN, $zero` (setting $a1 for Template B)

2. **Trace where the handler reads damage% from**
   - Could be from: entity struct field, descriptor byte, or a separate data table
   - The handler is called via `jalr` from the EXE engine

3. **Test by NOP-ing the handler call** (savestate-based)
   - If falling rocks stop doing damage -> confirmed the right function
   - Then read register values at that point to find the damage% source

### Option B: Brute-force descriptor bytes
1. The 32-byte descriptor at BLAZE 0x009ECFEC has multiple candidate values
2. Systematically patch each byte/halfword and test in-game
3. One of them should be the damage% field
4. Risk: some bytes may control other behaviors (like 0x009ECE8A controlled collision)

### Option C: Dynamic tracing (emulator)
1. Set a read breakpoint on entity+0x3C in the Cavern
2. When the engine reads the descriptor pointer, step through the dispatch
3. Follow the chain: descriptor -> handler function -> Template A/B -> damage function
4. This would conclusively identify which byte encodes damage%

---

## Key Reference: All BLAZE.ALL Offsets

| Description | BLAZE offset | RAM address |
|------------|-------------|-----------|
| Cavern overlay mapping base | 0x009268A8 | 0x80060000 |
| Entity data block (collision) | 0x009ECE84 | — |
| Falling rock descriptor | 0x009ECFEC | 0x800BF7EC |
| Template A1 function | 0x009ED00C | 0x800BF80C |
| Template B1 function | 0x009ED648 | — |
| Template A2 function | 0x009F34A8 | — |
| Template B2 function | 0x009F3AE4 | — |
| Template A3 function | 0x009FBD2C | — |
| Template B3 function | 0x009FC368 | — |
| EXE descriptor init | — | 0x80021E68 |
| EXE damage function | — | 0x80024F90 |
| Global struct pointer | — | 0x80054914 |
