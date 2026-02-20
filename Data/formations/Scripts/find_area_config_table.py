#!/usr/bin/env python3
"""
find_area_config_table.py - Search for area configuration tables in the Cavern overlay.

Theory: The engine might have a per-area config table like:
  area1: {N=3, stats_offset=0x7C, ...}
  area2: {N=4, stats_offset=0xA8, ...}

This would explain:
- Why Area 1 crashes (engine uses hardcoded stats_offset=0x7C from table)
- Why Area 2 works natively (table says N=4)
- Why patching overlay data refs didn't help (those are formation/spawn refs, not structure refs)

Searches:
1. Near overlay refs: look for sequences containing small structure values (0x7C, 0xA8, 0x60, 0x4C, 0x6C)
2. The ENTIRE overlay region for 16-byte table entries with N=3,4 values
3. The overlay region for absolute refs to the AREA_START (0xF7A900)
4. Compare with what Area 2's overlay entry looks like (if it exists)

Usage: py -3 Data/formations/Scripts/find_area_config_table.py
"""

import struct
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL    = PROJECT_ROOT / "output" / "BLAZE.ALL"

OVERLAY_START = 0x1880000
OVERLAY_END   = 0x18A0000

AREA1_START = 0x00F7A900
AREA2_START = 0x00F7E100

# Key structural values we want to find near AREA_START references
VANILLA_VALUES = {
    "AREA_START":       0x00F7A900,
    "vanilla_N=3":      3,
    "middle_size_N3":   0x7C,   # = 124
    "middle_size_N4":   0xA8,   # = 168
    "stats_offset_N3":  0x7C,   # = 124 (same as middle_size_N3)
    "stats_offset_N4":  0xA8,   # = 168
    "stat_block_size":  0x60,   # = 96
    "ptr_table_N3":     0x4C,   # pointer_table starts at offset 76 for N=3
    "ptr_table_N4":     0x6C,   # pointer_table starts at offset 108 for N=4
    "assign_offset_N3": 0x64,   # assignment entries at offset 100 for N=3
    "assign_offset_N4": 0x88,   # assignment entries at offset 136 for N=4
}


def find_area_start_refs(data):
    """Find all references to AREA_START (0xF7A900) in the overlay region."""
    print("=" * 70)
    print("  AREA_START (0xF7A900) REFS IN OVERLAY REGION")
    print("=" * 70)

    target = struct.pack('<I', AREA1_START)
    found = []
    for off in range(OVERLAY_START, OVERLAY_END - 4):
        if data[off:off+4] == target:
            found.append(off)

    print(f"\n  Found {len(found)} exact refs to 0x00F7A900 in overlay")
    for off in found:
        print(f"    0x{off:08X} (align={off%4})")
        start = max(OVERLAY_START, off-32)
        end = min(OVERLAY_END, off+32)
        row_bytes = data[start:end]
        hex_str = ' '.join(f'{b:02X}' for b in row_bytes)
        print(f"    Context: {hex_str}")
        print()
    return found


def find_small_values_near_area1_ref(data, ref_locations):
    """
    For each AREA_START ref, dump 256 bytes around it looking for
    small structure constants (0x7C, 0xA8, 0x60, etc.) as LE16 or LE32.
    """
    print("=" * 70)
    print("  STRUCTURE CONSTANTS NEAR AREA_START REFS")
    print("=" * 70)

    struct_vals = [0x7C, 0xA8, 0x60, 0x4C, 0x6C, 0x64, 0x88, 3, 4, 0x120, 0x180]

    for ref_off in ref_locations:
        print(f"\n  === Around AREA_START ref at 0x{ref_off:08X} ===")
        scan_start = max(OVERLAY_START, ref_off - 128)
        scan_end   = min(OVERLAY_END, ref_off + 128)

        for val in struct_vals:
            # Find as standalone LE16 or LE32 (word-aligned)
            hits = []
            for off in range(scan_start & ~1, scan_end, 1):
                b = data[off]
                if b == val:
                    hits.append((off, 'byte'))
            for off in range(scan_start & ~1, scan_end-1, 2):
                v16 = struct.unpack_from('<H', data, off)[0]
                if v16 == val:
                    hits.append((off, 'LE16'))
            for off in range(scan_start & ~3, scan_end-3, 4):
                v32 = struct.unpack_from('<I', data, off)[0]
                if v32 == val:
                    hits.append((off, 'LE32'))

            if hits:
                closest = min(hits, key=lambda x: abs(x[0] - ref_off))
                print(f"    val=0x{val:04X}: {len(hits)} hits, closest at 0x{closest[0]:08X} "
                      f"({closest[1]}, dist {closest[0]-ref_off:+d})")


def search_area_config_table(data):
    """
    Search for a 'per-area config' table in the overlay. Expected structure:
    Each entry has a small byte near 3 or 4 (N), plus the AREA_START address.
    Also look for pairs (AREA_START, middle_size) near each other.
    """
    print("\n" + "=" * 70)
    print("  SEARCH FOR AREA CONFIG TABLE PATTERN")
    print(f"  Pattern: AREA_START (0x{AREA1_START:08X}) followed within 32B by N=3 or 0x7C")
    print("=" * 70)

    target1 = struct.pack('<I', AREA1_START)
    target2 = struct.pack('<I', AREA2_START)

    for off in range(OVERLAY_START, OVERLAY_END - 4):
        found_a1 = data[off:off+4] == target1
        found_a2 = data[off:off+4] == target2
        if not (found_a1 or found_a2):
            continue

        area = "Area1" if found_a1 else "Area2"
        print(f"\n  {area} addr found at 0x{off:08X}")

        # Scan ±64 bytes for structural values
        scan = data[max(0, off-64):min(len(data), off+64)]
        scan_base = max(0, off-64)

        interesting = {}
        for i, b in enumerate(scan):
            if b in [3, 4, 0x7C, 0xA8, 0x60, 0x4C, 0x6C, 0x88]:
                interesting.setdefault(b, []).append(scan_base + i)

        for val, positions in sorted(interesting.items()):
            print(f"    byte=0x{val:02X}: at {[hex(p) for p in positions[:5]]}")


def search_overlay_for_N3_configs(data):
    """
    Search the entire overlay region for any 4-byte aligned value = 3 (N=3) followed
    within 16 bytes by 0x7C (middle section size). This would be a config table.
    """
    print("\n" + "=" * 70)
    print("  ALIGNED SEARCH: LE32 value=3 followed within 16B by byte 0x7C")
    print("  (Looking for area config: {N=3, middle_size=0x7C})")
    print("=" * 70)

    found_N3 = []
    for off in range(OVERLAY_START, OVERLAY_END - 20, 4):
        v = struct.unpack_from('<I', data, off)[0]
        if v == 3:
            # Check for 0x7C within next 16 bytes
            nearby = data[off:off+20]
            if 0x7C in nearby:
                pos_7C = nearby.index(0x7C)
                found_N3.append((off, off + pos_7C))

    print(f"\n  Found {len(found_N3)} candidate patterns")
    for (off_3, off_7C) in found_N3[:20]:
        ctx = data[off_3:off_3+20]
        print(f"    N=3 at 0x{off_3:08X}, 0x7C at 0x{off_7C:08X}: {ctx.hex()}")


def search_structural_offsets_in_overlay(data):
    """
    Search for the pair (0x7C, 0xA8) or (124, 168) stored as consecutive bytes
    or nearby in the overlay - this would be a [N3_size, N4_size] lookup.
    """
    print("\n" + "=" * 70)
    print("  SEARCH FOR STRUCTURAL OFFSET PAIRS (0x7C/0xA8 = 124/168)")
    print("=" * 70)

    # As consecutive bytes: 7C A8 or A8 7C
    pair1 = bytes([0x7C, 0xA8])
    pair2 = bytes([0xA8, 0x7C])
    # As LE16
    v1 = struct.pack('<H', 0x7C)
    v2 = struct.pack('<H', 0xA8)
    # As LE32
    v3 = struct.pack('<I', 0x7C)
    v4 = struct.pack('<I', 0xA8)

    patterns = [
        (pair1, "bytes [7C A8]"),
        (pair2, "bytes [A8 7C]"),
        (v1 + v2, "LE16 0x7C then LE16 0xA8"),
        (v3, "LE32 0x7C"),
        (v4, "LE32 0xA8"),
    ]

    for pat, desc in patterns:
        hits = []
        for off in range(OVERLAY_START, OVERLAY_END - len(pat)):
            if data[off:off+len(pat)] == pat:
                hits.append(off)
        if hits:
            print(f"\n  {desc}: {len(hits)} hits")
            for h in hits[:5]:
                ctx = data[max(OVERLAY_START, h-8):min(OVERLAY_END, h+16)]
                print(f"    0x{h:08X}: {ctx.hex()}")


def dump_overlay_code_before_data_table(data):
    """Dump 256 bytes BEFORE the known data table start (0x01892080) as MIPS context."""
    table_start = 0x01892080
    code_end    = table_start
    code_start  = max(OVERLAY_START, table_start - 256)

    print("\n" + "=" * 70)
    print(f"  OVERLAY CODE SECTION BEFORE DATA TABLE (0x{code_start:08X} to 0x{code_end:08X})")
    print("=" * 70)

    for row in range(code_start, code_end, 16):
        row_end = min(row + 16, code_end)
        row_bytes = data[row:row_end]
        hex_str = ' '.join(f'{b:02X}' for b in row_bytes)
        # Try to detect if 4-byte-aligned instruction-like (opcode in 0x00-0x3F)
        annot = ''
        if len(row_bytes) >= 4 and row % 4 == 0:
            w = struct.unpack_from('<I', row_bytes, 0)[0]
            op6 = (w >> 26) & 0x3F
            rs  = (w >> 21) & 0x1F
            rt  = (w >> 16) & 0x1F
            imm = w & 0xFFFF
            rd  = (w >> 11) & 0x1F
            if op6 == 0x09:  # addiu
                annot = f'addiu $r{rt},$r{rs},{imm if imm < 0x8000 else imm-0x10000}'
            elif op6 == 0x08:  # addi
                annot = f'addi $r{rt},$r{rs},{imm if imm < 0x8000 else imm-0x10000}'
            elif op6 == 0x0F:  # lui
                annot = f'lui $r{rt},0x{imm:04X}'
            elif op6 == 0x23:  # lw
                annot = f'lw $r{rt},{imm if imm < 0x8000 else imm-0x10000}($r{rs})'
            elif op6 == 0x2B:  # sw
                annot = f'sw $r{rt},{imm if imm < 0x8000 else imm-0x10000}($r{rs})'
            elif op6 == 0x03:  # jal
                target = ((w & 0x03FFFFFF) << 2)
                annot = f'jal 0x{target:08X}'
            elif op6 == 0x00 and (w & 0x3F) == 0x08:  # jr
                annot = f'jr $r{rs}'
            elif w == 0:
                annot = 'nop'
        print(f"    {row:08X}: {hex_str:<48} {annot}")


def main():
    if not BLAZE_ALL.exists():
        print("[ERROR] BLAZE.ALL not found")
        return 1

    data = BLAZE_ALL.read_bytes()
    print(f"[OK] Loaded BLAZE.ALL ({len(data):,} bytes)")
    print(f"     Overlay region: 0x{OVERLAY_START:X} - 0x{OVERLAY_END:X}\n")

    # 1. Find refs to AREA_START itself
    area1_refs = find_area_start_refs(data)

    # 2. Check for structural constants near AREA_START refs
    if area1_refs:
        find_small_values_near_area1_ref(data, area1_refs)

    # 3. Area config table pattern search
    search_area_config_table(data)

    # 4. Search for N=3 config pattern
    search_overlay_for_N3_configs(data)

    # 5. Search for structural offset pairs
    search_structural_offsets_in_overlay(data)

    # 6. Dump overlay code before data table
    dump_overlay_code_before_data_table(data)

    return 0


if __name__ == '__main__':
    exit(main())
