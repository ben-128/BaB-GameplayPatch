"""
patch_monster_stats.py
Patches monster stats in BLAZE.ALL only
(The BIN injection script will then copy BLAZE.ALL into the BIN)

Usage: py -3 patch_monster_stats.py
"""

import json
import struct
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"
JSON_DIR = SCRIPT_DIR

# Stats field order (offset from monster entry + 0x10)
STATS_FIELDS = {
    'hp': 0x00,
    'mp': 0x02,
    'str': 0x04,
    'int': 0x06,
    'wil': 0x08,
    'agl': 0x0A,
    'con': 0x0C,
    'pow': 0x0E,
    'luk': 0x10,
    'at': 0x12,
    'mat': 0x14,
    'def': 0x16,
    'mdef': 0x18,
    'exp': 0x1A,
    'gold': 0x1C
}


def patch_stats(data: bytearray, name_offset: int, stats: dict, name: str) -> bool:
    """Patch monster stats in data at given name offset"""
    stats_base = name_offset + 0x10

    for field, field_offset in STATS_FIELDS.items():
        if field in stats:
            value = stats[field]
            write_offset = stats_base + field_offset

            if write_offset + 2 > len(data):
                return False

            # Pack as little-endian uint16
            packed = struct.pack('<H', value)
            data[write_offset:write_offset+2] = packed

    return True


def find_all_occurrences(data: bytes, name: str) -> list:
    """Find all offsets where monster name appears"""
    search = name.encode('ascii')
    offsets = []
    pos = 0
    while True:
        pos = data.find(search, pos)
        if pos == -1:
            break

        # Check if substring of larger name
        if pos > 0:
            prev_char = data[pos-1]
            if (0x41 <= prev_char <= 0x5A) or (0x61 <= prev_char <= 0x7A) or prev_char == 0x2D:
                pos += 1
                continue

        # Verify proper monster entry
        entry = data[pos:pos+16]
        if b'\x00' in entry:
            actual_name = entry.split(b'\x00')[0].decode('ascii', errors='ignore')
            if actual_name == name:
                offsets.append(pos)
        pos += 1
    return offsets


def main():
    print("=" * 60)
    print("  Monster Stats BLAZE.ALL Patcher")
    print("=" * 60)
    print()

    # Read BLAZE.ALL
    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        return

    print(f"Reading {BLAZE_ALL}...")
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  Size: {len(blaze_data)} bytes")
    print()

    # Process JSON files
    json_files = [f for f in JSON_DIR.glob("**/*.json") if not f.name.startswith('_')]
    print(f"Processing {len(json_files)} monster files...")
    print()

    total_patched = 0

    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                monster = json.load(f)

            name = monster.get('name', json_file.stem)
            stats = monster.get('stats', {})

            # Find ALL occurrences
            offsets = find_all_occurrences(bytes(blaze_data), name)

            if not offsets:
                print(f"  WARNING: {name} - not found")
                continue

            # Patch at ALL locations
            for offset in offsets:
                patch_stats(blaze_data, offset, stats, name)

            total_patched += len(offsets)
            print(f"  {name}: patched {len(offsets)} occurrence{'s' if len(offsets) > 1 else ''}")

        except Exception as e:
            print(f"  ERROR: {json_file.name}: {e}")

    print()
    print(f"Patched {total_patched} total monster entries in BLAZE.ALL")
    print()

    # Write output
    print(f"Writing {BLAZE_ALL}...")
    BLAZE_ALL.write_bytes(blaze_data)

    print()
    print("=" * 60)
    print("  BLAZE.ALL patched successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
