#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Analyze monster formation composition in Blaze & Blade script areas.

Goal: Find what controls the NUMBER and COMPOSITION of monsters per spawn
(e.g., "3 goblins + 2 bats" vs "1 shaman + 4 bats").

Scans the script area after 96-byte entries for:
- Monster ID bytes and their surrounding context
- Repeating structures / record patterns
- Possible formation tables near the start of script area
"""

import struct
from pathlib import Path

# ---- Configuration ----
PROJECT_ROOT = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch")
BLAZE_ALL_PRIMARY = PROJECT_ROOT / "output" / "BLAZE.ALL"
BLAZE_ALL_FALLBACK = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# Monster IDs from _index.json
MONSTER_NAMES = {
    48: "Giant-Ant",     49: "Giant-Bat",      50: "Giant-Beetle",
    51: "Giant-Centipede", 52: "Giant-Club",   53: "Giant-Scorpion",
    54: "Giant-Snake",   55: "Giant-Spider",    56: "Giant",
    57: "Goblin-Fly",    58: "Goblin-Leader",   59: "Goblin-Shaman",
    60: "Goblin-Wizard", 61: "Goblin",          79: "Kobold",
    84: "Lv20.Goblin",   86: "Lv30.Goblin",     88: "Lv6.Kobold",
    26: "Big-Viper",     34: "Cave-Bear",       35: "Cave-Scissors",
    77: "Killer-Fish",   107: "Spirit-Ball",    32: "Blue-Slime",
    95: "Ogre",          64: "Green-Giant",     109: "Succubus",
    45: "Gargoyle",      46: "Ghost",           47: "Ghoul",
    75: "Killer-Bear",   76: "Killer-Bee",
}

# Areas to analyze
AREAS = [
    {
        "name": "Cavern Floor 1 Area 1",
        "group_offset": 0xF7A97C,
        "num_monsters": 3,
        "monsters": {84: "Lv20.Goblin", 59: "Goblin-Shaman", 49: "Giant-Bat"},
        "next_group_offset": 0xF7E1A8,
    },
    {
        "name": "Cavern Floor 1 Area 2",
        "group_offset": 0xF7E1A8,
        "num_monsters": 4,
        "monsters": {84: "Lv20.Goblin", 59: "Goblin-Shaman", 49: "Giant-Bat", 58: "Goblin-Leader"},
        "next_group_offset": 0xF819A0,
    },
]


def hex_dump(data, base_offset, bytes_per_line=16, highlight_offsets=None):
    """Print hex dump with optional byte highlighting."""
    if highlight_offsets is None:
        highlight_offsets = set()
    lines = []
    for i in range(0, len(data), bytes_per_line):
        addr = base_offset + i
        hex_parts = []
        ascii_parts = []
        for j in range(bytes_per_line):
            if i + j < len(data):
                b = data[i + j]
                hex_parts.append('{:02X}'.format(b))
                ascii_parts.append(chr(b) if 32 <= b < 127 else '.')
            else:
                hex_parts.append('  ')
                ascii_parts.append(' ')
        hex_str = ' '.join(hex_parts[:8]) + '  ' + ' '.join(hex_parts[8:16])
        ascii_str = ''.join(ascii_parts)
        lines.append('  {:08X}  {}  |{}|'.format(addr, hex_str, ascii_str))
    return '\n'.join(lines)


def is_in_ascii_string(data, pos, min_run=4):
    """Check if byte at pos is inside a run of printable ASCII characters."""
    # Count printable ASCII in both directions
    count_before = 0
    for i in range(pos - 1, max(pos - 20, -1), -1):
        if i < 0:
            break
        if 32 <= data[i] < 127:
            count_before += 1
        else:
            break
    count_after = 0
    for i in range(pos + 1, min(pos + 20, len(data))):
        if 32 <= data[i] < 127:
            count_after += 1
        else:
            break
    return (count_before + count_after) >= min_run


def find_monster_id_occurrences(data, base_offset, monster_ids, label=""):
    """Find all occurrences of monster IDs as bytes, filtering ASCII false positives."""
    results = []
    for i in range(len(data)):
        b = data[i]
        if b in monster_ids:
            if is_in_ascii_string(data, i):
                continue  # Skip - this is inside text
            results.append((i, b))
    return results


def analyze_context_around_hit(data, base_offset, pos, byte_val, context_before=32, context_after=16):
    """Analyze and print context around a monster ID hit."""
    start = max(0, pos - context_before)
    end = min(len(data), pos + context_after + 1)
    chunk = data[start:end]
    abs_pos = base_offset + pos

    # Relative position of the hit within chunk
    hit_in_chunk = pos - start

    name = MONSTER_NAMES.get(byte_val, "???")
    print("    Hit at 0x{:08X}: byte 0x{:02X} ({}) = {}".format(abs_pos, byte_val, byte_val, name))

    # Print context hex
    print("    Context ({} bytes before, {} bytes after):".format(pos - start, end - pos - 1))
    print(hex_dump(chunk, base_offset + start))

    # Look at specific fields relative to the hit
    if pos >= 1:
        byte_before = data[pos - 1]
        print("      byte[-1] = 0x{:02X} ({})".format(byte_before, byte_before))
    if pos + 1 < len(data):
        byte_after = data[pos + 1]
        print("      byte[+1] = 0x{:02X} ({}) -- possible count?".format(byte_after, byte_after))
    if pos + 2 < len(data):
        byte_after2 = data[pos + 2]
        print("      byte[+2] = 0x{:02X} ({})".format(byte_after2, byte_after2))

    # Check if this could be uint16 LE
    if pos + 1 < len(data):
        val16 = struct.unpack_from('<H', data, pos)[0]
        print("      as uint16 LE: 0x{:04X} ({})".format(val16, val16))

    print()
    return abs_pos


def scan_for_repeating_structures(data, base_offset, start_rel=0, end_rel=None, label=""):
    """Look for repeating record structures (fixed-size blocks) in data."""
    if end_rel is None:
        end_rel = len(data)
    region = data[start_rel:end_rel]

    print("  --- Repeating structure scan ({}) ---".format(label))
    print("  Region: 0x{:08X} to 0x{:08X} ({} bytes)".format(
        base_offset + start_rel, base_offset + end_rel, end_rel - start_rel))

    # Find FF FF FF FF terminators as potential record boundaries
    ff_positions = []
    for i in range(len(region) - 3):
        if region[i:i+4] == b'\xff\xff\xff\xff':
            ff_positions.append(i + start_rel)  # absolute within data

    if ff_positions:
        print("  Found {} FF-FF-FF-FF markers at:".format(len(ff_positions)))
        for p in ff_positions:
            print("    0x{:08X} (rel +0x{:X})".format(base_offset + p, p))

        # Calculate gaps between FF markers
        if len(ff_positions) >= 2:
            gaps = [ff_positions[i+1] - ff_positions[i] for i in range(len(ff_positions)-1)]
            print("  Gaps between FF markers: {}".format(gaps))
            # Check if gaps are consistent
            if len(set(gaps)) == 1:
                print("  ** CONSISTENT gap size: {} bytes **".format(gaps[0]))
            else:
                print("  Gaps vary (min={}, max={}, unique={})".format(
                    min(gaps), max(gaps), sorted(set(gaps))))
    else:
        print("  No FF-FF-FF-FF markers found in this region")

    # Also look for 00 00 00 00 blocks as padding/separators
    zero4_positions = []
    for i in range(len(region) - 3):
        if region[i:i+4] == b'\x00\x00\x00\x00' and (i == 0 or region[i-1:i] != b'\x00'):
            zero4_positions.append(i + start_rel)

    if zero4_positions and len(zero4_positions) < 50:
        print("  Found {} zero-4 boundaries".format(len(zero4_positions)))
        if len(zero4_positions) >= 2 and len(zero4_positions) <= 20:
            gaps = [zero4_positions[i+1] - zero4_positions[i] for i in range(len(zero4_positions)-1)]
            print("  Gaps: {}".format(gaps[:20]))
    print()


def analyze_script_area_start(data, base_offset, num_bytes=256):
    """Analyze the first N bytes of the script area for formation table."""
    region = data[:num_bytes]
    print("  --- First {} bytes of script area (possible formation index) ---".format(num_bytes))
    print(hex_dump(region, base_offset))
    print()

    # Look for small integers that could be monster counts (1-6)
    print("  Bytes with value 1-6 (possible monster counts):")
    for i, b in enumerate(region):
        if 1 <= b <= 6:
            if not is_in_ascii_string(data, i):
                abs_pos = base_offset + i
                # Show context of 4 bytes around it
                ctx_start = max(0, i - 4)
                ctx_end = min(len(region), i + 5)
                ctx = region[ctx_start:ctx_end]
                ctx_hex = ' '.join('{:02X}'.format(x) for x in ctx)
                print("    0x{:08X}: value={}, context: {}".format(abs_pos, b, ctx_hex))
    print()


def look_for_spawn_commands(data, base_offset, monster_ids):
    """Look for potential spawn command structures containing monster IDs.

    Hypothesis: spawn commands might be variable-length records like:
    [opcode] [monster_slot_index] [count] [x,y,z coords...]
    or fixed-size formation records.
    """
    print("  --- Spawn command structure analysis ---")

    # First, find ALL hits
    hits = find_monster_id_occurrences(data, base_offset, monster_ids)
    print("  Total non-ASCII hits for target monster IDs: {}".format(len(hits)))

    id_counts = {}
    for pos, val in hits:
        name = MONSTER_NAMES.get(val, "???")
        id_counts[val] = id_counts.get(val, 0) + 1
    print("  Hit counts per monster ID:")
    for mid, count in sorted(id_counts.items()):
        name = MONSTER_NAMES.get(mid, "???")
        print("    0x{:02X} ({:3d}) {}: {} occurrences".format(mid, mid, name, count))
    print()

    # For each hit, check if there's a consistent byte at a fixed offset
    # that could be a "count" field
    if hits:
        print("  Detailed context for each hit:")
        print("  " + "=" * 76)

    hit_abs_positions = []
    for pos, val in hits:
        abs_pos = analyze_context_around_hit(data, base_offset, pos, val)
        hit_abs_positions.append(abs_pos)

    # Check if hits cluster at regular intervals
    if len(hit_abs_positions) >= 2:
        gaps = [hit_abs_positions[i+1] - hit_abs_positions[i]
                for i in range(len(hit_abs_positions) - 1)]
        print("  Gaps between consecutive hits: {}".format(gaps))
        print()

    return hits


def search_uint16_monster_ids(data, base_offset, monster_ids):
    """Search for monster IDs as uint16 LE values."""
    print("  --- uint16 LE monster ID search ---")
    hits = []
    for i in range(len(data) - 1):
        val = struct.unpack_from('<H', data, i)[0]
        if val in monster_ids:
            if not is_in_ascii_string(data, i) and not is_in_ascii_string(data, i + 1):
                abs_pos = base_offset + i
                name = MONSTER_NAMES.get(val, "???")
                hits.append((i, val))
                # Show context
                start = max(0, i - 8)
                end = min(len(data), i + 10)
                chunk = data[start:end]
                print("    0x{:08X}: uint16=0x{:04X} ({}) = {}".format(
                    abs_pos, val, val, name))
                print(hex_dump(chunk, base_offset + start))
                print()
    print("  Found {} uint16 LE hits".format(len(hits)))
    print()
    return hits


def search_slot_index_patterns(data, base_offset, num_monsters):
    """Look for patterns using slot indices (0,1,2 or 1,2,3) instead of global IDs."""
    print("  --- Slot index pattern search (0-based and 1-based for {} monsters) ---".format(num_monsters))

    # Look for sequences like 00 xx 01 xx 02 xx (slot + something)
    for stride in [2, 4, 8, 12, 16, 20, 24, 28, 32]:
        for start_val in [0, 1]:
            for i in range(len(data) - stride * num_monsters):
                match = True
                for slot in range(num_monsters):
                    expected = start_val + slot
                    if data[i + slot * stride] != expected:
                        match = False
                        break
                if match:
                    # Verify it's not in ASCII
                    if is_in_ascii_string(data, i):
                        continue
                    abs_pos = base_offset + i
                    end = i + stride * num_monsters
                    chunk = data[i:min(end + 8, len(data))]
                    print("    0x{:08X}: stride={}, start={}, match!".format(
                        abs_pos, stride, start_val))
                    print(hex_dump(chunk, abs_pos))
                    print()
    print()


def analyze_opcode_distribution(data, base_offset, first_n=512):
    """Analyze byte value distribution in the first N bytes to find opcodes."""
    region = data[:min(first_n, len(data))]
    print("  --- Byte value distribution (first {} bytes) ---".format(len(region)))

    counts = {}
    for b in region:
        counts[b] = counts.get(b, 0) + 1

    # Show top-20 most frequent values
    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])[:20]
    print("  Top 20 most frequent byte values:")
    for val, cnt in sorted_counts:
        name = MONSTER_NAMES.get(val, "")
        extra = " <- {}".format(name) if name else ""
        print("    0x{:02X} ({:3d}): {:3d} times{}".format(val, val, cnt, extra))
    print()


def cross_area_comparison(blaze, areas):
    """Compare script area structures between two areas."""
    print("=" * 80)
    print("  CROSS-AREA COMPARISON")
    print("=" * 80)
    print()

    for area in areas:
        name = area["name"]
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        script_size = next_off - script_start

        print("  {} script area: 0x{:X} to 0x{:X} ({} bytes)".format(
            name, script_start, next_off, script_size))

        data = blaze[script_start:next_off]

        # Find first non-zero run
        first_nonzero = None
        for i, b in enumerate(data):
            if b != 0:
                first_nonzero = i
                break
        if first_nonzero is not None:
            print("    First non-zero byte at relative +0x{:X} (abs 0x{:X})".format(
                first_nonzero, script_start + first_nonzero))

        # Find all FF FF FF FF positions
        ff_positions = []
        for i in range(len(data) - 3):
            if data[i:i+4] == b'\xff\xff\xff\xff':
                ff_positions.append(i)
        print("    FF-FF-FF-FF count: {}".format(len(ff_positions)))
        if ff_positions[:10]:
            print("    First 10 FF positions (relative): {}".format(
                ['0x{:X}'.format(p) for p in ff_positions[:10]]))

        # Find text strings
        text_runs = []
        run_start = None
        for i in range(len(data)):
            if 32 <= data[i] < 127:
                if run_start is None:
                    run_start = i
            else:
                if run_start is not None and (i - run_start) >= 6:
                    text = data[run_start:i].decode('ascii', errors='replace')
                    text_runs.append((run_start, text))
                run_start = None
        if text_runs:
            print("    Text strings found: {}".format(len(text_runs)))
            for pos, text in text_runs[:5]:
                print("      0x{:X}: \"{}\"".format(script_start + pos, text[:60]))
            if len(text_runs) > 5:
                print("      ... and {} more".format(len(text_runs) - 5))

        print()


def deep_dive_script_start(blaze, area):
    """Deep dive into the first 1KB of script area looking for formation records."""
    group_off = area["group_offset"]
    num_m = area["num_monsters"]
    script_start = group_off + num_m * 96
    next_off = area["next_group_offset"]
    monsters = area["monsters"]

    data = blaze[script_start:next_off]

    print("  --- DEEP DIVE: {} ---".format(area["name"]))
    print("  Script area: 0x{:X} to 0x{:X} ({} bytes)".format(
        script_start, next_off, next_off - script_start))
    print("  Monsters: {}".format(
        ", ".join("0x{:02X}={}".format(k, v) for k, v in sorted(monsters.items()))))
    print()

    # 1. Full hex dump of first 512 bytes
    print("  [First 512 bytes of script area]")
    print(hex_dump(data[:512], script_start))
    print()

    # 2. Search for monster IDs as single bytes
    print("  [Monster ID byte search in FULL script area]")
    look_for_spawn_commands(data, script_start, set(monsters.keys()))

    # 3. Search for monster IDs as uint16 LE
    print("  [Monster ID uint16 LE search in first 2048 bytes]")
    search_uint16_monster_ids(data[:2048], script_start, set(monsters.keys()))

    # 4. Slot index patterns
    print("  [Slot index patterns in first 2048 bytes]")
    search_slot_index_patterns(data[:2048], script_start, num_m)

    # 5. Repeating structures
    scan_for_repeating_structures(data, script_start, 0, min(2048, len(data)),
                                   "first 2KB")

    # 6. Analyze byte distribution
    analyze_opcode_distribution(data, script_start)

    # 7. Look for the script area start structure
    analyze_script_area_start(data, script_start)


def look_for_formation_table_before_scripts(blaze, area):
    """Check if there's a formation table BEFORE the script area
    but AFTER the 96-byte entries. Sometimes there's a gap."""
    group_off = area["group_offset"]
    num_m = area["num_monsters"]
    entries_end = group_off + num_m * 96

    print("  --- Region immediately after 96-byte entries ---")
    print("  Entries end at 0x{:X}".format(entries_end))

    # Dump 64 bytes right after entries end
    data = blaze[entries_end:entries_end + 64]
    print("  [First 64 bytes after entries]")
    print(hex_dump(data, entries_end))
    print()


def scan_for_02D_opcodes(data, base_offset, limit=4096):
    """Search for 0x2C/0x2D opcodes which were noted as potential spawn commands."""
    region = data[:min(limit, len(data))]
    print("  --- Opcode 0x2C/0x2D scan (first {} bytes) ---".format(len(region)))

    for opcode in [0x2C, 0x2D, 0x0D, 0x04]:
        positions = []
        for i, b in enumerate(region):
            if b == opcode and not is_in_ascii_string(data, i):
                positions.append(i)
        if positions:
            print("  Opcode 0x{:02X}: {} occurrences".format(opcode, len(positions)))
            for p in positions[:5]:
                abs_pos = base_offset + p
                # Show 16 bytes starting from opcode
                chunk = data[p:min(p + 24, len(data))]
                hex_str = ' '.join('{:02X}'.format(x) for x in chunk)
                print("    0x{:08X}: {}".format(abs_pos, hex_str))
            if len(positions) > 5:
                print("    ... and {} more".format(len(positions) - 5))
    print()


def main():
    # Load BLAZE.ALL
    blaze_path = BLAZE_ALL_PRIMARY if BLAZE_ALL_PRIMARY.exists() else BLAZE_ALL_FALLBACK
    print("Loading BLAZE.ALL from: {}".format(blaze_path))
    blaze = bytearray(blaze_path.read_bytes())
    print("File size: {} bytes (0x{:X})".format(len(blaze), len(blaze)))
    print()

    # ===================================================================
    # PART 1: Deep dive into each area's script area
    # ===================================================================
    for area in AREAS:
        print("=" * 80)
        print("  AREA: {}".format(area["name"]))
        print("=" * 80)
        print()

        look_for_formation_table_before_scripts(blaze, area)

        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]

        # Opcode scan
        scan_for_02D_opcodes(data, script_start)

        deep_dive_script_start(blaze, area)

        print()
        print("-" * 80)
        print()

    # ===================================================================
    # PART 2: Cross-area comparison
    # ===================================================================
    cross_area_comparison(blaze, AREAS)

    # ===================================================================
    # PART 3: Look for any "formation table" structure that lists
    # (monster_slot, count) tuples. Try different record sizes.
    # ===================================================================
    print("=" * 80)
    print("  PART 3: FORMATION TABLE HYPOTHESIS")
    print("=" * 80)
    print()

    for area in AREAS:
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]
        monsters = area["monsters"]

        print("  --- {} ---".format(area["name"]))
        print("  Looking for (slot_index, count) pairs where count=1..6:")
        print()

        # Search for bytes 0x00-0x02 (slot indices for 3 monsters) followed by 1-6
        for i in range(len(data) - 1):
            slot = data[i]
            count = data[i + 1]
            if slot < num_m and 1 <= count <= 6:
                # Check it's not in ASCII
                if is_in_ascii_string(data, i):
                    continue
                # Only show if this looks structural (not random)
                # Check if nearby bytes also form slot+count pairs
                nearby_pairs = 0
                for j in range(max(0, i - 16), min(len(data) - 1, i + 16)):
                    s = data[j]
                    c = data[j + 1]
                    if s < num_m and 1 <= c <= 6:
                        nearby_pairs += 1
                if nearby_pairs >= 3:  # At least 3 potential pairs nearby
                    abs_pos = script_start + i
                    ctx_start = max(0, i - 8)
                    ctx_end = min(len(data), i + 24)
                    chunk = data[ctx_start:ctx_end]
                    print("    0x{:08X}: slot={}, count={} (nearby_pairs={})".format(
                        abs_pos, slot, count, nearby_pairs))
                    print(hex_dump(chunk, script_start + ctx_start))
                    print()
                    # Don't flood output - limit to first 10
                    break

    # ===================================================================
    # PART 4: Search for the specific patterns 0x54/0x3B/0x31 as uint16
    # near coordinates (which would suggest spawn records)
    # ===================================================================
    print("=" * 80)
    print("  PART 4: SEARCH FOR MONSTER IDs NEAR COORDINATE-LIKE VALUES")
    print("=" * 80)
    print()

    for area in AREAS:
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]
        monsters = area["monsters"]

        print("  --- {} ---".format(area["name"]))

        # A coordinate on PS1 is typically int16 LE, range -4096..4096
        # Look for monster ID byte followed within 8 bytes by plausible coordinates
        hits = find_monster_id_occurrences(data, script_start, set(monsters.keys()))

        for pos, val in hits:
            name = MONSTER_NAMES.get(val, "???")
            # Check if there are int16 values nearby that look like coordinates
            has_coords = False
            for off in range(1, 12):
                if pos + off + 1 < len(data):
                    coord = struct.unpack_from('<h', data, pos + off)[0]
                    if -8000 <= coord <= 8000 and coord != 0:
                        has_coords = True
                        break
            if has_coords:
                abs_pos = script_start + pos
                # Show 32 bytes
                start = max(0, pos - 4)
                end = min(len(data), pos + 32)
                chunk = data[start:end]
                print("    0x{:08X}: 0x{:02X}={} (coords nearby)".format(abs_pos, val, name))
                print(hex_dump(chunk, script_start + start))
                # Decode as int16 LE pairs
                for off in range(0, min(32, end - pos), 2):
                    if pos + off + 1 < len(data):
                        v = struct.unpack_from('<h', data, pos + off)[0]
                        if off == 0:
                            print("      int16[+{}]: {} (monster ID byte)".format(off, v))
                        else:
                            print("      int16[+{}]: {}".format(off, v))
                print()

    # ===================================================================
    # PART 5: Wider hex dump - show bytes around every FF block
    # in the first 4KB to understand record structure
    # ===================================================================
    print("=" * 80)
    print("  PART 5: FF-BLOCK RECORD ANALYSIS (Cavern F1A1)")
    print("=" * 80)
    print()

    area = AREAS[0]
    group_off = area["group_offset"]
    num_m = area["num_monsters"]
    script_start = group_off + num_m * 96
    next_off = area["next_group_offset"]
    data = blaze[script_start:next_off]

    # Find ALL FFFFFFFF positions
    ff_positions = []
    i = 0
    while i < len(data) - 3:
        if data[i:i+4] == b'\xff\xff\xff\xff':
            ff_positions.append(i)
            # Skip contiguous FF blocks
            while i < len(data) and data[i] == 0xFF:
                i += 1
        else:
            i += 1

    print("  Total FF-block positions: {}".format(len(ff_positions)))
    print()

    # For each FF block, show the record between this and the next FF block
    for idx in range(min(len(ff_positions), 30)):
        pos = ff_positions[idx]
        # Find extent of FF block
        ff_end = pos
        while ff_end < len(data) and data[ff_end] == 0xFF:
            ff_end += 1
        ff_len = ff_end - pos

        # Next FF block
        next_ff = ff_positions[idx + 1] if idx + 1 < len(ff_positions) else len(data)
        record_after = data[ff_end:next_ff]
        record_size = next_ff - ff_end

        abs_pos = script_start + pos
        print("  FF-block #{:2d} at 0x{:08X} ({} FF bytes), next record: {} bytes".format(
            idx, abs_pos, ff_len, record_size))

        # Show the record between FF blocks
        if record_size > 0 and record_size <= 128:
            print(hex_dump(record_after, script_start + ff_end))

            # Check for monster IDs in this record
            for j, b in enumerate(record_after):
                if b in area["monsters"]:
                    name = MONSTER_NAMES.get(b, "???")
                    print("    ** byte[{}] = 0x{:02X} = {} **".format(j, b, name))
        elif record_size > 128:
            # Just show first 64 bytes
            print(hex_dump(record_after[:64], script_start + ff_end))
            print("    ... ({} more bytes)".format(record_size - 64))
        print()

    # ===================================================================
    # PART 6: Look at the data BETWEEN text strings
    # Text strings are dialogue; the structural data between them
    # might contain spawn/formation info
    # ===================================================================
    print("=" * 80)
    print("  PART 6: NON-TEXT SEGMENTS (between dialogue strings)")
    print("=" * 80)
    print()

    for area in AREAS[:1]:  # Just first area for now
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]

        # Find text and non-text segments
        segments = []  # (start, end, is_text)
        in_text = False
        seg_start = 0

        for i in range(len(data)):
            is_printable = (32 <= data[i] < 127)
            if is_printable and not in_text:
                # End of non-text segment
                if i > seg_start:
                    segments.append((seg_start, i, False))
                seg_start = i
                in_text = True
            elif not is_printable and in_text:
                # End of text segment
                if i > seg_start:
                    segments.append((seg_start, i, True))
                seg_start = i
                in_text = False
        if seg_start < len(data):
            segments.append((seg_start, len(data), in_text))

        # Merge very short segments (< 4 bytes) with neighbors
        merged = []
        for seg in segments:
            start, end, is_text = seg
            length = end - start
            if is_text and length < 4:
                # Reclassify short "text" as non-text
                is_text = False
            if merged and merged[-1][2] == is_text:
                # Merge with previous
                merged[-1] = (merged[-1][0], end, is_text)
            else:
                merged.append((start, end, is_text))

        print("  {} - {} segments (merged)".format(area["name"], len(merged)))
        for start, end, is_text in merged:
            length = end - start
            abs_start = script_start + start
            if is_text:
                text = data[start:end].decode('ascii', errors='replace')
                if length > 60:
                    text = text[:57] + "..."
                print("  TEXT  0x{:08X} ({:5d} bytes): \"{}\"".format(abs_start, length, text))
            else:
                print("  DATA  0x{:08X} ({:5d} bytes)".format(abs_start, length))
                # Show first 128 bytes of non-text segments > 16 bytes
                if length >= 16 and length <= 512:
                    print(hex_dump(data[start:min(start + 128, end)], abs_start))
                elif length > 512:
                    print(hex_dump(data[start:start + 128], abs_start))
                    print("    ... ({} more bytes)".format(length - 128))
                print()


if __name__ == '__main__':
    main()
