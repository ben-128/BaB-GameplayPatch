#!/usr/bin/env python3
"""
find_overlay_refs.py -- Search for ALL absolute references to Cavern F1 Area 1
sections within the Cavern overlay region, and dump surrounding context.

Searches for vanilla addresses:
  0xF7A900 = AREA_START / middle_start
  0xF7A97C = group_offset / stats_start
  0xF7AA9C = script_area_start
  0xF7AEB4 = spawn_points_start
  0xF7AFFC = formation_start  (known, 4 refs)
  0xF7B520 = zone_spawns_start
  0xF7B8FC = zone_spawns[mid]  (known, 2 refs)

Also searches for:
  N=3 as MIPS immediate: bytes 03 00 XX 24 (addiu $reg, $zero, 3)
  124 = 0x7C as MIPS immediate: bytes 7C 00 XX 24 (addiu $reg, $zero, 0x7C)
  288 = 0x120 as MIPS immediate: bytes 20 01 XX 24 (addiu $reg, $zero, 0x120)

Usage: py -3 Data/formations/Scripts/find_overlay_refs.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern overlay region — we know the formation refs are around 0x1892000
# Search a generous window around that area
OVERLAY_SEARCH_START = 0x1880000
OVERLAY_SEARCH_END   = 0x18A0000

# Vanilla section addresses for Cavern F1 Area 1
VANILLA_REFS = {
    "AREA_START":          0x00F7A900,
    "group_offset(stats)": 0x00F7A97C,
    "script_start":        0x00F7AA9C,
    "spawn_points_start":  0x00F7AEB4,
    "formation_start":     0x00F7AFFC,
    "zone_spawns_start":   0x00F7B520,
    "zone_spawns_mid":     0x00F7B8FC,
}

# Expected new values after 140-byte shift
SHIFT = 0x8C  # 140

NEW_REFS = {k: v + SHIFT for k, v in VANILLA_REFS.items()}
# AREA_START does NOT shift (in-place rewrite keeps boundaries)
NEW_REFS["AREA_START"] = VANILLA_REFS["AREA_START"]
# group_offset shifts by MIDDLE_EXPANSION (44) not TOTAL_EXPANSION (140)
NEW_REFS["group_offset(stats)"] = VANILLA_REFS["group_offset(stats)"] + 44


def search_uint32_le(data, target, region_start, region_end, label):
    """Search for a uint32 LE value at any byte offset (non-aligned allowed)."""
    target_bytes = struct.pack('<I', target)
    results = []
    region = data[region_start:region_end]
    start = 0
    while True:
        pos = region.find(target_bytes, start)
        if pos == -1:
            break
        abs_pos = region_start + pos
        results.append(abs_pos)
        start = pos + 1
    return results


def dump_context(data, offset, before=16, after=32):
    """Dump hex bytes around offset."""
    start = max(0, offset - before)
    end = min(len(data), offset + after)
    chunk = data[start:end]
    hex_str = chunk.hex()
    # Format in groups of 8 bytes
    lines = []
    for i in range(0, len(chunk), 16):
        row_offset = start + i
        row_bytes = chunk[i:i+16]
        hex_cols = ' '.join(f'{b:02X}' for b in row_bytes)
        marker = ' <<< TARGET' if start + i <= offset < start + i + 16 else ''
        lines.append(f"  {row_offset:08X}: {hex_cols:<48}{marker}")
    return '\n'.join(lines)


def search_mips_immediate(data, imm_value, region_start, region_end, label):
    """
    Search for MIPS instructions that load imm_value as a 16-bit immediate.
    Pattern: XX XX rr OP where XX XX = imm_value LE, OP = 24/34/3C (addiu/ori/andi)
    Only matches 4-byte aligned positions.
    """
    imm_lo = imm_value & 0xFFFF
    imm_bytes_le = struct.pack('<H', imm_lo)
    results = []

    for pos in range(region_start, min(region_end - 4, len(data) - 4), 4):
        word_bytes = data[pos:pos+4]
        # Little-endian MIPS: word_bytes[0:2] = lower 16 bits, word_bytes[2] = rs, word_bytes[3] = opcode
        if word_bytes[0:2] == imm_bytes_le:
            opcode = word_bytes[3]
            # addiu=0x24, ori=0x34, andi=0x30, lui=0x3C
            if opcode in (0x24, 0x34, 0x30, 0x3C):
                rs = word_bytes[2]
                rt = (struct.unpack('<I', word_bytes)[0] >> 16) & 0x1F
                results.append((pos, opcode, rs, rt, imm_lo))
    return results


def main():
    if not BLAZE_ALL.exists():
        print(f"[ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        return 1

    data = bytearray(BLAZE_ALL.read_bytes())
    print(f"[OK] Loaded BLAZE.ALL ({len(data):,} bytes)")
    print(f"     Search region: 0x{OVERLAY_SEARCH_START:X} - 0x{OVERLAY_SEARCH_END:X}")
    print()

    total_found = 0

    # ── 1. Search for ALL absolute address refs ──────────────────────────────
    print("=" * 70)
    print("  ABSOLUTE ADDRESS REFERENCES (uint32 LE, non-aligned search)")
    print("=" * 70)
    print()

    for label, vanilla_val in VANILLA_REFS.items():
        new_val = NEW_REFS[label]
        hits_vanilla = search_uint32_le(data, vanilla_val,
                                        OVERLAY_SEARCH_START, OVERLAY_SEARCH_END, label)
        hits_new = search_uint32_le(data, new_val,
                                    OVERLAY_SEARCH_START, OVERLAY_SEARCH_END, label)

        if hits_vanilla or hits_new:
            total_found += len(hits_vanilla) + len(hits_new)
            print(f"[{label}]")
            print(f"  Vanilla 0x{vanilla_val:08X}: {len(hits_vanilla)} hits")
            for off in hits_vanilla:
                print(f"    @ 0x{off:08X} (alignment: {off % 4})")
                print(dump_context(data, off))
                print()
            print(f"  New     0x{new_val:08X}: {len(hits_new)} hits")
            for off in hits_new:
                print(f"    @ 0x{off:08X} (alignment: {off % 4})")
                print(dump_context(data, off))
                print()
        else:
            print(f"[{label}]  0x{vanilla_val:08X} -> 0x{new_val:08X}: NOT FOUND in overlay region")

    print()

    # ── 2. Also search for these refs ANYWHERE in the entire file ───────────
    print("=" * 70)
    print("  FULL-FILE SEARCH (for group_offset and script_start only)")
    print("=" * 70)
    print()
    for label in ["group_offset(stats)", "script_start", "spawn_points_start"]:
        vanilla_val = VANILLA_REFS[label]
        hits = search_uint32_le(data, vanilla_val, 0, len(data), label)
        # Exclude hits in the area data itself (0xF7A900 region is in actual data section)
        outside_hits = [h for h in hits if not (0xF7A900 <= h <= 0xF7CA48)]
        print(f"[{label}] 0x{vanilla_val:08X}: {len(hits)} total, "
              f"{len(outside_hits)} outside area")
        for off in outside_hits:
            print(f"    @ 0x{off:08X}")
            print(dump_context(data, off))
            print()

    print()

    # ── 3. Search for MIPS immediates near overlay refs ──────────────────────
    print("=" * 70)
    print("  MIPS IMMEDIATE SEARCH (4-byte aligned, overlay region only)")
    print("=" * 70)
    print()

    imm_targets = [
        (3,     "N=3 (monster count)"),
        (4,     "N=4 (new monster count)"),
        (0x7C,  "124 = vanilla middle section size"),
        (0xA8,  "168 = expanded middle section size"),
        (0x120, "288 = vanilla stats size (3x96)"),
        (0x180, "384 = expanded stats size (4x96)"),
        (0x60,  "96 = bytes per stat block"),
        (0x380, "896 = formation area bytes"),
    ]

    opcode_names = {0x24: "addiu", 0x34: "ori", 0x30: "andi", 0x3C: "lui"}

    for imm_val, imm_label in imm_targets:
        hits = search_mips_immediate(data, imm_val,
                                     OVERLAY_SEARCH_START, OVERLAY_SEARCH_END, imm_label)
        if hits:
            print(f"  imm=0x{imm_val:04X} ({imm_label}): {len(hits)} instructions")
            for pos, opcode, rs, rt, imm in hits:
                op_name = opcode_names.get(opcode, f"OP{opcode:02X}")
                print(f"    0x{pos:08X}: {op_name} $r{rt}, $r{rs}, 0x{imm:04X}")
        else:
            print(f"  imm=0x{imm_val:04X} ({imm_label}): not found")

    print()
    print(f"Total absolute refs found: {total_found}")
    return 0


if __name__ == '__main__':
    exit(main())
