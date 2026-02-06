#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Extract formation templates from BLAZE.ALL for all areas in all levels.

Formation templates are 32-byte records in the script area (after the 96-byte
monster stat entries). They define the composition of each encounter:
  - byte[8] = monster slot index (0, 1, 2, ... referencing the spawn_group order)
  - byte[9] = 0xFF (template marker)
  - bytes[12:18] = coordinates (always 0,0,0 for templates)
  - bytes[4:8] = FF FF FF FF marks the START of a new formation group

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


def extract_formations(blaze_data, group_offset, num_monsters, scan_end):
    """Extract formation template records from the script area."""
    script_start = group_offset + num_monsters * 96
    scan_size = scan_end - script_start
    if scan_size <= 0:
        return []

    data = blaze_data[script_start:scan_end]

    # Find all 6-byte FF blocks (record terminators)
    ff6_positions = []
    i = 0
    while i < len(data) - 5:
        if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
            ff6_positions.append(i)
            i += 6
        else:
            i += 1

    # Parse 32-byte records (26 data bytes + 6 FF terminator)
    template_records = []
    for ff_pos in ff6_positions:
        rec_start = ff_pos - 26
        if rec_start < 0:
            continue
        rec = data[rec_start:ff_pos + 6]
        if len(rec) != 32:
            continue

        coord = (
            struct.unpack_from('<h', rec, 12)[0],
            struct.unpack_from('<h', rec, 14)[0],
            struct.unpack_from('<h', rec, 16)[0],
        )

        # Template records: byte[9]=0xFF, coords=0, and byte[8] must be
        # a valid slot index (not 0xFF which is a false positive)
        is_template = (rec[9] == 0xFF and coord == (0, 0, 0)
                       and rec[8] < num_monsters)
        if not is_template:
            continue

        has_inner_ff = (rec[4:8] == b'\xff\xff\xff\xff')

        template_records.append({
            'abs_offset': script_start + rec_start,
            'byte0': rec[0],
            'byte8': rec[8],
            'is_group_start': has_inner_ff,
        })

    # Split into formations by group-start delimiter
    # Also enforce contiguity: within a formation, each record must be
    # exactly 32 bytes after the previous one
    formations = []
    current = []
    for rec in template_records:
        if rec['is_group_start'] and current:
            formations.append(current)
            current = []
        elif current:
            prev_offset = current[-1]['abs_offset']
            expected = prev_offset + 32
            if rec['abs_offset'] != expected:
                # Non-contiguous record - start new formation
                formations.append(current)
                current = []
        current.append(rec)
    if current:
        formations.append(current)

    return formations


def format_formation(formation, slot_names):
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
        "offset": "0x{:X}".format(formation[0]['abs_offset']),
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

            formations = extract_formations(blaze_data, offset, num_monsters, scan_end)

            area_data = {
                "level_name": level_name,
                "name": group['name'],
                "group_offset": "0x{:X}".format(offset),
                "monsters": group['monsters'],
                "formation_count": len(formations),
                "formations": [],
            }

            for fidx, formation in enumerate(formations):
                area_data["formations"].append(
                    format_formation(formation, slot_names)
                )

            # Write area JSON
            area_key = area_name_to_key(group['name'])
            out_path = level_dir / "{}.json".format(area_key)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(area_data, f, indent=2, ensure_ascii=False)
            total_files += 1

            # Print summary
            total_f = len(formations)
            print("  {} - {} formations -> {}/{}".format(
                group['name'], total_f, level_key, out_path.name))
            for fidx, f in enumerate(area_data["formations"]):
                parts = []
                for c in f["composition"]:
                    parts.append("{}x{}".format(c["count"], c["monster"]))
                print("    F{:02d}: [{}] {}".format(fidx, f["total"], " + ".join(parts)))

        print()

    print("Done! {} area JSONs written to {}".format(total_files, OUTPUT_DIR))


if __name__ == '__main__':
    main()
