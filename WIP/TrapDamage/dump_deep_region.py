#!/usr/bin/env python3
"""
Phase 1.1: Dump the Deep Entity Region for ALL zones.

The "deep entity region" is the large unknown area in each level's script data,
located at approximately script+0x900 to script+0x1DC0 (5312 bytes).

This region contains 32-byte records with coordinates and parameters.
When modified, "dark entities" appear in-game, suggesting these are
environmental objects (potentially including traps).

Record format (32 bytes):
  bytes[0:4]   = prev_terminator / header
  bytes[4:8]   = padding (00 00 00 00) or marker (FF FF FF FF = group start)
  bytes[8:12]  = cmd_header (4 bytes)
  bytes[12:16] = [XX FF 00 00] slot/type marker
  bytes[16:18] = x (int16)
  bytes[18:20] = y (int16)
  bytes[20:22] = z (int16)
  bytes[22:24] = padding (00 00)
  bytes[24:28] = extra (uint32) - unknown parameter
  bytes[28:30] = val (uint16) - unknown parameter
  bytes[30:32] = terminator / padding

Usage: py -3 WIP/TrapDamage/dump_deep_region.py
"""

import struct
import json
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
FORMATIONS_DIR = PROJECT_ROOT / "Data" / "formations"
OUTPUT_DIR = SCRIPT_DIR / "dumps"


def load_blaze_data():
    """Load BLAZE.ALL - prefer source (unpatched) for analysis."""
    path = BLAZE_SRC if BLAZE_SRC.exists() else BLAZE_ALL
    if not path.exists():
        print(f"[ERROR] BLAZE.ALL not found at {BLAZE_SRC} or {BLAZE_ALL}")
        return None, None
    data = path.read_bytes()
    print(f"  Loaded: {path.name} ({len(data):,} bytes)")
    return data, path


def load_all_zones():
    """Load all formation JSON files and return zone info."""
    zones = []
    for json_file in sorted(FORMATIONS_DIR.rglob("*.json")):
        if json_file.name == "ai_blocks_dump.json":
            continue
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                zone = json.load(f)
            zones.append({
                'file': json_file,
                'level': zone.get('level_name', '?'),
                'name': zone.get('name', '?'),
                'group_offset': int(zone['group_offset'], 16),
                'num_monsters': len(zone.get('monsters', [])),
                'monsters': zone.get('monsters', []),
                'area_id': zone.get('area_id', '????'),
                'formation_area_start': int(zone['formation_area_start'], 16) if zone.get('formation_area_start') else None,
                'spawn_points_area_start': int(zone['spawn_points_area_start'], 16) if zone.get('spawn_points_area_start') else None,
                'zone_spawns_area_start': int(zone['zone_spawns_area_start'], 16) if zone.get('zone_spawns_area_start') else None,
            })
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"  [WARN] Skipping {json_file.name}: {e}")
    return zones


def compute_script_bounds(zone, data_len):
    """Compute the script area start and approximate end for a zone."""
    script_start = zone['group_offset'] + zone['num_monsters'] * 96

    # Find end of script area: use the earliest known area after script
    end_candidates = []
    if zone['formation_area_start']:
        end_candidates.append(zone['formation_area_start'])
    if zone['spawn_points_area_start']:
        end_candidates.append(zone['spawn_points_area_start'])

    if end_candidates:
        script_end = min(end_candidates)
    else:
        # Fallback: assume ~8KB script area
        script_end = script_start + 0x2000

    # Clamp to data bounds
    script_end = min(script_end, data_len)
    script_start = min(script_start, data_len)

    return script_start, script_end


def parse_deep_records(data, deep_start, deep_end):
    """Parse 32-byte records in the deep entity region.

    Returns list of parsed records with all fields.
    """
    records = []
    region = data[deep_start:deep_end]
    region_size = len(region)

    # Scan for [XX FF 00 00] slot markers at offset 12 within 32-byte aligned records
    # Also do a raw 32-byte stride scan
    for offset in range(0, region_size - 32, 4):
        abs_off = deep_start + offset

        # Check for slot marker pattern at various positions
        # The [XX FF 00 00] pattern appears at bytes 12-15 of a 32-byte record
        chunk = region[offset:offset+32]

        # Method 1: Look for XX FF 00 00 pattern
        for marker_pos in [8, 12]:
            if marker_pos + 4 > len(chunk):
                continue
            if chunk[marker_pos+1] == 0xFF and chunk[marker_pos+2] == 0x00 and chunk[marker_pos+3] == 0x00:
                xx = chunk[marker_pos]
                slot = xx & 0x1F
                flags = xx & 0xE0

                if slot <= 15:  # reasonable slot range
                    # Try to parse coordinates after the marker
                    coord_base = marker_pos + 4
                    if coord_base + 8 <= len(chunk):
                        x = struct.unpack_from('<h', chunk, coord_base)[0]
                        y = struct.unpack_from('<h', chunk, coord_base + 2)[0]
                        z = struct.unpack_from('<h', chunk, coord_base + 4)[0]
                        pad = struct.unpack_from('<H', chunk, coord_base + 6)[0]

                        # Remaining bytes
                        extra_base = coord_base + 8
                        extra = struct.unpack_from('<I', chunk, extra_base)[0] if extra_base + 4 <= len(chunk) else 0
                        val = struct.unpack_from('<H', chunk, extra_base + 4)[0] if extra_base + 6 <= len(chunk) else 0

                        records.append({
                            'abs_offset': abs_off,
                            'rel_offset': offset,
                            'marker_pos': marker_pos,
                            'raw_xx': xx,
                            'slot': slot,
                            'flags': flags,
                            'x': x, 'y': y, 'z': z,
                            'pad': pad,
                            'extra': extra,
                            'val': val,
                            'header': chunk[:marker_pos].hex(),
                            'raw_hex': chunk.hex(),
                        })

    # Deduplicate by abs_offset (same record found at different marker_pos)
    seen = set()
    unique = []
    for r in records:
        key = (r['abs_offset'], r['marker_pos'])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


def scan_nonzero_regions(data, start, end, granularity=16):
    """Find contiguous non-zero regions."""
    regions = []
    in_nonzero = False
    region_start = 0

    for i in range(start, end, granularity):
        chunk = data[i:i+granularity]
        is_nz = any(b != 0 for b in chunk)

        if is_nz and not in_nonzero:
            region_start = i
            in_nonzero = True
        elif not is_nz and in_nonzero:
            regions.append((region_start, i))
            in_nonzero = False

    if in_nonzero:
        regions.append((region_start, end))

    return regions


def dump_zone(data, zone, outfile):
    """Dump deep entity region for a single zone."""
    script_start, script_end = compute_script_bounds(zone, len(data))
    script_size = script_end - script_start

    # Deep region: script+0x900 to script+0x1DC0 (or end of script area)
    deep_start = script_start + 0x0900
    deep_end_ideal = script_start + 0x1DC0
    deep_end = min(deep_end_ideal, script_end)

    if deep_start >= deep_end or deep_start >= len(data):
        outfile.write(f"  [SKIP] Deep region out of bounds (script only {script_size} bytes)\n")
        return 0

    deep_size = deep_end - deep_start

    outfile.write(f"  Script: 0x{script_start:X} - 0x{script_end:X} ({script_size} bytes)\n")
    outfile.write(f"  Deep region: 0x{deep_start:X} - 0x{deep_end:X} ({deep_size} bytes)\n")

    # Check how much is non-zero
    nz_regions = scan_nonzero_regions(data, deep_start, deep_end)
    total_nz = sum(e - s for s, e in nz_regions)
    outfile.write(f"  Non-zero: {total_nz} bytes in {len(nz_regions)} region(s)\n")

    if total_nz == 0:
        outfile.write(f"  [EMPTY] Deep region is all zeros\n")
        return 0

    # Show non-zero regions
    for rs, re_ in nz_regions:
        outfile.write(f"    0x{rs:X} - 0x{re_:X} ({re_-rs} bytes, script+0x{rs-script_start:X})\n")

    # Parse records with slot markers
    records = parse_deep_records(data, deep_start, deep_end)
    outfile.write(f"\n  Parsed records (XX FF 00 00 markers): {len(records)}\n")

    if records:
        outfile.write(f"  {'Offset':>10s}  {'Rel':>6s}  {'MkPos':>5s}  {'XX':>4s}  {'Slot':>4s}  {'Flg':>4s}  "
                      f"{'X':>7s}  {'Y':>7s}  {'Z':>7s}  {'Extra':>10s}  {'Val':>6s}\n")
        outfile.write(f"  {'-'*10}  {'-'*6}  {'-'*5}  {'-'*4}  {'-'*4}  {'-'*4}  "
                      f"{'-'*7}  {'-'*7}  {'-'*7}  {'-'*10}  {'-'*6}\n")

        for r in records:
            outfile.write(f"  0x{r['abs_offset']:08X}  +{r['rel_offset']:04X}  "
                         f"mk{r['marker_pos']:02d}  0x{r['raw_xx']:02X}  "
                         f"{r['slot']:4d}  0x{r['flags']:02X}  "
                         f"{r['x']:7d}  {r['y']:7d}  {r['z']:7d}  "
                         f"0x{r['extra']:08X}  {r['val']:6d}\n")

    # Also do a raw hex dump of the first 512 bytes of non-zero data
    outfile.write(f"\n  Raw hex (first non-zero region, up to 512 bytes):\n")
    if nz_regions:
        dump_start = nz_regions[0][0]
        dump_end = min(dump_start + 512, nz_regions[0][1])
        for i in range(dump_start, dump_end, 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            rel = i - script_start
            outfile.write(f"    0x{i:08X} (+{rel:04X}): {hex_str}  | {ascii_str}\n")

    return len(records)


def main():
    print("=" * 70)
    print("  Trap Damage Research - Phase 1.1: Deep Entity Region Dump")
    print("=" * 70)

    data, src_path = load_blaze_data()
    if data is None:
        return

    zones = load_all_zones()
    print(f"  Loaded {len(zones)} zones from formation JSONs\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Group zones by level
    levels = {}
    for z in zones:
        lvl = z['level']
        if lvl not in levels:
            levels[lvl] = []
        levels[lvl].append(z)

    # Summary output
    summary_path = OUTPUT_DIR / "deep_region_summary.txt"
    detail_path = OUTPUT_DIR / "deep_region_detail.txt"

    total_records = 0
    zone_stats = []

    with open(detail_path, 'w', encoding='cp1252') as detail:
        detail.write("DEEP ENTITY REGION - DETAILED DUMP\n")
        detail.write(f"Source: {src_path}\n")
        detail.write("=" * 80 + "\n\n")

        for level_name in sorted(levels.keys()):
            level_zones = levels[level_name]
            detail.write(f"\n{'='*80}\n")
            detail.write(f"  LEVEL: {level_name} ({len(level_zones)} zones)\n")
            detail.write(f"{'='*80}\n")

            for z in sorted(level_zones, key=lambda x: x['name']):
                detail.write(f"\n--- {z['level']} / {z['name']} ---\n")
                detail.write(f"  Monsters ({z['num_monsters']}): {', '.join(z['monsters'])}\n")
                detail.write(f"  Group offset: 0x{z['group_offset']:X}\n")

                n_records = dump_zone(data, z, detail)
                total_records += n_records

                zone_stats.append({
                    'level': z['level'],
                    'name': z['name'],
                    'num_monsters': z['num_monsters'],
                    'records': n_records,
                    'group_offset': z['group_offset'],
                })

    # Write summary
    with open(summary_path, 'w', encoding='cp1252') as summary:
        summary.write("DEEP ENTITY REGION - SUMMARY\n")
        summary.write(f"Source: {src_path}\n")
        summary.write(f"Total zones: {len(zones)}\n")
        summary.write(f"Total deep records: {total_records}\n")
        summary.write("=" * 80 + "\n\n")

        # Sort by record count (descending) to highlight zones with most data
        zone_stats.sort(key=lambda x: -x['records'])

        summary.write(f"{'Level':<30s}  {'Area':<25s}  {'Mon':>3s}  {'Records':>7s}\n")
        summary.write(f"{'-'*30}  {'-'*25}  {'-'*3}  {'-'*7}\n")

        for zs in zone_stats:
            summary.write(f"{zs['level']:<30s}  {zs['name']:<25s}  {zs['num_monsters']:3d}  {zs['records']:7d}\n")

        # Highlight trap zones
        trap_levels = ['Cavern of Death', 'The Tower', 'Castle of Vamp']
        summary.write(f"\n\n--- TRAP ZONES (known) ---\n")
        for zs in zone_stats:
            if any(tl in zs['level'] for tl in trap_levels):
                summary.write(f"  {zs['level']:<30s}  {zs['name']:<25s}  records={zs['records']}\n")

        summary.write(f"\n--- NON-TRAP ZONES ---\n")
        for zs in zone_stats:
            if not any(tl in zs['level'] for tl in trap_levels):
                summary.write(f"  {zs['level']:<30s}  {zs['name']:<25s}  records={zs['records']}\n")

    print(f"\n  Output:")
    print(f"    Summary: {summary_path}")
    print(f"    Detail:  {detail_path}")
    print(f"\n  Total records across all zones: {total_records}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
