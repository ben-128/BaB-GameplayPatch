"""
find_spawn_tables.py
Smart analysis to find real monster spawn/encounter tables in BLAZE.ALL

Instead of brute-force scanning for individual monster IDs (which produces
tons of false positives, especially for ID 0), this script looks for:
1. Clusters of DIVERSE monster IDs in small regions
2. Regular-stride tables where valid IDs appear at fixed intervals
3. Encounter-table-like structures (count + array of entries)

Usage: py -3 find_spawn_tables.py
"""

import struct
import json
from pathlib import Path
from collections import defaultdict

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "Blaze & Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
# Fallback to output copy
if not BLAZE_ALL.exists():
    BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Valid monster IDs (from _index.json: 0-84, 86, 88, 90-123)
VALID_IDS = set(range(0, 85)) | {86, 88} | set(range(90, 124))
# Non-zero IDs only (to avoid false positives from null bytes)
VALID_IDS_NONZERO = VALID_IDS - {0}
# Max valid ID
MAX_MONSTER_ID = 123

# Load monster names
def load_monster_names():
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


def find_id_clusters(data, window_size=128, min_unique=3, min_nonzero=2):
    """
    Find regions where multiple different valid monster IDs appear close together.
    This is the most reliable way to find encounter/spawn tables.

    Args:
        window_size: Size of sliding window in bytes
        min_unique: Minimum unique monster IDs (including 0) in window
        min_nonzero: Minimum non-zero unique monster IDs in window
    """
    print(f"\n[CLUSTER SEARCH] Window={window_size}B, min_unique={min_unique}, min_nonzero={min_nonzero}")

    clusters = []
    file_len = len(data)
    step = window_size // 2  # 50% overlap

    for start in range(0, file_len - window_size, step):
        window = data[start:start + window_size]

        # Read all uint16 values at even offsets
        ids_found = set()
        ids_nonzero = set()
        id_positions = []

        for i in range(0, len(window) - 1, 2):
            val = struct.unpack_from('<H', window, i)[0]
            if val in VALID_IDS:
                ids_found.add(val)
                if val > 0:
                    ids_nonzero.add(val)
                    id_positions.append((i, val))

        if len(ids_found) >= min_unique and len(ids_nonzero) >= min_nonzero:
            clusters.append({
                'offset': start,
                'unique_ids': sorted(ids_found),
                'nonzero_ids': sorted(ids_nonzero),
                'num_unique': len(ids_found),
                'num_nonzero': len(ids_nonzero),
                'id_positions': id_positions,
                'raw_hex': window.hex()
            })

    # Merge overlapping clusters
    merged = []
    for c in clusters:
        if merged and c['offset'] - merged[-1]['offset'] < window_size:
            # Merge: keep the one with more unique IDs
            if c['num_nonzero'] > merged[-1]['num_nonzero']:
                merged[-1] = c
            elif c['num_nonzero'] == merged[-1]['num_nonzero'] and c['num_unique'] > merged[-1]['num_unique']:
                merged[-1] = c
        else:
            merged.append(c)

    return merged


def find_stride_tables(data, min_entries=4):
    """
    Find tables where valid monster IDs appear at regular intervals (strides).
    Tests various stride sizes and field offsets within the stride.
    """
    print(f"\n[STRIDE TABLE SEARCH] min_entries={min_entries}")

    strides_to_test = [4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48]
    file_len = len(data)
    tables = []

    # Don't search the entire file - focus on known level data areas
    # and also scan broadly for unknown areas
    search_regions = [
        (0x000000, 0x100000, "First 1MB (game data)"),
        (0x100000, 0x300000, "1-3MB (level zone)"),
        (0x300000, 0x500000, "3-5MB (level zone)"),
        (0x500000, 0x700000, "5-7MB (level zone)"),
        (0x700000, 0x900000, "7-9MB (level zone)"),
        (0x900000, 0xB00000, "9-11MB (level/data zone)"),
        (0x00B00000, 0x01000000, "11-16MB"),
        (0x01000000, 0x01800000, "16-24MB"),
        (0x01800000, 0x02000000, "24-32MB"),
        (0x02000000, 0x02C00000, "32-44MB"),
    ]

    for region_start, region_end, region_name in search_regions:
        if region_start >= file_len:
            break
        region_end = min(region_end, file_len)

        for stride in strides_to_test:
            # Try each possible uint16 offset within the stride
            for field_offset in range(0, stride, 2):
                best_run_start = None
                best_run_length = 0
                best_run_ids = []

                current_start = None
                current_length = 0
                current_ids = []

                pos = region_start + field_offset
                while pos < region_end - 1:
                    val = struct.unpack_from('<H', data, pos)[0]

                    if val in VALID_IDS_NONZERO:
                        if current_start is None:
                            current_start = pos
                            current_ids = []
                        current_length += 1
                        current_ids.append(val)
                    else:
                        if current_length >= min_entries:
                            # Check we have at least 2 different IDs
                            if len(set(current_ids)) >= 2:
                                if current_length > best_run_length:
                                    best_run_start = current_start
                                    best_run_length = current_length
                                    best_run_ids = current_ids[:]
                        current_start = None
                        current_length = 0
                        current_ids = []

                    pos += stride

                # Check final run
                if current_length >= min_entries and len(set(current_ids)) >= 2:
                    if current_length > best_run_length:
                        best_run_start = current_start
                        best_run_length = current_length
                        best_run_ids = current_ids[:]

                if best_run_length >= min_entries:
                    tables.append({
                        'offset': best_run_start,
                        'region': region_name,
                        'stride': stride,
                        'field_offset': field_offset,
                        'num_entries': best_run_length,
                        'monster_ids': best_run_ids,
                        'unique_ids': sorted(set(best_run_ids)),
                        'num_unique': len(set(best_run_ids)),
                    })

    # Deduplicate: same offset region, keep best stride
    tables.sort(key=lambda t: (-t['num_entries'], -t['num_unique']))

    # Remove duplicates (same data region found with different parameters)
    seen_offsets = set()
    unique_tables = []
    for t in tables:
        # Round offset to nearest 16 bytes for dedup
        key = t['offset'] // 16
        if key not in seen_offsets:
            seen_offsets.add(key)
            unique_tables.append(t)

    return unique_tables[:50]  # Top 50


def find_counted_arrays(data):
    """
    Look for patterns like: [count_byte/word] followed by [count] monster IDs.
    Common in PS1 game data structures.
    """
    print(f"\n[COUNTED ARRAY SEARCH]")

    results = []
    file_len = len(data)

    for pos in range(0, file_len - 64):
        # Try count as uint8
        count = data[pos]
        if 2 <= count <= 20:
            # Check if the next `count` uint16 values are valid monster IDs
            ids = []
            valid = True
            has_nonzero = False
            for j in range(count):
                id_offset = pos + 1 + j * 2
                if id_offset + 1 >= file_len:
                    valid = False
                    break
                val = struct.unpack_from('<H', data, id_offset)[0]
                if val not in VALID_IDS or val > MAX_MONSTER_ID:
                    valid = False
                    break
                ids.append(val)
                if val > 0:
                    has_nonzero = True

            if valid and has_nonzero and len(set(ids)) >= 2:
                results.append({
                    'offset': pos,
                    'count_type': 'uint8',
                    'count': count,
                    'ids': ids,
                    'unique_ids': sorted(set(ids)),
                    'raw_hex': data[pos:pos + 1 + count * 2].hex()
                })

        # Try count as uint16 (at even positions only)
        if pos % 2 == 0 and pos + 1 < file_len:
            count16 = struct.unpack_from('<H', data, pos)[0]
            if 2 <= count16 <= 30:
                ids = []
                valid = True
                has_nonzero = False
                for j in range(count16):
                    id_offset = pos + 2 + j * 2
                    if id_offset + 1 >= file_len:
                        valid = False
                        break
                    val = struct.unpack_from('<H', data, id_offset)[0]
                    if val not in VALID_IDS or val > MAX_MONSTER_ID:
                        valid = False
                        break
                    ids.append(val)
                    if val > 0:
                        has_nonzero = True

                if valid and has_nonzero and len(set(ids)) >= 2:
                    results.append({
                        'offset': pos,
                        'count_type': 'uint16',
                        'count': count16,
                        'ids': ids,
                        'unique_ids': sorted(set(ids)),
                        'raw_hex': data[pos:pos + 2 + count16 * 2].hex()
                    })

    # Deduplicate overlapping results
    results.sort(key=lambda r: (-r['count'], -len(r['unique_ids'])))
    seen = set()
    unique = []
    for r in results:
        key = r['offset'] // 4
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:50]


def find_nonzero_id_sequences(data):
    """
    Simple but effective: find sequences of non-zero valid monster IDs
    at uint16 boundaries (no stride, just consecutive uint16 values).
    """
    print(f"\n[CONSECUTIVE ID SEARCH]")

    results = []
    file_len = len(data)

    current_start = None
    current_ids = []

    for pos in range(0, file_len - 1, 2):
        val = struct.unpack_from('<H', data, pos)[0]

        if val in VALID_IDS_NONZERO:
            if current_start is None:
                current_start = pos
                current_ids = []
            current_ids.append(val)
        else:
            if len(current_ids) >= 3 and len(set(current_ids)) >= 2:
                results.append({
                    'offset': current_start,
                    'count': len(current_ids),
                    'ids': current_ids[:],
                    'unique_ids': sorted(set(current_ids)),
                    'num_unique': len(set(current_ids)),
                    'raw_hex': data[current_start:current_start + len(current_ids) * 2].hex()
                })
            current_start = None
            current_ids = []

    results.sort(key=lambda r: (-r['num_unique'], -r['count']))
    return results[:50]


def dump_region_analysis(data, offset, size, names):
    """Dump a region with multiple interpretations for manual analysis."""
    region = data[offset:offset + size]

    lines = []
    lines.append(f"  Offset: {hex(offset)} - {hex(offset + size)}")
    lines.append(f"  Raw hex: {region.hex()}")

    # Show as uint16 values
    vals = []
    for i in range(0, len(region) - 1, 2):
        v = struct.unpack_from('<H', region, i)[0]
        vals.append(v)
    lines.append(f"  uint16: {vals}")

    # Highlight monster IDs
    monster_hits = []
    for i, v in enumerate(vals):
        if v in VALID_IDS and v <= MAX_MONSTER_ID:
            name = names.get(v, f"ID_{v}")
            monster_hits.append(f"  [{i*2}] = {v} ({name})")
    if monster_hits:
        lines.append("  Monster IDs found:")
        lines.extend(monster_hits)

    # Show as uint8 values
    bytes_list = list(region)
    lines.append(f"  uint8: {bytes_list}")

    # Show as int16 (signed)
    signed = []
    for i in range(0, len(region) - 1, 2):
        v = struct.unpack_from('<h', region, i)[0]
        signed.append(v)
    lines.append(f"  int16: {signed}")

    return '\n'.join(lines)


def main():
    print("=" * 70)
    print("  SMART SPAWN TABLE FINDER")
    print("=" * 70)

    # Load BLAZE.ALL
    print(f"\nReading {BLAZE_ALL}...")
    if not BLAZE_ALL.exists():
        print(f"ERROR: File not found: {BLAZE_ALL}")
        return

    data = BLAZE_ALL.read_bytes()
    print(f"Size: {len(data):,} bytes ({len(data) / 1024 / 1024:.1f} MB)")

    # Load monster names
    names = load_monster_names()
    print(f"Monster names loaded: {len(names)}")
    print(f"Valid IDs (non-zero): {len(VALID_IDS_NONZERO)} (range 1-{MAX_MONSTER_ID})")

    all_results = {}

    # =========================================================================
    # Method 1: Cluster search (most reliable)
    # =========================================================================
    print("\n" + "=" * 70)
    print("[1/4] CLUSTER SEARCH - Regions with diverse monster IDs")
    print("=" * 70)

    clusters = find_id_clusters(data, window_size=128, min_unique=3, min_nonzero=2)
    print(f"\nFound {len(clusters)} candidate clusters")

    for i, c in enumerate(clusters[:30]):
        id_names = [names.get(mid, f"ID_{mid}") for mid in c['nonzero_ids']]
        print(f"\n  #{i+1} @ {hex(c['offset'])} - {c['num_nonzero']} unique monsters: {', '.join(id_names)}")
        print(dump_region_analysis(data, c['offset'], 128, names))

    all_results['clusters'] = [{
        'offset': hex(c['offset']),
        'num_unique': c['num_unique'],
        'num_nonzero': c['num_nonzero'],
        'nonzero_ids': c['nonzero_ids'],
        'nonzero_names': [names.get(mid, f"ID_{mid}") for mid in c['nonzero_ids']],
    } for c in clusters]

    # =========================================================================
    # Method 2: Stride tables
    # =========================================================================
    print("\n" + "=" * 70)
    print("[2/4] STRIDE TABLE SEARCH - Regular-interval monster ID patterns")
    print("=" * 70)

    stride_tables = find_stride_tables(data, min_entries=4)
    print(f"\nFound {len(stride_tables)} candidate stride tables")

    for i, t in enumerate(stride_tables[:20]):
        id_names = [names.get(mid, f"ID_{mid}") for mid in t['unique_ids']]
        print(f"\n  #{i+1} @ {hex(t['offset'])} [{t['region']}]")
        print(f"    Stride: {t['stride']}B, field at +{t['field_offset']}, {t['num_entries']} entries")
        print(f"    Monster IDs: {t['monster_ids']}")
        print(f"    Unique: {', '.join(id_names)}")
        # Dump the full table region
        table_size = t['stride'] * t['num_entries']
        print(dump_region_analysis(data, t['offset'] - t['field_offset'], min(table_size, 256), names))

    all_results['stride_tables'] = [{
        'offset': hex(t['offset']),
        'region': t['region'],
        'stride': t['stride'],
        'field_offset': t['field_offset'],
        'num_entries': t['num_entries'],
        'monster_ids': t['monster_ids'],
        'unique_names': [names.get(mid, f"ID_{mid}") for mid in t['unique_ids']],
    } for t in stride_tables]

    # =========================================================================
    # Method 3: Counted arrays
    # =========================================================================
    print("\n" + "=" * 70)
    print("[3/4] COUNTED ARRAY SEARCH - [count] + [monster_id] * count")
    print("=" * 70)

    counted = find_counted_arrays(data)
    print(f"\nFound {len(counted)} candidate counted arrays")

    for i, c in enumerate(counted[:20]):
        id_names = [names.get(mid, f"ID_{mid}") for mid in c['unique_ids']]
        print(f"\n  #{i+1} @ {hex(c['offset'])} - count={c['count']} ({c['count_type']})")
        print(f"    IDs: {c['ids']}")
        print(f"    Unique: {', '.join(id_names)}")
        print(f"    Raw: {c['raw_hex']}")

    all_results['counted_arrays'] = [{
        'offset': hex(c['offset']),
        'count_type': c['count_type'],
        'count': c['count'],
        'ids': c['ids'],
        'unique_names': [names.get(mid, f"ID_{mid}") for mid in c['unique_ids']],
        'raw_hex': c['raw_hex']
    } for c in counted]

    # =========================================================================
    # Method 4: Consecutive non-zero ID sequences
    # =========================================================================
    print("\n" + "=" * 70)
    print("[4/4] CONSECUTIVE ID SEARCH - Sequences of valid monster IDs")
    print("=" * 70)

    sequences = find_nonzero_id_sequences(data)
    print(f"\nFound {len(sequences)} candidate sequences")

    for i, s in enumerate(sequences[:20]):
        id_names = [names.get(mid, f"ID_{mid}") for mid in s['unique_ids']]
        print(f"\n  #{i+1} @ {hex(s['offset'])} - {s['count']} consecutive IDs, {s['num_unique']} unique")
        print(f"    IDs: {s['ids']}")
        print(f"    Names: {', '.join(id_names)}")
        # Show more context (bytes before and after)
        ctx_start = max(0, s['offset'] - 16)
        ctx_end = min(len(data), s['offset'] + s['count'] * 2 + 16)
        print(f"    Context: {data[ctx_start:ctx_end].hex()}")

    all_results['consecutive_sequences'] = [{
        'offset': hex(s['offset']),
        'count': s['count'],
        'ids': s['ids'],
        'num_unique': s['num_unique'],
        'unique_names': [names.get(mid, f"ID_{mid}") for mid in s['unique_ids']],
    } for s in sequences]

    # =========================================================================
    # Save results
    # =========================================================================
    output_file = SCRIPT_DIR / "spawn_table_candidates.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Clusters (diverse IDs in region):  {len(clusters)}")
    print(f"Stride tables (regular intervals): {len(stride_tables)}")
    print(f"Counted arrays ([count] + IDs):    {len(counted)}")
    print(f"Consecutive ID sequences:          {len(sequences)}")
    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == '__main__':
    main()
