"""
dump_stat_tooltips.py - Dump the stat tooltip area
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"


def main():
    data = BLAZE_ALL.read_bytes()

    # Stat tooltips area
    start = 0x0090E0D0
    end = 0x0090E300

    print("STAT TOOLTIPS AREA (0x0090E0D0 - 0x0090E300)")
    print("=" * 70)

    # Extract readable strings
    chunk = data[start:end]

    # Find null-terminated strings
    current_offset = start
    i = 0
    while i < len(chunk):
        # Skip null bytes
        while i < len(chunk) and chunk[i] == 0:
            i += 1
        if i >= len(chunk):
            break

        # Find end of string
        str_start = i
        while i < len(chunk) and chunk[i] != 0:
            i += 1

        if i - str_start > 3:  # Only show strings > 3 chars
            try:
                s = chunk[str_start:i].decode('ascii', errors='replace')
                offset = start + str_start
                print(f"0x{offset:08X}: {s}")
            except:
                pass

    # Now look for the zone before class names (might have stat tables)
    print("\n" + "=" * 70)
    print("ZONE BEFORE CLASS NAMES (0x0090B600 - 0x0090B6E8)")
    print("=" * 70)

    start2 = 0x0090B600
    end2 = 0x0090B6E8
    chunk2 = data[start2:end2]

    i = 0
    while i < len(chunk2):
        while i < len(chunk2) and chunk2[i] == 0:
            i += 1
        if i >= len(chunk2):
            break

        str_start = i
        while i < len(chunk2) and chunk2[i] != 0:
            i += 1

        if i - str_start > 3:
            try:
                s = chunk2[str_start:i].decode('ascii', errors='replace')
                offset = start2 + str_start
                print(f"0x{offset:08X}: {s}")
            except:
                pass

    # Hex dump of zone before first class name
    print("\n" + "=" * 70)
    print("HEX DUMP 0x0090B680 - 0x0090B6F0")
    print("=" * 70)

    start3 = 0x0090B680
    for i in range(0, 0x70, 16):
        chunk = data[start3+i:start3+i+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {start3+i:08X}: {hex_str}  {ascii_str}")


if __name__ == '__main__':
    main()
