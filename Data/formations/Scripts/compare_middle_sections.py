#!/usr/bin/env python3
"""
compare_middle_sections.py - Dump and compare middle sections for N=3 and N=4 areas.

Dumps:
  1. Vanilla Area 1 (N=3, 124 bytes at 0xF7A900) - labeled sections
  2. Vanilla Area 2 (N=4, 168 bytes at 0xF7E100) - labeled sections
  3. What our expansion script builds for Area 1 (using same logic as add_elite_slot_cavern_f1a1.py)

Then prints pointer_table values side-by-side so we can verify the ordering.

Also dumps ALL N=4 areas found in BLAZE.ALL for cross-validation.

Usage: py -3 Data/formations/Scripts/compare_middle_sections.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# Try both vanilla extract and output (prefer vanilla for comparison)
VANILLA_BLAZE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
OUTPUT_BLAZE  = PROJECT_ROOT / "output" / "BLAZE.ALL"

AREA1_START = 0xF7A900
AREA2_START = 0xF7E100


def fmt_hex_block(data, base_offset, size, label_ranges=None):
    """Print hex block with optional labeled ranges."""
    lines = []
    # label_ranges: list of (start_rel, end_rel, label)
    for i in range(0, size, 16):
        row_off = base_offset + i
        row_bytes = data[base_offset + i : base_offset + i + 16]
        hex_cols = ' '.join(f'{b:02X}' for b in row_bytes)

        # Find label for this row
        label = ''
        if label_ranges:
            for (s, e, lbl) in label_ranges:
                if s <= i < e:
                    if i == s:
                        label = f'  <- {lbl} starts'
                    break
        lines.append(f"  {row_off:08X}: {hex_cols:<48} {label}")
    return '\n'.join(lines)


def parse_pointer_table(data, area_start, n_monsters):
    """Parse pointer_table entries from a middle section."""
    if n_monsters == 3:
        # N=3: header=12, anim=24, data=40, ptr_table at +0x4C (6 entries)
        ptr_offset = 0x4C
        n_entries = 6
    elif n_monsters == 4:
        # N=4: header=12, anim=32, data=64, ptr_table at +0x6C (7 entries)
        ptr_offset = 0x6C
        n_entries = 7
    else:
        return []

    entries = []
    for i in range(n_entries):
        val = struct.unpack_from('<I', data, area_start + ptr_offset + i * 4)[0]
        entries.append(val)
    return entries


def find_all_areas(data, search_start=0x50000, search_end=0x1800000):
    """Scan for area middle sections by looking for the 12-byte header pattern."""
    # Heuristic: header bytes 0-3 = 00 00 00 00, bytes 4-7 = 04 00 00 00 or similar
    # Then check if stats follow (contain 'Lv' prefix)
    found = []
    for off in range(search_start, search_end, 4):
        if data[off:off+4] == b'\x00\x00\x00\x00':
            b4 = struct.unpack_from('<I', data, off + 4)[0]
            if b4 in (0x00000004, 0x00000002, 0x00000003):
                # Candidate: check if remainder is zero too
                if data[off+8:off+12] == b'\x00\x00\x00\x00':
                    found.append((off, b4))
    return found


def dump_area_middle(data, area_start, n, label):
    """Dump and label a middle section."""
    if n == 3:
        middle_size = 124
        n_anim = 3; n_data_per_half = 5; n_ptr = 6; n_assign = 3
        data_start = 0x24
    else:
        middle_size = 168
        n_anim = 4; n_data_per_half = 8; n_ptr = 7; n_assign = 4
        data_start = 0x2C

    ptr_offset = 0x4C if n == 3 else 0x6C
    assign_offset = 0x64 if n == 3 else 0x88

    print(f"\n{'='*70}")
    print(f"  {label} (N={n}, {middle_size} bytes at 0x{area_start:08X})")
    print(f"{'='*70}")

    label_ranges = [
        (0x00, 0x0C, "Header (12B)"),
        (0x0C, 0x0C + n_anim * 8, f"Anim table ({n_anim}x8={n_anim*8}B)"),
        (data_start, ptr_offset, f"Data block ({n_data_per_half}x8={(ptr_offset - data_start)}B)"),
        (ptr_offset, assign_offset, f"Pointer table ({n_ptr}x4={n_ptr*4}B)"),
        (assign_offset, middle_size, f"Assignments ({n_assign}x8={n_assign*8}B)"),
    ]

    print(fmt_hex_block(data, area_start, middle_size, label_ranges))

    # Print pointer table values
    ptrs = parse_pointer_table(data, area_start, n)
    print(f"\n  Pointer table at +0x{ptr_offset:02X}: {[hex(p) for p in ptrs]}")
    non_zero = [(i, p) for i, p in enumerate(ptrs) if p != 0]
    print(f"  Non-zero entries ({len(non_zero)}): {[(i, hex(p)) for i, p in non_zero]}")

    # Print assignment entries
    print(f"\n  Assignment entries at +0x{assign_offset:02X}:")
    for i in range(n_assign):
        a = data[area_start + assign_offset + i*8 : area_start + assign_offset + i*8 + 8]
        print(f"    Slot {i}: {a.hex()}  model={a[0]:02X} L={a[1]:02X} tex={a[2]:02X} "
              f"uid={a[4]:02X} R={a[5]:02X} flag={a[7]:02X}")

    return ptrs


def simulate_expansion(data, area1_start):
    """Simulate what add_elite_slot_cavern_f1a1.py builds, return the 168-byte result."""
    area_data = bytes(data[area1_start:area1_start + 124 + 288 + 9000])  # generous

    middle = bytearray(168)

    # Header (12 bytes)
    middle[0x00:0x0C] = area_data[0x00:0x0C]

    # Anim table (4x8 = 32 bytes)
    middle[0x0C:0x14] = area_data[0x0C:0x14]  # Slot 0 (Goblin)
    middle[0x14:0x1C] = area_data[0x14:0x1C]  # Slot 1 (Shaman)
    middle[0x1C:0x24] = area_data[0x1C:0x24]  # Slot 2 (Bat)
    middle[0x24:0x2C] = area_data[0x14:0x1C]  # Slot 3 (E-Shaman = copy Shaman)

    # Pointed entries (4x8 = 32 bytes)
    middle[0x2C:0x34] = area_data[0x24:0x2C]
    middle[0x34:0x3C] = area_data[0x2C:0x34]
    middle[0x3C:0x44] = area_data[0x34:0x3C]
    middle[0x44:0x4C] = area_data[0x2C:0x34]

    # Unpointed entries (4x8 = 32 bytes)
    struct.pack_into('<I', middle, 0x4C, 0x0000000C)
    struct.pack_into('<I', middle, 0x50, 0x00030000)
    middle[0x54:0x5C] = area_data[0x3C:0x44]
    middle[0x5C:0x64] = area_data[0x44:0x4C]
    struct.pack_into('<I', middle, 0x64, 0x00000024)
    struct.pack_into('<I', middle, 0x68, 0x00044000)

    # Pointer table (7x4 = 28 bytes)  -- THE SUSPECT
    pointers = [0x00000000, 0x00000000,
                0x0000002C, 0x00000034, 0x0000003C, 0x00000044,
                0x00000000]
    for i, ptr in enumerate(pointers):
        struct.pack_into('<I', middle, 0x6C + i * 4, ptr)

    # Assignments (4x8 = 32 bytes)
    middle[0x88:0x90] = area_data[0x64:0x6C]
    middle[0x90:0x98] = area_data[0x6C:0x74]
    middle[0x98:0xA0] = area_data[0x74:0x7C]
    middle[0xA0:0xA8] = b'\x03\x01\x01\x00\x03\x05\x00\x40'

    return bytes(middle)


def main():
    # Load binary
    blaze_path = VANILLA_BLAZE if VANILLA_BLAZE.exists() else OUTPUT_BLAZE
    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found")
        return 1

    data = blaze_path.read_bytes()
    print(f"[OK] Loaded {blaze_path.name} ({len(data):,} bytes)")

    # Dump Area 1 (N=3 vanilla)
    ptrs1 = dump_area_middle(data, AREA1_START, 3, "Vanilla Area 1 (Cavern F1)")

    # Dump Area 2 (N=4 vanilla)
    ptrs2 = dump_area_middle(data, AREA2_START, 4, "Vanilla Area 2 (Cavern F1)")

    # Show pointer table comparison
    print("\n" + "="*70)
    print("  POINTER TABLE COMPARISON")
    print("="*70)
    print(f"\n  Area 1 (N=3, 6 entries at +0x4C):")
    for i, p in enumerate(ptrs1):
        marker = " <-- POINTER" if p != 0 else ""
        print(f"    [{i}] = 0x{p:08X}{marker}")

    print(f"\n  Area 2 (N=4, 7 entries at +0x6C):")
    for i, p in enumerate(ptrs2):
        marker = " <-- POINTER" if p != 0 else ""
        print(f"    [{i}] = 0x{p:08X}{marker}")

    print(f"\n  Our expansion script builds (7 entries):")
    sim_ptrs = [0x00000000, 0x00000000, 0x0000002C, 0x00000034, 0x0000003C, 0x00000044, 0x00000000]
    for i, p in enumerate(sim_ptrs):
        matches = " <-- MATCHES AREA2" if i < len(ptrs2) and p == ptrs2[i] else (" <-- DIFFERS!" if p != 0 or (i < len(ptrs2) and ptrs2[i] != 0) else "")
        print(f"    [{i}] = 0x{p:08X}{matches}")

    # Simulate expansion and compare with Area 2
    print("\n" + "="*70)
    print("  SIMULATED EXPANSION vs AREA 2 - byte-by-byte diff")
    print("="*70)

    sim = simulate_expansion(data, AREA1_START)
    area2 = data[AREA2_START:AREA2_START + 168]

    diffs = []
    for i in range(168):
        if sim[i] != area2[i]:
            diffs.append((i, sim[i], area2[i]))

    if not diffs:
        print("\n  [PERFECT MATCH] Simulated expansion identical to Area 2 (all 168 bytes)")
    else:
        print(f"\n  {len(diffs)} byte differences:")
        for (off, sim_val, a2_val) in diffs[:50]:
            section = ""
            if off < 0x0C:
                section = "(header)"
            elif off < 0x2C:
                section = "(anim_table)"
            elif off < 0x6C:
                section = "(data_block)"
            elif off < 0x88:
                section = "(pointer_table)"
            else:
                section = "(assignments)"
            print(f"    +0x{off:02X}: sim=0x{sim_val:02X} area2=0x{a2_val:02X} {section}")

    # Also: search for other N=4 areas by scanning for 168-byte middle sections
    # with 7-entry pointer tables having 4 non-zero values
    print("\n" + "="*70)
    print("  SCAN: All areas with N=4 pointer tables (4 non-zero in 7 entries)")
    print("="*70)
    n4_areas = []
    for scan_off in range(0x50000, min(len(data) - 200, 0x1800000), 4):
        # Look for header pattern: 12 bytes of 00/specific pattern
        h = data[scan_off:scan_off+12]
        if h[0:4] == b'\x00\x00\x00\x00' and h[8:12] == b'\x00\x00\x00\x00':
            # Read pointer table at +0x6C (N=4 layout)
            try:
                ptrs = [struct.unpack_from('<I', data, scan_off + 0x6C + i*4)[0] for i in range(7)]
                non_zero = sum(1 for p in ptrs if p != 0)
                if non_zero == 4:
                    # Check pointers are plausible offsets (< 0x200)
                    nz_vals = [p for p in ptrs if p != 0]
                    if all(0x10 < p < 0x100 for p in nz_vals):
                        n4_areas.append((scan_off, ptrs, h))
            except Exception:
                pass

    # Deduplicate and print top results
    seen = set()
    printed = 0
    for off, ptrs, hdr in n4_areas:
        if off in seen or printed >= 20:
            continue
        seen.add(off)
        # Verify assignments are present (check for 0x40 flag byte at offset+0x88+7)
        if len(data) > off + 0xA8:
            assign_flags = [data[off + 0x88 + i*8 + 7] for i in range(4)]
            has_40 = any(f == 0x40 for f in assign_flags)
        else:
            has_40 = False
        nz_idx = [i for i, p in enumerate(ptrs) if p != 0]
        print(f"  0x{off:08X}: ptrs={[hex(p) for p in ptrs if p != 0]} at indices {nz_idx}  "
              f"hdr[4]={hdr[4]:02X} {'[has 0x40 flag]' if has_40 else ''}")
        printed += 1

    if printed == 0:
        print("  None found")

    return 0


if __name__ == '__main__':
    exit(main())
