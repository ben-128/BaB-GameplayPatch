#!/usr/bin/env python3
"""
Add 5 monster slots - COMPLETE solution with animation tables

DIFFERENCE from add_5_slots_complete.py:
  - This script ADDS 2 animation tables (for slots 3-4)
  - Sets header_count = 5 (so game loads all 5 tables)
  - Slots 3-4 will REUSE animation data from slots 0-1 (Goblin, Shaman)
  - But they'll have their own stats (Goblin-Leader, Big-Viper)

Structure:
  - 5 animation tables (tables 3-4 duplicate tables 0-1)
  - 5 animation records (records 3-4 duplicate records 0-1)
  - 5 assignments
  - 5 stats
  - header_count = 5
  - middle_count = 5
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
HEADER_COUNT_OFFSET = 0xF7A851
MIDDLE_COUNT_OFFSET = 0xF7A93A

# New: we're adding 2 anim tables + 2 anim records
SHIFT_ANIM = 16  # 2 tables (8 bytes each)
SHIFT_RECORDS = 16  # 2 records (8 bytes each)
SHIFT_ASSIGNMENTS = 16  # 2 assignments (8 bytes each)
SHIFT_STATS = 192  # 2 stats (96 bytes each)
TOTAL_SHIFT = SHIFT_ANIM + SHIFT_RECORDS + SHIFT_ASSIGNMENTS + SHIFT_STATS  # 240 bytes

print("=" * 70)
print("ADD 5 MONSTER SLOTS - With Animation Tables")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

# Extract vanilla sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables_old = data[CAVERN_ANIM+8:CAVERN_ANIM+32]  # 3×8
anim_records_old = data[CAVERN_ANIM+32:CAVERN_ANIM+56]  # 3×8
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]  # 44 bytes
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]  # 3×8
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]  # 3×96

# Extract individual vanilla elements
table0 = anim_tables_old[0:8]   # Goblin table
table1 = anim_tables_old[8:16]  # Shaman table
table2 = anim_tables_old[16:24] # Bat table

record0 = anim_records_old[0:8]   # Goblin record
record1 = anim_records_old[8:16]  # Shaman record
record2 = anim_records_old[16:24] # Bat record

stat0 = stats_old[0:96]   # Goblin
stat1 = stats_old[96:192] # Shaman
stat2 = stats_old[192:288] # Bat

print("Creating 5 animation tables:")
print("  Slot 0: Goblin (vanilla)")
print("  Slot 1: Shaman (vanilla)")
print("  Slot 2: Bat (vanilla)")
print("  Slot 3: Goblin (DUPLICATE of slot 0)")
print("  Slot 4: Shaman (DUPLICATE of slot 1)")
print()

# Create 5 animation tables (duplicate 0 and 1 for slots 3 and 4)
anim_tables_new = bytearray()
anim_tables_new += table0  # Slot 0
anim_tables_new += table1  # Slot 1
anim_tables_new += table2  # Slot 2
anim_tables_new += table0  # Slot 3 (reuse Goblin animation)
anim_tables_new += table1  # Slot 4 (reuse Shaman animation)

# Create 5 animation records (duplicate 0 and 1 for slots 3 and 4)
anim_records_new = bytearray()
anim_records_new += record0  # Slot 0
anim_records_new += record1  # Slot 1
anim_records_new += record2  # Slot 2
anim_records_new += record0  # Slot 3 (reuse Goblin record)
anim_records_new += record1  # Slot 4 (reuse Shaman record)

print("Creating 5 stats:")

# Create stats
def create_stats(name, level, hp):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, level, hp] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

stats_new = bytearray()
stats_new += stat0  # Slot 0: Goblin (vanilla)
stats_new += stat1  # Slot 1: Shaman (vanilla)
stats_new += stat2  # Slot 2: Bat (vanilla)
stats_new += create_stats("Goblin-Leader", 63, 200)  # Slot 3: NEW
stats_new += create_stats("Big-Viper", 5, 80)  # Slot 4: NEW

print("  Slot 0: Lv20.Goblin (vanilla)")
print("  Slot 1: Goblin-Shaman (vanilla)")
print("  Slot 2: Giant-Bat (vanilla)")
print("  Slot 3: Goblin-Leader (NEW, level 63)")
print("  Slot 4: Big-Viper (NEW, level 5)")
print()

# Create 5 assignments
# Slots 0-2: vanilla pattern
# Slots 3-4: use anim indices 3,4 (which duplicate 0,1) with new stat indices
assignment_0 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x40])
assignment_1 = bytes([0x01, 0x01, 0x00, 0x00, 0x01, 0x03, 0x00, 0x40])
assignment_2 = bytes([0x02, 0x03, 0x00, 0x00, 0x02, 0x04, 0x00, 0x40])
assignment_3 = bytes([0x03, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])  # Anim 3, stat 3
assignment_4 = bytes([0x04, 0x01, 0x00, 0x00, 0x04, 0x06, 0x00, 0x40])  # Anim 4, stat 4

assignments_new = assignment_0 + assignment_1 + assignment_2 + assignment_3 + assignment_4

print("Creating 5 assignments (link animations to stats)")
print()

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05

# Rebuild section
new_section = bytearray()
new_section += anim_header        # 8
new_section += anim_tables_new    # 40 (5 tables!)
new_section += anim_records_new   # 40 (5 records!)
new_section += middle             # 44 (count=5)
new_section += assignments_new    # 40 (5 assignments)
new_section += stats_new          # 480 (5 stats)

print(f"Section totale: {len(new_section)} bytes")
print(f"  Shift total: +{TOTAL_SHIFT} bytes")
print()

# Calculate new offsets
NEW_SCRIPT = CAVERN_SCRIPT + TOTAL_SHIFT
NEW_FORMATION = CAVERN_FORMATION + TOTAL_SHIFT

print("Nouveaux offsets:")
print(f"  Script:    0x{CAVERN_SCRIPT:X} -> 0x{NEW_SCRIPT:X}")
print(f"  Formation: 0x{CAVERN_FORMATION:X} -> 0x{NEW_FORMATION:X}")
print()

# Build new file
with open(BACKUP, 'rb') as f:
    backup = bytearray(f.read())

# Extract script and rest from backup
script_and_rest = backup[CAVERN_SCRIPT:]

# Start with backup
data = backup

# Write new section at animation position
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Write script and rest at new position, truncating TOTAL_SHIFT from end
new_script_pos = CAVERN_ANIM + len(new_section)
data[new_script_pos:new_script_pos + len(script_and_rest) - TOTAL_SHIFT] = script_and_rest[:-TOTAL_SHIFT]

# Truncate to original size
if len(data) > len(backup):
    data = data[:len(backup)]

print("Données copiées")
print()

# Update formation refs
print("Mise à jour des formation refs:")
for ref in FORMATION_REFS:
    struct.pack_into('<I', data, ref, NEW_FORMATION)
    print(f"  0x{ref:X}: 0x{CAVERN_FORMATION:X} -> 0x{NEW_FORMATION:X}")
print()

# Update header count to 5
print("Mise à jour du header count:")
print(f"  0x{HEADER_COUNT_OFFSET:X}: {data[HEADER_COUNT_OFFSET]} -> 5")
data[HEADER_COUNT_OFFSET] = 0x05
print()

# Save
with open(OUTPUT, 'wb') as f:
    f.write(data)

print("=" * 70)
print("TERMINE!")
print("=" * 70)
print()
print("Changements:")
print("  - 5 animation tables (slots 3-4 dupliquent 0-1)")
print("  - 5 animation records (slots 3-4 dupliquent 0-1)")
print("  - 5 stats (Goblin-Leader, Big-Viper)")
print("  - 5 assignments")
print("  - header_count = 5")
print("  - middle_count = 5")
print()
print("Slots 3-4 utilisent les MEMES animations que slots 0-1")
print("mais avec des stats DIFFERENTES (nom, level, HP)")
print()
print("Test maintenant - devrait charger sans infinite loading!")
