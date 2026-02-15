#!/usr/bin/env python3
"""
Manually update the offset table based on formation patcher logic

The offset table contains RELATIVE offsets from a base within the script/formation area.
When we shift formations, we need to understand if these offsets are:
A) Relative to script start (need updating)
B) Relative to formation start (don't need updating)
"""

import struct
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
CURRENT = Path("output/BLAZE.ALL")

# Offsets in the MODIFIED file
SCRIPT_START_NEW = 0xF7AB6C  # After +208 shift
FORMATION_START_NEW = 0xF7B0CC  # After +208 shift

# Offsets in vanilla
SCRIPT_START_OLD = 0xF7AA9C
FORMATION_START_OLD = 0xF7AFFC

SHIFT = 208

print("=" * 70)
print("DEBUG: Vérification de la structure")
print("=" * 70)
print()

# First, let's check if our modified file is correct
with open(CURRENT, 'rb') as f:
    data = f.read()

print(f"Fichier modifié: {len(data):,} bytes")
print()

# Check what's at the old vs new script positions
print("Vérification des positions:")
print(f"  Script old @ 0x{SCRIPT_START_OLD:X}:")
old_script = data[SCRIPT_START_OLD:SCRIPT_START_OLD+16]
print(f"    {old_script.hex(' ')}")

print(f"  Script new @ 0x{SCRIPT_START_NEW:X}:")
new_script = data[SCRIPT_START_NEW:SCRIPT_START_NEW+16]
print(f"    {new_script.hex(' ')}")
print()

# The script data should have MOVED from old to new position
# So new position should have the offset table
# Let's check the offset table at new position

print("Table d'offsets au NOUVEAU script start:")
for i in range(0, 40, 4):
    val = struct.unpack_from('<I', data, SCRIPT_START_NEW + i)[0]
    print(f"  Entry {i//4:2d} @ +0x{i:02X}: 0x{val:08X} ({val})")
    if val == 0 and i > 4:
        next_val = struct.unpack_from('<I', data, SCRIPT_START_NEW + i + 4)[0]
        if next_val == 0:
            print("  (two zeros - end of table)")
            break

print()

# Now check formation start
print(f"Formation start @ 0x{FORMATION_START_NEW:X}:")
formation_data = data[FORMATION_START_NEW:FORMATION_START_NEW+32]
print(f"  {formation_data.hex(' ')}")

# Check if this looks like formation data (should have area_id dc01)
if b'\xdc\x01' in formation_data:
    print("  ✓ Area ID dc01 found - looks correct!")
else:
    print("  ✗ Area ID dc01 NOT found - wrong position?")

print()

# The real question: did our script copying work correctly?
# Let's compare the script at new position with vanilla script
with open(BACKUP, 'rb') as f:
    backup = f.read()

vanilla_script = backup[SCRIPT_START_OLD:SCRIPT_START_OLD+100]
current_script = data[SCRIPT_START_NEW:SCRIPT_START_NEW+100]

if vanilla_script == current_script:
    print("✓ Script data copied correctly to new position")
else:
    print("✗ Script data DIFFERENT - copy problem!")
    print()
    print("Vanilla script (first 32 bytes):")
    print(vanilla_script[:32].hex(' '))
    print()
    print("Current script at new position (first 32 bytes):")
    print(current_script[:32].hex(' '))
