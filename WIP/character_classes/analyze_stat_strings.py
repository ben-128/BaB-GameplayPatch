"""
analyze_stat_strings.py - Analyze areas around stat string occurrences
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def main():
    data = BLAZE_ALL.read_bytes()

    # Stat string locations found earlier
    stat_strings = {
        'STR': 0x0003ED11,
        'INT': 0x00820FF9,
        'WIL': 0x0084DD86,
        'AGL': 0x0090E159,
        'CON': 0x008228FC,
        'POW': 0x00818862,
        'LUK': 0x0081C4FD,
    }

    for name, offset in stat_strings.items():
        print(f"\n{'='*60}")
        print(f"{name} at 0x{offset:08X}")
        print(f"{'='*60}")

        # Show 64 bytes before and 64 bytes after
        start = max(0, offset - 64)
        end = min(len(data), offset + 64)

        print(hexdump(data[start:end], start))

    # Also look for all occurrences of these stat names
    print(f"\n{'='*60}")
    print("ALL OCCURRENCES OF STAT NAMES")
    print(f"{'='*60}")

    for name in ['STR', 'INT', 'WIL', 'AGL', 'CON', 'POW', 'LUK']:
        search = name.encode('ascii')
        pos = 0
        occurrences = []
        while len(occurrences) < 10:
            pos = data.find(search, pos)
            if pos == -1:
                break
            occurrences.append(pos)
            pos += 1

        print(f"\n{name}: {len(occurrences)} occurrences")
        for occ in occurrences:
            # Get context
            ctx_start = max(0, occ - 20)
            ctx_end = min(len(data), occ + 20)
            ctx = data[ctx_start:ctx_end]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print(f"  0x{occ:08X}: ...{ascii_ctx}...")

    # Search for "Level" which might be near progression data
    print(f"\n{'='*60}")
    print("LEVEL STRING OCCURRENCES")
    print(f"{'='*60}")

    for search in [b'Level', b'level', b'Lv', b'LV']:
        pos = 0
        found = []
        while len(found) < 5:
            pos = data.find(search, pos)
            if pos == -1:
                break
            found.append(pos)
            pos += 1
        if found:
            print(f"\n'{search.decode()}':")
            for occ in found:
                ctx_start = max(0, occ - 10)
                ctx_end = min(len(data), occ + 30)
                ctx = data[ctx_start:ctx_end]
                ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
                print(f"  0x{occ:08X}: {ascii_ctx}")


if __name__ == '__main__':
    main()
