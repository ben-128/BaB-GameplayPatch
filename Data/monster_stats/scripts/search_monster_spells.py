"""
Search for AI/behavior code that references spells
"""
import struct
from pathlib import Path

BLAZE_ALL = Path(__file__).parent.parent.parent.parent / "output" / "BLAZE.ALL"
data = BLAZE_ALL.read_bytes()

print("=" * 70)
print("Search 1: Find spell name strings and their indices")
print("=" * 70)

# Find all spell names and calculate their index
spell_entries = []
search_names = [b"Bullet", b"Sleep", b"Healing", b"Blaze", b"Meteor"]

for name in search_names:
    pos = 0
    while True:
        pos = data.find(name, pos)
        if pos == -1:
            break
        # Get context before
        start = max(0, pos - 20)
        prefix = data[start:pos]
        full_name = prefix.split(b'\x00')[-1] + data[pos:pos+16].split(b'\x00')[0]
        spell_entries.append((pos, full_name.decode('ascii', errors='ignore')))
        pos += 1

# Sort by address
spell_entries = sorted(set(spell_entries))
print(f"\nFound {len(spell_entries)} spell entries:")
for addr, name in spell_entries[:30]:
    print(f"  0x{addr:X}: {name}")

print("\n" + "=" * 70)
print("Search 2: Look for AI script patterns")
print("=" * 70)

# PS1 games often use jump tables or switch statements for AI
# Look for sequences of small numbers that could be AI state/action codes

# Check around monster data areas
monster_areas = [
    (0x1480000, 0x14A0000),  # Early monster area
    (0x1960000, 0x1990000),  # Later monster area
]

for area_start, area_end in monster_areas:
    print(f"\nScanning 0x{area_start:X} - 0x{area_end:X}...")

    # Sample every 0x1000 bytes
    for offset in range(area_start, area_end, 0x1000):
        if offset + 256 > len(data):
            break

        # Look for sequences that might be spell/action lists
        for rel in range(0, 256, 4):
            addr = offset + rel
            vals = list(data[addr:addr+16])

            # Pattern: small values (1-50) with variety
            if all(0 <= v <= 60 for v in vals):
                unique = len(set(vals))
                non_zero = sum(1 for v in vals if v > 0)
                if 4 <= unique <= 10 and 6 <= non_zero <= 14:
                    print(f"  0x{addr:X}: {vals}")

print("\n" + "=" * 70)
print("Search 3: Find references to spell table addresses")
print("=" * 70)

# Spell area is around 0x908000-0x910000
# Look for pointers to this area
spell_base = 0x908000
for offset in range(0, len(data) - 4, 4):
    val = struct.unpack('<I', data[offset:offset+4])[0]
    if spell_base <= val <= spell_base + 0x10000:
        # Check if this looks like code/data referencing spells
        context = data[offset-8:offset+12]
        # Only print if near ASCII or in a structured area
        if offset < 0x100000 or 0x1400000 <= offset <= 0x2000000:
            nearby = data[offset-32:offset].split(b'\x00')[-1]
            if len(nearby) > 3:
                print(f"  0x{offset:X}: ptr=0x{val:X} near '{nearby.decode('ascii', errors='ignore')[:20]}'")

# Known monster IDs
GOBLIN_SHAMAN_ID = 59
GOBLIN_WIZARD_ID = 60
ARCH_MAGI_ID = 0  # Unknown

# Spell table area
SPELL_AREA_START = 0x908000
SPELL_AREA_END = 0x910000

# ============================================================
# Search 1: Find Goblin-Shaman ID (59) near spell definitions
# ============================================================
print("\n[1] Searching for Goblin-Shaman ID (59) in spell area...")

for offset in range(SPELL_AREA_START, SPELL_AREA_END):
    if data[offset] == 59 or (offset + 1 < len(data) and struct.unpack('<H', data[offset:offset+2])[0] == 59):
        # Show context
        context_start = max(0, offset - 16)
        context = data[context_start:offset+32]

        # Check if this looks interesting (near spell-like data)
        nearby = list(data[offset-8:offset+8])
        if any(8 <= b <= 50 for b in nearby):  # Spell IDs nearby
            print(f"  0x{offset:X}: {list(data[offset:offset+16])}")

# ============================================================
# Search 2: Find tables with monster ID -> spell list structure
# ============================================================
print("\n[2] Searching for monster ID -> spell mapping tables...")

# Look for patterns like: [monster_id, spell1, spell2, spell3, spell4]
for offset in range(0, len(data) - 20, 2):
    vals = [struct.unpack('<H', data[offset+i*2:offset+i*2+2])[0] for i in range(10)]

    # Check if first value could be a monster ID (1-150)
    if 1 <= vals[0] <= 150:
        # Check if next values look like spell IDs (small, some in valid range)
        spell_candidates = vals[1:5]
        valid_spells = [v for v in spell_candidates if 1 <= v <= 100]

        if len(valid_spells) >= 3 and len(set(spell_candidates)) >= 2:
            # Check if this pattern repeats (table structure)
            next_entry = [struct.unpack('<H', data[offset+10+i*2:offset+10+i*2+2])[0] for i in range(5)]
            if 1 <= next_entry[0] <= 150 and next_entry[0] != vals[0]:
                print(f"  0x{offset:X}: ID={vals[0]}, spells?={vals[1:5]}")
                if offset < 0x100000:  # Limit output
                    continue

# ============================================================
# Search 3: Find spell name references with monster associations
# ============================================================
print("\n[3] Searching near spell definitions for monster refs...")

spell_addrs = {
    "Sleep": 0x909858,
    "Stone Bullet": 0x908EFE,
    "Healing": None,  # Too many
    "Fire Bullet": 0x908E6D,
}

for spell_name, addr in spell_addrs.items():
    if addr is None:
        continue
    print(f"\n  {spell_name} at 0x{addr:X}:")

    # Look in 256 bytes before and after for interesting patterns
    for check_offset in range(addr - 256, addr + 256, 4):
        if check_offset < 0 or check_offset + 4 > len(data):
            continue

        val = struct.unpack('<I', data[check_offset:check_offset+4])[0]

        # Could be a pointer to monster data?
        if 0x1400000 <= val <= 0x2000000:  # Monster data range
            rel = check_offset - addr
            print(f"    +{rel}: 0x{val:X} (pointer to monster area?)")

# ============================================================
# Search 4: Find AI/behavior tables that might reference spells
# ============================================================
print("\n[4] Searching for AI behavior tables...")

# Look for byte sequences that could be spell choice tables
# Pattern: small values (0-50) repeated in groups
for offset in range(0, len(data) - 32, 1):
    chunk = list(data[offset:offset+16])

    # All values small and some repetition
    if all(0 <= v <= 50 for v in chunk):
        counts = {}
        for v in chunk:
            counts[v] = counts.get(v, 0) + 1

        # Must have meaningful pattern (not all zeros, some variety)
        non_zero = [v for v in chunk if v > 0]
        if 4 <= len(non_zero) <= 12 and len(counts) >= 3 and max(counts.values()) >= 2:
            # Check if near a monster name
            nearby_start = max(0, offset - 0x100)
            nearby_data = data[nearby_start:offset]

            # Look for ASCII monster names
            for monster in [b"Goblin", b"Shaman", b"Wizard", b"Magi"]:
                if monster in nearby_data:
                    print(f"  0x{offset:X}: {chunk} (near {monster.decode()})")
                    break

# ============================================================
# Search 5: Find Goblin-Shaman name and scan surrounding area
# ============================================================
print("\n[5] Deep scan around Goblin-Shaman instances...")

search = b"Goblin-Shaman"
pos = 0
while True:
    pos = data.find(search, pos)
    if pos == -1:
        break

    print(f"\n  Instance at 0x{pos:X}:")

    # Scan +0x1000 bytes after for spell-like patterns
    for rel in range(0, 0x1000, 0x10):
        check = pos + rel
        if check + 16 > len(data):
            break

        chunk = list(data[check:check+16])

        # Look for small repeated values (potential spell table)
        small_vals = [v for v in chunk if 1 <= v <= 50]
        if len(small_vals) >= 6:
            counts = {}
            for v in small_vals:
                counts[v] = counts.get(v, 0) + 1
            if len(counts) >= 2 and max(counts.values()) >= 2:
                hex_str = ' '.join(f'{v:02X}' for v in chunk)
                print(f"    +0x{rel:03X}: {hex_str}")

    pos += 1

print("\n" + "=" * 70)
print("Search complete.")
