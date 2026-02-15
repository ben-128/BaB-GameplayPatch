#!/usr/bin/env python3
"""
Extract REAL animation tables for Big-Viper and Goblin-Leader

Big-Viper: exists in Cavern Floor 3 Area 1, slot 2
Goblin-Leader: need to find where it appears

We'll extract their animation tables and records from the backup binary.
"""

import json
import struct
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")

# Floor 3 Area 1 data (from JSON)
F3A1_GROUP_OFFSET = 0xF86198
F3A1_MONSTERS = ["Giant-Scorpion", "Giant-Bat", "Big-Viper", "Giant-Spider"]

print("=" * 70)
print("EXTRACT REAL ANIMATIONS")
print("=" * 70)
print()

with open(BACKUP, 'rb') as f:
    data = f.read()

print("Floor 3 Area 1 structure:")
print(f"  Group offset: 0x{F3A1_GROUP_OFFSET:X}")
print(f"  Monsters: {F3A1_MONSTERS}")
print()

# Animation section structure (same as Floor 1):
# - 8 bytes: header
# - N * 8 bytes: animation tables (N = header count)
# - N * 8 bytes: animation records
# - 44 bytes: middle section (includes count)
# - M * 8 bytes: assignments (M = middle count)
# - M * 96 bytes: stats

# Read header
header_offset = F3A1_GROUP_OFFSET + 8  # Skip group header
header = data[header_offset:header_offset+8]
print(f"Header @ 0x{header_offset:X}: {header.hex(' ')}")

# Extract header count (byte 3, assuming same structure)
header_count_offset = header_offset - 0xAF  # Same relative position as Floor 1
header_count = data[header_count_offset]
print(f"Header count @ 0x{header_count_offset:X}: {header_count}")
print()

# Read animation tables
anim_tables_offset = header_offset + 8
anim_tables_size = header_count * 8
anim_tables = data[anim_tables_offset:anim_tables_offset+anim_tables_size]

print(f"Animation tables @ 0x{anim_tables_offset:X} ({header_count} tables):")
for i in range(header_count):
    table = anim_tables[i*8:(i+1)*8]
    monster = F3A1_MONSTERS[i] if i < len(F3A1_MONSTERS) else "???"
    print(f"  Slot {i} ({monster}): {table.hex(' ')}")
print()

# Read animation records
anim_records_offset = anim_tables_offset + anim_tables_size
anim_records_size = header_count * 8
anim_records = data[anim_records_offset:anim_records_offset+anim_records_size]

print(f"Animation records @ 0x{anim_records_offset:X} ({header_count} records):")
for i in range(header_count):
    record = anim_records[i*8:(i+1)*8]
    monster = F3A1_MONSTERS[i] if i < len(F3A1_MONSTERS) else "???"
    print(f"  Slot {i} ({monster}): {record.hex(' ')}")
print()

# Extract Big-Viper (slot 2)
if header_count >= 3:
    big_viper_table = anim_tables[2*8:3*8]
    big_viper_record = anim_records[2*8:3*8]

    print("=" * 70)
    print("BIG-VIPER ANIMATIONS (Slot 2)")
    print("=" * 70)
    print(f"Table:  {big_viper_table.hex(' ')}")
    print(f"Record: {big_viper_record.hex(' ')}")
    print()

    # Save to file for easy copy-paste
    with open("output/big_viper_animations.txt", 'w') as f:
        f.write(f"Big-Viper Animation Table: {big_viper_table.hex(' ')}\n")
        f.write(f"Big-Viper Animation Record: {big_viper_record.hex(' ')}\n")

    print("Saved to output/big_viper_animations.txt")
else:
    print("ERROR: Not enough slots to extract Big-Viper")

print()
print("=" * 70)
print("NEXT: Search for Goblin-Leader")
print("=" * 70)
print()
print("Goblin-Leader doesn't appear in extracted formations.")
print("It might be:")
print("  1. In a zone we haven't extracted yet")
print("  2. A renamed monster (different name in binary)")
print("  3. Only exists in our modified JSONs")
print()
print("Check WIP/level_design or search the binary for monster ID 58")
