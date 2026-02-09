#!/usr/bin/env python3
"""
Survey ALL occurrences of the chest despawn countdown pattern in BLAZE.ALL.

The state 2 countdown code is:
  96220014  lhu $v0, 0x14($s1)
  00000000  nop
  2442FFFF  addiu $v0, $v0, -1   <- PATCH TARGET (NOP this)
  A6220014  sh $v0, 0x14($s1)
  00021400  sll $v0, $v0, 16     (sign extend for bgez check)
  04410002  bgez $v0, 2          (skip state transition if timer >= 0)
  24020003  addiu $v0, $zero, 3  (state = 3)
  A6220010  sh $v0, 0x10($s1)   (write state)

We use the full 32-byte signature for safety, but also search shorter patterns
to find any variations.
"""

import struct
from pathlib import Path

BLAZE_ALL_PATH = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")

# Full 32-byte signature (8 instructions)
FULL_SIG = [
    0x96220014,  # lhu $v0, 0x14($s1)
    0x00000000,  # nop
    0x2442FFFF,  # addiu $v0, $v0, -1  <- INDEX 2
    0xA6220014,  # sh $v0, 0x14($s1)
    0x00021400,  # sll $v0, $v0, 16
    0x04410002,  # bgez $v0, 2
    0x24020003,  # addiu $v0, $zero, 3
    0xA6220010,  # sh $v0, 0x10($s1)
]

# Shorter 20-byte signature (5 instructions) - the core countdown
SHORT_SIG = [
    0x96220014,  # lhu $v0, 0x14($s1)
    0x00000000,  # nop
    0x2442FFFF,  # addiu $v0, $v0, -1
    0xA6220014,  # sh $v0, 0x14($s1)
    0x00021400,  # sll $v0, $v0, 16
]

# Even shorter: just the lhu/addiu/sh triplet with nop
MINI_SIG = [
    0x96220014,  # lhu $v0, 0x14($s1)
    0x00000000,  # nop
    0x2442FFFF,  # addiu $v0, $v0, -1
    0xA6220014,  # sh $v0, 0x14($s1)
]

# Broader: any lhu+gap+addiu(-1)+sh with offset 0x14 and $s1
# Same as MINI_SIG but allowing any instruction in the nop slot
BROAD_SIG_MASK = [
    (0x96220014, 0xFFFFFFFF),  # lhu $v0, 0x14($s1) exact
    (0x00000000, 0x00000000),  # any instruction (wildcard)
    (0x2442FFFF, 0xFFFFFFFF),  # addiu $v0, $v0, -1 exact
    (0xA6220014, 0xFFFFFFFF),  # sh $v0, 0x14($s1) exact
]


def search_sig(data, sig_words, name):
    """Search for a signature (list of uint32 LE words) in data."""
    sig_bytes = b''.join(struct.pack('<I', w) for w in sig_words)
    positions = []
    pos = 0
    while True:
        pos = data.find(sig_bytes, pos)
        if pos == -1:
            break
        if pos % 4 == 0:  # aligned
            positions.append(pos)
        pos += 4
    return positions


def search_masked(data, sig_mask, name):
    """Search with wildcard mask."""
    positions = []
    for i in range(0, len(data) - len(sig_mask) * 4 + 1, 4):
        match = True
        for j, (expected, mask) in enumerate(sig_mask):
            word = struct.unpack_from('<I', data, i + j * 4)[0]
            if (word & mask) != (expected & mask):
                match = False
                break
        if match:
            positions.append(i)
    return positions


def main():
    blaze = BLAZE_ALL_PATH.read_bytes()
    print(f"BLAZE.ALL: {len(blaze):,} bytes")

    # Search full 32-byte signature
    print(f"\n{'='*70}")
    print(f"  Full 32-byte signature (8 instructions)")
    print(f"{'='*70}")
    full_matches = search_sig(blaze, FULL_SIG, "full")
    print(f"  Found: {len(full_matches)} occurrence(s)")
    for p in full_matches:
        print(f"    BLAZE.ALL 0x{p:08X} (addiu at 0x{p+8:08X})")

    # Search 20-byte signature
    print(f"\n{'='*70}")
    print(f"  Short 20-byte signature (5 instructions)")
    print(f"{'='*70}")
    short_matches = search_sig(blaze, SHORT_SIG, "short")
    print(f"  Found: {len(short_matches)} occurrence(s)")
    for p in short_matches:
        print(f"    BLAZE.ALL 0x{p:08X} (addiu at 0x{p+8:08X})")

    # Search 16-byte mini signature
    print(f"\n{'='*70}")
    print(f"  Mini 16-byte signature (lhu+nop+addiu+sh)")
    print(f"{'='*70}")
    mini_matches = search_sig(blaze, MINI_SIG, "mini")
    print(f"  Found: {len(mini_matches)} occurrence(s)")
    for p in mini_matches:
        print(f"    BLAZE.ALL 0x{p:08X} (addiu at 0x{p+8:08X})")

    # Search broad (wildcard nop slot)
    print(f"\n{'='*70}")
    print(f"  Broad: lhu $v0,0x14($s1) / ANY / addiu $v0,$v0,-1 / sh $v0,0x14($s1)")
    print(f"{'='*70}")
    broad_matches = search_masked(blaze, BROAD_SIG_MASK, "broad")
    print(f"  Found: {len(broad_matches)} occurrence(s)")
    for p in broad_matches:
        w1 = struct.unpack_from('<I', blaze, p + 4)[0]
        print(f"    BLAZE.ALL 0x{p:08X} (middle instr: 0x{w1:08X}, addiu at 0x{p+8:08X})")

    # Search even broader: any register for lhu/addiu/sh with offset 0x14
    print(f"\n{'='*70}")
    print(f"  Any-register: lhu $r,0x14($base) / ... / addiu $r,$r,-1 / sh $r,0x14($base)")
    print(f"{'='*70}")
    count = 0
    for i in range(0, len(blaze) - 16, 4):
        w0 = struct.unpack_from('<I', blaze, i)[0]
        w2 = struct.unpack_from('<I', blaze, i + 8)[0]
        w3 = struct.unpack_from('<I', blaze, i + 12)[0]

        # w0: lhu rt, 0x14(rs)
        if (w0 >> 26) != 0x25 or (w0 & 0xFFFF) != 0x0014:
            continue
        rs = (w0 >> 21) & 0x1F
        rt = (w0 >> 16) & 0x1F

        # w2: addiu rt, rt, -1
        if w2 != (0x24000000 | (rt << 21) | (rt << 16) | 0xFFFF):
            continue

        # w3: sh rt, 0x14(rs)
        if w3 != (0xA4000000 | (rs << 21) | (rt << 16) | 0x0014):
            continue

        regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
        w1 = struct.unpack_from('<I', blaze, i + 4)[0]
        print(f"    0x{i:08X}: lhu {regs[rt]},0x14({regs[rs]}) / 0x{w1:08X} / addiu -1 / sh")
        count += 1

    print(f"  Total: {count}")

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Full 32-byte matches:  {len(full_matches)}")
    print(f"  Short 20-byte matches: {len(short_matches)}")
    print(f"  Mini 16-byte matches:  {len(mini_matches)}")
    print(f"  Broad (wildcard nop):  {len(broad_matches)}")
    print(f"  Any-register:          {count}")

    if len(full_matches) > 0:
        print(f"\n  PATCH LOCATIONS (addiu to NOP):")
        for p in full_matches:
            print(f"    BLAZE.ALL 0x{p+8:08X}: 2442FFFF -> 00000000")


if __name__ == '__main__':
    main()
