#!/usr/bin/env python3
"""
scan_area_headers.py - Scan ALL area middle section headers in vanilla BLAZE.ALL.

Goals:
1. Find all areas with header pattern [00 00 00 00][N=2,3,or 4][00 00 00 00]
2. Print the full first 32 bytes of each candidate to compare N=3 vs N=4
3. Understand what byte[4-7] actually encodes if not N

Usage: py -3 Data/formations/Scripts/scan_area_headers.py
"""

import struct
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

VANILLA_BLAZE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
OUTPUT_BLAZE  = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Known area positions for cross-checking
AREA1_START = 0xF7A900   # N=3 vanilla
AREA2_START = 0xF7E100   # N=4 vanilla

SCAN_START = 0x50000
SCAN_END   = 0x1800000


def dump_area_header(data, off, label=""):
    h = data[off:off+48]
    hex_str = ' '.join(f'{b:02X}' for b in h)
    n_field = struct.unpack_from('<I', data, off+4)[0]
    print(f"  {off:08X} n_field={n_field} {label}")
    # Print in 16-byte rows
    for row in range(0, 48, 16):
        row_bytes = h[row:row+16]
        hex_row = ' '.join(f'{b:02X}' for b in row_bytes)
        labels = ''
        if row == 0:
            labels = '  [header: 0x00-0x0B]'
        elif row == 16:
            labels = '  [anim_table_start: 0x10-...]'
        print(f"    +{row:02X}: {hex_row}  {labels}")
    print()


def scan_headers(data):
    """Find all areas by header pattern."""
    print("=" * 70)
    print("  AREA HEADER SCAN")
    print(f"  Range: [0x{SCAN_START:X}, 0x{SCAN_END:X})")
    print("=" * 70)
    print()

    found = []
    for off in range(SCAN_START, min(len(data) - 16, SCAN_END), 4):
        if data[off:off+4] == b'\x00\x00\x00\x00':
            n_val = struct.unpack_from('<I', data, off+4)[0]
            if n_val in (2, 3, 4) and data[off+8:off+12] == b'\x00\x00\x00\x00':
                found.append((off, n_val))

    print(f"Found {len(found)} candidates with pattern [00 00 00 00][N=2,3,4][00 00 00 00]")
    print()

    # Group by N
    by_n = {}
    for off, n in found:
        by_n.setdefault(n, []).append(off)

    for n in sorted(by_n.keys()):
        print(f"  N={n}: {len(by_n[n])} candidates")
        for off in by_n[n]:
            label = ""
            if off == AREA1_START:
                label = "  *** AREA1_START (Cavern F1 A1, vanilla N=3)"
            elif off == AREA2_START:
                label = "  *** AREA2_START (Cavern F1 A2, vanilla N=4)"
        print()

    return found, by_n


def compare_n3_n4_headers(data, by_n):
    """Compare first 32 bytes of N=3 vs N=4 candidates side by side."""
    print("=" * 70)
    print("  FIRST 16 N=3 CANDIDATES")
    print("=" * 70)
    print()
    for off in by_n.get(3, [])[:16]:
        label = "*** AREA1_START" if off == AREA1_START else ""
        dump_area_header(data, off, label)

    print("=" * 70)
    print("  FIRST 16 N=4 CANDIDATES")
    print("=" * 70)
    print()
    for off in by_n.get(4, [])[:16]:
        label = "*** AREA2_START" if off == AREA2_START else ""
        dump_area_header(data, off, label)


def check_anim_table_entry_count(data, found):
    """
    For each candidate area, check the anim table area.
    The anim table starts at +0x0C, each entry is 8 bytes.
    For N=3: 3 entries -> ends at +0x0C+24 = +0x24
    For N=4: 4 entries -> ends at +0x0C+32 = +0x2C

    Theory: the engine might compute N from the header field at +0x04
    or from the anim entries themselves.
    Read bytes 0x0C through 0x34 to see what distinguishes N=3 from N=4.
    """
    print("=" * 70)
    print("  ANIM TABLE REGION ANALYSIS (+0x0C to +0x34)")
    print("  Checking for how anim entry count is determined")
    print("=" * 70)
    print()

    # Check AREA1 and AREA2 specifically
    for area_off, label in [(AREA1_START, "Area1 N=3 vanilla"), (AREA2_START, "Area2 N=4 vanilla")]:
        print(f"  {label} at 0x{area_off:08X}:")
        for row_off in range(0, 0x40, 8):
            chunk = data[area_off + row_off : area_off + row_off + 8]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            section = ""
            if row_off == 0x00:
                section = "header[0:8]"
            elif row_off == 0x08:
                section = "header[8:12] + anim[0][0:4]"
            elif 0x0C <= row_off < 0x2C:
                idx = (row_off - 0x0C) // 8
                section = f"anim[{idx}] or part thereof"
            elif row_off == 0x2C:
                section = "data_block_start (N=4) or middle (N=3)"
            elif row_off == 0x34:
                section = "data_block"
            elif row_off == 0x38:
                section = "data_block"
            print(f"    +{row_off:02X}: {hex_str}  {section}")
        print()


def scan_nearby_for_n_field(data, found):
    """
    For known AREA1 and AREA2:
    Look at the 256 bytes BEFORE the area start for any N-encoding.
    The engine might have a separate table that maps area_index -> N.
    """
    print("=" * 70)
    print("  256 BYTES BEFORE EACH KNOWN AREA")
    print("=" * 70)
    print()

    for area_off, label in [(AREA1_START, "Area1 (N=3)"), (AREA2_START, "Area2 (N=4)")]:
        pre_start = max(0, area_off - 256)
        print(f"  {label}: 0x{pre_start:08X} to 0x{area_off:08X}")
        for row in range(pre_start, area_off, 16):
            row_bytes = data[row:row+16]
            hex_str = ' '.join(f'{b:02X}' for b in row_bytes)
            # Flag interesting bytes (small numbers like 3, 4)
            flag = ''
            for i, b in enumerate(row_bytes):
                if b in (3, 4, 0x7C, 0xA8):
                    flag += f' [{i}]={b}'
            print(f"    {row:08X}: {hex_str}{flag}")
        print()


def check_full_header_bytes(data):
    """
    Dump the full 12-byte header for Area 1 and Area 2, byte by byte.
    Then dump 16 bytes AFTER each area start to see what follows.
    """
    print("=" * 70)
    print("  FULL 12-BYTE HEADER ANALYSIS")
    print("=" * 70)
    print()

    for area_off, label in [(AREA1_START, "Area1 N=3 vanilla"), (AREA2_START, "Area2 N=4 vanilla")]:
        header = data[area_off:area_off+12]
        print(f"  {label} at 0x{area_off:08X}:")
        for i, b in enumerate(header):
            print(f"    byte[{i:2d}] = 0x{b:02X} ({b:3d})")
        # Also check the 12-byte header as LE16 and LE32 fields
        words = [struct.unpack_from('<H', data, area_off + i*2)[0] for i in range(6)]
        dwords = [struct.unpack_from('<I', data, area_off + i*4)[0] for i in range(3)]
        print(f"    as LE16: {[hex(w) for w in words]}")
        print(f"    as LE32: {[hex(d) for d in dwords]}")
        print()


def find_N_in_anim_table(data):
    """
    Key hypothesis: The engine reads N from the ANIM TABLE ITSELF,
    by counting valid entries (non-zero or with sentinel).
    Each anim entry is 8 bytes. If entries use 0x00000000 as terminator,
    the engine would count until it hits zero.

    For N=3 Area 1: should have 3 non-zero entries then possibly a zero
    For N=4 Area 2: should have 4 non-zero entries then possibly a zero
    """
    print("=" * 70)
    print("  ANIM TABLE ENTRY ANALYSIS (N=3 vs N=4)")
    print("=" * 70)
    print()

    for area_off, label, expected_n in [(AREA1_START, "Area1 N=3", 3), (AREA2_START, "Area2 N=4", 4)]:
        print(f"  {label} at 0x{area_off:08X}:")
        # Read 10 anim entries (80 bytes) starting at +0x0C
        for i in range(10):
            entry_off = area_off + 0x0C + i * 8
            entry = data[entry_off:entry_off+8]
            hex_str = ' '.join(f'{b:02X}' for b in entry)
            dword0 = struct.unpack_from('<I', data, entry_off)[0]
            dword1 = struct.unpack_from('<I', data, entry_off+4)[0]
            is_zero = dword0 == 0 and dword1 == 0
            marker = " <-- ZERO (possible terminator)" if is_zero else ""
            print(f"    anim[{i}]: {hex_str}  d0=0x{dword0:08X} d1=0x{dword1:08X}{marker}")
            if is_zero and i >= expected_n:
                break
        print()


def main():
    blaze_path = VANILLA_BLAZE if VANILLA_BLAZE.exists() else OUTPUT_BLAZE
    if not blaze_path.exists():
        print("[ERROR] BLAZE.ALL not found")
        return 1

    data = blaze_path.read_bytes()
    print(f"[OK] Loaded {blaze_path.name} ({len(data):,} bytes)")
    print()

    # 1. Check full header byte-by-byte
    check_full_header_bytes(data)

    # 2. Anim table entry analysis (key for N discovery)
    find_N_in_anim_table(data)

    # 3. Scan all headers
    found, by_n = scan_headers(data)

    # 4. Compare N=3 vs N=4 headers
    compare_n3_n4_headers(data, by_n)

    # 5. Check anim table region analysis
    check_anim_table_entry_count(data, found)

    # 6. Scan 256 bytes before each area
    scan_nearby_for_n_field(data, found)

    return 0


if __name__ == '__main__':
    exit(main())
