#!/usr/bin/env python3
"""
Extract animation tables from Floor 2 Area 1

Monsters:
  Slot 0: Goblin-Shaman
  Slot 1: Giant-Bat
  Slot 2: Big-Viper       <- Extract this
  Slot 3: Goblin-Leader   <- Extract this
"""

import struct
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")

# Floor 2 Area 1 offsets from JSON
F2A1_GROUP_OFFSET = 0xF819A0

# Structure (same as Floor 1):
# Group offset + 8 = start of animation section
# But we need to find header_count offset first

# Floor 1 Area 1 structure for reference:
# Header count @ 0xF7A851
# Animation section @ 0xF7A900 (= 0xF7A851 + 0xAF)

# So for Floor 2:
# Header count should be at: F2A1_GROUP_OFFSET - some_offset
# Let's search for the pattern

print("=" * 70)
print("EXTRACT Floor 2 Area 1 Animations")
print("=" * 70)
print()

with open(BACKUP, 'rb') as f:
    data = f.read()

# The animation section starts shortly after group_offset
# Let's scan the area around group_offset to find the header

print(f"Group offset: 0x{F2A1_GROUP_OFFSET:X}")
print()

# Scan 256 bytes before group_offset to find header count
# Header count is typically 1 byte, value 3-5
print("Scanning for header section...")

# Floor 1 pattern: header is 0xAF bytes before animation start
# Let's check if same pattern applies

HEADER_COUNT_OFFSET = F2A1_GROUP_OFFSET - 0xAF
header_count = data[HEADER_COUNT_OFFSET]

print(f"Header count @ 0x{HEADER_COUNT_OFFSET:X}: {header_count}")

if header_count < 2 or header_count > 10:
    print(f"  WARNING: Unusual header count {header_count}")
    print(f"  Trying alternative offset...")

    # Try scanning
    for offset in range(F2A1_GROUP_OFFSET - 256, F2A1_GROUP_OFFSET):
        val = data[offset]
        if val == 4:  # We expect 4 monsters
            # Check if this looks like a header count position
            # by verifying surrounding structure
            print(f"  Found value 4 at 0x{offset:X}")
            HEADER_COUNT_OFFSET = offset
            header_count = 4
            break

print()

# Animation section starts at group_offset + 8
ANIM_SECTION_START = F2A1_GROUP_OFFSET + 8

# Read header (8 bytes)
header = data[ANIM_SECTION_START:ANIM_SECTION_START+8]
print(f"Header @ 0x{ANIM_SECTION_START:X}:")
print(f"  {header.hex(' ')}")
print()

# Read animation tables
ANIM_TABLES_OFFSET = ANIM_SECTION_START + 8
anim_tables_size = header_count * 8
anim_tables = data[ANIM_TABLES_OFFSET:ANIM_TABLES_OFFSET+anim_tables_size]

print(f"Animation Tables @ 0x{ANIM_TABLES_OFFSET:X} ({header_count} tables):")
for i in range(header_count):
    table = anim_tables[i*8:(i+1)*8]
    monsters = ["Goblin-Shaman", "Giant-Bat", "Big-Viper", "Goblin-Leader"]
    monster = monsters[i] if i < len(monsters) else "???"
    print(f"  Slot {i} ({monster:15s}): {table.hex(' ')}")
print()

# Read animation records
ANIM_RECORDS_OFFSET = ANIM_TABLES_OFFSET + anim_tables_size
anim_records_size = header_count * 8
anim_records = data[ANIM_RECORDS_OFFSET:ANIM_RECORDS_OFFSET+anim_records_size]

print(f"Animation Records @ 0x{ANIM_RECORDS_OFFSET:X} ({header_count} records):")
for i in range(header_count):
    record = anim_records[i*8:(i+1)*8]
    monsters = ["Goblin-Shaman", "Giant-Bat", "Big-Viper", "Goblin-Leader"]
    monster = monsters[i] if i < len(monsters) else "???"
    print(f"  Slot {i} ({monster:15s}): {record.hex(' ')}")
print()

# Extract Big-Viper (slot 2) and Goblin-Leader (slot 3)
if header_count >= 4:
    big_viper_table = anim_tables[2*8:3*8]
    big_viper_record = anim_records[2*8:3*8]

    goblin_leader_table = anim_tables[3*8:4*8]
    goblin_leader_record = anim_records[3*8:4*8]

    print("=" * 70)
    print("EXTRACTED ANIMATIONS")
    print("=" * 70)
    print()
    print("Big-Viper (Slot 2):")
    print(f"  Table:  {big_viper_table.hex(' ')}")
    print(f"  Record: {big_viper_record.hex(' ')}")
    print()
    print("Goblin-Leader (Slot 3):")
    print(f"  Table:  {goblin_leader_table.hex(' ')}")
    print(f"  Record: {goblin_leader_record.hex(' ')}")
    print()

    # Save to file
    with open("output/extracted_animations.txt", 'w') as f:
        f.write("# Floor 2 Area 1 - Extracted Animations\n\n")
        f.write("## Big-Viper (Slot 2)\n")
        f.write(f"table  = bytes([{', '.join(f'0x{b:02X}' for b in big_viper_table)}])\n")
        f.write(f"record = bytes([{', '.join(f'0x{b:02X}' for b in big_viper_record)}])\n")
        f.write("\n")
        f.write("## Goblin-Leader (Slot 3)\n")
        f.write(f"table  = bytes([{', '.join(f'0x{b:02X}' for b in goblin_leader_table)}])\n")
        f.write(f"record = bytes([{', '.join(f'0x{b:02X}' for b in goblin_leader_record)}])\n")

    print("Saved to: output/extracted_animations.txt")
    print()

    # Also save as Python variables
    with open("output/floor2_animations.py", 'w') as f:
        f.write("# Animation tables and records from Floor 2 Area 1\n\n")
        f.write("# Big-Viper (Slot 2)\n")
        f.write(f"BIG_VIPER_TABLE = bytes([{', '.join(f'0x{b:02X}' for b in big_viper_table)}])\n")
        f.write(f"BIG_VIPER_RECORD = bytes([{', '.join(f'0x{b:02X}' for b in big_viper_record)}])\n")
        f.write("\n")
        f.write("# Goblin-Leader (Slot 3)\n")
        f.write(f"GOBLIN_LEADER_TABLE = bytes([{', '.join(f'0x{b:02X}' for b in goblin_leader_table)}])\n")
        f.write(f"GOBLIN_LEADER_RECORD = bytes([{', '.join(f'0x{b:02X}' for b in goblin_leader_record)}])\n")

    print("Python module: output/floor2_animations.py")

else:
    print("ERROR: Not enough slots in Floor 2 Area 1")
