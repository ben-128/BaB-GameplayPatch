#!/usr/bin/env python3
"""
Clone Forest F1 A2 structure to Cavern F1 A1

Instead of trying to reconstruct the structure, we copy the ENTIRE
working structure from Forest (5 monsters vanilla) and adapt it for Cavern.

This will help us identify what exactly is different/broken.
"""

import struct
import shutil
from pathlib import Path

BLAZE_ALL = Path("output/BLAZE.ALL")
BACKUP = Path("output/BLAZE.ALL.backup")

# Forest F1 A2 (5 monsters vanilla - SOURCE)
FOREST_ANIM = 0x1490900
FOREST_STATS = 0x14909B0

# Cavern F1 A1 (3 monsters vanilla -> 5 monsters TARGET)
CAVERN_ANIM = 0xF7A900
CAVERN_STATS_ORIG = 0xF7A97C

# Structure sizes for 5 monsters
ANIM_HEADER = 8
ANIM_TABLES = 40  # 5 × 8
ANIM_RECORDS = 40  # 5 × 8
MIDDLE = 48
ASSIGNMENTS = 40  # 5 × 8
STATS = 480  # 5 × 96

TOTAL_MONSTER_SECTION = ANIM_HEADER + ANIM_TABLES + ANIM_RECORDS + MIDDLE + ASSIGNMENTS + STATS

print("=" * 70)
print("CLONE FOREST STRUCTURE TO CAVERN")
print("=" * 70)
print()

# Load files
with open(BACKUP, 'rb') as f:
    vanilla = bytearray(f.read())

print(f"[OK] Loaded vanilla backup")
print()

# Extract Forest structure (everything for 5 monsters)
forest_structure = vanilla[FOREST_ANIM:FOREST_ANIM + TOTAL_MONSTER_SECTION]

print("Forest structure extracted:")
print(f"  Anim header:   {ANIM_HEADER} bytes")
print(f"  Anim tables:   {ANIM_TABLES} bytes")
print(f"  Anim records:  {ANIM_RECORDS} bytes")
print(f"  Middle:        {MIDDLE} bytes")
print(f"  Assignments:   {ASSIGNMENTS} bytes")
print(f"  Stats:         {STATS} bytes")
print(f"  TOTAL:         {len(forest_structure)} bytes")
print()

# Extract Cavern stats (to preserve monster-specific data)
cavern_stats_orig = vanilla[CAVERN_STATS_ORIG:CAVERN_STATS_ORIG + 288]  # 3 × 96

print("Cavern original stats (3 monsters):")
for i in range(3):
    name = cavern_stats_orig[i*96:i*96+16].rstrip(b'\x00').decode('ascii', errors='ignore')
    print(f"  Slot {i}: {name}")
print()

# Build new Cavern structure
new_cavern = bytearray(forest_structure)

# Replace stats section with Cavern monsters (keep first 3, add 2 placeholders)
stats_offset = ANIM_HEADER + ANIM_TABLES + ANIM_RECORDS + MIDDLE + ASSIGNMENTS

# Copy Cavern's 3 monsters
new_cavern[stats_offset:stats_offset+288] = cavern_stats_orig

# Add 2 placeholder monsters
for i in range(2):
    slot_offset = stats_offset + 288 + i*96
    name = f"NewSlot{i+1}".encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, 1, 50] + [0]*37
    stats_bytes = name + b''.join(struct.pack('<H', v) for v in stats)
    new_cavern[slot_offset:slot_offset+96] = stats_bytes

print("New Cavern structure:")
print(f"  Slot 0-2: Original Cavern monsters")
print(f"  Slot 3-4: Placeholders (NewSlot1, NewSlot2)")
print()

# Copy to BLAZE.ALL
data = bytearray(vanilla)
data[CAVERN_ANIM:CAVERN_ANIM + len(new_cavern)] = new_cavern

# But wait! This changes the size of the zone!
# We need to adjust everything after...
# Actually, let's calculate the size difference

old_cavern_size = CAVERN_STATS_ORIG - CAVERN_ANIM + 288  # Original 3 monsters
new_cavern_size = len(new_cavern)
size_diff = new_cavern_size - old_cavern_size

print(f"Size difference: {size_diff} bytes")
print()

if size_diff != 0:
    print("[WARNING] Cloning changes zone size!")
    print("This approach won't work without shifting everything after.")
    print()
    print("Alternative: We need to understand and REBUILD the structure,")
    print("not just clone it.")
    exit(1)

# Save
backup_clone = BLAZE_ALL.with_suffix('.ALL.backup_clone')
shutil.copy2(BLAZE_ALL, backup_clone)

with open(BLAZE_ALL, 'wb') as f:
    f.write(data)

print(f"[SAVED] {BLAZE_ALL.name}")
print(f"[BACKUP] {backup_clone.name}")
