#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Patch monster spell bitfield init in output/BLAZE.ALL overlay code.

The overlay init code writes entity+0x160 (spell availability bitfield) during
monster spawn. Original code sets byte 0 = 1 (only Fire Bullet) and clears
bytes 1-3. The level-up simulation then adds more bits based on monster level.

This patcher modifies the init code to write a custom 4-byte value, giving ALL
monsters in the zone the specified spell bitfield as a starting point.

There are two init patterns in BLAZE.ALL:
  - "verbose": loads entity ptr from RAM each time (overlay-specific init)
  - "compact": uses saved register $s5 (shared entity init)

This patcher handles the "verbose" pattern found in zone overlays.

NOTE: This replaces the old patcher which incorrectly patched EXE address
0x8002BE38 (CD-ROM DMA code) instead of the actual spell assignment.

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

# MIPS instruction builders
def mips_ori(rt, rs, imm):
    """ori rt, rs, imm"""
    return (0x0D << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

def mips_sb(rt, offset, base):
    """sb rt, offset(base)"""
    return (0x28 << 26) | (base << 21) | (rt << 16) | (offset & 0xFFFF)

REG_ZERO = 0
REG_V1 = 3


def patch_verbose_site(data, offsets, bf_bytes):
    """Patch a verbose init site (loads entity ptr from RAM each time).

    The verbose pattern is:
      ori $v1, $zero, 0x0001         @ byte0_ori
      sb $v1, 0x0160($v0)            @ byte0_sb
      ... (reload $v0) ...
      nop                            @ byte1_nop
      sb $zero, 0x0161($v0)          @ byte1_sb
      ... (reload $v0) ...
      nop                            @ byte2_nop
      sb $zero, 0x0162($v0)          @ byte2_sb
      ... (reload $v0) ...
      nop                            @ byte3_nop
      sb $zero, 0x0163($v0)          @ byte3_sb

    We patch:
      - byte0_ori: change immediate to bf_bytes[0]
      - byte1_nop: change to ori $v1, $zero, bf_bytes[1]
      - byte1_sb:  change rt from $zero to $v1
      - byte2_nop: change to ori $v1, $zero, bf_bytes[2]
      - byte2_sb:  change rt from $zero to $v1
      - byte3_nop: change to ori $v1, $zero, bf_bytes[3]
      - byte3_sb:  change rt from $zero to $v1
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


def main():
    print("  Monster Spell Bitfield Patcher (BLAZE.ALL overlay)")
    print("  " + "-" * 50)

    if not CONFIG_FILE.exists():
        print("  [SKIP] Config not found: {}".format(CONFIG_FILE.name))
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    section = config.get("overlay_bitfield_patches", {})
    if not section.get("enabled", False):
        print("  [SKIP] overlay_bitfield_patches not enabled")
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
        bf_hex = patch.get("bitfield_value", "0x00000001")
        bf_value = int(bf_hex, 16)
        bf_bytes = [
            bf_value & 0xFF,
            (bf_value >> 8) & 0xFF,
            (bf_value >> 16) & 0xFF,
            (bf_value >> 24) & 0xFF,
        ]

        # Offsets are in _internal_do_not_modify (new format) or offsets (old format)
        internal = patch.get("_internal_do_not_modify", {})
        offsets = patch.get("offsets", internal)
        patch_type = offsets.get("type", patch.get("type", "verbose"))

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

    if applied > 0:
        BLAZE_ALL.write_bytes(data)
        print("  [OK] {} overlay bitfield patch(es) applied".format(applied))
    else:
        print("  [SKIP] No overlay bitfield patches applied")


if __name__ == "__main__":
    main()
