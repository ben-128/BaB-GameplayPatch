"""
parse_spawn_entries.py
Parse the 32-byte spawn entries found in BLAZE.ALL

Entry format (32 bytes):
  [0-3]   FFFFFFFF     - Delimiter marker
  [4-5]   uint16       - Monster ID A (primary monster)
  [6-7]   uint16       - Unknown (often 0, sometimes a value)
  [8-9]   uint16       - Some parameter (count? difficulty?)
  [10-11]  uint16      - Monster ID B (companion monster)
  [12-13]  uint16      - Flags (0xFF82, 0xFF02, 0xFF00, 0xFFC2, etc.)
  [14-15]  uint16      - Extra monster ID or 0
  [16-17]  int16       - X coordinate
  [18-19]  int16       - Y coordinate
  [20-21]  int16       - Z coordinate
  [22-23]  uint16      - Padding
  [24-25]  uint16      - Some value (height? layer?)
  [26-27]  uint16      - Padding
  [28-29]  uint16      - Some value
  [30-31]  FFFF        - End marker

Usage: py -3 parse_spawn_entries.py
"""

import struct
import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

# Load monster names
def load_monsters():
    index_file = PROJECT_ROOT / "Data" / "monster_stats" / "_index.json"
    names = {}
    if index_file.exists():
        with open(index_file, 'r') as f:
            data = json.load(f)
            for m in data.get('monsters', []):
                mid = m.get('id')
                if mid is not None:
                    names[mid] = m.get('name', f'Monster_{mid}')
    return names

# Level name locations for mapping spawn entries to levels
LEVEL_STRINGS = {
    "Castle Of Vamp": [],
    "CAVERN OF DEATH": [],
    "The Forest": [],
    "VALLEY OF WHITE WIND": [],
}

def find_level_regions(data):
    """Find level name strings and define regions around them."""
    level_names = [
        b"Castle Of Vamp",
        b"CAVERN OF DEATH",
        b"VALLEY OF WHITE WIND",
    ]

    regions = []
    for name in level_names:
        pos = 0
        while True:
            pos = data.find(name, pos)
            if pos == -1:
                break
            regions.append((pos, name.decode('ascii', errors='ignore')))
            pos += 1

    # Also search for specific region markers
    pos = data.find(b"The Forest")
    if pos != -1:
        regions.append((pos, "The Forest"))

    return sorted(regions)


def find_spawn_entries(data, names):
    """
    Find all 32-byte spawn entries that match the pattern:
    FFFFFFFF [monster_data] ... FFFF

    The key signature:
    - Starts with FFFFFFFF
    - Contains valid monster IDs at bytes 4-5 and 10-11
    - Ends with FFFF at bytes 30-31
    """
    valid_ids = set(names.keys())
    entries = []

    # Search for FFFFFFFF pattern
    marker = b'\xff\xff\xff\xff'
    pos = 0

    while pos < len(data) - 32:
        pos = data.find(marker, pos)
        if pos == -1:
            break

        # Read the 32-byte entry
        if pos + 32 > len(data):
            break

        entry = data[pos:pos+32]

        # Check end marker (last 2 bytes = FFFF)
        if entry[30:32] != b'\xff\xff':
            pos += 1
            continue

        # Parse the entry
        vals = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 32, 2)]

        # Check for monster IDs at position [4] (bytes 8-9) and [5] (bytes 10-11)
        id_a = vals[2]  # bytes 4-5
        id_b = vals[5]  # bytes 10-11

        # At least one must be a valid non-zero monster ID
        a_valid = id_a in valid_ids and 1 <= id_a <= 123
        b_valid = id_b in valid_ids and 1 <= id_b <= 123

        if a_valid or b_valid:
            # Parse coordinates (bytes 16-21 as signed int16)
            x = struct.unpack_from('<h', entry, 16)[0]
            y = struct.unpack_from('<h', entry, 18)[0]
            z = struct.unpack_from('<h', entry, 20)[0]

            # Parse other fields
            param = vals[4]  # bytes 8-9
            flags = vals[6]  # bytes 12-13
            extra = vals[7]  # bytes 14-15
            val_24 = vals[12]  # bytes 24-25
            val_28 = vals[14]  # bytes 28-29

            entry_data = {
                'offset': pos,
                'monster_a': id_a if a_valid else None,
                'monster_a_name': names.get(id_a, '?') if a_valid else None,
                'monster_b': id_b if b_valid else None,
                'monster_b_name': names.get(id_b, '?') if b_valid else None,
                'param': param,
                'flags': hex(flags),
                'extra': extra,
                'extra_name': names.get(extra) if extra in valid_ids and 1 <= extra <= 123 else None,
                'position': {'x': x, 'y': y, 'z': z},
                'val_24': val_24,
                'val_28': val_28,
                'raw_hex': entry.hex(),
            }
            entries.append(entry_data)
            pos += 32  # Skip to next entry
        else:
            pos += 1

    return entries


def group_by_region(entries):
    """Group spawn entries by 1MB regions."""
    by_region = defaultdict(list)
    for e in entries:
        mb = e['offset'] // (1024 * 1024)
        by_region[mb].append(e)
    return dict(sorted(by_region.items()))


def main():
    print("=" * 70)
    print("  SPAWN ENTRY PARSER")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    names = load_monsters()
    print(f"Loaded {len(names)} monster names")

    # Find level name regions for reference
    print("\n[1] Finding level name locations...")
    regions = find_level_regions(data)
    for offset, name in regions:
        print(f"  {hex(offset)}: {name}")

    # Find all spawn entries
    print("\n[2] Scanning for spawn entries (FFFFFFFF...FFFF pattern)...")
    entries = find_spawn_entries(data, names)
    print(f"\nFound {len(entries)} spawn entries total!")

    # Group by region
    by_region = group_by_region(entries)

    print(f"\n[3] Entries by MB region:")
    for mb, region_entries in by_region.items():
        # Count unique monsters
        monsters = set()
        for e in region_entries:
            if e['monster_a']:
                monsters.add(e['monster_a_name'])
            if e['monster_b']:
                monsters.add(e['monster_b_name'])
        print(f"  {mb}MB ({hex(mb * 0x100000)}): {len(region_entries)} entries, {len(monsters)} unique monsters")
        if len(monsters) <= 15:
            print(f"    Monsters: {', '.join(sorted(monsters))}")

    # Show sample entries from each region
    print(f"\n[4] Sample entries per region:")
    for mb, region_entries in by_region.items():
        print(f"\n  --- {mb}MB ({hex(mb * 0x100000)}) - {len(region_entries)} entries ---")
        for e in region_entries[:5]:
            a = f"{e['monster_a_name']}({e['monster_a']})" if e['monster_a'] else "none"
            b = f"{e['monster_b_name']}({e['monster_b']})" if e['monster_b'] else "none"
            extra = f" + {e['extra_name']}({e['extra']})" if e['extra_name'] else ""
            pos = e['position']
            print(f"    {hex(e['offset'])}: {a} + {b}{extra}  pos=({pos['x']},{pos['y']},{pos['z']}) flags={e['flags']} param={e['param']}")
        if len(region_entries) > 5:
            print(f"    ... ({len(region_entries) - 5} more)")

    # Save full results
    output_file = Path(__file__).parent / "spawn_entries.json"

    # Convert for JSON
    json_entries = []
    for e in entries:
        je = dict(e)
        je['offset'] = hex(e['offset'])
        json_entries.append(je)

    results = {
        'total_entries': len(entries),
        'entries_by_region': {
            f"{mb}MB": {
                'count': len(ents),
                'offset_range': f"{hex(ents[0]['offset'])} - {hex(ents[-1]['offset'])}",
                'unique_monsters': sorted(set(
                    [e['monster_a_name'] for e in ents if e['monster_a_name']] +
                    [e['monster_b_name'] for e in ents if e['monster_b_name']]
                ))
            }
            for mb, ents in by_region.items()
        },
        'entries': json_entries
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\nResults saved to {output_file}")
    print("=" * 70)


if __name__ == '__main__':
    main()
