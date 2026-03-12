#!/usr/bin/env python3
"""
Loot Timer Patcher v20 - FIVE LAYERS (function + callers + timer + entry + chest region)

=== Why v19 failed ===

v19 added Pattern D (movement handler at BLAZE 0x0094E4BC), but chests still disappear.
Root cause: there are MORE independent handlers for the chest entity, each with their own
dead flag check using different register combinations not covered by Patterns A-D.

Known unpatched kills:
- BLAZE 0x0094E140: fade-out handler (lw $a1,0($s0) + lui $a2,0x200 = Pattern E)
  Decrements entity+0x38 (color) when dead flag set, kills when color reaches 0.
- BLAZE 0x0094EE78: opacity check (slti $v0,$v0,128 -> kill) - triggered by fade-out
- Multiple other checks in 0x0094DECC-0x0094F800 region

=== v20 STRATEGY: Five layers ===

LAYER 1: Patch check_kill function to return 0
LAYER 2: NOP all JAL callers
LAYER 3: Scan for timer-based kill pattern
LAYER 4: Named pattern dead flag checks (A/B/C/D) across all overlays
LAYER 5 (NEW): Generic broad scan of chest handler region 0x0094DECC-0x0094F800
  Catches ALL dead flag check patterns regardless of register combination:
  lui $ANY, 0x0200 + and $v0, $X, $ANY + beq/bne $v0,$zero,N
  beq -> unconditional, bne -> NOP
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

# Pattern D: separate handler (RAM 0x80087C14 / BLAZE 0x0094E4BC), uses $v1 and $a0 (12 bytes)
# This is a DIFFERENT entity handler function (movement/positioning) also called by the
# entity manager each frame. It checks the dead flag independently of chest_update.
# When dead flag set externally by EXE (parent monster freed): decrements entity+0x28,
# then kills entity with sw $zero when entity+0x28 < 8.
# Fix: make beq unconditional so we never enter the fade-out/kill path.
#   lw $v1, 0x0000($s1)      8E230000
#   lui $a0, 0x0200           3C040200
#   and $v0, $v1, $a0         00641024
#   beq $v0, $zero, N         1040XXXX -> unconditional (1000XXXX)
PATTERN_D = bytes([
    0x00, 0x00, 0x23, 0x8E,  # 8E230000
    0x00, 0x02, 0x04, 0x3C,  # 3C040200
    0x24, 0x10, 0x64, 0x00,  # 00641024
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

    # --- Pattern D: separate movement handler (RAM 0x80087C14, BLAZE 0x0094E4BC) ---
    # Uses $v1 and $a0 registers (different from A/B/C).
    # This is a second entity handler for the chest (movement/positioning), called
    # independently by the entity manager. When dead flag is set externally, it
    # decrements entity+0x28 (opacity) and kills with sw $zero when < 8.
    # Fix: make beq unconditional so we skip the fade-out/kill path entirely.
    patched_d = 0
    pos = CODE_START
    while pos < len(data) - 16:
        idx = data.find(PATTERN_D, pos)
        if idx == -1 or idx >= len(data) - 16:
            break

        branch_off = idx + 12
        branch = struct.unpack_from('<I', data, branch_off)[0]
        branch_op = (branch >> 26) & 0x3F
        branch_rt = (branch >> 16) & 0x1F

        if branch_op == 0x04 and branch_rt == 0:  # beq $v0, $zero, N
            branch = branch & ~(0x1F << 21)
            struct.pack_into('<I', data, branch_off, branch)
            patched_d += 1
            print(f"  [D] 0x{branch_off:08X}: beq -> unconditional (movement handler bypass)")
        elif branch_op == 0x05 and branch_rt == 0:  # bne $v0, $zero, N
            struct.pack_into('<I', data, branch_off, 0x00000000)
            patched_d += 1
            print(f"  [D] 0x{branch_off:08X}: bne -> nop (movement handler bypass)")

        pos = idx + 4

    total = patched_a + patched_bc + patched_d
    print(f"  Pattern A (chest_update entry): {patched_a}")
    print(f"  Pattern B/C (STUB/other): {patched_bc}")
    print(f"  Pattern D (movement handler): {patched_d}")
    print(f"  Total entry checks disabled: {total}")

    if total == 0:
        print("  [WARN] No patterns found! Layer 4 had no effect.")
        return False

    return True


def patch_layer5_chest_region(data):
    """Generic broad scan of chest handler region (BLAZE 0x0094DECC to 0x0094F800).

    Catches ALL dead flag (0x02000000) check patterns regardless of register
    combinations. Covers the fade-out handler, opacity handler, and any other
    chest-specific handlers that Layer 4 named patterns miss.

    Generic pattern detected:
      lui $ANY, 0x0200       (op=0x0F, imm=0x0200)
      ... 0-3 instructions ...
      and $v0, $X, $ANY      (op=0, func=0x24, rd=$v0=2, one operand = lui reg)
      ... 0-1 instructions ...
      beq/bne $v0, $zero, N  (op=0x04/0x05, comparing reg 2 vs reg 0)

    Fix:
      beq $v0, $zero, N  -> unconditional (always skip death handler)
      bne $v0, $zero, N  -> NOP (never jump to death handler)
    """
    print("\n  --- LAYER 5: Generic broad scan of chest handler region ---")

    # Covers both STUB (shared) handlers and MAIN (Cavern F1) chest handlers.
    # STUB handlers start at ~0x00940000 and also contain dead flag checks
    # with register combos ($v1/$v1, $v0/$s1, $v1/$s1) not caught by Layer 4.
    CHEST_START = 0x00940000
    CHEST_END   = 0x0094F800
    patched = 0
    skipped_already = 0

    i = CHEST_START
    while i < CHEST_END - 4:
        w = struct.unpack_from('<I', data, i)[0]

        # Look for: lui $ANY, 0x0200
        if (w >> 26) & 0x3F != 0x0F or (w & 0xFFFF) != 0x0200:
            i += 4
            continue

        lui_reg = (w >> 16) & 0x1F  # which register got 0x0200

        # Search for: and $v0, $X, lui_reg  within next 4 instructions
        found_and = False
        and_pos = -1
        for j in range(i + 4, min(i + 20, CHEST_END), 4):
            wj = struct.unpack_from('<I', data, j)[0]
            if (wj >> 26) & 0x3F != 0x00 or (wj & 0x3F) != 0x24:  # not R-type 'and'
                continue
            rd = (wj >> 11) & 0x1F
            rs = (wj >> 21) & 0x1F
            rt = (wj >> 16) & 0x1F
            if rd == 2 and (rs == lui_reg or rt == lui_reg):  # result in $v0, uses lui_reg
                found_and = True
                and_pos = j
                break

        if not found_and:
            i += 4
            continue

        # Search for: beq/bne $v0, $zero, N  within 2 instructions after 'and'
        for k in range(and_pos + 4, min(and_pos + 12, CHEST_END), 4):
            wk = struct.unpack_from('<I', data, k)[0]
            b_op = (wk >> 26) & 0x3F
            b_rs = (wk >> 21) & 0x1F
            b_rt = (wk >> 16) & 0x1F

            if b_op not in (0x04, 0x05):  # not beq or bne
                continue

            is_v0_zero = (b_rs == 2 and b_rt == 0) or (b_rs == 0 and b_rt == 2)
            if not is_v0_zero:
                continue

            if b_op == 0x04:  # beq $v0, $zero, N -> unconditional
                already_uncond = (b_rs == 0 and b_rt == 0)
                if already_uncond:
                    skipped_already += 1
                    break
                new_w = wk & ~(0x1F << 21) & ~(0x1F << 16)  # clear rs and rt
                struct.pack_into('<I', data, k, new_w)
                patched += 1
                print(f"  [L5] 0x{k:08X}: beq $v0,$zero -> unconditional "
                      f"(lui@0x{i:08X} and@0x{and_pos:08X})")
            else:  # bne $v0, $zero, N -> NOP
                if wk == 0x00000000:
                    skipped_already += 1
                    break
                struct.pack_into('<I', data, k, 0x00000000)
                patched += 1
                print(f"  [L5] 0x{k:08X}: bne $v0,$zero -> nop "
                      f"(lui@0x{i:08X} and@0x{and_pos:08X})")
            break

        i += 4

    print(f"  Chest region dead flag checks patched: {patched} "
          f"(already done: {skipped_already})")
    return True


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    work_blaze = project_dir / 'output' / 'BLAZE.ALL'

    print("=" * 60)
    print("Loot Timer Patcher v20 - Chest region broad scan added")
    print("  Layer 1: check_kill function -> return 0")
    print("  Layer 2: All JAL callers -> $v0 = 0")
    print("  Layer 3: Timer kill patterns -> NOP dead flag")
    print("  Layer 4: Entry dead flag check -> NOP/bypass (A/B/C/D)")
    print("  Layer 5: Generic broad scan chest+STUB region 0x00940000-0x0094F800")
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
    ok5 = patch_layer5_chest_region(data)

    if not (ok1 and ok2 and ok3 and ok4 and ok5):
        print("\n  [ERROR] Some patches failed!")
        sys.exit(1)

    work_blaze.write_bytes(data)

    print(f"\n  [OK] All 5 layers applied successfully!")
    print(f"  Effect: Entities immune to external dead flag + timer + check_kill + ALL chest handlers")
    print("=" * 60)

    sys.exit(0)


if __name__ == '__main__':
    main()
