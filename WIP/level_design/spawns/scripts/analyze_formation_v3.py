#!/usr/bin/env python3
"""
analyze_formation_v3.py
Final analysis using the 8E02 FFFF FFFFFFFF anchor pattern.

From the raw dump, the pattern "8E 02 FF FF FF FF FF FF" appears at a regular
cadence - this is the tail of every formation record. Let me find ALL such
anchors and work backwards to determine actual record structure.

Key observation from v2 raw dump:
  First "8E 02" at 0x148CCE2 (offset +24 from 0x148CCC4)
  => Record is 32 bytes, and "8E 02 FF FF FF FF FF FF" is at bytes [24:32]

But then look at the records that have FFFFFFFF at +8:
  Rec[3] @ 0x148CD24: bytes[8:12]=FFFFFFFF, and "8E 02 FF FF" at bytes[28:32]
  These records are DIFFERENT: the FFFFFFFF at +8 shifts the "8E 02" to +28.

Actually wait - let me look more carefully at the raw hex. The "8E 02 FF FF"
might actually be a coincidence in the last-record case. Let me re-examine
with the actual hex values side by side.
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


def hex_dump(data, base, length, label=""):
    if label:
        print(f"\n{'=' * 78}")
        print(f"  {label}")
        print(f"{'=' * 78}")
    for row in range(0, min(length, len(data)), 16):
        addr = base + row
        chunk = data[row:row+16]
        h = ' '.join(f"{b:02X}" for b in chunk)
        a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {addr:08X}  {h:<48s}  {a}")


def main():
    print("=" * 78)
    print("  FORMATION v3 - ANCHOR-BASED RECORD PARSING")
    print("=" * 78)

    data = BLAZE_ALL.read_bytes()
    print(f"Loaded: {len(data):,} bytes\n")

    # ===================================================================
    # Step 1: Find ALL "8E 02" occurrences in the formation neighborhood
    # ===================================================================
    search_start = FORMATION_START - 32
    search_end = FORMATION_START + 2048

    anchor = b'\x8E\x02'
    positions = []
    pos = search_start
    while pos < search_end:
        idx = data.find(anchor, pos, search_end)
        if idx == -1:
            break
        positions.append(idx)
        pos = idx + 1

    print(f"Found {len(positions)} '8E 02' anchors in range "
          f"0x{search_start:X}-0x{search_end:X}:")

    for i, p in enumerate(positions):
        # Show context around this anchor
        ctx = data[p-8:p+10]
        rel = p - FORMATION_START
        h = ctx.hex(' ').upper()
        # Check if bytes after 8E 02 are FF FF FF FF FF FF (full tail pattern)
        tail = data[p:p+8]
        is_full_tail = tail == b'\x8E\x02\xFF\xFF\xFF\xFF\xFF\xFF'
        marker = " <-- FULL TAIL" if is_full_tail else ""
        print(f"  [{i:2d}] 0x{p:X} (rel +{rel}): ...{h}...{marker}")

    # ===================================================================
    # Step 2: Use full tail anchors to determine record boundaries
    # ===================================================================
    print()
    print("=" * 78)
    print("  Step 2: RECORD BOUNDARY ANALYSIS")
    print("=" * 78)

    full_tails = [p for p in positions if data[p:p+8] == b'\x8E\x02\xFF\xFF\xFF\xFF\xFF\xFF']

    print(f"\n  Full tail anchors: {len(full_tails)}")
    print(f"  These mark the END of each record (the tail is at bytes[24:32])")
    print(f"  So each record starts 24 bytes BEFORE the anchor.")
    print()

    # Compute record start offsets
    record_starts = [p - 24 for p in full_tails]

    # Check spacing between consecutive records
    print("  Record starts and spacing:")
    for i, rs in enumerate(record_starts):
        spacing = ""
        if i > 0:
            diff = rs - record_starts[i-1]
            spacing = f"  (gap from prev: {diff} bytes)"
        rec = data[rs:rs+32]
        h = rec.hex(' ').upper()
        print(f"  [{i:2d}] 0x{rs:X}{spacing}")
        print(f"       {h}")

    # ===================================================================
    # Step 3: Find the FFFFFFFF-at-offset-8 "last record" markers
    # ===================================================================
    print()
    print("=" * 78)
    print("  Step 3: LAST-RECORD IDENTIFICATION")
    print("=" * 78)
    print()

    # The last record in a group has FFFFFFFF at bytes[8:12]
    # But from the raw dump, it seems the "last record" format is DIFFERENT:
    # It has 4 extra bytes (the FFFFFFFF at +8 shifts everything by 4?)
    # Or it's actually a 36-byte record?
    #
    # Let me check: in F00, between the last "normal" record and the next group:
    # Rec[2] (normal): 0x148CD04, tail at 0x148CD04+24 = 0x148CD1C (8E 02 at 0x148CD1C)
    # Next record (normal): starts at 0x148CD04+32 = 0x148CD24? But the raw dump shows
    # something else at 0x148CD24...
    #
    # Let me look at what's between consecutive full-tail anchors.

    print("  Examining data between full-tail record ends:")
    for i in range(len(record_starts) - 1):
        end_cur = record_starts[i] + 32
        start_next = record_starts[i + 1]
        gap = start_next - end_cur

        if gap != 0:
            gap_data = data[end_cur:start_next]
            h = gap_data.hex(' ').upper()
            print(f"\n  Between rec[{i}] end (0x{end_cur:X}) and rec[{i+1}] start (0x{start_next:X}):")
            print(f"    Gap: {gap} bytes")
            print(f"    Data: {h}")

            # Check if the gap contains the FFFFFFFF marker
            if b'\xFF\xFF\xFF\xFF' in gap_data[:8]:
                print(f"    => Contains FFFFFFFF: this is the last-record marker!")

                # The "last record" in a group seems to be:
                # normal-32-bytes + 4-byte-FFFFFFFF-gap + next-record
                # OR: the last record is 36 bytes (32 + 4 FFFFFFFF separator)
                # OR: the FFFFFFFF is a separate 4-byte sentinel between groups
        else:
            print(f"\n  rec[{i}] -> rec[{i+1}]: contiguous (0 gap)")

    # ===================================================================
    # Step 4: Alternative parsing - treat each record as ending at 8E 02 FF..FF
    # and whatever comes between records as "header/separator"
    # ===================================================================
    print()
    print("=" * 78)
    print("  Step 4: FORMATION GROUP STRUCTURE")
    print("=" * 78)
    print()

    # Let me try a different approach. Parse from FORMATION_START,
    # reading records and detecting group boundaries by the gap content.

    # From the raw dump, look at the actual byte patterns more carefully.
    # Let's dump the formation area as individual 4-byte words to see alignment.
    print("  Formation area as uint32 words (from 0x{:X}):".format(FORMATION_START))
    print()

    num_words = 80  # 320 bytes = 10 records
    for i in range(num_words):
        off = FORMATION_START + i * 4
        val = struct.unpack_from('<I', data, off)[0]
        word_idx = i % 8  # position within a 32-byte record

        # Start a new line every 8 words (32 bytes)
        if word_idx == 0:
            if i > 0:
                print()
            print(f"  0x{off:08X}: ", end="")

        print(f" {val:08X}", end="")

    print("\n")

    # ===================================================================
    # Step 5: DEFINITIVE STRUCTURE with field labels
    # ===================================================================
    print()
    print("=" * 78)
    print("  Step 5: DEFINITIVE RECORD FORMAT")
    print("=" * 78)
    print()

    # Based on the 32-byte-aligned dump:
    # Word0  Word1  Word2  Word3  Word4  Word5  Word6  Word7
    # 00..   00..   sl.FF  00..   00..   00..   8E02   FFFF
    #
    # Normal record:
    #   [0:4]  = 00 00 00 00
    #   [4:8]  = 00 00 00 00 (or FF FF FF FF for first record of F00)
    #   [8]    = slot_index (0,1,2)
    #   [9]    = FF
    #   [10]   = formation_id? (00, 01)
    #   [11]   = 00
    #   [12:24]= zeros
    #   [24:26]= 8E 02 (= 0x028E = 654)
    #   [26:28]= FF FF
    #   [28:32]= FF FF FF FF
    #
    # Last record (before group separator):
    #   [0:4]  = 00 00 00 00
    #   [4:8]  = 00 00 00 00
    #   [8:12] = FF FF FF FF   <-- signals "last in group"
    #   [12]   = slot_index
    #   [13]   = FF
    #   [14]   = formation_id?
    #   [15]   = 00
    #   [16:28]= zeros
    #   [28:30]= 8E 02
    #   [30:32]= FF FF
    #
    # Then 4 bytes: FF FF FF FF (group separator)
    # Then next group's first record starts

    # Let me verify this by parsing properly with this model:

    pos = FORMATION_START
    group_idx = 0
    groups = []
    MAX_EXTENT = FORMATION_START + 2048

    while pos + 32 <= MAX_EXTENT:
        grp_records = []
        grp_start = pos

        while pos + 32 <= MAX_EXTENT:
            rec = data[pos:pos+32]

            # Check if this record has FFFFFFFF at bytes[8:12] (last record)
            is_last = rec[8:12] == b'\xFF\xFF\xFF\xFF'

            if not is_last:
                # Normal record
                slot_idx = rec[8]
                byte9 = rec[9]
                byte10 = rec[10]
                grp_records.append({
                    'offset': pos,
                    'type': 'normal',
                    'slot': slot_idx,
                    'param': byte10,
                    'data': rec,
                })
            else:
                # Last record - different field layout
                slot_idx = rec[12]
                byte13 = rec[13]
                byte14 = rec[14]
                grp_records.append({
                    'offset': pos,
                    'type': 'last',
                    'slot': slot_idx,
                    'param': byte14,
                    'data': rec,
                })

            pos += 32

            if is_last:
                # Check for 4-byte group separator
                if pos + 4 <= MAX_EXTENT:
                    sep = struct.unpack_from('<I', data, pos)[0]
                    if sep == 0xFFFFFFFF:
                        pos += 4  # skip separator
                break

        if grp_records:
            groups.append({
                'index': group_idx,
                'start': grp_start,
                'end': pos,
                'records': grp_records,
            })
            group_idx += 1

        # Check if we've left the formation area
        # Look at the next 32 bytes to see if they still look like a formation record
        if pos + 32 <= MAX_EXTENT:
            next_rec = data[pos:pos+32]
            # Check for 8E 02 at byte 24 or 28
            has_8e02_24 = next_rec[24:26] == b'\x8E\x02'
            has_8e02_28 = next_rec[28:30] == b'\x8E\x02'
            if not has_8e02_24 and not has_8e02_28:
                # Check a few more bytes ahead - maybe there's padding
                look_ahead = data[pos:pos+64]
                if b'\x8E\x02' not in look_ahead:
                    print(f"  Formations end at 0x{pos:X}")
                    print(f"  Next 32 bytes: {next_rec.hex(' ').upper()}")
                    break

    # Print the groups
    print(f"\n  Found {len(groups)} formation groups:\n")

    for grp in groups:
        n = len(grp['records'])
        print(f"  === Formation Group F{grp['index']:02d} ({n} records) "
              f"@ 0x{grp['start']:X} ===")

        for i, rec in enumerate(grp['records']):
            d = rec['data']
            h = d.hex(' ').upper()
            slot = rec['slot']
            param = rec['param']
            rtype = rec['type']
            print(f"    [{i}] {rtype:6s} slot={slot} param={param:02X}  {h}")

        # Show separator info
        last_rec_end = grp['records'][-1]['offset'] + 32
        if last_rec_end < grp['end']:
            sep_data = data[last_rec_end:grp['end']]
            print(f"    --- Separator ({grp['end'] - last_rec_end} bytes): "
                  f"{sep_data.hex(' ').upper()}")

        print()

    formation_true_end = groups[-1]['end'] if groups else FORMATION_START

    # ===================================================================
    # Step 6: What comes AFTER the formation area
    # ===================================================================
    print("=" * 78)
    print(f"  Step 6: POST-FORMATION STRUCTURE (0x{formation_true_end:X})")
    print("=" * 78)

    post = data[formation_true_end:formation_true_end + 256]
    hex_dump(post, formation_true_end, 256,
             f"256 bytes after formations (0x{formation_true_end:X})")

    # ===================================================================
    # Step 7: Summary
    # ===================================================================
    print()
    print("=" * 78)
    print("  FINAL SUMMARY")
    print("=" * 78)

    total_recs = sum(len(g['records']) for g in groups)
    sizes = [len(g['records']) for g in groups]
    true_size = formation_true_end - FORMATION_START
    gap_to_next = NEXT_SPAWN_GRP - formation_true_end

    print(f"\n  Formation area: 0x{FORMATION_START:X} - 0x{formation_true_end:X}")
    print(f"  Total size: {true_size} bytes (0x{true_size:X})")
    print(f"  Groups: {len(groups)}")
    print(f"  Records per group: {sizes}")
    print(f"  Total records: {total_recs}")
    print(f"  Gap to next spawn group: {gap_to_next} bytes (0x{gap_to_next:X})")
    print()

    # Pointer search result from v2: NO aligned pointers found
    print("  POINTER SCAN RESULT: NO 4-byte-aligned pointers found")
    print("  pointing into the formation area from the script area or")
    print("  from the 4KB before the spawn group.")
    print()
    print("  STRUCTURE SUMMARY:")
    print("    - Formation records are 32 bytes each")
    print("    - Normal record: slot at byte[8], 8E02 FFFF FFFFFFFF at [24:32]")
    print("    - Last record: FFFFFFFF at byte[8:12], slot at byte[12]")
    print("    - Groups separated by 4-byte FFFFFFFF sentinel")
    print("    - No external pointers reference individual records")
    print()
    print("  INSERTION FEASIBILITY:")
    print("    Adding/removing records WITHIN the formation area would require")
    print("    shifting all subsequent data. Since no pointers point INTO the")
    print("    formations, the shift is safe for the formation area itself.")
    print("    HOWEVER: the data AFTER formations (0x{:X} onwards) contains".format(
        formation_true_end))
    print("    what appears to be a different structure (type-7 entries, L/R pairs,")
    print("    etc.). If the engine expects these at a FIXED OFFSET from the spawn")
    print("    group start, then shifting would break them.")
    print()
    print("    SAFE APPROACH: Overwrite existing records in-place. The formation")
    print("    area has {} records in {} groups. To change group sizes,".format(
        total_recs, len(groups)))
    print("    one could potentially rewrite the entire block from 0x{:X}".format(
        FORMATION_START))
    print("    to 0x{:X} as long as the total size stays the same.".format(
        formation_true_end))

    print()
    print("Done.")


if __name__ == '__main__':
    main()
