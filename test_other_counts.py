#!/usr/bin/env python3
"""
Test: Change the OTHER count fields (+0x14, +0x30)

Found that Forest (5m) has different values at header+0x14 and header+0x30
compared to Cavern (3m). Test if changing these helps with stats.
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT = Path("output/BLAZE.ALL")

HEADER_COUNT = 0xF7A851
COUNT_0x14 = 0xF7A865  # HEADER_COUNT + 0x14
COUNT_0x30 = 0xF7A881  # HEADER_COUNT + 0x30
MIDDLE_COUNT = 0xF7A93A

CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]

print("=" * 70)
print("TEST: Change OTHER count fields")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

print("Vanilla counts:")
print(f"  Header @ 0x{HEADER_COUNT:X}: {data[HEADER_COUNT]}")
print(f"  +0x14  @ 0x{COUNT_0x14:X}: {struct.unpack_from('<I', data, COUNT_0x14)[0]}")
print(f"  +0x30  @ 0x{COUNT_0x30:X}: {struct.unpack_from('<I', data, COUNT_0x30)[0]}")
print(f"  Middle @ 0x{MIDDLE_COUNT:X}: {data[MIDDLE_COUNT]}")
print()

# Extract sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments = data[CAVERN_STATS-24:CAVERN_STATS]
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]

# Create new stats for Goblin-Leader and Big-Viper
def create_stats(name, level, hp):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, level, hp] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

stats_slot3 = create_stats("Goblin-Leader", 63, 200)  # Level 63
stats_slot4 = create_stats("Big-Viper", 5, 80)  # Level 5

stats_new = stats_old + stats_slot3 + stats_slot4

# Create new assignments for slots 3,4
# Reuse animations from slots 0,1
assignment_3 = bytes([0x00, 0x00, 0x00, 0x00, 0x03, 0x02, 0x00, 0x40])
assignment_4 = bytes([0x01, 0x01, 0x00, 0x00, 0x04, 0x03, 0x00, 0x40])
assignments_new = assignments + assignment_3 + assignment_4

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05

# Rebuild section
new_section = bytearray()
new_section += anim_header
new_section += anim_tables  # Still 3
new_section += anim_records  # Still 3
new_section += middle  # Count=5
new_section += assignments_new  # 5 assignments
new_section += stats_new  # 5 stats!

# Write back
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

print("Changes applied:")
print(f"  Assignments: 24 -> 40 bytes (+16)")
print(f"  Stats: 288 -> 480 bytes (+192)")
print(f"  Total shift: +208 bytes")
print()

# Update counts
# Keep header count at 3 (to avoid infinite loading)
# But change the OTHER counts
print("Updating counts:")
print(f"  Header @ 0x{HEADER_COUNT:X}: 3 (unchanged)")

# Change +0x14 count from 2 to 3 (following Forest pattern)
old_val = struct.unpack_from('<I', data, COUNT_0x14)[0]
struct.pack_into('<I', data, COUNT_0x14, 3)
print(f"  +0x14  @ 0x{COUNT_0x14:X}: {old_val} -> 3")

# Change +0x30 count from 2 to 3
old_val = struct.unpack_from('<I', data, COUNT_0x30)[0]
struct.pack_into('<I', data, COUNT_0x30, 3)
print(f"  +0x30  @ 0x{COUNT_0x30:X}: {old_val} -> 3")

print(f"  Middle @ 0x{MIDDLE_COUNT:X}: 3 -> 5")
print()

# Update formation refs
print("Updating formation refs (+208 bytes):")
for ref in FORMATION_REFS:
    old_offset = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_offset + 208)
    print(f"  0x{ref:X}: 0x{old_offset:X} -> 0x{old_offset+208:X}")

with open(OUTPUT, 'wb') as f:
    f.write(data)

print()
print("=" * 70)
print("SUCCESS!")
print()
print("Test this version:")
print("  - Header count = 3 (no infinite loading)")
print("  - +0x14 count = 3 (was 2)")
print("  - +0x30 count = 3 (was 2)")
print("  - Middle count = 5")
print("  - Stats = 5 (with Goblin-Leader and Big-Viper)")
print()
print("Expected: If +0x14 or +0x30 controls stats reading,")
print("          this should fix the BLACK LEVEL issue!")
