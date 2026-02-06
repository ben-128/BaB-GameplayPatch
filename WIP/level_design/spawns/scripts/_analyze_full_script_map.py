#!/usr/bin/env python3
"""
Map the FULL script area for Cavern F1 Area1.
Goal: find any unmapped region that could contain AI/behavior data.

Known structures in script area:
- Blocks 0-3: initial spawn records (script+0x080 to +0x106)
- Block 4: resource binding table with type entries (script+0x106 to +0x41C)
- Blocks 5-15: spawn commands (script+0x420 to +0x564)
- Blocks 16+: type-7 target data / texture data (script+0x564 to +0x600+)
- Type-8 targets: at script+0x1DC0 and +0x1FC4 (deep bytecode)

UNKNOWN: everything between ~script+0x600 and script+0x1DC0
"""

import struct
from pathlib import Path

BLAZE = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
data = bytearray(BLAZE.read_bytes())

# Cavern F1 Area1
GROUP_OFFSET = 0xF7A97C
NUM = 3
SCRIPT_START = GROUP_OFFSET + NUM * 96  # 0xF7AA9C

# Area2 group is at 0xF7E1A8, script area ends before that
AREA2_GROUP = 0xF7E1A8
SCRIPT_END_APPROX = AREA2_GROUP - 0x280  # rough estimate, pre-group structures

print("=" * 80)
print(f"  FULL SCRIPT AREA MAP - Cavern F1 Area1")
print(f"  Script starts at: 0x{SCRIPT_START:X}")
print(f"  Approx end: 0x{SCRIPT_END_APPROX:X}")
print(f"  Total size: ~{SCRIPT_END_APPROX - SCRIPT_START:,} bytes")
print("=" * 80)

region = data[SCRIPT_START:SCRIPT_END_APPROX]

# SECTION 1: Find all non-zero regions
print(f"\n=== NON-ZERO REGIONS (16-byte granularity) ===")
in_nonzero = False
region_start = 0
nonzero_regions = []

for i in range(0, len(region), 16):
    chunk = region[i:i+16]
    is_nonzero = any(b != 0 for b in chunk)

    if is_nonzero and not in_nonzero:
        region_start = i
        in_nonzero = True
    elif not is_nonzero and in_nonzero:
        nonzero_regions.append((region_start, i))
        in_nonzero = False

if in_nonzero:
    nonzero_regions.append((region_start, len(region)))

for start, end in nonzero_regions:
    size = end - start
    print(f"  script+0x{start:04X} to +0x{end:04X} ({size:5d} bytes) "
          f"= abs 0x{SCRIPT_START+start:X} to 0x{SCRIPT_START+end:X}")

# SECTION 2: Focus on the UNMAPPED REGION (script+0x600 to +0x900)
print(f"\n=== REGION: script+0x5A0 to +0x0A00 (unmapped zone) ===")
for i in range(0x5A0, min(0xA00, len(region)), 16):
    chunk = region[i:i+16]
    if any(b != 0 for b in chunk):
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        # Also interpret as uint16 and uint32
        u16s = [struct.unpack_from('<H', chunk, j)[0] for j in range(0, 16, 2)]
        u16_str = ' '.join(f'{v:5d}' for v in u16s)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        abs_addr = SCRIPT_START + i
        print(f"  0x{abs_addr:X} (+{i:04X}): {hex_str} | {ascii_str}")

# SECTION 3: Type-8 target data (the deep bytecode)
print(f"\n=== TYPE-8 TARGET DATA ===")
type8_offsets = [0x1DC0, 0x1FC4]
for t8_off in type8_offsets:
    abs_addr = SCRIPT_START + t8_off
    print(f"\n  --- Type-8 target at script+0x{t8_off:X} = abs 0x{abs_addr:X} ---")
    for i in range(0, 512, 16):
        if t8_off + i >= len(region):
            break
        chunk = region[t8_off + i:t8_off + i + 16]
        if len(chunk) < 16:
            break
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        u16s = [struct.unpack_from('<H', chunk, j)[0] for j in range(0, min(16, len(chunk)), 2)]
        u16_str = ' '.join(f'{v:5d}' for v in u16s)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"    +{i:03X}: {hex_str}  | {ascii_str}")

# SECTION 4: Region between spawn commands and type-8 targets
# This is the big unknown region: ~script+0x900 to +0x1DC0
print(f"\n=== BIG UNKNOWN REGION: script+0x0900 to +0x1DC0 ===")
print(f"  Size: {0x1DC0 - 0x0900} bytes")

# Show first 512 bytes of this region
print(f"\n  First 512 bytes (script+0x900 to +0xB00):")
for i in range(0x900, min(0xB00, len(region)), 16):
    chunk = region[i:i+16]
    if any(b != 0 for b in chunk):
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        abs_addr = SCRIPT_START + i
        print(f"    0x{abs_addr:X} (+{i:04X}): {hex_str}  | {ascii_str}")

# Show 512 bytes near middle
mid = (0x900 + 0x1DC0) // 2
print(f"\n  Middle section (script+0x{mid:X} to +0x{mid+0x200:X}):")
for i in range(mid, min(mid + 0x200, len(region)), 16):
    chunk = region[i:i+16]
    if any(b != 0 for b in chunk):
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        abs_addr = SCRIPT_START + i
        print(f"    0x{abs_addr:X} (+{i:04X}): {hex_str}  | {ascii_str}")

# Show last 512 bytes before type-8 target
print(f"\n  Before type-8 target (script+0x{0x1DC0-0x200:X} to +0x1DC0):")
for i in range(0x1DC0 - 0x200, min(0x1DC0, len(region)), 16):
    chunk = region[i:i+16]
    if any(b != 0 for b in chunk):
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        abs_addr = SCRIPT_START + i
        print(f"    0x{abs_addr:X} (+{i:04X}): {hex_str}  | {ascii_str}")

# SECTION 5: Look for slot references (0, 1, 2) in structured positions
# throughout the unknown region
print(f"\n=== SLOT REFERENCE SEARCH in script+0x600 to +0x1DC0 ===")
print(f"  Looking for patterns that differentiate per slot (0, 1, 2)...")

# Look for [XX 0B] patterns (the spawn command prefix)
count_0b = 0
for i in range(0x600, min(0x1DC0, len(region)) - 2):
    if region[i+1] == 0x0B and region[i] <= 3 and region[i+3] == 0x00:
        abs_addr = SCRIPT_START + i
        ctx = region[max(0,i-4):min(len(region),i+12)]
        print(f"  [XX 0B] at +{i:04X} (0x{abs_addr:X}): XX={region[i]} YY=0x{region[i+2]:02X}  ctx: {ctx.hex()}")
        count_0b += 1

print(f"  Found {count_0b} [XX 0B YY 00] patterns")

# Look for [FFFFFFFFFFFF] terminators
print(f"\n  FF-terminators in unknown region:")
count_ff = 0
for i in range(0x600, min(0x1DC0, len(region)) - 6):
    if region[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
        slot_after = struct.unpack_from('<H', region, i+6)[0] if i+8 <= len(region) else -1
        val_before = struct.unpack_from('<H', region, i-2)[0] if i >= 2 else -1
        abs_addr = SCRIPT_START + i
        # context
        ctx = region[max(0,i-8):min(len(region),i+12)]
        print(f"    +{i:04X} (0x{abs_addr:X}): val_before={val_before:5d} slot_after={slot_after:3d}  ctx: {ctx.hex()}")
        count_ff += 1

print(f"  Found {count_ff} FFFFFFFFFFFF terminators")

# SECTION 6: look for per-slot patterns in blocks of 8, 16, 32 bytes
# If there are 3 monsters, look for any group of 3 related values
print(f"\n=== TRIPLET PATTERNS in script+0x600 to +0x1DC0 ===")
for stride in [2, 4, 8, 16, 32]:
    found = 0
    for i in range(0x600, min(0x1DC0, len(region)) - 3 * stride, stride):
        if stride == 2:
            vals = [struct.unpack_from('<H', region, i + j * stride)[0] for j in range(3)]
        elif stride == 4:
            vals = [struct.unpack_from('<I', region, i + j * stride)[0] for j in range(3)]
        else:
            # Just compare first 4 bytes
            vals = [struct.unpack_from('<I', region, i + j * stride)[0] for j in range(3)]

        # Look for triplets that are: all nonzero, all different, reasonable range
        if (all(v != 0 for v in vals) and
            all(v != 0xFFFFFFFF for v in vals) and
            len(set(vals)) == 3 and
            all(v < 0x10000 for v in vals)):
            abs_addr = SCRIPT_START + i
            if found < 5:  # only show first 5 per stride
                print(f"  stride={stride:2d} at +{i:04X} (0x{abs_addr:X}): {[f'0x{v:X}' for v in vals]}")
            found += 1
    if found > 5:
        print(f"  ... and {found - 5} more")
    elif found == 0:
        print(f"  stride={stride:2d}: none found")

# SECTION 7: Configuration block around script+0x900
# Previously found: 08 00 FF 05 14 00 01 00 01 00 01 01
print(f"\n=== CONFIG BLOCK at script+0x898 to +0x920 ===")
for i in range(0x898, min(0x920, len(region)), 8):
    chunk = region[i:i+8]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    u16s = [struct.unpack_from('<H', chunk, j)[0] for j in range(0, min(8, len(chunk)), 2)]
    abs_addr = SCRIPT_START + i
    print(f"  0x{abs_addr:X} (+{i:04X}): {hex_str}  | u16: {u16s}")

print(f"\n{'='*80}")
print("  DONE")
print(f"{'='*80}")
