#!/usr/bin/env python3
"""
Search for alternative damage functions in EXE.

Look for the magic constant 0x51EB851F used in fast /100 division.
This might reveal other damage calculation functions.
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BIN_FILE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"

# SLES_008.45 location in BIN
SLES_LBA = 295081
SECTOR_SIZE = 2352
HEADER_SIZE = 24
SLES_BIN_OFFSET = SLES_LBA * SECTOR_SIZE + HEADER_SIZE

# Known damage function
KNOWN_DAMAGE_FUNC = 0x80024F90

# Magic constant for /100 fast division
MAGIC_DIV100 = 0x51EB851F

print("=" * 70)
print("Searching for Alternative Damage Functions")
print("=" * 70)
print()
print(f"Known damage function: 0x{KNOWN_DAMAGE_FUNC:08X}")
print(f"Magic /100 constant:   0x{MAGIC_DIV100:08X}")
print()

with open(BIN_FILE, 'rb') as f:
    f.seek(SLES_BIN_OFFSET)
    exe_data = f.read(824 * 1024)  # SLES is 824KB

print(f"EXE size: {len(exe_data)} bytes")
print()

# Find all occurrences of the magic constant
print("Searching for /100 division pattern...")
print()

matches = []
for offset in range(0, len(exe_data) - 4, 4):
    word = struct.unpack_from('<I', exe_data, offset)[0]
    if word == MAGIC_DIV100:
        ram_addr = 0x80010000 + offset - 0x800
        matches.append((offset, ram_addr))

print(f"Found {len(matches)} occurrences of 0x{MAGIC_DIV100:08X}:")
print()

# Analyze context around each match
for i, (offset, ram) in enumerate(matches, 1):
    print(f"=== Match {i}: RAM 0x{ram:08X}, File offset 0x{offset:08X} ===")

    # Read context (32 instructions before and after)
    context_start = max(0, offset - 32 * 4)
    context_end = min(len(exe_data), offset + 32 * 4)
    context = exe_data[context_start:context_end]

    # Look for function prologue/epilogue markers
    has_stack_frame = False
    has_jr_ra = False
    has_mult = False
    has_mflo_mfhi = False

    for j in range(0, len(context) - 4, 4):
        word = struct.unpack_from('<I', context, j)[0]

        # Stack frame: addiu $sp, $sp, -N
        if (word >> 16) == 0x27BD and (word & 0xFFFF) > 0x8000:
            has_stack_frame = True

        # Function return: jr $ra
        if word == 0x03E00008:
            has_jr_ra = True

        # Multiplication (for percent calculation)
        if (word >> 26) == 0 and (word & 0x3F) == 0x18:  # mult
            has_mult = True

        # Get result: mflo/mfhi
        if (word >> 26) == 0 and ((word & 0x3F) == 0x10 or (word & 0x3F) == 0x12):
            has_mflo_mfhi = True

    print(f"  Context analysis:")
    print(f"    - Has stack frame: {has_stack_frame}")
    print(f"    - Has jr $ra:      {has_jr_ra}")
    print(f"    - Has mult:        {has_mult}")
    print(f"    - Has mflo/mfhi:   {has_mflo_mfhi}")

    # Disassemble around the magic constant
    print(f"  Code snippet (±8 instructions):")
    snippet_start = max(0, offset - 8 * 4)
    for k in range(-8, 9):
        instr_offset = offset + k * 4
        if instr_offset < 0 or instr_offset + 4 > len(exe_data):
            continue

        word = struct.unpack_from('<I', exe_data, instr_offset)[0]
        instr_ram = 0x80010000 + instr_offset - 0x800
        marker = " <-- MAGIC" if k == 0 else ""

        # Basic disassembly
        op = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        rd = (word >> 11) & 0x1F
        imm = word & 0xFFFF

        if op == 0x0F:  # lui
            print(f"    0x{instr_ram:08X}: {word:08X}  lui ${rt}, 0x{imm:04X}{marker}")
        elif op == 0x0D:  # ori
            print(f"    0x{instr_ram:08X}: {word:08X}  ori ${rt}, ${rs}, 0x{imm:04X}{marker}")
        elif op == 0x00 and (word & 0x3F) == 0x18:  # mult
            print(f"    0x{instr_ram:08X}: {word:08X}  mult ${rs}, ${rt}")
        elif op == 0x00 and (word & 0x3F) == 0x10:  # mflo
            print(f"    0x{instr_ram:08X}: {word:08X}  mflo ${rd}")
        elif op == 0x00 and (word & 0x3F) == 0x12:  # mfhi
            print(f"    0x{instr_ram:08X}: {word:08X}  mfhi ${rd}")
        elif op == 0x00 and (word & 0x3F) == 0x03:  # sra
            sa = (word >> 6) & 0x1F
            print(f"    0x{instr_ram:08X}: {word:08X}  sra ${rd}, ${rt}, {sa}")
        else:
            print(f"    0x{instr_ram:08X}: {word:08X}")

    print()

print("=" * 70)
print("Analysis complete")
print("=" * 70)
print()
print("Next steps:")
print("  1. Review each function found above")
print("  2. Look for functions that:")
print("     - Take damage% as parameter")
print("     - Multiply by maxHP")
print("     - Divide by 100")
print("  3. Set breakpoint and test which one is called by falling rocks")
print()
