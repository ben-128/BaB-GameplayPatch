# -*- coding: cp1252 -*-
"""
Spell damage formula - FINAL analysis v4.

IDENTIFIED: The main spell damage function is at 0x80025E90.
It is called from overlay Cluster 3 (spell execution).

This function:
1. Loads spell entry from pointer_table[list_idx][spell_id * 48]
2. Reads spell_entry+0x16 (element), +0x1E (unknown_param), +0x18 (damage)
3. Uses caster stats at entity+0x38, +0x2A, +0x2C, +0x3A
4. Uses target stats similarly
5. Calls elemental functions 0x80026460/0x80026650
6. Computes final damage with stat scaling

Let's disassemble the FULL function and annotate it.
"""

import struct
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
EXE_PATH = os.path.join(PROJECT_DIR,
    "Blaze  Blade - Eternal Quest (Europe)", "extract", "SLES_008.45")

with open(EXE_PATH, 'rb') as f:
    exe_data = f.read()

REG_NAMES = [
    "$zero","$at","$v0","$v1","$a0","$a1","$a2","$a3",
    "$t0","$t1","$t2","$t3","$t4","$t5","$t6","$t7",
    "$s0","$s1","$s2","$s3","$s4","$s5","$s6","$s7",
    "$t8","$t9","$k0","$k1","$gp","$sp","$fp","$ra"
]

def sign_extend_16(val):
    return val - 0x10000 if val & 0x8000 else val

def disasm_one(word, addr):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    imms = sign_extend_16(imm)
    target = (word & 0x3FFFFFF) << 2
    if word == 0: return "nop"
    if op == 0:
        m = {0x20:"add",0x21:"addu",0x22:"sub",0x23:"subu",0x24:"and",0x25:"or",
             0x26:"xor",0x27:"nor",0x2A:"slt",0x2B:"sltu"}
        if funct in m: return "%s %s, %s, %s" % (m[funct], REG_NAMES[rd], REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x00: return "sll %s, %s, %d" % (REG_NAMES[rd], REG_NAMES[rt], shamt)
        if funct == 0x02: return "srl %s, %s, %d" % (REG_NAMES[rd], REG_NAMES[rt], shamt)
        if funct == 0x03: return "sra %s, %s, %d" % (REG_NAMES[rd], REG_NAMES[rt], shamt)
        if funct == 0x04: return "sllv %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rt], REG_NAMES[rs])
        if funct == 0x06: return "srlv %s, %s, %s" % (REG_NAMES[rd], REG_NAMES[rt], REG_NAMES[rs])
        if funct == 0x08: return "jr %s" % REG_NAMES[rs]
        if funct == 0x09: return "jalr %s, %s" % (REG_NAMES[rd], REG_NAMES[rs])
        if funct == 0x10: return "mfhi %s" % REG_NAMES[rd]
        if funct == 0x12: return "mflo %s" % REG_NAMES[rd]
        if funct == 0x18: return "mult %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x19: return "multu %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x1A: return "div %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x1B: return "divu %s, %s" % (REG_NAMES[rs], REG_NAMES[rt])
        if funct == 0x0D: return "break"
        return "R-type funct=0x%02X" % funct
    if op == 0x02: return "j 0x%08X" % ((addr & 0xF0000000) | target)
    if op == 0x03: return "jal 0x%08X" % ((addr & 0xF0000000) | target)
    if op == 0x04: return "beq %s, %s, 0x%08X" % (REG_NAMES[rs], REG_NAMES[rt], addr + 4 + (imms << 2))
    if op == 0x05: return "bne %s, %s, 0x%08X" % (REG_NAMES[rs], REG_NAMES[rt], addr + 4 + (imms << 2))
    if op == 0x06: return "blez %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
    if op == 0x07: return "bgtz %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
    if op == 0x01:
        if rt == 0: return "bltz %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        if rt == 1: return "bgez %s, 0x%08X" % (REG_NAMES[rs], addr + 4 + (imms << 2))
        return "REGIMM rt=%d" % rt
    if op == 0x08: return "addi %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x09: return "addiu %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0A: return "slti %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0B: return "sltiu %s, %s, %d" % (REG_NAMES[rt], REG_NAMES[rs], imms)
    if op == 0x0C: return "andi %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0D: return "ori %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0E: return "xori %s, %s, 0x%04X" % (REG_NAMES[rt], REG_NAMES[rs], imm)
    if op == 0x0F: return "lui %s, 0x%04X" % (REG_NAMES[rt], imm)
    if op == 0x20: return "lb %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x21: return "lh %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x23: return "lw %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x24: return "lbu %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x25: return "lhu %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x28: return "sb %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x29: return "sh %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    if op == 0x2B: return "sw %s, %d(%s)" % (REG_NAMES[rt], imms, REG_NAMES[rs])
    return "??? op=0x%02X (0x%08X)" % (op, word)

def ram_to_file(ram_addr):
    return (ram_addr - 0x80010000) + 0x800

def read_word(file_off):
    if file_off < 0 or file_off + 4 > len(exe_data):
        return None
    return struct.unpack_from('<I', exe_data, file_off)[0]


# ============================================================
# Full disassembly of 0x80025E90 to its end (jr $ra)
# ============================================================

print("=" * 70)
print("FULL FUNCTION: 0x80025E90 (Main Spell Damage/Effect)")
print("=" * 70)

addr = 0x80025E90
end_addr = 0x80026500  # generous upper bound
found_jr = False
for i in range(500):
    a = addr + i * 4
    if a >= end_addr:
        break
    foff = ram_to_file(a)
    w = read_word(foff)
    if w is None:
        break
    asm = disasm_one(w, a)

    # Add annotations for key offsets
    ann = ""
    op = (w >> 26) & 0x3F
    rs_r = (w >> 21) & 0x1F
    rt_r = (w >> 16) & 0x1F
    imms = sign_extend_16(w & 0xFFFF)

    if op in (0x24, 0x25, 0x21, 0x23):  # load ops
        # Spell entry fields
        if imms == 0x16 and rs_r != 29:
            ann = "  ; << SPELL ELEMENT >>"
        if imms == 0x18 and rs_r != 29:
            ann = "  ; << SPELL DAMAGE >>"
        if imms == 0x1E and rs_r != 29:
            ann = "  ; << SPELL +0x1E param >>"
        if imms == 0x14 and rs_r != 29:
            ann = "  ; spell level/power?"
        # Entity stat fields
        if imms == 0x38 and rs_r != 29:
            ann = "  ; << CASTER STAT +0x38 (INT?) >>"
        if imms == 0x3A and rs_r != 29:
            ann = "  ; << ENTITY STAT +0x3A >>"
        if imms == 0x2A and rs_r != 29:
            ann = "  ; << ENTITY STAT +0x2A >>"
        if imms == 0x2C and rs_r != 29:
            ann = "  ; << ENTITY STAT +0x2C >>"
        if 0x010C <= imms <= 0x0120:
            ann = "  ; entity combat field +0x%X" % imms

    if op == 0 and (w & 0x3F) in (0x18, 0x19, 0x1A, 0x1B):
        ann = "  ; << ARITHMETIC >>"

    if op == 0x03:
        tgt = ((a & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
        known = {
            0x80026840: "hit_check",
            0x800235B0: "player_target_select",
            0x80023630: "monster_target_select",
            0x800250CC: "unknown_combat",
            0x8006E044: "overlay_spell_effect",
            0x80073F9C: "overlay_visual_effect",
            0x80073B2C: "overlay_spell_execute",
            0x80039CB0: "random_number",
            0x80026460: "elemental_check_A",
            0x80026650: "elemental_check_B",
            0x80025124: "defense_calculation",
            0x800252B4: "unknown_combat_check",
            0x800739D8: "overlay_anim_trigger",
        }
        if tgt in known:
            ann = "  ; << %s >>" % known[tgt]

    print("  0x%08X: %08X  %s%s" % (a, w, asm, ann))

    # Check for jr $ra
    if (w & 0xFC1FFFFF) == 0x03E00008:
        # Print delay slot
        a2 = a + 4
        w2 = read_word(ram_to_file(a2))
        if w2 is not None:
            asm2 = disasm_one(w2, a2)
            print("  0x%08X: %08X  %s" % (a2, w2, asm2))
        found_jr = True
        break


# ============================================================
# Now disassemble key helper functions
# ============================================================

print("\n" + "=" * 70)
print("HELPER: 0x80026460 (elemental_check_A)")
print("=" * 70)
for i in range(80):
    a = 0x80026460 + i * 4
    foff = ram_to_file(a)
    w = read_word(foff)
    if w is None: break
    asm = disasm_one(w, a)
    print("  0x%08X: %08X  %s" % (a, w, asm))
    if (w & 0xFC1FFFFF) == 0x03E00008:
        w2 = read_word(ram_to_file(a + 4))
        if w2: print("  0x%08X: %08X  %s" % (a + 4, w2, disasm_one(w2, a + 4)))
        break


print("\n" + "=" * 70)
print("HELPER: 0x80026650 (elemental_check_B)")
print("=" * 70)
for i in range(80):
    a = 0x80026650 + i * 4
    foff = ram_to_file(a)
    w = read_word(foff)
    if w is None: break
    asm = disasm_one(w, a)
    print("  0x%08X: %08X  %s" % (a, w, asm))
    if (w & 0xFC1FFFFF) == 0x03E00008:
        w2 = read_word(ram_to_file(a + 4))
        if w2: print("  0x%08X: %08X  %s" % (a + 4, w2, disasm_one(w2, a + 4)))
        break


print("\n" + "=" * 70)
print("HELPER: 0x80025124 (defense_calculation)")
print("=" * 70)
for i in range(80):
    a = 0x80025124 + i * 4
    foff = ram_to_file(a)
    w = read_word(foff)
    if w is None: break
    asm = disasm_one(w, a)
    print("  0x%08X: %08X  %s" % (a, w, asm))
    if (w & 0xFC1FFFFF) == 0x03E00008:
        w2 = read_word(ram_to_file(a + 4))
        if w2: print("  0x%08X: %08X  %s" % (a + 4, w2, disasm_one(w2, a + 4)))
        break


# ============================================================
# ANNOTATED PSEUDOCODE for Handler [10]
# ============================================================

print("\n" + "=" * 70)
print("ANNOTATED PSEUDOCODE: Handler [10] (0x800276B0)")
print("=" * 70)
print("""
handler_10($a0=action_struct, $a1=caster_or_something, $a2=param):

  $s0 = action_struct
  sp[0x10] = 3     // target_mode = 3 (this handler = spell type 3)
  sp[0x14] = $a2   // extra parameter

  // Call target selection
  ret = target_select_0x80023698($a0, $a1, &caster_ptr, &target_ptr)
  if (ret != 0) return 1  // miss/fail

  // Load spell entry
  spell_list_idx = action_struct[7]   // byte at +0x07
  spell_slot     = action_struct[6]   // byte at +0x06

  data_ptr = *(0x8005490C)           // global game data ptr
  pointer_table = *(data_ptr + 0x9C) // spell pointer table base
  list_base = pointer_table[spell_list_idx]

  // spell_slot * 48: (slot*2 + slot) * 16 = slot * 48
  spell_entry = list_base + spell_slot * 48

  // --- CASTER STAT CONTRIBUTION ---
  caster = caster_ptr  // from sp[0x18]

  // Stat A: entity+0x38 (halfword, unsigned)
  // This appears to be a "magic power" or "spell level" stat
  stat_A_raw = lhu caster[0x38]
  power_level = (int16)(stat_A_raw) >> 3   // arithmetic right shift 3 = /8
  power_level = power_level + 40           // base of 40

  // Stat B: entity+0x2A (halfword)
  // This appears to be INT or WIL
  stat_B_raw = lhu caster[0x2A]
  stat_B = (int16)(stat_B_raw)
  stat_B_div3 = stat_B / 3                // compiler magic: mult by 0x2AAAAAAB

  // --- SPELL BASE DAMAGE ---
  spell_base_damage = lhu spell_entry[0x18]   // +0x18 = damage field

  // --- FINAL DAMAGE ---
  final_damage = stat_B_div3 + spell_base_damage

  // --- TARGET APPLICATION ---
  target = target_ptr  // from sp[0x1C]
  threshold = lhu target[0x86]
  if (threshold < power_level):
      target[0x86] = power_level      // update threshold/priority
      target[0xE4] = final_damage     // apply damage

  return 0

KEY INSIGHT:
  damage = (entity_stat_0x2A / 3) + spell_entry_0x18

  For handlers [10]-[13], the formula is THE SAME but stores to
  different target entity offsets:
    [10] -> target[0x86] / target[0xE4]   (element type 3?)
    [11] -> target[0x88] / target[0xE6]   (element type 4?)
    [12] -> target[0x8A] / target[0xE8]   (element type 5?)
    [13] -> target[0x8C] / target[0xEA]   (element type 6?)

  The target_mode values (3,4,5,6) likely correspond to
  elements: 3=water, 4=earth, 5=wind, 6=light (from spell entry)
""")


# ============================================================
# ANNOTATED PSEUDOCODE for Main Function 0x80025E90
# ============================================================

print("\n" + "=" * 70)
print("ANNOTATED PSEUDOCODE: Main Spell Function (0x80025E90)")
print("=" * 70)
print("""
spell_damage_main($a0=caster_entity, $a1=target_entity,
                  $a2=spell_list_idx, $a3=spell_slot_id,
                  sp[0x50]=element_override):

  $s5 = caster_entity
  $s4 = target_entity
  $s3 = spell_list_idx
  $s0 = spell_slot_id

  // Hit check
  ret = hit_check_0x80026840(caster, target)
  if (ret != 0) return 1

  // Link caster <-> target
  caster[0x70] = target
  target[0x70] = caster

  // Get caster/target resolution (player vs monster paths)
  if (caster is player):
      caster_resolved = player_target_select(caster, -1, 0)
  else:
      caster_resolved = monster_target_select(caster, -1, 0)

  // Same for target
  target_resolved = ...

  // Overlay spell effects
  overlay_spell_effect(caster, 0x07)
  overlay_spell_effect(target, 0x11)

  // Check target immunity flags
  if (target_resolved[0x40] & 0x0010):   // immune to spell?
      overlay_visual_effect(target, ...)
      return 1

  // === LOAD SPELL ENTRY ===
  data_ptr = *(0x8005490C)
  pointer_table = *(data_ptr + 0x9C)
  list_base = pointer_table[spell_list_idx]
  spell_entry = list_base + spell_slot_id * 48
  $fp = spell_entry

  // Read element info from spell entry (+0x16 = element)
  element_offset = sp[0x50]   // 5th stack arg: element override
  element = lbu (spell_entry + element_offset)[0x16]  ; SPELL ELEMENT

  if (element != 0):
      // Element-specific damage processing
      element_idx = element * 2
      caster_resolved[0x010C + element_idx] += lhu (spell_entry + element_offset)[0x18]
      // This adds spell damage to caster's elemental attack accumulator

      // Zero out unrelated elemental slots for caster/target
      ...

  // === CASTER ATTACK POWER ===
  caster_attack = lh caster_resolved[0x38]     ; CASTER STAT +0x38
  divisor = lbu spell_entry[0x1E]              ; SPELL +0x1E param
  caster_attack = caster_attack / divisor      ; divide by spell param!

  random_val = random_number()
  luck_factor = lhu caster_resolved[0x2C]      ; CASTER STAT +0x2C (LUK?)
  luck_mod = random_val %% (luck_factor + 1)
  luck_mod = luck_mod / 4
  caster_attack = caster_attack + luck_mod
  if (caster_attack < 0) caster_attack = 0

  // === TARGET DEFENSE ===
  target_defense = lh target_resolved[0x3A]    ; TARGET STAT +0x3A (MDEF?)
  random_val2 = random_number()
  luck_factor2 = lhu target_resolved[0x2C]     ; TARGET STAT +0x2C (LUK?)
  luck_mod2 = random_val2 %% (luck_factor2 + 1)
  luck_mod2 = luck_mod2 / 4
  target_defense = target_defense + luck_mod2
  if (target_defense < 0) target_defense = 0

  // === ELEMENTAL INTERACTION ===
  elem_result = elemental_check_B(caster, target, caster_resolved, target_resolved)

  if (elem_result == 0):
      target_defense = target_defense / 2   // halved if elemental weakness

  raw_damage = caster_attack - target_defense
  if (raw_damage < 0) raw_damage = 0

  // === DEFENSE CALCULATION ===
  defense_mod = defense_calculation(caster_resolved, target_resolved)
  raw_damage = raw_damage + defense_mod

  // === APPLY TO SPELL ENTRY DAMAGE ===
  if (element != 0):
      // ...check element vulnerability...
      spell_base = lhu (spell_entry + element_offset)[0x18]  ; SPELL DAMAGE again
      raw_damage = raw_damage + spell_base

  // Store final damage
  ...

CRITICAL FORMULA SUMMARY:
  caster_power = entity_stat_0x38 / spell_param_0x1E
  caster_power += random(0, entity_stat_0x2C) / 4
  target_mdef  = entity_stat_0x3A
  target_mdef  += random(0, entity_stat_0x2C) / 4
  if (elemental_weakness): target_mdef /= 2
  raw_damage = caster_power - target_mdef
  raw_damage += defense_mod(caster, target)
  raw_damage += spell_entry_0x18  // flat spell base damage added on top

  Entity field mapping (tentative):
    +0x38 = Magic Attack (MATK)
    +0x3A = Magic Defense (MDEF)
    +0x2A = INT stat (used by simple handlers [10]-[13] as /3 contribution)
    +0x2C = LUK or similar (random factor)
    +0x010C = elemental damage accumulators
""")


# ============================================================
# Summary
# ============================================================

print("\n" + "=" * 70)
print("FINAL ANSWER: SPELL DAMAGE IS NOT PURELY FLAT")
print("=" * 70)
print("""
The spell damage formula has TWO LAYERS:

LAYER 1 - Simple handlers [10]-[13] (elemental spells?):
  damage = (caster_stat_0x2A / 3) + spell_entry_0x18
  - stat_0x2A appears to be INT/WIL
  - spell_entry_0x18 is the flat base damage from the spell table
  - No random component, no defense subtraction in these handlers
  - Stored to specific elemental damage slots on the target

LAYER 2 - Full function 0x80025E90 (main spell execution):
  caster_power = caster_MATK / spell_param_0x1E + random_luck
  target_defense = target_MDEF + random_luck
  if (elemental_weakness): target_defense /= 2
  damage = (caster_power - target_defense) + defense_mod + spell_entry_0x18

  KEY FIELDS:
  - spell_entry+0x18 = base damage (FLAT additive component)
  - spell_entry+0x1E = DIVISOR for caster MATK (higher = weaker scaling)
  - spell_entry+0x16 = element type (affects weakness/resistance)
  - entity+0x38 = Magic Attack stat (MATK)
  - entity+0x3A = Magic Defense stat (MDEF)
  - entity+0x2C = Luck/variance stat

CONCLUSION:
  Spell damage IS stat-scaled. The +0x18 damage value is added as a
  FLAT BONUS on top of the stat-based calculation:
    final_damage = stat_scaling_result + spell_base_damage

  The +0x1E field acts as a DIVISOR for the caster's MATK stat.
  A spell with +0x1E = 2 would use MATK/2, while +0x1E = 4 uses MATK/4.
  This means +0x1E controls how much stats matter relative to flat damage.
""")
