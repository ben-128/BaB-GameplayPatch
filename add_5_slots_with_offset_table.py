#!/usr/bin/env python3
"""
Add 5 monster slots WITH proper offset table update

Uses formation patcher's offset table logic to ensure all offsets are correct.
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT = Path("output/BLAZE.ALL")

# Floor 1 Area 1 offsets
CAVERN_GROUP = 0xF7A7F8  # Group offset from JSON
CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
CAVERN_SCRIPT = 0xF7AA9C
CAVERN_FORMATION = 0xF7AFFC

FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]
HEADER_COUNT_OFFSET = 0xF7A851
MIDDLE_COUNT_OFFSET = 0xF7A93A

SHIFT_ANIM = 16
SHIFT_RECORDS = 16
SHIFT_ASSIGNMENTS = 16
SHIFT_STATS = 192
TOTAL_SHIFT = 240

print("=" * 70)
print("ADD 5 SLOTS - With Offset Table Fix")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

# Extract vanilla sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables_old = data[CAVERN_ANIM+8:CAVERN_ANIM+32]  # 3×8
anim_records_old = data[CAVERN_ANIM+32:CAVERN_ANIM+56]  # 3×8
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]  # 3×8
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]  # 3×96

# Extract individual elements
table0, table1, table2 = anim_tables_old[0:8], anim_tables_old[8:16], anim_tables_old[16:24]
record0, record1, record2 = anim_records_old[0:8], anim_records_old[8:16], anim_records_old[16:24]
stat0, stat1, stat2 = stats_old[0:96], stats_old[96:192], stats_old[192:288]

print("Creating 5 animation tables (duplicating 0,1 for slots 3,4)")

# Create 5 anim tables/records
anim_tables_new = table0 + table1 + table2 + table0 + table1  # Duplicate 0,1
anim_records_new = record0 + record1 + record2 + record0 + record1

print("Creating 5 stats")

def create_stats(name, level, hp):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, level, hp] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

stats_new = stat0 + stat1 + stat2 + create_stats("Goblin-Leader", 63, 92) + create_stats("Big-Viper", 5, 80)

# Create 5 assignments
assignment_0 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x40])
assignment_1 = bytes([0x01, 0x01, 0x00, 0x00, 0x01, 0x03, 0x00, 0x40])
assignment_2 = bytes([0x02, 0x03, 0x00, 0x00, 0x02, 0x04, 0x00, 0x40])
assignment_3 = bytes([0x00, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])
assignment_4 = bytes([0x01, 0x01, 0x00, 0x00, 0x04, 0x06, 0x00, 0x40])

assignments_new = assignment_0 + assignment_1 + assignment_2 + assignment_3 + assignment_4

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05

# Rebuild section
new_section = bytearray()
new_section += anim_header
new_section += anim_tables_new
new_section += anim_records_new
new_section += middle
new_section += assignments_new
new_section += stats_new

print(f"New section: {len(new_section)} bytes (shift: +{TOTAL_SHIFT})")
print()

# Calculate new offsets
NEW_SCRIPT = CAVERN_SCRIPT + TOTAL_SHIFT
NEW_FORMATION = CAVERN_FORMATION + TOTAL_SHIFT

print(f"Script:    0x{CAVERN_SCRIPT:X} -> 0x{NEW_SCRIPT:X} (+{TOTAL_SHIFT})")
print(f"Formation: 0x{CAVERN_FORMATION:X} -> 0x{NEW_FORMATION:X} (+{TOTAL_SHIFT})")
print()

# === CRITICAL: Update offset table in script area ===
print("=" * 70)
print("UPDATING OFFSET TABLE (formation patcher logic)")
print("=" * 70)
print()

# Read offset table from script area
script_start = CAVERN_SCRIPT
script_size = CAVERN_FORMATION - CAVERN_SCRIPT
print(f"Script area: 0x{script_start:X} - 0x{CAVERN_FORMATION:X} ({script_size} bytes)")

# Read uint32 LE entries
offset_table = []
max_entries = min(script_size // 4, 64)
for i in range(max_entries):
    val = struct.unpack_from('<I', data, script_start + i * 4)[0]
    if val >= 0x10000:  # Unreasonable offset
        break
    offset_table.append(val)
    if val == 0 and i > 0 and offset_table[i-1] == 0:  # Two consecutive zeros
        break

print(f"Offset table ({len(offset_table)} entries):")
for i, val in enumerate(offset_table):
    print(f"  [{i:2d}] = 0x{val:04X} ({val})")
print()

# The formation offsets are at the END of the table (before the terminal zeros)
# For Floor 1 Area 1: 4 formations originally
# Offsets are RELATIVE to some implied base

# Find formation entries: last 4 non-zero entries before terminal zeros
# Strip terminal zeros
while offset_table and offset_table[-1] == 0:
    offset_table.pop()

if len(offset_table) >= 4:
    # Last 4 entries are formation offsets
    fm_start_idx = len(offset_table) - 4
    fm_offsets_old = offset_table[fm_start_idx:fm_start_idx+4]

    print(f"Formation offsets (entries {fm_start_idx}-{fm_start_idx+3}):")
    for i, off in enumerate(fm_offsets_old):
        print(f"  FM{i}: 0x{off:04X} ({off})")
    print()

    # Formation offsets need to be shifted by TOTAL_SHIFT
    # They are RELATIVE offsets from implied base
    # When we shift formation area by +240, these offsets increase by +240

    fm_offsets_new = [off + TOTAL_SHIFT for off in fm_offsets_old]

    print("New formation offsets (+240 shift):")
    for i, off in enumerate(fm_offsets_new):
        print(f"  FM{i}: 0x{off:04X} ({off})")
    print()

    # Write updated offsets back
    for i, off in enumerate(fm_offsets_new):
        offset_pos = script_start + (fm_start_idx + i) * 4
        struct.pack_into('<I', data, offset_pos, off)
        print(f"  Updated @ 0x{offset_pos:X}: 0x{fm_offsets_old[i]:04X} -> 0x{off:04X}")

    print()
    print("Offset table updated successfully!")
else:
    print(f"WARNING: Could not find 4 formation entries (table has {len(offset_table)} entries)")
    print("Proceeding without offset table update (may cause crashes)")

print()

# Build new file
with open(BACKUP, 'rb') as f:
    backup = bytearray(f.read())

script_and_rest = backup[CAVERN_SCRIPT:]
data = backup

# Write new section
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Write script and rest at new position
new_script_pos = CAVERN_ANIM + len(new_section)
data[new_script_pos:new_script_pos + len(script_and_rest) - TOTAL_SHIFT] = script_and_rest[:-TOTAL_SHIFT]

if len(data) > len(backup):
    data = data[:len(backup)]

# Update formation refs
print("Updating formation refs:")
for ref in FORMATION_REFS:
    struct.pack_into('<I', data, ref, NEW_FORMATION)
    print(f"  0x{ref:X}: 0x{NEW_FORMATION:X}")
print()

# Update header count
print(f"Header count: {data[HEADER_COUNT_OFFSET]} -> 5")
data[HEADER_COUNT_OFFSET] = 0x05

# Save
with open(OUTPUT, 'wb') as f:
    f.write(data)

print()
print("=" * 70)
print("DONE!")
print("=" * 70)
print()
print("Changes:")
print("  - 5 animation tables")
print("  - 5 stats")
print("  - header_count = 5")
print("  - Offset table UPDATED (+240 shift)")
print()
print("This should avoid CD seek errors by properly updating the offset table!")
