"""
Find the link between monsters and their spell table entries - Part 3
Focus on finding how the game code accesses spell entries.

The spell table is at 0x9E8D8E in BLAZE.ALL.
When loaded into PS1 RAM, addresses are often offset by the load address.
"""
import struct
from pathlib import Path

BLAZE_ALL = Path(__file__).parent.parent.parent.parent / "output" / "BLAZE.ALL"
EXECUTABLE = Path(__file__).parent.parent.parent.parent / "work" / "SLES_008.45"

data = BLAZE_ALL.read_bytes()
exe = EXECUTABLE.read_bytes() if EXECUTABLE.exists() else None

SPELL_TABLE_START = 0x9E8D8E
SPELL_ENTRY_SIZE = 16
TOTAL_SPELL_ENTRIES = 30

print("=" * 70)
print("Analysis: Find all instances of Goblin-Shaman and look for spell index")
print("=" * 70)

# Find all Goblin-Shaman instances
search = b"Goblin-Shaman"
pos = 0
instances = []
while True:
    pos = data.find(search, pos)
    if pos == -1:
        break
    instances.append(pos)
    pos += 1

print(f"\nFound {len(instances)} instances of 'Goblin-Shaman':")
for offset in instances:
    print(f"\n  Instance at 0x{offset:X}:")

    # Look at full 256 byte area (monster might be part of a larger structure)
    start = max(0, offset - 128)
    end = min(len(data), offset + 128)

    # Look for the value 6 anywhere in this area
    area = data[start:end]
    for i, b in enumerate(area):
        if b == 6:
            rel = i - 128  # relative to monster name
            # Check context
            context = area[max(0,i-4):min(len(area),i+8)]
            hex_ctx = ' '.join(f'{x:02X}' for x in context)
            if rel not in range(-16, 96):  # Exclude the monster stats area
                print(f"    Found value 6 at relative offset {rel}: {hex_ctx}")

print("\n" + "=" * 70)
print("Analysis: Look for a lookup table in BLAZE.ALL")
print("=" * 70)

# Search for tables that could map monsters to spell entries
# A table might be: [monster_id or index, spell_entry_index, ...]

# Look for consecutive entries like: 00 00 06 00 (entry 0 -> spell 6?)
# or sequences of small values that could be indices

print("\nSearching for potential monster->spell mapping tables...")

# Look for patterns where we see sequential or structured spell indices
candidates = []

for offset in range(0x900000, 0xA00000):
    if offset + 64 > len(data):
        break

    # Check for table-like structure with 16-bit entries
    chunk = []
    for i in range(0, 32, 2):
        val = struct.unpack('<H', data[offset+i:offset+i+2])[0]
        chunk.append(val)

    # Look for patterns with spell entry indices (0-16)
    valid_spell_entries = [v for v in chunk if 0 <= v <= 16]

    # If we have many valid spell entry values and some structure
    if len(valid_spell_entries) >= 8:
        # Check if values are reasonably distributed (not all the same)
        if len(set(chunk[:8])) >= 3:
            # Look for entry 6 specifically
            if 6 in chunk[:8]:
                hex_str = ' '.join(f'{v:02X}' for v in chunk[:8])
                candidates.append((offset, hex_str))

print(f"Found {len(candidates)} candidate tables containing entry 6:")
for offset, hex_str in candidates[:20]:
    print(f"  0x{offset:X}: {hex_str}")

print("\n" + "=" * 70)
print("Analysis: Check if spell entry is stored by monster name order")
print("=" * 70)

# Maybe spell entries are assigned by the order monsters appear in the file
# Let's find all caster-type monsters and see their order

caster_names = [
    b"Goblin-Shaman",
    b"Goblin-Wizard",
    b"Dark-Magi",
    b"Arch-Magi",
    b"Dark-Wizard",
    b"Succubus",
    b"Ghost",
    b"Shadow",
]

print("\nFirst occurrence of each caster monster:")
casters_by_offset = []
for name in caster_names:
    pos = data.find(name)
    if pos != -1:
        casters_by_offset.append((pos, name.decode('ascii')))

casters_by_offset.sort()
for i, (offset, name) in enumerate(casters_by_offset):
    print(f"  {i}: {name:20s} at 0x{offset:X}")

print("\n" + "=" * 70)
print("Analysis: Look at spell table entry flags more carefully")
print("=" * 70)

# The flags in spell entries might encode monster type
# Entry 6 (Goblin-Shaman) has flags AF 00
# Let's decode what AF and B0 mean

print("\nSpell entry flags analysis:")
for i in range(17):
    entry_offset = SPELL_TABLE_START + (i * SPELL_ENTRY_SIZE)
    entry = data[entry_offset:entry_offset+16]

    flag1, flag2 = entry[0], entry[1]
    spell_ids = list(entry[2:10])

    # Decode flags
    # AF = 1010 1111, B0 = 1011 0000, BF = 1011 1111, C0 = 1100 0000, DF = 1101 1111
    flag1_high = (flag1 >> 4) & 0xF
    flag1_low = flag1 & 0xF

    print(f"  Entry {i:2d}: flags=0x{flag1:02X} 0x{flag2:02X} (high={flag1_high:X} low={flag1_low:X}), spells={spell_ids}")

print("\n" + "=" * 70)
print("Analysis: Try to find AI behavior code referencing spell table")
print("=" * 70)

if exe:
    # In PS1 executables, code often loads addresses using lui/addiu pairs
    # or references data via offsets from a base register

    # The spell table might be accessed with a calculated address
    # Look for references to the spell table offset or nearby values

    # Search for parts of the spell table address
    search_vals = [
        0x9E8D8E,  # Exact offset
        0x9E8D,    # High word
        0x8D8E,    # Low word
    ]

    print("\nSearching executable for spell table references...")

    for search_val in search_vals:
        # Search for this value as a 16-bit immediate
        for i in range(0, len(exe) - 4, 4):
            # Check lower 16 bits of instruction
            instr = struct.unpack('<I', exe[i:i+4])[0]
            imm16 = instr & 0xFFFF
            if imm16 == (search_val & 0xFFFF):
                # Check if this looks like a lui or addiu instruction
                opcode = (instr >> 26) & 0x3F
                if opcode in [0x0F, 0x09]:  # lui or addiu
                    print(f"  EXE 0x{i:X}: instruction 0x{instr:08X}, imm16=0x{imm16:04X}")
else:
    print("Executable not found at expected path")

print("\n" + "=" * 70)
print("Analysis: Look for monster ID -> spell entry direct mapping")
print("=" * 70)

# Maybe there's a simple array where array[monster_index] = spell_entry
# Let's search for an array that has 6 at position that could correspond to Goblin-Shaman

# Goblin-Shaman is monster ID 59 in our index
# If there's a byte array where [59] = 6...

print("\nSearching for byte arrays where position N has value 6...")
for offset in range(0x900000, 0xB00000):
    if offset + 100 > len(data):
        break

    # Check various positions that might correspond to caster IDs
    for pos_of_6 in [6, 59, 60]:  # Try different possible monster IDs
        if data[offset + pos_of_6] == 6:
            # Check if surrounding values also look like spell indices
            context = list(data[offset:offset+min(80, len(data)-offset)])

            # Valid if most values are small (0-30) or 0xFF
            valid = [v for v in context if v <= 30 or v == 0xFF]
            if len(valid) >= 60:
                # Check if there's variety (not all the same)
                unique = len(set(context[:30]))
                if unique >= 5:
                    hex_str = ' '.join(f'{v:02X}' for v in context[:20])
                    print(f"  0x{offset:X} [pos {pos_of_6}]=6: {hex_str}...")
                    break

print("\nDone.")
