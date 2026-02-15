#!/usr/bin/env python3
"""
Test adding slots with HEADER COUNT = 3 (not 5)

Since changing header count causes infinite loading, keep it at 3
and test if we can add structural changes.
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT_DIR = Path("output/test_versions")
OUTPUT_DIR.mkdir(exist_ok=True)

# Offsets
HEADER_COUNT = 0xF7A851  # KEEP THIS AT 3!
CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]

def load_vanilla():
    with open(BACKUP, 'rb') as f:
        return bytearray(f.read())

def save_test(data, name):
    output = OUTPUT_DIR / f"{name}.ALL"
    with open(output, 'wb') as f:
        f.write(data)
    print(f"  Created: {output.name}")

print("=" * 70)
print("TEST: Add slots with HEADER COUNT = 3")
print("=" * 70)
print()

# ============================================================================
# TEST A: Middle count = 5 ONLY (baseline - should work)
# ============================================================================
print("[TEST A] Middle count = 5, Header = 3 (baseline)")
data = load_vanilla()
data[CAVERN_ANIM + 56 + 2] = 0x05  # Middle count = 5
# Header stays at 3
save_test(data, "testA_middle5_header3_baseline")
print("  Changes: Middle=5, Header=3 (no structure)")
print("  Expected: WORKS (we know this works)")
print()

# ============================================================================
# TEST B: Middle = 5, Header = 3, Add STATS only
# ============================================================================
print("[TEST B] Middle=5, Header=3, Add stats")
data = load_vanilla()

# Extract sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments = data[CAVERN_STATS-24:CAVERN_STATS]
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]

# Create new stats
def create_stats(name):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, 1, 50] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

stats_new = stats_old + create_stats("NewSlot1") + create_stats("NewSlot2")

# Rebuild
middle = bytearray(middle)
middle[2] = 0x05  # Middle count = 5

new_section = bytearray()
new_section += anim_header
new_section += anim_tables  # Still 3 slots
new_section += anim_records  # Still 3 slots
new_section += middle  # Count=5 but size=44
new_section += assignments  # Still 3 slots
new_section += stats_new  # 5 slots!

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Update formation refs (+192)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 192)

save_test(data, "testB_middle5_header3_add_stats")
print("  Changes: Middle=5, Header=3, Stats 288->480")
print("  Expected: Unknown - tests if stats alone causes crash")
print()

# ============================================================================
# TEST C: Middle = 5, Header = 3, Add ASSIGNMENTS only
# ============================================================================
print("[TEST C] Middle=5, Header=3, Add assignments")
data = load_vanilla()

# Extract sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]
stats = data[CAVERN_STATS:CAVERN_STATS+288]

# Add assignments
new_assignment = bytes([0x03, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])
assignments_new = assignments_old + new_assignment * 2

# Rebuild
middle = bytearray(middle)
middle[2] = 0x05

new_section = bytearray()
new_section += anim_header
new_section += anim_tables  # Still 3 slots
new_section += anim_records  # Still 3 slots
new_section += middle
new_section += assignments_new  # 5 slots!
new_section += stats  # Still 3 slots

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Update formation refs (+16)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 16)

save_test(data, "testC_middle5_header3_add_assignments")
print("  Changes: Middle=5, Header=3, Assignments 24->40")
print("  Expected: Unknown")
print()

# ============================================================================
# TEST D: Middle = 5, Header = 3, Add ANIM TABLES only
# ============================================================================
print("[TEST D] Middle=5, Header=3, Add anim tables")
data = load_vanilla()

# Extract sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables_old = data[CAVERN_ANIM+8:CAVERN_ANIM+32]
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments = data[CAVERN_STATS-24:CAVERN_STATS]
stats = data[CAVERN_STATS:CAVERN_STATS+288]

# Add anim tables
new_table = anim_tables_old[0:8]
anim_tables_new = anim_tables_old + new_table * 2

# Rebuild
middle = bytearray(middle)
middle[2] = 0x05

new_section = bytearray()
new_section += anim_header
new_section += anim_tables_new  # 5 slots!
new_section += anim_records  # Still 3 slots
new_section += middle
new_section += assignments  # Still 3 slots
new_section += stats  # Still 3 slots

# Update middle position
middle_offset = 8 + 40 + 24
new_section[middle_offset + 2] = 0x05

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Update formation refs (+16)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 16)

save_test(data, "testD_middle5_header3_add_anim_tables")
print("  Changes: Middle=5, Header=3, Anim tables 24->40")
print("  Expected: Unknown")
print()

print("=" * 70)
print("Created 4 tests with HEADER = 3")
print()
print("TEST ORDER:")
print("  A. Baseline (middle=5, header=3, no structure)")
print("  B. Add stats only")
print("  C. Add assignments only")
print("  D. Add anim tables only")
