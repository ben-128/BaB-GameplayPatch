"""
Find what controls AI/behavior per monster slot.

We know L controls the 3D model but NOT the AI.
The AI must be in the script area or some other structure.

Strategy: Compare the script area structures between areas with
different monsters to find what varies per-monster.

Areas to compare:
- Cavern F1 Area 1: 3 monsters (Goblin, Shaman, Bat)
- Cavern F1 Area 2: 4 monsters (Goblin, Shaman, Bat, Goblin-Leader)
- Cavern F3 Area 1: 4 monsters (Scorpion, Bat, Big-Viper, Spider)
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"


def hex_line(data, base, length=16):
    d = data[:length]
    h = ' '.join(f'{b:02X}' for b in d)
    a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d)
    return f'{base:08X}: {h:<48s} |{a}|'


def main():
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())

    areas = [
        ("Cavern F1 Area1", 0xF7A97C, 3, ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]),
        ("Cavern F1 Area2", 0xF7E1A8, 4, ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "Goblin-Leader"]),
        ("Cavern F3 Area1", 0xF86198, 4, ["Giant-Scorpion", "Giant-Bat", "Big-Viper", "Giant-Spider"]),
    ]

    for name, group_off, num, monsters in areas:
        script_start = group_off + num * 96
        print("=" * 90)
        print(f"  {name} | group=0x{group_off:X} | {num} monsters: {', '.join(monsters)}")
        print(f"  Script area starts at 0x{script_start:X}")
        print("=" * 90)

        # Read pre-group assignment entries
        assign_base = group_off - num * 8
        print(f"\n  --- Assignment entries (at 0x{assign_base:X}) ---")
        for i in range(num):
            off = assign_base + i * 8
            ai = blaze[off:off+4]
            mod = blaze[off+4:off+8]
            print(f"    Slot {i} ({monsters[i]:20s}): AI=[{ai.hex()}] L={ai[1]:2d} | Mod=[{mod.hex()}] R={mod[1]:2d}")

        # Dump first 512 bytes of script area with annotations
        script_data = blaze[script_start:script_start + 768]

        # 1. Offset table at start
        print(f"\n  --- Offset table ---")
        off_table = []
        for i in range(0, 64, 4):
            val = struct.unpack_from('<I', script_data, i)[0]
            if val == 0 and i > 0:
                print(f"    [{i:3d}] 0x{val:08X}  (terminator)")
                break
            off_table.append(val)
            print(f"    [{i:3d}] 0x{val:08X}  ({val})")

        # 2. Data after offset table
        table_end = (len(off_table) + 1) * 4  # +1 for terminator
        # Align to 4 bytes
        data_start = table_end
        while data_start < len(script_data) and script_data[data_start:data_start+4] == b'\x00\x00\x00\x00':
            data_start += 4

        print(f"\n  --- Post-offset-table data (from byte {data_start}) ---")
        # Show as uint32 pairs with annotations
        for i in range(data_start, min(data_start + 256, len(script_data)), 4):
            val = struct.unpack_from('<I', script_data, i)[0]
            raw = script_data[i:i+4]
            abs_off = script_start + i

            # Check for interesting values
            note = ""
            if val == 0x0384:
                note = "  <- 0x384 = 900 (repeating)"
            elif raw[3] == 0x40:
                note = "  <- flag 0x40!"
            elif val == 0:
                note = "  <- zero"
            elif raw == b'\xff\xff\xff\xff':
                note = "  <- FFFFFFFF terminator"

            print(f"    0x{abs_off:08X} [{i:3d}]: {raw.hex()} = 0x{val:08X} ({val:10d}){note}")

        # 3. Look for the FF-terminated records (spawn commands)
        print(f"\n  --- FF-terminated records ---")
        i = 0
        rec_num = 0
        while i < len(script_data) - 4:
            if script_data[i:i+4] == b'\xff\xff\xff\xff':
                # Found FF block - show the record (32 bytes ending here + counter after)
                rec_start = max(0, i - 20)
                rec_end = min(len(script_data), i + 12)
                rec = script_data[rec_start:rec_end]
                abs_start = script_start + rec_start

                # The counter is at i+4 (after the FF block)
                counter = struct.unpack_from('<I', script_data, i + 4)[0] if i + 8 <= len(script_data) else -1

                print(f"    Record {rec_num} (counter={counter}) at 0x{abs_start:08X}:")
                print(f"      {rec.hex()}")

                # Look for the 2-byte value before FF (potential AI type?)
                if i >= 2:
                    pre_ff_val = struct.unpack_from('<H', script_data, i - 2)[0]
                    pre_ff_byte = script_data[i - 2]
                    print(f"      Bytes before FF: 0x{pre_ff_byte:02X} ({pre_ff_byte}) uint16=0x{pre_ff_val:04X}")

                rec_num += 1
                i += 12
            else:
                i += 1

        # 4. Look for the type+index entries (type 7 = per-monster)
        print(f"\n  --- Type+index entries (resource definitions) ---")
        # Search for the pattern: [small_offset uint32] [07 XX XX 00]
        for i in range(0, len(script_data) - 8, 4):
            if i + 8 <= len(script_data):
                val_off = struct.unpack_from('<I', script_data, i)[0]
                val_data = script_data[i+4:i+8]
                if val_data[0] in (4, 5, 6, 7, 14) and val_data[3] == 0 and 0 < val_off < 0x1000:
                    # Potential type+index entry
                    type_byte = val_data[0]
                    idx = val_data[1]
                    slot = val_data[2]
                    abs_off = script_start + i
                    monster_name = ""
                    if type_byte == 7 and slot < num:
                        monster_name = f"  <- {monsters[slot]}"
                    print(f"    0x{abs_off:08X}: [0x{val_off:04X}] type={type_byte:2d} idx=0x{idx:02X} slot={slot}{monster_name}")

        print()


if __name__ == '__main__':
    main()
