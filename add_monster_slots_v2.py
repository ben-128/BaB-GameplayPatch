#!/usr/bin/env python3
"""
Add Monster Slots - Comprehensive Solution v2

Based on binary analysis comparing Cavern (3m) vs Forest (5m):
- Updates TWO monster count locations (header + middle section)
- Expands middle section from 44 to 48 bytes
- Adds all necessary slot data (tables, records, assignments, stats)
- Updates formation offset references

Key Discovery: Monster count appears in TWO places!
  1. Header @ 0xF7A851 (175 bytes before animation)
  2. Middle section byte[2] @ 0xF7A93A
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
CURRENT = Path("output/BLAZE.ALL")

# Cavern F1 A1 offsets
HEADER_MONSTER_COUNT = 0xF7A851  # NEW: Monster count in header
CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
CAVERN_SCRIPT = 0xF7AA9C
CAVERN_FORMATION = 0xF7AFFC

# Formation offset references
FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]

# Size calculations
OLD_MONSTER_COUNT = 3
NEW_MONSTER_COUNT = 5
SLOTS_TO_ADD = 2

# Expected structure expansion
ANIM_TABLE_BYTES = 8 * SLOTS_TO_ADD  # 16
ANIM_RECORD_BYTES = 8 * SLOTS_TO_ADD  # 16
ASSIGNMENT_BYTES = 8 * SLOTS_TO_ADD  # 16
STATS_BYTES = 96 * SLOTS_TO_ADD  # 192
MIDDLE_EXPANSION = 4  # 44 -> 48 bytes
TOTAL_SHIFT = ANIM_TABLE_BYTES + ANIM_RECORD_BYTES + MIDDLE_EXPANSION + ASSIGNMENT_BYTES + STATS_BYTES  # 244

print("=" * 70)
print("ADD MONSTER SLOTS - Comprehensive v2")
print("=" * 70)
print()

# Restore backup
shutil.copy2(BACKUP, CURRENT)

with open(CURRENT, 'rb') as f:
    data = bytearray(f.read())

print("[STEP 1] Extract vanilla sections")
print()

# Header section
header_monster_count_old = data[HEADER_MONSTER_COUNT]
print(f"  Header monster count @ 0x{HEADER_MONSTER_COUNT:X}: {header_monster_count_old}")

# Animation section
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
print(f"  Animation header: {anim_header.hex(' ')}")

# Animation tables (3×8)
anim_tables_old = data[CAVERN_ANIM+8:CAVERN_ANIM+32]
print(f"  Animation tables: {len(anim_tables_old)} bytes (3 slots)")

# Animation records (3×8)
anim_records_old = data[CAVERN_ANIM+32:CAVERN_ANIM+56]
print(f"  Animation records: {len(anim_records_old)} bytes (3 slots)")

# Middle section (44 bytes)
middle_section_old = data[CAVERN_ANIM+56:CAVERN_STATS-24]
print(f"  Middle section: {len(middle_section_old)} bytes")
print(f"    Middle byte[2] (monster count): {middle_section_old[2]}")

# Assignments (3×8)
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]
print(f"  Assignments: {len(assignments_old)} bytes (3 slots)")

# Stats (3×96)
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]
print(f"  Stats: {len(stats_old)} bytes (3 slots)")

print()
print("[STEP 2] Create new slots (copying slot 0)")
print()

# Copy slot 0 data for new slots
new_anim_table = anim_tables_old[0:8]
new_anim_record = anim_records_old[0:8]
new_assignment = bytes([0x03, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])  # Pattern from vanilla

# Create stats for new slots
def create_stats(slot_name):
    name = slot_name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, 1, 50] + [0]*37  # exp=0, level=1, hp=50, rest=0
    return name + b''.join(struct.pack('<H', v) for v in stats)

new_stats_1 = create_stats("NewSlot1")
new_stats_2 = create_stats("NewSlot2")

print(f"  New animation table: {new_anim_table.hex(' ')}")
print(f"  New animation record: {new_anim_record.hex(' ')}")
print(f"  New assignment: {new_assignment.hex(' ')}")

print()
print("[STEP 3] Expand middle section (44 -> 48 bytes)")
print()

# Expand middle section (insert 4 bytes after first 8 bytes)
middle_section_new = bytearray(middle_section_old[:8] + bytes([0, 0, 0, 0]) + middle_section_old[8:])
print(f"  Old size: {len(middle_section_old)} bytes")
print(f"  New size: {len(middle_section_new)} bytes")

# Update monster count in middle section byte[2]
middle_section_new[2] = NEW_MONSTER_COUNT
print(f"  Updated byte[2]: {middle_section_old[2]} -> {middle_section_new[2]}")

print()
print("[STEP 4] Rebuild animation section")
print()

new_anim_section = bytearray()
new_anim_section += anim_header  # 8
new_anim_section += anim_tables_old + new_anim_table * 2  # 40 (3+2 slots)
new_anim_section += anim_records_old + new_anim_record * 2  # 40
new_anim_section += middle_section_new  # 48
new_anim_section += assignments_old + new_assignment * 2  # 40
new_anim_section += stats_old + new_stats_1 + new_stats_2  # 480

print(f"  Total size: {len(new_anim_section)} bytes")
print(f"    Header: 8")
print(f"    Tables: 40 (5 slots)")
print(f"    Records: 40 (5 slots)")
print(f"    Middle: 48")
print(f"    Assignments: 40 (5 slots)")
print(f"    Stats: 480 (5 slots)")

print()
print("[STEP 5] Rebuild zone (shift sections)")
print()

# Extract sections that come after
script_data = data[CAVERN_SCRIPT:CAVERN_FORMATION]
formation_data = data[CAVERN_FORMATION:CAVERN_FORMATION+896]  # Formation section size
zone_spawns_data = data[CAVERN_FORMATION+896:]  # Everything after

# Build new zone
new_zone = bytearray()
new_zone += new_anim_section
new_zone += script_data
new_zone += formation_data
# Reduce zone_spawns to maintain file size
# (we added 244 bytes, so remove 244 from end)

print(f"  Script size: {len(script_data)} bytes (unchanged)")
print(f"  Formation size: {len(formation_data)} bytes (unchanged)")
print(f"  Zone expansion: +{TOTAL_SHIFT} bytes")

print()
print("[STEP 6] Update monster count in HEADER")
print()

# Update the HEADER monster count
data[HEADER_MONSTER_COUNT] = NEW_MONSTER_COUNT
print(f"  @ 0x{HEADER_MONSTER_COUNT:X}: {header_monster_count_old} -> {NEW_MONSTER_COUNT}")

print()
print("[STEP 7] Write back to BLAZE.ALL")
print()

# Calculate new offsets
NEW_STATS = CAVERN_STATS + TOTAL_SHIFT
NEW_SCRIPT = CAVERN_SCRIPT + TOTAL_SHIFT
NEW_FORMATION = CAVERN_FORMATION + TOTAL_SHIFT

# Write new zone (excluding the tail for now)
zone_size = len(new_anim_section) + len(script_data) + len(formation_data)
data[CAVERN_ANIM:CAVERN_ANIM + zone_size] = new_zone[:zone_size]

print(f"  Wrote {zone_size} bytes starting at 0x{CAVERN_ANIM:X}")

print()
print("[STEP 8] Update formation offset references")
print()

for ref in FORMATION_REFS:
    old_offset = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, NEW_FORMATION)
    print(f"  @ 0x{ref:X}: 0x{old_offset:X} -> 0x{NEW_FORMATION:X}")

# Save
with open(CURRENT, 'wb') as f:
    f.write(data)

print()
print("[SUCCESS] Monster slots added!")
print()
print(f"File size: {len(data):,} bytes")
print()
print("CHANGES MADE:")
print(f"  1. Header monster count: 3 -> 5 @ 0x{HEADER_MONSTER_COUNT:X}")
print(f"  2. Middle section byte[2]: 3 -> 5 @ 0x{CAVERN_ANIM+56+2:X}")
print(f"  3. Middle section expanded: 44 -> 48 bytes")
print(f"  4. Added 2 animation tables (16 bytes)")
print(f"  5. Added 2 animation records (16 bytes)")
print(f"  6. Added 2 assignments (16 bytes)")
print(f"  7. Added 2 stat blocks (192 bytes)")
print(f"  8. Updated 4 formation offset references")
print()
print("NEXT: Copy to bin and test in-game")
