"""
analyze_doors.py
Analyze doors, gates, and portals: positions, types, keys, and conditions

Usage: py -3 analyze_doors.py
"""

from pathlib import Path
import struct
import json
import re

SCRIPT_DIR = Path(__file__).parent.parent.parent.parent  # Remonte à WIP/
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def find_door_references(data):
    """Find all door-related text and categorize them"""
    door_types = {
        'magic_locked': [],
        'demon_engraved': [],
        'ghost_engraved': [],
        'key_locked': [],
        'generic': []
    }

    # Search patterns
    patterns = {
        'magic_locked': [b'magic', b'Magic', b'locked by magic'],
        'demon_engraved': [b'demon engraving', b'demon-engraved', b'Demon'],
        'ghost_engraved': [b'ghost engraving', b'ghost-engraved', b'Ghost'],
        'key_locked': [b'locked', b'Locked', b'key']
    }

    # Find all "door" occurrences
    offset = 0
    while True:
        pos = data.find(b'door', offset)
        if pos == -1:
            break

        # Get context
        start = max(0, pos - 50)
        end = min(len(data), pos + 100)
        context = data[start:end]

        try:
            text = context.decode('ascii', errors='ignore')

            # Categorize
            categorized = False
            for dtype, patterns_list in patterns.items():
                for pattern in patterns_list:
                    if pattern.lower() in context.lower():
                        door_types[dtype].append({
                            'offset': hex(pos),
                            'context': text.strip()[:100]
                        })
                        categorized = True
                        break
                if categorized:
                    break

            if not categorized:
                door_types['generic'].append({
                    'offset': hex(pos),
                    'context': text.strip()[:100]
                })

        except:
            pass

        offset = pos + 1

    return door_types

def find_gate_references(data):
    """Find gates and Gate Crystals"""
    gates = {
        'gate_crystals': [],
        'gates': []
    }

    # Find Gate Crystal references
    offset = 0
    while True:
        pos = data.find(b'Gate Crystal', offset)
        if pos == -1:
            break

        start = max(0, pos - 50)
        end = min(len(data), pos + 100)

        try:
            text = data[start:end].decode('ascii', errors='ignore')
            gates['gate_crystals'].append({
                'offset': hex(pos),
                'context': text.strip()[:100]
            })
        except:
            pass

        offset = pos + 1

    # Find general gate references
    offset = 0
    while True:
        pos = data.find(b'gate', offset)
        if pos == -1:
            break

        # Skip if it's part of "Gate Crystal"
        if data[pos:pos+12] == b'Gate Crystal':
            offset = pos + 1
            continue

        start = max(0, pos - 50)
        end = min(len(data), pos + 100)

        try:
            text = data[start:end].decode('ascii', errors='ignore')
            if len(gates['gates']) < 50:  # Limit
                gates['gates'].append({
                    'offset': hex(pos),
                    'context': text.strip()[:100]
                })
        except:
            pass

        offset = pos + 1

    return gates

def find_portal_references(data):
    """Find portal references and their destinations"""
    portals = []

    offset = 0
    while True:
        pos = data.find(b'portal', offset)
        if pos == -1:
            break

        start = max(0, pos - 50)
        end = min(len(data), pos + 150)

        try:
            text = data[start:end].decode('ascii', errors='ignore')

            # Try to extract destination
            destination = None
            if 'Underlevel' in text:
                match = re.search(r'(\d+)\w+\s+Underlevel', text)
                if match:
                    destination = f"{match.group(1)}st Underlevel"

            portals.append({
                'offset': hex(pos),
                'context': text.strip()[:120],
                'destination': destination
            })

        except:
            pass

        offset = pos + 1

        if len(portals) >= 100:  # Limit
            break

    return portals

def find_key_items(data):
    """Find all key items and what they open"""
    keys = []

    # Common key patterns
    key_names = [
        b'Key',
        b'key'
    ]

    seen_offsets = set()

    for key_pattern in key_names:
        offset = 0
        while True:
            pos = data.find(key_pattern, offset)
            if pos == -1:
                break

            if pos in seen_offsets:
                offset = pos + 1
                continue

            # Get extended context
            start = max(0, pos - 30)
            end = min(len(data), pos + 150)
            context = data[start:end]

            try:
                text = context.decode('ascii', errors='ignore')

                # Check if it's actually a key description
                if 'open' in text.lower() or 'unlock' in text.lower() or 'door' in text.lower():
                    # Extract key name (usually before the description)
                    lines = text.split('\n')
                    key_name = None
                    description = None

                    for line in lines:
                        if 'Key' in line or 'key' in line:
                            if len(line.strip()) < 50 and len(line.strip()) > 3:
                                key_name = line.strip()
                            else:
                                description = line.strip()[:100]

                    if key_name:
                        keys.append({
                            'offset': hex(pos),
                            'name': key_name,
                            'description': description,
                            'full_context': text[:150]
                        })

                        seen_offsets.add(pos)

            except:
                pass

            offset = pos + 1

            if len(keys) >= 50:
                break

    return keys

def find_door_structures(data):
    """
    Try to find binary door structures
    Hypothesis: door structure might contain:
    - Position (x, y, z) - 6 bytes
    - Type (locked/unlocked/magic) - 2 bytes
    - Key ID required - 2 bytes
    - Destination level ID - 2 bytes
    - State flags - 2 bytes
    Total: ~14-16 bytes
    """

    doors = []

    # Search in level data zones
    search_zones = [
        (0x100000, 0x200000),
        (0x500000, 0x600000)
    ]

    for start, end in search_zones:
        if end > len(data):
            continue

        for i in range(start, end - 16, 4):
            try:
                # Read potential door structure
                x = struct.unpack_from('<h', data, i)[0]
                y = struct.unpack_from('<h', data, i+2)[0]
                z = struct.unpack_from('<h', data, i+4)[0]

                # Validate coordinates
                if not all(-8192 <= coord <= 8192 for coord in [x, y, z]):
                    continue

                door_type = struct.unpack_from('<H', data, i+6)[0]
                key_id = struct.unpack_from('<H', data, i+8)[0]
                dest_id = struct.unpack_from('<H', data, i+10)[0]
                flags = struct.unpack_from('<H', data, i+12)[0]

                # Heuristics for door detection
                # - door_type should be small (0-10)
                # - key_id reasonable (0-100)
                # - dest_id reasonable (0-50)
                if door_type > 10 or key_id > 100 or dest_id > 50:
                    continue

                # Check if following bytes look like another structure
                # (tables have repeated patterns)
                next_x = struct.unpack_from('<h', data, i+16)[0] if i+18 < len(data) else 0

                if -8192 <= next_x <= 8192:
                    # Possibly part of a door table!
                    doors.append({
                        'offset': hex(i),
                        'position': {'x': x, 'y': y, 'z': z},
                        'type': door_type,
                        'key_id': key_id,
                        'destination_id': dest_id,
                        'flags': hex(flags),
                        'type_description': interpret_door_type(door_type),
                        'raw_hex': data[i:i+16].hex()
                    })

                    if len(doors) >= 50:
                        break

            except:
                pass

        if len(doors) >= 50:
            break

    return doors

def interpret_door_type(dtype):
    """Interpret door type value"""
    type_map = {
        0: 'Unlocked',
        1: 'Key Locked',
        2: 'Magic Locked',
        3: 'Demon Engraved',
        4: 'Ghost Engraved',
        5: 'Event Locked',
        6: 'Boss Door',
        7: 'One-way Door'
    }
    return type_map.get(dtype, f'Unknown ({dtype})')

def main():
    print("=" * 70)
    print("  DOOR & GATE ANALYSIS")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Step 1: Door references
    print("\n[1] DOOR REFERENCES BY TYPE")
    print("-" * 70)
    door_types = find_door_references(data)

    for dtype, doors in door_types.items():
        print(f"\n{dtype.upper().replace('_', ' ')}: {len(doors)} references")
        if doors:
            print(f"  Sample: {doors[0]['context'][:80]}")

    # Step 2: Gate references
    print("\n[2] GATE REFERENCES")
    print("-" * 70)
    gates = find_gate_references(data)
    print(f"Gate Crystals: {len(gates['gate_crystals'])} references")
    print(f"Generic Gates: {len(gates['gates'])} references")

    if gates['gate_crystals']:
        print(f"\nSample Gate Crystal: {gates['gate_crystals'][0]['context'][:80]}")

    # Step 3: Portal references
    print("\n[3] PORTAL REFERENCES")
    print("-" * 70)
    portals = find_portal_references(data)
    print(f"Found {len(portals)} portal references")

    portals_with_dest = [p for p in portals if p['destination']]
    print(f"Portals with known destinations: {len(portals_with_dest)}")

    if portals_with_dest:
        print("\nPortals with destinations:")
        for portal in portals_with_dest[:10]:
            print(f"  {portal['offset']}: -> {portal['destination']}")

    # Step 4: Key items
    print("\n[4] KEY ITEMS")
    print("-" * 70)
    keys = find_key_items(data)
    print(f"Found {len(keys)} key items")

    print("\nKey items found:")
    for key in keys[:15]:
        print(f"\n  {key['offset']}: {key['name']}")
        if key['description']:
            print(f"    {key['description']}")

    # Step 5: Door structures
    print("\n[5] DOOR STRUCTURE ANALYSIS")
    print("-" * 70)
    door_structures = find_door_structures(data)
    print(f"Found {len(door_structures)} potential door structures")

    if door_structures:
        print("\nFirst 10 door structures:")
        for door in door_structures[:10]:
            print(f"\n  {door['offset']}")
            print(f"    Position: ({door['position']['x']}, {door['position']['y']}, {door['position']['z']})")
            print(f"    Type: {door['type_description']}")
            print(f"    Key ID: {door['key_id']}")
            print(f"    Destination: {door['destination_id']}")

    # Save results
    output_file = Path(__file__).parent.parent / "data" / "door_analysis.json"
    results = {
        'door_types': door_types,
        'gates': gates,
        'portals': portals[:50],  # Limit
        'keys': keys,
        'door_structures': door_structures,
        'summary': {
            'total_door_refs': sum(len(v) for v in door_types.values()),
            'total_gates': len(gates['gates']),
            'total_gate_crystals': len(gates['gate_crystals']),
            'total_portals': len(portals),
            'total_keys': len(keys),
            'total_door_structures': len(door_structures)
        }
    }

    print(f"\n\nSaving results to {output_file.name}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Create CSV for Unity
    if door_structures:
        csv_file = Path(__file__).parent.parent / "data" / "door_positions.csv"
        with open(csv_file, 'w') as f:
            f.write("offset,x,y,z,type,type_desc,key_id,dest_id,flags\n")
            for door in door_structures:
                f.write(f"{door['offset']},{door['position']['x']},{door['position']['y']},{door['position']['z']},")
                f.write(f"{door['type']},{door['type_description']},{door['key_id']},{door['destination_id']},{door['flags']}\n")

        print(f"Door positions saved to: {csv_file.name}")
        print("  -> Can be imported into Unity for visualization")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Door text references: {sum(len(v) for v in door_types.values())}")
    print(f"  - Magic locked: {len(door_types['magic_locked'])}")
    print(f"  - Demon engraved: {len(door_types['demon_engraved'])}")
    print(f"  - Ghost engraved: {len(door_types['ghost_engraved'])}")
    print(f"  - Key locked: {len(door_types['key_locked'])}")
    print(f"  - Generic: {len(door_types['generic'])}")
    print(f"Gate Crystals: {len(gates['gate_crystals'])}")
    print(f"Portals: {len(portals)}")
    print(f"Key items: {len(keys)}")
    print(f"Door structures: {len(door_structures)}")
    print(f"\nFiles created:")
    print(f"  - door_analysis.json")
    if door_structures:
        print(f"  - door_positions.csv (Unity-ready)")
    print("="*70)

if __name__ == '__main__':
    main()
