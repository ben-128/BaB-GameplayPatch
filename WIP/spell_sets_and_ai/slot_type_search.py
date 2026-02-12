"""
Search for slot_type values in BLAZE.ALL to find the spell set definition table.

Searches for known slot_type values (02000000, 03000000, 00000a00, etc.) and
lists their occurrences with surrounding context.
"""
import sys
from pathlib import Path

BLAZE_ALL = Path(__file__).parent.parent.parent / "output" / "BLAZE.ALL"

# Known slot_types from formations (little-endian)
SLOT_TYPES = {
    b'\x00\x00\x00\x00': '00000000 (Base)',
    b'\x02\x00\x00\x00': '02000000 (Shaman Sleep)',
    b'\x03\x00\x00\x00': '03000000 (Tower Heal)',
    b'\x00\x0a\x00\x00': '00000a00 (Bat FireBullet)',
    b'\x00\x01\x00\x00': '00000100 (Rare Arch-Magi)',
}

def search_slot_types():
    if not BLAZE_ALL.exists():
        print(f"[ERROR] {BLAZE_ALL} not found")
        return 1

    data = BLAZE_ALL.read_bytes()
    print(f"[INFO] Loaded {len(data):,} bytes from {BLAZE_ALL.name}")
    print(f"[INFO] Searching for {len(SLOT_TYPES)} known slot_type values...\n")

    for slot_bytes, name in SLOT_TYPES.items():
        if slot_bytes == b'\x00\x00\x00\x00':
            # Skip 00000000 - too many matches
            continue

        print(f"{'='*70}")
        print(f"Searching for: {name}")
        print(f"{'='*70}")

        matches = []
        offset = 0
        while True:
            offset = data.find(slot_bytes, offset)
            if offset == -1:
                break
            matches.append(offset)
            offset += 1

        if not matches:
            print(f"  No matches found.\n")
            continue

        print(f"  Found {len(matches)} occurrences:\n")

        # Show first 20 matches with context
        for i, off in enumerate(matches[:20]):
            # Show 16 bytes before and 16 bytes after
            start = max(0, off - 16)
            end = min(len(data), off + 4 + 16)
            context = data[start:end]

            hex_str = ' '.join(f'{b:02x}' for b in context)
            # Highlight the match
            match_pos = (off - start) * 3
            highlighted = (hex_str[:match_pos] +
                          f'\033[91m{hex_str[match_pos:match_pos+11]}\033[0m' +
                          hex_str[match_pos+11:])

            print(f"  [{i+1}] Offset 0x{off:06X} ({off:,})")
            print(f"      {highlighted}")

            # Try to show ASCII if printable
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
            print(f"      {ascii_str}")
            print()

        if len(matches) > 20:
            print(f"  ... and {len(matches) - 20} more occurrences\n")

    return 0

if __name__ == '__main__':
    sys.exit(search_slot_types())
