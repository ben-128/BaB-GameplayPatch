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

## Callers in BLAZE.ALL Overlay Code

### Statistics
- **189 total** `jal 0x80024F90` across all overlay regions
- **15 with hardcoded immediate $a1** (patchable by overlay patcher)
- **174 with register-based $a1** (data-driven, NOT patchable by overlay patcher)

### Hardcoded Callers (overlay patcher patches these)

| Count | Original % | Description |
|-------|-----------|-------------|
| 2 | 2% | Light environmental (fall damage) |
| 3 | 3% | Medium-light traps |
| 6 | 5% | Poison/periodic damage |
| 3 | 10% | Heavy traps |
| 1 | 20% | Very heavy trap |

Found across 7+ overlay regions:
- 0x0093xxxx (Cavern of Death)
- 0x0178xxxx, 0x0270xxxx, 0x0278xxxx
- 0x027Fxxxx, 0x0289xxxx, 0x028Fxxxx
- 0x0296xxxx, 0x02B7xxxx

### Data-Driven Callers (NOT patched by overlay patcher)

These load $a1 from a register ($s7, $s6, etc.), not from an immediate.
The damage value comes from entity data loaded at runtime.

**Example: Cavern of Death falling rocks (10%)**

```
Function at BLAZE+0x009ED00C:
  0x009ED014: lhu  $s7, 72($sp)   ; damage_param from stack arg (= 10)
  0x009ED01C: lhu  $s5, 76($sp)   ; damage_type from stack arg
  0x009ED024: addu $s6, $a2, $zero ; another param from $a2
  ...
  0x009ED160: sll  $a1, $s7, 16   ; sign-extend $s7 -> $a1
  0x009ED168: sra  $a1, $a1, 16
  0x009ED16C: jal  0x80024F90     ; call damage function
```

The 10% value is passed as a **function argument** through the stack.
It originates from higher-level code that reads entity/area data.
Cannot be patched by simply changing an immediate value in overlay code.

#### Cavern Overlay - All 9 callers to 0x80024F90

| # | BLAZE Offset | $a1 Source | Value | Type |
|---|-------------|-----------|-------|------|
| 1 | 0x00936E60 | immediate `ori $a1, $zero, N` | 2% (now 10%) | Hardcoded - PATCHED |
| 2 | 0x00937C28 | immediate `ori $a1, $zero, N` | 2% (now 10%) | Hardcoded - PATCHED |
| 3 | 0x0093C004 | immediate `ori $a1, $zero, N` | 5% (now 25%) | Hardcoded - PATCHED |
| 4 | 0x009ED16C | register `sll/sra $a1, $s7` | 10%? | Data-driven (stack arg) |
| 5 | 0x009ED748 | register `sll/sra $a1, $s6` | ?? | Data-driven (function arg) |
| 6 | 0x009F3608 | register `sll/sra $a1, $s-reg` | ?? | Data-driven |
| 7 | 0x009F3BE4 | register `sll/sra $a1, $s-reg` | ?? | Data-driven |
| 8 | 0x009FBE8C | register `sll/sra $a1, $s-reg` | ?? | Data-driven |
| 9 | 0x009FC468 | register `sll/sra $a1, $s-reg` | ?? | Data-driven |

---

## Previous Wrong Lead: 0x8008A3E4

Function 0x8008A3E4 is a **COLOR/TINT modifier**, NOT damage:
- Reads 3 bytes at entity+0x38/0x39/0x3A (RGB)
- Adds deltas from $a1/$a2/$a3
- Clamps each to [0, 255]
- Stores back

Callers with negative args = visual darkening, NOT HP damage.
In-game test confirmed: modifying these values has NO effect on damage.

---

## Patching Options

### Option A: Overlay Patcher (CURRENT - step 7d)
- File: `patch_trap_damage.py`
- Patches: Hardcoded immediate $a1 values near `jal 0x80024F90`
- Scope: Only affects 15 callers with hardcoded percentages
- Status: **WORKING** (confirmed 2% -> 10% in-game)
- Limitation: Does NOT affect data-driven callers (falling rocks = 10%)

### Option B: EXE Division Shift (IMPLEMENTED but DISABLED)
- File: `patch_trap_damage_exe.py` (step 9d)
- Modify `sra $v1, $t0, 5` at EXE 0x80025004
- Change shift from 5 to 4 = divide by 50 instead of 100 = **2x ALL damage**
- Change shift from 5 to 3 = divide by 25 = **4x ALL damage**
- EXE offset: 0x15804 (0x800 header + 0x15004)
- Instruction: 0x00081943 (sra 5) -> 0x00081903 (sra 4) for 2x
- **DISABLED**: Affects ALL 189 callers including **combat damage** - not desirable
- Only useful if you want to globally amplify ALL %-based HP damage
- Stacks with overlay patches: effective = overlay_value * exe_multiplier

### Option C: Trace Entity Data Source (NOT DONE)
- Find where the 10% value is stored in BLAZE.ALL area data
- Would require tracing function call chain backward from 0x009ED00C
- The value passes through multiple function calls via stack arguments
- Most targeted but most complex approach

---

## ePSXe Savestate Format
- Compression: gzip
- Header: "ePSXe\x06\x00" + game ID (64 bytes)
- PS1 RAM: decompressed offset **0x1BA**, size 2MB
- Overlay mapping (Cavern): BLAZE_offset = RAM_offset + 0x008C68A8

## Useful Tools
- `WIP/TrapDamage/diff_savestates.py` - Compare two savestates (before/after hit)
- `WIP/TrapDamage/prove_multi_dungeon_v3.py` - Function-agnostic damage caller search
