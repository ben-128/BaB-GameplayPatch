#!/usr/bin/env python3
"""
Patch chest despawn timer decrements in BLAZE.ALL overlay code (v6).

v5 was too broad: it matched ANY addiu -1 followed by sh 0x14, catching
monster animation timers (e.g. Goblin Shaman spell animation freeze).

v6 requires the FULL chest timer pattern with context validation:
  1. lhu <any>, 0x14(<base>)      -- load timer (within 4 instr before)
  2. addiu <any>, <any>, -1       -- decrement
  3. sh <any>, 0x14(<base>)       -- store timer (within 2 instr after addiu)
  4. sll <any>, <any>, 16         -- sign-extend for underflow check (within 4 after sh)

This eliminates:
  - Initialization patterns (addiu $reg, $zero, -1 with no preceding lhu)
  - Monster animation/spell timers (no sll 16 sign-extension after)

Total: ~35 patterns (Europe), down from ~103 in v5.

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
EXPECTED_MIN = 25
EXPECTED_MAX = 60


def has_lhu_before(data, addiu_pos):
    """Check for lhu <any>, 0x14(<any>) within 4 instructions before addiu."""
    for k in range(1, 5):
        pos = addiu_pos - k * 4
        if pos < 0:
            break
        w = struct.unpack_from('<I', data, pos)[0]
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x25 and imm == 0x0014:  # lhu with offset 0x14
            return True
    return False


def has_sll16_after(data, sh_pos):
    """Check for sll <any>, <any>, 16 within 4 instructions after sh."""
    for k in range(1, 5):
        pos = sh_pos + k * 4
        if pos + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, pos)[0]
        op = (w >> 26) & 0x3F
        funct = w & 0x3F
        shamt = (w >> 6) & 0x1F
        if op == 0x00 and funct == 0x00 and shamt == 16 and w != 0:  # sll by 16
            return True
    return False


def find_all_decrement_patterns(data):
    """
    Find chest timer decrement patterns with context validation:
      lhu <any>, 0x14(<base>)       -- within 4 instructions before
      addiu rt, rs, -1              -- the decrement
      sh rt2, 0x14(base)            -- within 1-2 instructions after
      sll <any>, <any>, 16          -- within 4 instructions after sh

    Only searches in dungeon overlay regions (0x009xxxxx - 0x02Cxxxxx).
    """
    matches = []

    # Search only in overlay code regions (empirically determined)
    overlay_start = 0x00900000
    overlay_end = 0x02D00000
    search_start = max(0, overlay_start)
    search_end = min(len(data) - 12, overlay_end)

    for i in range(search_start, search_end, 4):
        w_addiu = struct.unpack_from('<I', data, i)[0]

        # Check for: addiu rt, rs, -1
        opcode = (w_addiu >> 26) & 0x3F
        imm = w_addiu & 0xFFFF

        if opcode == 0x09 and imm == 0xFFFF:  # addiu with -1
            rt = (w_addiu >> 16) & 0x1F  # destination register
            rs = (w_addiu >> 21) & 0x1F  # source register

            # Look for sh to 0x14 in next 1-2 instructions
            for j in range(1, 3):
                w_sh = struct.unpack_from('<I', data, i + j*4)[0]
                op_sh = (w_sh >> 26) & 0x3F
                imm_sh = w_sh & 0xFFFF

                if op_sh == 0x29 and imm_sh == 0x14:  # sh to offset 0x14
                    rt_sh = (w_sh >> 16) & 0x1F
                    rs_sh = (w_sh >> 21) & 0x1F  # base register

                    sh_pos = i + j * 4

                    # Context validation: require lhu 0x14 before AND sll 16 after
                    if has_lhu_before(data, i) and has_sll16_after(data, sh_pos):
                        matches.append({
                            'addiu_pos': i,
                            'sh_pos': sh_pos,
                            'gap': j * 4,
                            'addiu_dst': rt,
                            'addiu_src': rs,
                            'sh_src': rt_sh,
                            'sh_base': rs_sh
                        })
                    break

    return matches


def apply_patches(data, matches, config):
    """
    Patch strategy depends on config:
    - If timer disabled (0): NOP the addiu instruction
    - If timer configured (>0): modify the initial value (not implemented yet)
    """
    timer_seconds = config.get('chest_despawn_seconds', 0)

    if timer_seconds == 0:
        # NOP all decrements (infinite timer)
        patched = 0
        skipped = 0

        for m in matches:
            pos = m['addiu_pos']
            old_word = struct.unpack_from('<I', data, pos)[0]

            if old_word == NOP_WORD:
                skipped += 1
                continue

            # Verify it's still an addiu -1
            if (old_word >> 26) != 0x09 or (old_word & 0xFFFF) != 0xFFFF:
                print(f"  [WARNING] 0x{pos:08X}: expected addiu -1, got 0x{old_word:08X}")
                skipped += 1
                continue

            # NOP it
            data[pos:pos+4] = struct.pack('<I', NOP_WORD)

            rs = (old_word >> 21) & 0x1F
            rt = (old_word >> 16) & 0x1F
            print(f"  PATCH 0x{pos:08X}: addiu {REGS[rt]},{REGS[rs]},-1 -> nop")
            patched += 1

        return patched, skipped

    else:
        # TODO: Implement initial value patching for configurable timer
        print(f"[ERROR] Configurable timer ({timer_seconds}s) not yet implemented")
        print("        Use chest_despawn_seconds=0 for infinite timer")
        sys.exit(1)


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'output' / 'BLAZE.ALL'
    config_path = script_dir / 'loot_timer.json'

    print("Loot Timer v6: patch chest despawn decrements with context validation")
    print(f"  Target: {blaze_path}")

    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    # Load config
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())
        timer_s = config.get('chest_despawn_seconds', 0)
        print(f"  Config: {timer_s}s timer ({'infinite' if timer_s == 0 else 'timed'})")
    else:
        print(f"  Config: not found, using defaults (infinite timer)")

    data = bytearray(blaze_path.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    # Find all decrement patterns
    matches = find_all_decrement_patterns(data)
    print(f"\n  Found {len(matches)} chest timer patterns (lhu 0x14 + addiu -1 + sh 0x14 + sll 16)")

    if len(matches) == 0:
        print("[ERROR] No patterns found in BLAZE.ALL!")
        sys.exit(1)

    if len(matches) < EXPECTED_MIN:
        print(f"[WARNING] Only {len(matches)} matches (expected >= {EXPECTED_MIN})")

    if len(matches) > EXPECTED_MAX:
        print(f"[ERROR] Too many matches ({len(matches)} > {EXPECTED_MAX}) - aborting")
        sys.exit(1)

    # Check how many are already NOPed
    already_nopped = sum(1 for m in matches
                         if struct.unpack_from('<I', data, m['addiu_pos'])[0] == NOP_WORD)
    unpatched = len(matches) - already_nopped

    print(f"  Status: {unpatched} unpatched, {already_nopped} already NOPed")
    print()

    # Apply patches
    patched, skipped = apply_patches(data, matches, config)

    if patched > 0:
        blaze_path.write_bytes(data)
        print()

    print(f"{'='*60}")
    print(f"  {patched} new + {already_nopped} existing = "
          f"{patched + already_nopped} total patches")
    print(f"  Chest despawn timer frozen in all dungeon areas")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
