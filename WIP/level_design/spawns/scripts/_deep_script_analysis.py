import struct
from pathlib import Path

BLAZE = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
data = bytearray(BLAZE.read_bytes())

# Cavern F1 Area1
GROUP_OFFSET = 0xF7A97C
NUM = 3
SCRIPT_START = GROUP_OFFSET + NUM * 96  # 0xF7AA9C
MONSTERS = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]

# Known spell IDs from the spell system (from monster_attacks.json or similar)
# Common spells: Fire=1, Ice=2, Lightning=3, etc.
# Let's also look for creature_type values from 96-byte entries

# Get creature_type for each monster
for i in range(NUM):
    entry_off = GROUP_OFFSET + i * 96
    name = data[entry_off:entry_off+16].split(b'\x00')[0].decode('ascii')
    creature_type = struct.unpack_from('<H', data, entry_off + 16 + 20)[0]  # stat[10]
    print(f"  {name}: creature_type={creature_type}")

# Scan the FULL script area (up to next area's data)
# Area 2 group is at 0xF7E1A8, so scan up to that minus some margin
AREA2_START = 0xF7E1A8 - 512  # rough pre-group area of Area 2
SCRIPT_SIZE = AREA2_START - SCRIPT_START
print(f"\nScript area: 0x{SCRIPT_START:X} to ~0x{AREA2_START:X} ({SCRIPT_SIZE} bytes)")

region = data[SCRIPT_START:SCRIPT_START + SCRIPT_SIZE]

# ANALYSIS 1: Find ALL occurrences of slot-related values (0, 1, 2) 
# in structured patterns
print("\n" + "=" * 80)
print("  ANALYSIS 1: Byte frequency per position in 8-byte aligned blocks")
print("=" * 80)

# Look at first 2048 bytes in 8-byte blocks
for block_start in [0, 0x400, 0x500]:
    block_end = min(block_start + 512, len(region))
    print(f"\n  Region script+0x{block_start:03X} to script+0x{block_end:03X}:")
    for pos in range(8):
        vals = {}
        for i in range(block_start, block_end, 8):
            if i + pos < len(region):
                v = region[i + pos]
                vals[v] = vals.get(v, 0) + 1
        # Show top 5 values
        top = sorted(vals.items(), key=lambda x: -x[1])[:5]
        top_str = ', '.join(f'0x{v:02X}({c})' for v, c in top)
        print(f"    byte[{pos}]: {top_str}")

# ANALYSIS 2: Find the uint16 values just before FFFFFFFFFFFF terminators
# These varied per spawn command and might be spell/AI references
print("\n" + "=" * 80)
print("  ANALYSIS 2: uint16 values before FF terminators (potential AI/spell refs)")
print("=" * 80)

ff_values = []
for i in range(len(region) - 8):
    if region[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
        if i >= 2:
            val = struct.unpack_from('<H', region, i - 2)[0]
            slot_after = struct.unpack_from('<H', region, i + 6)[0] if i + 8 <= len(region) else -1
            abs_addr = SCRIPT_START + i
            ff_values.append((abs_addr, val, slot_after))

print(f"  Found {len(ff_values)} FF-terminated values:")
for addr, val, slot in ff_values[:40]:
    print(f"    0x{addr:X}: val=0x{val:04X} ({val:5d}) | slot_after={slot}")

# Collect unique values
unique_vals = sorted(set(v[1] for v in ff_values))
print(f"\n  Unique values: {[f'0x{v:04X}({v})' for v in unique_vals]}")

# ANALYSIS 3: Look for structures with per-monster differentiation
# Scan for any 3-element patterns (since there are 3 monsters)
print("\n" + "=" * 80)
print("  ANALYSIS 3: Triplet patterns (3 related values = 3 monsters?)")
print("=" * 80)

# Look for 3 consecutive different non-zero uint16 values
for i in range(0, min(4096, len(region)) - 6, 2):
    v0 = struct.unpack_from('<H', region, i)[0]
    v1 = struct.unpack_from('<H', region, i + 2)[0]
    v2 = struct.unpack_from('<H', region, i + 4)[0]
    
    # Must all be non-zero, non-FF, different from each other
    if (v0 != 0 and v1 != 0 and v2 != 0 and
        v0 != 0xFFFF and v1 != 0xFFFF and v2 != 0xFFFF and
        v0 != v1 and v1 != v2 and v0 != v2 and
        v0 < 1000 and v1 < 1000 and v2 < 1000):  # reasonable range
        abs_addr = SCRIPT_START + i
        # Show context
        ctx = region[max(0,i-4):min(len(region),i+12)]
        print(f"    0x{abs_addr:X}: [{v0}, {v1}, {v2}]  ctx: {ctx.hex()}")

# ANALYSIS 4: Look for the area between spawn commands and the next big section
# After the spawn commands (around script+0x600), what's there?
print("\n" + "=" * 80)
print("  ANALYSIS 4: Data after spawn commands (script+0x600 to +0x900)")
print("=" * 80)

for i in range(0x600, min(0x900, len(region)), 16):
    chunk = region[i:i+16]
    if any(b != 0 for b in chunk):  # skip all-zero lines
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        abs_addr = SCRIPT_START + i
        # uint32 interpretation
        u32s = []
        for j in range(0, min(16, len(chunk)), 4):
            if j + 4 <= len(chunk):
                u32s.append(struct.unpack_from('<I', chunk, j)[0])
        u32_str = ' '.join(f'{v:08X}' for v in u32s)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  0x{abs_addr:X}: {hex_str:<48s} | {ascii_str}")

# ANALYSIS 5: Search for known spell-related patterns
# From the spell system, spells have IDs. Let's search for spell table structures
print("\n" + "=" * 80)
print("  ANALYSIS 5: Potential spell tables (consecutive small values)")  
print("=" * 80)

for i in range(0, min(8192, len(region)) - 16, 4):
    # Look for groups of 4 uint16 values all in spell range (1-50)
    vals = [struct.unpack_from('<H', region, i + j*2)[0] for j in range(4)]
    if all(0 < v < 50 for v in vals) and len(set(vals)) >= 2:
        abs_addr = SCRIPT_START + i
        ctx = region[i:i+16]
        print(f"    0x{abs_addr:X}: {vals}  raw: {ctx.hex()}")

# ANALYSIS 6: Look at the FULL block structure with FF delimiters
# Map out every FF-terminated block in the first 2KB
print("\n" + "=" * 80)
print("  ANALYSIS 6: Complete block map (first 2KB)")
print("=" * 80)

pos = 0
block_num = 0
while pos < min(2048, len(region)) - 4:
    # Find next FFFFFFFF
    ff_pos = -1
    for j in range(pos, min(pos + 512, len(region) - 4)):
        if region[j:j+4] == b'\xff\xff\xff\xff':
            ff_pos = j
            break
    
    if ff_pos < 0:
        break
    
    block_size = ff_pos - pos
    block_data = region[pos:ff_pos]
    
    # Count non-zero bytes
    nonzero = sum(1 for b in block_data if b != 0)
    
    abs_start = SCRIPT_START + pos
    abs_ff = SCRIPT_START + ff_pos
    
    # Show compact summary
    if block_size > 0 and nonzero > 0:
        preview = block_data[:24].hex() + ('...' if block_size > 24 else '')
        print(f"  Block {block_num:2d}: 0x{abs_start:X}-0x{abs_ff:X} ({block_size:4d}b, {nonzero:3d} nonzero) {preview}")
    
    # Skip past FF block (could be 4, 6, or 8 bytes of FF)
    skip = ff_pos
    while skip < len(region) and region[skip] == 0xFF:
        skip += 1
    pos = skip
    block_num += 1

# ANALYSIS 7: What's at the type-7 target offsets + further?
# The texture variant data was at script+0x0580. What's beyond that?
print("\n" + "=" * 80)
print("  ANALYSIS 7: Data around type-7 targets (script+0x560 to +0x5F0)")
print("=" * 80)

for i in range(0x560, min(0x5F0, len(region)), 8):
    chunk = region[i:i+8]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    abs_addr = SCRIPT_START + i
    i16s = [struct.unpack_from('<h', chunk, k)[0] for k in range(0, len(chunk), 2) if k+2 <= len(chunk)]
    i16_str = ' '.join(f'{v:6d}' for v in i16s)
    print(f"  0x{abs_addr:X} (+{i:03X}): {hex_str:<24s} | {i16_str}")
