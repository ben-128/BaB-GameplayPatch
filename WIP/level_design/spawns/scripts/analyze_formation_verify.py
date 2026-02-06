#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
VERIFICATION: Formation composition is encoded in byte[8] of template records.

Template records have:
  - coord=(0,0,0) at bytes [12:18]
  - byte[9]=0xFF
  - byte[8] = MONSTER SLOT INDEX (0, 1, 2, or 3)

Each template record represents ONE monster in the formation.
The number of records per group = total monsters in that formation.
The byte[8] value of each record = which monster slot is used.

This script counts formations and prints them as human-readable compositions.
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch")
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

AREAS = [
    {
        "name": "Cavern F1 Area 1",
        "group_offset": 0xF7A97C,
        "num_monsters": 3,
        "slot_names": {0: "Lv20.Goblin", 1: "Goblin-Shaman", 2: "Giant-Bat"},
        "next_group_offset": 0xF7E1A8,
    },
    {
        "name": "Cavern F1 Area 2",
        "group_offset": 0xF7E1A8,
        "num_monsters": 4,
        "slot_names": {0: "Lv20.Goblin", 1: "Goblin-Shaman", 2: "Giant-Bat", 3: "Goblin-Leader"},
        "next_group_offset": 0xF819A0,
    },
    # Add Forest areas for cross-reference
    {
        "name": "Forest Area 1",
        "group_offset": 0xF49A78,
        "num_monsters": 3,
        "slot_names": {0: "Kobold", 1: "Giant-Ant", 2: "Giant-Beetle"},
        "next_group_offset": 0xF4CE24,
    },
]


def main():
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())
    print("Loaded BLAZE.ALL ({} bytes)".format(len(blaze)))
    print()

    for area in AREAS:
        name = area["name"]
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]

        if script_start >= len(blaze) or next_off > len(blaze):
            print("SKIP {} - offset out of range".format(name))
            continue

        print("=" * 80)
        print("  {}".format(name))
        print("  Slots: {}".format(
            ", ".join("{}={}".format(s, n) for s, n in sorted(area["slot_names"].items()))))
        print("=" * 80)
        print()

        # Find all 6-byte FF block positions
        ff6_positions = []
        i = 0
        while i < len(data) - 5:
            if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                ff6_positions.append(i)
                i += 6
            else:
                i += 1

        # Parse 32-byte records (26 data + 6 FF)
        records = []
        for ff_pos in ff6_positions:
            rec_start = ff_pos - 26
            if rec_start < 0:
                continue
            rec = data[rec_start:ff_pos + 6]
            if len(rec) != 32:
                continue
            records.append({
                'start': rec_start,
                'data': rec,
                'byte0': rec[0],
                'byte8': rec[8],
                'byte9': rec[9],
                'coord': (
                    struct.unpack_from('<h', rec, 12)[0],
                    struct.unpack_from('<h', rec, 14)[0],
                    struct.unpack_from('<h', rec, 16)[0],
                ),
                'xx': rec[24],
                'yy': rec[25],
            })

        # Classify records into types:
        # TYPE A: "Spawn point" records - have coordinates, byte[9] != 0xFF
        # TYPE B: "Formation template" records - coord=(0,0,0), byte[9]=0xFF
        # TYPE C: Other

        spawn_records = []
        formation_records = []
        other_records = []

        for rec in records:
            if rec['byte9'] == 0xFF and rec['coord'] == (0, 0, 0):
                formation_records.append(rec)
            elif rec['coord'] != (0, 0, 0) and abs(rec['coord'][0]) < 10000:
                spawn_records.append(rec)
            else:
                other_records.append(rec)

        print("  Record types:")
        print("    Spawn point records (with coordinates): {}".format(len(spawn_records)))
        print("    Formation template records (coord=0, byte9=FF): {}".format(len(formation_records)))
        print("    Other records: {}".format(len(other_records)))
        print()

        # Group formation records into consecutive sequences
        # (they should be in groups separated by 8-byte gaps or spawn records)
        formation_groups = []
        current_group = []

        for i, rec in enumerate(formation_records):
            if current_group:
                prev_end = current_group[-1]['start'] + 32
                gap = rec['start'] - prev_end
                if gap > 32:  # New group if more than 32 bytes gap
                    formation_groups.append(current_group)
                    current_group = []
            current_group.append(rec)

        if current_group:
            formation_groups.append(current_group)

        print("  FORMATION TEMPLATES ({} groups):".format(len(formation_groups)))
        print("  " + "-" * 60)
        print()

        for gidx, group in enumerate(formation_groups):
            # Count monsters per slot
            slot_counts = {}
            for rec in group:
                slot = rec['byte8']
                slot_counts[slot] = slot_counts.get(slot, 0) + 1

            total = len(group)
            abs_start = script_start + group[0]['start']
            abs_end = script_start + group[-1]['start'] + 32

            # Format as "3x Goblin + 2x Bat"
            composition = []
            for slot_idx in sorted(slot_counts.keys()):
                count = slot_counts[slot_idx]
                slot_name = area["slot_names"].get(slot_idx, "???slot{}".format(slot_idx))
                composition.append("{}x {}".format(count, slot_name))

            comp_str = " + ".join(composition) if composition else "(empty)"

            print("  Formation {:2d} (0x{:08X}): {} monsters -> {}".format(
                gidx, abs_start, total, comp_str))

            # Print raw byte[8] values
            byte8_vals = [rec['byte8'] for rec in group]
            print("    byte[8] sequence: [{}]".format(', '.join(str(v) for v in byte8_vals)))

            # Also show the XX values for reference
            xx_vals = [rec['xx'] for rec in group]
            print("    XX values: [{}]".format(', '.join('0x{:02X}'.format(v) for v in xx_vals)))

        print()

        # Also show the spawn point records and their byte[8] values
        print("  SPAWN POINT RECORDS ({} total):".format(len(spawn_records)))
        for idx, rec in enumerate(spawn_records[:10]):
            abs_pos = script_start + rec['start']
            print("    [{:2d}] 0x{:08X}: byte0={} byte8={} coord=({},{},{}) XX=0x{:02X} YY=0x{:02X}".format(
                idx, abs_pos, rec['byte0'], rec['byte8'],
                rec['coord'][0], rec['coord'][1], rec['coord'][2],
                rec['xx'], rec['yy']))
        if len(spawn_records) > 10:
            print("    ... and {} more".format(len(spawn_records) - 10))
        print()
        print()

    # ================================================================
    # SUMMARY: Print a clean formation table
    # ================================================================
    print("=" * 80)
    print("  FORMATION COMPOSITION SUMMARY")
    print("=" * 80)
    print()
    print("  Each formation template group defines one possible enemy encounter.")
    print("  byte[8] of each record = monster slot index.")
    print("  Number of records = total monsters in the encounter.")
    print()

    for area in AREAS:
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]

        if script_start >= len(blaze) or next_off > len(blaze):
            continue

        data = blaze[script_start:next_off]

        # Re-parse (quick)
        ff6_positions = []
        i = 0
        while i < len(data) - 5:
            if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                ff6_positions.append(i)
                i += 6
            else:
                i += 1

        formation_records = []
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
            if rec[9] == 0xFF and coord == (0, 0, 0):
                formation_records.append({
                    'start': rec_start,
                    'byte8': rec[8],
                })

        groups = []
        current = []
        for rec in formation_records:
            if current:
                gap = rec['start'] - (current[-1]['start'] + 32)
                if gap > 32:
                    groups.append(current)
                    current = []
            current.append(rec)
        if current:
            groups.append(current)

        print("  {} -- {} formation templates:".format(area["name"], len(groups)))
        for gidx, group in enumerate(groups):
            slot_counts = {}
            for rec in group:
                s = rec['byte8']
                slot_counts[s] = slot_counts.get(s, 0) + 1
            composition = []
            for s in sorted(slot_counts.keys()):
                c = slot_counts[s]
                n = area["slot_names"].get(s, "?slot{}".format(s))
                composition.append("{}x{}".format(c, n))
            print("    F{:02d}: {} total = {}".format(
                gidx, len(group), " + ".join(composition)))
        print()


if __name__ == '__main__':
    main()
