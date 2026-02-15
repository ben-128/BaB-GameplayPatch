#!/usr/bin/env python3
"""
Patch the animation loading loop to use limit=3 instead of 5

The loop at 0x80030A1C compares a counter to v1 (the limit).
We need to find where v1 is loaded with value 5 and change it to 3.

Common MIPS patterns for loading immediate value 5:
  li v1, 5           → 05 00 03 24  (addiu v1, zero, 5)
  addiu v1, zero, 5  → 05 00 03 24
  ori v1, zero, 5    → 05 00 23 34

Or loading from memory (header_count):
  lbu v1, offset(reg)
  lw v1, offset(reg)
"""

import struct
from pathlib import Path

OUTPUT = Path("output/BLAZE.ALL")

# Pattern 1: addiu v1, zero, 5
PATTERN_ADDIU_V1_5 = bytes([0x05, 0x00, 0x03, 0x24])
PATCH_ADDIU_V1_3 = bytes([0x03, 0x00, 0x03, 0x24])

# Pattern 2: ori v1, zero, 5
PATTERN_ORI_V1_5 = bytes([0x05, 0x00, 0x23, 0x34])
PATCH_ORI_V1_3 = bytes([0x03, 0x00, 0x23, 0x34])

# Pattern 3: li at, 5 (might be in upper bits)
# This is harder to search for generically

print("=" * 70)
print("PATCH: Change animation loop limit from 5 to 3")
print("=" * 70)
print()

if not OUTPUT.exists():
    print("ERROR: output/BLAZE.ALL not found")
    exit(1)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

print("Searching for v1 load patterns...")
print()

# Search for addiu v1, zero, 5
print("Pattern 1: addiu v1, zero, 5 (05 00 03 24)")
matches_addiu = []
for i in range(len(data) - 4):
    if data[i:i+4] == PATTERN_ADDIU_V1_5:
        matches_addiu.append(i)

print(f"  Found {len(matches_addiu)} matches")
if matches_addiu and len(matches_addiu) < 20:
    for match in matches_addiu[:10]:
        print(f"    0x{match:X}")

print()

# Search for ori v1, zero, 5
print("Pattern 2: ori v1, zero, 5 (05 00 23 34)")
matches_ori = []
for i in range(len(data) - 4):
    if data[i:i+4] == PATTERN_ORI_V1_5:
        matches_ori.append(i)

print(f"  Found {len(matches_ori)} matches")
if matches_ori and len(matches_ori) < 20:
    for match in matches_ori[:10]:
        print(f"    0x{match:X}")

print()

# For now, let's try a different approach: search near the loop code
# The loop is at RAM 0x80030A1C, which is in the Cavern overlay
# The Cavern overlay starts around 0xF7A000 in BLAZE.ALL

print("Searching near Cavern overlay (0xF70000 - 0xF90000)...")
print()

OVERLAY_START = 0xF70000
OVERLAY_END = 0xF90000

# Search for the slt v0, v0, v1 instruction (2A 10 43 00)
SLT_PATTERN = bytes([0x2A, 0x10, 0x43, 0x00])  # slt v0, v0, v1

print(f"Looking for 'slt v0, v0, v1' instruction: {SLT_PATTERN.hex(' ')}")
slt_matches = []
for i in range(OVERLAY_START, min(OVERLAY_END, len(data) - 4)):
    if data[i:i+4] == SLT_PATTERN:
        slt_matches.append(i)

print(f"  Found {len(slt_matches)} matches in overlay range")
for match in slt_matches[:5]:
    print(f"    0x{match:X}")
    # Show context (20 bytes before)
    context = data[match-20:match]
    print(f"      Context: {context.hex(' ')}")

print()

if slt_matches:
    print("Checking for v1 loads near each slt match...")
    print()

    for slt_offset in slt_matches[:5]:
        print(f"Near slt @ 0x{slt_offset:X}:")

        # Check 100 bytes before for v1 loads
        search_start = max(0, slt_offset - 100)
        search_end = slt_offset

        found_v1_load = False

        # Check for any instruction that writes to v1 ($3)
        # v1 = register 3
        # Common patterns:
        #   addiu $3, ... → XX XX 03 24
        #   ori $3, ...   → XX XX 23 34
        #   lw $3, ...    → XX XX 23 8C (or similar)
        #   lbu $3, ...   → XX XX 23 90

        for i in range(search_start, search_end, 4):
            instr = data[i:i+4]
            if len(instr) < 4:
                continue

            # Check if this writes to register 3 (v1)
            # In MIPS, destination register is often at byte[1] bits 0-4
            # For immediate instructions: opcode(6) | rs(5) | rt(5) | immediate(16)
            # rt = destination = byte[1] bits 0-4

            # addiu $3, $0, X → X 00 03 24
            if instr[2] == 0x03 and instr[3] == 0x24:
                value = instr[0] | (instr[1] << 8)
                if value >= 1 and value <= 10:  # Reasonable range
                    print(f"    0x{i:X}: addiu v1, zero, {value}")
                    if value == 5:
                        print(f"      *** FOUND IT! This loads v1=5 ***")
                        found_v1_load = True

            # ori $3, $0, X → X 00 23 34
            if instr[2] == 0x23 and instr[3] == 0x34:
                value = instr[0] | (instr[1] << 8)
                if value >= 1 and value <= 10:
                    print(f"    0x{i:X}: ori v1, zero, {value}")
                    if value == 5:
                        print(f"      *** FOUND IT! This loads v1=5 ***")
                        found_v1_load = True

        if not found_v1_load:
            print(f"    No v1=5 load found in 100 bytes before slt")

        print()

print("=" * 70)
print("MANUAL SEARCH COMPLETE")
print("=" * 70)
print()
print("If v1=5 load was found above, we can patch it.")
print("Otherwise, we need to:")
print("  1. Scroll up more in DuckStation debugger")
print("  2. Find where v1 gets value 5")
print("  3. Report the instruction and offset")
