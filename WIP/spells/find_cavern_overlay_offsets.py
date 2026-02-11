# -*- coding: cp1252 -*-
"""
Find the CORRECT overlay offsets for Cavern of Death spell bitfield init.

PROBLEM: The offsets identified (0x0098A69C, 0x0092BF74) are never executed
for Cavern F1. Freeze tests proved the code exists but is for a different dungeon.

APPROACH:
1. Search for ALL patterns that write entity+0x160 in BLAZE.ALL
2. For each pattern, compute which RAM range it would map to
3. Cross-reference with Cavern overlay range (0x80060000-0x800A0000)
4. Find patterns that fall WITHIN this range = candidates

PATTERN SIGNATURES:
A) Spawn init (14-instr verbose):
   ori $v1, $zero, 1      (0x34030001)
   sb $v1, 0x160($v0)     (0xA0430160)
   [lui/lw/nop pattern repeats for bytes 1-3]

B) Combat init (compact):
   ori $vX, $zero, 1      (0x340X0001 where X=2 or 3)
   sb $vX, 0x160($sY)     (0xA0XX0160 where Y=any)

C) Entity init (zeroing):
   sb $zero, 0x160($sX)   (0xA0X00160)
   sb $zero, 0x161($sX)   (0xA0X00161)
   sb $zero, 0x162($sX)   (0xA0X00162)
   sb $zero, 0x163($sX)   (0xA0X00163)
"""

import struct
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# Cavern overlay range (verified by savestate analysis)
CAVERN_RAM_START = 0x80060000
CAVERN_RAM_END = 0x800A0000
BLAZE_TO_RAM = 0x7F739758  # Delta: RAM = BLAZE + this

def blaze_to_ram(blaze_off):
    return blaze_off + BLAZE_TO_RAM

def is_in_cavern_overlay(blaze_off):
    ram = blaze_to_ram(blaze_off)
    return CAVERN_RAM_START <= ram < CAVERN_RAM_END

def find_pattern_a_spawn_init(data):
    """Find 14-instr verbose spawn init pattern."""
    candidates = []
    target = struct.pack('<I', 0x34030001)  # ori $v1, $zero, 1
    idx = 0
    while True:
        idx = data.find(target, idx)
        if idx == -1:
            break
        # Check if next word is sb $v1, 0x160($v0)
        if idx + 4 < len(data):
            next_word = struct.unpack_from('<I', data, idx + 4)[0]
            # sb opcode = 0x28, base=$v0 (2), rt=$v1 (3), offset=0x0160
            # Format: 0x28 | (2 << 21) | (3 << 16) | 0x0160
            if next_word == 0xA0430160:
                candidates.append(('spawn_init', idx))
        idx += 4
    return candidates

def find_pattern_b_combat_init(data):
    """Find compact combat init pattern (ori + sb)."""
    candidates = []
    # Search for sb xxx, 0x160($sY)
    # sb opcode = 0x28, offset = 0x0160
    for i in range(0, len(data) - 8, 4):
        word = struct.unpack_from('<I', data, i)[0]
        if (word & 0xFC00FFFF) == 0xA0000160:  # sb with offset 0x160
            # Check 1-4 words before for ori $vX, $zero, 1
            for j in range(max(0, i - 16), i, 4):
                prev = struct.unpack_from('<I', data, j)[0]
                # ori $vX, $zero, 1: 0x340X0001 where X=2 or 3
                if prev == 0x34020001 or prev == 0x34030001:
                    candidates.append(('combat_init', i))
                    break
    return candidates

def find_pattern_c_entity_init(data):
    """Find entity init zeroing pattern (4 consecutive sb $zero)."""
    candidates = []
    target = [
        0xA0000160,  # sb $zero, 0x160($sX) - mask off base reg
        0xA0000161,
        0xA0000162,
        0xA0000163
    ]
    for i in range(0, len(data) - 16, 4):
        words = [struct.unpack_from('<I', data, i + j)[0] for j in range(0, 16, 4)]
        match = True
        for k in range(4):
            # Check opcode and offset, ignore base register
            if (words[k] & 0xFC00FFFF) != target[k]:
                match = False
                break
        if match:
            candidates.append(('entity_init', i))
    return candidates

def main():
    print("Loading BLAZE.ALL...")
    with open(BLAZE_ALL, 'rb') as f:
        data = f.read()
    print(f"Size: {len(data):,} bytes ({len(data) / (1024*1024):.1f} MB)")
    print()

    print("=" * 80)
    print("SEARCHING FOR SPELL BITFIELD INIT PATTERNS")
    print("=" * 80)
    print()

    # Find all patterns
    all_candidates = []
    all_candidates.extend(find_pattern_a_spawn_init(data))
    all_candidates.extend(find_pattern_b_combat_init(data))
    all_candidates.extend(find_pattern_c_entity_init(data))

    print(f"Total patterns found: {len(all_candidates)}")
    print()

    # Filter by Cavern overlay range
    cavern_candidates = []
    for ptype, offset in all_candidates:
        if is_in_cavern_overlay(offset):
            cavern_candidates.append((ptype, offset))

    print(f"Patterns in Cavern overlay range (0x{CAVERN_RAM_START:08X}-0x{CAVERN_RAM_END:08X}):")
    print(f"  {len(cavern_candidates)} candidates")
    print()

    if cavern_candidates:
        print("CAVERN OVERLAY CANDIDATES:")
        print("-" * 80)
        for ptype, offset in cavern_candidates:
            ram = blaze_to_ram(offset)
            print(f"  [{ptype:12s}] BLAZE 0x{offset:08X} -> RAM 0x{ram:08X}")
        print()
        print("ACTION: Test these offsets with freeze patch (beq $zero,$zero,-1)")
    else:
        print("WARNING: NO patterns found in Cavern overlay range!")
        print("This suggests:")
        print("  1. The init code uses a different pattern")
        print("  2. The BLAZE-to-RAM delta is zone-specific (not constant)")
        print("  3. entity+0x160 is initialized by EXE code, not overlay")
        print()
        print("NEXT STEP: Disassemble entire Cavern overlay region and search manually")

    # Show distribution of all patterns
    print()
    print("=" * 80)
    print("PATTERN DISTRIBUTION (all BLAZE.ALL)")
    print("=" * 80)
    ranges = [
        (0x00900000, 0x00920000, "0x0090xxxx"),
        (0x00920000, 0x00940000, "0x0092xxxx"),
        (0x00940000, 0x00960000, "0x0094xxxx"),
        (0x00960000, 0x00980000, "0x0096xxxx"),
        (0x00980000, 0x009A0000, "0x0098xxxx"),
    ]
    for start, end, label in ranges:
        count = sum(1 for _, off in all_candidates if start <= off < end)
        if count > 0:
            print(f"  {label}: {count:3d} patterns")

if __name__ == '__main__':
    main()
