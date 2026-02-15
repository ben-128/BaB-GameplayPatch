#!/usr/bin/env python3
"""
Test: Add stats BUT use padding to keep script at correct calculated offset

Theory: Game calculates script_offset = stats_start + (header_count × 96)
        With header=3: script should be at stats+288

Solution: Add 2 stats BEFORE the original 3 stats, then pad to reach
          the calculated script offset
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT = Path("output/BLAZE.ALL")

CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C
CAVERN_SCRIPT = 0xF7AA9C
FORMATION_REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]
MIDDLE_COUNT_OFFSET = 0xF7A93A

print("=" * 70)
print("TEST: Stats with padding to maintain script offset")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

# Extract sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]
assignments = data[CAVERN_STATS-24:CAVERN_STATS]
stats_vanilla = data[CAVERN_STATS:CAVERN_STATS+288]  # 3 stats
script_data = data[CAVERN_SCRIPT:]  # Rest of file

print("Vanilla structure:")
print(f"  Stats @ 0x{CAVERN_STATS:X} (288 bytes)")
print(f"  Script @ 0x{CAVERN_SCRIPT:X}")
print(f"  Distance: {CAVERN_SCRIPT - CAVERN_STATS} bytes")
print()

# Create stats for Goblin-Leader and Big-Viper
def create_stats(name, level, hp):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, level, hp] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

stats_slot3 = create_stats("Goblin-Leader", 63, 200)
stats_slot4 = create_stats("Big-Viper", 5, 80)

# Strategy: Put ALL 5 stats, but game will only READ first 3
# based on header_count=3
# Slots 3,4 will be at the end and might not be read properly,
# but at least script offset will be correct

stats_new = stats_vanilla + stats_slot3 + stats_slot4  # 480 bytes total

# Calculate where script SHOULD be if game calculates it
# Game likely does: script = stats_start + (header_count × 96)
# With header=3: script = stats_start + 288
# So script should stay at same relative position!

# But we have 480 bytes of stats now, so script will actually be +192 later
# We need to either:
# A) Keep script at +288 by not including new stats in the binary stream
# B) Accept script will move and update references

# Let's try approach A: Interleave stats differently
# Put the NEW stats in the "padding" area between old slots

# Actually, let's try a different strategy:
# What if assignments control which stat to read?
# Assignment byte[5] might be stat_index+2
# So we can have 5 assignments pointing to the 3 existing stats!

print("NEW STRATEGY: 5 assignments, but only 3 stats")
print("  Slots 0,1,2 use stats 0,1,2 (vanilla)")
print("  Slots 3,4 REUSE stats 0,1 (Goblin, Shaman)")
print()

# Create assignments for 5 slots
# Slot 0: stat 0
# Slot 1: stat 1
# Slot 2: stat 2
# Slot 3: stat 0 (reuse Goblin stats) - but we'll REPLACE stat 0 with Goblin-Leader!
# Slot 4: stat 1 (reuse Shaman stats) - but we'll REPLACE stat 1 with Big-Viper!

assignment_0 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x40])  # Stat 0
assignment_1 = bytes([0x01, 0x01, 0x00, 0x00, 0x01, 0x03, 0x00, 0x40])  # Stat 1
assignment_2 = bytes([0x02, 0x03, 0x00, 0x00, 0x02, 0x04, 0x00, 0x40])  # Stat 2
assignment_3 = bytes([0x00, 0x00, 0x00, 0x00, 0x03, 0x02, 0x00, 0x40])  # Reuse stat 0
assignment_4 = bytes([0x01, 0x01, 0x00, 0x00, 0x04, 0x03, 0x00, 0x40])  # Reuse stat 1

assignments_new = assignment_0 + assignment_1 + assignment_2 + assignment_3 + assignment_4

# Replace stats 0 and 1 with our new monsters
stats_new = bytearray()
stats_new += stats_slot3  # Stat 0 = Goblin-Leader (replaces Lv20.Goblin)
stats_new += stats_slot4  # Stat 1 = Big-Viper (replaces Goblin-Shaman)
stats_new += stats_vanilla[192:]  # Stat 2 = Giant-Bat (keep vanilla)

print("Modified stats:")
print("  Stat 0: Goblin-Leader (was Lv20.Goblin)")
print("  Stat 1: Big-Viper (was Goblin-Shaman)")
print("  Stat 2: Giant-Bat (vanilla)")
print()
print("Slot assignments:")
print("  Slot 0 -> Stat 0 (Goblin-Leader)")
print("  Slot 1 -> Stat 1 (Big-Viper)")
print("  Slot 2 -> Stat 2 (Giant-Bat)")
print("  Slot 3 -> Stat 0 (Goblin-Leader, reused)")
print("  Slot 4 -> Stat 1 (Big-Viper, reused)")
print()

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05

# Rebuild
new_section = bytearray()
new_section += anim_header
new_section += anim_tables  # 3 slots
new_section += anim_records  # 3 slots
new_section += middle  # Count=5
new_section += assignments_new  # 5 assignments
new_section += stats_new  # 3 stats (same size as vanilla!)

# Stats size unchanged (288 bytes), so script offset unchanged!
print(f"Stats size: {len(stats_vanilla)} -> {len(stats_new)} bytes (UNCHANGED!)")
print(f"Script will stay at: 0x{CAVERN_SCRIPT:X}")
print()

# Write back
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Formation refs shift by +16 (only assignments added)
print("Updating formation refs (+16 bytes for assignments):")
for ref in FORMATION_REFS:
    old_offset = struct.unpack_from('<I', data, ref)[0]
    struct.pack_into('<I', data, ref, old_offset + 16)
    print(f"  0x{ref:X}: 0x{old_offset:X} -> 0x{old_offset+16:X}")

with open(OUTPUT, 'wb') as f:
    f.write(data)

print()
print("=" * 70)
print("SUCCESS!")
print()
print("Key insight: Keep stats count at 3, but:")
print("  - 5 assignments (5 slots)")
print("  - 3 stats with NEW monsters")
print("  - Slots 3,4 REUSE stats from slots 0,1")
print()
print("Expected: Should load correctly (no black level)")
print("          Slots 0,3 will both spawn Goblin-Leader")
print("          Slots 1,4 will both spawn Big-Viper")
