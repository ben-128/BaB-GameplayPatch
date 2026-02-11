#!/usr/bin/env python3
"""
Patch chest despawn timer in BLAZE.ALL overlay code (v10).

v1-v8: Patched Function A in the main overlay (0x80080000+).
       All FAILED because Function A is NEVER called by the dispatcher.
       Function A is dead code for chests.

v9:    Patched Handler [0] in the stub region (0x8006E3AC).
       FAILED because Handler [0] is the ITEM bytecode interpreter,
       NOT the chest world entity system.

v10:   Patches the REAL chest_update function in the main overlay.
       The chest despawn timer is at entity+0x14, decremented every 20th frame
       by the entity update handler (index 41 in table at 0x8005A800).

       Target pattern (16 bytes):
         96xx0014  lhu $reg, 0x14($base)    ; load timer
         00000000  nop
         2442FFFF  addiu $v0,$v0,-1         ; decrement ← NOP THIS
         A6xx0014  sh $reg, 0x14($base)     ; store timer

       Followed within 12 bytes by:
         3C0x0200  lui $reg, 0x0200          ; dead flag 0x02000000

       The main overlay is per-dungeon, so we scan the entire BLAZE.ALL
       for all matching patterns to cover all dungeons.

Runs at build step 7 (patches output/BLAZE.ALL before BIN injection).
"""

import struct
import sys
from pathlib import Path

NOP = 0x00000000
ADDIU_M1 = 0x2442FFFF  # addiu $v0,$v0,-1


def find_chest_timer_patterns(data: bytes) -> list[int]:
    """Scan BLAZE.ALL for the chest timer decrement pattern.

    Pattern: lhu $reg, 0x14($base) / nop / addiu $v0,$v0,-1 / sh $reg, 0x14($base)
    Followed within 20 bytes by: lui $reg, 0x0200 (dead flag constant).
    """
    matches = []

    # Search for addiu $v0,$v0,-1 (0x2442FFFF) throughout the file
    target_bytes = struct.pack('<I', ADDIU_M1)
    pos = 0
    while True:
        pos = data.find(target_bytes, pos)
        if pos == -1:
            break
        if pos % 4 != 0:
            pos += 1
            continue

        # Check preceding instructions: lhu $reg, 0x14($base) at -8, nop at -4
        if pos < 8 or pos + 8 > len(data):
            pos += 4
            continue

        pre2 = struct.unpack_from('<I', data, pos - 8)[0]  # lhu
        pre1 = struct.unpack_from('<I', data, pos - 4)[0]  # nop
        post1 = struct.unpack_from('<I', data, pos + 4)[0]  # sh

        # Check nop
        if pre1 != 0x00000000:
            pos += 4
            continue

        # Check lhu $reg, 0x14($base): opcode=100101 (0x96), offset=0x0014
        if (pre2 >> 26) != 0x25 or (pre2 & 0xFFFF) != 0x0014:
            pos += 4
            continue

        # Check sh $reg, 0x14($base): opcode 0x29, offset 0x0014
        if (post1 >> 26) != 0x29 or (post1 & 0xFFFF) != 0x0014:
            pos += 4
            continue

        # Verify dead flag constant (lui $reg, 0x0200) within 20 bytes after sh
        found_dead_flag = False
        for j in range(8, 28, 4):
            if pos + j + 4 > len(data):
                break
            instr = struct.unpack_from('<I', data, pos + j)[0]
            # lui $reg, 0x0200: top bits = 0x3C0x, immediate = 0x0200
            if (instr >> 16) & 0xFFE0 == 0x3C00 and (instr & 0xFFFF) == 0x0200:
                found_dead_flag = True
                break

        if not found_dead_flag:
            pos += 4
            continue

        matches.append(pos)
        pos += 4

    return matches


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'output' / 'BLAZE.ALL'

    print("Loot Timer v10: chest_update overlay patch (pattern scan)")
    print(f"  Target: {blaze_path}")

    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    data = bytearray(blaze_path.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    matches = find_chest_timer_patterns(data)
    print(f"  Pattern matches found: {len(matches)}")

    if not matches:
        print("[ERROR] No chest timer patterns found!")
        sys.exit(1)

    patched = 0
    for offset in matches:
        current = struct.unpack_from('<I', data, offset)[0]
        ram_main = (offset - 0x009468A8) + 0x80080000

        if current == NOP:
            print(f"  0x{offset:08X} (RAM ~0x{ram_main:08X}): already NOPed")
            continue

        if current != ADDIU_M1:
            print(f"  0x{offset:08X}: UNEXPECTED 0x{current:08X}, skipping")
            continue

        data[offset:offset+4] = struct.pack('<I', NOP)
        patched += 1
        print(f"  PATCH 0x{offset:08X} (RAM ~0x{ram_main:08X}): addiu $v0,$v0,-1 -> nop")

    if patched == 0:
        print()
        print(f"{'='*60}")
        print(f"  All {len(matches)} chest timer decrements already patched")
        print(f"{'='*60}")
    else:
        blaze_path.write_bytes(data)
        print()
        print(f"{'='*60}")
        print(f"  Patched {patched}/{len(matches)} chest timer decrements")
        print(f"  Chest despawn timer frozen for all dungeons")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()
