#!/usr/bin/env python3
"""
Compare monster entity structs from combat savestate to find AI-controlling fields.

Cavern F1 Area1 test area has: Goblin (slot 0), Shaman (slot 1), Bat (slot 2).

Strategy:
1. Extract RAM from savestate
2. Find large entity structs by scanning for overlay config pointers at +0x70
   combined with creature_type=0 at +0x2B5
3. Identify which monster each entity is (by cross-referencing config pointer)
4. Dump and compare all entity bytes between different monsters
5. Cross-reference with 96-byte stat entries from BLAZE.ALL
6. Highlight unknown differences that could control AI/ability selection
"""

import gzip
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------
# Paths
# ---------------------------------------------------------------
SAVESTATE = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\combat\SLES_008.45.000")
BLAZE_ALL = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
EXE_PATH  = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")

RAM_BASE = 0x80000000
RAM_SIZE = 0x200000

# Area data in BLAZE.ALL for Cavern F1 Area1
AREA_ASSIGN_OFF = 0xF7A964   # Assignment entries (L/R pairs)
AREA_STATS_OFF  = 0xF7A97C   # 96-byte stat entries (3 monsters)
AREA_SCRIPT_OFF = 0xF7AA9C   # Script area start

# Entity struct known fields (from dispatch at 0x80024494)
KNOWN_FIELDS = {
    0x070: ("config_ptr",      4, "Overlay config data pointer (model/polygon)"),
    0x144: ("level",           2, "Level counter (halfword, determines tier)"),
    0x146: ("loop_counter",    2, "Loop counter (compared to 0x270F)"),
    0x148: ("counter_a",       2, "Additional counter A"),
    0x14A: ("counter_b",       2, "Additional counter B"),
    0x150: ("flags",           1, "Flags byte (AND 0x07 for table lookup)"),
    0x158: ("timer",           4, "Timer/counter (word)"),
    0x160: ("bitmask_0",       4, "Action bitmask type 0"),
    0x164: ("bitmask_1",       4, "Action bitmask type 0 hi"),
    0x168: ("bitmask_2",       4, "Action bitmask type 1"),
    0x16C: ("bitmask_3",       4, "Action bitmask type 1 hi"),
    0x170: ("bitmask_4",       4, "Action bitmask type 2"),
    0x174: ("bitmask_5",       4, "Action bitmask type 2 hi"),
    0x178: ("bitmask_6",       4, "Action bitmask type 3"),
    0x17C: ("bitmask_7",       4, "Action bitmask type 3 hi"),
    0x280: ("stat_hw_0",       2, "Stat halfword 0"),
    0x282: ("stat_hw_1",       2, "Stat halfword 1"),
    0x284: ("stat_hw_2",       2, "Stat halfword 2"),
    0x286: ("stat_hw_3",       2, "Stat halfword 3"),
    0x288: ("stat_hw_4",       2, "Stat halfword 4"),
    0x28A: ("stat_hw_5",       2, "Stat halfword 5"),
    0x28C: ("stat_hw_6",       2, "Stat halfword 6"),
    0x2AC: ("base_stat",       2, "Base stat value (halfword)"),
    0x2B5: ("creature_type",   1, "creature_type byte (always 0)"),
}

# Overlay region range
OVERLAY_LO = 0x800A0000
OVERLAY_HI = 0x800D0000


def ri(addr):
    return addr - RAM_BASE

def ru32(ram, addr):
    return struct.unpack_from('<I', ram, ri(addr))[0]

def ru16(ram, addr):
    return struct.unpack_from('<H', ram, ri(addr))[0]

def ru8(ram, addr):
    return ram[ri(addr)]

def decode_ascii(data, max_len=32):
    result = []
    for b in data[:max_len]:
        if b == 0:
            break
        if 32 <= b < 127:
            result.append(chr(b))
        else:
            return ""
    return ''.join(result)


def find_entity_structs_by_name(ram, blaze):
    """
    Find entity structs by searching for monster/player name strings in RAM.
    The 96-byte stat entries contain names (e.g., "Lv20.Goblin").
    The init function copies these names to the entity struct.
    Find name occurrences in RAM and use surrounding data to determine entity base.
    """
    # Read monster names from BLAZE.ALL 96-byte entries
    monster_names = []
    for i in range(3):
        off = AREA_STATS_OFF + i * 96
        name = decode_ascii(blaze[off:off+16])
        if name:
            monster_names.append((i, name, blaze[off:off+96]))

    # Also search for player-like names
    player_names = ["Fighter", "Dwarf", "Elf", "Gnome", "Wizard", "Priest",
                    "Sorceress", "Hunter", "Rogue", "Fairy"]

    entities = []

    # Search for each monster name in RAM
    for slot_idx, name, stat_data in monster_names:
        name_bytes = name.encode('ascii')
        pos = 0
        while pos < RAM_SIZE:
            idx = ram.find(name_bytes, pos)
            if idx < 0:
                break
            ram_addr = RAM_BASE + idx
            # This could be: (a) the entity struct name field, (b) a copy of the stat entry,
            # (c) the original BLAZE.ALL data loaded to overlay
            # For entity struct: name should be near the start of the struct
            # Let's record all occurrences and analyze
            # Check if this looks like a 96-byte stat entry copy (next 96 bytes match)
            is_stat_copy = (ram[idx:idx+96] == stat_data)

            entities.append({
                'ram_addr': ram_addr,
                'name': name,
                'slot_idx': slot_idx,
                'is_stat_copy': is_stat_copy,
                'region': 'entity_mgmt' if 0x800B4000 <= ram_addr < 0x800C0000
                          else 'overlay' if 0x800A0000 <= ram_addr < 0x800B4000
                          else 'other',
            })
            pos = idx + 1

    return entities, monster_names


def identify_entity(ram, blaze, ent):
    """Try to identify what this entity is (player class or monster name)."""
    base = ent['base']
    ptr = ent['config_ptr']

    # Check if there's a name string somewhere in the entity
    # Try various offsets where names might be stored
    for name_off in [0x00, 0x04, 0x08, 0x10, 0x20, 0x2A0, 0x2A8, 0x2B0,
                     0x2B8, 0x2C0, 0x2C8, 0x2D0]:
        if base + name_off + 16 > RAM_BASE + RAM_SIZE:
            continue
        data = ram[ri(base + name_off) : ri(base + name_off) + 16]
        txt = decode_ascii(data)
        if txt and len(txt) >= 3:
            return txt, name_off

    return "???", -1


def dump_96byte_entries(blaze):
    """Read the 3 monster 96-byte stat entries from BLAZE.ALL."""
    monsters = []
    for i in range(3):
        off = AREA_STATS_OFF + i * 96
        data = blaze[off:off+96]
        # Try to read name from first 16 bytes
        name = decode_ascii(data[:16])
        monsters.append({
            'index': i,
            'offset': off,
            'name': name,
            'data': data,
        })
    return monsters


def dump_assignment_entries(blaze):
    """Read assignment entries (L/R pairs) from BLAZE.ALL."""
    entries = []
    off = AREA_ASSIGN_OFF
    for i in range(3):
        data = blaze[off + i*8 : off + (i+1)*8]
        L = struct.unpack_from('<I', data, 0)[0]
        R = struct.unpack_from('<I', data, 4)[0]
        entries.append({'L': L, 'R': R, 'L_flag': (L >> 24) & 0xFF, 'L_idx': L & 0xFFFF,
                       'R_flag': (R >> 24) & 0xFF, 'R_idx': R & 0xFFFF})
    return entries


def main():
    print("Loading savestate...")
    raw = gzip.open(str(SAVESTATE), 'rb').read()
    ram = bytearray(raw[0x1BA : 0x1BA + RAM_SIZE])
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())
    exe = bytearray(Path(EXE_PATH).read_bytes())

    # ================================================================
    # STEP 1: Find monster data in RAM via name string search
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 1: Find monster names in RAM")
    print("=" * 100)

    name_hits, monster_names = find_entity_structs_by_name(ram, blaze)
    print(f"\n  Found {len(name_hits)} name occurrences in RAM:\n")

    # Group by name
    by_name = {}
    for hit in name_hits:
        by_name.setdefault(hit['name'], []).append(hit)

    for name, hits in by_name.items():
        print(f"  \"{name}\":")
        for h in hits:
            stat_label = " [96-byte stat copy!]" if h['is_stat_copy'] else ""
            print(f"    0x{h['ram_addr']:08X} ({h['region']}){stat_label}")

    # For each stat copy in entity_mgmt region, this IS likely part of the entity struct
    # The 96-byte data is the entity's stat block. We need to find what ELSE is around it.
    filtered = []
    for hit in name_hits:
        if hit['is_stat_copy'] and hit['region'] == 'entity_mgmt':
            filtered.append(hit)

    if not filtered:
        # Try overlay region too
        for hit in name_hits:
            if hit['is_stat_copy']:
                filtered.append(hit)

    print(f"\n  Using {len(filtered)} stat-copy entities in entity mgmt region")

    # For each entity, dump the context around the 96-byte stat data
    # The stat data is 96 bytes. We want to see what's BEFORE and AFTER it.
    CONTEXT_BEFORE = 0x200  # bytes before the name
    CONTEXT_AFTER = 0x400   # bytes after the name
    entity_dumps = {}

    for hit in filtered:
        name = hit['name']
        stat_addr = hit['ram_addr']
        # Dump a large region centered on the stat data
        dump_start = stat_addr - CONTEXT_BEFORE
        dump_end = stat_addr + CONTEXT_AFTER
        if dump_start < RAM_BASE:
            dump_start = RAM_BASE
        if dump_end > RAM_BASE + RAM_SIZE:
            dump_end = RAM_BASE + RAM_SIZE
        dump_data = ram[ri(dump_start):ri(dump_end)]
        entity_dumps[name] = {
            'stat_addr': stat_addr,
            'dump_start': dump_start,
            'dump_end': dump_end,
            'data': dump_data,
            'stat_offset_in_dump': stat_addr - dump_start,
            'slot_idx': hit['slot_idx'],
        }

    # ================================================================
    # STEP 2: Read 96-byte stat entries from BLAZE.ALL
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 2: 96-byte stat entries from BLAZE.ALL (Cavern F1 Area1)")
    print("=" * 100)

    stat_entries = dump_96byte_entries(blaze)
    for s in stat_entries:
        print(f"\n  Monster {s['index']} at BLAZE 0x{s['offset']:08X}: \"{s['name']}\"")
        # Dump all 96 bytes in rows of 16
        for row in range(6):
            off = row * 16
            hexdata = ' '.join(f"{b:02X}" for b in s['data'][off:off+16])
            print(f"    +0x{off:02X}: {hexdata}")

    # ================================================================
    # STEP 3: Read assignment entries
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 3: Assignment entries (L/R) from BLAZE.ALL")
    print("=" * 100)

    assigns = dump_assignment_entries(blaze)
    for i, a in enumerate(assigns):
        print(f"  Slot {i}: L=0x{a['L']:08X} (flag=0x{a['L_flag']:02X} idx={a['L_idx']})  "
              f"R=0x{a['R']:08X} (flag=0x{a['R_flag']:02X} idx={a['R_idx']})")

    # ================================================================
    # STEP 4: Dump entity data around each stat block
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 4: Entity data around stat blocks")
    print("=" * 100)

    for name, dump in sorted(entity_dumps.items(), key=lambda x: x[1]['slot_idx']):
        stat_off = dump['stat_offset_in_dump']
        data = dump['data']
        stat_addr = dump['stat_addr']
        print(f"\n  --- {name} (stat at 0x{stat_addr:08X}, slot {dump['slot_idx']}) ---")
        print(f"  Dump: 0x{dump['dump_start']:08X} - 0x{dump['dump_end']:08X}")
        print(f"  Stat block at dump offset 0x{stat_off:03X}\n")

        # Dump 0x200 bytes before stat and 0x100 after stat end (96 bytes)
        # Show in 16-byte rows with annotations
        SHOW_BEFORE = min(stat_off, 0x200)
        SHOW_AFTER = min(len(data) - stat_off - 96, 0x300)
        show_start = stat_off - SHOW_BEFORE
        show_end = stat_off + 96 + SHOW_AFTER

        for row_off in range(show_start, show_end, 16):
            rel_to_stat = row_off - stat_off
            abs_addr = dump['dump_start'] + row_off
            hexdata = ' '.join(f"{data[row_off + b]:02X}" if row_off + b < len(data) else "  "
                              for b in range(16))
            # Annotate
            marker = ""
            if 0 <= rel_to_stat < 96:
                marker = " <STAT>"
            elif rel_to_stat == -16 or rel_to_stat == -32:
                marker = ""

            # Check for pointers in this row
            ptrs = []
            for b in range(0, 16, 4):
                if row_off + b + 4 <= len(data):
                    val = struct.unpack_from('<I', data, row_off + b)[0]
                    if 0x800A0000 <= val < 0x800B0000:
                        ptrs.append(f"+{b}=overlay:0x{val:08X}")
                    elif 0x800B0000 <= val < 0x800C0000:
                        ptrs.append(f"+{b}=entmgmt:0x{val:08X}")
                    elif 0x80010000 <= val < 0x80060000:
                        ptrs.append(f"+{b}=exe:0x{val:08X}")
            if ptrs:
                marker += " " + " ".join(ptrs)

            print(f"  0x{abs_addr:08X} ({rel_to_stat:+05d}): {hexdata}{marker}")

    # ================================================================
    # STEP 5: Byte-by-byte comparison aligned on stat block
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 5: Byte-by-byte comparison (aligned on stat block position)")
    print("=" * 100)
    print("  Comparing bytes at same offset RELATIVE TO STAT BLOCK\n")

    dump_names = sorted(entity_dumps.keys(), key=lambda n: entity_dumps[n]['slot_idx'])
    for i in range(len(dump_names)):
        for j in range(i + 1, len(dump_names)):
            name_a = dump_names[i]
            name_b = dump_names[j]
            da = entity_dumps[name_a]
            db = entity_dumps[name_b]
            data_a = da['data']
            data_b = db['data']
            stat_off_a = da['stat_offset_in_dump']
            stat_off_b = db['stat_offset_in_dump']

            print(f"\n  --- DIFF: {name_a} vs {name_b} (relative to stat block) ---")

            # Compare N bytes before and after stat block
            COMPARE_BEFORE = min(stat_off_a, stat_off_b, 0x200)
            stat_end_a = stat_off_a + 96
            stat_end_b = stat_off_b + 96
            after_a = len(data_a) - stat_end_a
            after_b = len(data_b) - stat_end_b
            COMPARE_AFTER = min(after_a, after_b, 0x300)

            diff_ranges = []
            in_diff = False
            diff_start = 0

            total_range = COMPARE_BEFORE + 96 + COMPARE_AFTER
            for rel in range(-COMPARE_BEFORE, 96 + COMPARE_AFTER):
                off_a = stat_off_a + rel
                off_b = stat_off_b + rel
                if off_a < 0 or off_b < 0 or off_a >= len(data_a) or off_b >= len(data_b):
                    if in_diff:
                        diff_ranges.append((diff_start, rel))
                        in_diff = False
                    continue
                if data_a[off_a] != data_b[off_b]:
                    if not in_diff:
                        diff_start = rel
                        in_diff = True
                else:
                    if in_diff:
                        diff_ranges.append((diff_start, rel))
                        in_diff = False
            if in_diff:
                diff_ranges.append((diff_start, 96 + COMPARE_AFTER))

            print(f"  {len(diff_ranges)} differing regions (offset relative to stat block):")
            for start, end in diff_ranges:
                size = end - start
                off_a = stat_off_a + start
                off_b = stat_off_b + start
                val_a = data_a[off_a:off_a+size]
                val_b = data_b[off_b:off_b+size]

                marker = ""
                if 0 <= start < 96:
                    marker = " [STAT BLOCK]"
                abs_a = da['dump_start'] + off_a
                abs_b = db['dump_start'] + off_b

                if size <= 8:
                    hex_a = ' '.join(f"{b:02X}" for b in val_a)
                    hex_b = ' '.join(f"{b:02X}" for b in val_b)
                    if size == 4:
                        int_a = struct.unpack_from('<I', val_a, 0)[0]
                        int_b = struct.unpack_from('<I', val_b, 0)[0]
                        extra = f"  (0x{int_a:08X} vs 0x{int_b:08X})"
                        if 0x800A0000 <= int_a < 0x800B0000:
                            extra += " A=overlay"
                        if 0x800A0000 <= int_b < 0x800B0000:
                            extra += " B=overlay"
                    elif size == 2:
                        int_a = struct.unpack_from('<H', val_a, 0)[0]
                        int_b = struct.unpack_from('<H', val_b, 0)[0]
                        extra = f"  ({int_a} vs {int_b})"
                    elif size == 1:
                        extra = f"  ({val_a[0]} vs {val_b[0]})"
                    else:
                        extra = ""
                    print(f"    stat{start:+05d} (abs 0x{abs_a:08X}/0x{abs_b:08X}): "
                          f"A=[{hex_a}]  B=[{hex_b}]{extra}{marker}")
                else:
                    hex_a = ' '.join(f"{b:02X}" for b in val_a[:16])
                    hex_b = ' '.join(f"{b:02X}" for b in val_b[:16])
                    sfx = "..." if size > 16 else ""
                    print(f"    stat{start:+05d} ({size:3d}B, abs 0x{abs_a:08X}/0x{abs_b:08X}):")
                    print(f"      A=[{hex_a}]{sfx}")
                    print(f"      B=[{hex_b}]{sfx}{marker}")

    # ================================================================
    # STEP 6: Find pointers near stat blocks (overlay ptrs = AI candidates)
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 6: Pointer scan near stat blocks (AI config candidates)")
    print("=" * 100)
    print("  Scanning 0x200 bytes before and 0x300 after each stat block")
    print("  for pointers to overlay code/data region (0x800A0000-0x800B0000).\n")

    for name in dump_names:
        dump = entity_dumps[name]
        data = dump['data']
        stat_off = dump['stat_offset_in_dump']

        print(f"  {name} (stat at 0x{dump['stat_addr']:08X}):")

        scan_start = max(0, stat_off - 0x200)
        scan_end = min(len(data) - 4, stat_off + 96 + 0x300)

        for off in range(scan_start, scan_end, 4):
            val = struct.unpack_from('<I', data, off)[0]
            rel = off - stat_off
            abs_addr = dump['dump_start'] + off

            if 0x800A0000 <= val < 0x800B0000:
                blaze_off = (val - 0x800A0000) + 0x008CA754
                in_stat = " [IN STAT BLOCK]" if 0 <= rel < 96 else ""
                print(f"    stat{rel:+05d} (0x{abs_addr:08X}): 0x{val:08X} -> overlay (BLAZE 0x{blaze_off:08X}){in_stat}")
            elif 0x80010000 <= val < 0x80060000:
                in_stat = " [IN STAT BLOCK]" if 0 <= rel < 96 else ""
                print(f"    stat{rel:+05d} (0x{abs_addr:08X}): 0x{val:08X} -> EXE region{in_stat}")
        print()

    # ================================================================
    # STEP 7: Entity struct stride detection
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 7: Entity struct stride detection")
    print("=" * 100)

    if len(entity_dumps) >= 2:
        addrs = [(name, entity_dumps[name]['stat_addr']) for name in dump_names]
        print("\n  Stat block addresses:")
        for name, addr in addrs:
            print(f"    {name:20s}: 0x{addr:08X}")
        print("\n  Differences between consecutive stat blocks:")
        for i in range(len(addrs) - 1):
            diff = addrs[i+1][1] - addrs[i][1]
            print(f"    {addrs[i][0]} -> {addrs[i+1][0]}: 0x{diff:04X} ({diff} bytes)")

    # ================================================================
    # STEP 8: Battle table and monster metadata analysis
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 8: Battle table (0x800BB93C) and monster metadata (0x800B9268)")
    print("=" * 100)

    # Dump battle table entries
    BATTLE_TABLE = 0x800BB93C
    print("\n  Battle table (12 entries at 0x800BB93C, stride 0x9C):")
    for slot in range(12):
        base = BATTLE_TABLE + slot * 0x9C
        w0 = ru32(ram, base)
        w1 = ru32(ram, base + 4)
        if w0 == 0 and w1 == 0:
            continue
        # Dump first 0x9C bytes
        print(f"\n  Slot {slot} at 0x{base:08X}:")
        for row_off in range(0, 0x9C, 16):
            hex_data = ' '.join(f"{ram[ri(base + row_off + b)]:02X}" for b in range(min(16, 0x9C - row_off)))
            # Check for pointers
            ptrs = []
            for b in range(0, min(16, 0x9C - row_off), 4):
                val = ru32(ram, base + row_off + b)
                if 0x800A0000 <= val < 0x800B0000:
                    ptrs.append(f"+0x{row_off+b:02X}=overlay:0x{val:08X}")
                elif 0x800B0000 <= val < 0x800C0000:
                    ptrs.append(f"+0x{row_off+b:02X}=entmgmt:0x{val:08X}")
            ptr_str = "  " + " ".join(ptrs) if ptrs else ""
            print(f"    +0x{row_off:02X}: {hex_data}{ptr_str}")

    # Dump monster metadata
    MONSTER_META = 0x800B9268
    print(f"\n\n  Monster metadata (stride 0x28, at 0x{MONSTER_META:08X}):")
    for slot in range(6):
        base = MONSTER_META + slot * 0x28
        w0 = ru32(ram, base)
        if w0 == 0:
            continue
        print(f"\n  Metadata slot {slot} at 0x{base:08X}:")
        for row_off in range(0, 0x28, 16):
            n = min(16, 0x28 - row_off)
            hex_data = ' '.join(f"{ram[ri(base + row_off + b)]:02X}" for b in range(n))
            ptrs = []
            for b in range(0, n, 4):
                val = ru32(ram, base + row_off + b)
                if 0x800A0000 <= val < 0x800B0000:
                    ptrs.append(f"+0x{row_off+b:02X}=overlay:0x{val:08X}")
                elif 0x800B0000 <= val < 0x800C0000:
                    ptrs.append(f"+0x{row_off+b:02X}=entmgmt:0x{val:08X}")
            ptr_str = "  " + " ".join(ptrs) if ptrs else ""
            print(f"    +0x{row_off:02X}: {hex_data}{ptr_str}")

    # ================================================================
    # STEP 9: Search for slot index / monster ID relative to stat block
    # ================================================================
    print()
    print("=" * 100)
    print("  STEP 9: Search for slot index / monster ID near stat blocks")
    print("=" * 100)

    if len(dump_names) >= 3:
        d0 = entity_dumps[dump_names[0]]
        d1 = entity_dumps[dump_names[1]]
        d2 = entity_dumps[dump_names[2]]

        COMPARE_RANGE = min(
            d0['stat_offset_in_dump'],
            d1['stat_offset_in_dump'],
            d2['stat_offset_in_dump'],
            0x200
        )
        COMPARE_AFTER = 0x300

        print(f"\n  Checking bytes at same offset relative to stat block:")

        # Search for (0, 1, 2) pattern
        print("\n  Exact (0,1,2) byte matches:")
        for rel in range(-COMPARE_RANGE, 96 + COMPARE_AFTER):
            off0 = d0['stat_offset_in_dump'] + rel
            off1 = d1['stat_offset_in_dump'] + rel
            off2 = d2['stat_offset_in_dump'] + rel
            if off0 < 0 or off1 < 0 or off2 < 0:
                continue
            if off0 >= len(d0['data']) or off1 >= len(d1['data']) or off2 >= len(d2['data']):
                continue
            v0 = d0['data'][off0]
            v1 = d1['data'][off1]
            v2 = d2['data'][off2]
            if v0 == 0 and v1 == 1 and v2 == 2:
                abs0 = d0['dump_start'] + off0
                in_stat = " [IN STAT]" if 0 <= rel < 96 else ""
                print(f"    stat{rel:+05d} (0x{abs0:08X}): EXACT (0,1,2){in_stat}")

        print(f"\n  Sequential (N, N+1, N+2) byte matches (N < 50):")
        for rel in range(-COMPARE_RANGE, 96 + COMPARE_AFTER):
            off0 = d0['stat_offset_in_dump'] + rel
            off1 = d1['stat_offset_in_dump'] + rel
            off2 = d2['stat_offset_in_dump'] + rel
            if off0 < 0 or off1 < 0 or off2 < 0:
                continue
            if off0 >= len(d0['data']) or off1 >= len(d1['data']) or off2 >= len(d2['data']):
                continue
            v0 = d0['data'][off0]
            v1 = d1['data'][off1]
            v2 = d2['data'][off2]
            if v1 == v0 + 1 and v2 == v0 + 2 and 0 < v0 < 50:
                abs0 = d0['dump_start'] + off0
                in_stat = " [IN STAT]" if 0 <= rel < 96 else ""
                print(f"    stat{rel:+05d} (0x{abs0:08X}): seq ({v0},{v1},{v2}){in_stat}")

        # Check 2-byte halfwords
        print(f"\n  Halfword (u16) (0,1,2) matches:")
        for rel in range(-COMPARE_RANGE, 96 + COMPARE_AFTER - 1, 2):
            off0 = d0['stat_offset_in_dump'] + rel
            off1 = d1['stat_offset_in_dump'] + rel
            off2 = d2['stat_offset_in_dump'] + rel
            if off0 < 0 or off1 < 0 or off2 < 0:
                continue
            if off0 + 2 > len(d0['data']) or off1 + 2 > len(d1['data']) or off2 + 2 > len(d2['data']):
                continue
            v0 = struct.unpack_from('<H', d0['data'], off0)[0]
            v1 = struct.unpack_from('<H', d1['data'], off1)[0]
            v2 = struct.unpack_from('<H', d2['data'], off2)[0]
            if v0 == 0 and v1 == 1 and v2 == 2:
                abs0 = d0['dump_start'] + off0
                in_stat = " [IN STAT]" if 0 <= rel < 96 else ""
                print(f"    stat{rel:+05d} (0x{abs0:08X}): u16 EXACT (0,1,2){in_stat}")

    print("\n" + "=" * 100)
    print("  DONE. Review steps 4-6 for AI candidates.")
    print("=" * 100)


if __name__ == '__main__':
    main()
