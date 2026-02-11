# -*- coding: cp1252 -*-
"""
Inspect the code at offset 0x0092BF78 to understand the pattern.
"""

import struct
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

REG_NAMES = [
    "$zero","$at","$v0","$v1","$a0","$a1","$a2","$a3",
    "$t0","$t1","$t2","$t3","$t4","$t5","$t6","$t7",
    "$s0","$s1","$s2","$s3","$s4","$s5","$s6","$s7",
    "$t8","$t9","$k0","$k1","$gp","$sp","$fp","$ra"
]

def disasm_one(word):
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    imm = word & 0xFFFF
    imms = imm - 0x10000 if imm & 0x8000 else imm

    if word == 0:
        return "nop"
    if op == 0x0F:
        return f"lui {REG_NAMES[rt]}, 0x{imm:04X}"
    if op == 0x0D:
        return f"ori {REG_NAMES[rt]}, {REG_NAMES[rs]}, 0x{imm:04X}"
    if op == 0x28:
        return f"sb {REG_NAMES[rt]}, {imms}({REG_NAMES[rs]})"
    if op == 0x23:
        return f"lw {REG_NAMES[rt]}, {imms}({REG_NAMES[rs]})"
    if op == 0x24:
        return f"lbu {REG_NAMES[rt]}, {imms}({REG_NAMES[rs]})"
    if op == 0x2B:
        return f"sw {REG_NAMES[rt]}, {imms}({REG_NAMES[rs]})"
    if op == 0x29:
        return f"sh {REG_NAMES[rt]}, {imms}({REG_NAMES[rs]})"
    if op == 0x09:
        return f"addiu {REG_NAMES[rt]}, {REG_NAMES[rs]}, {imms}"
    return f"0x{word:08X}"

with open(BLAZE_ALL, 'rb') as f:
    data = f.read()

# Inspect 0x0092BF78 and surrounding area
target = 0x0092BF78
ram = target + 0x7F739758

print("=" * 80)
print(f"INSPECTING BLAZE 0x{target:08X} (RAM 0x{ram:08X})")
print("=" * 80)
print()

print("CONTEXT (20 instructions before, 20 after):")
print("-" * 80)
for i in range(-20, 20):
    off = target + (i * 4)
    if 0 <= off < len(data) - 4:
        word = struct.unpack_from('<I', data, off)[0]
        marker = " <-- TARGET" if i == 0 else ""
        print(f"  {off:08X} (RAM {off + 0x7F739758:08X}): {word:08X}  {disasm_one(word)}{marker}")
