#!/usr/bin/env python3
"""
Loot Timer Patcher v18 - QUADRUPLE PATCH (function + callers + timer + entry)

=== Why v17 failed ===

v17 patched: check_kill function (Layer 1), all 17 JAL callers (Layer 2),
and timer-based kill (Layer 3). All patches verified IN RAM via savestate.
But chests still died.

Root cause: the dead flag (0x02000000) is set EXTERNALLY by the EXE entity
manager's free-list system when parent monster dies. The dead flag check at
each handler's ENTRY runs BEFORE check_kill, so the entity is destroyed
before check_kill can intervene.

=== v18 STRATEGY: Four layers ===

LAYER 1: Patch check_kill function to return 0 (same as v16/v17)
  - BLAZE 0x0093B908: jr $ra + addu $v0,$zero,$zero

LAYER 2: NOP all JAL callers - replace jal with addiu $v0,$zero,0 (same as v17)

LAYER 3: Scan for timer-based kill pattern (same as v17)

LAYER 4 (NEW): NOP the dead flag check at entity handler ENTRY
  - Pattern scan across ALL overlays in BLAZE.ALL
  - Pattern A: lw $v0,0($s0) / lw $s1,0x74($s0) / lui $v1,0x200 / and / bne
  - Pattern B: lw $a0,0($s1) / lui $a2,0x200 / and / beq
  - Pattern C: lw $a0,0($s0) / lui $a2,0x200 / and / beq
  - For bne: NOP it (fall through to normal code)
  - For beq: make unconditional (always skip death handler)
"""

import struct
import sys
from pathlib import Path


# ============================================================================
# LAYER 1: Function patch (check_kill -> return 0)
# ============================================================================
FUNC_BLAZE_OFFSET = 0x0093B908
FUNC_ORIG_1 = 0x8C840074   # lw $a0, 0x0074($a0)
FUNC_ORIG_2 = 0x00000000   # nop
FUNC_PATCH_1 = 0x03E00008  # jr $ra
FUNC_PATCH_2 = 0x00001021  # addu $v0, $zero, $zero

# ============================================================================
# LAYER 2: All 17 JAL callers (jal 0x80075060 = 0x0C01D418)
# Replace with: addiu $v0, $zero, 0 (= 0x24020000)
# ============================================================================
JAL_WORD = 0x0C01D418       # jal 0x80075060
JAL_REPLACE = 0x24020000     # addiu $v0, $zero, 0

# Known caller offsets (found by scanning entire BLAZE.ALL)
# 8 STUB callers (shared across all zones) + 9 MAIN callers (Cavern F1)
JAL_CALLERS = [
    # STUB callers (shared)
    0x009406FC, 0x00942E60, 0x00943788, 0x00943CBC,
    0x009444A0, 0x00944E2C, 0x009457F8, 0x009461B4,
    # MAIN callers (Cavern F1)
    0x00946E9C, 0x00948AF4, 0x0094CA78, 0x0094D348,
    0x0094E0C0, 0x0094E474, 0x0094F17C, 0x0094F3F4,
    0x0094F66C,
]

# ============================================================================
# LAYER 4: Dead flag check patterns at entity handler entry
# ============================================================================
# Pattern A: chest_update style (16 bytes)
#   lw $v0, 0x0000($s0)      8E020000
#   lw $s1, 0x0074($s0)      8E110074
#   lui $v1, 0x0200           3C030200
#   and $v0, $v0, $v1         00431024
#   bne $v0, $zero, N         1440XXXX -> NOP
PATTERN_A = bytes([
    0x00, 0x00, 0x02, 0x8E,  # 8E020000
    0x74, 0x00, 0x11, 0x8E,  # 8E110074
    0x00, 0x02, 0x03, 0x3C,  # 3C030200
    0x24, 0x10, 0x43, 0x00,  # 00431024
])

# Pattern B: STUB style with $s1 base (12 bytes)
#   lw $a0, 0x0000($s1)      8E240000
#   lui $a2, 0x0200           3C060200
#   and $v0, $a0, $a2         00861024
#   beq $v0, $zero, N         1040XXXX -> unconditional
PATTERN_B = bytes([
    0x00, 0x00, 0x24, 0x8E,  # 8E240000
    0x00, 0x02, 0x06, 0x3C,  # 3C060200
    0x24, 0x10, 0x86, 0x00,  # 00861024
])

# Pattern C: STUB style with $s0 base (12 bytes)
#   lw $a0, 0x0000($s0)      8E040000
#   lui $a2, 0x0200           3C060200
#   and $v0, $a0, $a2         00861024
#   beq $v0, $zero, N         1040XXXX -> unconditional
PATTERN_C = bytes([
    0x00, 0x00, 0x04, 0x8E,  # 8E040000
    0x00, 0x02, 0x06, 0x3C,  # 3C060200
    0x24, 0x10, 0x86, 0x00,  # 00861024
])


def patch_layer1(data):
    """Patch check_kill function to return 0."""
    print("\n  --- LAYER 1: Patch check_kill function ---")

    w1 = struct.unpack_from('<I', data, FUNC_BLAZE_OFFSET)[0]
    w2 = struct.unpack_from('<I', data, FUNC_BLAZE_OFFSET + 4)[0]

    if w1 == FUNC_PATCH_1 and w2 == FUNC_PATCH_2:
        print(f"  Already patched at 0x{FUNC_BLAZE_OFFSET:08X}")
        return True

    if w1 != FUNC_ORIG_1:
        print(f"  [WARN] Unexpected instruction at 0x{FUNC_BLAZE_OFFSET:08X}: "
              f"0x{w1:08X} (expected 0x{FUNC_ORIG_1:08X})")
        return False

    struct.pack_into('<I', data, FUNC_BLAZE_OFFSET, FUNC_PATCH_1)
    struct.pack_into('<I', data, FUNC_BLAZE_OFFSET + 4, FUNC_PATCH_2)
    print(f"  0x{FUNC_BLAZE_OFFSET:08X}: lw $a0,0x74($a0) -> jr $ra")
    print(f"  0x{FUNC_BLAZE_OFFSET + 4:08X}: nop -> addu $v0,$zero,$zero")
    return True


def patch_layer2(data):
    """NOP all 17 JAL callers: replace jal with addiu $v0,$zero,0."""
    print("\n  --- LAYER 2: NOP all JAL callers ---")

    patched = 0
    already = 0

    for off in JAL_CALLERS:
        w = struct.unpack_from('<I', data, off)[0]
        if w == JAL_WORD:
            struct.pack_into('<I', data, off, JAL_REPLACE)
            patched += 1
            print(f"  0x{off:08X}: jal 0x80075060 -> addiu $v0,$zero,0")
        elif w == JAL_REPLACE:
            already += 1
        else:
            print(f"  [WARN] 0x{off:08X}: unexpected 0x{w:08X} (not jal)")

    # Also scan for any additional JAL callers we might have missed
    extra = 0
    for i in range(0, len(data) - 4, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if w == JAL_WORD and i not in JAL_CALLERS:
            struct.pack_into('<I', data, i, JAL_REPLACE)
            extra += 1
            print(f"  0x{i:08X}: jal 0x80075060 -> addiu $v0,$zero,0 (EXTRA!)")

    print(f"  Patched: {patched}, already: {already}, extra: {extra}")
    return True


def patch_layer3(data):
    """Scan for timer-based dead flag pattern and NOP the kill instruction."""
    print("\n  --- LAYER 3: Scan for timer kill patterns ---")

    patched = 0

    for i in range(0, len(data) - 40, 4):
        w = struct.unpack_from('<I', data, i)[0]
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op != 0x0F or imm != 0x0200:  # lui $ANY, 0x0200
            continue
        mask_reg = (w >> 16) & 0x1F

        # Check: instruction before should be bne $reg, $zero, skip
        if i < 4:
            continue
        prev = struct.unpack_from('<I', data, i - 4)[0]
        prev_op = (prev >> 26) & 0x3F
        prev_rt = (prev >> 16) & 0x1F
        if prev_op != 0x05 or prev_rt != 0:  # bne $rs, $zero
            continue

        # Check: 2 instructions before bne should be sh $reg, 0x14($base)
        found_sh = False
        for back in range(2, 6):
            if i - back * 4 < 0:
                break
            wb = struct.unpack_from('<I', data, i - back * 4)[0]
            wb_op = (wb >> 26) & 0x3F
            wb_imm = wb & 0xFFFF
            if wb_op == 0x29 and wb_imm == 0x0014:  # sh $reg, 0x14($base)
                found_sh = True
                for back2 in range(1, 4):
                    if i - (back + back2) * 4 < 0:
                        break
                    wb2 = struct.unpack_from('<I', data, i - (back + back2) * 4)[0]
                    wb2_op = (wb2 >> 26) & 0x3F
                    wb2_imm = wb2 & 0xFFFF
                    if wb2_op == 0x25 and wb2_imm == 0x0014:  # lhu $reg, 0x14($base)
                        found_sh = True
                        break
                break

        if not found_sh:
            continue

        # Check kill sequence after lui
        if i + 20 > len(data):
            continue

        w1 = struct.unpack_from('<I', data, i + 4)[0]
        w2 = struct.unpack_from('<I', data, i + 8)[0]
        w3 = struct.unpack_from('<I', data, i + 12)[0]
        w4 = struct.unpack_from('<I', data, i + 16)[0]

        w1_op = (w1 >> 26) & 0x3F
        w1_imm = w1 & 0xFFFF
        w4_op = (w4 >> 26) & 0x3F
        w4_imm = w4 & 0xFFFF

        if w1_op != 0x23 or w1_imm != 0x0000:
            continue
        if w4_op != 0x2B or w4_imm != 0x0000:
            continue

        w3_op = (w3 >> 26) & 0x3F
        w3_func = w3 & 0x3F
        if w3_op != 0x00 or w3_func != 0x25:
            continue

        if w3 != 0x00000000:
            struct.pack_into('<I', data, i + 12, 0x00000000)
            struct.pack_into('<I', data, i + 16, 0x00000000)
            patched += 1
            print(f"  0x{i + 12:08X}: or -> nop (dead flag set disabled)")
            print(f"  0x{i + 16:08X}: sw -> nop")

    print(f"  Timer kill patterns patched: {patched}")
    return True


def patch_layer4(data):
    """NOP/bypass dead flag check at entity handler entry.

    The dead flag (0x02000000) is set EXTERNALLY by the entity manager
    when parent monster is freed. Each handler checks this flag at entry
    and destroys the entity if set. We disable this check so entities
    survive even when externally marked dead.

    Three patterns are searched across all overlay code in BLAZE.ALL:
    - Pattern A: bne after dead check -> NOP (fall through to normal code)
    - Pattern B/C: beq after dead check -> unconditional (always skip death handler)
    """
    print("\n  --- LAYER 4: NOP dead flag check at handler entry ---")

    # Only search in code region (overlays start around 0x0091D80C)
    CODE_START = 0x00900000
    patched_a = 0
    patched_bc = 0

    # --- Pattern A: chest_update style ---
    # 16-byte signature followed by bne
    pos = CODE_START
    while pos < len(data) - 20:
        idx = data.find(PATTERN_A, pos)
        if idx == -1 or idx >= len(data) - 20:
            break

        branch_off = idx + 16
        branch = struct.unpack_from('<I', data, branch_off)[0]
        branch_op = (branch >> 26) & 0x3F
        branch_rt = (branch >> 16) & 0x1F

        if branch_op == 0x05 and branch_rt == 0:  # bne $v0, $zero, N
            # NOP the bne
            struct.pack_into('<I', data, branch_off, 0x00000000)
            patched_a += 1
            print(f"  [A] 0x{branch_off:08X}: bne -> nop (dead flag check disabled)")
        elif branch_op == 0x04 and branch_rt == 0:  # beq $v0, $zero, N
            # Make unconditional: clear rs field
            branch = branch & ~(0x1F << 21)
            struct.pack_into('<I', data, branch_off, branch)
            patched_a += 1
            print(f"  [A] 0x{branch_off:08X}: beq -> unconditional")

        pos = idx + 4

    # --- Pattern B: STUB style with $s1 base ---
    pos = CODE_START
    while pos < len(data) - 16:
        idx = data.find(PATTERN_B, pos)
        if idx == -1 or idx >= len(data) - 16:
            break

        branch_off = idx + 12
        branch = struct.unpack_from('<I', data, branch_off)[0]
        branch_op = (branch >> 26) & 0x3F
        branch_rt = (branch >> 16) & 0x1F

        if branch_op == 0x04 and branch_rt == 0:  # beq $v0, $zero, N
            branch = branch & ~(0x1F << 21)
            struct.pack_into('<I', data, branch_off, branch)
            patched_bc += 1
            print(f"  [B] 0x{branch_off:08X}: beq -> unconditional")
        elif branch_op == 0x05 and branch_rt == 0:  # bne $v0, $zero, N
            struct.pack_into('<I', data, branch_off, 0x00000000)
            patched_bc += 1
            print(f"  [B] 0x{branch_off:08X}: bne -> nop")

        pos = idx + 4

    # --- Pattern C: STUB style with $s0 base ---
    pos = CODE_START
    while pos < len(data) - 16:
        idx = data.find(PATTERN_C, pos)
        if idx == -1 or idx >= len(data) - 16:
            break

        branch_off = idx + 12
        branch = struct.unpack_from('<I', data, branch_off)[0]
        branch_op = (branch >> 26) & 0x3F
        branch_rt = (branch >> 16) & 0x1F

        if branch_op == 0x04 and branch_rt == 0:  # beq $v0, $zero, N
            branch = branch & ~(0x1F << 21)
            struct.pack_into('<I', data, branch_off, branch)
            patched_bc += 1
            print(f"  [C] 0x{branch_off:08X}: beq -> unconditional")
        elif branch_op == 0x05 and branch_rt == 0:  # bne $v0, $zero, N
            struct.pack_into('<I', data, branch_off, 0x00000000)
            patched_bc += 1
            print(f"  [C] 0x{branch_off:08X}: bne -> nop")

        pos = idx + 4

    total = patched_a + patched_bc
    print(f"  Pattern A (chest_update): {patched_a}")
    print(f"  Pattern B/C (STUB/other): {patched_bc}")
    print(f"  Total entry checks disabled: {total}")

    if total == 0:
        print("  [WARN] No patterns found! Layer 4 had no effect.")
        return False

    return True


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    work_blaze = project_dir / 'output' / 'BLAZE.ALL'

    print("=" * 60)
    print("Loot Timer Patcher v18 - Quadruple Layer")
    print("  Layer 1: check_kill function -> return 0")
    print("  Layer 2: All JAL callers -> $v0 = 0")
    print("  Layer 3: Timer kill patterns -> NOP dead flag")
    print("  Layer 4: Entry dead flag check -> NOP/bypass")
    print("=" * 60)

    if not work_blaze.exists():
        print(f"[ERROR] Work BLAZE.ALL not found: {work_blaze}")
        sys.exit(1)

    data = bytearray(work_blaze.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    ok1 = patch_layer1(data)
    ok2 = patch_layer2(data)
    ok3 = patch_layer3(data)
    ok4 = patch_layer4(data)

    if not (ok1 and ok2 and ok3 and ok4):
        print("\n  [ERROR] Some patches failed!")
        sys.exit(1)

    work_blaze.write_bytes(data)

    print(f"\n  [OK] All 4 layers applied successfully!")
    print(f"  Effect: Entities immune to external dead flag + timer + check_kill")
    print("=" * 60)

    sys.exit(0)


if __name__ == '__main__':
    main()
