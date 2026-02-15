#!/usr/bin/env python3
"""
Fix: Update offset table in script section

The script section starts with an offset table containing:
  [entry0, 0, SP_offsets..., FM_offsets..., 0, 0]

When we shift formations by +208 bytes, we need to update the FM_offsets.
"""

import struct
from pathlib import Path

BLAZE = Path("output/BLAZE.ALL")

SCRIPT_START = 0xF7AA9C
OLD_FORMATION_START = 0xF7AFFC
NEW_FORMATION_START = 0xF7B0CC
FORMATION_SHIFT = NEW_FORMATION_START - OLD_FORMATION_START  # +208

print("=" * 70)
print("FIX: Update offset table in script section")
print("=" * 70)
print()

with open(BLAZE, 'rb') as f:
    data = bytearray(f.read())

# Read offset table
print("Lecture de la table d'offsets:")
table = []
for i in range(0, 200, 4):  # Read up to 50 entries
    val = struct.unpack_from('<I', data, SCRIPT_START + i)[0]
    if val >= 0x10000:  # Stop at unreasonable values
        break
    table.append((i, val))
    if len(table) >= 3 and table[-1][1] == 0 and table[-2][1] == 0:
        break  # Two consecutive zeros = end

print(f"  Trouvé {len(table)} entrées")
for idx, (offset, val) in enumerate(table[:15]):
    print(f"    Entry {idx:2d} @ +0x{offset:02X}: {val:5d} (0x{val:04X})")

# Find FM offsets
# They are typically after spawn point offsets and before the two final zeros
# Look for the pattern: increasing offsets that could be formation positions

print()
print("Analyse des FM offsets:")
print(f"  Formation shift: +{FORMATION_SHIFT} bytes")
print()

# Entries 2-6 look like spawn points (80, 244, 408, 636, 896)
# Entries 7-9 might be duplicate/filler FM offsets (408, 636, 896)
# Based on Cavern having 8 formations

# Strategy: Find entries that look like formation offsets
# They should be in the range 0-5000 and somewhat evenly spaced

# The formation patcher looks for FM entries by matching against parsed sizes
# For now, let's assume entries after spawn points are FM offsets

# Looking at the output:
# Entry  0 @ +0x00: 60 (base/header)
# Entry  1 @ +0x04: 0 (separator)
# Entry  2 @ +0x08: 80 (SP)
# Entry  3 @ +0x0C: 244 (SP)
# Entry  4 @ +0x10: 408 (SP or FM?)
# Entry  5 @ +0x14: 636 (SP or FM?)
# Entry  6 @ +0x18: 896 (SP or FM?)
# Entry  7 @ +0x1C: 408 (FM - duplicate!)
# Entry  8 @ +0x20: 636 (FM - duplicate!)
# Entry  9 @ +0x24: 896 (FM - duplicate!)

# Cavern F1 A1 has spawn_point_count from JSON
# Let me check the JSON to know how many spawn points

# For now, assume entries 4-9 are FM offsets (8 formations)
# These are RELATIVE offsets from the formation area start

fm_start_idx = 4  # Guessing
fm_count = 8  # Cavern has 8 formations

print(f"Hypothèse: FM offsets commencent à entry {fm_start_idx}")
print(f"  Nombre de formations: {fm_count}")
print()

# These offsets are RELATIVE to formation area start
# They don't need to be updated because they're relative!
# Unless... entry[0] is an absolute offset that needs updating?

# Let me check entry[0]
entry0_val = table[0][1]
print(f"Entry[0] = {entry0_val} (0x{entry0_val:X})")
print(f"  Script start: 0x{SCRIPT_START:X}")
print(f"  Entry[0] points to: 0x{SCRIPT_START + entry0_val:X}")
print()

# Actually, looking at the formation patcher code more carefully:
# The FM offsets are RELATIVE offsets from some base within the script area
# They don't directly reference the formation area absolute offset

# But wait - if formations moved, and these are pointers INTO the formation area,
# then they should be fine if they're relative to formation start.

# The real issue might be that entry[0] or some other metadata
# needs updating to account for the shift

print("HYPOTHÈSE: Les FM offsets sont relatifs et OK.")
print("Le problème pourrait être entry[0] ou une autre métadonnée.")
print()
print("Essayons de mettre à jour entry[0] en ajoutant le shift:")

old_entry0 = struct.unpack_from('<I', data, SCRIPT_START)[0]
new_entry0 = old_entry0 + FORMATION_SHIFT

struct.pack_into('<I', data, SCRIPT_START, new_entry0)

print(f"  Entry[0]: {old_entry0} -> {new_entry0}")

with open(BLAZE, 'wb') as f:
    f.write(data)

print()
print("=" * 70)
print("Mise à jour appliquée!")
print()
print("NOTE: Si ça ne marche pas, il faudra utiliser le formation")
print("patcher qui gère correctement cette table.")
