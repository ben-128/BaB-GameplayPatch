#!/usr/bin/env python3
"""
Patch chest despawn timer decrements in BLAZE.ALL overlay code (v8).

v7 scanned only FORWARD for opacity fields, missing "Function B" handlers
where opacity code (+0x28/+0x2A) comes BEFORE the timer decrement.
v7 found 12 patterns but missed ~25 more, so chests still despawned.

v8 scans BOTH directions (forward and backward) within the same function:
  1. addiu $rt, $rt, -1         -- SELF-decrement (rt == rs, rs != $zero)
  2. sh $rt, 0x14(<base>)       -- store timer (within 1-3 instr after)
  3. Access to +0x28 OR +0x2A   -- opacity fields UNIQUE to chest entities
     (scanned 80 instr forward AND backward, same base register)
  4. Exclude fade-in patterns   -- state=2 write to +0x10 means fade-in

Runs at build step 7 (patches output/BLAZE.ALL before BIN injection).
"""

import struct
import sys
import json
from pathlib import Path

REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
        '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
        '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
        '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

NOP_WORD = 0x00000000
EXPECTED_MIN = 20
EXPECTED_MAX = 60


def has_opacity_access(data, sh_pos, base_reg, scan_range=80):
    """
    Check if code near sh 0x14 accesses opacity fields +0x28 or +0x2A
    on the same base register. Scans BOTH forward and backward within
    the same function. These fields are unique to chest entities.
    Returns (has_opacity, is_fadein).
    """
    has_028 = False
    has_02A = False
    is_fadein = False  # True if writes state=2 to +0x10 (fade-in, not despawn)

    def _check_word(pos):
        nonlocal has_028, has_02A, is_fadein
        w = struct.unpack_from('<I', data, pos)[0]
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        imm = w & 0xFFFF

        if rs != base_reg:
            return
        # lhu/lh/sh with offset +0x28 or +0x2A
        if imm == 0x0028 and op in (0x25, 0x21, 0x29):
            has_028 = True
        if imm == 0x002A and op in (0x25, 0x21, 0x29):
            has_02A = True
        # Check for fade-in: sh <reg>, 0x10(<base>) with value 2
        if imm == 0x0010 and op == 0x29:
            if pos >= 4:
                pw = struct.unpack_from('<I', data, pos - 4)[0]
                pop = (pw >> 26) & 0x3F
                prs = (pw >> 21) & 0x1F
                pimm = pw & 0xFFFF
                if pop == 0x09 and prs == 0 and pimm == 2:
                    is_fadein = True

    # Scan FORWARD from sh 0x14
    for k in range(1, scan_range):
        pos = sh_pos + k * 4
        if pos + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, pos)[0]
        # Stop at jr $ra (function return)
        if w & 0xFC1FFFFF == 0x00000008 and ((w >> 21) & 0x1F) == 31:
            break
        _check_word(pos)

    # Scan BACKWARD from sh 0x14
    for k in range(1, scan_range):
        pos = sh_pos - k * 4
        if pos < 0:
            break
        w = struct.unpack_from('<I', data, pos)[0]
        # Stop at function prologue: addiu $sp, $sp, -XX (negative imm)
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        if op == 0x09 and rs == 29 and rt == 29 and imm >= 0x8000:
            break
        _check_word(pos)

    return (has_028 or has_02A), is_fadein


def find_chest_patterns(data):
    """
    Find chest timer decrement patterns with entity type validation.

    Step 1: Find self-decrement addiu $rt, $rt, -1 (not from $zero)
    Step 2: Find sh $rt, 0x14(<base>) within 1-3 instructions after
    Step 3: Verify +0x28 or +0x2A access on same base (chest opacity)
    Step 4: Exclude fade-in patterns (state=2 write to +0x10)
    """
    matches = []

    overlay_start = 0x00900000
    overlay_end = 0x02D00000
    search_end = min(len(data) - 16, overlay_end)

    for i in range(overlay_start, search_end, 4):
        w = struct.unpack_from('<I', data, i)[0]
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF

        if op != 0x09 or imm != 0xFFFF:
            continue

        rt = (w >> 16) & 0x1F
        rs = (w >> 21) & 0x1F

        # Must be self-decrement (rt == rs) and not from $zero
        if rt != rs or rs == 0:
            continue

        # Look for sh <rt>, 0x14(<base>) in next 1-3 instructions
        for j in range(1, 4):
            pos = i + j * 4
            if pos + 4 > len(data):
                break
            w2 = struct.unpack_from('<I', data, pos)[0]
            op2 = (w2 >> 26) & 0x3F
            rt2 = (w2 >> 16) & 0x1F
            rs2 = (w2 >> 21) & 0x1F
            imm2 = w2 & 0xFFFF

            if op2 == 0x29 and rt2 == rt and imm2 == 0x0014:
                base_reg = rs2

                # Check for chest-specific opacity fields
                has_opacity, is_fadein = has_opacity_access(data, pos, base_reg)

                if has_opacity and not is_fadein:
                    matches.append({
                        'addiu_pos': i,
                        'sh_pos': pos,
                        'val_reg': rt,
                        'base_reg': base_reg,
                    })
                break

    return matches


def apply_patches(data, matches, config):
    """NOP all chest timer decrements (infinite timer)."""
    timer_seconds = config.get('chest_despawn_seconds', 0)

    if timer_seconds != 0:
        print(f"[ERROR] Configurable timer ({timer_seconds}s) not yet implemented")
        print("        Use chest_despawn_seconds=0 for infinite timer")
        sys.exit(1)

    patched = 0
    skipped = 0

    for m in matches:
        pos = m['addiu_pos']
        old_word = struct.unpack_from('<I', data, pos)[0]

        if old_word == NOP_WORD:
            skipped += 1
            continue

        if (old_word >> 26) != 0x09 or (old_word & 0xFFFF) != 0xFFFF:
            print(f"  [WARNING] 0x{pos:08X}: expected addiu -1, got 0x{old_word:08X}")
            skipped += 1
            continue

        data[pos:pos+4] = struct.pack('<I', NOP_WORD)

        rs = (old_word >> 21) & 0x1F
        rt = (old_word >> 16) & 0x1F
        base = REGS[m['base_reg']]
        print(f"  PATCH 0x{pos:08X}: addiu {REGS[rt]},{REGS[rs]},-1 -> nop  (base={base})")
        patched += 1

    return patched, skipped


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'output' / 'BLAZE.ALL'
    config_path = script_dir / 'loot_timer.json'

    print("Loot Timer v8: bidirectional opacity scan")
    print(f"  Target: {blaze_path}")

    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())
        timer_s = config.get('chest_despawn_seconds', 0)
        print(f"  Config: {timer_s}s timer ({'infinite' if timer_s == 0 else 'timed'})")
    else:
        print(f"  Config: not found, using defaults (infinite timer)")

    data = bytearray(blaze_path.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    matches = find_chest_patterns(data)
    print(f"\n  Found {len(matches)} chest timer patterns "
          f"(self-decrement + sh 0x14 + opacity access)")

    if len(matches) == 0:
        print("[ERROR] No chest timer patterns found!")
        sys.exit(1)

    if len(matches) < EXPECTED_MIN:
        print(f"[WARNING] Only {len(matches)} matches (expected >= {EXPECTED_MIN})")

    if len(matches) > EXPECTED_MAX:
        print(f"[ERROR] Too many matches ({len(matches)} > {EXPECTED_MAX}) - aborting")
        sys.exit(1)

    already_nopped = sum(1 for m in matches
                         if struct.unpack_from('<I', data, m['addiu_pos'])[0] == NOP_WORD)
    unpatched = len(matches) - already_nopped

    print(f"  Status: {unpatched} unpatched, {already_nopped} already NOPed")
    print()

    patched, skipped = apply_patches(data, matches, config)

    if patched > 0:
        blaze_path.write_bytes(data)
        print()

    print(f"{'='*60}")
    print(f"  {patched} new + {already_nopped} existing = "
          f"{patched + already_nopped} total patches")
    print(f"  Chest despawn timer frozen (spells unaffected)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
