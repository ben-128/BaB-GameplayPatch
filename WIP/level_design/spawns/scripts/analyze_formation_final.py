#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
FINAL ANALYSIS: Extract and decode spawn records with their formation data.

Key insight from previous analysis:
- Each spawn record is 32 bytes, ending with FF FF FF FF FF FF (6 bytes)
- So 26 data bytes + 6 FF bytes = 32 bytes per record
- Records come in GROUPS separated by a 4-byte FF block (+ 8-byte footer)
- After the 4-byte FF block: 18 bytes of "group header" data, then the records

Record format (26 data bytes before the 6-byte FF terminator):
  [0]   = slot index that comes AFTER this FF block
  [8-9] = some identifier/opcode
  [12-17] = coordinates (3x int16 LE: X, Z, Y?)
  [24-25] = [XX, YY] right before FF block

The [XX, YY] values: XX could be some encounter/spawn param, YY is often 00-03

Let me focus on the GROUP structure to find formation definitions.
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch")
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

MONSTER_NAMES = {
    48: "Giant-Ant", 49: "Giant-Bat", 50: "Giant-Beetle",
    51: "Giant-Centipede", 52: "Giant-Club", 53: "Giant-Scorpion",
    54: "Giant-Snake", 55: "Giant-Spider", 56: "Giant",
    57: "Goblin-Fly", 58: "Goblin-Leader", 59: "Goblin-Shaman",
    60: "Goblin-Wizard", 61: "Goblin", 79: "Kobold",
    84: "Lv20.Goblin", 86: "Lv30.Goblin", 88: "Lv6.Kobold",
    26: "Big-Viper", 34: "Cave-Bear", 35: "Cave-Scissors",
    77: "Killer-Fish", 107: "Spirit-Ball", 32: "Blue-Slime",
    95: "Ogre", 64: "Green-Giant", 109: "Succubus",
    45: "Gargoyle", 46: "Ghost", 47: "Ghoul",
    75: "Killer-Bear", 76: "Killer-Bee", 65: "Green-Slime",
    66: "Gremlin", 69: "Harpy", 73: "Hippogriff",
    83: "Lizard-Man", 104: "Silver-Wolf", 110: "Trent",
    118: "Wolf", 37: "Crimson-Lizard", 101: "Salamander",
}

AREAS = [
    {
        "name": "Cavern F1 Area 1",
        "group_offset": 0xF7A97C,
        "num_monsters": 3,
        "monsters": {0: (84, "Lv20.Goblin"), 1: (59, "Goblin-Shaman"), 2: (49, "Giant-Bat")},
        "next_group_offset": 0xF7E1A8,
    },
    {
        "name": "Cavern F1 Area 2",
        "group_offset": 0xF7E1A8,
        "num_monsters": 4,
        "monsters": {0: (84, "Lv20.Goblin"), 1: (59, "Goblin-Shaman"), 2: (49, "Giant-Bat"), 3: (58, "Goblin-Leader")},
        "next_group_offset": 0xF819A0,
    },
]


def hex_dump(data, base_offset, per_line=16):
    lines = []
    for i in range(0, len(data), per_line):
        chunk = data[i:i+per_line]
        hex_str = ' '.join('{:02X}'.format(b) for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append('  {:08X}  {:48s}  |{}|'.format(base_offset + i, hex_str, ascii_str))
    return '\n'.join(lines)


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

        print("=" * 80)
        print("  {}: script 0x{:X}-0x{:X}".format(name, script_start, next_off))
        print("  Monsters: {}".format(
            ", ".join("slot{}=0x{:02X}({})".format(s, m[0], m[1])
                      for s, m in sorted(area["monsters"].items()))))
        print("=" * 80)
        print()

        # ============================================================
        # STEP 1: Parse the offset table at the start
        # ============================================================
        # First uint32 is a count (0x3C = 60 for Area 1 means ~15 offsets?)
        # Actually it might be a SIZE (first_offset = data start)
        first_u32 = struct.unpack_from('<I', data, 0)[0]
        print("  Offset table header: 0x{:X} ({})".format(first_u32, first_u32))

        # The offset table seems to be at bytes 0..first_u32
        # Each entry is uint32 LE. Read until 0x00000000
        offsets = []
        for i in range(0, first_u32, 4):
            val = struct.unpack_from('<I', data, i)[0]
            offsets.append((i, val))

        print("  Offset entries (count={}):".format(len(offsets)))
        for idx, (pos, val) in enumerate(offsets):
            abs_target = script_start + val if val < len(data) else val
            print("    [{:2d}] @+0x{:04X}: value=0x{:08X} -> abs 0x{:08X}".format(
                idx, pos, val, abs_target))
        print()

        # ============================================================
        # STEP 2: Parse the region from first_u32 to the first spawn record
        # This should be the "room setup" data
        # ============================================================
        print("  ROOM SETUP REGION (0x{:X} to first spawn records):".format(
            script_start + first_u32))

        # Find the first 6-byte FF block
        first_ff6 = None
        for i in range(first_u32, len(data) - 5):
            if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                first_ff6 = i
                break

        if first_ff6 is not None:
            setup_data = data[first_u32:first_ff6]
            print("  Setup region: +0x{:X} to +0x{:X} ({} bytes)".format(
                first_u32, first_ff6, len(setup_data)))
            print(hex_dump(setup_data, script_start + first_u32))
            print()

        # ============================================================
        # STEP 3: Parse ALL spawn record groups
        # Structure: groups of records, each ending with 6-byte FF
        # Groups separated by sections with different patterns
        # ============================================================
        print("  SPAWN RECORD GROUPS:")
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

        # Group the records: a "group" is a sequence of 32-byte records
        # (26 data + 6 FF). Between groups there's a different structure.
        groups = []
        current_group = []

        for idx in range(len(ff6_positions)):
            ff_pos = ff6_positions[idx]
            rec_data_start = ff_pos - 26
            if rec_data_start < 0:
                continue

            record = data[rec_data_start:ff_pos + 6]
            if len(record) != 32:
                continue

            # Check if this is part of a consecutive group
            # (32 bytes from previous FF end to this FF end)
            if current_group:
                prev_ff_end = current_group[-1]['ff_end']
                gap = rec_data_start - prev_ff_end
                if gap != 0 and gap != 8 and gap != 12:  # Allow small gaps for group separators
                    # This is a new group
                    groups.append(current_group)
                    current_group = []

            current_group.append({
                'data_start': rec_data_start,
                'ff_pos': ff_pos,
                'ff_end': ff_pos + 6,
                'record': record,
                'xx': record[24],
                'yy': record[25],
            })

        if current_group:
            groups.append(current_group)

        print("  Found {} spawn record groups".format(len(groups)))
        print()

        # ============================================================
        # STEP 4: For each group, decode the records and look for
        # formation patterns
        # ============================================================
        for gidx, group in enumerate(groups[:15]):  # Limit output
            first_rec = group[0]
            last_rec = group[-1]
            abs_start = script_start + first_rec['data_start']
            abs_end = script_start + last_rec['ff_end']

            print("  GROUP {:2d}: {} records, 0x{:08X}-0x{:08X}".format(
                gidx, len(group), abs_start, abs_end))

            # Decode each record in the group
            for ridx, rec_info in enumerate(group):
                rec = rec_info['record']
                abs_pos = script_start + rec_info['data_start']

                # Decode the 26 data bytes
                slot_after_ff = rec[0]  # byte after previous FF block
                b1 = rec[1]
                b2_3 = struct.unpack_from('<H', rec, 2)[0]
                b4_7 = struct.unpack_from('<I', rec, 4)[0]

                # bytes 8-11: some kind of opcode/params
                byte8 = rec[8]
                byte9 = rec[9]
                byte10 = rec[10]
                byte11 = rec[11]

                # bytes 12-17: 3x int16 LE (coordinates)
                x = struct.unpack_from('<h', rec, 12)[0]
                y = struct.unpack_from('<h', rec, 14)[0]
                z = struct.unpack_from('<h', rec, 16)[0]

                # bytes 18-23: 3x int16 LE or other data
                p1 = struct.unpack_from('<h', rec, 18)[0]
                p2 = struct.unpack_from('<h', rec, 20)[0]
                p3 = struct.unpack_from('<h', rec, 22)[0]

                # bytes 24-25: XX and YY (right before FF block)
                xx = rec[24]
                yy = rec[25]

                # Check if any byte matches a monster ID from this area
                monster_match = ""
                for s, (mid, mname) in area["monsters"].items():
                    if xx == mid:
                        monster_match = " <<SLOT{}={}>>".format(s, mname)

                # Display compact format
                hex_24 = ' '.join('{:02X}'.format(b) for b in rec[:26])
                print("    [{:2d}] 0x{:08X}: {} | {:02X} {:02X} FFFFFFFFFFFF".format(
                    ridx, abs_pos, hex_24, xx, yy))

                # Show decoded fields for first few records per group
                if ridx < 6 or monster_match:
                    print("         slot={:d} [8:11]={:02X},{:02X},{:02X},{:02X} coord=({},{},{}) [{:02X},{:02X}]{}".format(
                        slot_after_ff, byte8, byte9, byte10, byte11,
                        x, y, z, xx, yy, monster_match))

            # Analyze the group's XX values
            xx_vals = [r['xx'] for r in group]
            yy_vals = [r['yy'] for r in group]

            # Check if XX values correspond to slot indices
            slot_count = [0] * num_m
            for xx in xx_vals:
                for s, (mid, mname) in area["monsters"].items():
                    if xx == mid:
                        slot_count[s] += 1

            if any(c > 0 for c in slot_count):
                print("    ** Monster slot hits: {}".format(
                    ", ".join("slot{}({})={}".format(s, area["monsters"][s][1], c)
                              for s, c in enumerate(slot_count) if c > 0)))

            # Summarize YY values
            yy_summary = {}
            for yy in yy_vals:
                yy_summary[yy] = yy_summary.get(yy, 0) + 1
            print("    YY values: {}".format(
                ", ".join("0x{:02X}:{}x".format(k, v) for k, v in sorted(yy_summary.items()))))

            print()

        # ============================================================
        # STEP 5: Focus on the TRANSITION between initial spawn points
        # and encounter spawn records. The initial 4 records (group 0)
        # define fixed spawn points. What comes after?
        # ============================================================
        print()
        print("  --- TRANSITION ANALYSIS ---")

        if len(groups) >= 2:
            # Show the data between group 0 and group 1
            g0_end = groups[0][-1]['ff_end']
            g1_start = groups[1][0]['data_start']
            between = data[g0_end:g1_start]

            print("  Between group 0 (end 0x{:X}) and group 1 (start 0x{:X}): {} bytes".format(
                script_start + g0_end, script_start + g1_start, len(between)))
            if len(between) > 0:
                print(hex_dump(between, script_start + g0_end))
            print()

        # ============================================================
        # STEP 6: Extract spawn encounter blocks with monster IDs
        # Look at the 4-FF-block delimited sections that contain
        # actual monster IDs
        # ============================================================
        print()
        print("  --- ENCOUNTER BLOCKS WITH MONSTER IDs ---")
        print()

        # Find all 4-byte FF blocks (exactly 4, not 5 or 6)
        ff4_positions = []
        i = 0
        while i < len(data) - 3:
            if (data[i:i+4] == b'\xff\xff\xff\xff' and
                (i + 4 >= len(data) or data[i+4] != 0xFF) and
                (i == 0 or data[i-1] != 0xFF)):
                ff4_positions.append(i)
            i += 1

        print("  4-byte FF blocks: {}".format(len(ff4_positions)))

        # Each 4-FF block may start an encounter block
        # Format seems to be: FF FF FF FF [18 bytes header] [monster_id byte] [yy] FF FF FF FF FF FF
        for idx, ff_pos in enumerate(ff4_positions):
            block_start = ff_pos + 4
            if block_start + 24 > len(data):
                continue

            block = data[block_start:block_start + 24]

            # Check for monster IDs
            monster_hits = []
            for j in range(len(block)):
                for s, (mid, mname) in area["monsters"].items():
                    if block[j] == mid:
                        monster_hits.append((j, s, mid, mname))

            abs_pos = script_start + ff_pos
            if monster_hits:
                print("  Block at 0x{:08X}:".format(abs_pos))
                ctx_end = min(len(data), ff_pos + 36)
                print(hex_dump(data[ff_pos:ctx_end], abs_pos))
                for j, s, mid, mname in monster_hits:
                    next_byte = block[j+1] if j+1 < len(block) else None
                    prev_bytes = ' '.join('{:02X}'.format(block[k]) for k in range(max(0,j-4), j))
                    print("    byte[{:d}] = 0x{:02X} = slot{}({})  prev=[{}] next=0x{:02X}".format(
                        j + 4, mid, s, mname, prev_bytes,
                        next_byte if next_byte is not None else 0))
                print()

        # ============================================================
        # STEP 7: THE KEY QUESTION - Count spawn records per group
        # and per monster slot to see if this correlates with
        # in-game formation composition
        # ============================================================
        print()
        print("  --- FORMATION COMPOSITION HYPOTHESIS ---")
        print()
        print("  Hypothesis: The number of spawn records with slot index S")
        print("  in each group determines how many of monster S appear in")
        print("  that encounter formation.")
        print()

        # For each group, count how many records have each slot index
        # The "slot index" might be encoded in the byte AFTER the FF block
        # (byte 0 of the next record), or in the YY field
        for gidx, group in enumerate(groups[:15]):
            # Count by first byte (slot_after_ff = byte[0] of record)
            slot_counts_byte0 = {}
            for rec_info in group:
                b0 = rec_info['record'][0]
                slot_counts_byte0[b0] = slot_counts_byte0.get(b0, 0) + 1

            # Count by YY field
            yy_counts = {}
            for rec_info in group:
                yy = rec_info['yy']
                yy_counts[yy] = yy_counts.get(yy, 0) + 1

            # Count by XX field matching monster IDs
            xx_monster_counts = {}
            for rec_info in group:
                xx = rec_info['xx']
                for s, (mid, mname) in area["monsters"].items():
                    if xx == mid:
                        xx_monster_counts[s] = xx_monster_counts.get(s, 0) + 1

            print("  Group {:2d} ({} records):".format(gidx, len(group)))
            print("    byte[0] counts: {}".format(
                ", ".join("{}:{}x".format(k, v) for k, v in sorted(slot_counts_byte0.items()))))
            print("    YY counts: {}".format(
                ", ".join("0x{:02X}:{}x".format(k, v) for k, v in sorted(yy_counts.items()))))
            if xx_monster_counts:
                print("    XX monster matches: {}".format(
                    ", ".join("slot{}({}):{}x".format(s, area["monsters"][s][1], c)
                              for s, c in sorted(xx_monster_counts.items()))))
            print()

        print()


if __name__ == '__main__':
    main()
