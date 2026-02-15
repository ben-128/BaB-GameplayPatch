#!/usr/bin/env python3
"""
Incremental Testing - Isolate Crash Cause

Creates multiple test versions with progressively more changes.
Run each test in-game to identify which change causes the crash.
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT_DIR = Path("output/test_versions")
OUTPUT_DIR.mkdir(exist_ok=True)

# Offsets
HEADER_COUNT = 0xF7A851
CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
CAVERN_SCRIPT = 0xF7AA9C
FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]

def load_vanilla():
    """Load vanilla data"""
    with open(BACKUP, 'rb') as f:
        return bytearray(f.read())

def save_test(data, test_name):
    """Save test version"""
    output = OUTPUT_DIR / f"{test_name}.ALL"
    with open(output, 'wb') as f:
        f.write(data)
    print(f"  Created: {output.name}")

def extract_sections(data):
    """Extract all sections for reconstruction"""
    return {
        'anim_header': data[CAVERN_ANIM:CAVERN_ANIM+8],
        'anim_tables': data[CAVERN_ANIM+8:CAVERN_ANIM+32],  # 3×8
        'anim_records': data[CAVERN_ANIM+32:CAVERN_ANIM+56],  # 3×8
        'middle': data[CAVERN_ANIM+56:CAVERN_STATS-24],  # 44 bytes
        'assignments': data[CAVERN_STATS-24:CAVERN_STATS],  # 3×8
        'stats': data[CAVERN_STATS:CAVERN_STATS+288],  # 3×96
        'script': data[CAVERN_SCRIPT:CAVERN_SCRIPT+1376],
    }

print("=" * 70)
print("INCREMENTAL TESTING - Isolate Crash Cause")
print("=" * 70)
print()

# ============================================================================
# TEST 1: Change BOTH monster counts ONLY (no structure changes)
# ============================================================================
print("[TEST 1] Change both monster counts only (no structure)")
data = load_vanilla()
data[HEADER_COUNT] = 0x05  # Header
data[CAVERN_ANIM + 56 + 2] = 0x05  # Middle section byte[2]
save_test(data, "test1_counts_only")
print("  Changes: Header count=5, Middle count=5")
print("  Expected: Should work (we tested middle count=5 alone before)")
print()

# ============================================================================
# TEST 2: Change counts + expand middle section ONLY
# ============================================================================
print("[TEST 2] Change counts + expand middle section")
data = load_vanilla()
sections = extract_sections(data)

# Expand middle section (insert 4 bytes after first 8)
middle_new = bytearray(sections['middle'][:8] + bytes([0, 0, 0, 0]) + sections['middle'][8:])
middle_new[2] = 0x05  # Update count

# Rebuild just the middle section area
new_section = bytearray()
new_section += sections['anim_header']
new_section += sections['anim_tables']
new_section += sections['anim_records']
new_section += middle_new  # 48 bytes now
new_section += sections['assignments']
new_section += sections['stats']

# Write back (this shifts everything after by +4 bytes)
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section
data[HEADER_COUNT] = 0x05

# Update formation refs (+4 bytes shift)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 4)

save_test(data, "test2_counts_middle_expanded")
print("  Changes: Counts=5, Middle 44->48 bytes, Formation refs +4")
print("  Expected: May crash (we know middle expansion caused crash before)")
print()

# ============================================================================
# TEST 3: Counts + add animation TABLES only
# ============================================================================
print("[TEST 3] Counts + add animation tables only")
data = load_vanilla()
sections = extract_sections(data)

# Add 2 animation tables (copy slot 0)
new_anim_table = sections['anim_tables'][0:8]
tables_expanded = sections['anim_tables'] + new_anim_table * 2  # 40 bytes

# Rebuild
new_section = bytearray()
new_section += sections['anim_header']
new_section += tables_expanded  # 40 bytes (3+2 slots)
new_section += sections['anim_records']  # Still 24 bytes (3 slots)
new_section += sections['middle']  # Still 44 bytes
new_section += sections['assignments']  # Still 24 bytes
new_section += sections['stats']  # Still 288 bytes

# Update counts
middle_offset = 8 + 40 + 24  # New middle position
new_section[middle_offset + 2] = 0x05

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section
data[HEADER_COUNT] = 0x05

# Update formation refs (+16 bytes shift)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 16)

save_test(data, "test3_counts_anim_tables")
print("  Changes: Counts=5, Anim tables 24->40 bytes, Formation refs +16")
print("  Expected: Unknown - tests if anim tables can be added")
print()

# ============================================================================
# TEST 4: Counts + add animation RECORDS only
# ============================================================================
print("[TEST 4] Counts + add animation records only")
data = load_vanilla()
sections = extract_sections(data)

# Add 2 animation records (copy slot 0)
new_anim_record = sections['anim_records'][0:8]
records_expanded = sections['anim_records'] + new_anim_record * 2  # 40 bytes

# Rebuild
new_section = bytearray()
new_section += sections['anim_header']
new_section += sections['anim_tables']  # Still 24 bytes
new_section += records_expanded  # 40 bytes (3+2 slots)
new_section += sections['middle']  # Still 44 bytes
new_section += sections['assignments']  # Still 24 bytes
new_section += sections['stats']  # Still 288 bytes

# Update counts
middle_offset = 8 + 24 + 40  # New middle position
new_section[middle_offset + 2] = 0x05

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section
data[HEADER_COUNT] = 0x05

# Update formation refs (+16 bytes shift)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 16)

save_test(data, "test4_counts_anim_records")
print("  Changes: Counts=5, Anim records 24->40 bytes, Formation refs +16")
print("  Expected: Unknown - tests if anim records can be added")
print()

# ============================================================================
# TEST 5: Counts + add ASSIGNMENTS only
# ============================================================================
print("[TEST 5] Counts + add assignments only")
data = load_vanilla()
sections = extract_sections(data)

# Add 2 assignments (using pattern from vanilla)
new_assignment = bytes([0x03, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])
assignments_expanded = sections['assignments'] + new_assignment * 2  # 40 bytes

# Rebuild
new_section = bytearray()
new_section += sections['anim_header']
new_section += sections['anim_tables']  # Still 24 bytes
new_section += sections['anim_records']  # Still 24 bytes
new_section += sections['middle']  # Still 44 bytes
new_section += assignments_expanded  # 40 bytes (3+2 slots)
new_section += sections['stats']  # Still 288 bytes

# Update counts
new_section[56 + 2] = 0x05  # Middle byte[2]

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section
data[HEADER_COUNT] = 0x05

# Update formation refs (+16 bytes shift)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 16)

save_test(data, "test5_counts_assignments")
print("  Changes: Counts=5, Assignments 24->40 bytes, Formation refs +16")
print("  Expected: Unknown - tests if assignments can be added")
print()

# ============================================================================
# TEST 6: Counts + add STATS only
# ============================================================================
print("[TEST 6] Counts + add stats only")
data = load_vanilla()
sections = extract_sections(data)

# Add 2 stat blocks
def create_stats(slot_name):
    name = slot_name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, 1, 50] + [0]*37
    return name + b''.join(struct.pack('<H', v) for v in stats)

stats_expanded = sections['stats'] + create_stats("NewSlot1") + create_stats("NewSlot2")  # 480 bytes

# Rebuild
new_section = bytearray()
new_section += sections['anim_header']
new_section += sections['anim_tables']  # Still 24 bytes
new_section += sections['anim_records']  # Still 24 bytes
new_section += sections['middle']  # Still 44 bytes
new_section += sections['assignments']  # Still 24 bytes
new_section += stats_expanded  # 480 bytes (3+2 slots)

# Update counts
new_section[56 + 2] = 0x05  # Middle byte[2]

data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section
data[HEADER_COUNT] = 0x05

# Update formation refs (+192 bytes shift)
for ref in FORMATION_REFS:
    old_val = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_val + 192)

save_test(data, "test6_counts_stats")
print("  Changes: Counts=5, Stats 288->480 bytes, Formation refs +192")
print("  Expected: Unknown - tests if stats can be added")
print()

# ============================================================================
# TEST 7: Counts + ONLY header count (no middle count)
# ============================================================================
print("[TEST 7] Change header count only (not middle)")
data = load_vanilla()
data[HEADER_COUNT] = 0x05  # Header only
# Do NOT change middle section count
save_test(data, "test7_header_count_only")
print("  Changes: Header count=5 (middle stays 3)")
print("  Expected: Test if header count matters alone")
print()

print("=" * 70)
print(f"Created 7 test versions in {OUTPUT_DIR}/")
print()
print("TEST ORDER (recommended):")
print("  1. test1_counts_only           - Baseline (both counts, no structure)")
print("  2. test7_header_count_only     - Isolate header count")
print("  3. test2_counts_middle_expanded - Test middle section expansion")
print("  4. test3_counts_anim_tables    - Test adding anim tables")
print("  5. test4_counts_anim_records   - Test adding anim records")
print("  6. test5_counts_assignments    - Test adding assignments")
print("  7. test6_counts_stats          - Test adding stats")
print()
print("For each test:")
print("  1. cp output/test_versions/testX*.ALL output/BLAZE.ALL")
print("  2. cp output/BLAZE.ALL 'Blaze  Blade.../extract/'")
print("  3. python patch_blaze_all.py")
print("  4. Test in-game")
print("  5. Report: WORKS or CRASH")
