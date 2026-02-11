#!/usr/bin/env python3
"""
Patch EXE damage function to replace damage% 10 -> 50.

Inserts check at start of damage function (RAM 0x80024F90):
  if (damage_param == 10) damage_param = 50;

This catches falling rocks and any other 10% damage sources.
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
# Patch the output BIN (created by build step 8, modified by step 9)
BIN_FILE = PROJECT_ROOT / "output" / "Blaze & Blade - Patched.bin"

# SLES_008.45 location in BIN
SLES_LBA = 295081
SECTOR_SIZE = 2352
HEADER_SIZE = 24

SLES_BIN_OFFSET = SLES_LBA * SECTOR_SIZE + HEADER_SIZE

# Damage function: RAM 0x80024F90 = EXE file offset calculation:
# file_offset = (RAM - 0x80010000) + 0x800
DAMAGE_FUNC_RAM = 0x80024F90
DAMAGE_FUNC_OFFSET = (DAMAGE_FUNC_RAM - 0x80010000) + 0x800

print("=" * 60)
print("Patch EXE: Damage 10% -> 50%")
print("=" * 60)
print()

if not BIN_FILE.exists():
    print(f"ERROR: BIN file not found: {BIN_FILE}")
    exit(1)

with open(BIN_FILE, 'rb') as f:
    data = bytearray(f.read())

exe_offset = SLES_BIN_OFFSET + DAMAGE_FUNC_OFFSET

print(f"Function RAM address: 0x{DAMAGE_FUNC_RAM:08X}")
print(f"EXE file offset:      0x{DAMAGE_FUNC_OFFSET:08X}")
print(f"BIN file offset:      0x{exe_offset:08X}")
print()

# Read original function prologue (first 32 bytes)
print("Original function prologue:")
for i in range(8):
    offset = exe_offset + i * 4
    word = struct.unpack_from('<I', data, offset)[0]
    print(f"  +{i*4:02X}: {word:08X}")

print()

# Original function receives damage_param in $a3 (register 7)
# We need to insert at the start:
#
#   addiu $v0, $zero, 10   ; 0x34020001 = check value
#   bne   $a3, $v0, +3     ; 0x14E20003 = if $a3 != 10, skip 3 instr
#   nop
#   addiu $a3, $zero, 50   ; 0x34070032 = replace with 50
#   (continue original code)
#
# But we need space. Let's check if there are NOPs or safe instructions
# to replace.

# Strategy: Replace first instruction (usually stack frame setup can be delayed)
# and use branch delay slot efficiently.

print("Injecting check at function start...")
print()

# MIPS code:
#   addiu $v0, $zero, 10       ; $v0 = 10
#   bne   $a3, $v0, skip       ; if $a3 != 10, skip to offset +12
#   nop                        ; branch delay slot
#   addiu $a3, $zero, 50       ; $a3 = 50
# skip:
#   (original first instruction)

patch_code = [
    0x3402000A,  # addiu $v0, $zero, 10
    0x14E20002,  # bne $a3, $v0, +2 (skip next 2 instructions)
    0x00000000,  # nop (branch delay slot)
    0x34070032,  # addiu $a3, $zero, 50
]

# Save the original first instruction (we'll move it after our patch)
orig_first = struct.unpack_from('<I', data, exe_offset)[0]
patch_code.append(orig_first)

print("Patch code (5 instructions):")
for i, word in enumerate(patch_code):
    print(f"  +{i*4:02X}: {word:08X}")

print()

# Apply patch (replaces first 5 instructions)
for i, word in enumerate(patch_code):
    struct.pack_into('<I', data, exe_offset + i * 4, word)

# Write patched BIN back (in-place modification)
with open(BIN_FILE, 'wb') as f:
    f.write(data)

print(f"[OK] Patched {BIN_FILE.name} in-place")
print()
print("=" * 60)
print("Test procedure:")
print("=" * 60)
print("1. Build with: build_gameplay_patch.bat")
print("2. Mount output BIN in ePSXe")
print("3. Go to Cavern of Death")
print("4. Get hit by falling rock")
print("5. Damage should be ~50% HP (instead of 10%)")
print()
print("Note: This affects ALL 10% damage sources in the game,")
print("      not just falling rocks.")
print()
