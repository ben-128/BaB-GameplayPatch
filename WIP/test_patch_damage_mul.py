#!/usr/bin/env python3
"""
Test patch: Multiplier ALL damage% by 5 at the damage function level.

This patches the damage calculation formula in EXE at 0x80024F90:
  damage = (maxHP * param%) / 100

We change it to:
  damage = (maxHP * param% * 5) / 100

If falling rocks go from 10% to 50%, we know the 10% value IS reaching
the damage function (just not patchable in BLAZE.ALL data).
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BIN_FILE = SCRIPT_DIR.parent / "Blaze & Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"

# SLES_008.45 location in BIN
SLES_LBA = 295081
SECTOR_SIZE = 2352
HEADER_SIZE = 24
DATA_SIZE = 2048

SLES_BIN_OFFSET = SLES_LBA * SECTOR_SIZE + HEADER_SIZE

# Damage function in EXE (RAM 0x80024F90 = file offset 0x15790)
# Formula: damage = (maxHP * param%) / 100
# Code at 0x80024FEC:
#   0x80024FEC: mult $a1, $a3    ; $a1=maxHP, $a3=param%
#   0x80024FF0: mflo $a1         ; $a1 = maxHP * param%
#
# We insert: mult $a1, 5 before the /100 division

EXE_DAMAGE_MULT_OFFSET = (0x80024FEC - 0x80010000) + 0x800  # Correct EXE offset

print(f"Test patch: Multiplier tous les dégâts par 5")
print(f"BIN file: {BIN_FILE}")
print()

with open(BIN_FILE, 'rb') as f:
    data = bytearray(f.read())

print(f"EXE damage function offset: 0x{SLES_BIN_OFFSET + EXE_DAMAGE_MULT_OFFSET:08X}")

# Read original instructions
offset = SLES_BIN_OFFSET + EXE_DAMAGE_MULT_OFFSET
orig = struct.unpack_from('<II', data, offset)
print(f"Original @0x{offset:X}:")
print(f"  {orig[0]:08X} {orig[1]:08X}")

# MIPS: ori $v0, $zero, 5  (0x34020005)
#       mult $a1, $v0      (0x00A20018)
mult_5 = [
    0x34020005,  # ori $v0, $zero, 5
    0x00A20018,  # mult $a1, $v0
]

print(f"Patched:")
for word in mult_5:
    print(f"  {word:08X}")

# Apply patch
struct.pack_into('<II', data, offset, *mult_5)

# Write to output
output_bin = SCRIPT_DIR.parent / "output" / "test_damage_x5.bin"
output_bin.parent.mkdir(exist_ok=True)

with open(output_bin, 'wb') as f:
    f.write(data)

print()
print(f"✓ Patched BIN saved to: {output_bin}")
print()
print("TEST:")
print("  1. Monter cette BIN dans ePSXe")
print("  2. Se faire toucher par rocher tombant")
print("  3. Si dégâts ~50% PV → le 10% atteint bien la fonction")
print("  4. Si dégâts toujours ~10% → problème plus profond")
