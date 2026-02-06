#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
DEEP ANALYSIS: Focused on the 32-byte spawn records and spawn command patterns.

Key findings from initial scan:
1. Script area starts with an OFFSET TABLE (uint32 LE values)
2. Then ~32-byte records with pattern: [slot_idx 00 00 00 00 00 00 00] [params] [coords?] [FF FF FF FF FF FF]
3. After the 32-byte records: spawn commands with [monsterID byte] [XX] [FF FF FF FF FF FF]
4. The monsterID byte + next byte might be the formation entry

This script focuses on:
A. Decoding the 32-byte records completely
B. Finding ALL instances of [byte] [byte] FF FF FF FF FF FF pattern
C. Checking if the byte before FF...FF is always a monster slot/ID
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


def hex_line(data, base_offset, length=16):
    hex_str = ' '.join('{:02X}'.format(b) for b in data[:length])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:length])
    return '  {:08X}  {:48s}  |{}|'.format(base_offset, hex_str, ascii_str)


def hex_dump(data, base_offset, per_line=16):
    lines = []
    for i in range(0, len(data), per_line):
        chunk = data[i:i+per_line]
        lines.append(hex_line(chunk, base_offset + i, per_line))
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
        script_size = next_off - script_start

        print("=" * 80)
        print("  {}: script 0x{:X}-0x{:X} ({} bytes)".format(
            name, script_start, next_off, script_size))
        print("  Monsters: {}".format(
            ", ".join("slot{}=0x{:02X}({})".format(s, m[0], m[1])
                      for s, m in sorted(area["monsters"].items()))))
        print("=" * 80)
        print()

        # ==============================================================
        # PART A: Decode the offset table at the start
        # ==============================================================
        print("--- A. OFFSET TABLE ---")
        # First uint32 seems to be a count or size
        first_u32 = struct.unpack_from('<I', data, 0)[0]
        print("  First uint32: 0x{:X} ({})".format(first_u32, first_u32))

        # Read offsets until we hit 0x00000000
        offsets = []
        for i in range(0, min(256, len(data)), 4):
            val = struct.unpack_from('<I', data, i)[0]
            offsets.append(val)
            if val == 0 and i > 0:
                break

        print("  Offset table ({} entries):".format(len(offsets)))
        for idx, off in enumerate(offsets):
            if off == 0 and idx > 0:
                print("    [{}] 0x{:08X} (terminator)".format(idx, off))
                break
            print("    [{}] 0x{:08X} ({})".format(idx, off, off))
        print()

        # ==============================================================
        # PART B: Find all [XX YY] FF FF FF FF FF FF patterns
        # This is the key spawn record pattern
        # ==============================================================
        print("--- B. [XX YY] FF FF FF FF FF FF pattern search ---")
        print()

        ff6_hits = []
        for i in range(len(data) - 7):
            if data[i+2:i+8] == b'\xff\xff\xff\xff\xff\xff':
                # Found 6 FF bytes at i+2
                xx = data[i]
                yy = data[i + 1]
                ff6_hits.append((i, xx, yy))

        print("  Found {} instances of [XX YY] FF FF FF FF FF FF".format(len(ff6_hits)))
        print()

        # Print each with context
        for idx, (pos, xx, yy) in enumerate(ff6_hits):
            abs_pos = script_start + pos
            # Get 8 bytes before and 16 bytes after the pattern
            ctx_before_start = max(0, pos - 24)
            ctx_after_end = min(len(data), pos + 24)
            ctx = data[ctx_before_start:ctx_after_end]
            ctx_abs = script_start + ctx_before_start

            # Check if xx is a monster ID
            monster_name = MONSTER_NAMES.get(xx, "")
            slot_name = ""
            for s, (mid, mname) in area["monsters"].items():
                if mid == xx:
                    slot_name = "=SLOT{}({})".format(s, mname)

            # Check what byte is at pos-1 (the byte before XX)
            byte_before = data[pos - 1] if pos > 0 else None
            # Check byte after the FF block
            byte_after_ff = data[pos + 8] if pos + 8 < len(data) else None

            print("  #{:3d} at 0x{:08X}: XX=0x{:02X}({:3d}) YY=0x{:02X}({:3d}) {}{}".format(
                idx, abs_pos, xx, xx, yy, yy,
                slot_name,
                " [{}]".format(monster_name) if monster_name and not slot_name else ""))

            # Only print full context for the first 40 and any with monster IDs
            if idx < 40 or slot_name or monster_name:
                print(hex_dump(ctx, ctx_abs))
                if byte_before is not None:
                    print("    byte[-1]=0x{:02X}  byte_after_ff={}".format(
                        byte_before,
                        "0x{:02X}".format(byte_after_ff) if byte_after_ff is not None else "N/A"))
                print()

        # Analyze XX values
        print()
        print("  XX value distribution:")
        xx_counts = {}
        for pos, xx, yy in ff6_hits:
            xx_counts[xx] = xx_counts.get(xx, 0) + 1
        for xx_val, count in sorted(xx_counts.items()):
            monster = MONSTER_NAMES.get(xx_val, "")
            slot = ""
            for s, (mid, mname) in area["monsters"].items():
                if mid == xx_val:
                    slot = " <<SLOT{}>>".format(s)
            print("    0x{:02X} ({:3d}): {:3d} times  {}{}".format(
                xx_val, xx_val, count, monster, slot))

        # Analyze YY values
        print()
        print("  YY value distribution:")
        yy_counts = {}
        for pos, xx, yy in ff6_hits:
            yy_counts[yy] = yy_counts.get(yy, 0) + 1
        for yy_val, count in sorted(yy_counts.items()):
            print("    0x{:02X} ({:3d}): {:3d} times".format(yy_val, yy_val, count))

        # ==============================================================
        # PART C: Look specifically at the 32-byte records (stride=32 from offset ~0xA6)
        # These are the initial spawn point records
        # ==============================================================
        print()
        print("--- C. 32-BYTE SPAWN POINT RECORDS ---")

        # Find the first FFFFFF block
        first_ff = None
        for i in range(len(data) - 5):
            if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                first_ff = i
                break

        if first_ff is not None:
            # The record starts 6 bytes before (at first_ff - 26 or the start is 8 bytes before FF)
            # Looking at the data: the FF block is at relative 0xA6 (after 26 bytes of record data)
            # So records start at 0xA6 - 26 = 0x8C... but let's check
            # Actually the pattern is: record starts, then 26 bytes of data, then 6 FF bytes = 32 bytes
            record_start = first_ff + 6  # after the first FF block
            # But wait - let me re-examine. The FF block is the TERMINATOR of a record.
            # Record 0 starts at first_ff - 26 bytes? No...
            # Looking at the data again:
            # 00F7AB3C  00 00 00 00 42 02 FF FF  FF FF FF FF  <- this is the end of record 0
            # 00F7AB48  00 00 00 00 00 00 00 00  01 00 11 00 6E FD 04 FC 83 F0 00 00 00 00 00 00 4C 00 FF FF FF FF FF FF
            # That's 32 bytes from 00F7AB48 to right before the next record at 00F7AB68

            # Let me find all 6-byte FF blocks and compute record boundaries
            ff6_positions = []
            i = 0
            while i < len(data) - 5:
                if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
                    ff6_positions.append(i)
                    i += 6  # skip past this FF block
                else:
                    i += 1

            print("  Found {} 6-byte FF blocks".format(len(ff6_positions)))
            print()

            # The pattern seems to be: each 32-byte record ENDS with FF FF FF FF FF FF
            # So a record = 26 data bytes + 6 FF bytes = 32 bytes
            # Let me verify by looking at the spacing between FF blocks
            if len(ff6_positions) >= 2:
                gaps = [ff6_positions[i+1] - ff6_positions[i] for i in range(min(30, len(ff6_positions) - 1))]
                print("  First 30 gaps between 6-byte FF blocks: {}".format(gaps))
                print()

            # Decode each record (26 data bytes before each 6-FF block, or 32 bytes ending with FF)
            print("  Decoding spawn point records:")
            print()

            # The first record ends at ff6_positions[0] + 6
            # So it starts at ff6_positions[0] + 6 - 32 = ff6_positions[0] - 26
            for idx in range(min(20, len(ff6_positions))):
                ff_pos = ff6_positions[idx]
                rec_end = ff_pos + 6
                rec_start = ff_pos - 26  # 26 data bytes before FF

                if rec_start < 0:
                    continue

                record = data[rec_start:rec_end]
                abs_start = script_start + rec_start

                if len(record) != 32:
                    continue

                # Decode fields
                # Based on the pattern observed:
                # Bytes 0-3: slot index? (byte 0 = slot, bytes 1-3 = 0)
                # Bytes 4-7: flags/padding (often 0)
                # Bytes 8-9: some param (varies)
                # Bytes 10-11: sub-param
                # Bytes 12-17: 3 int16 LE values (coordinates? X, Y, Z?)
                # Bytes 18-19: another param
                # Bytes 20-21: padding?
                # Bytes 22-25: some value
                # Bytes 26-31: FF FF FF FF FF FF

                slot = record[0]
                flags = struct.unpack_from('<I', record, 0)[0]
                param_a = struct.unpack_from('<H', record, 4)[0]
                param_b = struct.unpack_from('<H', record, 6)[0]

                byte8 = record[8]
                byte9 = record[9]
                byte10 = record[10]
                byte11 = record[11]

                coord_x = struct.unpack_from('<h', record, 12)[0]
                coord_y = struct.unpack_from('<h', record, 14)[0]
                coord_z = struct.unpack_from('<h', record, 16)[0]

                param_post = struct.unpack_from('<H', record, 18)[0]
                param_post2 = struct.unpack_from('<H', record, 20)[0]
                param_post3 = struct.unpack_from('<H', record, 22)[0]
                last_xx = record[24]
                last_yy = record[25]

                # Check if last_xx is a monster ID
                monster = MONSTER_NAMES.get(last_xx, "")
                slot_info = ""
                for s, (mid, mname) in area["monsters"].items():
                    if mid == last_xx:
                        slot_info = " <<SLOT{}={}>>".format(s, mname)

                print("  Record #{:2d} at 0x{:08X}:".format(idx, abs_start))
                print(hex_dump(record, abs_start))
                print("    slot/idx=0x{:02X}  [8:9]=0x{:02X},0x{:02X}  [10:11]=0x{:02X},0x{:02X}".format(
                    slot, byte8, byte9, byte10, byte11))
                print("    coord?=({},{},{})  post=0x{:04X}  post2=0x{:04X}".format(
                    coord_x, coord_y, coord_z, param_post, param_post2))
                print("    XX=0x{:02X} YY=0x{:02X} {}{}".format(
                    last_xx, last_yy, monster, slot_info))
                print()

        # ==============================================================
        # PART D: Look for the [monsterID] [small_byte] pattern
        # specifically in spawn commands (not in text or offset tables)
        # ==============================================================
        print()
        print("--- D. SPAWN COMMAND RECORDS (monster_ID in spawn context) ---")
        print()

        # The confirmed pattern from Area 1 hit at 0xF7AECC:
        #   00 00 00 00 3B 02 FF FF FF FF FF FF
        # This is at relative position right after a 4-byte FF block

        # And from Area 2 at 0xF7E3FC:
        #   00 0A 00 00 3B 01 FF FF FF FF FF FF

        # Look for 4-byte FF blocks (not 6-byte) that precede spawn commands
        print("  Looking for 4-byte FF blocks followed by spawn data:")
        ff4_positions = []
        i = 0
        while i < len(data) - 3:
            if (data[i:i+4] == b'\xff\xff\xff\xff' and
                (i + 4 >= len(data) or data[i+4] != 0xFF) and
                (i == 0 or data[i-1] != 0xFF)):
                ff4_positions.append(i)
            i += 1

        print("  Found {} 4-byte FF blocks".format(len(ff4_positions)))

        # For each 4-byte FF block, check if the data after it contains a monster ID
        for idx, ff_pos in enumerate(ff4_positions[:30]):
            after_start = ff_pos + 4
            if after_start + 24 > len(data):
                continue
            after_data = data[after_start:after_start + 24]

            # Check for monster IDs in the spawn command
            has_monster = False
            for j, b in enumerate(after_data[:8]):
                for s, (mid, mname) in area["monsters"].items():
                    if b == mid:
                        has_monster = True

            abs_ff = script_start + ff_pos
            abs_after = script_start + after_start

            if has_monster or idx < 10:
                label = " ** HAS MONSTER ID **" if has_monster else ""
                print("  4-FF at 0x{:08X}, data after:{}".format(abs_ff, label))
                print(hex_dump(data[ff_pos:min(ff_pos + 32, len(data))], abs_ff))

                # Decode the spawn command
                # Pattern: [opcode_bytes] [monster_id] [count?] [FF FF FF FF FF FF]
                for j in range(min(20, len(after_data))):
                    b = after_data[j]
                    for s, (mid, mname) in area["monsters"].items():
                        if b == mid:
                            next_b = after_data[j+1] if j+1 < len(after_data) else None
                            print("    >> byte[{}]=0x{:02X}={} next=0x{:02X}".format(
                                j, b, mname,
                                next_b if next_b is not None else 0))
                print()

        # ==============================================================
        # PART E: Focused extraction of the spawn records in the initial
        # section (before text begins)
        # ==============================================================
        print()
        print("--- E. ALL SPAWN RECORDS IN INITIAL DATA SECTION ---")
        print()

        # Find where text begins (first ASCII run >= 10 bytes)
        text_start = None
        run = 0
        for i in range(len(data)):
            if 32 <= data[i] < 127:
                run += 1
                if run >= 10:
                    text_start = i - run + 1
                    break
            else:
                run = 0

        data_section_end = text_start if text_start else len(data)
        print("  Data section: 0x{:X} to 0x{:X} ({} bytes)".format(
            script_start, script_start + data_section_end, data_section_end))
        if text_start:
            snippet = data[text_start:min(text_start + 40, len(data))]
            text_preview = ''.join(chr(b) if 32 <= b < 127 else '.' for b in snippet)
            print("  First text at 0x{:X}: \"{}\"".format(
                script_start + text_start, text_preview[:40]))
        print()

        # Print complete hex dump of the data section (first 2KB)
        print("  Full data section dump (first 2048 bytes):")
        print(hex_dump(data[:min(data_section_end, 2048)], script_start))
        print()

        print()
        print()


if __name__ == '__main__':
    main()
