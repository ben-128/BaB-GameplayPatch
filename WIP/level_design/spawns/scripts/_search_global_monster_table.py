#!/usr/bin/env python3
"""
Search for a GLOBAL monster table in BLAZE.ALL.

The 96-byte entries in area data are per-area copies. But a master monster
database likely exists elsewhere with:
  - Monster name
  - Base stats
  - AI pattern ID
  - Spell list
  - Loot table

Search strategy:
1. Find ALL occurrences of monster names in BLAZE.ALL
2. Look for occurrences OUTSIDE known area data regions
3. Analyze the data around those occurrences
"""

import struct
from pathlib import Path

BLAZE = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
data = BLAZE.read_bytes()

# Monster names to search for (ASCII, as they appear in 96-byte entries)
NAMES = [
    b"Lv20.Goblin",
    b"Goblin-Shaman",
    b"Giant-Bat",
    b"Goblin-Leader",
    b"Giant-Scorpion",
    b"Big-Viper",
    b"Giant-Spider",
    b"Cave-Bear",
    b"Blue-Slime",
    b"Ogre",
]

# Known area data regions (approximate) - to filter out
AREA_REGIONS = [
    (0xF7A900, 0xF7E000),  # Cavern F1 areas
    (0xF7E000, 0xF90000),  # More cavern areas
]

def is_in_area_data(offset):
    for start, end in AREA_REGIONS:
        if start <= offset < end:
            return True
    return False

print("=" * 80)
print("  SEARCH: Global monster table in BLAZE.ALL")
print(f"  File size: {len(data):,} bytes")
print("=" * 80)

for name in NAMES:
    print(f"\n  Searching for '{name.decode()}'...")
    pos = 0
    occurrences = []
    while True:
        idx = data.find(name, pos)
        if idx < 0:
            break
        in_area = is_in_area_data(idx)
        occurrences.append((idx, in_area))
        pos = idx + 1

    area_count = sum(1 for _, a in occurrences if a)
    other_count = sum(1 for _, a in occurrences if not a)
    print(f"    Total: {len(occurrences)} (in area data: {area_count}, OTHER: {other_count})")

    # Show non-area occurrences with context
    for off, in_area in occurrences:
        if not in_area:
            # Show 64 bytes before and 96 bytes after
            before = data[max(0, off-32):off]
            after = data[off:min(len(data), off+96)]

            # Check if this looks like a 96-byte entry (name + stats)
            if off + 96 <= len(data):
                stats_raw = data[off+16:off+96]
                stats = [struct.unpack_from('<H', stats_raw, i)[0] for i in range(0, 80, 2)]
                # Check if stats look valid (some non-zero, reasonable values)
                nonzero = sum(1 for s in stats if s != 0)

                print(f"    0x{off:08X}: [{before[-16:].hex()}] '{name.decode()}' "
                      f"stats_nonzero={nonzero}/40")

                if nonzero > 0:
                    # Show key stats
                    print(f"      exp={stats[0]} lvl={stats[1]} hp={stats[2]} "
                          f"magic={stats[3]} creature_type={stats[10]} "
                          f"dmg={stats[16]} armor={stats[17]}")

                    # Look for any data BEFORE that could be an AI reference
                    pre_data = data[max(0, off-64):off]
                    pre_hex = ' '.join(f'{b:02X}' for b in pre_data[-32:])
                    print(f"      32 bytes before: {pre_hex}")

                    # Look for data AFTER the 96-byte entry
                    post = data[off+96:off+128]
                    post_hex = ' '.join(f'{b:02X}' for b in post)
                    print(f"      32 bytes after entry: {post_hex}")
            else:
                print(f"    0x{off:08X}: (near end of file)")

# Also search for a simple pattern: consecutive monster names
# A global table might have names packed together
print(f"\n{'='*80}")
print("  SEARCH: Consecutive monster names (global table indicator)")
print(f"{'='*80}")

for i in range(len(NAMES) - 1):
    name1 = NAMES[i]
    name2 = NAMES[i+1]

    pos = 0
    while True:
        idx1 = data.find(name1, pos)
        if idx1 < 0:
            break

        # Look for name2 within 256 bytes after name1
        idx2 = data.find(name2, idx1 + len(name1), idx1 + 256)
        if idx2 >= 0 and not is_in_area_data(idx1):
            gap = idx2 - idx1
            print(f"  '{name1.decode()}' at 0x{idx1:X} + {gap} bytes -> '{name2.decode()}' at 0x{idx2:X}")
        pos = idx1 + 1

# Search for spell-related patterns near monster data
# Look for "Fire", "Ice", "Lightning" etc near monster names
print(f"\n{'='*80}")
print("  SEARCH: Spell/magic keywords near monster data")
print(f"{'='*80}")

SPELL_KEYWORDS = [b"Fire", b"Ice", b"Thunder", b"Heal", b"Poison", b"Blaze", b"Freeze"]
for keyword in SPELL_KEYWORDS:
    pos = 0
    count = 0
    while True:
        idx = data.find(keyword, pos)
        if idx < 0:
            break
        count += 1
        # Check if near any monster name (within 4KB)
        near_monster = False
        for name in NAMES:
            name_pos = data.find(name, max(0, idx - 4096), idx + 4096)
            if name_pos >= 0:
                near_monster = True
                break
        if near_monster and count <= 5:
            ctx = data[max(0,idx-16):min(len(data),idx+32)]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print(f"  '{keyword.decode()}' at 0x{idx:X} (near monster data): {ascii_ctx}")
        pos = idx + 1
    print(f"  '{keyword.decode()}': {count} total occurrences")

print(f"\n{'='*80}")
print("  DONE")
print(f"{'='*80}")
