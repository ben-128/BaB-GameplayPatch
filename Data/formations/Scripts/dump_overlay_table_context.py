#!/usr/bin/env python3
"""
dump_overlay_table_context.py - Deep dive into the overlay data table around the 6 refs.

Goals:
1. Dump 256 bytes around each known ref to see the full data table structure
2. Search for N=3 (0x03), N=4 (0x04), middle_size=124 (0x7C), 168 (0xA8) as
   DATA BYTES (not MIPS instructions) anywhere within 256 bytes of each ref
3. Full-file search for formation_start (0x00F7AFFC) OUTSIDE the known overlay region
4. Full-file search for ALL addresses pointing into Area 1's boundary [0xF7A900, 0xF7CA48)
5. Dump the 64 bytes BETWEEN consecutive refs to reveal table structure

Usage: py -3 Data/formations/Scripts/dump_overlay_table_context.py
"""

import struct
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL   = PROJECT_ROOT / "output" / "BLAZE.ALL"

AREA1_START = 0xF7A900
AREA1_END   = 0xF7CA48

VANILLA_REFS = {
    "formation_start ref 1":  0x18920CB,
    "zone_spawns_mid ref 1":  0x18920DB,
    "formation_start ref 2":  0x1892133,
    "formation_start ref 3":  0x189234B,
    "zone_spawns_mid ref 2":  0x189235B,
    "formation_start ref 4":  0x18923B3,
}

FORMATION_START_VANILLA = 0x00F7AFFC
OVERLAY_REGION = (0x1880000, 0x18A0000)


def search_all_area1_refs(data):
    """Full-file scan for ALL uint32 LE values in [AREA1_START, AREA1_END) range."""
    print("=" * 70)
    print("  FULL-FILE SCAN: All addresses pointing into Area 1 boundary")
    print(f"  Range: [0x{AREA1_START:08X}, 0x{AREA1_END:08X})")
    print("=" * 70)

    found_by_value = {}
    step = 1  # non-aligned search
    for off in range(0, len(data) - 4, step):
        val = struct.unpack_from('<I', data, off)[0]
        if AREA1_START <= val < AREA1_END:
            found_by_value.setdefault(val, []).append(off)

    # Sort by value
    print(f"\n  Found {sum(len(v) for v in found_by_value.values())} total refs "
          f"({len(found_by_value)} distinct values):\n")

    for val in sorted(found_by_value.keys()):
        locs = found_by_value[val]
        overlay_locs = [l for l in locs if OVERLAY_REGION[0] <= l < OVERLAY_REGION[1]]
        other_locs   = [l for l in locs if l not in overlay_locs]
        print(f"  Value=0x{val:08X} (offset from area: +0x{val-AREA1_START:04X}): "
              f"{len(locs)} total refs")
        for loc in overlay_locs:
            print(f"    0x{loc:08X} [in overlay] align={loc%4}")
        for loc in other_locs:
            print(f"    0x{loc:08X} [OUTSIDE overlay] align={loc%4}")
    return found_by_value


def dump_region(data, start, end, label, highlight_offsets=None):
    """Hex dump a region with optional highlights."""
    print(f"\n  --- {label} (0x{start:08X} - 0x{end:08X}, {end-start} bytes) ---")
    for row in range(start, end, 16):
        row_end = min(row + 16, end)
        row_bytes = data[row:row_end]
        hex_str = ' '.join(f'{b:02X}' for b in row_bytes)
        marker = ''
        if highlight_offsets:
            for h_off in highlight_offsets:
                if row <= h_off < row + 16:
                    marker = f'  << REF at +{h_off - row}'
                    break
        print(f"    {row:08X}: {hex_str:<48} {marker}")


def analyze_data_table_structure(data):
    """Try to identify the table structure by looking at the gaps between refs."""
    print("\n" + "=" * 70)
    print("  OVERLAY DATA TABLE STRUCTURE ANALYSIS")
    print("=" * 70)

    # The 6 refs sorted by offset
    sorted_refs = sorted(VANILLA_REFS.items(), key=lambda x: x[1])

    print("\n  Ref positions and gaps:")
    for i, (label, off) in enumerate(sorted_refs):
        val = struct.unpack_from('<I', data, off)[0]
        print(f"  0x{off:08X} ({label}): value=0x{val:08X}, align={off%4}")
        if i > 0:
            prev_off = sorted_refs[i-1][1]
            gap = off - prev_off
            print(f"    gap from previous: {gap} bytes (0x{gap:X})")

    # Dump the full range from first ref-256 to last ref+128
    first_ref = min(VANILLA_REFS.values())
    last_ref  = max(VANILLA_REFS.values())
    dump_start = (first_ref - 64) & ~0xF  # align to 16
    dump_end   = min(last_ref + 64, len(data))

    print(f"\n  Full data table region: 0x{dump_start:08X} - 0x{dump_end:08X}")
    print(f"  ({dump_end - dump_start} bytes)\n")
    dump_region(data, dump_start, dump_end,
                "Overlay data table region",
                list(VANILLA_REFS.values()))

    # Scan for suspicious small values (N=3, N=4, 0x7C, 0xA8) as bytes near refs
    print("\n  Suspicious byte values near refs (+/-256):")
    suspects = {3: "N=3", 4: "N=4", 0x7C: "0x7C=124 (vanilla middle size)",
                0xA8: "0xA8=168 (expanded middle size)",
                0x60: "0x60=96 (stat block size)", 0x120: "N/A (288=3x96)"}

    scan_start = first_ref - 256
    scan_end   = last_ref + 256

    for val, meaning in suspects.items():
        locs = []
        for off in range(max(0, scan_start), min(len(data), scan_end)):
            if data[off] == val:
                locs.append(off)
        if locs:
            nearby = [l for l in locs if any(abs(l - r) < 64 for r in VANILLA_REFS.values())]
            print(f"    byte=0x{val:02X} ({meaning}): "
                  f"{len(locs)} in scan range, {len(nearby)} within 64B of a ref")
            for l in nearby[:10]:
                # Find nearest ref
                nearest_ref_name = min(VANILLA_REFS.items(), key=lambda x: abs(x[1]-l))
                print(f"      0x{l:08X} (dist {l-nearest_ref_name[1]:+d} from {nearest_ref_name[0]})")


def check_overlay_code_for_N_values(data):
    """
    Look for MIPS instructions that encode N=3 or N=4 as immediates SPECIFICALLY
    in the code region near/between the ref clusters.
    The refs are in data sections; the code that READS them should be nearby.
    """
    print("\n" + "=" * 70)
    print("  MIPS CODE SCAN near overlay refs")
    print("  Looking for: addiu/ori with imm=3,4,7C,A8 within +/-2KB of any ref")
    print("=" * 70)

    # Extend search window
    scan_center = min(VANILLA_REFS.values())
    scan_start  = scan_center - 0x800
    scan_end    = max(VANILLA_REFS.values()) + 0x800

    imm_targets = [
        (3,    "N=3"),
        (4,    "N=4"),
        (0x7C, "124=vanilla_middle_size"),
        (0xA8, "168=expanded_middle_size"),
        (0x60, "96=stat_block_size"),
        (0x7,  "7=ptr_table_entries_N4"),
        (0x6,  "6=ptr_table_entries_N3"),
    ]

    opcodes = {0x09: "addiu", 0x0D: "ori", 0x08: "addi", 0x0C: "andi"}

    for imm_val, imm_label in imm_targets:
        hits = []
        imm_lo = imm_val & 0xFFFF
        imm_hi = (imm_val >> 16) & 0xFF
        for pos in range(scan_start & ~3, (scan_end + 4) & ~3, 4):
            if pos + 4 > len(data):
                break
            word = struct.unpack_from('<I', data, pos)[0]
            op6  = (word >> 26) & 0x3F
            imm  = word & 0xFFFF
            if imm == imm_lo and op6 in opcodes:
                hits.append((pos, op6, word))

        if hits:
            print(f"\n  imm=0x{imm_val:04X} ({imm_label}): {len(hits)} instructions")
            for pos, op6, word in hits[:10]:
                rt = (word >> 16) & 0x1F
                rs = (word >> 21) & 0x1F
                dist_from_refs = min(abs(pos - r) for r in VANILLA_REFS.values())
                print(f"    0x{pos:08X}: {opcodes[op6]:6s} $r{rt}, $r{rs}, {imm_val}  "
                      f"(dist {dist_from_refs} from nearest ref)")


def dump_each_ref_context(data):
    """Dump 128 bytes before and after each ref."""
    print("\n" + "=" * 70)
    print("  PER-REF CONTEXT DUMPS (64B before, 64B after)")
    print("=" * 70)

    for label, off in sorted(VANILLA_REFS.items(), key=lambda x: x[1]):
        val = struct.unpack_from('<I', data, off)[0]
        dump_start = max(0, off - 64)
        dump_end   = min(len(data), off + 64)
        dump_region(data, dump_start, dump_end, f"{label} @ 0x{off:08X} = 0x{val:08X}", [off])


def main():
    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found")
        return 1

    data = BLAZE_ALL.read_bytes()
    print(f"[OK] Loaded BLAZE.ALL ({len(data):,} bytes)")

    # 1. Full-file scan for ALL Area 1 refs
    found = search_all_area1_refs(data)

    # 2. Data table structure analysis
    analyze_data_table_structure(data)

    # 3. MIPS code scan
    check_overlay_code_for_N_values(data)

    # 4. Per-ref context dumps
    dump_each_ref_context(data)

    return 0


if __name__ == '__main__':
    exit(main())
