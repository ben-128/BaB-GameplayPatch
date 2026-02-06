#!/usr/bin/env python3
"""
analyze_formation_boundaries.py
Analyze the exact boundaries and surrounding data of the formation template area
in Forest Floor 1 Area 1 to determine if inserting/removing records is feasible.

Key offsets (Forest Floor 1 Area 1):
  Spawn group:       0x148C184 (3 monsters: Kobold, Giant-Beetle, Giant-Ant)
  Script area start: 0x148C2A4 (= 0x148C184 + 3*96)
  Formations start:  0x148CCC4 (first record of F00)
  Last formation F05: 0x148CED8 (5 records, ends at 0x148CF98)
  Next spawn group:  0x14909B0 (Floor 1 Area 2)
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Key offsets
SPAWN_GROUP     = 0x148C184
SCRIPT_AREA     = 0x148C2A4  # spawn_group + 3*96
FORMATION_START = 0x148CCC4  # first record of F00
FORMATION_F05   = 0x148CED8  # first record of last formation F05
FORMATION_END   = 0x148CF98  # F05 + 5*32
NEXT_SPAWN_GRP  = 0x14909B0  # Floor 1 Area 2

RECORD_SIZE = 32  # each formation record is 32 bytes


def hex_dump(data, base_offset, length, label=""):
    """Print a hex dump with address, hex bytes, and ASCII."""
    if label:
        print(f"\n{'=' * 78}")
        print(f"  {label}")
        print(f"{'=' * 78}")
    for row_start in range(0, length, 16):
        addr = base_offset + row_start
        chunk = data[row_start:row_start + 16]
        hex_part = ' '.join(f"{b:02X}" for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {addr:08X}  {hex_part:<48s}  {ascii_part}")


def find_formation_groups(data, start, end):
    """Parse formation records from start to end.
    Each formation group: N records of 32 bytes, terminated by FFFFFFFF.
    """
    groups = []
    pos = start
    current_group = []
    group_start = pos

    while pos + 4 <= end:
        marker = struct.unpack_from('<I', data, pos)[0]
        if marker == 0xFFFFFFFF:
            # End of formation group
            groups.append({
                'start': group_start,
                'records': current_group,
                'end_marker': pos,
            })
            pos += 4  # skip the FFFFFFFF
            current_group = []
            group_start = pos
        else:
            # This is a 32-byte record
            if pos + RECORD_SIZE <= end + 64:  # allow slight overflow to see last record
                record = data[pos:pos + RECORD_SIZE]
                current_group.append({
                    'offset': pos,
                    'data': record,
                })
                pos += RECORD_SIZE
            else:
                break

    # If there are leftover records without a terminator
    if current_group:
        groups.append({
            'start': group_start,
            'records': current_group,
            'end_marker': None,
        })

    return groups


def main():
    print("=" * 78)
    print("  FORMATION BOUNDARY ANALYSIS - Forest Floor 1 Area 1")
    print("=" * 78)
    print()

    data = BLAZE_ALL.read_bytes()
    print(f"Loaded BLAZE.ALL: {len(data):,} bytes")
    print()

    # ---------------------------------------------------------------
    # 1. Dump 256 bytes BEFORE the first formation
    # ---------------------------------------------------------------
    pre_start = FORMATION_START - 256
    pre_data = data[pre_start:FORMATION_START]
    hex_dump(pre_data, pre_start, 256,
             "1. 256 BYTES BEFORE FIRST FORMATION (0x{:X} - 0x{:X})".format(
                 pre_start, FORMATION_START))

    # ---------------------------------------------------------------
    # 2. Dump 256 bytes AFTER the last formation record
    # ---------------------------------------------------------------
    post_data = data[FORMATION_END:FORMATION_END + 256]
    hex_dump(post_data, FORMATION_END, 256,
             "2. 256 BYTES AFTER LAST FORMATION (0x{:X} - 0x{:X})".format(
                 FORMATION_END, FORMATION_END + 256))

    # ---------------------------------------------------------------
    # 3. Parse ALL formation groups and check gaps between them
    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    print("  3. FORMATION GROUP PARSE (from 0x{:X})".format(FORMATION_START))
    print("=" * 78)

    # Parse formations starting a bit before to detect structure
    # Let's parse from FORMATION_START all the way to FORMATION_END + 64
    parse_end = FORMATION_END + 64
    groups = find_formation_groups(data, FORMATION_START, parse_end)

    for i, grp in enumerate(groups):
        n_records = len(grp['records'])
        grp_end = grp['end_marker'] if grp['end_marker'] else (grp['records'][-1]['offset'] + RECORD_SIZE if grp['records'] else grp['start'])

        print(f"\n  Formation F{i:02d} at 0x{grp['start']:X}:")
        print(f"    Records: {n_records}")
        if grp['end_marker'] is not None:
            print(f"    FFFFFFFF terminator at: 0x{grp['end_marker']:X}")
        else:
            print(f"    NO terminator found")

        # Print each record briefly
        for j, rec in enumerate(grp['records']):
            rec_hex = rec['data'].hex(' ').upper()
            print(f"    Rec[{j}] @ 0x{rec['offset']:X}: {rec_hex}")

        # Check what's between this terminator and the next formation's first record
        if grp['end_marker'] is not None and i < len(groups) - 1:
            gap_start = grp['end_marker'] + 4  # after FFFFFFFF
            gap_end = groups[i + 1]['start']
            if gap_start < gap_end:
                gap_data = data[gap_start:gap_end]
                gap_hex = gap_data.hex(' ').upper()
                print(f"    GAP after terminator: {gap_end - gap_start} bytes at 0x{gap_start:X}: [{gap_hex}]")
            elif gap_start == gap_end:
                print(f"    GAP: 0 bytes (next formation immediately follows)")

    # ---------------------------------------------------------------
    # 4. Scan entire script area for uint32 pointers INTO formation area
    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    print("  4. SCANNING SCRIPT AREA FOR POINTERS INTO FORMATION AREA")
    print(f"     Script area: 0x{SCRIPT_AREA:X} - 0x{NEXT_SPAWN_GRP:X}")
    print(f"     Formation area: 0x{FORMATION_START:X} - 0x{FORMATION_END:X}")
    print("=" * 78)

    # Collect all formation record offsets and group starts
    formation_offsets = set()
    for grp in groups:
        formation_offsets.add(grp['start'])
        for rec in grp['records']:
            formation_offsets.add(rec['offset'])
        if grp['end_marker'] is not None:
            formation_offsets.add(grp['end_marker'])

    print(f"\n  Formation offsets to look for: {len(formation_offsets)}")
    for off in sorted(formation_offsets):
        print(f"    0x{off:X}")

    # 4a. Search for ABSOLUTE offset matches (uint32 LE)
    print(f"\n  4a. Searching for ABSOLUTE offsets as uint32 LE...")
    found_abs = []
    scan_start = SCRIPT_AREA
    scan_end = NEXT_SPAWN_GRP
    for pos in range(scan_start, scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if val in formation_offsets:
            found_abs.append((pos, val))

    if found_abs:
        for pos, val in found_abs:
            print(f"    MATCH at 0x{pos:X}: value 0x{val:X} -> points to formation offset")
    else:
        print(f"    No absolute offset matches found.")

    # 4b. Search for RELATIVE offsets from script area start
    print(f"\n  4b. Searching for RELATIVE offsets (from script area start 0x{SCRIPT_AREA:X})...")
    relative_offsets = set()
    for off in formation_offsets:
        rel = off - SCRIPT_AREA
        relative_offsets.add(rel)

    found_rel = []
    for pos in range(scan_start, scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if val in relative_offsets:
            actual_target = SCRIPT_AREA + val
            found_rel.append((pos, val, actual_target))

    if found_rel:
        for pos, val, target in found_rel:
            print(f"    MATCH at 0x{pos:X}: relative 0x{val:X} -> absolute 0x{target:X}")
    else:
        print(f"    No relative offset matches found.")

    # 4c. Search for RELATIVE offsets from spawn group start
    print(f"\n  4c. Searching for RELATIVE offsets (from spawn group start 0x{SPAWN_GROUP:X})...")
    relative_offsets_sg = set()
    for off in formation_offsets:
        rel = off - SPAWN_GROUP
        relative_offsets_sg.add(rel)

    found_rel_sg = []
    for pos in range(scan_start, scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if val in relative_offsets_sg:
            actual_target = SPAWN_GROUP + val
            found_rel_sg.append((pos, val, actual_target))

    if found_rel_sg:
        for pos, val, target in found_rel_sg:
            print(f"    MATCH at 0x{pos:X}: relative 0x{val:X} -> absolute 0x{target:X}")
    else:
        print(f"    No relative offset matches found (from spawn group).")

    # 4d. Search for RELATIVE offsets from formation area start
    print(f"\n  4d. Searching for RELATIVE offsets (from formation start 0x{FORMATION_START:X})...")
    relative_offsets_fs = set()
    for off in formation_offsets:
        rel = off - FORMATION_START
        relative_offsets_fs.add(rel)

    found_rel_fs = []
    for pos in range(scan_start, scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if val in relative_offsets_fs:
            actual_target = FORMATION_START + val
            found_rel_fs.append((pos, val, actual_target))

    if found_rel_fs:
        for pos, val, target in found_rel_fs:
            print(f"    MATCH at 0x{pos:X}: relative 0x{val:X} -> absolute 0x{target:X}")
    else:
        print(f"    No relative offset matches found (from formation start).")

    # ---------------------------------------------------------------
    # 5. Search 4KB before spawn group for pointer tables
    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    print("  5. SEARCHING 4KB BEFORE SPAWN GROUP FOR FORMATION POINTERS")
    print(f"     Search area: 0x{SPAWN_GROUP - 0x1000:X} - 0x{SPAWN_GROUP:X}")
    print("=" * 78)

    pre_scan_start = SPAWN_GROUP - 0x1000
    pre_scan_end = SPAWN_GROUP

    # 5a. Absolute offsets
    print(f"\n  5a. Absolute offset matches...")
    found_pre_abs = []
    for pos in range(pre_scan_start, pre_scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if val in formation_offsets:
            found_pre_abs.append((pos, val))

    if found_pre_abs:
        for pos, val in found_pre_abs:
            print(f"    MATCH at 0x{pos:X}: value 0x{val:X}")
    else:
        print(f"    No absolute offset matches found.")

    # 5b. Look for any uint32 in the range [FORMATION_START, FORMATION_END]
    print(f"\n  5b. Any uint32 values in range [0x{FORMATION_START:X}, 0x{FORMATION_END:X}]...")
    found_range_pre = []
    for pos in range(pre_scan_start, pre_scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if FORMATION_START <= val <= FORMATION_END:
            found_range_pre.append((pos, val))

    if found_range_pre:
        for pos, val in found_range_pre[:20]:
            print(f"    VALUE at 0x{pos:X}: 0x{val:X}")
        if len(found_range_pre) > 20:
            print(f"    ... and {len(found_range_pre) - 20} more")
    else:
        print(f"    None found.")

    # Also check the script area itself for ANY uint32 in formation range
    print(f"\n  5c. Any uint32 in script area pointing into formation range...")
    found_range_script = []
    for pos in range(scan_start, scan_end - 3):
        val = struct.unpack_from('<I', data, pos)[0]
        if FORMATION_START <= val <= FORMATION_END:
            # exclude self-references (formation data itself contains these values)
            if pos < FORMATION_START or pos >= FORMATION_END:
                found_range_script.append((pos, val))

    if found_range_script:
        for pos, val in found_range_script[:30]:
            # Show context
            ctx = data[pos-4:pos+8]
            ctx_hex = ctx.hex(' ').upper()
            print(f"    0x{pos:X}: value 0x{val:X}  context: [{ctx_hex}]")
        if len(found_range_script) > 30:
            print(f"    ... and {len(found_range_script) - 30} more")
    else:
        print(f"    None found outside formation area itself.")

    # ---------------------------------------------------------------
    # 6. Additional: look at what's between script area and formations
    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    print("  6. GAP BETWEEN SCRIPT COMMANDS AND FORMATION START")
    print(f"     Script area: 0x{SCRIPT_AREA:X}")
    print(f"     Formation start: 0x{FORMATION_START:X}")
    print(f"     Gap size: {FORMATION_START - SCRIPT_AREA} bytes (0x{FORMATION_START - SCRIPT_AREA:X})")
    print("=" * 78)

    # Scan backwards from FORMATION_START to find where non-zero data ends
    # or where the previous data structure ends
    scan_back = 128
    region_before = data[FORMATION_START - scan_back:FORMATION_START]
    hex_dump(region_before, FORMATION_START - scan_back, scan_back,
             "Last 128 bytes before formations")

    # ---------------------------------------------------------------
    # 7. Check ALL 4-byte values between formation groups (the delimiters)
    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    print("  7. FFFFFFFF DELIMITER ANALYSIS")
    print("=" * 78)

    for i, grp in enumerate(groups):
        if grp['end_marker'] is not None:
            term_off = grp['end_marker']
            term_data = data[term_off:term_off + 4]
            # Check what immediately follows the 4 bytes
            after_term = data[term_off + 4:term_off + 8]
            print(f"  F{i:02d} terminator at 0x{term_off:X}: "
                  f"[{term_data.hex(' ').upper()}] followed by [{after_term.hex(' ').upper()}]")

    # ---------------------------------------------------------------
    # 8. What comes after last FFFFFFFF?
    # ---------------------------------------------------------------
    last_grp = groups[-1] if groups else None
    if last_grp and last_grp['end_marker'] is not None:
        after_last = last_grp['end_marker'] + 4
        print(f"\n  After last terminator (0x{after_last:X}):")
        trailing = data[after_last:after_last + 128]
        hex_dump(trailing, after_last, 128,
                 "128 bytes after last FFFFFFFF")

    # ---------------------------------------------------------------
    # 9. Summary
    # ---------------------------------------------------------------
    print()
    print("=" * 78)
    print("  9. SUMMARY")
    print("=" * 78)

    total_records = sum(len(g['records']) for g in groups)
    total_groups_count = len(groups)
    formation_area_size = FORMATION_END - FORMATION_START

    print(f"  Formation groups found: {total_groups_count}")
    print(f"  Total records: {total_records}")
    print(f"  Formation area: 0x{FORMATION_START:X} - 0x{FORMATION_END:X} ({formation_area_size} bytes)")
    print(f"  Space to next spawn group: {NEXT_SPAWN_GRP - FORMATION_END} bytes (0x{NEXT_SPAWN_GRP - FORMATION_END:X})")
    print()

    # Check if any pointers were found
    any_pointers = (found_abs or found_rel or found_rel_sg or found_rel_fs
                    or found_pre_abs or found_range_pre or found_range_script)
    if any_pointers:
        print("  ** POINTERS FOUND ** - Insertion requires patching pointer tables!")
    else:
        print("  ** NO POINTERS FOUND ** - Formation area appears self-contained!")
        print("  The engine likely parses formations sequentially using FFFFFFFF delimiters.")
        print("  Inserting/removing records may be feasible IF the parser reads until")
        print("  a final end-of-formations marker is found.")

    print()
    print("Done.")


if __name__ == '__main__':
    main()
