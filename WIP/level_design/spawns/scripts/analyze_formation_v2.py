#!/usr/bin/env python3
"""
analyze_formation_v2.py
Refined analysis of formation boundary structure.

Key finding from v1: F05 parsing went wrong because the assumed end was incorrect.
This script:
1. Re-parses formations more carefully, showing raw hex for each "record"
2. Identifies the TRUE end of the formation area
3. Examines the data structure AFTER formations in detail
4. Does a 4-byte-ALIGNED pointer scan (eliminates false positives from v1)
5. Looks at the structure connecting spawn commands to formations
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

SPAWN_GROUP     = 0x148C184
SCRIPT_AREA     = 0x148C2A4
FORMATION_START = 0x148CCC4
NEXT_SPAWN_GRP  = 0x14909B0

def hex_dump(data, base_offset, length, label=""):
    """Print hex dump."""
    if label:
        print(f"\n{'=' * 78}")
        print(f"  {label}")
        print(f"{'=' * 78}")
    for row_start in range(0, min(length, len(data)), 16):
        addr = base_offset + row_start
        chunk = data[row_start:row_start + 16]
        hex_part = ' '.join(f"{b:02X}" for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {addr:08X}  {hex_part:<48s}  {ascii_part}")


def main():
    print("=" * 78)
    print("  FORMATION BOUNDARY ANALYSIS v2 - Forest Floor 1 Area 1")
    print("=" * 78)

    data = BLAZE_ALL.read_bytes()
    print(f"Loaded: {len(data):,} bytes")
    print()

    # ===================================================================
    # SECTION 1: Careful formation parsing
    # ===================================================================
    # Each formation record: 32 bytes.
    # Last record in each group has bytes[8:12] == FF FF FF FF
    # (This is the "FFFFFFFF at offset +8" pattern, NOT a standalone 4-byte marker)
    # Groups are separated by... what? Let's find out.
    #
    # Let me re-examine: Look at F00 Rec[3]:
    # 00 00 00 00 00 00 00 00 FF FF FF FF 00 FF 00 00 ...
    # bytes[0:8]=zeros, bytes[8:12]=FFFFFFFF, then more data
    #
    # And after 4 records (4*32=128 bytes from 0x148CCC4 = 0x148CD44):
    # the v1 script found a "FFFFFFFF terminator" at 0x148CD44
    #
    # Let me look at what's ACTUALLY at 0x148CD44:
    print("--- RAW DATA at claimed F00 terminator (0x148CD44) ---")
    region = data[0x148CD44:0x148CD44+8]
    print(f"  0x148CD44: {region.hex(' ').upper()}")
    # And then at F01 start (0x148CD48):
    region2 = data[0x148CD48:0x148CD48+32]
    print(f"  0x148CD48: {region2.hex(' ').upper()}")
    print()

    # Actually, from v1 output:
    # F00 Rec[3] @ 0x148CD24: 00 00 00 00 00 00 00 00 FF FF FF FF 00 FF 00 00
    #                          00 00 00 00 00 00 00 00 00 00 00 00 8E 02 FF FF
    # This record has FFFFFFFF at bytes[8:12].
    #
    # Then at 0x148CD44 we see: FF FF FF FF 00 00 00 00 ...
    # This is the last 4 bytes of Rec[3] (bytes[28:32] = 8E 02 FF FF)
    # Wait, that doesn't add up. Let me re-check.
    #
    # Rec[3] starts at 0x148CD24, is 32 bytes, so ends at 0x148CD44.
    # But v1 found "FFFFFFFF terminator" at 0x148CD44.
    # So at 0x148CD44 there IS an FFFFFFFF that ISN'T part of a record.
    # Unless the record structure is different...
    #
    # Let me just dump the entire formation area raw.

    print("=" * 78)
    print("  SECTION 1: RAW FORMATION DUMP (0x148CCC4 onwards, 1024 bytes)")
    print("=" * 78)

    raw_start = FORMATION_START
    raw_len = 1024
    raw_data = data[raw_start:raw_start + raw_len]

    # Dump as 32-byte rows to align with record boundaries
    for row in range(0, raw_len, 32):
        addr = raw_start + row
        chunk = raw_data[row:row+32]
        if len(chunk) < 32:
            break

        hex_part = ' '.join(f"{b:02X}" for b in chunk)

        # Check if this looks like a formation record (has structure)
        # Check for FFFFFFFF at bytes 8:12
        has_inner_ff = chunk[8:12] == b'\xFF\xFF\xFF\xFF'
        # Check if entire 32 bytes is a delimiter
        is_delimiter = chunk[:4] == b'\xFF\xFF\xFF\xFF'

        marker = ""
        if is_delimiter and chunk[4:8] == b'\x00\x00\x00\x00':
            marker = " <-- FFFFFFFF+00000000 (possible group separator?)"
        elif has_inner_ff:
            marker = " <-- LAST REC (FFFFFFFF at +8)"

        # Byte 8 = slot index in non-last records
        slot_byte = chunk[8]

        print(f"  {addr:08X}  {hex_part}{marker}")

    # ===================================================================
    # SECTION 2: Determine actual formation record structure
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 2: FORMATION RECORD FIELD ANALYSIS")
    print("=" * 78)
    print()

    # Parse formations with the hypothesis:
    # - 32-byte records in groups
    # - A record with bytes[8:12]=FFFFFFFF signals "last in group"
    # - Between groups, there might be a 4-byte FFFFFFFF separator,
    #   or the groups are contiguous

    pos = FORMATION_START
    group_idx = 0
    all_groups = []

    while pos + 32 <= FORMATION_START + 1024:
        # Check if we hit a standalone FFFFFFFF (not part of a 32-byte record)
        word = struct.unpack_from('<I', data, pos)[0]

        # Is this the start of a new group?
        # Read records until we find one with FFFFFFFF at +8
        records = []
        grp_start = pos

        while pos + 32 <= FORMATION_START + 1024:
            rec = data[pos:pos+32]
            inner_ff = rec[8:12] == b'\xFF\xFF\xFF\xFF'

            records.append({
                'offset': pos,
                'data': rec,
                'is_last': inner_ff,
            })
            pos += 32

            if inner_ff:
                break

        if records:
            all_groups.append({
                'index': group_idx,
                'start': grp_start,
                'records': records,
                'end': pos,
            })
            group_idx += 1

            # Check what's at the current position
            if pos + 4 <= len(data):
                next_word = struct.unpack_from('<I', data, pos)[0]
                # If we hit something that doesn't look like a formation record,
                # we've exited the formation area
                # Check: does it look like more formation data?
                if pos + 32 <= len(data):
                    next_rec = data[pos:pos+32]
                    # Formation records typically have bytes 24-25 = 8E 02 (or similar)
                    # and bytes 30-31 = FF FF
                    b24_25 = struct.unpack_from('<H', next_rec, 24)[0]
                    b30_31 = struct.unpack_from('<H', next_rec, 30)[0]

                    if b30_31 != 0xFFFF and b24_25 != 0x028E:
                        print(f"  End of formations detected at 0x{pos:X}")
                        print(f"  Next bytes: {next_rec[:16].hex(' ').upper()}")
                        break

    print(f"  Found {len(all_groups)} formation groups:")
    for grp in all_groups:
        n = len(grp['records'])
        print(f"\n  --- Group F{grp['index']:02d} ({n} records) @ 0x{grp['start']:X} ---")
        for i, rec in enumerate(grp['records']):
            d = rec['data']
            # Interpret fields
            slot_l = d[0]   # slot for left?
            slot_r = d[4] if not rec['is_last'] else None
            byte8 = d[8]    # monster slot index (0,1,2)
            byte9 = d[9]    # often 0xFF
            byte10 = d[10]  # param

            label = "LAST" if rec['is_last'] else f"slot={byte8}"
            hex_str = d.hex(' ').upper()
            print(f"    Rec[{i}] @ 0x{rec['offset']:X}: {hex_str}  [{label}]")

    formation_end = all_groups[-1]['end'] if all_groups else FORMATION_START

    # ===================================================================
    # SECTION 3: What follows the formations?
    # ===================================================================
    print()
    print("=" * 78)
    print(f"  SECTION 3: DATA AFTER FORMATIONS (0x{formation_end:X})")
    print("=" * 78)

    post_data = data[formation_end:formation_end + 512]
    hex_dump(post_data, formation_end, 512,
             f"512 bytes after formation end (0x{formation_end:X})")

    # ===================================================================
    # SECTION 4: 4-byte ALIGNED pointer scan (no false positives)
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 4: 4-BYTE ALIGNED POINTER SCAN")
    print("=" * 78)

    # Build set of all meaningful formation offsets
    form_offsets = set()
    for grp in all_groups:
        form_offsets.add(grp['start'])
        for rec in grp['records']:
            form_offsets.add(rec['offset'])

    # 4a. Absolute offsets, 4-byte aligned scan in script area (excluding formation area itself)
    print(f"\n  4a. Absolute formation offsets in script area (4-byte aligned)...")
    found = []
    for pos in range(SCRIPT_AREA, NEXT_SPAWN_GRP, 4):
        if FORMATION_START <= pos < formation_end:
            continue  # skip formation area itself
        val = struct.unpack_from('<I', data, pos)[0]
        if val in form_offsets:
            found.append((pos, val))

    if found:
        for p, v in found:
            print(f"    0x{p:X}: uint32 = 0x{v:X}")
    else:
        print(f"    None found.")

    # 4b. Any 4-byte-aligned uint32 in the range [FORMATION_START..formation_end]
    print(f"\n  4b. Any uint32 in [0x{FORMATION_START:X}..0x{formation_end:X}] (4-byte aligned, outside formations)...")
    found2 = []
    for pos in range(SCRIPT_AREA, NEXT_SPAWN_GRP, 4):
        if FORMATION_START <= pos < formation_end:
            continue
        val = struct.unpack_from('<I', data, pos)[0]
        if FORMATION_START <= val < formation_end:
            found2.append((pos, val))

    if found2:
        for p, v in found2[:20]:
            ctx_before = data[p-8:p].hex(' ').upper()
            ctx_after = data[p+4:p+12].hex(' ').upper()
            print(f"    0x{p:X}: 0x{v:X}  context: [{ctx_before}] [val] [{ctx_after}]")
    else:
        print(f"    None found.")

    # 4c. Search in 4KB before spawn group too
    print(f"\n  4c. Same search in 4KB before spawn group...")
    found3 = []
    for pos in range(SPAWN_GROUP - 0x1000, SPAWN_GROUP, 4):
        val = struct.unpack_from('<I', data, pos)[0]
        if FORMATION_START <= val < formation_end:
            found3.append((pos, val))

    if found3:
        for p, v in found3[:20]:
            print(f"    0x{p:X}: 0x{v:X}")
    else:
        print(f"    None found.")

    # ===================================================================
    # SECTION 5: Scan for formation COUNT values
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 5: SEARCH FOR FORMATION COUNT / INDEX")
    print("=" * 78)

    # How many formation groups? Let's see what our count is.
    n_groups = len(all_groups)
    n_records_per = [len(g['records']) for g in all_groups]
    print(f"  Groups: {n_groups}")
    print(f"  Records per group: {n_records_per}")

    # Search for the count value (n_groups) as uint8, uint16, uint32
    # in the 128 bytes before the first formation
    pre_region = data[FORMATION_START - 128:FORMATION_START]
    print(f"\n  Searching for count={n_groups} in 128 bytes before formations...")
    for i in range(len(pre_region)):
        if pre_region[i] == n_groups:
            abs_off = FORMATION_START - 128 + i
            ctx = pre_region[max(0,i-4):i+5]
            print(f"    uint8 match at 0x{abs_off:X}: context [{ctx.hex(' ').upper()}]")

    for i in range(0, len(pre_region)-1, 2):
        val = struct.unpack_from('<H', pre_region, i)[0]
        if val == n_groups:
            abs_off = FORMATION_START - 128 + i
            ctx = pre_region[max(0,i-4):i+6]
            print(f"    uint16 match at 0x{abs_off:X}: context [{ctx.hex(' ').upper()}]")

    # ===================================================================
    # SECTION 6: Formation area size expressed as offset/size
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 6: FORMATION AREA METRICS")
    print("=" * 78)

    total_bytes = formation_end - FORMATION_START
    print(f"  Formation area: 0x{FORMATION_START:X} to 0x{formation_end:X}")
    print(f"  Total size: {total_bytes} bytes (0x{total_bytes:X})")
    print(f"  Groups: {n_groups}")
    print(f"  Records per group: {n_records_per}")
    print(f"  Total records: {sum(n_records_per)}")
    print(f"  Bytes per record: 32")
    print(f"  Formation area = {sum(n_records_per)} * 32 = {sum(n_records_per)*32} bytes")
    print(f"  (remaining {total_bytes - sum(n_records_per)*32} bytes could be group separators or terminators)")

    # The gap between formation end and next spawn group
    gap_to_next = NEXT_SPAWN_GRP - formation_end
    print(f"\n  Space to next spawn group (0x{NEXT_SPAWN_GRP:X}): {gap_to_next} bytes (0x{gap_to_next:X})")

    # ===================================================================
    # SECTION 7: Cross-check with another area (Forest Floor 1 Area 2)
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 7: CROSS-CHECK - Forest Floor 1 Area 2 formations")
    print("=" * 78)

    # Floor 1 Area 2 spawn group at 0x14909B0 (5 monsters: Lv6.Kobold, Kobold, Giant-Beetle, Wing-Fish, Giant-Club)
    # Script area = 0x14909B0 + 5*96 = 0x14909B0 + 0x1E0 = 0x1490B90
    area2_spawn = 0x14909B0
    area2_script = area2_spawn + 5 * 96

    print(f"  Area 2 spawn group: 0x{area2_spawn:X}")
    print(f"  Area 2 script area: 0x{area2_script:X}")

    # Find formations by scanning for the characteristic pattern:
    # Look for bytes with 0x8E, 0x02 pattern or FFFFFFFF at bytes +8
    # Actually, let's just look for the formation signature pattern
    # Scan from area2_script for formation-like records

    # Formations in area 2: scan for 32-byte records with FFFFFFFF at +8 in last record
    # and with byte pattern like XX XX 00 00 XX XX 00 00 XX FF ...

    # Let's search more broadly: look for consecutive 00 00 00 00 ... 8E 02 FF FF patterns
    print(f"\n  Scanning for '8E 02' pattern (formation signature) in area 2...")
    search_start = area2_script
    search_end = min(area2_spawn + 0x5000, len(data))

    matches_8e02 = []
    for pos in range(search_start, search_end - 1):
        if data[pos] == 0x8E and data[pos+1] == 0x02:
            matches_8e02.append(pos)

    if matches_8e02:
        print(f"  Found {len(matches_8e02)} occurrences of '8E 02':")
        for m in matches_8e02[:15]:
            # Show context
            ctx = data[m-24:m+8]
            rel = m - area2_script
            print(f"    0x{m:X} (script+0x{rel:X}): ...{ctx.hex(' ').upper()}...")

        if matches_8e02:
            # Estimate formation area start for area 2
            # The first 8E 02 should be at offset +24 of the first formation record
            first_8e02 = matches_8e02[0]
            estimated_form_start = first_8e02 - 24
            print(f"\n  Estimated Area 2 formation start: 0x{estimated_form_start:X}")
            print(f"  (offset from script area: 0x{estimated_form_start - area2_script:X})")

            # For comparison, Area 1:
            area1_form_offset = FORMATION_START - SCRIPT_AREA
            print(f"  Area 1 formation offset from script area: 0x{area1_form_offset:X}")

    # ===================================================================
    # SECTION 8: Examine the "spawn command" records that reference formations
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 8: SPAWN COMMAND RECORDS (32-byte blocks in script area)")
    print("=" * 78)

    # The spawn commands that reference monster slots are 32-byte blocks
    # with pattern: ... monster_id ... FF FF FF FF FF FF FF FF ...
    # These are at known offsets from Cavern analysis.
    # For Forest, let's find them by looking for monster type IDs.

    # Forest Floor 1 Area 1 monsters: Kobold, Giant-Beetle, Giant-Ant
    # We need their IDs. Let's search the monster JSON files.
    import json
    monster_dir = PROJECT_ROOT / "Data" / "monster_stats" / "normal_enemies"
    monster_ids = {}
    if monster_dir.exists():
        for jf in monster_dir.glob("*.json"):
            try:
                with open(jf, 'r') as f:
                    mdata = json.load(f)
                name = mdata.get('name', '')
                mid = mdata.get('id', -1)
                if name and mid >= 0:
                    monster_ids[name] = mid
            except:
                pass

    target_names = ['Kobold', 'Giant-Beetle', 'Giant-Ant']
    print(f"  Monster IDs for this area:")
    for name in target_names:
        mid = monster_ids.get(name, -1)
        print(f"    {name}: ID {mid} (0x{mid:02X})" if mid >= 0 else f"    {name}: NOT FOUND")

    # Now look for these IDs in the spawn commands area (between script_area and formations)
    # The spawn commands are between SCRIPT_AREA and FORMATION_START
    print(f"\n  Searching for spawn command records in 0x{SCRIPT_AREA:X} - 0x{FORMATION_START:X}...")

    for name in target_names:
        mid = monster_ids.get(name, -1)
        if mid < 0:
            continue

        pos = SCRIPT_AREA
        while pos < FORMATION_START:
            idx = data.find(bytes([mid]), pos, FORMATION_START)
            if idx == -1:
                break

            # Check if this is in a spawn-command-like context
            # Pattern: [monster_id] XX 00 00 XX XX 00 00 XX XX FF FF FF FF FF FF
            # or: ... XX XX 00 00 [monster_id] XX FF FF FF FF FF FF 00 00 00 00 ...
            ctx = data[idx-16:idx+16]

            # Check for FF FF FF FF FF FF FF FF within +/- 16 bytes
            has_ff8 = False
            for i in range(len(ctx) - 7):
                if ctx[i:i+8] == b'\xFF' * 8:
                    has_ff8 = True
                    break

            if has_ff8:
                abs_ctx_start = idx - 16
                hex_str = ctx.hex(' ').upper()
                print(f"    {name} (ID {mid}) at 0x{idx:X}: {hex_str}")

            pos = idx + 1

    # ===================================================================
    # SECTION 9: FINAL SUMMARY
    # ===================================================================
    print()
    print("=" * 78)
    print("  SECTION 9: CONCLUSIONS")
    print("=" * 78)
    print()

    no_abs_pointers = len(found) == 0
    no_range_pointers = len(found2) == 0
    no_pre_pointers = len(found3) == 0

    if no_abs_pointers and no_range_pointers and no_pre_pointers:
        print("  RESULT: NO 4-byte-aligned pointers found pointing into formations.")
        print()
        print("  The formation area appears to be parsed SEQUENTIALLY:")
        print("    - Records are 32 bytes each")
        print("    - Last record in each group has FFFFFFFF at bytes[8:12]")
        print("    - Groups follow each other contiguously (no gap bytes)")
        print("    - The engine counts groups or reads until a different structure begins")
        print()
        print("  IMPLICATIONS FOR INSERTING/REMOVING RECORDS:")
        print("    - Adding/removing records within a group: SAFE if the FFFFFFFF marker")
        print("      in the last record is preserved")
        print("    - The data AFTER formations must stay at the correct offset OR")
        print("      the engine parses formations until a sentinel/count is reached")
        print("    - Need to verify: is there a count somewhere, or does the engine")
        print("      just parse until it hits non-formation data?")
    else:
        print("  RESULT: Pointers found! Formation area is NOT self-contained.")
        if found:
            print(f"  Absolute pointer matches: {len(found)}")
        if found2:
            print(f"  Range pointer matches: {len(found2)}")
        if found3:
            print(f"  Pre-group pointer matches: {len(found3)}")

    print()
    print("Done.")


if __name__ == '__main__':
    main()
