#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Decode per-type AI behavior blocks v3 - Final focused decode.

Key findings from v1/v2:
 - L=0 block is 20 bytes (just a prefix: model pairs + flags + timer)
 - L=1 is NULL (Shaman shares behavior)
 - root[2] in Area1 = "shared ground-type block" with 3 FFFF records for L=0,1,2
 - root[2] in Area2 = L=2 (Goblin-Leader) with 1 FFFF record
 - root[3] = Bat (L=3): 1 FFFF record + AI dispatch table suffix
 - Config (root[4]): model/render pairs + bytecode offsets
 - root[5+]: bytecode offset tables (different per area, NOT shared pool)
 - Last table: interleaved (key,value) pairs with some SHARED values across areas

This v3 deep-dives into:
 1. STAT BLOCK structure in prefix data
 2. How the "AI dispatch table" (bat suffix) encodes opcodes
 3. The shared entries in the last table
 4. Additional areas to confirm the pattern
"""

import struct
import sys
from pathlib import Path

BLAZE_ALL = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377"
                 r"\GameplayPatch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")

AREAS = [
    {
        "name": "Area 1 (Goblin/Shaman/Bat)",
        "group_offset": 0xF7A97C,
        "num_monsters": 3,
        "formation_area_start": 0xF7AFFC,
        "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
        "L_values": [0, 1, 3],
    },
    {
        "name": "Area 2 (Goblin/Shaman/Bat/Leader)",
        "group_offset": 0xF7E1A8,
        "num_monsters": 4,
        "formation_area_start": 0xF7E9F0,
        "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "Goblin-Leader"],
        "L_values": [0, 1, 3, 2],
    },
]


def r32(d, o):
    if o + 4 <= len(d): return struct.unpack_from('<I', d, o)[0]
    return 0

def r16(d, o):
    if o + 2 <= len(d): return struct.unpack_from('<H', d, o)[0]
    return 0

def rs16(d, o):
    if o + 2 <= len(d): return struct.unpack_from('<h', d, o)[0]
    return 0


def parse_root_table(chunk, max_size):
    root = []
    cz = 0
    for i in range(0, max_size - 3, 4):
        v = r32(chunk, i)
        if v == 0:
            cz += 1
            root.append(v)
            if cz >= 2:
                while root and root[-1] == 0:
                    root.pop()
                break
        else:
            cz = 0
            root.append(v)
    root_end = (len(root) + cz) * 4
    return root, root_end


def main():
    data = BLAZE_ALL.read_bytes()
    print("BLAZE.ALL loaded: %d bytes" % len(data))

    all_areas = []

    for area_idx, area in enumerate(AREAS):
        group_off = area["group_offset"]
        n_mon = area["num_monsters"]
        fm_start = area["formation_area_start"]
        monsters = area["monsters"]
        L_values = area["L_values"]

        script_start = group_off + n_mon * 96
        script_size = fm_start - script_start
        chunk = data[script_start:fm_start]
        root, root_end = parse_root_table(chunk, script_size)

        l_to_mon = {}
        for si, L in enumerate(L_values):
            l_to_mon[L] = monsters[si]

        max_L = max(L_values)

        print()
        print("=" * 78)
        print("AREA %d: %s" % (area_idx + 1, area["name"]))
        print("  script_start=0x%08X  size=%d  root entries=%d" %
              (script_start, script_size, len(root)))
        print("=" * 78)

        # ================================================================
        # 1. STAT BLOCK decode in the shared descriptor prefix
        # ================================================================
        print("\n--- 1. STAT BLOCK analysis ---\n")

        # In Area 1, root[2] prefix has at +06C: 90 01 00 02 00 00 7D 00 7D 00 7D 00
        # = 0x0190 0x0200 then 0x0000 0x007D 0x007D 0x007D
        # The 0x0190 = 400 and 0x0200 = 512 seem to be RANGE values
        # The three 0x007D = 125 values are the ACTUAL stat values
        #
        # In Area 2, root[2] prefix has TWO stat blocks:
        #   +060: 00 00 7C 00 7C 00 7C 00 = values (124, 124, 124) -- NO header!
        #   +06C: 90 01 00 02 00 00 14 00 14 00 14 00 = header(400,512) + values (20, 20, 20)
        #   +07C: 90 01 00 02 00 00 82 00 BE 00 82 00 = header(400,512) + values (130, 190, 130)
        #
        # Wait - let me re-examine. The stat block format may be:
        #   byte[0:2] = 0x0000 (padding) or value[0]
        #   byte[2:4] = value[1] or part of header
        #   ...
        # Actually it's more likely a fixed-size record.

        # Let me look at Area 1 root[2] prefix more carefully:
        # +050: 00 00 00 08  <- behavior flag byte at position 3
        # +054: 84 03 00 00  <- 0x384 = 900 timer
        # +058: 00 00 00 00  <- zero
        # +05C: 84 03 00 00  <- 0x384 = 900 timer
        # +060: 00 00 00 0E  <- behavior flag 0x0E
        # +064: 84 03 00 00  <- 0x384 = 900 timer
        # +068: 00 00 00 00  <- zero
        # +06C: 90 01 00 02  <- 0x0190 and 0x0200
        # +070: 00 00 7D 00  <- uint16 pair (0, 125)
        # +074: 7D 00 7D 00  <- uint16 pair (125, 125)
        # +078: 00 00 00 00  <- zero
        # +07C: 00 00 00 00  <- zero
        # +080: 18 05 00 00  <- program ref 0x0518
        # +084: 01 00 00 00  <- index 1
        # +088: 20 05 00 00  <- program ref 0x0520
        # +08C: 02 00 00 00  <- index 2
        # +090: 00 00 00 00  <- zero terminator

        # INSIGHT: The pattern is groups of:
        #   [flag_byte, 0, 0, 0] [0x384, 0, 0, 0]
        # repeated, then
        #   [0x0190, 0x0200] [0, val, val, val] [0, 0, 0, 0]
        # then
        #   [program_ref, 0, 0, 0] [index, 0, 0, 0]
        # pairs.
        #
        # The flag_bytes are: 0x08, then 0x00+0x384, then 0x00, then 0x384,
        # then 0x0E, then 0x384, then 0x00.
        #
        # Hmm wait. Let me re-read treating byte[3] of each 4-byte word as the flag:
        # Actually the uint32 LE value 0x08000000 has:
        #   byte[0]=0x00, byte[1]=0x00, byte[2]=0x00, byte[3]=0x08
        # So the flag is at the HIGH byte of the uint32.

        # Let me reinterpret the prefix as a sequence of (uint16, uint16) pairs:

        # Find the block containing stat data
        for L_check in range(max_L + 1):
            if L_check >= len(root) or root[L_check] == 0:
                continue

            off = root[L_check]
            nxt = script_size
            for j in range(L_check + 1, len(root)):
                if root[j] > off:
                    nxt = root[j]
                    break

            blk = chunk[off:nxt]
            mon = l_to_mon.get(L_check, "root[%d]" % L_check)

            # Search for 0x0190 in the block
            for p in range(0, len(blk) - 12, 2):
                if r16(blk, p) == 0x0190 and r16(blk, p + 2) == 0x0200:
                    # Found a stat header
                    # Read 6 bytes after: uint16 padding + 3 x uint16 values
                    pad = r16(blk, p + 4)
                    v1 = r16(blk, p + 6)
                    v2 = r16(blk, p + 8)
                    v3 = r16(blk, p + 10)
                    print("  L=%d (%s): STAT BLOCK at block+%d:" % (L_check, mon, p))
                    print("    Header: 0x0190 (400) 0x0200 (512)")
                    print("    Pad: %d" % pad)
                    print("    Values: %d, %d, %d" % (v1, v2, v3))

                    # Check if there's another block of 6 uint16 values BEFORE the header
                    if p >= 8:
                        pre_pad = r16(blk, p - 8)
                        pre_v1 = r16(blk, p - 6)
                        pre_v2 = r16(blk, p - 4)
                        pre_v3 = r16(blk, p - 2)
                        if pre_v1 > 0 and pre_v2 > 0 and pre_v3 > 0 and pre_v1 < 500 and pre_v2 < 500:
                            print("    Pre-header values (no 0190/0200): %d, %d, %d, %d" %
                                  (pre_pad, pre_v1, pre_v2, pre_v3))

        # ================================================================
        # 2. AI dispatch table decode (bat suffix)
        # ================================================================
        print("\n--- 2. AI dispatch table (Bat suffix) ---\n")

        r3_off = root[3]
        r3_end = script_size
        for j in range(4, len(root)):
            if root[j] > r3_off:
                r3_end = root[j]
                break

        blk3 = chunk[r3_off:r3_end]

        # Skip the first 32-byte FFFF record
        suffix_off = 32
        suffix = blk3[suffix_off:]

        # Key insight: the suffix contains interleaved:
        #   BYTECODE_REF (0x05xx), then a PARAM value
        # The BYTECODE_REF values are monotonically increasing with stride ~8
        # (0x0528, 0x0540, 0x0558, 0x0560, 0x0568, 0x0570, 0x0578, 0x0580, 0x0588, 0x0590, 0x0598)
        # The PARAM values are: 0x0540, 0x0000, 0x0560, 0x0000, 0x00A0, 4, 0x0105, 0x0206, ...
        #
        # Wait -- let me look at the actual sequential values again from v2 output:
        # [ 0] 0x0528, [ 1] 0x0540, [ 2] 0x0000, [ 3] 0x0558
        # [ 4] 0x0560, [ 5] 0x0000, [ 6] 0x00A0, [ 7] 0x0568
        # [ 8] 0x0004, [ 9] 0x0570, [10] 0x0105, [11] 0x0578
        # [12] 0x0206, [13] 0x0580, [14] 0x1007, [15] 0x0588
        # [16] 0x11107, [17] 0x0590, [18] 0x21207, [19] 0x0598
        # [20] 0x130E, [21] 0x0000, [22] 0x0000, [23] 0x05A0
        # [24] 0x0000, [25] 0x05A8, [26] 0x40000000, [27] 0x0000
        # [28] 0x0000, [29] 0x05B0, [30] 0x40000000, [31] 0x05B8
        # [32] 0x40000200
        #
        # The 0x05xx values are OFFSETS -- they increase: 0528, 0540, 0558, 0560, 0568, 0570, etc.
        # Every ODD position also has 0x05xx values! So the suffix is NOT interleaved pairs.
        #
        # Instead, the suffix seems to be a FLAT TABLE of uint32 values that are either:
        #  - Bytecode offsets (0x05xx-0x06xx range)
        #  - Parameter values (small integers, packed bytes)
        #  - Zero (null/separator)
        #  - Flag values (0x40000000+)
        #
        # Let me try grouping them differently: groups of 3 (offset, offset, param)?
        # Or perhaps the structure is a series of VARIABLE-LENGTH records.

        # Let me look at the Bat suffix from BOTH areas side by side:
        print("  Bat L=3 suffix (after 32-byte record):")
        print("  Area %d:" % (area_idx + 1))

        vals = []
        for p in range(0, len(suffix) - 3, 4):
            v = r32(suffix, p)
            vals.append(v)

        # Print all values with classification
        for i, v in enumerate(vals):
            note = ""
            if 0x0500 <= v <= 0x0700:
                note = "OFFSET"
            elif v == 0:
                note = "NULL"
            elif v == 0xA0:
                note = "0xA0 (special)"
            elif 0x40000000 <= v:
                note = "FLAG (0x%08X)" % v
            elif v < 0x20:
                note = "SMALL(%d)" % v
            elif 0x100 <= v < 0x1000:
                note = "PARAM(0x%03X)" % v
            else:
                # Decode as byte fields
                b0 = v & 0xFF
                b1 = (v >> 8) & 0xFF
                b2 = (v >> 16) & 0xFF
                b3 = (v >> 24) & 0xFF
                note = "BYTES(%02X.%02X.%02X.%02X)" % (b0, b1, b2, b3)

            print("    [%2d] 0x%08X  %s" % (i, v, note))

        # Now let me try a DIFFERENT interpretation: pairs of (OFFSET, VALUE)
        # where OFFSETs are the 0x05xx values, reading pairs starting from first OFFSET.
        print("\n  Re-parse as (OFFSET -> VALUE) dispatch entries:")
        i = 0
        entry_num = 0
        while i < len(vals):
            v = vals[i]
            if 0x0500 <= v <= 0x0700:
                # This is an offset, next value is its parameter
                param = vals[i + 1] if i + 1 < len(vals) else 0
                # Decode param
                if param == 0:
                    param_s = "NULL"
                elif 0x0500 <= param <= 0x0700:
                    param_s = "OFFSET(0x%04X)" % param
                elif 0x40000000 <= param:
                    param_s = "FLAG(0x%08X)" % param
                else:
                    b0 = param & 0xFF
                    b1 = (param >> 8) & 0xFF
                    b2 = (param >> 16) & 0xFF
                    b3 = (param >> 24) & 0xFF
                    if param < 0x20:
                        param_s = "IDX(%d)" % param
                    elif b2 == 0 and b3 == 0:
                        param_s = "opcode=%02X arg=%02X" % (b0, b1)
                    else:
                        param_s = "%02X.%02X.%02X.%02X" % (b0, b1, b2, b3)

                print("    [%2d] 0x%04X -> %s" % (entry_num, v, param_s))
                i += 2
                entry_num += 1
            elif v == 0:
                # NULL entry (no offset)
                print("    [%2d] NULL" % entry_num)
                i += 1
                entry_num += 1
            elif 0x40000000 <= v:
                # Flag value without preceding offset -- this is a flag for prev entry
                print("    [--] FLAG(0x%08X) (modifies previous)" % v)
                i += 1
            else:
                # Unknown
                print("    [??] 0x%08X" % v)
                i += 1

        all_areas.append({
            "root": root,
            "chunk": chunk,
            "script_start": script_start,
            "script_size": script_size,
            "monsters": monsters,
            "L_values": L_values,
            "l_to_mon": l_to_mon,
            "max_L": max_L,
        })

    # ================================================================
    # 3. DEEP COMPARISON: Shared entries in last table
    # ================================================================
    if len(all_areas) >= 2:
        a1, a2 = all_areas[0], all_areas[1]

        print("\n" + "=" * 78)
        print("3. DEEP COMPARISON: Last (wide-range) table entries")
        print("=" * 78)

        # Get the last offset table from each area
        for ai, ad in enumerate(all_areas):
            root = ad["root"]
            chunk = ad["chunk"]
            ss = ad["script_size"]
            max_L = ad["max_L"]

            # Find the last offset table (the one with wide range)
            for ri in range(len(root) - 1, max_L, -1):
                if root[ri] == 0:
                    continue
                off = root[ri]
                nxt = ss
                for j in range(ri + 1, len(root)):
                    if root[j] > off:
                        nxt = root[j]
                        break
                section = chunk[off:nxt]

                # Read as uint32
                vals = []
                for p in range(0, len(section) - 3, 4):
                    v = r32(section, p)
                    if v != 0 and v > 0x10000:
                        break
                    vals.append(v)

                nonz = [v for v in vals if v != 0]
                if nonz and max(nonz) - min(nonz) > 10000:
                    # Found the wide range table
                    ad["wide_table"] = vals
                    ad["wide_table_idx"] = ri
                    break

        if "wide_table" in a1 and "wide_table" in a2:
            t1 = a1["wide_table"]
            t2 = a2["wide_table"]

            print("\n  Area 1 root[%d]: %d entries" % (a1["wide_table_idx"], len(t1)))
            print("  Area 2 root[%d]: %d entries" % (a2["wide_table_idx"], len(t2)))

            # The wide table has TWO sections:
            # SECTION A: First ~10 entries are sequential offsets (area-specific)
            # SECTION B: Last entries are interleaved pairs (some shared)

            # Find where the sequential section ends (where values stop being monotonic)
            def find_seq_end(vals):
                for i in range(1, len(vals)):
                    if vals[i] == 0:
                        continue
                    if vals[i] != 0 and i > 0 and vals[i-1] != 0 and vals[i] < vals[i-1]:
                        return i
                return len(vals)

            seq1_end = find_seq_end(t1)
            seq2_end = find_seq_end(t2)
            print("\n  Sequential section ends: A1 at [%d], A2 at [%d]" % (seq1_end, seq2_end))

            print("\n  SECTION A (sequential, area-specific):")
            print("    A1: %s" % ', '.join(('0x%04X' % v if v else 'NULL') for v in t1[:seq1_end]))
            print("    A2: %s" % ', '.join(('0x%04X' % v if v else 'NULL') for v in t2[:seq2_end]))

            print("\n  SECTION B (interleaved pairs):")
            b1 = t1[seq1_end:]
            b2 = t2[seq2_end:]

            # Print as pairs
            max_b = max(len(b1), len(b2))
            print("    %-5s  %-22s  %-22s  %s" % ("Pair", "Area 1", "Area 2", "Match?"))
            print("    " + "-" * 65)
            for pi in range(0, max_b, 2):
                k1 = b1[pi] if pi < len(b1) else None
                v1 = b1[pi+1] if pi+1 < len(b1) else None
                k2 = b2[pi] if pi < len(b2) else None
                v2 = b2[pi+1] if pi+1 < len(b2) else None

                def fmt(k, v):
                    if k is None:
                        return "---"
                    return "0x%04X -> 0x%04X" % (k, v if v is not None else 0)

                match = ""
                if k1 is not None and k2 is not None:
                    if k1 == k2 and v1 == v2:
                        match = "IDENTICAL"
                    elif k1 == k2:
                        match = "SAME KEY"
                    else:
                        match = "different"

                print("    [%2d]  %-22s  %-22s  %s" %
                      (pi//2, fmt(k1, v1), fmt(k2, v2), match))

            # Identify the shared pairs
            print("\n  Shared key-value pairs across both areas:")
            set1 = set()
            for pi in range(0, len(b1) - 1, 2):
                set1.add((b1[pi], b1[pi+1]))
            set2 = set()
            for pi in range(0, len(b2) - 1, 2):
                set2.add((b2[pi], b2[pi+1]))

            shared = set1 & set2
            for k, v in sorted(shared):
                print("    0x%04X -> 0x%04X" % (k, v))

            only_a1 = set1 - set2
            only_a2 = set2 - set1
            if only_a1:
                print("\n  Only in Area 1:")
                for k, v in sorted(only_a1):
                    print("    0x%04X -> 0x%04X" % (k, v))
            if only_a2:
                print("\n  Only in Area 2:")
                for k, v in sorted(only_a2):
                    print("    0x%04X -> 0x%04X" % (k, v))

    # ================================================================
    # 4. Full structural map summary
    # ================================================================
    print("\n" + "=" * 78)
    print("FULL STRUCTURAL MAP - Per-type behavior block format")
    print("=" * 78)
    print("""
ROOT TABLE LAYOUT (per spawn group):
  root[0..max_L]  = Per-behavior-type blocks (indexed by L value from monster entry)
  root[max_L+1]   = Config/model section
  root[max_L+2+]  = Bytecode offset tables + command sections

GAP (between root table end and root[0]):
  Optional model ID pairs (uint16, uint16) for the base monster type.

PER-BEHAVIOR-TYPE BLOCK (root[L]):
  The block is split into:

  A) HEADER SECTION (variable length, starts at root[L]):
     Repeating groups of:
       [4 bytes] FLAG_WORD:    0xNN000000 where NN = behavior flag (0x08, 0x0E, etc.)
       [4 bytes] TIMER:        0x00000384 = 900 (frame count constant)
     Then optionally:
       [4 bytes] STAT_HEADER:  0x0190 | 0x0200 (marks start of stat values)
       [8 bytes] STAT_VALUES:  3 x uint16 LE + padding
     Then optionally:
       [4 bytes] PROGRAM_REF:  uint32 offset (0x0500-0x0600 range)
       [4 bytes] INDEX:        uint32 program index (0, 1, 2, ...)
     Terminated by a zero dword.

  B) SPAWN POSITION RECORDS (32 bytes each, FFFF-terminated):
     [0:2]   header bytes (byte0=order/group, byte1=sub-index)
     [2:4]   type_code (0x0011=ground, 0x0012=ground-alt, 0x0015=flying, 0x0024=mixed)
     [4:6]   X coordinate (signed int16)
     [6:8]   Y coordinate (signed int16)
     [8:12]  distance/radius value (uint32)
     [12:16] flags (uint32, 0x0000=normal, 0x0800=variant, 0x0C00=flying-variant)
     [16:18] marker ID (uint16, unique per-record identifier)
     [18:24] separator: 0xFFFF 0xFFFFFFFF (6 bytes)
     [24:28] L value (uint32, behavior type index for this record's monster)
     [28:32] padding (zero)

  C) AI DISPATCH TABLE (optional, after records):
     Interleaved entries:
       [4 bytes] BYTECODE_OFFSET (0x0500-0x0600 range, monotonically increasing)
       [4 bytes] OPCODE/PARAM:
         - 0x00000000 = no program
         - 0x000000NN = simple index NN
         - 0xNNMM0000 = opcode NN, param MM
         - 0x40000000+ = render/model flag
     This table is used by the bat (flying type) and not by ground-type monsters.

CONFIG SECTION (root[max_L+1]):
  Two parts:
  PART 1: Model/render slot table (paired entries):
    [4 bytes] MODEL_REF:    offset (0x0500-0x0700 range)
    [4 bytes] RENDER_FLAGS: 0x40000300, 0x40000100, 0x40000000, or 0x00000000
    Organized in groups of 8 slots (some zeroed = unused)

  PART 2: Bytecode offset sequence:
    Sequential uint32 offsets into bytecode program area (0x0D00-0x2000 range)
    Used as a lookup table for scripts/AI programs

BYTECODE OFFSET TABLES (root[max_L+2]+):
  Each table = array of uint32 offsets into external bytecode program area.
  The offsets are AREA-SPECIFIC (different base per area), NOT shared.
  Entry count varies: 4, 17, 25, 33 entries per table.
  Tables correspond to different program categories (movement, attack, spell, etc.)
  NULL entries = no program for that slot.

  LAST TABLE (wide range):
    Split into:
    SECTION A: Sequential offsets (area-specific, for local bytecode)
    SECTION B: Interleaved (key, value) pairs that may reference GLOBAL data.
      Some pairs are SHARED across areas (identical key->value mapping),
      suggesting they point into a shared/global bytecode pool.

COMMAND SECTIONS (last root entries):
  Prefix: uint16 counting sequence (e.g., 3,4,5,6,7,8,9,10) + 0xFFFF terminator
  Then 32-byte 0B command records:
    [0]     monster slot index
    [1]     0x0B marker
    [2]     command subtype (0x04..0x0A)
    [3]     0x00
    [4:8]   coordinates (uint16 x, uint16 y)
    [8:12]  distance value
    [12:16] padding (zero)
    [16:18] marker ID
    [18:24] FFFF FFFFFFFF separator
    [24:28] L value
    [28:32] padding
  Grouped by L value, separated by FFFF FFFF blocks.
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
