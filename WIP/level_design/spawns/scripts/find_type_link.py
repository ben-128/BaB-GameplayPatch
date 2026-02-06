"""
Find what links a spawned monster to its visual/AI/loot type.

Strategy: For each spawn group, dump the area BEFORE the name entries
and look for consistent patterns that could be monster type IDs.

We know:
- The 96-byte entries (name+stats) start at the group offset
- Changing name+stats does NOT change visual/AI/loot
- The executable has AI handlers indexed by a "type ID" (e.g. 0x18 for Goblin-Shaman)
- That type ID must be stored somewhere in the spawn/level data
"""

import struct
import json
import os

BLAZE_ALL = r"Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL"
EXE_FILE = r"Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45"

# Load all spawn groups from all zone files
SPAWN_DIR = r"WIP\level_design\spawns\data\spawn_groups"

# Monster name -> _index.json ID mapping
INDEX_FILE = r"Data\monster_stats\_index.json"

def load_monster_index():
    with open(INDEX_FILE, 'r') as f:
        data = json.load(f)
    return {m['name']: m for m in data['monsters']}

def load_all_spawn_groups():
    groups = []
    for fname in os.listdir(SPAWN_DIR):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(SPAWN_DIR, fname), 'r') as f:
            data = json.load(f)
        level = data.get('level_name', fname)
        for g in data['groups']:
            groups.append({
                'level': level,
                'name': g['name'],
                'offset': int(g['offset'], 16),
                'monsters': g['monsters'],
                'num_monsters': len(g['monsters'])
            })
    return groups

def hex_dump(data, base_offset, highlight_bytes=None):
    """Pretty hex dump with optional byte highlighting."""
    lines = []
    for i in range(0, len(data), 16):
        addr = base_offset + i
        hex_parts = []
        ascii_parts = []
        for j in range(16):
            if i + j < len(data):
                b = data[i + j]
                hex_parts.append(f'{b:02X}')
                ascii_parts.append(chr(b) if 32 <= b < 127 else '.')
            else:
                hex_parts.append('  ')
                ascii_parts.append(' ')
        hex_str = ' '.join(hex_parts)
        ascii_str = ''.join(ascii_parts)
        lines.append(f'  {addr:08X}  {hex_str}  {ascii_str}')
    return '\n'.join(lines)

def analyze_pre_group_region(blaze_data, group, monster_index):
    """Analyze the region before a spawn group's name entries."""
    offset = group['offset']
    num_monsters = group['num_monsters']

    # Read monster names at the group offset to verify
    names_found = []
    for i in range(num_monsters):
        name_offset = offset + i * 96
        if name_offset + 16 <= len(blaze_data):
            name_bytes = blaze_data[name_offset:name_offset + 16]
            name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace')
            names_found.append(name)

    # Compute expected end of group (after all 96-byte entries)
    group_end = offset + num_monsters * 96

    # Read 512 bytes before the group AND the first 32 bytes of the group
    pre_size = 512
    pre_start = max(0, offset - pre_size)
    pre_data = blaze_data[pre_start:offset]

    # Also read the area AFTER the stats entries (between this group and next data)
    post_data = blaze_data[group_end:group_end + 256]

    return {
        'names_found': names_found,
        'pre_data': pre_data,
        'pre_start': pre_start,
        'post_data': post_data,
        'post_start': group_end,
    }

def search_for_small_values(data, base_offset, max_val=127):
    """Find sequences of small values that could be type IDs.
    Look for groups of 1-6 small values (matching monster count)."""
    results = []
    for i in range(len(data) - 1):
        val = data[i]
        if 0 < val <= max_val:
            # Check if this could be part of a sequence
            seq = [val]
            pos = [i]
            j = i + 1
            # Look for next values with small gaps (1-8 bytes apart)
            while j < min(len(data), i + 64) and len(seq) < 8:
                if 0 < data[j] <= max_val and data[j] != data[j-1]:
                    seq.append(data[j])
                    pos.append(j)
                j += 1
                if j < len(data) and data[j] == 0 and j - pos[-1] > 4:
                    break
            if len(seq) >= 2:
                results.append({
                    'offset': base_offset + i,
                    'values': seq,
                    'positions': [base_offset + p for p in pos]
                })
    return results

def find_repeating_structure(data, base_offset):
    """Find repeating fixed-size structures in the data."""
    results = []
    # Try different structure sizes (common: 4, 8, 12, 16, 20, 24, 32)
    for struct_size in [4, 8, 12, 16, 20, 24, 28, 32]:
        for start in range(min(len(data) - struct_size * 3, 256)):
            # Check if there's a repeating pattern
            matches = 0
            for k in range(1, min(8, (len(data) - start) // struct_size)):
                s1 = data[start:start + struct_size]
                s2 = data[start + k * struct_size:start + (k + 1) * struct_size]
                if len(s2) < struct_size:
                    break
                # Check structural similarity (same zero positions, similar value ranges)
                zero_match = sum(1 for a, b in zip(s1, s2) if (a == 0) == (b == 0))
                if zero_match >= struct_size * 0.6:
                    matches += 1
            if matches >= 2:
                results.append({
                    'offset': base_offset + start,
                    'struct_size': struct_size,
                    'repeats': matches + 1,
                    'first_entries': [
                        data[start + k * struct_size:start + (k + 1) * struct_size].hex()
                        for k in range(min(matches + 1, 6))
                    ]
                })
    return results

def main():
    print("=" * 80)
    print("MONSTER TYPE LINK ANALYSIS")
    print("=" * 80)

    monster_index = load_monster_index()
    groups = load_all_spawn_groups()

    print(f"\nLoaded {len(groups)} spawn groups across multiple zones")
    print(f"Loaded {len(monster_index)} monsters from index")

    with open(BLAZE_ALL, 'rb') as f:
        blaze_data = f.read()

    print(f"BLAZE.ALL size: {len(blaze_data)} bytes")

    # For each group, analyze the pre-group region
    print("\n" + "=" * 80)
    print("PHASE 1: RAW HEX DUMP - 256 bytes before each group")
    print("=" * 80)

    for group in groups[:12]:  # Analyze first 12 groups across zones
        offset = group['offset']
        num = group['num_monsters']

        print(f"\n{'-' * 80}")
        print(f"  {group['level']} / {group['name']}")
        print(f"  Offset: 0x{offset:X} | Monsters: {num} | {', '.join(group['monsters'])}")
        print(f"{'-' * 80}")

        # Verify names at offset
        for i in range(num):
            name_off = offset + i * 96
            name = blaze_data[name_off:name_off + 16].split(b'\x00')[0].decode('ascii', errors='replace')
            # Read stat0 (first uint16 after name)
            stat0 = struct.unpack_from('<H', blaze_data, name_off + 16)[0]
            stat1 = struct.unpack_from('<H', blaze_data, name_off + 18)[0]
            print(f"  Slot {i}: '{name}' stat0={stat0} stat1={stat1}")

        # Dump 256 bytes before the names
        pre_start = offset - 256
        pre_data = blaze_data[pre_start:offset]
        print(f"\n  --- Pre-group data (0x{pre_start:X} to 0x{offset:X}) ---")
        print(hex_dump(pre_data, pre_start))

        # Also dump 64 bytes AFTER the last 96-byte entry
        post_offset = offset + num * 96
        post_data = blaze_data[post_offset:post_offset + 64]
        print(f"\n  --- Post-group data (0x{post_offset:X}) ---")
        print(hex_dump(post_data, post_offset))

    # PHASE 2: Look at the SAME relative offsets across all groups
    print("\n" + "=" * 80)
    print("PHASE 2: COMPARE SPECIFIC OFFSETS ACROSS ALL GROUPS")
    print("=" * 80)

    # For each relative offset before the group, collect the values
    for rel_off in [-0x08, -0x10, -0x18, -0x20, -0x28, -0x30, -0x38, -0x40,
                    -0x48, -0x50, -0x58, -0x60, -0x68, -0x70, -0x78, -0x80]:
        print(f"\n  Relative offset {rel_off:#x} ({rel_off}):")
        for group in groups[:12]:
            abs_off = group['offset'] + rel_off
            if abs_off >= 0 and abs_off + 8 <= len(blaze_data):
                chunk = blaze_data[abs_off:abs_off + 8]
                vals_u8 = list(chunk)
                vals_u16 = [struct.unpack_from('<H', chunk, i)[0] for i in range(0, 8, 2)]
                vals_u32 = [struct.unpack_from('<I', chunk, i)[0] for i in range(0, 8, 4)]
                print(f"    {group['level']:20s} {group['name']:20s} "
                      f"u8={vals_u8}  u16={vals_u16}  hex={chunk.hex()}")

    # PHASE 3: Look for the number of monsters (count field) near the group
    print("\n" + "=" * 80)
    print("PHASE 3: SEARCH FOR MONSTER COUNT NEAR GROUP START")
    print("=" * 80)

    for group in groups[:12]:
        offset = group['offset']
        num = group['num_monsters']

        # Search for the monster count value in the 512 bytes before the group
        count_positions = []
        for i in range(512):
            check_off = offset - 512 + i
            if check_off >= 0:
                val = blaze_data[check_off]
                if val == num:
                    # Check if it's in a reasonable context (not in middle of text)
                    count_positions.append(offset - 512 + i)

        # Also check as uint16
        count_positions_u16 = []
        for i in range(512):
            check_off = offset - 512 + i
            if check_off >= 0 and check_off + 1 < len(blaze_data):
                val = struct.unpack_from('<H', blaze_data, check_off)[0]
                if val == num:
                    count_positions_u16.append(offset - 512 + i)

        if count_positions:
            # Show only the last few (closest to group)
            nearby = [p for p in count_positions if offset - p <= 128]
            if nearby:
                offsets_str = ', '.join(f'0x{p:X} (rel {p - offset:#x})' for p in nearby[-8:])
                print(f"  {group['level']:20s} {group['name']:20s} "
                      f"count={num} found at: {offsets_str}")

    # PHASE 4: Look at the EXE jump table
    print("\n" + "=" * 80)
    print("PHASE 4: EXE AI HANDLER JUMP TABLE (offset 0x02BDE0)")
    print("=" * 80)

    with open(EXE_FILE, 'rb') as f:
        exe_data = f.read()

    # The jump table at 0x02BDE0 maps type ID to handler address
    # PS1 uses 32-bit MIPS addresses
    jt_offset = 0x02BDE0
    print(f"\n  Jump table at file offset 0x{jt_offset:X}:")
    for type_id in range(0x40):  # First 64 entries
        if jt_offset + type_id * 4 + 4 <= len(exe_data):
            handler = struct.unpack_from('<I', exe_data, jt_offset + type_id * 4)[0]
            if handler != 0:
                print(f"    Type 0x{type_id:02X} ({type_id:3d}) -> handler 0x{handler:08X}")

    # PHASE 5: Search for 4-byte or 2-byte fields that match expected type IDs
    # We need to figure out what the type IDs actually are per monster
    # Hypothesis: look for small unique values in the pre-group data that
    # appear in groups matching the monster count
    print("\n" + "=" * 80)
    print("PHASE 5: STRUCTURED SEARCH - Look for N-tuples matching monster count")
    print("=" * 80)

    for group in groups[:12]:
        offset = group['offset']
        num = group['num_monsters']

        # Read 1024 bytes before
        scan_size = 1024
        scan_start = max(0, offset - scan_size)
        scan_data = blaze_data[scan_start:offset]

        # Look for sequences of exactly N uint16 values (each 0-127)
        # that appear consecutively or with fixed stride
        findings = []

        # Try consecutive uint16 values
        for i in range(len(scan_data) - num * 2):
            vals = []
            for j in range(num):
                v = struct.unpack_from('<H', scan_data, i + j * 2)[0]
                vals.append(v)
            # Check if all values are in reasonable type ID range (0-127)
            if all(0 < v < 128 for v in vals):
                # And they should be somewhat diverse (not all the same)
                if len(set(vals)) >= min(2, num):
                    abs_pos = scan_start + i
                    findings.append({
                        'offset': abs_pos,
                        'rel': abs_pos - offset,
                        'values': vals,
                        'stride': 2
                    })

        # Try uint16 with stride 4 (interleaved with other data)
        for stride in [4, 8, 12, 16]:
            for i in range(len(scan_data) - num * stride):
                vals = []
                for j in range(num):
                    if i + j * stride + 2 <= len(scan_data):
                        v = struct.unpack_from('<H', scan_data, i + j * stride)[0]
                        vals.append(v)
                if len(vals) == num and all(0 < v < 128 for v in vals):
                    if len(set(vals)) >= min(2, num):
                        abs_pos = scan_start + i
                        findings.append({
                            'offset': abs_pos,
                            'rel': abs_pos - offset,
                            'values': vals,
                            'stride': stride
                        })

        # Try uint8 with stride 1
        for i in range(len(scan_data) - num):
            vals = [scan_data[i + j] for j in range(num)]
            if all(0 < v < 128 for v in vals):
                if len(set(vals)) >= min(2, num):
                    abs_pos = scan_start + i
                    findings.append({
                        'offset': abs_pos,
                        'rel': abs_pos - offset,
                        'values': vals,
                        'stride': 1
                    })

        if findings:
            # Filter: only show findings close to the group (within 256 bytes)
            close = [f for f in findings if abs(f['rel']) <= 256]
            if close:
                print(f"\n  {group['level']} / {group['name']} ({num} monsters: {', '.join(group['monsters'])})")
                # Deduplicate and show unique
                seen = set()
                for f in close[-30:]:
                    key = (f['rel'], f['stride'])
                    if key not in seen:
                        seen.add(key)
                        print(f"    rel={f['rel']:#06x} stride={f['stride']} values={f['values']}")

if __name__ == '__main__':
    main()
