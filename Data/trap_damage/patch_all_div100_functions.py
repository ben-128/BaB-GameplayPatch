#!/usr/bin/env python3
"""
Patch ALL 14 functions that use /100 division (0x51EB851F magic constant).

Strategy: Inject "if (param == 10) param = 50" at the START of each function
that performs /100 division. One of these is the real falling rocks damage function.
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BIN_FILE = PROJECT_ROOT / "output" / "Blaze & Blade - Patched.bin"

# SLES_008.45 location in BIN
SLES_LBA = 295081
SECTOR_SIZE = 2352
HEADER_SIZE = 24
SLES_BIN_OFFSET = SLES_LBA * SECTOR_SIZE + HEADER_SIZE

# All 14 functions that use lui/ori to construct 0x51EB851F
TARGETS = [
    (0x80026A50, "$10"),  # Register $10 (t2)
    (0x80026EE8, "$9"),   # Register $9 (t1)
    (0x80026F58, "$2"),   # Register $2 (v0)
    (0x80027B70, "$3"),   # Register $3 (v1)
    (0x80027BF4, "$3"),
    (0x80027C78, "$3"),
    (0x80027CFC, "$3"),
    (0x80027D80, "$3"),
    (0x80027E04, "$3"),
    (0x80027EA8, "$3"),
    (0x800281D4, "$2"),
    (0x80028D64, "$3"),
    (0x8002A344, "$2"),
    (0x8002A3D0, "$2"),
]

print("=" * 70)
print("Patching ALL /100 Division Functions (14 sites)")
print("=" * 70)
print()

if not BIN_FILE.exists():
    print(f"ERROR: BIN file not found: {BIN_FILE}")
    exit(1)

with open(BIN_FILE, 'rb') as f:
    data = bytearray(f.read())

patched_count = 0

for ram_addr, reg_name in TARGETS:
    # Calculate file offset
    file_offset = (ram_addr - 0x80010000) + 0x800
    bin_offset = SLES_BIN_OFFSET + file_offset

    print(f"Target {patched_count + 1}/14: RAM 0x{ram_addr:08X}, BIN 0x{bin_offset:08X}, reg {reg_name}")

    # Read original lui instruction
    orig_word = struct.unpack_from('<I', data, bin_offset)[0]
    op = (orig_word >> 26) & 0x3F
    rt = (orig_word >> 16) & 0x1F
    imm = orig_word & 0xFFFF

    if op != 0x0F or imm != 0x51EB:
        print(f"  WARNING: Expected 'lui' with 0x51EB, got 0x{orig_word:08X}")
        print(f"  Skipping this site.")
        print()
        continue

    # Check if this is at the start of a function (look back for prologue)
    # Function prologue: addiu $sp, $sp, -N (within 64 bytes before)
    is_function_start = False
    for back_offset in range(4, 65, 4):
        check_offset = bin_offset - back_offset
        if check_offset < SLES_BIN_OFFSET:
            break
        word = struct.unpack_from('<I', data, check_offset)[0]
        # addiu $sp, $sp, -N (op=0x09, rs=29, rt=29, imm>0x8000)
        if (word >> 16) == 0x27BD and (word & 0xFFFF) > 0x8000:
            is_function_start = True
            break

    if not is_function_start:
        print(f"  INFO: lui/ori in middle of function (will patch result after division)")
    else:
        print(f"  INFO: lui/ori at function start")

    # Strategy:
    # Instead, patch the division result AFTER the /100 happens.
    #
    # Pattern after lui/ori:
    #   mult $reg_with_value, $reg_with_magic
    #   mfhi $result
    #   sra  $result, $result, 5
    #
    # We inject AFTER the sra: if ($result == 10) $result = 50

    # Find the sra instruction (should be within 16 bytes after lui/ori)
    sra_offset = None
    for forward_offset in range(8, 20, 4):
        check_offset = bin_offset + forward_offset
        if check_offset + 4 > len(data):
            break
        word = struct.unpack_from('<I', data, check_offset)[0]
        # sra: op=0x00, func=0x03, sa=5
        if (word >> 26) == 0 and (word & 0x3F) == 0x03 and ((word >> 6) & 0x1F) == 5:
            sra_offset = check_offset
            break

    if sra_offset is None:
        print(f"  WARNING: Could not find 'sra $reg, 5' after /100 division")
        print()
        continue

    sra_word = struct.unpack_from('<I', data, sra_offset)[0]
    result_reg = (sra_word >> 11) & 0x1F  # rd field

    print(f"  Found: sra ${result_reg}, ..., 5 at BIN 0x{sra_offset:08X}")
    print(f"  Injecting: if (${result_reg} == 10) ${result_reg} = 50 after sra")

    # Patch code (inject 4 instructions after sra):
    #   addiu $v0, $zero, 10       ; $v0 = 10
    #   bne   $result, $v0, skip   ; if $result != 10, skip
    #   nop                        ; delay slot
    #   addiu $result, $zero, 50   ; $result = 50
    # skip:
    #   (continue original code)

    patch_offset = sra_offset + 4  # Right after sra

    # Save original 4 instructions that will be replaced
    orig_instructions = []
    for i in range(4):
        word = struct.unpack_from('<I', data, patch_offset + i * 4)[0]
        orig_instructions.append(word)

    # Build patch
    patch_code = [
        0x3402000A,  # addiu $v0, $zero, 10
        0x14000000 | ((result_reg << 21) | (2 << 16) | 2),  # bne $result, $v0, +2
        0x00000000,  # nop
        0x34000032 | (result_reg << 16),  # addiu $result, $zero, 50
    ]

    # Apply patch
    for i, word in enumerate(patch_code):
        struct.pack_into('<I', data, patch_offset + i * 4, word)

    patched_count += 1
    print(f"  [OK] Patched function {patched_count}/14")
    print()

# Write patched BIN
if patched_count > 0:
    with open(BIN_FILE, 'wb') as f:
        f.write(data)

    print("=" * 70)
    print(f"SUCCESS: Patched {patched_count} /100 division functions")
    print("=" * 70)
    print()
    print(f"Patched BIN: {BIN_FILE}")
    print()
    print("Test in-game:")
    print("  1. Mount output BIN in ePSXe")
    print("  2. Go to Cavern of Death")
    print("  3. Get hit by falling rock")
    print("  4. Check damage amount")
    print()
    print("If damage is NOW 50%, we found the right function!")
else:
    print("=" * 70)
    print("ERROR: No functions could be patched")
    print("=" * 70)
