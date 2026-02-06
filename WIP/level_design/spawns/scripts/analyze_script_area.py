"""
Analyze the script area AFTER the 96-byte entries and the zone header
BEFORE the first spawn group.

Goal: Find where the 3D model/mesh is defined for each monster.
We've tested everything in the immediate pre-group area - texture ref,
AI assignment, model assignment - none control the 3D mesh.

The mesh must be defined in:
1. The room script (after 96-byte entries) - spawn commands with monster IDs?
2. A zone header (before the first spawn group's data)
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"


def hex_dump(data, base_offset, bytes_per_line=16):
    lines = []
    for i in range(0, len(data), bytes_per_line):
        addr = base_offset + i
        hex_parts = []
        ascii_parts = []
        for j in range(bytes_per_line):
            if i + j < len(data):
                b = data[i + j]
                hex_parts.append(f'{b:02X}')
                ascii_parts.append(chr(b) if 32 <= b < 127 else '.')
            else:
                hex_parts.append('  ')
                ascii_parts.append(' ')
        hex_grouped = ' '.join(hex_parts[:4]) + '  ' + ' '.join(hex_parts[4:8]) + '  ' + ' '.join(hex_parts[8:12]) + '  ' + ' '.join(hex_parts[12:16])
        ascii_str = ''.join(ascii_parts)
        lines.append(f'  {addr:08X}  {hex_grouped}  |{ascii_str}|')
    return '\n'.join(lines)


def main():
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())

    # Cavern of Death groups
    groups = [
        ("Floor 1 - Area 1", 0xF7A97C, 3),
        ("Floor 1 - Area 2", 0xF7E1A8, 4),
        ("Floor 2 - Area 1", 0xF819A0, 4),
    ]

    # ===================================================================
    # PART 1: Script area after 96-byte entries (first 512 bytes)
    # ===================================================================
    print("=" * 90)
    print("  PART 1: SCRIPT AREA (after 96-byte entries)")
    print("=" * 90)

    for name, offset, num in groups[:2]:
        post_start = offset + num * 96
        post_data = blaze[post_start:post_start + 512]

        print(f"\n--- {name} (offset 0x{offset:X}, {num} monsters) ---")
        print(f"  Script area starts at 0x{post_start:X}")
        print()

        # Look for 32-byte repeating structures with FF FF FF FF terminators
        print("  [Searching for FF-terminated records]")
        i = 0
        record_count = 0
        while i < len(post_data) - 8:
            # Check for FFFFFFFF at position i or i+4
            if post_data[i:i+4] == b'\xff\xff\xff\xff':
                # Found FF block, look at surrounding context
                rec_start = max(0, i - 24)
                rec_end = min(len(post_data), i + 16)
                chunk = post_data[rec_start:rec_end]
                abs_start = post_start + rec_start
                print(f"    Record at 0x{abs_start:08X}: {chunk.hex()}")
                record_count += 1
                i += 16
            else:
                i += 1

        print(f"  Found {record_count} FF-terminated records")
        print()
        print(f"  [Full hex dump: first 512 bytes after entries]")
        print(hex_dump(post_data, post_start))

    # ===================================================================
    # PART 2: Zone header - data BEFORE the first spawn group
    # ===================================================================
    print()
    print("=" * 90)
    print("  PART 2: ZONE HEADER (before first spawn group)")
    print("=" * 90)

    first_group_offset = 0xF7A97C
    # The pre-group data starts around -512 to -400 bytes before the 96-byte entries
    # Let's go 8KB before the first group to find the zone header
    header_start = first_group_offset - 8192
    header_end = first_group_offset - 400  # stop before the known pre-group area

    print(f"\n  Scanning 0x{header_start:X} to 0x{header_end:X} ({header_end - header_start} bytes)")

    zone_data = blaze[header_start:header_end]

    # Look for structures that could be monster type lists
    # Monster IDs from _index.json for Cavern monsters:
    # Lv20.Goblin=84, Goblin-Shaman=59, Giant-Bat=49, Goblin-Leader=57
    # Big-Viper=46, Giant-Scorpion=52, Giant-Spider=54, Giant-Centipede=51
    # Dragon-Puppy=47, Cave-Bear=44, Cave-Scissors=45, Killer-Fish=66
    # Spirit-Ball=101, Blue-Slime=43, Ogre=92, Green-Giant=55, Troll=109
    cavern_monsters = {
        84: "Lv20.Goblin", 59: "Goblin-Shaman", 49: "Giant-Bat",
        57: "Goblin-Leader", 46: "Big-Viper", 52: "Giant-Scorpion",
        54: "Giant-Spider", 51: "Giant-Centipede", 47: "Dragon-Puppy",
        44: "Cave-Bear", 45: "Cave-Scissors", 66: "Killer-Fish",
        101: "Spirit-Ball", 43: "Blue-Slime", 92: "Ogre",
        55: "Green-Giant", 109: "Troll"
    }

    # Search for clusters of Cavern monster IDs
    print(f"\n  [Searching for clusters of Cavern monster IDs]")
    for i in range(len(zone_data)):
        val = zone_data[i]
        if val in cavern_monsters:
            # Check if there are more monster IDs nearby (within 32 bytes)
            nearby = []
            for j in range(max(0, i-16), min(len(zone_data), i+16)):
                if zone_data[j] in cavern_monsters:
                    nearby.append((j, zone_data[j], cavern_monsters[zone_data[j]]))
            if len(nearby) >= 3:  # At least 3 monster IDs in 32-byte window
                abs_pos = header_start + i
                # Show context
                ctx_start = max(0, i - 8)
                ctx_end = min(len(zone_data), i + 24)
                ctx = zone_data[ctx_start:ctx_end]
                ids_str = ", ".join(f"{n[1]}={n[2]}" for n in nearby)
                print(f"    0x{abs_pos:08X}: {ctx.hex()}")
                print(f"      IDs: {ids_str}")
                # Skip ahead to avoid duplicate reports
                break

    # Search for uint16 LE monster IDs
    print(f"\n  [Searching for uint16 LE Cavern monster IDs]")
    for i in range(len(zone_data) - 1):
        val = struct.unpack_from('<H', zone_data, i)[0]
        if val in cavern_monsters:
            # Check neighborhood
            nearby_u16 = []
            for j in range(max(0, i-16), min(len(zone_data)-1, i+16), 2):
                v = struct.unpack_from('<H', zone_data, j)[0]
                if v in cavern_monsters:
                    nearby_u16.append((j, v, cavern_monsters[v]))
            if len(nearby_u16) >= 3:
                abs_pos = header_start + i
                ctx_start = max(0, i - 4)
                ctx_end = min(len(zone_data), i + 32)
                ctx = zone_data[ctx_start:ctx_end]
                ids_str = ", ".join(f"0x{n[1]:02X}={n[2]}" for n in nearby_u16)
                print(f"    0x{abs_pos:08X}: {ctx.hex()}")
                print(f"      IDs: {ids_str}")
                break

    # ===================================================================
    # PART 3: Scan between Area 1 and Area 2
    # ===================================================================
    print()
    print("=" * 90)
    print("  PART 3: GAP between Area 1 end and Area 2 start")
    print("=" * 90)

    area1_end = 0xF7A97C + 3 * 96  # end of 96-byte entries
    area2_pre = 0xF7E1A8 - 512     # start of area 2's pre-group region

    print(f"\n  Area 1 entries end: 0x{area1_end:X}")
    print(f"  Area 2 pre-group starts ~: 0x{area2_pre:X}")
    print(f"  Gap size: {area2_pre - area1_end} bytes")

    # Dump the LAST 256 bytes before Area 2's pre-group region
    # This is where Area 2's header/init data would be
    tail_start = area2_pre - 256
    tail_data = blaze[tail_start:area2_pre]
    print(f"\n  [Last 256 bytes before Area 2 pre-group (0x{tail_start:X})]")
    print(hex_dump(tail_data, tail_start))

    # Also dump the transition between dialogue text and next area
    # Find end of ASCII text in Area 1's script area
    scan_start = area1_end + 1024  # skip past the spawn commands
    scan_data = blaze[scan_start:area2_pre]
    last_text = 0
    for i in range(len(scan_data)):
        if 32 <= scan_data[i] < 127:
            last_text = i

    if last_text > 0:
        text_end = scan_start + last_text + 1
        print(f"\n  [Last ASCII text ends around 0x{text_end:X}]")
        # Dump 256 bytes after text ends
        post_text = blaze[text_end:text_end + 256]
        print(f"  [256 bytes after text end]")
        print(hex_dump(post_text, text_end))

    # ===================================================================
    # PART 4: Look at the FIRST 256 bytes of the script area for
    # spawn command structure with monster IDs
    # ===================================================================
    print()
    print("=" * 90)
    print("  PART 4: SPAWN COMMANDS (detailed analysis)")
    print("=" * 90)

    # Focus on the first part of script area after Floor 1 Area 1
    cmd_start = 0xF7A97C + 3 * 96  # 0xF7AA9C
    cmd_data = blaze[cmd_start:cmd_start + 1024]

    # Look for 32-byte records
    print(f"\n  [32-byte record scan from 0x{cmd_start:X}]")
    i = 0
    records = []
    while i < len(cmd_data) - 32:
        # Check if there's a FF FF FF FF pattern nearby
        has_ff = False
        for j in range(0, 32, 4):
            if i + j + 4 <= len(cmd_data):
                if cmd_data[i+j:i+j+4] == b'\xff\xff\xff\xff':
                    has_ff = True
                    break

        if has_ff:
            rec = cmd_data[i:i+32]
            # Check if any byte matches a known monster ID
            monster_hits = []
            for j, b in enumerate(rec):
                if b in cavern_monsters:
                    monster_hits.append((j, b, cavern_monsters[b]))

            abs_addr = cmd_start + i
            records.append({
                'offset': abs_addr,
                'data': rec,
                'monsters': monster_hits
            })

            # Print
            hex1 = rec[:16].hex()
            hex2 = rec[16:].hex()
            print(f"    0x{abs_addr:08X}: {hex1}")
            print(f"                    {hex2}")
            if monster_hits:
                for pos, mid, mname in monster_hits:
                    print(f"      -> byte[{pos}] = 0x{mid:02X} ({mid}) = {mname}")
            print()

            i += 32
        else:
            i += 4  # skip ahead


if __name__ == '__main__':
    main()
