#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Extract formation templates, direct spawn points, and zone spawns from
BLAZE.ALL for all areas in all levels.

All three types use the same 32-byte record format (26 data + 6 FF terminator):
  - Formation templates: byte9=0xFF, coords=(0,0,0) - encounter composition
  - Direct spawn points: byte9=0x0B, real coords - placed monsters
  - Zone spawns:         byte9=0xFF, real coords - zone placement points

Output: Data/formations/<level_key>/<area_key>.json
"""

import struct
import json
import os
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SPAWN_GROUPS_DIR = PROJECT_ROOT / "WIP" / "level_design" / "spawns" / "data" / "spawn_groups"
OUTPUT_DIR = SCRIPT_DIR

BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"


def area_name_to_key(name):
    """Convert area name to filename-safe key. e.g. 'Floor 1 - Area 2' -> 'floor_1_area_2'"""
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def load_all_spawn_groups():
    """Load all spawn group JSONs, sorted by level then offset."""
    levels = {}
    for fname in sorted(os.listdir(SPAWN_GROUPS_DIR)):
        if not fname.endswith('.json'):
            continue
        with open(SPAWN_GROUPS_DIR / fname, 'r') as f:
            data = json.load(f)
        level_name = data.get('level_name', fname.replace('.json', ''))
        level_key = fname.replace('.json', '')
        groups = []
        for g in data['groups']:
            groups.append({
                'name': g['name'],
                'offset': int(g['offset'], 16),
                'monsters': g['monsters'],
            })
        groups.sort(key=lambda x: x['offset'])
        levels[level_key] = {
            'level_name': level_name,
            'groups': groups,
        }
    return levels


def scan_records(blaze_data, group_offset, num_monsters, scan_end):
    """Scan script area for all valid 32-byte records. Returns categorized lists.

    Returns (formations, spawn_points, zone_spawns) where each is a list of
    raw record dicts ready for grouping.
    """
    script_start = group_offset + num_monsters * 96
    scan_size = scan_end - script_start
    if scan_size <= 0:
        return [], [], []

    data = blaze_data[script_start:scan_end]

    # Find all 6-byte FF blocks (record terminators) in one pass
    ff6_positions = []
    i = 0
    while i < len(data) - 5:
        if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
            ff6_positions.append(i)
            i += 6
        else:
            i += 1

    formations = []
    spawn_points = []
    zone_spawns = []

    for ff_pos in ff6_positions:
        rec_start = ff_pos - 26
        if rec_start < 0:
            continue
        rec = data[rec_start:ff_pos + 6]
        if len(rec) != 32:
            continue

        byte8 = rec[8]
        byte9 = rec[9]
        if byte8 >= num_monsters:
            continue

        coord = (
            struct.unpack_from('<h', rec, 12)[0],
            struct.unpack_from('<h', rec, 14)[0],
            struct.unpack_from('<h', rec, 16)[0],
        )
        has_inner_ff = (rec[4:8] == b'\xff\xff\xff\xff')
        abs_offset = script_start + rec_start

        # Reject false positives from FF-dense data regions:
        # - byte10_11 containing 0xFF (legit records use small values)
        # - any coordinate with |value| > 15000 (outside game world)
        byte10_11 = rec[10:12]
        if 0xFF in byte10_11:
            continue
        if any(abs(c) > 15000 for c in coord):
            continue

        if byte9 == 0xFF and coord == (0, 0, 0):
            # Formation template
            formations.append({
                'abs_offset': abs_offset,
                'byte0': rec[0],
                'byte8': byte8,
                'area_id': rec[24:26],
                'is_group_start': has_inner_ff,
            })
        elif byte9 == 0x0B and coord != (0, 0, 0):
            # Direct spawn point
            spawn_points.append({
                'abs_offset': abs_offset,
                'byte0': rec[0],
                'byte8': byte8,
                'byte10_11': byte10_11,
                'x': coord[0], 'y': coord[1], 'z': coord[2],
                'area_id': rec[24:26],
                'is_group_start': has_inner_ff,
            })
        elif byte9 == 0xFF and coord != (0, 0, 0):
            # Zone spawn (0xFF marker with real coordinates)
            zone_spawns.append({
                'abs_offset': abs_offset,
                'byte0': rec[0],
                'byte8': byte8,
                'byte10_11': byte10_11,
                'x': coord[0], 'y': coord[1], 'z': coord[2],
                'area_id': rec[24:26],
                'is_group_start': has_inner_ff,
            })

    return formations, spawn_points, zone_spawns


def group_records(records):
    """Group records by FFFFFFFF delimiter + contiguity."""
    groups = []
    current = []
    for rec in records:
        if rec['is_group_start'] and current:
            groups.append(current)
            current = []
        elif current:
            prev_offset = current[-1]['abs_offset']
            expected = prev_offset + 32
            if rec['abs_offset'] != expected:
                groups.append(current)
                current = []
        current.append(rec)
    if current:
        groups.append(current)
    return groups


def compute_suffix(blaze_data, formation):
    """Read the 4-byte suffix after a formation's last record."""
    last_rec = formation[-1]
    suffix_offset = last_rec['abs_offset'] + 32
    return blaze_data[suffix_offset:suffix_offset + 4]


def format_formation(formation, slot_names, suffix_bytes):
    """Format a single formation into a readable dict."""
    slot_counts = {}
    for rec in formation:
        s = rec['byte8']
        slot_counts[s] = slot_counts.get(s, 0) + 1

    composition = []
    for s in sorted(slot_counts.keys()):
        count = slot_counts[s]
        name = slot_names.get(s, "?slot{}".format(s))
        composition.append({
            "count": count,
            "slot": s,
            "monster": name,
        })

    return {
        "total": len(formation),
        "composition": composition,
        "slots": [rec['byte8'] for rec in formation],
        "suffix": suffix_bytes.hex(),
        "offset": "0x{:X}".format(formation[0]['abs_offset']),
    }


def format_spawn_point_group(group, slot_names, suffix_bytes):
    """Format a single spawn point group into a readable dict."""
    slot_counts = {}
    for rec in group:
        s = rec['byte8']
        slot_counts[s] = slot_counts.get(s, 0) + 1

    composition = []
    for s in sorted(slot_counts.keys()):
        count = slot_counts[s]
        name = slot_names.get(s, "?slot{}".format(s))
        composition.append({
            "count": count,
            "slot": s,
            "monster": name,
        })

    records = []
    for rec in group:
        records.append({
            "slot": rec['byte8'],
            "x": rec['x'],
            "y": rec['y'],
            "z": rec['z'],
            "byte0": rec['byte0'],
            "byte10_11": rec['byte10_11'].hex(),
            "area_id": rec['area_id'].hex(),
            "offset": "0x{:X}".format(rec['abs_offset']),
        })

    return {
        "total": len(group),
        "composition": composition,
        "records": records,
        "suffix": suffix_bytes.hex(),
        "offset": "0x{:X}".format(group[0]['abs_offset']),
    }


def main():
    print("Loading BLAZE.ALL from {}...".format(BLAZE_ALL))
    blaze_data = BLAZE_ALL.read_bytes()
    print("  Size: {:,} bytes".format(len(blaze_data)))

    levels = load_all_spawn_groups()
    print("  Levels: {}".format(len(levels)))
    total_groups = sum(len(v['groups']) for v in levels.values())
    print("  Total groups: {}".format(total_groups))
    print()

    total_files = 0

    for level_key, level_data in sorted(levels.items()):
        level_name = level_data['level_name']
        groups = level_data['groups']

        # Create level directory
        level_dir = OUTPUT_DIR / level_key
        level_dir.mkdir(exist_ok=True)

        print("Processing: {} ({} areas)".format(level_name, len(groups)))

        for i, group in enumerate(groups):
            offset = group['offset']
            num_monsters = len(group['monsters'])
            slot_names = {j: name for j, name in enumerate(group['monsters'])}

            # Determine scan end: next group offset or +32KB for last group
            if i + 1 < len(groups):
                scan_end = groups[i + 1]['offset']
            else:
                scan_end = offset + num_monsters * 96 + 32768

            f_recs, sp_recs, zs_recs = scan_records(
                blaze_data, offset, num_monsters, scan_end)
            formations = group_records(f_recs)
            sp_groups = group_records(sp_recs)
            zs_groups = group_records(zs_recs)

            # Compute spawn points area metadata
            if sp_groups:
                sp_first = sp_groups[0][0]['abs_offset']
                sp_last_g = sp_groups[-1]
                sp_last_end = sp_last_g[-1]['abs_offset'] + 32
                sp_area_bytes = sp_last_end + 4 - sp_first  # +4 for last suffix
                sp_total_slots = sum(len(g) for g in sp_groups)
            else:
                sp_first = 0
                sp_area_bytes = 0
                sp_total_slots = 0

            # Compute zone spawns area metadata
            if zs_groups:
                zs_first = zs_groups[0][0]['abs_offset']
                zs_last_g = zs_groups[-1]
                zs_last_end = zs_last_g[-1]['abs_offset'] + 32
                zs_area_bytes = zs_last_end + 4 - zs_first
                zs_total_slots = sum(len(g) for g in zs_groups)
            else:
                zs_first = 0
                zs_area_bytes = 0
                zs_total_slots = 0

            # Compute formation area metadata
            if formations:
                first_offset = formations[0][0]['abs_offset']
                last_f = formations[-1]
                last_end = last_f[-1]['abs_offset'] + 32  # end of last record
                formation_area_bytes = last_end + 4 - first_offset  # +4 for last suffix
                total_slots = sum(len(f) for f in formations)
                # Read area_id from first record
                area_id = formations[0][0]['area_id'].hex()
            else:
                first_offset = 0
                formation_area_bytes = 0
                total_slots = 0
                area_id = "0000"

            area_data = {
                "level_name": level_name,
                "name": group['name'],
                "group_offset": "0x{:X}".format(offset),
                "monsters": group['monsters'],
                "formation_area_start": "0x{:X}".format(first_offset) if formations else None,
                "formation_area_bytes": formation_area_bytes,
                "original_total_slots": total_slots,
                "area_id": area_id,
                "formation_count": len(formations),
                "formations": [],
                "_placed_spawns": "--- placed spawns (per-record offsets) ---",
                "spawn_points_area_start": "0x{:X}".format(sp_first) if sp_groups else None,
                "spawn_points_area_bytes": sp_area_bytes,
                "original_total_spawn_slots": sp_total_slots,
                "spawn_point_count": len(sp_groups),
                "spawn_points": [],
                "zone_spawns_area_start": "0x{:X}".format(zs_first) if zs_groups else None,
                "zone_spawns_area_bytes": zs_area_bytes,
                "original_total_zone_spawn_slots": zs_total_slots,
                "zone_spawn_count": len(zs_groups),
                "zone_spawns": [],
            }

            for fidx, formation in enumerate(formations):
                suffix = compute_suffix(blaze_data, formation)
                area_data["formations"].append(
                    format_formation(formation, slot_names, suffix)
                )

            for sp_group in sp_groups:
                suffix = compute_suffix(blaze_data, sp_group)
                area_data["spawn_points"].append(
                    format_spawn_point_group(sp_group, slot_names, suffix)
                )

            for zs_group in zs_groups:
                suffix = compute_suffix(blaze_data, zs_group)
                area_data["zone_spawns"].append(
                    format_spawn_point_group(zs_group, slot_names, suffix)
                )

            # Write area JSON
            area_key = area_name_to_key(group['name'])
            out_path = level_dir / "{}.json".format(area_key)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(area_data, f, indent=2, ensure_ascii=False)
            total_files += 1

            # Print summary
            total_f = len(formations)
            total_sp = len(sp_groups)
            total_zs = len(zs_groups)
            parts_summary = []
            if total_sp > 0:
                parts_summary.append("{} spawn groups ({} slots)".format(
                    total_sp, sp_total_slots))
            if total_zs > 0:
                parts_summary.append("{} zone spawns ({} slots)".format(
                    total_zs, zs_total_slots))
            if total_f > 0:
                parts_summary.append("{} formations ({} slots, {}B)".format(
                    total_f, total_slots, formation_area_bytes))
            if parts_summary:
                print("  {} - {} -> {}/{}".format(
                    group['name'], ", ".join(parts_summary),
                    level_key, out_path.name))
            else:
                print("  {} - (empty) -> {}/{}".format(
                    group['name'], level_key, out_path.name))
            for spidx, sp in enumerate(area_data["spawn_points"]):
                parts = []
                for c in sp["composition"]:
                    parts.append("{}x{}".format(c["count"], c["monster"]))
                print("    SP{:02d}: [{}] {} (suf:{})".format(
                    spidx, sp["total"], " + ".join(parts), sp["suffix"]))
            for zsidx, zs in enumerate(area_data["zone_spawns"]):
                parts = []
                for c in zs["composition"]:
                    parts.append("{}x{}".format(c["count"], c["monster"]))
                print("    ZS{:02d}: [{}] {} (suf:{})".format(
                    zsidx, zs["total"], " + ".join(parts), zs["suffix"]))
            for fidx, f in enumerate(area_data["formations"]):
                parts = []
                for c in f["composition"]:
                    parts.append("{}x{}".format(c["count"], c["monster"]))
                print("    F{:02d}: [{}] {} (suf:{})".format(
                    fidx, f["total"], " + ".join(parts), f["suffix"]))

        print()

    print("Done! {} area JSONs written to {}".format(total_files, OUTPUT_DIR))


if __name__ == '__main__':
    main()
