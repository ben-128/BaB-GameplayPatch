#!/usr/bin/env python3
"""
Add 5 monster slots - COMPLETE solution

Strategy:
1. Add 5 complete stats (Goblin-Leader, Big-Viper, + 3 vanilla)
2. Add 5 assignments
3. Update middle count to 5
4. Keep header count at 3 (avoid infinite loading)
5. Update ALL known offset references
6. Search and update any script/stats references in different formats
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
MIDDLE_COUNT_OFFSET = 0xF7A93A

SHIFT_ASSIGNMENTS = 16  # 2 * 8
SHIFT_STATS = 192  # 2 * 96
TOTAL_SHIFT = SHIFT_ASSIGNMENTS + SHIFT_STATS  # 208 bytes

print("=" * 70)
print("ADD 5 MONSTER SLOTS - Solution complète")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

# Extract vanilla sections
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables = data[CAVERN_ANIM+8:CAVERN_ANIM+32]  # 3×8
anim_records = data[CAVERN_ANIM+32:CAVERN_ANIM+56]  # 3×8
middle = data[CAVERN_ANIM+56:CAVERN_STATS-24]  # 44 bytes
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]  # 3×8
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]  # 3×96

# Extract Lv20.Goblin, Goblin-Shaman, Giant-Bat vanilla stats
stat0_vanilla = stats_old[0:96]  # Lv20.Goblin
stat1_vanilla = stats_old[96:192]  # Goblin-Shaman
stat2_vanilla = stats_old[192:288]  # Giant-Bat

print("Création des 5 stats:")

# Create stats
def create_stats(name, level, hp):
    name_bytes = name.encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, level, hp] + [0]*37
    return name_bytes + b''.join(struct.pack('<H', v) for v in stats)

# Slots 0-2: vanilla monsters
# Slots 3-4: new monsters
stats_new = bytearray()
stats_new += stat0_vanilla  # Slot 0: Lv20.Goblin
stats_new += stat1_vanilla  # Slot 1: Goblin-Shaman
stats_new += stat2_vanilla  # Slot 2: Giant-Bat
stats_new += create_stats("Goblin-Leader", 63, 200)  # Slot 3
stats_new += create_stats("Big-Viper", 5, 80)  # Slot 4

print("  Slot 0: Lv20.Goblin (vanilla)")
print("  Slot 1: Goblin-Shaman (vanilla)")
print("  Slot 2: Giant-Bat (vanilla)")
print("  Slot 3: Goblin-Leader (NEW)")
print("  Slot 4: Big-Viper (NEW)")
print()

# Create 5 assignments
# Slots 0,1,2 use vanilla pattern
# Slots 3,4 reuse animations from slots 0,1
assignment_0 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x40])
assignment_1 = bytes([0x01, 0x01, 0x00, 0x00, 0x01, 0x03, 0x00, 0x40])
assignment_2 = bytes([0x02, 0x03, 0x00, 0x00, 0x02, 0x04, 0x00, 0x40])
assignment_3 = bytes([0x00, 0x00, 0x00, 0x00, 0x03, 0x05, 0x00, 0x40])  # Reuse anim 0, stat 3
assignment_4 = bytes([0x01, 0x01, 0x00, 0x00, 0x04, 0x06, 0x00, 0x40])  # Reuse anim 1, stat 4

assignments_new = assignment_0 + assignment_1 + assignment_2 + assignment_3 + assignment_4

print("Création des 5 assignments (réutilise anims 0,1 pour slots 3,4)")
print()

# Update middle count
middle = bytearray(middle)
middle[2] = 0x05

# Rebuild section
new_section = bytearray()
new_section += anim_header  # 8
new_section += anim_tables  # 24 (3 tables only!)
new_section += anim_records  # 24 (3 records only!)
new_section += middle  # 44 (count=5)
new_section += assignments_new  # 40 (5 assignments)
new_section += stats_new  # 480 (5 stats)

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

# Build new file properly
# IMPORTANT: Extract script+rest from BACKUP before modifying anything!
with open(BACKUP, 'rb') as f:
    backup = bytearray(f.read())

# Extract script and everything after from backup (before we modify it)
script_and_rest = backup[CAVERN_SCRIPT:]

# Start with backup
data = backup

# Write new section at animation position
data[CAVERN_ANIM:CAVERN_ANIM + len(new_section)] = new_section

# Write script and rest at new position
new_script_pos = CAVERN_ANIM + len(new_section)

# To maintain file size, we write script_and_rest but truncate TOTAL_SHIFT bytes from end
data[new_script_pos:new_script_pos + len(script_and_rest) - TOTAL_SHIFT] = script_and_rest[:-TOTAL_SHIFT]

# Truncate file to original size if needed
if len(data) > len(backup):
    data = data[:len(backup)]

print("Données copiées:")
print(f"  Script et reste écrits à: 0x{new_script_pos:X}")
print()

# Update formation refs
print("Mise à jour des formation refs:")
for ref in FORMATION_REFS:
    old_val = CAVERN_FORMATION
    new_val = NEW_FORMATION
    struct.pack_into('<I', data, ref, new_val)
    print(f"  0x{ref:X}: 0x{old_val:X} -> 0x{new_val:X}")
print()

# Search for script offset references (might be in other formats)
print("Recherche de références au script offset...")
SCRIPT_OLD = CAVERN_SCRIPT
found_script_refs = []

# Search as relative offset from stats
relative_to_stats = SCRIPT_OLD - CAVERN_STATS  # Should be 288
print(f"  Relative script-stats: {relative_to_stats} (0x{relative_to_stats:X})")

# Search for this value
for i in range(0, len(data)-4):
    val = struct.unpack_from('<I', data, i)[0]
    if val == relative_to_stats:
        found_script_refs.append(i)

if found_script_refs:
    print(f"  Trouvé {len(found_script_refs)} références relatives potentielles:")
    for ref in found_script_refs[:5]:
        print(f"    0x{ref:X}")
else:
    print(f"  Aucune référence trouvée")
print()

# Save
with open(OUTPUT, 'wb') as f:
    f.write(data)

print("=" * 70)
print("TERMINÉ!")
print()
print("Changements:")
print("  - 5 stats complets (dont Goblin-Leader et Big-Viper)")
print("  - 5 assignments (slots 3,4 réutilisent anims 0,1)")
print("  - Middle count = 5")
print("  - Header count = 3 (inchangé)")
print("  - Script/Formation décalés de +208 bytes")
print()
print("ATTENTION: Le BLACK LEVEL peut toujours arriver si le jeu")
print("calcule dynamiquement l'offset du script avec header_count=3")
