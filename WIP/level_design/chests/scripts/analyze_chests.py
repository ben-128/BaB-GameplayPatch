"""
analyze_chests.py
Analyze chest data: locations, contents, and conditions

Usage: py -3 analyze_chests.py
"""

from pathlib import Path
import struct
import json

SCRIPT_DIR = Path(__file__).parent.parent.parent.parent  # Remonte à WIP/
BLAZE_ALL = SCRIPT_DIR / "work" / "BLAZE.ALL"

def load_items_database():
    """Load items database for chest content identification"""
    items_file = SCRIPT_DIR / "items" / "all_items_clean.json"

    if not items_file.exists():
        print("Warning: Items database not found")
        return []

    with open(items_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('items', [])

def find_chest_keywords(data):
    """Find all chest-related text references"""
    chest_keywords = [
        b'treasure chest',
        b'Treasure chest',
        b'steel chest',
        b'Steel chest',
        b'locked chest',
        b'sealed chest'
    ]

    results = []
    for keyword in chest_keywords:
        offset = 0
        while True:
            pos = data.find(keyword, offset)
            if pos == -1:
                break

            # Get surrounding context
            start = max(0, pos - 100)
            end = min(len(data), pos + 200)
            context = data[start:end]

            # Extract the full sentence
            try:
                text = context.decode('ascii', errors='ignore')
                # Find sentence boundaries
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword.decode('ascii', errors='ignore').lower() in sentence.lower():
                        results.append({
                            'offset': hex(pos),
                            'keyword': keyword.decode('ascii'),
                            'context': sentence.strip()
                        })
                        break
            except:
                pass

            offset = pos + 1

    return results

def find_key_references(data):
    """Find key items that open chests"""
    key_patterns = [
        b'Key',
        b'key',
        b'opens',
        b'unlock'
    ]

    keys = []

    # Look for key descriptions
    for i in range(len(data) - 100):
        chunk = data[i:i+100]
        if b'Key' in chunk and (b'open' in chunk or b'unlock' in chunk):
            try:
                text = chunk.decode('ascii', errors='ignore')
                if len(text.strip()) > 10:
                    keys.append({
                        'offset': hex(i),
                        'description': text[:80].strip()
                    })
            except:
                pass

    return keys[:50]  # Limit results

def analyze_chest_structures(data):
    """
    Try to find binary structures that might represent chests
    Typical chest structure might contain:
    - Position (x, y, z) - 6 bytes
    - Item ID - 2 bytes
    - Quantity - 2 bytes
    - Locked flag - 1-2 bytes
    - Key requirement - 2 bytes
    Total: ~14-16 bytes per chest
    """

    # Known item IDs from items database
    items = load_items_database()
    item_ids = set()

    for item in items:
        item_id = item.get('id')
        if item_id is not None:
            item_ids.add(item_id)

    print(f"Loaded {len(item_ids)} item IDs for reference")

    # Search for potential chest structures
    candidates = []

    # Sample key offsets where chests might be
    search_zones = [
        (0x100000, 0x200000),  # Zone 1-2MB
        (0x500000, 0x600000),  # Zone 5-6MB
        (0x800000, 0x900000),  # Zone 8-9MB
    ]

    for start, end in search_zones:
        if end > len(data):
            continue

        print(f"\nSearching zone {hex(start)} - {hex(end)}...")

        # Look for structures with item IDs
        for i in range(start, end - 16, 4):
            try:
                # Try to read as potential chest structure
                # Format hypothesis: [x, y, z, item_id, quantity, flags]
                x = struct.unpack_from('<h', data, i)[0]
                y = struct.unpack_from('<h', data, i+2)[0]
                z = struct.unpack_from('<h', data, i+4)[0]
                item_id = struct.unpack_from('<H', data, i+6)[0]
                quantity = struct.unpack_from('<H', data, i+8)[0]
                flags = struct.unpack_from('<H', data, i+10)[0]

                # Validate coordinates (reasonable ranges)
                if not all(-8192 <= coord <= 8192 for coord in [x, y, z]):
                    continue

                # Check if item_id exists
                if item_id not in item_ids:
                    continue

                # Quantity should be reasonable (1-99)
                if not (1 <= quantity <= 99):
                    continue

                # Found a potential chest!
                candidates.append({
                    'offset': hex(i),
                    'position': {'x': x, 'y': y, 'z': z},
                    'item_id': item_id,
                    'quantity': quantity,
                    'flags': hex(flags),
                    'raw_hex': data[i:i+16].hex()
                })

                if len(candidates) >= 100:
                    break
            except:
                pass

        if len(candidates) >= 100:
            break

    return candidates

def map_items_to_chests(chests, items):
    """Map item IDs to item names"""
    item_map = {item['id']: item for item in items}

    for chest in chests:
        item_id = chest.get('item_id')
        if item_id in item_map:
            item = item_map[item_id]
            chest['item_name'] = item.get('name', 'Unknown')
            chest['item_type'] = item.get('type', 'Unknown')
            chest['item_value'] = item.get('price', 0)

def main():
    print("=" * 70)
    print("  CHEST ANALYSIS")
    print("=" * 70)

    print(f"\nReading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes")

    # Load items database
    items = load_items_database()
    print(f"Loaded items database: {len(items)} items")

    # Step 1: Find chest text references
    print("\n[1] TEXT REFERENCES")
    print("-" * 70)
    chest_texts = find_chest_keywords(data)
    print(f"Found {len(chest_texts)} chest text references")

    print("\nSample chest references:")
    for ref in chest_texts[:10]:
        print(f"\n  Offset: {ref['offset']}")
        print(f"  Keyword: {ref['keyword']}")
        print(f"  Context: {ref['context'][:100]}")

    # Step 2: Find key references
    print("\n\n[2] KEY REFERENCES")
    print("-" * 70)
    keys = find_key_references(data)
    print(f"Found {len(keys)} key references")

    print("\nKey descriptions:")
    for key in keys[:10]:
        print(f"\n  {key['offset']}: {key['description']}")

    # Step 3: Find chest structures
    print("\n\n[3] CHEST STRUCTURE ANALYSIS")
    print("-" * 70)
    print("Searching for potential chest structures...")
    chests = analyze_chest_structures(data)

    print(f"\nFound {len(chests)} potential chest structures")

    if chests:
        # Map items
        map_items_to_chests(chests, items)

        print("\nFirst 20 potential chests:")
        for chest in chests[:20]:
            print(f"\n  Offset: {chest['offset']}")
            print(f"  Position: ({chest['position']['x']}, {chest['position']['y']}, {chest['position']['z']})")
            print(f"  Item ID: {chest['item_id']} - {chest.get('item_name', 'Unknown')}")
            print(f"  Quantity: {chest['quantity']}")
            print(f"  Flags: {chest['flags']}")

    # Save results
    output_file = Path(__file__).parent.parent / "data" / "chest_analysis.json"
    results = {
        'text_references': chest_texts,
        'key_references': keys[:30],  # Limit
        'chest_structures': chests,
        'summary': {
            'total_text_refs': len(chest_texts),
            'total_keys': len(keys),
            'total_chests_found': len(chests)
        }
    }

    print(f"\n\nSaving results to {output_file.name}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Create CSV for Unity
    csv_file = Path(__file__).parent.parent / "data" / "chest_positions.csv"
    if chests:
        with open(csv_file, 'w') as f:
            f.write("offset,x,y,z,item_id,item_name,quantity,flags\n")
            for chest in chests:
                f.write(f"{chest['offset']},{chest['position']['x']},{chest['position']['y']},{chest['position']['z']},")
                f.write(f"{chest['item_id']},{chest.get('item_name', 'Unknown')},{chest['quantity']},{chest['flags']}\n")

        print(f"Chest positions saved to: {csv_file.name}")
        print("  -> Can be imported into Unity for visualization")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Text references: {len(chest_texts)}")
    print(f"Key references: {len(keys)}")
    print(f"Potential chest structures: {len(chests)}")
    print(f"\nFiles created:")
    print(f"  - chest_analysis.json")
    if chests:
        print(f"  - chest_positions.csv (Unity-ready)")
    print("="*70)

if __name__ == '__main__':
    main()
