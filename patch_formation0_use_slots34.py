#!/usr/bin/env python3
"""
Patch Formation 0 to use slots 3 and 4

Formation 0 vanilla: 3 Goblins (slot 0)
Modified: 2× slot 3 (Goblin anims), 1× slot 4 (Shaman anims)
"""

from pathlib import Path

BLAZE = Path("output/BLAZE.ALL")
FORMATION_START = 0xF7B00C  # After slot expansion (+16 from vanilla 0xF7AFFC)

print("=" * 70)
print("Patch Formation 0 to use slots 3 and 4")
print("=" * 70)
print()

with open(BLAZE, 'rb') as f:
    data = bytearray(f.read())

print(f"Formation area @ 0x{FORMATION_START:X}")
print()

# Formation 0 starts at FORMATION_START
# Structure: offset_table, then formations
# Skip offset table to get to actual formation data

# Read offset table first
import struct
offset_table_start = FORMATION_START
entry0 = struct.unpack_from('<I', data, offset_table_start)[0]
print(f"Offset table entry[0]: 0x{entry0:X}")

# Formation data starts after offset table
# For Cavern F1 A1: 8 formations, so table is ~10 entries (entry0, 0, SP offsets, FM offsets, 0, 0)
# Skip ~40 bytes for offset table
formation_data_start = offset_table_start + 40

print(f"Formation data starts around: 0x{formation_data_start:X}")
print()

# Show current Formation 0 (first 100 bytes)
print("Current Formation 0 data (first 100 bytes):")
form0_data = data[formation_data_start:formation_data_start+100]
print(form0_data.hex(' '))
print()

# Formation records are 32 bytes each
# Vanilla Formation 0: 3 records + suffix
# Record format: prefix(4) + FFFFFFFF(4) + slot(1) + 0xFF(1) + zeros(14) + area_id(2) + FFFFFF...(6)

# Find the FFFFFFFF marker (start of first record)
marker_offset = form0_data.find(bytes([0xFF, 0xFF, 0xFF, 0xFF]))
if marker_offset == -1:
    print("ERROR: Can't find FFFFFFFF marker!")
    exit(1)

print(f"Found FFFFFFFF at offset +{marker_offset} from formation data start")
first_record_start = formation_data_start + marker_offset - 4  # -4 for prefix
print(f"First record starts at: 0x{first_record_start:X}")
print()

# Patch the 3 records to use slots 3, 3, 4
# Record structure:
#   byte[0:4] = prefix
#   byte[4:8] = FFFFFFFF (first record only)
#   byte[8] = slot index
#   byte[9] = 0xFF
#   byte[10:24] = zeros
#   byte[24:26] = area_id
#   byte[26:32] = FFFFFFFFFFFF

# Record 0: slot 3
record0_offset = first_record_start
data[record0_offset + 8] = 0x03  # Change slot 0 -> 3
print(f"Record 0 @ 0x{record0_offset:X}: slot 0 -> 3")

# Record 1: slot 3
record1_offset = record0_offset + 32
data[record1_offset + 8] = 0x03  # Change slot 0 -> 3
print(f"Record 1 @ 0x{record1_offset:X}: slot 0 -> 3")

# Record 2: slot 4
record2_offset = record1_offset + 32
data[record2_offset + 8] = 0x04  # Change slot 0 -> 4
print(f"Record 2 @ 0x{record2_offset:X}: slot 0 -> 4")

print()
print("Modified Formation 0:")
print(data[first_record_start:first_record_start+100].hex(' '))

# Save
with open(BLAZE, 'wb') as f:
    f.write(data)

print()
print("=" * 70)
print("SUCCESS! Formation 0 now uses slots 3, 3, 4")
print("=" * 70)
