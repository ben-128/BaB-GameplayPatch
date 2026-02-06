#!/usr/bin/env python3
"""
Patch the chest despawn timer in BLAZE.ALL.

Searches for the countdown pattern in per-dungeon overlays:
  lhu   $v0, 0x0014($base)   ; load timer
  ...                         ; (nop or delay slot fill)
  addiu $v0, $v0, -1          ; decrement
  sh    $v0, 0x0014($base)   ; store back

Replaces the decrement with addiu $v0, $v0, 0 (freeze timer = chests stay).

This is a TEST patch to confirm the mechanism. 41 instances across BLAZE.ALL.
"""

import json
import os
import struct
import sys

# MIPS instruction constants
ADDIU_V0_V0_MINUS1 = 0x2442FFFF  # addiu $v0, $v0, -1
ADDIU_V0_V0_ZERO = 0x24420000    # addiu $v0, $v0, 0 (NOP the decrement)

OP_LHU = 0x25
OP_LH = 0x21
OP_SH = 0x29
REG_V0 = 2
FIELD_OFFSET = 0x0014


def decode_mips(word):
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    imm = word & 0xFFFF
    return opcode, rs, rt, imm


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    blaze_path = os.path.join(project_dir, 'output', 'BLAZE.ALL')

    print("Loot Timer: patching countdown decrement (addiu $v0,$v0,-1 -> 0)")
    print("            Target: entity field +0x14 in per-dungeon overlays")

    if not os.path.exists(blaze_path):
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    with open(blaze_path, 'rb') as f:
        data = bytearray(f.read())

    # Find all addiu $v0, $v0, -1
    target = struct.pack('<I', ADDIU_V0_V0_MINUS1)
    replacement = struct.pack('<I', ADDIU_V0_V0_ZERO)
    patched = 0
    pos = 0

    reg_names = {
        0: 'zero', 2: 'v0', 3: 'v1', 4: 'a0', 5: 'a1', 6: 'a2', 7: 'a3',
        16: 's0', 17: 's1', 18: 's2', 19: 's3', 20: 's4',
    }

    while True:
        pos = data.find(target, pos)
        if pos == -1:
            break

        if pos % 4 != 0:
            pos += 1
            continue

        # Check sh $v0, 0x0014($base) after the addiu
        if pos + 8 > len(data):
            pos += 4
            continue

        sh_word = struct.unpack_from('<I', data, pos + 4)[0]
        sh_op, sh_base, sh_rt, sh_off = decode_mips(sh_word)

        if not (sh_op == OP_SH and sh_rt == REG_V0 and sh_off == FIELD_OFFSET):
            pos += 4
            continue

        # Check lhu/lh $v0, 0x0014($base) before (within 5 instructions)
        found_load = False
        for back in range(4, 24, 4):
            if pos - back < 0:
                break
            ld_word = struct.unpack_from('<I', data, pos - back)[0]
            ld_op, ld_base, ld_rt, ld_off = decode_mips(ld_word)

            if ld_op in (OP_LHU, OP_LH) and ld_rt == REG_V0 and ld_off == FIELD_OFFSET:
                if ld_base == sh_base:
                    found_load = True
                    break

        if not found_load:
            pos += 4
            continue

        base_name = reg_names.get(sh_base, f'r{sh_base}')
        print(f"  PATCH 0x{pos:08X}: addiu $v0,$v0,-1 -> 0  (base=${base_name})")

        data[pos:pos + 4] = replacement
        patched += 1
        pos += 4

    if patched == 0:
        print("[WARNING] No countdown patterns found!")
        sys.exit(1)

    with open(blaze_path, 'wb') as f:
        f.write(data)

    print(f"\nPatched {patched} countdown decrements (chests should stay permanently)")


if __name__ == '__main__':
    main()
