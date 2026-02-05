"""
Search for monster type IDs in the pre-group structure (512 bytes before group offset)
of specific groups in BLAZE.ALL for cross-referencing.
"""

import struct
import sys

BLAZE_PATH = r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL"

# Define the groups to analyze
GROUPS = [
    {
        "name": "Cavern of Death Floor 1 Area 2",
        "offset": 0xF7E1A8,
        "monsters": [
            ("Lv20.Goblin",    84, 0x54),
            ("Goblin-Shaman",  59, 0x3B),
            ("Giant-Bat",      49, 0x31),
            ("Goblin-Leader",  58, 0x3A),
        ],
    },
    {
        "name": "Forest Floor 1 Area 1",
        "offset": 0x148C184,
        "monsters": [
            ("Kobold",        79, 0x4F),
            ("Giant-Beetle",  50, 0x32),
            ("Giant-Ant",     48, 0x30),
        ],
    },
]

SCAN_SIZE = 512  # bytes before group offset to scan


def dump_hex_ascii(data, base_offset, group_offset):
    """Dump data in hex+ASCII format, 16 bytes per line."""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        abs_off = base_offset + i
        rel_off = abs_off - group_offset  # negative offset relative to group start

        hex_part = ""
        for j, b in enumerate(chunk):
            if j == 8:
                hex_part += " "
            hex_part += f"{b:02X} "

        # Pad if last line is short
        expected_hex_len = 16 * 3 + 1  # 16 bytes * "XX " + 1 extra space at midpoint
        hex_part = hex_part.ljust(expected_hex_len)

        ascii_part = ""
        for b in chunk:
            if 0x20 <= b <= 0x7E:
                ascii_part += chr(b)
            else:
                ascii_part += "."

        lines.append(f"  {abs_off:08X} (rel {rel_off:+5d}) | {hex_part}| {ascii_part}")
    return "\n".join(lines)


def search_monster_ids(data, base_offset, group_offset, monsters):
    """Search for each monster's ID as uint8 in the data buffer."""
    results = []
    for mon_name, mon_id, mon_hex in monsters:
        hits = []
        for i in range(len(data)):
            if data[i] == mon_id:
                abs_off = base_offset + i
                rel_off = abs_off - group_offset

                # Extract 16-byte context window centered on the hit
                ctx_start = max(0, i - 8)
                ctx_end = min(len(data), i + 8)
                context = data[ctx_start:ctx_end]

                # Position of the hit within the context
                hit_pos_in_ctx = i - ctx_start

                hits.append({
                    "data_offset": i,
                    "abs_offset": abs_off,
                    "rel_offset": rel_off,
                    "context": context,
                    "hit_pos_in_ctx": hit_pos_in_ctx,
                })
        results.append((mon_name, mon_id, mon_hex, hits))
    return results


def format_context(context, hit_pos):
    """Format a context window with the target byte highlighted."""
    parts = []
    for j, b in enumerate(context):
        if j == hit_pos:
            parts.append(f"[{b:02X}]")
        else:
            parts.append(f" {b:02X} ")
    return "".join(parts)


def main():
    print(f"Opening: {BLAZE_PATH}")
    print(f"Scan window: {SCAN_SIZE} bytes before each group offset")
    print("=" * 100)

    with open(BLAZE_PATH, "rb") as f:
        for group in GROUPS:
            name = group["name"]
            group_off = group["offset"]
            monsters = group["monsters"]

            read_start = group_off - SCAN_SIZE
            if read_start < 0:
                print(f"\n[WARNING] Group '{name}' offset 0x{group_off:X} too close to file start, adjusting.")
                read_start = 0

            actual_scan_size = group_off - read_start

            print(f"\n{'=' * 100}")
            print(f"GROUP: {name}")
            print(f"  Group offset:  0x{group_off:08X} ({group_off})")
            print(f"  Scan range:    0x{read_start:08X} .. 0x{group_off:08X} ({actual_scan_size} bytes)")
            print(f"  Monsters ({len(monsters)}):")
            for mon_name, mon_id, mon_hex in monsters:
                print(f"    - {mon_name:20s}  ID={mon_id:3d} (0x{mon_hex:02X})")
            print()

            # Read the pre-group data
            f.seek(read_start)
            data = f.read(actual_scan_size)

            if len(data) < actual_scan_size:
                print(f"  [WARNING] Only read {len(data)} bytes (expected {actual_scan_size})")

            # --- Search for monster IDs ---
            print(f"--- Monster ID Search Results ---")
            search_results = search_monster_ids(data, read_start, group_off, monsters)

            for mon_name, mon_id, mon_hex, hits in search_results:
                print(f"\n  {mon_name} (ID={mon_id}/0x{mon_hex:02X}): {len(hits)} occurrence(s)")
                if not hits:
                    print(f"    (no matches found in pre-group region)")
                for h in hits:
                    ctx_str = format_context(h["context"], h["hit_pos_in_ctx"])
                    print(f"    @ abs=0x{h['abs_offset']:08X}  rel={h['rel_offset']:+5d}  "
                          f"(data[{h['data_offset']}])")
                    print(f"      context: {ctx_str}")

            # --- Full hex dump ---
            print(f"\n--- Full Hex+ASCII Dump (0x{read_start:08X} to 0x{group_off:08X}) ---")
            print(dump_hex_ascii(data, read_start, group_off))

    print(f"\n{'=' * 100}")
    print("Done.")


if __name__ == "__main__":
    main()
