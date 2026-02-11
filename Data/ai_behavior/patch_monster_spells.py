#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Patch monster spell bitfield init in output/BLAZE.ALL overlay code.

**STATUS (2026-02-11): PERMANENTLY DISABLED**

All 6 patching attempts failed (v1-v6):
- Freeze tests confirmed offsets are DEAD CODE (no crash = never executes)
- Hardcoded values ignored (0x03FFFFFF had zero effect)
- See Data/ai_behavior/FAILED_ATTEMPTS.md for exhaustive log

Alternative solutions:
1. Patch EXE dispatch loop/tier table (RECOMMENDED)
2. Hybrid stats approach (increase MP + MATK for caster monsters)
See Data/ai_behavior/NEXT_STEPS.md for details.

---

ORIGINAL DESCRIPTION (now defunct):
The overlay init code writes entity+0x160 (spell availability bitfield) during
monster spawn. Original code sets byte 0 = 1 (only Fire Bullet) and clears
bytes 1-3. The level-up simulation then adds more bits based on monster level.

Two modes:
  - "zone_wide": All monsters in the zone get the same bitfield (original behavior).
    Patches ori+sb instructions to write different byte values.
  - "per_monster": Each monster type gets its own bitfield via table lookup.
    Replaces 14-instruction verbose pattern with compact MIPS code + embedded table.

Usage (standalone):  py -3 Data/ai_behavior/patch_monster_spells.py
Usage (in build):    Called at step 7e (patches BLAZE.ALL, not BIN)
"""

import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "overlay_bitfield_config.json"
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

# BLAZE.ALL <-> RAM mapping constant
# RAM = BLAZE_offset + BLAZE_TO_RAM_DELTA
# Derived from: RAM 0x80061478 -> BLAZE 0x00927D20 (verified for all zones)
BLAZE_TO_RAM_DELTA = 0x80000000 - 0x008C68A8  # = 0x7F739758

# MIPS R3000 register numbers
REG_ZERO = 0
REG_AT = 1
REG_V0 = 2
REG_V1 = 3

# -------------------------------------------------------------------
# MIPS instruction builders
# -------------------------------------------------------------------

def mips_ori(rt, rs, imm):
    """ori rt, rs, imm"""
    return (0x0D << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

def mips_sb(rt, offset, base):
    """sb rt, offset(base)"""
    return (0x28 << 26) | (base << 21) | (rt << 16) | (offset & 0xFFFF)

def mips_lui(rt, imm):
    """lui rt, imm"""
    return (0x0F << 26) | (rt << 16) | (imm & 0xFFFF)

def mips_lbu(rt, offset, base):
    """lbu rt, offset(base)"""
    return (0x24 << 26) | (base << 21) | (rt << 16) | (offset & 0xFFFF)

def mips_lw(rt, offset, base):
    """lw rt, offset(base)"""
    return (0x23 << 26) | (base << 21) | (rt << 16) | (offset & 0xFFFF)

def mips_sw(rt, offset, base):
    """sw rt, offset(base)"""
    return (0x2B << 26) | (base << 21) | (rt << 16) | (offset & 0xFFFF)

def mips_sll(rd, rt, shamt):
    """sll rd, rt, shamt"""
    return (rt << 16) | (rd << 11) | ((shamt & 0x1F) << 6)

def mips_addu(rd, rs, rt):
    """addu rd, rs, rt"""
    return (rs << 21) | (rt << 16) | (rd << 11) | 0x21

def mips_beq(rs, rt, offset):
    """beq rs, rt, offset (signed 16-bit word offset)"""
    return (0x04 << 26) | (rs << 21) | (rt << 16) | (offset & 0xFFFF)

def mips_addiu(rt, rs, imm):
    """addiu rt, rs, imm (signed 16-bit immediate)"""
    return (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

def mips_sh(rt, offset, base):
    """sh rt, offset(base)"""
    return (0x29 << 26) | (base << 21) | (rt << 16) | (offset & 0xFFFF)

def mips_nop():
    """nop (sll $zero, $zero, 0)"""
    return 0x00000000

# -------------------------------------------------------------------
# MIPS instruction disassembly (for logging)
# -------------------------------------------------------------------

REGNAMES = [
    '$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
    '$t0',   '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
    '$s0',   '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
    '$t8',   '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra',
]

def disasm_brief(word):
    """Brief disassembly for logging purposes."""
    if word == 0:
        return "nop"
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    imm = word & 0xFFFF
    if op == 0x0F:
        return "lui %s,0x%04X" % (REGNAMES[rt], imm)
    if op == 0x0D:
        return "ori %s,%s,0x%04X" % (REGNAMES[rt], REGNAMES[rs], imm)
    if op == 0x24:
        return "lbu %s,%d(%s)" % (REGNAMES[rt], imm if imm < 0x8000 else imm - 0x10000, REGNAMES[rs])
    if op == 0x23:
        return "lw %s,%d(%s)" % (REGNAMES[rt], imm if imm < 0x8000 else imm - 0x10000, REGNAMES[rs])
    if op == 0x2B:
        return "sw %s,%d(%s)" % (REGNAMES[rt], imm if imm < 0x8000 else imm - 0x10000, REGNAMES[rs])
    if op == 0x28:
        return "sb %s,%d(%s)" % (REGNAMES[rt], imm if imm < 0x8000 else imm - 0x10000, REGNAMES[rs])
    if op == 0x29:
        return "sh %s,%d(%s)" % (REGNAMES[rt], imm if imm < 0x8000 else imm - 0x10000, REGNAMES[rs])
    if op == 0x09:
        return "addiu %s,%s,%d" % (REGNAMES[rt], REGNAMES[rs], imm if imm < 0x8000 else imm - 0x10000)
    if op == 0x04:
        return "beq %s,%s,+%d" % (REGNAMES[rs], REGNAMES[rt], imm if imm < 0x8000 else imm - 0x10000)
    if op == 0 and (word & 0x3F) == 0 and shamt:
        return "sll %s,%s,%d" % (REGNAMES[rd], REGNAMES[rt], shamt)
    if op == 0 and (word & 0x3F) == 0x21:
        return "addu %s,%s,%s" % (REGNAMES[rd], REGNAMES[rs], REGNAMES[rt])
    return "0x%08X" % word


# -------------------------------------------------------------------
# Zone-wide patching (original mode)
# -------------------------------------------------------------------

def patch_verbose_site(data, offsets, bf_bytes):
    """Patch a verbose init site for zone-wide bitfield.

    Modifies ori immediates and sb register fields to write a custom 4-byte
    value instead of the original 01 00 00 00.
    """
    changes = []

    # Patch byte 0: change ori immediate
    off = int(offsets["byte0_ori"], 16)
    old = struct.unpack_from('<I', data, off)[0]
    new = mips_ori(REG_V1, REG_ZERO, bf_bytes[0])
    if old != new:
        if (old >> 26) != 0x0D:
            return None, "byte0_ori at 0x{:X}: not an ori (got 0x{:08X})".format(off, old)
        struct.pack_into('<I', data, off, new)
        changes.append("byte0_ori: 0x{:02X}".format(bf_bytes[0]))

    # Patch bytes 1-3
    for i, suffix in enumerate(["1", "2", "3"]):
        nop_key = "byte{}_nop".format(suffix)
        sb_key = "byte{}_sb".format(suffix)

        nop_off = int(offsets[nop_key], 16)
        sb_off = int(offsets[sb_key], 16)

        # Patch nop -> ori $v1, $zero, value
        old_nop = struct.unpack_from('<I', data, nop_off)[0]
        new_ori = mips_ori(REG_V1, REG_ZERO, bf_bytes[i + 1])
        if old_nop != new_ori:
            if old_nop != 0 and (old_nop >> 26) != 0x0D:
                return None, "byte{}_nop at 0x{:X}: not nop/ori (got 0x{:08X})".format(
                    suffix, nop_off, old_nop)
            struct.pack_into('<I', data, nop_off, new_ori)
            changes.append("byte{}_nop->ori 0x{:02X}".format(suffix, bf_bytes[i + 1]))

        # Patch sb: change rt from $zero to $v1
        old_sb = struct.unpack_from('<I', data, sb_off)[0]
        if (old_sb >> 26) != 0x28:
            return None, "byte{}_sb at 0x{:X}: not an sb (got 0x{:08X})".format(
                suffix, sb_off, old_sb)

        expected_offset = 0x0161 + i
        sb_imm = old_sb & 0xFFFF
        if sb_imm != expected_offset:
            return None, "byte{}_sb: offset 0x{:04X} != expected 0x{:04X}".format(
                suffix, sb_imm, expected_offset)

        rs = (old_sb >> 21) & 0x1F
        new_sb = mips_sb(REG_V1, expected_offset, rs)
        if old_sb != new_sb:
            struct.pack_into('<I', data, sb_off, new_sb)
            changes.append("byte{}_sb: $zero->$v1".format(suffix))

    return changes, None


# -------------------------------------------------------------------
# Per-monster patching (new mode)
# -------------------------------------------------------------------

def patch_per_monster_site(data, internal, monsters_config, default_bitfield):
    """Replace the 14-instruction verbose pattern with a table lookup + sentinel.

    Writes entity+0x160 (bitfield) AND entity+0x146 (sentinel = 9999).
    The sentinel causes the dispatch OR-loop to SKIP, so our bitfield is
    the definitive spell availability (not overwritten by level-up sim).

    Uses identity subtraction to compact the table:
      table_index = identity_byte - min_identity

    14 slots = 11 code instructions + 3 table entries:
      [0]  lui   $at, TABLE_HI
      [1]  lbu   $v1, ID_OFF($v0)       ; identity byte
      [2]  nop                            ; lbu load delay
      [3]  addiu $v1, $v1, -MIN_ID       ; compact index
      [4]  sll   $v1, $v1, 2            ; * 4
      [5]  addu  $at, $at, $v1          ; &table[index]
      [6]  lw    $v1, TABLE_LO($at)     ; bitfield
      [7]  ori   $at, $zero, 0x270F     ; sentinel=9999 (fills lw delay, reuses $at)
      [8]  sw    $v1, 0x160($v0)        ; store bitfield
      [9]  beq   $zero, $zero, +4       ; branch to [14] (past table)
      [10] sh    $at, 0x146($v0)        ; DELAY SLOT: store sentinel
      [11-13] table[0..2]               ; compact table (3 entries)
    """
    code_start = int(internal["code_start"], 16)
    identity_offset = int(internal["identity_offset"], 16)
    identity_map = internal["identity_map"]
    min_identity = int(internal.get("min_identity", 0))

    NUM_CODE = 11
    NUM_TABLE = 3
    NUM_SLOTS = NUM_CODE + NUM_TABLE  # 14

    # Build compact lookup table: (identity - min_identity) -> bitfield
    table = [default_bitfield] * NUM_TABLE
    for name, identity in identity_map.items():
        if isinstance(identity, str):
            identity = int(identity)
        idx = identity - min_identity
        if idx < 0 or idx >= NUM_TABLE:
            return None, "identity {} for '{}' -> index {} out of range [0, {})".format(
                identity, name, idx, NUM_TABLE)
        bf_hex = monsters_config.get(name)
        if bf_hex is None:
            return None, "monster '{}' in identity_map but not in monsters config".format(name)
        table[idx] = int(bf_hex, 16)

    # Compute table RAM address (table starts at instruction [NUM_CODE])
    table_blaze = code_start + NUM_CODE * 4
    table_ram = (table_blaze + BLAZE_TO_RAM_DELTA) & 0xFFFFFFFF

    table_lo = table_ram & 0xFFFF
    table_hi = (table_ram >> 16) & 0xFFFF
    if table_lo >= 0x8000:
        table_hi = (table_hi + 1) & 0xFFFF

    # Branch at [9] targets code_start + NUM_SLOTS*4
    beq_ram = ((code_start + 9 * 4) + BLAZE_TO_RAM_DELTA) & 0xFFFFFFFF
    skip_ram = ((code_start + NUM_SLOTS * 4) + BLAZE_TO_RAM_DELTA) & 0xFFFFFFFF
    branch_offset = (skip_ram - (beq_ram + 4)) // 4
    if branch_offset < 0 or branch_offset > 0x7FFF:
        return None, "branch offset {} out of range".format(branch_offset)

    # Validate first instruction
    old_word0 = struct.unpack_from('<I', data, code_start)[0]
    op0 = (old_word0 >> 26) & 0x3F
    if op0 not in (0x0D, 0x0F):  # ori=0x0D, lui=0x0F
        return None, "code_start 0x{:X}: expected ori/lui at [0], got opcode 0x{:02X} (0x{:08X})".format(
            code_start, op0, old_word0)

    # Encode min_identity subtraction as signed 16-bit: -min_identity
    sub_imm = (-min_identity) & 0xFFFF

    instructions = [
        mips_lui(REG_AT, table_hi),                         # [0]
        mips_lbu(REG_V1, identity_offset, REG_V0),         # [1]
        mips_nop(),                                          # [2] lbu delay
        mips_addiu(REG_V1, REG_V1, sub_imm),               # [3] identity - min
        mips_sll(REG_V1, REG_V1, 2),                       # [4] * 4
        mips_addu(REG_AT, REG_AT, REG_V1),                 # [5]
        mips_lw(REG_V1, table_lo, REG_AT),                 # [6] bitfield
        mips_ori(REG_AT, REG_ZERO, 0x270F),                # [7] sentinel=9999
        mips_sw(REG_V1, 0x0160, REG_V0),                   # [8] store bitfield
        mips_beq(REG_ZERO, REG_ZERO, branch_offset),       # [9] branch past table
        mips_sh(REG_AT, 0x0146, REG_V0),                   # [10] DELAY: sentinel
    ]

    changes = []
    all_words = instructions + table
    for i, word in enumerate(all_words):
        off = code_start + i * 4
        old = struct.unpack_from('<I', data, off)[0]
        if old != word:
            struct.pack_into('<I', data, off, word)
            if i < NUM_CODE:
                changes.append("[{}] {} -> {}".format(i, disasm_brief(old), disasm_brief(word)))
            else:
                idx = i - NUM_CODE
                names = [n for n, v in identity_map.items()
                         if (int(v) if isinstance(v, str) else v) - min_identity == idx]
                label = names[0] if names else "default"
                changes.append("table[{}] ({}) = 0x{:08X}".format(idx, label, word))

    return changes, None


# -------------------------------------------------------------------
# Per-monster patching: combat init site (13 instructions)
# -------------------------------------------------------------------

REG_S5 = 21

def patch_combat_init_site(data, site_config, identity_map, monsters_config,
                           default_bitfield, identity_offset, min_identity):
    """Replace the 13-instruction combat init pattern with table lookup + sentinel.

    Writes entity+0x160 (bitfield) AND entity+0x146 (sentinel = 9999).
    The sentinel causes the dispatch OR-loop to SKIP, so our bitfield is
    the definitive spell availability (not overwritten by level-up sim).

    Uses $s5 as entity base (not $v0). 13 instruction slots available.
    Uses identity subtraction to compact the table:
      table_index = identity_byte - min_identity

    13 slots = 10 code instructions + 3 table entries:
      [0]  lbu   $v1, ID_OFF($s5)       ; identity byte
      [1]  lui   $at, TABLE_HI          ; table addr high (fills lbu delay)
      [2]  addiu $v1, $v1, -MIN_ID      ; compact index
      [3]  sll   $v1, $v1, 2            ; * 4
      [4]  addu  $at, $at, $v1          ; &table[index]
      [5]  lw    $v1, TABLE_LO($at)     ; bitfield
      [6]  ori   $v0, $zero, 0x270F     ; sentinel=9999 (fills lw delay)
      [7]  sw    $v1, 0x160($s5)        ; store bitfield
      [8]  beq   $zero, $zero, +4       ; branch to [13] (past table)
      [9]  sh    $v0, 0x146($s5)        ; DELAY SLOT: store sentinel
      [10-12] table[0..2]               ; compact table (3 entries)
    """
    code_start = int(site_config["code_start"], 16)

    NUM_CODE = 10
    NUM_TABLE = 3
    NUM_SLOTS = NUM_CODE + NUM_TABLE  # 13

    # Build compact lookup table: (identity - min_identity) -> bitfield
    table = [default_bitfield] * NUM_TABLE
    for name, identity in identity_map.items():
        if isinstance(identity, str):
            identity = int(identity)
        idx = identity - min_identity
        if idx < 0 or idx >= NUM_TABLE:
            return None, "identity {} for '{}' -> index {} out of range [0, {})".format(
                identity, name, idx, NUM_TABLE)
        bf_hex = monsters_config.get(name)
        if bf_hex is None:
            return None, "monster '{}' in identity_map but not in monsters config".format(name)
        table[idx] = int(bf_hex, 16)

    # Table starts at instruction [NUM_CODE]
    table_blaze = code_start + NUM_CODE * 4
    table_ram = (table_blaze + BLAZE_TO_RAM_DELTA) & 0xFFFFFFFF

    table_lo = table_ram & 0xFFFF
    table_hi = (table_ram >> 16) & 0xFFFF
    if table_lo >= 0x8000:
        table_hi = (table_hi + 1) & 0xFFFF

    # Branch at [8] targets code_start + NUM_SLOTS*4
    beq_ram = ((code_start + 8 * 4) + BLAZE_TO_RAM_DELTA) & 0xFFFFFFFF
    skip_ram = ((code_start + NUM_SLOTS * 4) + BLAZE_TO_RAM_DELTA) & 0xFFFFFFFF
    branch_offset = (skip_ram - (beq_ram + 4)) // 4
    if branch_offset < 0 or branch_offset > 0x7FFF:
        return None, "branch offset {} out of range".format(branch_offset)

    # Validate: [0] should be ori (original) or lbu (already patched)
    old_word0 = struct.unpack_from('<I', data, code_start)[0]
    op0 = (old_word0 >> 26) & 0x3F
    if op0 not in (0x0D, 0x24):  # ori=0x0D, lbu=0x24
        return None, "combat code_start 0x{:X}: expected ori/lbu at [0], got opcode 0x{:02X} (0x{:08X})".format(
            code_start, op0, old_word0)

    # Encode min_identity subtraction as signed 16-bit
    sub_imm = (-min_identity) & 0xFFFF

    # Build 10 MIPS instructions (entity base = $s5)
    instructions = [
        mips_lbu(REG_V1, identity_offset, REG_S5),     # [0]
        mips_lui(REG_AT, table_hi),                      # [1] fills lbu delay
        mips_addiu(REG_V1, REG_V1, sub_imm),            # [2] identity - min
        mips_sll(REG_V1, REG_V1, 2),                    # [3] * 4
        mips_addu(REG_AT, REG_AT, REG_V1),              # [4]
        mips_lw(REG_V1, table_lo, REG_AT),              # [5] bitfield
        mips_ori(REG_V0, REG_ZERO, 0x270F),             # [6] sentinel=9999
        mips_sw(REG_V1, 0x0160, REG_S5),                # [7] store bitfield
        mips_beq(REG_ZERO, REG_ZERO, branch_offset),    # [8] branch past table
        mips_sh(REG_V0, 0x0146, REG_S5),                # [9] DELAY SLOT: sentinel
    ]

    # Write all 13 words
    changes = []
    all_words = instructions + table
    for i, word in enumerate(all_words):
        off = code_start + i * 4
        old = struct.unpack_from('<I', data, off)[0]
        if old != word:
            struct.pack_into('<I', data, off, word)
            if i < NUM_CODE:
                changes.append("[{}] {} -> {}".format(i, disasm_brief(old), disasm_brief(word)))
            else:
                idx = i - NUM_CODE
                names = [n for n, v in identity_map.items()
                         if (int(v) if isinstance(v, str) else v) - min_identity == idx]
                label = names[0] if names else "default"
                changes.append("table[{}] ({}) = 0x{:08X}".format(idx, label, word))

    return changes, None


# -------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------

def main():
    print("  Monster Spell Bitfield Patcher (BLAZE.ALL overlay)")
    print("  " + "-" * 50)
    print()
    print("  ⚠️  WARNING: This patcher is PERMANENTLY DISABLED")
    print("  All 6 attempts failed (v1-v6). Freeze tests confirmed: dead code.")
    print("  See Data/ai_behavior/FAILED_ATTEMPTS.md for details.")
    print()

    if not CONFIG_FILE.exists():
        print("  [SKIP] Config not found: {}".format(CONFIG_FILE.name))
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    section = config.get("overlay_bitfield_patches", {})
    if not section.get("enabled", False):
        print("  [SKIP] overlay_bitfield_patches not enabled (correct - system doesn't work)")
        return

    patches = section.get("patches", [])
    if not patches:
        print("  [SKIP] No patches defined")
        return

    if not BLAZE_ALL.exists():
        print("  [ERROR] BLAZE.ALL not found: {}".format(BLAZE_ALL))
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())
    applied = 0

    for patch in patches:
        if not patch.get("enabled", False):
            continue

        zone = patch.get("zone", "unknown")
        mode = patch.get("mode", "zone_wide")

        internal = patch.get("_internal_do_not_modify", {})
        patch_type = internal.get("type", patch.get("type", "verbose"))

        if mode == "per_monster":
            # Per-monster table lookup mode
            monsters_config = patch.get("monsters", {})
            default_hex = patch.get("default_bitfield", "0x00000001")
            default_bf = int(default_hex, 16)

            if not monsters_config:
                print("  [ERROR] {}: per_monster mode but no monsters defined".format(zone))
                sys.exit(1)

            identity_offset = int(internal["identity_offset"], 16)
            identity_map = internal["identity_map"]
            min_identity = int(internal.get("min_identity", 0))

            # Site 1: spawn init (14 instructions, entity in $v0)
            changes, error = patch_per_monster_site(data, internal, monsters_config, default_bf)
            if error:
                print("  [ERROR] {} spawn_init: {}".format(zone, error))
                sys.exit(1)
            if changes:
                print("  [PATCH] {} spawn_init (per_monster):".format(zone))
                for name, bf_hex in monsters_config.items():
                    print("    {}: bitfield={}".format(name, bf_hex))
                print("    default: 0x{:08X}".format(default_bf))
                for c in changes:
                    print("    {}".format(c))
                applied += 1
            else:
                print("  [OK] {} spawn_init: already patched".format(zone))

            # Site 2: combat init (13 instructions, entity in $s5)
            combat_sites = internal.get("combat_init_sites", [])
            for ci, combat_site in enumerate(combat_sites):
                changes2, error2 = patch_combat_init_site(
                    data, combat_site, identity_map, monsters_config,
                    default_bf, identity_offset, min_identity)
                if error2:
                    print("  [ERROR] {} combat_init[{}]: {}".format(zone, ci, error2))
                    sys.exit(1)
                if changes2:
                    print("  [PATCH] {} combat_init[{}] at 0x{}:".format(
                        zone, ci, combat_site["code_start"]))
                    for c in changes2:
                        print("    {}".format(c))
                    applied += 1
                else:
                    print("  [OK] {} combat_init[{}]: already patched".format(zone, ci))

        elif mode == "freeze_test":
            # DIAGNOSTIC: infinite loop at spawn+combat init sites
            INFINITE_LOOP = mips_beq(REG_ZERO, REG_ZERO, 0xFFFF)
            internal = patch.get("_internal_do_not_modify", {})
            spawn_start = int(internal["code_start"], 16)
            struct.pack_into('<I', data, spawn_start, INFINITE_LOOP)
            for combat_site in internal.get("combat_init_sites", []):
                combat_start = int(combat_site["code_start"], 16)
                struct.pack_into('<I', data, combat_start, INFINITE_LOOP)
            print("  [DIAG] {} FREEZE_TEST at spawn+combat init".format(zone))
            applied += 1

        elif mode == "freeze_test_entity_init":
            # DIAGNOSTIC: infinite loop at ENTITY INIT site (0x916C44)
            # This site zeros entity+0x160..+0x163, should be in Cavern overlay range
            INFINITE_LOOP = mips_beq(REG_ZERO, REG_ZERO, 0xFFFF)
            ENTITY_INIT_OFF = 0x00916C44
            struct.pack_into('<I', data, ENTITY_INIT_OFF, INFINITE_LOOP)
            print("  [DIAG] {} FREEZE_TEST at entity init BLAZE 0x{:08X}".format(
                zone, ENTITY_INIT_OFF))
            print("    If FREEZE → entity init executes (Cavern overlay includes 0x916xxx)")
            print("    If OK → entity init also not in Cavern overlay range")
            applied += 1

        elif mode == "hardcoded":
            # Hardcoded diagnostic: lui+ori+sw constant, no table, no sentinel
            # Tests whether code at these offsets actually EXECUTES.
            bf_hex = patch.get("default_bitfield", "0x03FFFFFF")
            bf_value = int(bf_hex, 16)
            bf_hi = (bf_value >> 16) & 0xFFFF
            bf_lo = bf_value & 0xFFFF

            internal = patch.get("_internal_do_not_modify", {})
            spawn_start = int(internal["code_start"], 16)

            # Spawn init: 14 slots, entity in $v0 (reg 2)
            spawn_code = [
                mips_lui(REG_V1, bf_hi),            # [0]
                mips_ori(REG_V1, REG_V1, bf_lo),    # [1]
                mips_sw(REG_V1, 0x0160, REG_V0),    # [2]
            ] + [mips_nop()] * 11                    # [3-13]

            changes_s = 0
            for i, word in enumerate(spawn_code):
                off = spawn_start + i * 4
                old = struct.unpack_from('<I', data, off)[0]
                if old != word:
                    struct.pack_into('<I', data, off, word)
                    changes_s += 1

            # Combat init: 13 slots, entity in $s5 (reg 21)
            combat_sites = internal.get("combat_init_sites", [])
            changes_c = 0
            for combat_site in combat_sites:
                combat_start = int(combat_site["code_start"], 16)
                combat_code = [
                    mips_lui(REG_V0, bf_hi),            # [0]
                    mips_ori(REG_V0, REG_V0, bf_lo),    # [1]
                    mips_sw(REG_V0, 0x0160, REG_S5),    # [2]
                ] + [mips_nop()] * 10                    # [3-12]

                for i, word in enumerate(combat_code):
                    off = combat_start + i * 4
                    old = struct.unpack_from('<I', data, off)[0]
                    if old != word:
                        struct.pack_into('<I', data, off, word)
                        changes_c += 1

            print("  [DIAG] {} HARDCODED mode: bitfield=0x{:08X}".format(zone, bf_value))
            print("    spawn_init: {} words changed".format(changes_s))
            print("    combat_init: {} words changed".format(changes_c))
            print("    No table, no sentinel, no identity lookup")
            print("    If NO EFFECT: code path not executed for this area")
            applied += 1

        elif mode == "zone_wide":
            # Zone-wide mode (original behavior)
            bf_hex = patch.get("bitfield_value", "0x00000001")
            bf_value = int(bf_hex, 16)
            bf_bytes = [
                bf_value & 0xFF,
                (bf_value >> 8) & 0xFF,
                (bf_value >> 16) & 0xFF,
                (bf_value >> 24) & 0xFF,
            ]

            offsets = patch.get("offsets", internal)

            if patch_type == "verbose":
                changes, error = patch_verbose_site(data, offsets, bf_bytes)
                if error:
                    print("  [ERROR] {}: {}".format(zone, error))
                    sys.exit(1)
                if changes:
                    print("  [PATCH] {}: bitfield=0x{:08X}".format(zone, bf_value))
                    for c in changes:
                        print("    {}".format(c))
                    applied += 1
                else:
                    print("  [OK] {}: already patched to 0x{:08X}".format(zone, bf_value))
            else:
                print("  [ERROR] Unknown patch type '{}'".format(patch_type))
                sys.exit(1)
        else:
            print("  [ERROR] Unknown mode '{}'".format(mode))
            sys.exit(1)

    if applied > 0:
        BLAZE_ALL.write_bytes(data)
        print("  [OK] {} overlay bitfield patch(es) applied".format(applied))
    else:
        print("  [SKIP] No overlay bitfield patches applied")


if __name__ == "__main__":
    main()
