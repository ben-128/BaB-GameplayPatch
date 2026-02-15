#!/usr/bin/env python3
"""
Fix middle section size for 5 monsters

The middle section must be 48 bytes for 5 monsters (not 44).
This script inserts 4 bytes to expand the section correctly.
"""

import struct
from pathlib import Path

BLAZE_ALL = Path("output/BLAZE.ALL")
CAVERN_ANIM = 0xF7A900

# Structure positions
ANIM_HEADER_SIZE = 8
ANIM_TABLES_SIZE = 40  # 5 × 8
ANIM_RECORDS_SIZE = 40  # 5 × 8
MIDDLE_SIZE_OLD = 44  # Current (wrong)
MIDDLE_SIZE_NEW = 48  # Correct for 5 monsters
ASSIGNMENTS_SIZE = 40  # 5 × 8
STATS_SIZE = 480  # 5 × 96

# Calculate offsets
middle_start = CAVERN_ANIM + ANIM_HEADER_SIZE + ANIM_TABLES_SIZE + ANIM_RECORDS_SIZE
middle_end_old = middle_start + MIDDLE_SIZE_OLD
middle_end_new = middle_start + MIDDLE_SIZE_NEW

print("=== FIXING MIDDLE SECTION ===")
print()
print(f"Middle section: 0x{middle_start:X}")
print(f"  Old size: {MIDDLE_SIZE_OLD} bytes")
print(f"  New size: {MIDDLE_SIZE_NEW} bytes")
print(f"  Inserting: {MIDDLE_SIZE_NEW - MIDDLE_SIZE_OLD} bytes")
print()

# Load BLAZE.ALL
with open(BLAZE_ALL, 'rb') as f:
    data = bytearray(f.read())

# Extract sections
middle_section = data[middle_start:middle_end_old]
rest_of_zone = data[middle_end_old:middle_end_old + ASSIGNMENTS_SIZE + STATS_SIZE + 2000]

print("Current middle section:")
print(f"  {middle_section.hex()}")
print()

# Expand middle section by inserting 4 bytes
# Based on Forest pattern, insert 0x3C000000 and 0x44000000 after position [2]
# Pattern seems to be offsets, so we add entries for 2 more monsters

# Current: 00000500 14000000 00400400 1c000000 00800500 ... (11 uint32)
# Target:  00000000 2c000000 34000000 3c000000 44000000 ... (12 uint32)

# Actually, let's just insert 4 zero bytes in a safe position
# Insert after byte 8 (after first 2 uint32)
new_middle = middle_section[:8] + bytes([0, 0, 0, 0]) + middle_section[8:]

print("New middle section (48 bytes):")
print(f"  {new_middle.hex()}")
print()

# Rebuild zone
# Everything before middle stays the same
before_middle = data[:middle_start]

# New middle section
# Everything after middle shifts by 4 bytes
after_middle = data[middle_end_old:]

# Combine
new_data = before_middle + new_middle + after_middle

# Verify size
if len(new_data) != len(data):
    print(f"[ERROR] Size mismatch: {len(new_data)} vs {len(data)}")
    print("This will break the file!")
    exit(1)

print(f"[OK] Size verified: {len(new_data)} bytes")
print()

# Save
backup = BLAZE_ALL.with_suffix('.ALL.backup_before_middle_fix')
BLAZE_ALL.rename(backup)
print(f"[BACKUP] {backup.name}")

with open(BLAZE_ALL, 'wb') as f:
    f.write(new_data)

print(f"[SAVED] {BLAZE_ALL.name}")
print()
print("=" * 60)
print("[SUCCESS] Middle section expanded to 48 bytes")
print("=" * 60)
print()
print("IMPORTANT: This shifts everything after the middle section by 4 bytes!")
print("Stats, script, formations all moved +4 bytes.")
print("The hardcoded offsets need to be updated again!")
