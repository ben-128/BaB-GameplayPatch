"""
Find the link between monsters and their spell table entries.

Known data:
- Spell table at 0x9E8D8E, each entry 16 bytes
- Goblin-Shaman uses entry 6 (offset 0x9E8DEE)
- Goblin-Shaman monster data at 0x1498278

Strategy: Look for references to spell entry indices near monster data,
or search for patterns that could encode the spell table index.
"""
import struct
from pathlib import Path

BLAZE_ALL = Path(__file__).parent.parent.parent.parent / "output" / "BLAZE.ALL"
data = BLAZE_ALL.read_bytes()

# Known casters with their monster data offsets
CASTERS = {
    "Goblin-Shaman": {"offset": 0x1498278, "spell_entry": 6},
    "Goblin-Wizard": {"offset": 0x2BEF2A8, "spell_entry": None},  # Unknown
    "Dark-Magi": {"offset": 0x197619c, "spell_entry": None},
    "Arch-Magi": {"offset": 0x199b228, "spell_entry": None},
    "Dark-Wizard": {"offset": 0x19951ec, "spell_entry": None},
}

SPELL_TABLE_START = 0x9E8D8E
SPELL_ENTRY_SIZE = 16

print("=" * 70)
print("Analysis 1: Look for spell entry index in monster data area")
print("=" * 70)

for name, info in CASTERS.items():
    offset = info["offset"]
    spell_entry = info["spell_entry"]

    print(f"\n{name} at 0x{offset:X}:")

    # Read extended area around monster entry (96 bytes standard + extra)
    start = max(0, offset - 64)
    chunk = data[start:offset + 256]

    # Show first 96 bytes (standard monster entry)
    monster_entry = data[offset:offset+96]
    name_bytes = monster_entry[:16]
    stats = monster_entry[16:]

    # Decode stats as int16 values
    stat_values = []
    for i in range(0, len(stats), 2):
        val = struct.unpack('<H', stats[i:i+2])[0]
        stat_values.append(val)

    # Look for small values (0-30) that could be spell entry indices
    print(f"  Stats with small values (potential spell index):")
    for i, val in enumerate(stat_values):
        if 0 <= val <= 30:
            print(f"    stat[{i}] (offset +0x{16+i*2:02X}) = {val}")

    # Look in area before monster entry
    print(f"\n  Bytes before monster entry (-64 to 0):")
    pre_bytes = data[offset-64:offset]
    for rel in range(0, 64, 16):
        chunk = pre_bytes[rel:rel+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        print(f"    -{64-rel:02d}: {hex_str}")

print("\n" + "=" * 70)
print("Analysis 2: Search for spell table address references")
print("=" * 70)

# Look for pointers to spell table entries near monster data
for name, info in CASTERS.items():
    offset = info["offset"]

    # Search in a wider area around the monster
    search_start = max(0, offset - 0x1000)
    search_end = min(len(data), offset + 0x1000)

    refs_found = []
    for pos in range(search_start, search_end, 4):
        val = struct.unpack('<I', data[pos:pos+4])[0]
        # Check if it points to spell table area
        if SPELL_TABLE_START <= val <= SPELL_TABLE_START + (30 * SPELL_ENTRY_SIZE):
            entry_idx = (val - SPELL_TABLE_START) // SPELL_ENTRY_SIZE
            refs_found.append((pos, val, entry_idx))

    if refs_found:
        print(f"\n{name}: Found {len(refs_found)} spell table refs:")
        for pos, val, idx in refs_found[:5]:
            rel = pos - offset
            print(f"    0x{pos:X} (rel {rel:+d}): ptr=0x{val:X} -> entry {idx}")

print("\n" + "=" * 70)
print("Analysis 3: Look for spell entry index pattern")
print("=" * 70)

# Goblin-Shaman uses entry 6
# Let's see if the value 6 appears in a specific position in all caster data
print("\nSearching for value 6 in Goblin-Shaman data area:")
offset = CASTERS["Goblin-Shaman"]["offset"]

for rel in range(-256, 512, 2):
    pos = offset + rel
    if pos < 0 or pos + 2 > len(data):
        continue
    val = struct.unpack('<H', data[pos:pos+2])[0]
    if val == 6:
        context = data[pos-8:pos+24]
        hex_ctx = ' '.join(f'{b:02X}' for b in context)
        print(f"  offset +{rel}: value=6, context: {hex_ctx}")

print("\n" + "=" * 70)
print("Analysis 4: Compare monster model/AI pointers")
print("=" * 70)

# PS1 games often have a pointer to AI code or behavior data
# Look for common pointer patterns before/after monster name

for name, info in CASTERS.items():
    offset = info["offset"]

    print(f"\n{name}:")

    # Look at potential pointer locations before the name
    for rel in [-8, -4, 96, 100, 104]:
        pos = offset + rel
        if pos < 0 or pos + 4 > len(data):
            continue
        val = struct.unpack('<I', data[pos:pos+4])[0]
        # Check if it looks like a valid pointer (in loaded game areas)
        if 0x80000000 <= val <= 0x80200000:  # PS1 RAM
            print(f"  +{rel}: 0x{val:X} (PS1 RAM ptr)")
        elif 0x800000 <= val <= 0x2000000:  # BLAZE.ALL data
            print(f"  +{rel}: 0x{val:X} (BLAZE.ALL ptr)")

print("\n" + "=" * 70)
print("Analysis 5: Search for monster name near spell assignments")
print("=" * 70)

# Maybe there's a separate table that maps monster names to spell entries
# Search for monster names in a different area

for name in ["Goblin-Shaman", "Goblin-Wizard", "Arch-Magi", "Dark-Magi"]:
    search = name.encode('ascii')
    pos = 0
    print(f"\n{name} instances:")
    count = 0
    while count < 5:
        pos = data.find(search, pos)
        if pos == -1:
            break
        print(f"  0x{pos:X}")
        pos += 1
        count += 1

print("\n" + "=" * 70)
print("Analysis 6: Examine spell table flags pattern")
print("=" * 70)

# The first bytes of each spell entry have flags (AF, B0, BF, C0, DF, etc.)
# Maybe these flags encode the monster type

print("Spell entries with their flag bytes:")
for i in range(20):
    entry_offset = SPELL_TABLE_START + (i * SPELL_ENTRY_SIZE)
    entry = data[entry_offset:entry_offset+16]
    flag1, flag2 = entry[0], entry[1]
    hex_str = ' '.join(f'{b:02X}' for b in entry[:10])
    print(f"  Entry {i:2d} (0x{entry_offset:X}): flags={flag1:02X} {flag2:02X}, data: {hex_str}")

print("\nDone.")
