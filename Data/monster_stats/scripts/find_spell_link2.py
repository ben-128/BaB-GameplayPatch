"""
Find the link between monsters and their spell table entries - Part 2
Focus on data structure around monster entries and look for AI/spell index references.
"""
import struct
from pathlib import Path

BLAZE_ALL = Path(__file__).parent.parent.parent.parent / "output" / "BLAZE.ALL"
data = BLAZE_ALL.read_bytes()

SPELL_TABLE_START = 0x9E8D8E
SPELL_ENTRY_SIZE = 16

# Get all monster names from the file
def find_all_monsters():
    """Find all monster name entries in BLAZE.ALL"""
    monsters = []
    # Known monster area ranges
    ranges = [
        (0x1400000, 0x1A00000),
        (0x2B00000, 0x2C00000),
    ]

    for start, end in ranges:
        pos = start
        while pos < end:
            # Look for ASCII strings that could be monster names
            chunk = data[pos:pos+16]
            if b'\x00' in chunk:
                name_bytes = chunk.split(b'\x00')[0]
                if len(name_bytes) >= 4 and name_bytes.isalpha() == False:
                    # Check if it looks like a monster name (has - or capital letters)
                    try:
                        name = name_bytes.decode('ascii')
                        if '-' in name and name[0].isupper():
                            # Verify by checking if next bytes look like stats
                            stats_area = data[pos+16:pos+32]
                            if len(stats_area) >= 16:
                                monsters.append((pos, name))
                    except:
                        pass
            pos += 1
    return monsters

print("=" * 70)
print("Analysis: Look for behavior/AI data near known casters")
print("=" * 70)

# Focus on areas where we found data structure at -16 for Dark-Magi
# The data at 0x197619C - 16 = 0x197618C was:
# 01 08 00 00 01 07 00 40 02 02 00 00 02 08 00 40
# This looks like: [byte, byte, 00, 00] repeated

casters_detailed = {
    "Goblin-Shaman": 0x1498278,
    "Goblin-Wizard": 0x2BEF2A8,
    "Dark-Magi": 0x197619c,
    "Arch-Magi": 0x199b228,
    "Dark-Wizard": 0x19951ec,
}

print("\nLooking at extended data before each monster:")
for name, offset in casters_detailed.items():
    print(f"\n{name} at 0x{offset:X}:")

    # Show data from -128 to +16
    for rel in range(-128, 32, 16):
        pos = offset + rel
        if pos < 0 or pos + 16 > len(data):
            continue
        chunk = data[pos:pos+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)

        # Mark the monster name position
        marker = " <-- NAME" if rel == 0 else ""
        print(f"  {rel:+4d} (0x{pos:X}): {hex_str}{marker}")

print("\n" + "=" * 70)
print("Analysis: Search for spell entry 6 reference near Goblin-Shaman")
print("=" * 70)

# The spell entry index might be in a table elsewhere
# Let's search for patterns where 6 appears with other values

offset = 0x1498278  # Goblin-Shaman

# Maybe there's a table of monster_id -> spell_entry elsewhere
# Search for sequences that include expected values

print("\nSearching for monster type/spell index mapping tables...")

# Look for table-like structures with small sequential or related values
for search_start in range(0x900000, 0xA00000, 0x10):
    chunk = data[search_start:search_start+64]

    # Look for patterns that could be index tables
    # Check if we have a series of small values (0-30)
    small_vals = [b for b in chunk if 0 <= b <= 30]
    if len(small_vals) >= 16 and len(set(chunk)) >= 4:
        # Check if it looks like a structured table
        zeros = chunk.count(0)
        if 8 <= zeros <= 40:  # Some structure with zeros
            hex_str = ' '.join(f'{b:02X}' for b in chunk[:32])
            print(f"  0x{search_start:X}: {hex_str}")

print("\n" + "=" * 70)
print("Analysis: Look at model/behavior ID field")
print("=" * 70)

# The stat4_magic field is high for casters (91, 101, 279, etc.)
# But this doesn't directly map to spell entry
# Let's look at the offset pattern

print("\nMonster offsets and their stat4_magic values:")
for name, offset in sorted(casters_detailed.items(), key=lambda x: x[1]):
    stats_offset = offset + 16
    stat4 = struct.unpack('<H', data[stats_offset + 6:stats_offset + 8])[0]
    print(f"  {name:20s} offset=0x{offset:X} stat4_magic={stat4}")

print("\n" + "=" * 70)
print("Analysis: Check AI/behavior byte at specific offset")
print("=" * 70)

# PS1 monster data often has an AI type byte
# Let's look at position -64 + specific offsets

for name, offset in casters_detailed.items():
    print(f"\n{name}:")

    # Check at various negative offsets for AI/behavior data
    for check_offset in [-64, -60, -56, -52, -48, -44, -40]:
        pos = offset + check_offset
        val = data[pos]
        val2 = struct.unpack('<H', data[pos:pos+2])[0]
        print(f"  offset {check_offset:+3d}: byte={val:3d} (0x{val:02X}), uint16={val2}")

print("\n" + "=" * 70)
print("Analysis: Compare with non-caster monsters")
print("=" * 70)

non_casters = {
    "Goblin": 0x14977E8,  # Regular goblin shouldn't cast
    "Wolf": 0x1497A08,
    "Skeleton": 0x1499AC8,
}

print("\nComparing casters vs non-casters at offset -64:")
print("\nCasters:")
for name, offset in casters_detailed.items():
    chunk = data[offset-64:offset-48]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    print(f"  {name:20s}: {hex_str}")

print("\nNon-casters:")
for name, offset in non_casters.items():
    chunk = data[offset-64:offset-48]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    print(f"  {name:20s}: {hex_str}")

print("\nDone.")
