#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Split formation template records into sub-groups using 4-byte FF delimiters.

The template records are at coord=(0,0,0) with byte[9]=0xFF.
Between formations: a 4-byte FF block + 8 byte gap (total 12 bytes).
Within a formation: records are consecutive (32 bytes apart).

Actually looking at the data more carefully:
  Groups 3-10 from the earlier analysis each had consistent byte[8] values.
  The "group" boundaries were defined by the 8-byte gap between records.

Let me re-examine using the byte[0] field which often starts with 0x02 or 0x00
to see if formations are split by the byte[0] value changing.

Actually the real delimiter is the 4-byte FF at bytes [4:8] of a record!
Records with data[4:8] = FF FF FF FF are group starters.
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
]


def hex_dump_line(data, offset):
    hex_str = ' '.join('{:02X}'.format(b) for b in data)
    return '  {:08X}  {}'.format(offset, hex_str)


def main():
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())
    print("Loaded BLAZE.ALL")
    print()

    for area in AREAS:
        name = area["name"]
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]

        print("=" * 80)
        print("  {}".format(name))
        print("  Slots: {}".format(
            ", ".join("{}={}".format(s, n) for s, n in sorted(area["slot_names"].items()))))
        print("=" * 80)
        print()

        # Find all 6-byte FF blocks
        ff6_positions = []
        i = 0
        while i < len(data) - 5:
            if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                ff6_positions.append(i)
                i += 6
            else:
                i += 1

        # Parse ALL 32-byte records (26 data + 6 FF terminator)
        all_records = []
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

            is_template = (rec[9] == 0xFF and coord == (0, 0, 0))
            has_inner_ff = (rec[4:8] == b'\xff\xff\xff\xff')  # 4-byte FF at bytes 4-7

            all_records.append({
                'start': rec_start,
                'ff_pos': ff_pos,
                'data': rec,
                'byte0': rec[0],
                'byte8': rec[8],
                'byte9': rec[9],
                'coord': coord,
                'is_template': is_template,
                'is_group_start': has_inner_ff,
                'xx': rec[24],
                'yy': rec[25],
            })

        # Filter just template records
        template_records = [r for r in all_records if r['is_template']]

        print("  Total template records: {}".format(len(template_records)))
        print()

        # Print all template records with their raw data
        print("  All template records (32 bytes each):")
        for idx, rec in enumerate(template_records):
            abs_pos = script_start + rec['start']
            hex32 = ' '.join('{:02X}'.format(b) for b in rec['data'])
            is_start = " ** GROUP START **" if rec['is_group_start'] else ""
            slot_name = area["slot_names"].get(rec['byte8'], "?")
            print("  [{:2d}] 0x{:08X}: {}{}".format(idx, abs_pos, hex32, is_start))
            print("       byte[0]={} byte[8]={} ({}) XX=0x{:02X} YY=0x{:02X}".format(
                rec['byte0'], rec['byte8'], slot_name, rec['xx'], rec['yy']))
        print()

        # Now split into sub-groups using the is_group_start flag
        # A record with bytes[4:8]=FFFFFFFF marks the START of a new formation
        formations = []
        current = []
        for rec in template_records:
            if rec['is_group_start'] and current:
                formations.append(current)
                current = []
            current.append(rec)
        if current:
            formations.append(current)

        print("  FORMATIONS (split by inner FF at bytes[4:8]):")
        print("  " + "-" * 60)
        for fidx, formation in enumerate(formations):
            slot_counts = {}
            for rec in formation:
                s = rec['byte8']
                slot_counts[s] = slot_counts.get(s, 0) + 1

            composition = []
            for s in sorted(slot_counts.keys()):
                c = slot_counts[s]
                n = area["slot_names"].get(s, "?slot{}".format(s))
                composition.append("{}x {}".format(c, n))

            comp_str = " + ".join(composition)
            total = len(formation)
            byte8_vals = [rec['byte8'] for rec in formation]

            print("    F{:02d}: {} monsters = {}".format(fidx, total, comp_str))
            print("         byte[8]: [{}]".format(', '.join(str(v) for v in byte8_vals)))

        print()
        print()

    # Final summary
    print("=" * 80)
    print("  CLEAN FORMATION TABLE")
    print("=" * 80)
    print()

    for area in AREAS:
        group_off = area["group_offset"]
        num_m = area["num_monsters"]
        script_start = group_off + num_m * 96
        next_off = area["next_group_offset"]
        data = blaze[script_start:next_off]

        ff6_positions = []
        i = 0
        while i < len(data) - 5:
            if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                ff6_positions.append(i)
                i += 6
            else:
                i += 1

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
            if rec[9] == 0xFF and coord == (0, 0, 0):
                template_records.append({
                    'start': rec_start,
                    'data': rec,
                    'byte8': rec[8],
                    'is_group_start': (rec[4:8] == b'\xff\xff\xff\xff'),
                })

        formations = []
        current = []
        for rec in template_records:
            if rec['is_group_start'] and current:
                formations.append(current)
                current = []
            current.append(rec)
        if current:
            formations.append(current)

        print("  {} ({} formations):".format(area["name"], len(formations)))
        for fidx, formation in enumerate(formations):
            slot_counts = {}
            for rec in formation:
                s = rec['byte8']
                slot_counts[s] = slot_counts.get(s, 0) + 1

            parts = []
            for s in sorted(slot_counts.keys()):
                c = slot_counts[s]
                n = area["slot_names"].get(s, "?{}".format(s))
                parts.append("{}x{}".format(c, n))

            print("    {:2d}. [{}] {}".format(fidx, len(formation), " + ".join(parts)))
        print()


if __name__ == '__main__':
    main()
