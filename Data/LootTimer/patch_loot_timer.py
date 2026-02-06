#!/usr/bin/env python3
"""
Patch the chest despawn timer in BLAZE.ALL.

Searches for MIPS instruction patterns that initialize the chest timer:
  addiu $v0, $zero, 1000  followed by  sh $v0, 0x0012($reg)
and patches the value 1000 to the desired frame count.

Also patches the slti guard instructions that cap the timer at 1000/1001.

Original: 1000 frames @ 50fps PAL = 20 seconds.
"""

import json
import os
import struct
import sys

ORIGINAL_FRAMES = 1000
PAL_FPS = 50

# MIPS opcodes
OP_ADDIU = 0x09
OP_SLTI = 0x0A
OP_SH = 0x29

# Register: $v0 = 2, $zero = 0
REG_V0 = 2
REG_ZERO = 0

# Entity field offset for the timer
TIMER_FIELD_OFFSET = 0x0012


def find_all(data, pattern):
    results = []
    start = 0
    while True:
        pos = data.find(pattern, start)
        if pos == -1:
            break
        results.append(pos)
        start = pos + 1
    return results


def decode_mips(word):
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    imm = word & 0xFFFF
    return opcode, rs, rt, imm


def encode_instruction(opcode, rs, rt, imm):
    return struct.pack('<I', (opcode << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF))


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'loot_timer.json')
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    blaze_path = os.path.join(project_dir, 'output', 'BLAZE.ALL')

    if not os.path.exists(config_path):
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    seconds = config.get('chest_despawn_seconds', 20)
    new_frames = seconds * PAL_FPS

    if new_frames > 32767:
        print(f"[ERROR] {seconds}s * {PAL_FPS}fps = {new_frames} frames exceeds signed 16-bit max (32767)")
        print(f"        Maximum supported: {32767 // PAL_FPS}s = {32767 // PAL_FPS * PAL_FPS} frames")
        sys.exit(1)

    print(f"Loot Timer: {seconds}s = {new_frames} frames @ {PAL_FPS}fps (original: {ORIGINAL_FRAMES} frames = {ORIGINAL_FRAMES // PAL_FPS}s)")

    if not os.path.exists(blaze_path):
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    with open(blaze_path, 'rb') as f:
        data = bytearray(f.read())

    # Pattern: addiu $v0, $zero, 1000 = 0x240203E8
    addiu_pattern = encode_instruction(OP_ADDIU, REG_ZERO, REG_V0, ORIGINAL_FRAMES)
    addiu_hits = find_all(data, addiu_pattern)

    patched_addiu = 0
    patched_slti = 0

    for pos in addiu_hits:
        if pos + 8 > len(data):
            continue

        # Check next instruction: sh $v0, 0x0012($reg)?
        next_word = struct.unpack_from('<I', data, pos + 4)[0]
        opcode, base_reg, rt, offset = decode_mips(next_word)

        if not (opcode == OP_SH and rt == REG_V0 and offset == TIMER_FIELD_OFFSET):
            continue

        reg_names = {16: 's0', 17: 's1', 6: 'a2', 5: 'a1', 4: 'a0'}
        base_name = reg_names.get(base_reg, f'r{base_reg}')
        print(f"  PATCH 0x{pos:08X}: addiu $v0,$zero,{ORIGINAL_FRAMES} + sh $v0,0x12(${base_name})")

        # Patch addiu value
        data[pos:pos + 4] = encode_instruction(OP_ADDIU, REG_ZERO, REG_V0, new_frames)
        patched_addiu += 1

        # Look backwards for slti guard (within 5 instructions = 20 bytes)
        for back in range(4, 24, 4):
            if pos - back < 0:
                break
            prev_word = struct.unpack_from('<I', data, pos - back)[0]
            prev_op, prev_rs, prev_rt, prev_imm = decode_mips(prev_word)

            if prev_op == OP_SLTI and prev_imm in (ORIGINAL_FRAMES, ORIGINAL_FRAMES + 1):
                new_slti_val = new_frames if prev_imm == ORIGINAL_FRAMES else new_frames + 1
                data[pos - back:pos - back + 4] = encode_instruction(
                    OP_SLTI, prev_rs, prev_rt, new_slti_val
                )
                patched_slti += 1
                print(f"    + slti guard at 0x{pos - back:08X}: {prev_imm} -> {new_slti_val}")
                break

    if patched_addiu == 0:
        print("[WARNING] No timer patterns found in BLAZE.ALL!")
        print("          The file may already be patched or is not a clean copy.")
        sys.exit(1)

    with open(blaze_path, 'wb') as f:
        f.write(data)

    print(f"\nPatched {patched_addiu} timer values + {patched_slti} slti guards")
    print(f"Chest despawn: {ORIGINAL_FRAMES} frames ({ORIGINAL_FRAMES // PAL_FPS}s) -> {new_frames} frames ({seconds}s)")


if __name__ == '__main__':
    main()
