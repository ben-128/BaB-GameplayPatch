#!/usr/bin/env python3
"""
Patch the infinite loading loop when header_count=5

PROBLEM: Game loops at 0x80030A9C waiting for animation tables 4-5 to load
SOLUTION: Force v0 to be non-zero so the loop exits

Assembly at RAM 0x80030A9C:
  80030A9C: addu v0, zero, zero  # v0=0 (PROBLEM - always fails check)
  80030AA0: bne v0, zero, 0x80030bbc  # Exit if v0!=0 (never exits!)

PATCH: Change instruction at 0x80030A9C
  FROM: addu v0, zero, zero  # 21 10 00 00
  TO:   addiu v0, zero, 1    # 01 00 02 24

This makes v0=1, so the branch at 0x80030AA0 will take and exit the loop.
"""

import struct
from pathlib import Path

# This code is in the Cavern overlay
# Need to find the offset in BLAZE.ALL

# Pattern to find:
# 80030A94: j 0x80030aa0        # 0C 28 02 28 (might vary)
# 80030A98: addiu v0, zero, -1  # FF FF 02 24
# 80030A9C: addu v0, zero, zero # 21 10 00 00  <- PATCH THIS
# 80030AA0: bne v0, zero, ...   # XX XX 40 14 (might vary)

PATTERN_BEFORE = bytes([
    0xFF, 0xFF, 0x02, 0x24,  # addiu v0, zero, -1
])

PATTERN_TARGET = bytes([
    0x21, 0x10, 0x00, 0x00,  # addu v0, zero, zero
])

PATTERN_AFTER = bytes([
    0x14, 0x40,  # bne v0, zero (partial - last 2 bytes vary)
])

PATCH_NEW = bytes([
    0x01, 0x00, 0x02, 0x24,  # addiu v0, zero, 1
])

OUTPUT = Path("output/BLAZE.ALL")

print("=" * 70)
print("PATCH: Header=5 Infinite Loading Loop")
print("=" * 70)
print()

if not OUTPUT.exists():
    print("ERROR: output/BLAZE.ALL not found")
    print("Run test_header5_for_debug.py first")
    exit(1)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

print("Searching for pattern...")
print(f"  Pattern: {PATTERN_BEFORE.hex(' ')} {PATTERN_TARGET.hex(' ')} [bne v0]")
print()

# Search for the pattern
found_offsets = []

for i in range(len(data) - 12):
    # Check if we match: [BEFORE][TARGET][bne partial]
    if (data[i:i+4] == PATTERN_BEFORE and
        data[i+4:i+8] == PATTERN_TARGET and
        data[i+8:i+10] == PATTERN_AFTER):
        found_offsets.append(i + 4)  # Offset of TARGET instruction

if not found_offsets:
    print("ERROR: Pattern not found!")
    print()
    print("This could mean:")
    print("  1. The overlay isn't in BLAZE.ALL at this pattern")
    print("  2. The pattern is slightly different")
    print("  3. The code is in a different overlay")
    print()
    print("We need to search more broadly...")

    # Try searching for just the target instruction
    print("Searching for target instruction only: 21 10 00 00")
    simple_matches = []
    for i in range(len(data) - 4):
        if data[i:i+4] == PATTERN_TARGET:
            simple_matches.append(i)

    print(f"Found {len(simple_matches)} matches for 'addu v0, zero, zero'")
    if simple_matches and len(simple_matches) < 50:
        print()
        print("First 20 matches (check these manually):")
        for match in simple_matches[:20]:
            print(f"  0x{match:X}")
            # Show context
            before = data[match-4:match]
            target = data[match:match+4]
            after = data[match+4:match+8]
            print(f"    {before.hex(' ')} [{target.hex(' ')}] {after.hex(' ')}")

    exit(1)

print(f"Found {len(found_offsets)} match(es):")
for offset in found_offsets:
    print(f"  BLAZE.ALL offset: 0x{offset:X}")

    # Show context
    before = data[offset-4:offset]
    target = data[offset:offset+4]
    after = data[offset+4:offset+12]

    print(f"    Before: {before.hex(' ')}")
    print(f"    Target: {target.hex(' ')} (will patch)")
    print(f"    After:  {after.hex(' ')}")
    print()

if len(found_offsets) == 0:
    print("No matches found - cannot patch")
    exit(1)

if len(found_offsets) > 1:
    print("WARNING: Multiple matches found!")
    print("Will patch ALL of them (they might all be the same loop in different overlays)")
    print()

# Apply patch
print("Applying patch...")
for offset in found_offsets:
    print(f"  Patching @ 0x{offset:X}")
    print(f"    OLD: {data[offset:offset+4].hex(' ')} (addu v0, zero, zero)")
    data[offset:offset+4] = PATCH_NEW
    print(f"    NEW: {data[offset:offset+4].hex(' ')} (addiu v0, zero, 1)")

print()

# Write patched file
with open(OUTPUT, 'wb') as f:
    f.write(data)

print("=" * 70)
print("PATCH APPLIED!")
print("=" * 70)
print()
print("What this does:")
print("  - OLD: v0 = 0 (always fails the check)")
print("  - NEW: v0 = 1 (always passes the check)")
print()
print("Result:")
print("  - Loop will exit immediately instead of waiting forever")
print("  - Game will continue loading even though tables 4-5 don't exist")
print()
print("Test now:")
print("  1. Load the game in DuckStation")
print("  2. Enter Cavern F1 A1")
print("  3. Should load successfully (no infinite loading)")
print()
print("If it crashes AFTER loading, that's progress! It means:")
print("  - The infinite loop is fixed")
print("  - But the game needs those animation tables for something")
print("  - We'll need a different approach (add actual tables)")
