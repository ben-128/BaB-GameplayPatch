#!/usr/bin/env python3
"""
Deep analysis of spawn command records (FF-terminated blocks) in the script area.

These are the ONLY per-slot data in BLAZE.ALL we haven't tested for AI control.
Goal: identify which bytes could be a monster-type / AI reference.

Strategy:
1. Parse all spawn command payloads for multiple areas
2. Look for bytes that correlate with monster types
3. Compare across areas with same/different monsters
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

AREAS = [
    {
        'name': "Cavern F1 Area1",
        'group_offset': 0xF7A97C,
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
    {
        'name': "Cavern F7 Area1",
        'group_offset': 0xF8C1C4,
        'num': 3,
        'monsters': ["Cave-Bear", "Blue-Slime", "Ogre"],
    },
]


def parse_spawn_commands(data, script_start, max_scan=4096):
    """Parse the script area to find FF-terminated spawn command records."""
    region = data[script_start:script_start + max_scan]

    # First: find the offset table (first part of script area)
    offsets = []
    for i in range(0, min(256, len(region)), 4):
        val = struct.unpack_from('<I', region, i)[0]
        if val == 0 and i > 0:
            offsets.append(0)  # terminator
            break
        offsets.append(val)

    offset_table_end = len(offsets) * 4

    # Find first FF FF FF FF block
    first_ff = -1
    for i in range(offset_table_end, len(region) - 4):
        if region[i:i+4] == b'\xff\xff\xff\xff':
            first_ff = i
            break

    if first_ff < 0:
        return None

    # Walk backwards from first FF to find the header
    # The spawn command block typically starts with a header, then payload, then FF
    # Look for the start of the block (after zero padding)
    block_start = first_ff
    # Each payload is 24 bytes before the FF terminator (which is 8 bytes)
    # But the first block may have an 8-byte header too
    # Let's scan backwards for the start of non-zero data
    scan = first_ff - 1
    while scan > offset_table_end and region[scan] == 0:
        scan -= 1
    # The non-zero data ends at scan+1, but the block might start earlier
    # Let's look for the 8-byte header pattern: XX XX YY YY 00 00 ZZ 00

    # Actually, let's just parse from the first non-zero byte after offset table
    data_start = offset_table_end
    while data_start < first_ff and region[data_start:data_start+4] == b'\x00\x00\x00\x00':
        data_start += 4

    # Now parse all FF-terminated blocks
    commands = []
    pos = data_start

    while pos < len(region) - 8:
        # Find next FF FF FF FF
        ff_pos = -1
        for i in range(pos, min(pos + 256, len(region) - 4)):
            if region[i:i+4] == b'\xff\xff\xff\xff':
                ff_pos = i
                break

        if ff_pos < 0:
            break

        # Extract payload (everything from pos to ff_pos)
        payload = bytes(region[pos:ff_pos])

        # Read the FF terminator info (8 bytes)
        ff_block = region[ff_pos:ff_pos+8]
        counter_raw = struct.unpack_from('<I', region, ff_pos + 4)[0]
        # High bits seem to be 0xFFFF, low 2 bytes are the actual counter
        counter_hi = (counter_raw >> 16) & 0xFFFF
        counter_lo = counter_raw & 0xFFFF

        commands.append({
            'payload_offset': script_start + pos,
            'payload': payload,
            'ff_offset': script_start + ff_pos,
            'counter_raw': counter_raw,
            'counter_hi': counter_hi,
            'counter_lo': counter_lo,
        })

        pos = ff_pos + 8  # skip past FF block

    return {
        'script_start': script_start,
        'offset_table': offsets,
        'offset_table_end': offset_table_end,
        'data_start': data_start,
        'first_ff': first_ff,
        'commands': commands,
    }


def main():
    data = bytearray(Path(BLAZE_ALL).read_bytes())
    print("SPAWN COMMAND DEEP ANALYSIS")
    print("=" * 100)

    for area in AREAS:
        name = area['name']
        group_off = area['group_offset']
        num = area['num']
        monsters = area['monsters']

        script_start = group_off + num * 96

        result = parse_spawn_commands(data, script_start)
        if not result:
            print(f"\n  {name}: No spawn commands found!")
            continue

        print(f"\n{'=' * 100}")
        print(f"  {name} | {num} monsters: {', '.join(monsters)}")
        print(f"  Script area: 0x{script_start:X}")
        print(f"  Offset table: {len(result['offset_table'])} entries")
        print(f"  Data starts at script+0x{result['data_start']:X}")
        print(f"  {len(result['commands'])} spawn commands")
        print(f"{'=' * 100}")

        # Show intermediate data between offset table and spawn commands
        inter_start = result['offset_table_end']
        inter_end = result['data_start']
        if inter_end > inter_start:
            inter_data = data[script_start + inter_start:script_start + inter_end]
            # Skip leading zeros
            first_nonzero = 0
            while first_nonzero < len(inter_data) and inter_data[first_nonzero] == 0:
                first_nonzero += 1

            if first_nonzero < len(inter_data):
                print(f"\n  Intermediate data (script+0x{inter_start + first_nonzero:X} to script+0x{inter_end:X}):")
                for i in range(first_nonzero, len(inter_data), 8):
                    chunk = inter_data[i:i+8]
                    abs_off = script_start + inter_start + i
                    hex_str = ' '.join(f'{b:02X}' for b in chunk)
                    print(f"    0x{abs_off:08X}: {hex_str}")

        # Show each spawn command
        for ci, cmd in enumerate(result['commands']):
            payload = cmd['payload']
            abs_off = cmd['payload_offset']

            print(f"\n  --- Command {ci} (counter=0x{cmd['counter_raw']:08X}) ---")
            print(f"  Payload at 0x{abs_off:X} ({len(payload)} bytes):")

            # Show raw hex in 8-byte lines
            for i in range(0, len(payload), 8):
                chunk = payload[i:i+8]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                vals = []
                for j in range(0, len(chunk) - 1, 2):
                    u16 = struct.unpack_from('<H', chunk, j)[0]
                    s16 = struct.unpack_from('<h', chunk, j)[0]
                    vals.append(f"{s16:6d}")
                val_str = ' '.join(vals)
                print(f"    +{i:02d}: {hex_str:<24s}  int16: {val_str}")

            # Highlight key fields
            if len(payload) >= 16:
                # Check if first 8 bytes look like a header (only for first command)
                if ci == 0 and len(payload) >= 32:
                    header = payload[:8]
                    h_vals = [struct.unpack_from('<H', header, j)[0] for j in range(0, 8, 2)]
                    print(f"    HEADER: uint16 = {h_vals}")
                    body = payload[8:]
                else:
                    body = payload

                # Parse the 24-byte body
                if len(body) >= 24:
                    # Bytes 0-7: flags/config
                    flags = body[:8]
                    # Bytes 8-9: potential type reference
                    type_ref = struct.unpack_from('<H', body, 8)[0]
                    # Bytes 10-15: potential coordinates (3 x int16)
                    coords = [struct.unpack_from('<h', body, 10 + j*2)[0] for j in range(3)]
                    # Bytes 16-23: additional params
                    params = body[16:24]
                    param_u16 = [struct.unpack_from('<H', params, j)[0] for j in range(0, 8, 2)]

                    print(f"    PARSED: flags=[{flags.hex()}] type_ref=0x{type_ref:04X}({type_ref}) "
                          f"coords=({coords[0]},{coords[1]},{coords[2]}) "
                          f"params={param_u16}")

        # Summary: list all type_ref values and their distribution
        print(f"\n  --- Type reference summary ---")
        type_refs = []
        for ci, cmd in enumerate(result['commands']):
            payload = cmd['payload']
            if ci == 0 and len(payload) >= 32:
                body = payload[8:]
            else:
                body = payload
            if len(body) >= 10:
                tr = struct.unpack_from('<H', body, 8)[0]
                type_refs.append(tr)
                print(f"    Cmd {ci}: type_ref=0x{tr:04X} ({tr})")

        # Also show all unique non-zero byte values across all payloads
        # to spot potential monster references
        print(f"\n  --- All unique byte values in spawn commands ---")
        all_bytes = {}
        for ci, cmd in enumerate(result['commands']):
            for i, b in enumerate(cmd['payload']):
                if b != 0 and b != 0xFF:
                    key = (i % 24, b)  # position within 24-byte cycle
                    if key not in all_bytes:
                        all_bytes[key] = []
                    all_bytes[key].append(ci)

        # Group by position
        by_pos = {}
        for (pos, val), cmds in sorted(all_bytes.items()):
            if pos not in by_pos:
                by_pos[pos] = []
            by_pos[pos].append((val, cmds))

        for pos in sorted(by_pos.keys()):
            vals = by_pos[pos]
            if len(vals) > 1 or any(v[0] > 3 for v in vals):
                val_str = ', '.join(f'0x{v:02X}(cmd {",".join(str(c) for c in cs)})' for v, cs in vals)
                print(f"    Byte pos {pos:2d}: {val_str}")

    print("\n" + "=" * 100)
    print("Look for type_ref values that correlate with monster types across areas.")
    print("Also check intermediate data for per-monster config entries.")


if __name__ == '__main__':
    main()
