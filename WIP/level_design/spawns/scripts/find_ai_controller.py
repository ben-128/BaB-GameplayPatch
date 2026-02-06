#!/usr/bin/env python3
"""
Find what controls AI/behavior per monster slot.

Confirmed so far:
  - L (flag 0x00) + anim bytes = 3D model + animations
  - R (flag 0x40) = ??? (no visible effect)
  - 8-byte model_ref = VRAM texture offset
  - Type-7 index = texture + anim type
  - 96-byte entries = name + stats
  - ??? = AI / behavior / spells  <-- WHAT WE'RE LOOKING FOR

AI stayed with the slot when L was swapped, so it's either:
  A) In the 96-byte entries (which weren't swapped)
  B) In the spawn commands / script area (positional)
  C) Derived from some other per-slot structure

This script dumps ALL per-slot data for comparison.
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

STAT_NAMES = {
    0: 'exp', 1: 'level', 2: 'hp', 3: 'magic', 4: 'randomness',
    5: 'collider_type', 6: 'death_fx_size', 7: 'hit_fx_id',
    8: 'collider_size', 9: 'drop_rate', 10: 'creature_type',
    11: 'armor_type', 12: 'elem_fire_ice', 13: 'elem_poison_air',
    14: 'elem_light_night', 15: 'elem_divine_malefic',
    16: 'dmg', 17: 'armor',
}

# Areas to compare
AREAS = [
    {
        'name': "Cavern F1 Area1",
        'group_offset': 0xF7A97C,
        'section_start': 0xF7A904,  # start of pre-group section
        'num': 3,
        'monsters': ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
    },
    {
        'name': "Cavern F1 Area2",
        'group_offset': 0xF7E1A8,
        'num': 4,
        'monsters': ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "Goblin-Leader"],
    },
    {
        'name': "Cavern F3 Area1",
        'group_offset': 0xF86198,
        'num': 4,
        'monsters': ["Giant-Scorpion", "Giant-Bat", "Big-Viper", "Giant-Spider"],
    },
]


def find_section_start(data, group_offset, num):
    """Walk backwards from group_offset to find the section start.

    Structure (bottom-up from group_offset):
      [assignment entries]  num * 8 bytes
      [extra offsets?]      variable (Forest only)
      [offset table]        (num+1) * 4 bytes (num uint32 + zero terminator)
      [zero terminator]     8 bytes
      [8-byte records]      num * 8 bytes
      [animation table]     variable
      [header: 00000000 04000000]  8 bytes
      [zero padding]        variable
    """
    # Assignment entries: num * 8 bytes before group
    assign_start = group_offset - num * 8

    # Offset table: before assignment entries
    # Read backwards to find the offset table
    pos = assign_start - 4
    # First should be zero terminator of offset table
    term = struct.unpack_from('<I', data, pos)[0]
    if term != 0:
        # Might be Forest-style extra offsets, skip them
        while pos > group_offset - 256 and struct.unpack_from('<I', data, pos)[0] != 0:
            pos -= 4

    # Now read offset values backwards
    pos -= 4  # skip zero terminator
    offsets = []
    while pos > group_offset - 512:
        val = struct.unpack_from('<I', data, pos)[0]
        if val == 0:
            break
        offsets.insert(0, val)
        pos -= 4

    # Zero terminator of 8-byte records
    pos -= 4  # skip the zero we just found
    # Check for 8-byte zero terminator
    check = data[pos-3:pos+1]
    if check == b'\x00\x00\x00\x00':
        pos -= 4

    # 8-byte records: num records
    records_end = pos + 4  # just after zero terminator
    records_start = records_end - num * 8

    # Animation table: variable, ends at records_start
    # Walk backwards to find header [00000000 04000000]
    search_pos = records_start - 1
    while search_pos > group_offset - 1024:
        if data[search_pos-7:search_pos+1] == b'\x04\x00\x00\x00\x00\x00\x00\x00':
            return search_pos - 7
        search_pos -= 1

    return records_start - 64  # fallback


def dump_area(data, area):
    name = area['name']
    group_off = area['group_offset']
    num = area['num']
    monsters = area['monsters']

    section_start = area.get('section_start')
    if not section_start:
        section_start = find_section_start(data, group_off, num)

    print("=" * 95)
    print(f"  {name}")
    print(f"  Group offset: 0x{group_off:X} | Section start: ~0x{section_start:X} | {num} monsters")
    print("=" * 95)

    # ---------------------------------------------------------------
    # 1. PRE-GROUP STRUCTURES (bottom-up from group_offset)
    # ---------------------------------------------------------------

    # Assignment entries (L/R pairs)
    assign_base = group_off - num * 8
    print(f"\n  [1] ASSIGNMENT ENTRIES (0x{assign_base:X})")
    for i in range(num):
        off = assign_base + i * 8
        ai_entry = data[off:off+4]
        mod_entry = data[off+4:off+8]
        print(f"      Slot {i} ({monsters[i]:20s}): "
              f"L=[{ai_entry[0]:02X} {ai_entry[1]:02X} {ai_entry[2]:02X} {ai_entry[3]:02X}] L_val={ai_entry[1]:2d} | "
              f"R=[{mod_entry[0]:02X} {mod_entry[1]:02X} {mod_entry[2]:02X} {mod_entry[3]:02X}] R_val={mod_entry[1]:2d}")

    # Offset table (before assignment entries)
    # Scan backwards from assign_base
    print(f"\n  [2] OFFSET TABLE (before assignments)")
    pos = assign_base - 4
    # Find zero terminator
    while pos > group_off - 256:
        val = struct.unpack_from('<I', data, pos)[0]
        if val == 0:
            break
        pos -= 4

    off_table_end = pos  # zero terminator position
    # Read offsets backwards
    off_table = []
    p = off_table_end - 4
    while p > group_off - 512:
        val = struct.unpack_from('<I', data, p)[0]
        if val == 0:
            break
        off_table.insert(0, (p, val))
        p -= 4

    for addr, val in off_table:
        print(f"      0x{addr:08X}: 0x{val:08X} ({val})")
    print(f"      0x{off_table_end:08X}: 0x00000000 (terminator)")

    # 8-byte records
    # They end with an 8-byte zero terminator, then offset table starts
    records_end_addr = off_table[0][0] if off_table else off_table_end
    # Walk back past zero terminator
    zero_term_addr = records_end_addr - 4
    # Check for 8-byte zero terminator
    if data[zero_term_addr-4:zero_term_addr] == b'\x00\x00\x00\x00':
        zero_term_addr -= 4

    records_start_addr = zero_term_addr - num * 8

    print(f"\n  [3] 8-BYTE RECORDS (0x{records_start_addr:X})")
    for i in range(num):
        off = records_start_addr + i * 8
        rec = data[off:off+8]
        anim_off = struct.unpack_from('<I', rec, 0)[0]
        texref = struct.unpack_from('<I', rec, 4)[0]
        print(f"      Slot {i} ({monsters[i]:20s}): "
              f"anim_off=0x{anim_off:04X} texref=0x{texref:08X} | raw=[{rec.hex()}]")

    # Animation table
    anim_table_end = records_start_addr
    # The animation table starts after the [04 00 00 00] [00 00 00 00] header
    # Search backwards for this header
    header_pos = None
    for p in range(anim_table_end - 4, max(anim_table_end - 128, 0), -1):
        if data[p:p+8] == b'\x04\x00\x00\x00\x00\x00\x00\x00':
            header_pos = p
            break

    if header_pos:
        anim_start = header_pos + 8
        anim_data = data[anim_start:anim_table_end]
        print(f"\n  [4] ANIMATION TABLE (0x{anim_start:X}, {len(anim_data)} bytes)")
        # Show per-slot animation data using the offsets from 8-byte records
        for i in range(num):
            rec_off = records_start_addr + i * 8
            slot_anim_off = struct.unpack_from('<I', data, rec_off)[0]
            abs_anim = anim_start + slot_anim_off
            # Each slot typically has 8 bytes
            slot_data = data[abs_anim:abs_anim+8]
            print(f"      Slot {i} ({monsters[i]:20s}): offset=0x{slot_anim_off:02X} -> "
                  f"[{slot_data.hex()}] at 0x{abs_anim:X}")

        # Show full table
        print(f"      Full: [{anim_data.hex()}]")

    # ---------------------------------------------------------------
    # 2. 96-BYTE ENTRIES (the group itself)
    # ---------------------------------------------------------------
    print(f"\n  [5] 96-BYTE ENTRIES (0x{group_off:X})")
    for i in range(num):
        entry_off = group_off + i * 96
        entry = data[entry_off:entry_off+96]

        # Name (16 bytes)
        name_raw = entry[:16]
        name_str = name_raw.split(b'\x00')[0].decode('ascii', errors='replace')

        # Stats (40 uint16 values)
        stats = []
        for j in range(40):
            val = struct.unpack_from('<H', entry, 16 + j * 2)[0]
            stats.append(val)

        print(f"\n      Slot {i}: {name_str}")
        print(f"        Name hex: [{name_raw.hex()}]")

        # Print ALL stats, highlighting named ones and unknowns
        line = "        Stats: "
        for j in range(40):
            label = STAT_NAMES.get(j, f's{j}')
            val = stats[j]
            if j in STAT_NAMES:
                line += f"{label}={val} "
            else:
                if val != 0:  # Only show non-zero unknowns
                    line += f"[{label}={val}] "

            if j == 17:
                print(line)
                line = "                 "
        print(line)

        # Raw hex of stat area for comparison
        print(f"        Raw stats hex: [{entry[16:].hex()}]")

    # ---------------------------------------------------------------
    # 3. SCRIPT AREA (after 96-byte entries)
    # ---------------------------------------------------------------
    script_start = group_off + num * 96
    print(f"\n  [6] SCRIPT AREA (0x{script_start:X})")

    # Read first 512 bytes
    script_data = data[script_start:script_start + 512]

    # Look for type-7 entries (resource definitions)
    print(f"\n      Type entries (resource defs):")
    for i in range(0, len(script_data) - 8, 4):
        if i + 8 <= len(script_data):
            val_off = struct.unpack_from('<I', script_data, i)[0]
            val_data = script_data[i+4:i+8]
            if val_data[0] in (4, 5, 6, 7, 14) and val_data[3] == 0 and 0 < val_off < 0x1000:
                type_byte = val_data[0]
                idx = val_data[1]
                slot = val_data[2]
                abs_off = script_start + i
                monster_name = ""
                if type_byte == 7 and slot < num:
                    monster_name = f"  <- {monsters[slot]}"
                print(f"        0x{abs_off:08X}: off=0x{val_off:04X} type={type_byte:2d} "
                      f"idx=0x{idx:02X} slot={slot}{monster_name}")

    # Look for spawn commands with FF terminators
    print(f"\n      FF-terminated records (spawn commands):")
    i = 0
    rec_num = 0
    while i < len(script_data) - 4:
        if script_data[i:i+4] == b'\xff\xff\xff\xff':
            # Show context: 32 bytes before + 16 after
            ctx_start = max(0, i - 32)
            ctx_end = min(len(script_data), i + 16)

            # The counter after FF
            counter = -1
            if i + 8 <= len(script_data):
                counter = struct.unpack_from('<I', script_data, i + 4)[0]

            # Extract the record bytes
            rec_bytes = script_data[ctx_start:ctx_end]
            abs_addr = script_start + ctx_start

            print(f"\n        Record {rec_num} (counter={counter}) near 0x{script_start + i:X}:")
            # Show in 16-byte lines
            for line_off in range(0, len(rec_bytes), 16):
                chunk = rec_bytes[line_off:line_off+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                abs_line = abs_addr + line_off
                print(f"          0x{abs_line:08X}: {hex_str}")

            rec_num += 1
            i = min(ctx_end, i + 8)
        else:
            i += 1

    # Dump first 256 bytes as uint32 pairs for pattern finding
    print(f"\n      First 128 bytes as uint32 pairs:")
    for i in range(0, min(128, len(script_data)), 8):
        v1 = struct.unpack_from('<I', script_data, i)[0]
        v2 = struct.unpack_from('<I', script_data, i + 4)[0]
        raw = script_data[i:i+8]
        abs_off = script_start + i
        note = ""
        if raw[3] == 0x40 or raw[7] == 0x40:
            note = "  <- 0x40 flag"
        elif v1 == 0 and v2 == 0:
            note = "  <- zeros"
        elif raw[:4] == b'\xff\xff\xff\xff' or raw[4:] == b'\xff\xff\xff\xff':
            note = "  <- FF terminator"
        print(f"        0x{abs_off:08X}: {raw[:4].hex()} {raw[4:].hex()} "
              f"= ({v1:10d}, {v2:10d}){note}")

    print()
    return {
        'section_start': section_start if header_pos is None else header_pos,
        'records_start': records_start_addr,
        'assign_base': assign_base,
    }


def compare_same_monsters(data, areas):
    """Compare stats of the same monster appearing in different areas."""
    print("\n" + "=" * 95)
    print("  CROSS-AREA COMPARISON: Same monsters in different areas")
    print("=" * 95)

    # Collect all monster stats by name
    monster_stats = {}
    for area in areas:
        for i in range(area['num']):
            entry_off = area['group_offset'] + i * 96
            entry = data[entry_off:entry_off+96]
            name = entry[:16].split(b'\x00')[0].decode('ascii', errors='replace')

            stats = []
            for j in range(40):
                val = struct.unpack_from('<H', entry, 16 + j * 2)[0]
                stats.append(val)

            if name not in monster_stats:
                monster_stats[name] = []
            monster_stats[name].append({
                'area': area['name'],
                'slot': i,
                'stats': stats,
                'raw': entry[16:].hex(),
            })

    # Show monsters that appear multiple times
    for name, instances in sorted(monster_stats.items()):
        if len(instances) < 2:
            continue

        print(f"\n  {name} ({len(instances)} instances):")

        # Compare stat by stat
        all_same = True
        for j in range(40):
            values = [inst['stats'][j] for inst in instances]
            if len(set(values)) > 1:
                all_same = False
                label = STAT_NAMES.get(j, f's{j}')
                vals_str = ", ".join(f"{inst['area']}={inst['stats'][j]}" for inst in instances)
                print(f"    DIFFERS stat[{j:2d}] ({label:18s}): {vals_str}")

        if all_same:
            print(f"    All stats IDENTICAL across areas")
        else:
            # Show the full stats for reference
            for inst in instances:
                print(f"    {inst['area']} slot {inst['slot']}: "
                      f"creature_type={inst['stats'][10]} collider_type={inst['stats'][5]}")


def main():
    print("FIND AI CONTROLLER - Comprehensive per-slot data dump")
    print("=" * 95)

    data = bytearray(Path(BLAZE_ALL).read_bytes())
    print(f"Loaded BLAZE.ALL: {len(data):,} bytes\n")

    # Dump each area
    for area in AREAS:
        dump_area(data, area)

    # Cross-area comparison
    compare_same_monsters(data, AREAS)

    # Summary
    print("\n" + "=" * 95)
    print("  NEXT STEPS")
    print("=" * 95)
    print("""
  If creature_type or another stat field differs per monster type consistently,
  that field might control AI. Test by swapping ONLY the 96-byte entries.

  If all stats are identical for same monsters, then AI is in the script area
  (spawn commands or type entries), tied to the slot position.

  Key test: swap 96-byte entries for Goblin <-> Bat WITHOUT swapping L or anim.
  - If AI swaps -> AI is in the 96-byte entries
  - If AI stays -> AI is positional (script area)
""")


if __name__ == '__main__':
    main()
