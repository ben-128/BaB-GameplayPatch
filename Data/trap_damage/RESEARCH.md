# Trap/Environmental Damage - Research Notes

## Damage Function (CONFIRMED)

**Address:** `0x80024F90` (EXE, never moves)
**JAL word:** `0x0C0093E4` (same for all overlays)

### Formula
```
damage = (maxHP * damage_param) / 100
```
- `damage_param` = percentage of max HP (e.g., 2 = 2%, 10 = 10%)
- Minimum damage = 1 (clamped)
- Death: HP set to 0, flag `0x40000000` set at entity+0x0140

### Disassembly (key part)
```
0x80024FE4: lh   $a1, 0x148($at)     ; load max_HP from player block
0x80024FEC: mult $a1, $a3            ; max_HP * damage_param
0x80024FF0: mflo $a1
0x80024FF4: lui  $v0, 0x51EB         ; magic constant for /100
0x80024FF8: ori  $v0, 0x851F
0x80024FFC: mult $a1, $v0
0x80025000: mfhi $t0
0x80025004: sra  $v1, $t0, 5         ; >> 5 completes /100
0x80025010-18: min damage = 1
0x8002501C: lhu  $v0, 0x14C($a0)     ; load current HP
0x80025024: subu $v0, $v0, $a1       ; HP -= damage
0x80025028: sh   $v0, 0x14C($a0)     ; store new HP
```

### Player Data Blocks
- Base: `0x800F0000 + player_index * 0x2000`
- Player index loaded via `lbu $a0, 8($entity)` then `sll $v1, $a0, 13`
- +0x0100 = name (ASCII), +0x0144 = level, +0x0148 = maxHP, +0x014C = curHP

---

## Two Types of Trap Damage Code

### Type 1: Direct JAL callers (Pass 1)

Overlay code calls `jal 0x80024F90` with `$a1` set to an immediate value.

| Count | Original % | Description |
|-------|-----------|-------------|
| 2 | 2% | Light environmental (fall damage) |
| 3 | 3% | Medium-light traps |
| 6 | 5% | Poison/periodic damage |
| 3 | 10% | Heavy traps |
| 1 | 20% | Very heavy trap |

**15 total** across 7+ overlay regions. Pattern:
```
addiu/ori $a1, $zero, N    ; $a1 = damage%
...
jal   0x80024F90           ; call damage function
```

### Type 2: GPE Entity Init (Pass 2) - DECODED 2026-02-10

GPE entities (falling rocks, heavy traps) store damage% to **entity+0x14**
during state transitions. The function at 0x009ED00C later reads entity+0x14
and passes it to the damage function via register (data-driven caller).

**Pattern:**
```
ori/addiu $v0, $zero, N     ; damage% (10 or 20)
sh  $v0, 0x14($s5)          ; store to GPE entity field
```

**Entity structure for GPE traps:**
- `entity+0x10` (uint16): State code (101 = damage phase)
- `entity+0x12` (uint16): Timer/counter
- `entity+0x14` (uint16): **Damage percentage** (10%, 20%)
- `entity+0x16` (uint16): **Damage type** (1=physical, 0=other)

**Cross-overlay scan results (all 28 dungeon overlays):**

| Count | Value | Description |
|-------|-------|-------------|
| 11 | 2% | Light GPE entity damage |
| 28 | 10% | Standard GPE damage (1 per overlay) |
| 56 | 20% | Heavy GPE damage (2 per overlay) |

**Key discriminator:** `$s5` register = GPE entity pointer. All GPE inits use `sh $v0, 0x14($s5)`.

**Context signature (verified identical across all 28 overlays for val=10%):**
```
0x3C01800D       lui $at, 0x800D        ; global state address
0xA022xxxx       sb $v0, xxxx($at)      ; store to global (varies per overlay)
0x3402000A       ori $v0, $zero, 10     ; <-- DAMAGE %
0xA6A20014       sh $v0, 0x14($s5)      ; store to entity+0x14
0x34020001       ori $v0, $zero, 1      ; damage_type = 1
```

**Backward trace (how 10% reaches the damage function):**
1. Entity init: `ori $v0, $zero, 10` + `sh $v0, 0x14($s5)` (PATCHED HERE)
2. State handler reads entity+0x14, passes as stack arg to 0x009ED00C
3. Function 0x009ED00C reads `lhu $s7, 72($sp)` (the damage%)
4. Passes `$s7` as `$a1` to `jal 0x80024F90`
5. Damage applied: `HP -= (maxHP * 10) / 100`

The function at 0x009ED00C is called **indirectly** (via `jalr` / function pointer),
which is why zero `jal` instructions target it directly.

---

## Patcher v4 (CURRENT - step 7d)

**File:** `patch_trap_damage.py`
**Config:** `trap_damage_config.json` (`overlay_patches.values`)
**110 total patches** = 15 jal + 95 GPE entity init

Both passes use the same per-value config:
```json
{"2": 10, "3": 15, "5": 25, "10": 40, "20": 60}
```

### Pass 1: JAL callers (15 sites)
- Searches for `jal 0x80024F90` with immediate `$a1`
- Same as patcher v3

### Pass 2: GPE entity init (95 sites)
- Searches for adjacent `li $v0, N` + `sh $v0, 0x14($s5)` (word 0xA6A20014)
- Covers falling rocks, heavy traps, and light GPE entities
- 28 overlays: 11x 2%, 28x 10%, 56x 20%

---

## EXE Division Shift (REMOVED)

Was `patch_trap_damage_exe.py` (step 9d) - modified the division shift in the damage
function at EXE 0x80025004. **Removed** because it affects ALL 189 callers including
combat damage, not just traps. The overlay patcher (v4) is the correct solution.

---

## Previous Wrong Lead: 0x8008A3E4

Function 0x8008A3E4 is a **COLOR/TINT modifier**, NOT damage.
In-game test confirmed: modifying these values has NO effect on damage.

---

## ePSXe Savestate Format
- Compression: gzip
- Header: "ePSXe\x06\x00" + game ID (64 bytes)
- PS1 RAM: decompressed offset **0x1BA**, size 2MB
- Overlay mapping (Cavern): BLAZE_offset = RAM_offset + 0x008C68A8
