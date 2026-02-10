# Monster AI & Spell System - Complete Architecture

## CRITICAL BUG FIX (2026-02-10)

All previous EXE analysis scripts had a **0x800-byte offset error**:
- The SLES file has a 0x800-byte PS-X header before code
- **Wrong formula**: `file_offset = RAM - 0x80010000`
- **Correct formula**: `file_offset = (RAM - 0x80010000) + 0x800`
- This means ALL prior disassembly results (in AI_BEHAVIOR_RESEARCH.md) were
  reading 0x800 bytes before the intended addresses!
- The script `ai_spell_v3_fixed.py` has the corrected formula

---

## 1. The Bytecode Interpreter (0x80017B6C)

The "AI dispatcher" is actually a **BYTECODE INTERPRETER**. Each monster entity
runs a scripted bytecode program that controls its per-frame behavior.

### Function: `ai_run_bytecode` at 0x80017B6C
- Stack frame: **2304 bytes** (massive - includes entity struct checkpoint)
- Parameters: `$a0 = caller_context`, `$a1 = entity_struct_ptr`
- Calls 5 functions: 0x80016E10, 0x80016ED0, 0x80016FFC, 0x800178A4, 0x80018894

### Entity AI Fields (in entity struct, base = $s2)
| Offset | Size | Name | Purpose |
|--------|------|------|---------|
| +0x000E | u8 | render_count | Render commands pending |
| +0x0014 | u8 | sub_entity_count | Related to subroutines |
| +0x0015 | u8 | return_stack_depth | Bytecode call stack depth (0 = no return) |
| +0x0022 | u8 | opcode_param | Last opcode parameter stored |
| +0x08A8 | u32 | callback_ptr | Function pointer called when program ends |
| +0x08AC | u32 | program_ptr | Current bytecode program start address |
| +0x08B0 | u32 | callback_param | Argument for callback at +0x08A8 |
| +0x08B4 | u32[N] | return_stack | Bytecode subroutine return addresses (up to ~5 levels) |
| +0x08C4 | u8 | ai_param_0 | Per-type AI behavior parameter |
| +0x08C5 | u8 | ai_param_1 | Per-type AI behavior parameter |
| +0x08C6 | u8 | ai_timer | Frame countdown timer (>0 = paused, decrements 1/frame) |
| +0x08C7 | u8 | ai_flags | Behavior flags bitfield (see below) |

### AI Flags Byte (+0x08C7)
| Bit | Hex | Meaning |
|-----|-----|---------|
| 0 | 0x01 | Bytecode program active/running |
| 1 | 0x02 | AI disabled / paused |
| 2 | 0x04 | Timer-only mode (skip to timer check, no bytecode) |
| 3-5 | - | Unknown |
| 6 | 0x40 | Force immediate return (stunned?) |
| 7 | 0x80 | Force immediate return (dead?) |

### Interpreter Flow (per frame)
```
1. CHECK FLAGS:
   if (flags & 0x04) -> skip to timer_check
   if (flags & 0x02) -> RETURN (AI disabled)
   if (flags & 0x40) -> RETURN (stunned/locked)
   if (flags & 0x80) -> RETURN (dead/removed)

2. TIMER CHECK:
   if (timer > 0) { timer--; RETURN; }  // delay N frames

3. LOAD PROGRAM:
   program = entity+0x08AC
   if (program == NULL) RETURN

4. CHECKPOINT:
   Copy entity struct (0x8C8 bytes) to stack buffer

5. BYTECODE LOOP (first pass - "pre-render"):
   byte = *program++
   if (byte == 0x00):
     if (return_stack_depth > 0):
       pop return address, continue
     else:
       CLEAR flag 0x01, zero program_ptr
       if (callback at +0x08A8): call it with param +0x08B0
       GOTO step 8
   if (byte < 32):
     result = state_handlers[byte](program, entity)
     program = result  // handler returns new program position
     if (byte == 9 or 14 or 15): GOTO step 6  // loop terminators
     continue loop
   if (128 <= byte-128 < 32):
     program++  // skip high-range scripting commands
   else:
     // Conditional/string comparison commands
     // Compare entity variables, set s3 (skip flag)
     continue loop

6. RESTORE ENTITY from checkpoint

7. BYTECODE LOOP (second pass - "post-render"):
   Same structure as first loop, using jump table at 0x8003B324+0x144
   (Second table also at same base, offset by index)

8. POST-UPDATE:
   call 0x80018894(entity)  // animation/physics/collision update
   if (global_4AB0 != 0): call 0x80016E10(entity)  // render pass
   if (entity+0x0E != 0): call 0x80016ED0(entity)  // additional render
```

---

## 2. Bytecode Opcode Table (0x8003B324, 32 entries)

These are NOT "AI states" - they are **bytecode opcodes** for the script interpreter.

| Opcode | Handler | Purpose (deduced from disassembly) |
|--------|---------|-------------------------------------|
| 0 | 0x80018CE0 | **SET_ENTITY_PARAM**: store byte from bytecode to entity+0x22, handle render count |
| 1-8 | 0x800181F4+ | **GPU/RENDER COMMANDS**: load 3 bytes (resource indices), configure VRAM texture, set GPU drawing primitives (E100 command, color, UV coords) |
| 9 | 0x80018660 | **TERMINATE_LOOP**: special - exits the per-frame bytecode loop |
| 10 | 0x80018718 | (handler specific, likely movement/position) |
| 11 | 0x80018794 | (handler specific) |
| 12 | 0x80018800 | (handler specific) |
| 13 | 0x800189F4 | (handler specific, 40-byte frame) |
| 14 | 0x80018698 | **AI_FLAG_OPERATION**: reads/modifies AI flags (+0x8C7), sets bit 0x04 |
| 15 | 0x80018B40 | **AI_FLAG_OPERATION_2**: reads AI flags, sets bit 0x04 |
| 16-19 | various | Small handlers |
| 20 | 0x80018CE0 | Same as opcode 0 |
| 21-27 | various | Small handlers |
| 28 | 0x80018B64 | (handler specific) |
| 29 | 0x80018C24 | (handler specific) |
| 30 | 0x80018EB4 | (handler specific) |
| 31 | 0x80018ED4 | (handler specific) |

**Key insight**: opcodes 1-8 all share the same base function (0x800181F4)
which is a GPU primitive setup function. The bytecodes are primarily for
**rendering/animation scripting**, not combat AI!

---

## 3. Combat Action Table (0x8003C1B0, 55 entries)

This table contains the **actual combat behavior handlers**. All 55 entries
are valid function pointers in the range 0x800270B8 - 0x80029980.

| Index | Handler | Notes |
|-------|---------|-------|
| 0 | 0x800270B8 | |
| 1 | 0x800271C8 | |
| 2 | 0x800272D8 | |
| ... | ... | (55 total, all unique) |
| 54 | 0x80029980 | |

These handlers are in the 0x80027xxx-0x80029xxx range and likely implement:
- Physical attack animations/damage
- Spell casting decisions
- Movement patterns (chase/flee/wander)
- Target selection
- Death/spawn effects

**TODO**: Disassemble these handlers to understand monster-type-specific combat behavior.

---

## 4. Spell System Architecture

### Spell Definition Table (BLAZE.ALL)
- Location: `0x908E68` in BLAZE.ALL
- Format: 48-byte entries, ~123 entries
- Fields: name (ASCII) + damage, element, cast_probability, range, target
- **Single copy** - shared by players AND monsters

### Entity Spell Fields
| Offset | Size | Name | Purpose |
|--------|------|------|---------|
| +0x0144 | u16 | stat_counter | Level/progression counter |
| +0x0146 | u16 | stat_exp | Experience-like accumulator |
| +0x0148 | u16 | stat_hp_growth | HP growth accumulator |
| +0x014A | u16 | stat_mp_growth | MP growth accumulator |
| +0x0150 | u8 | class_type | Entity class (& 0x07 = 0-7 class index) |
| +0x0158 | u32 | timer_158 | Accumulator/timer (compared vs growth thresholds) |
| +0x0160 | u32 | spell_bitfield | Spell availability flags |
| +0x02AC | u16 | spell_param | Spell-related parameter |
| +0x02B5 | u8 | spell_list_index | Index into spell pointer table (always 0) |

### Spell Casting Code Path
1. **Spell function starts at 0x80024C94** (NOT 0x80024E14 as previously noted)
2. **Zero direct JAL callers in EXE** - called from overlay code only
3. The function is a **level-up / stat growth** function, not purely spell-casting
4. It reads entity+0x2B5 (spell_list_index) at 0x80024504 and 0x80024E14
5. Calls `0x80039CB0` (rand) 4 times for stat growth randomization
6. Uses tables at RAM 0x8004C478 and 0x8004C480 for growth parameters

### Key BSS/Runtime Addresses
| RAM | Purpose |
|-----|---------|
| 0x80044C08 | Lookup table (256 bytes) - maps byte values to indices |
| 0x80054908 | Zone data pointer array (4 * N entries) |
| 0x8004C478 | Stat growth table (7 entries, signed 16-bit) |
| 0x8004C480 | Secondary growth table |
| 0x8004BF00 | Render buffer pointer |
| 0x80054AB0 | Global timer/frame counter |
| 0x80054690 | Render flag |

### How Monsters Get Their Spells (STILL UNRESOLVED)
- entity+0x2B5 is ALWAYS 0 (BSS table at 0x80058B30 never populated)
- pointer_table[0] from data_ptr+0x9C determines available spells
- data_ptr stored at 0x8005490C (set by overlay loader, not EXE code)
- The overlay code (loaded from BLAZE.ALL) calls the spell function
- **Need savestate analysis** to find runtime pointer_table[0] target

---

## 5. Key Functions Map

| Address | Name | Purpose |
|---------|------|---------|
| 0x80017B6C | ai_run_bytecode | Main bytecode interpreter (2304-byte frame!) |
| 0x80018894 | ai_post_update | Called after bytecode, animation/collision update |
| 0x800181F4 | opcode_gpu_render | GPU primitive setup (shared by opcodes 1-8) |
| 0x80018CE0 | opcode_set_param | Set entity byte from bytecode (opcodes 0, 20) |
| 0x80016E10 | render_pass | Render entity visuals |
| 0x80016ED0 | render_extra | Additional render pass |
| 0x80016FFC | entity_lookup | Entity search/targeting |
| 0x800178A4 | movement_update | Entity movement processing |
| 0x80024C94 | stat_growth | Level-up / stat growth (contains spell references) |
| 0x80024F90 | damage_calc | Damage calculation (maxHP * percent / 100) |
| 0x80039CB0 | rand | Random number generator |
| 0x80073B2C | play_sound | Sound effect playback |
| 0x800BF684 | secondary_default | Default handler for secondary function table (all 32 slots point here) |

---

## 6. Who Calls What (Cross-Reference)

### Combat-range functions and their callers:
| Function | Callers | Role |
|----------|---------|------|
| 0x80024024 | 7 sites | Combat utility |
| 0x80024088 | 7 sites | Combat utility |
| 0x80024F90 | 1 site (0x8001C574) | Damage calculation |
| 0x800250CC | 4 sites | Combat handler |
| 0x80026460 | 9 sites (from combat action table) | Target selection? |
| 0x80026650 | 11 sites | Common combat subroutine |
| 0x80026840 | 14 sites | Very common combat subroutine |
| 0x800269B8 | 1 site (0x8001C3B4) | Combat initialization? |

---

## 7. Architecture Summary

```
GAME LOOP (per frame)
  |
  +-- For each monster entity:
  |     |
  |     +-- ai_run_bytecode(0x80017B6C)
  |     |     |
  |     |     +-- Check AI flags (0x8C7): disabled/paused/dead?
  |     |     +-- Check AI timer (0x8C6): delay countdown?
  |     |     +-- Run bytecode program from entity+0x8AC:
  |     |     |     +-- Opcode 0: set param / end program
  |     |     |     +-- Opcodes 1-8: GPU render commands
  |     |     |     +-- Opcodes 9,14,15: loop terminators / flag ops
  |     |     |     +-- Opcodes 10-13,16-31: movement/behavior
  |     |     |     +-- Opcodes 128+: high-level scripting
  |     |     |
  |     |     +-- ai_post_update(0x80018894)
  |     |     +-- Render passes (0x80016E10, 0x80016ED0)
  |     |
  |     +-- OVERLAY CODE (loaded from BLAZE.ALL):
  |           |
  |           +-- Combat decision making
  |           +-- Spell casting (calls 0x80024C94 area)
  |           +-- Uses entity+0x8C4/0x8C5 for state
  |           +-- 55 combat actions via table at 0x8003C1B0
  |
  +-- Player input handling
  +-- World/camera updates
```

### KEY CONCLUSION:
**Monster AI has TWO layers:**

1. **EXE Bytecode Layer** (0x80017B6C): Controls scripted animation sequences,
   movement patterns, and rendering. The bytecodes in the script area
   (root table) drive this. This is what the "L field" indexes into.

2. **Overlay Combat Layer** (loaded from BLAZE.ALL): Controls actual combat
   decisions - when to attack, which spell to cast, target selection.
   This code resides in BLAZE.ALL overlay sections and calls EXE functions.
   Entity+0x8C4/0x8C5 hold combat state used by this layer.

**The combat AI is NOT in the EXE's state machine handlers.** It's in the
overlay code loaded from BLAZE.ALL. This is why patching EXE tables and
bytecode blocks had no effect on combat behavior.

---

## 8. Next Steps for Modding

### To change combat behavior (attack speed, aggression, spells):
- Need to find and patch the **overlay code** in BLAZE.ALL
- Use savestate analysis to find:
  - Which overlay region handles combat AI
  - What pointer_table[0] points to (spell subset)
  - The combat action dispatch mechanism in overlay code
- The 33 entity+0x8C7 accesses across multiple functions map the overlay AI

### To change scripted behavior (movement, animation, idle patterns):
- Modify the **bytecode programs** in the script area (root table entries)
- The 32 opcodes are documented above
- This controls animations, GPU commands, and basic movement

### To change which combat actions a monster uses:
- The 55-entry table at 0x8003C1B0 maps action_index -> handler
- Need to find how action_index is assigned per monster type
- Likely in overlay code using entity+0x8C4 or creature_type field

---

## Investigation Scripts
- `WIP/ai_spell_v3_fixed.py` - Corrected EXE analysis (use this one!)
- `WIP/ai_spell_investigation.py` - v1 (WRONG offsets, do not use)
- `WIP/ai_spell_deep_v2.py` - v2 (WRONG offsets, do not use)
- `Data/formations/dump_ai_blocks.py` - Script area dumper (works correctly)
- `WIP/level_design/spawns/scripts/analyze_bytecode_interpreter.py` - Original analysis (WRONG offsets)
