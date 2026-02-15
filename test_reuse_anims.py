#!/usr/bin/env python3
"""
Test: Reuse existing anim tables for new slots

Instead of adding new anim tables (which crashes), create assignments
that point to existing anim tables.

Slot 0,1,2 have anim tables 0,1,2
Slot 3,4 will reuse anim tables 0,1 (no new tables needed)
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT = Path("output/BLAZE.ALL")

CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]

print("=" * 70)
print("TEST: Reuse anim tables for new slots")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

# Extract sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]  # 3 slots
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]  # 3 slots
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]  # 44 bytes
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]  # 3 slots
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]  # 3 slots

print("Vanilla assignments:")
for i in range(3):
    assign = assignments_old[i*8:(i+1)*8]
    print(f"  Slot {i}: {assign.hex(' ')}")
print()

# Create NEW assignments that REUSE existing anim tables
# Slot 3: reuse slot 0's anims (Goblin)
# Slot 4: reuse slot 1's anims (Shaman)
assignment_3 = bytes([0x00, 0x00, 0x00, 0x00, 0x03, 0x02, 0x00, 0x40])  # Points to anim 0
assignment_4 = bytes([0x01, 0x01, 0x00, 0x00, 0x04, 0x03, 0x00, 0x40])  # Points to anim 1

print("New assignments (reusing anims):")
print(f"  Slot 3: {assignment_3.hex(' ')} (reuses anim 0 - Goblin)")
print(f"  Slot 4: {assignment_4.hex(' ')} (reuses anim 1 - Shaman)")
print()

# Add new assignments
assignments_new = assignments_old + assignment_3 + assignment_4  # 40 bytes

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05
print(f"Middle count: 3 -> 5")
print()

# Rebuild section
new_section = bytearray()
new_section += anim_header
new_section += anim_tables  # Still 3 tables! (don't add more)
new_section += anim_records  # Still 3 records!
new_section += middle  # Count=5
new_section += assignments_new  # 5 assignments (2 reuse existing anims)
new_section += stats_old  # Still 3 stats! (don't add more)

print("Section sizes:")
print(f"  Anim tables: 24 bytes (3 slots - NO CHANGE)")
print(f"  Anim records: 24 bytes (3 slots - NO CHANGE)")
print(f"  Middle: 44 bytes (count=5)")
print(f"  Assignments: 40 bytes (5 slots - 2 added)")
print(f"  Stats: 288 bytes (3 slots - NO CHANGE)")
print()

# Write back
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Update formation refs (+16 for added assignments)
print("Updating formation refs (+16 bytes):")
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 16)
    print(f"  0x{ref:X}: 0x{old_val:X} -> 0x{old_val+16:X}")

with open(OUTPUT, 'wb') as f:
    f.write(data)

print()
print("=" * 70)
print("SUCCESS!")
print()
print("Changes:")
print("  - Header count: stays 3 (no infinite loading)")
print("  - Middle count: 3 -> 5")
print("  - Anim tables: 3 (unchanged - no crash)")
print("  - Assignments: 5 (slots 3,4 reuse anims 0,1)")
print("  - Stats: 3 (unchanged - no black level)")
print()
print("Expected behavior:")
print("  - Should load correctly")
print("  - Slots 3,4 will use Goblin/Shaman animations")
print("  - May need to test if slots 3,4 can spawn")
