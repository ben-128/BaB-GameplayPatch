#!/usr/bin/env python3
"""
Test: 3 animation tables, 5 stats, header=3, middle=5

This will likely cause BLACK LEVEL (wrong script offset)
but NOT crash at 0x00000874.

If it crashes at 0x00000874, the problem is NOT header_count.
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT = Path("output/BLAZE.ALL")

CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
CAVERN_SCRIPT = 0xF7AA9C
CAVERN_FORMATION = 0xF7AFFC

FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]
MIDDLE_COUNT_OFFSET = 0xF7A93A

# Only adding stats/assignments, NOT anim tables
SHIFT_ASSIGNMENTS = 16
SHIFT_STATS = 192
TOTAL_SHIFT = SHIFT_ASSIGNMENTS + SHIFT_STATS  # 208 bytes

print("=" * 70)
print("TEST: 3 anim tables, 5 stats (header=3, middle=5)")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

# Extract vanilla
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]  # 3×8 ONLY
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]  # 3×8 ONLY
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]

# Create 5 stats
def create_stats(name, level, hp):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, level, hp] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

stats_new = bytearray()
stats_new += stats_old[0:96]  # Slot 0
stats_new += stats_old[96:192]  # Slot 1
stats_new += stats_old[192:288]  # Slot 2
stats_new += create_stats("Goblin-Leader", 63, 92)  # Slot 3
stats_new += create_stats("Big-Viper", 5, 80)  # Slot 4

# Create 5 assignments (reuse anims 0,1 for slots 3,4)
assignment_0 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x40])
assignment_1 = bytes([0x01, 0x01, 0x00, 0x00, 0x01, 0x03, 0x00, 0x40])
assignment_2 = bytes([0x02, 0x03, 0x00, 0x00, 0x02, 0x04, 0x00, 0x40])
assignment_3 = bytes([0x00, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])
assignment_4 = bytes([0x01, 0x01, 0x00, 0x00, 0x04, 0x06, 0x00, 0x40])

assignments_new = assignment_0 + assignment_1 + assignment_2 + assignment_3 + assignment_4

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05

# Rebuild
new_section = bytearray()
new_section += anim_header
new_section += anim_tables  # 24 (3 tables ONLY!)
new_section += anim_records  # 24 (3 records ONLY!)
new_section += middle  # 44 (count=5)
new_section += assignments_new  # 40 (5 assignments)
new_section += stats_new  # 480 (5 stats)

print(f"Section: {len(new_section)} bytes")
print(f"  3 anim tables (24 bytes)")
print(f"  3 anim records (24 bytes)")
print(f"  5 assignments (40 bytes)")
print(f"  5 stats (480 bytes)")
print(f"  header_count = 3 (unchanged)")
print(f"  middle_count = 5")
print()

# Build file
with open(BACKUP, 'rb') as f:
    backup = bytearray(f.read())

script_and_rest = backup[CAVERN_SCRIPT:]
data = backup
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

new_script_pos = CAVERN_ANIM + len(new_section)
data[new_script_pos:new_script_pos + len(script_and_rest) - TOTAL_SHIFT] = script_and_rest[:-TOTAL_SHIFT]

if len(data) > len(backup):
    data = data[:len(backup)]

# Update formation refs
NEW_FORMATION = CAVERN_FORMATION + TOTAL_SHIFT
for ref in FORMATION_REFS:
    struct.pack_into('<I', data, ref, NEW_FORMATION)

with open(OUTPUT, 'wb') as f:
    f.write(data)

print("DONE!")
print()
print("Expected result: BLACK LEVEL (wrong script offset)")
print("If it crashes at 0x00000874 instead, problem is NOT header_count!")
