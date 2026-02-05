#!/usr/bin/env python3
"""
Blaze & Blade: Eternal Quest - Spawn Table Finder
==================================================
Searches BLAZE.ALL for regions where monster IDs from the same zone
cluster together as uint16 values. Also investigates what the "source
offset" values from monsters_by_zone.json might mean.

Monster IDs are uint16 (0-123). Zones have known lists of monster IDs.
Goal: find the actual byte offsets of spawn tables in BLAZE.ALL.
"""

import struct
import os
import sys
import array
from collections import defaultdict, Counter

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BLAZE_PATHS = [
    r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL",
    r"D:\projets\Bab_Gameplay_Patch\output\BLAZE.ALL",
]

# Zone definitions
ZONES = {
    "Forest": {
        "source": [0x148, 0x149, 0x14A, 0x14B],
        "ids": [24, 79, 88, 61, 59, 54, 75, 110, 76, 97, 48, 115, 52, 116, 15],
    },
    "Cavern of Death": {
        "source": list(range(0xF86, 0xF94)),
        "ids": [49, 26, 34, 32, 53, 51, 64, 55, 35, 77, 95, 17, 8],
    },
    "Castle Vamp Lower": {
        "source": [0x240, 0x241, 0x242],
        "ids": [112, 90, 123, 46, 31, 104, 105, 69, 21, 20],
    },
    "Castle Vamp Upper": {
        "source": [0x242, 0x243],
        "ids": [113, 80, 98, 103, 19],
    },
    "Tower": {
        "source": list(range(0x196, 0x19A)),
        "ids": [43, 86, 65, 83, 37, 39, 23, 33, 68, 108, 27, 96, 82, 67, 81, 57, 5, 121, 6, 102],
    },
    "Sealed Cave": {
        "source": [0x1DE, 0x1DF],
        "ids": [99, 122, 47, 29, 93, 94, 78, 119, 100, 114, 111, 9, 1, 18],
    },
    "Valley White Wind": {
        "source": [0x25D],
        "ids": [106, 117, 73, 12],
    },
    "Undersea/Lake": {
        "source": [0x269],
        "ids": [28, 120, 14, 13],
    },
    "Hall of Demons": {
        "source": list(range(0x2BE, 0x2C1)),
        "ids": [38, 60, 74, 44, 40, 30, 107, 42, 70, 63, 72, 25, 62, 66, 71, 109, 10, 22, 3, 11, 7, 4, 2, 101],
    },
    "Fire Mountain": {
        "source": [0x102],
        "ids": [16, 0],
    },
}

ALL_MONSTER_IDS = set()
for z in ZONES.values():
    ALL_MONSTER_IDS.update(z["ids"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_blaze():
    for path in BLAZE_PATHS:
        if os.path.isfile(path):
            print(f"Loading: {path}")
            with open(path, "rb") as f:
                data = f.read()
            print(f"  Size: {len(data):,} bytes ({len(data)/1024/1024:.1f} MB)")
            return data, path
    print("ERROR: Could not find BLAZE.ALL")
    sys.exit(1)


def hexdump(data, offset, length=64, prefix="    "):
    lines = []
    for i in range(0, min(length, len(data) - offset), 16):
        if offset + i >= len(data):
            break
        end = min(offset + i + 16, len(data))
        chunk = data[offset + i : end]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{prefix}0x{offset+i:08X}: {hex_part:<48s} {ascii_part}")
    return "\n".join(lines)


def read_u16_le(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def read_u32_le(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def build_u16_array(data):
    """Convert entire file to uint16 LE array for fast searching."""
    # Ensure even length
    if len(data) % 2 != 0:
        data = data + b'\x00'
    arr = array.array('H')
    arr.frombytes(data)
    return arr


# ===========================================================================
# PHASE 1: Investigate what the source offsets mean
# ===========================================================================

def investigate_source_offsets(data):
    print("\n" + "=" * 80)
    print("PHASE 1: INVESTIGATING SOURCE OFFSET MEANINGS")
    print("=" * 80)

    all_offsets = set()
    for z in ZONES.values():
        all_offsets.update(z["source"])
    all_offsets = sorted(all_offsets)
    print(f"\nAll unique source offsets: {[f'0x{o:X}' for o in all_offsets[:15]]}...")
    print(f"Range: 0x{min(all_offsets):X} - 0x{max(all_offsets):X}")

    # Key multipliers
    multipliers = [
        (2048, "x2048 (0x800) - CD sector"),
        (4096, "x4096 (0x1000)"),
        (8192, "x8192 (0x2000)"),
        (0x4000, "x0x4000 (16384)"),
        (0x8000, "x0x8000 (32768)"),
    ]

    file_size = len(data)
    test_offsets = [0x148, 0xF86, 0x240, 0x196, 0x2BE, 0x102]

    print("\n--- Testing key multiplier hypotheses ---")
    for mult, desc in multipliers:
        max_byte = max(all_offsets) * mult
        if max_byte >= file_size:
            print(f"\n  Multiplier {desc}: 0xF93*{mult} = 0x{0xF93*mult:X} > filesize, skipping")
            continue

        print(f"\n  Multiplier {desc} (factor={mult}, 0x{mult:X}):")
        for src_off in test_offsets:
            byte_off = src_off * mult
            if byte_off + 16 > file_size:
                continue
            snippet = data[byte_off:byte_off+16]
            hex_str = " ".join(f"{b:02X}" for b in snippet)
            u16_vals = [struct.unpack_from("<H", snippet, i)[0] for i in range(0, 16, 2)]
            # Check if any are valid monster IDs for the zone
            zone_name = "?"
            zone_ids = set()
            for zn, zd in ZONES.items():
                if src_off in zd["source"]:
                    zone_name = zn
                    zone_ids = set(zd["ids"])
                    break
            monsters_found = [v for v in u16_vals if v in zone_ids]
            marker = f" *** {len(monsters_found)} ZONE MATCHES! ***" if monsters_found else ""
            all_monsters = [v for v in u16_vals if v in ALL_MONSTER_IDS]
            if all_monsters and not monsters_found:
                marker = f" (has monster IDs but wrong zone: {all_monsters})"
            print(f"    0x{src_off:X} ({zone_name}) -> 0x{byte_off:08X}: {hex_str}  u16s={u16_vals}{marker}")

    # Check file header
    print("\n\n--- File header (first 32 bytes) ---")
    print(hexdump(data, 0, 32))
    print(f"  u32[0]=0x{read_u32_le(data,0):08X}  u32[1]=0x{read_u32_le(data,4):08X}  "
          f"u32[2]=0x{read_u32_le(data,8):08X}  u32[3]=0x{read_u32_le(data,12):08X}")

    # Check pointer table at offset 0x10 (16) since header says 0x10
    print("\n--- Checking for pointer/offset table starting at 0x10 ---")
    header_val = read_u32_le(data, 0)  # = 0x10
    if header_val < 0x1000:
        print(f"  Header u32[0] = {header_val} -- might be offset to first data or pointer count")
        print(f"  Data at 0x10:")
        print(hexdump(data, 0x10, 64))

    # Look for a TOC in first 64KB
    print("\n\n--- Searching for TOC / pointer tables in first 64KB ---")
    for start in range(0, min(0x10000, file_size - 16), 4):
        v0 = read_u32_le(data, start)
        v1 = read_u32_le(data, start + 4)
        v2 = read_u32_le(data, start + 8)
        v3 = read_u32_le(data, start + 12)
        if 0x100 < v0 < v1 < v2 < v3 < file_size:
            diffs = [v1 - v0, v2 - v1, v3 - v2]
            if all(16 <= d <= 0x100000 for d in diffs):
                count = 4
                prev = v3
                off = start + 16
                while off + 4 <= file_size and count < 2000:
                    v = read_u32_le(data, off)
                    if prev < v < file_size and v - prev <= 0x100000:
                        count += 1
                        prev = v
                        off += 4
                    else:
                        break
                if count >= 20:
                    print(f"  TOC at 0x{start:08X}: {count} entries, "
                          f"range 0x{v0:08X}..0x{prev:08X}")

                    # Test: source offsets as indices into this TOC
                    has_hits = False
                    for src_off in [0x102, 0x148, 0x196, 0x1DE, 0x240, 0x25D, 0x269, 0x2BE]:
                        if src_off < count:
                            ptr = read_u32_le(data, start + src_off * 4)
                            zone_name = "?"
                            zone_ids = set()
                            for zn, zd in ZONES.items():
                                if src_off in zd["source"]:
                                    zone_name = zn
                                    zone_ids = set(zd["ids"])
                                    break
                            if ptr + 32 <= file_size:
                                vals = [read_u16_le(data, ptr + i) for i in range(0, 64, 2)]
                                matches = [v for v in vals if v in zone_ids]
                                if matches:
                                    has_hits = True
                                    print(f"    >> idx 0x{src_off:X} ({zone_name}): ptr=0x{ptr:08X} "
                                          f"-> {len(matches)} zone matches: {matches}")
                                    print(hexdump(data, ptr, 96, "       "))
                    if not has_hits:
                        print(f"    (no zone ID matches when using source offsets as TOC indices)")


# ===========================================================================
# PHASE 2: Fast cluster search using position index
# ===========================================================================

def find_monster_clusters(data):
    print("\n" + "=" * 80)
    print("PHASE 2: SEARCHING FOR MONSTER ID CLUSTERS (uint16 LE)")
    print("=" * 80)

    file_size = len(data)
    u16arr = build_u16_array(data)
    n_u16 = len(u16arr)

    # Create zone lookup
    id_to_zones = defaultdict(list)
    for zone_name, zone_data in ZONES.items():
        for mid in zone_data["ids"]:
            id_to_zones[mid].append(zone_name)

    # Build position index: for each monster ID, list of u16-indices where it appears
    print("\nBuilding monster ID position index...")
    monster_positions = defaultdict(list)
    for idx in range(n_u16):
        val = u16arr[idx]
        if val <= 123 and val in ALL_MONSTER_IDS:
            monster_positions[val].append(idx)

    # Show occurrence counts
    print(f"\nMonster ID occurrence counts (top 20 most common):")
    counts = [(mid, len(positions)) for mid, positions in monster_positions.items()]
    counts.sort(key=lambda x: x[1], reverse=True)
    for mid, cnt in counts[:20]:
        zones = id_to_zones.get(mid, ["?"])
        print(f"  ID {mid:3d}: {cnt:6d} occurrences ({zones})")
    print(f"  ...")
    print(f"  Least common:")
    counts.sort(key=lambda x: x[1])
    for mid, cnt in counts[:10]:
        zones = id_to_zones.get(mid, ["?"])
        print(f"  ID {mid:3d}: {cnt:6d} occurrences ({zones})")

    # For each zone, collect positions and look for clusters
    for zone_name, zone_data in ZONES.items():
        zone_ids = set(zone_data["ids"])
        total_in_zone = len(zone_ids)
        print(f"\n{'='*70}")
        print(f"  Zone: {zone_name} ({total_in_zone} monsters: {sorted(zone_ids)})")
        print(f"{'='*70}")

        # Collect all u16-index positions for this zone's IDs
        positions = []  # list of (u16_index, monster_id)
        for mid in zone_ids:
            for idx in monster_positions.get(mid, []):
                positions.append((idx, mid))
        positions.sort()

        if not positions:
            print("  No matches found!")
            continue

        # Efficient sliding window using sorted position list
        # Window of W u16-values = 2*W bytes
        for window_u16 in [32, 64, 128, 256]:
            window_bytes = window_u16 * 2
            min_distinct = min(max(3, total_in_zone // 2), total_in_zone)

            best_clusters = []  # (start_idx, end_idx, distinct_ids)

            j = 0
            for i in range(len(positions)):
                start_idx = positions[i][0]
                end_idx = start_idx + window_u16
                while j < len(positions) and positions[j][0] < end_idx:
                    j += 1
                # Count distinct IDs in [i..j)
                ids_in_window = set()
                for k in range(i, j):
                    ids_in_window.add(positions[k][1])
                if len(ids_in_window) >= min_distinct:
                    best_clusters.append((start_idx, end_idx, frozenset(ids_in_window)))

            if not best_clusters:
                continue

            # Merge overlapping
            merged = []
            for c in best_clusters:
                if merged and c[0] * 2 <= merged[-1][1] * 2 + window_bytes:
                    old = merged[-1]
                    merged[-1] = (old[0], max(old[1], c[1]), old[2] | c[2])
                else:
                    merged.append(c)

            # Sort by count
            merged.sort(key=lambda x: len(x[2]), reverse=True)

            print(f"\n  Window={window_bytes} bytes, min_distinct={min_distinct}:")
            for start_idx, end_idx, found_ids in merged[:10]:
                start_byte = start_idx * 2
                end_byte = end_idx * 2
                pct = len(found_ids) / total_in_zone * 100
                missing = zone_ids - found_ids
                print(f"    0x{start_byte:08X}-0x{end_byte:08X}: "
                      f"{len(found_ids)}/{total_in_zone} IDs ({pct:.0f}%) "
                      f"missing={sorted(missing)}")

        # Find and show the BEST cluster (largest window, most IDs)
        # Re-do with largest window and show detailed analysis
        best_all = []
        for window_u16 in [256, 512]:
            j = 0
            for i in range(len(positions)):
                start_idx = positions[i][0]
                end_idx = start_idx + window_u16
                while j < len(positions) and positions[j][0] < end_idx:
                    j += 1
                ids_in_window = set()
                for k in range(i, j):
                    ids_in_window.add(positions[k][1])
                if len(ids_in_window) >= max(3, total_in_zone * 0.5):
                    best_all.append((start_idx, end_idx, ids_in_window, window_u16))

        if best_all:
            best_all.sort(key=lambda x: len(x[2]), reverse=True)
            best = best_all[0]
            start_byte = best[0] * 2
            end_byte = best[1] * 2
            print(f"\n  ** BEST CLUSTER: 0x{start_byte:08X}-0x{end_byte:08X} "
                  f"({len(best[2])}/{total_in_zone} IDs in {best[3]*2} byte window)")

            # Show all zone IDs found and their positions
            print(f"  Monster IDs found at these positions:")
            for idx in range(best[0], min(best[1], n_u16)):
                val = u16arr[idx]
                if val in zone_ids:
                    byte_off = idx * 2
                    # Show context: 3 u16s before and after
                    ctx = []
                    for ci in range(max(0, idx-4), min(n_u16, idx+5)):
                        v = u16arr[ci]
                        if ci == idx:
                            ctx.append(f"[{v}]")
                        else:
                            ctx.append(f"{v}")
                    print(f"    0x{byte_off:08X}: ID={val:3d}  ctx: {' '.join(ctx)}")

            # Show hex dump of region
            dump_start = max(0, start_byte - 32)
            dump_len = min(end_byte - dump_start + 32, 384)
            print(f"\n  Hex dump around best cluster:")
            print(hexdump(data, dump_start, dump_len))

            # Analyze strides between consecutive zone IDs
            zone_id_offsets = []
            for idx in range(best[0], min(best[1], n_u16)):
                if u16arr[idx] in zone_ids:
                    zone_id_offsets.append(idx * 2)
            if len(zone_id_offsets) >= 2:
                strides = [zone_id_offsets[i+1] - zone_id_offsets[i]
                           for i in range(len(zone_id_offsets)-1)]
                stride_counts = Counter(strides)
                print(f"\n  Strides between consecutive zone IDs: {strides[:30]}")
                print(f"  Most common strides: {stride_counts.most_common(5)}")


# ===========================================================================
# PHASE 3: Search for IDs as uint8 sequences
# ===========================================================================

def search_byte_patterns(data):
    print("\n" + "=" * 80)
    print("PHASE 3: SEARCHING FOR MONSTER IDs AS UINT8 SEQUENCES")
    print("=" * 80)

    file_size = len(data)

    for zone_name, zone_data in ZONES.items():
        zone_ids = set(zone_data["ids"])
        if len(zone_ids) < 4:
            continue

        best_runs = []
        i = 0
        while i < file_size:
            if data[i] in zone_ids:
                run_start = i
                found_ids = set()
                j = i
                while j < file_size and j - run_start < 128:
                    if data[j] in zone_ids:
                        found_ids.add(data[j])
                        j += 1
                    else:
                        break
                run_len = j - run_start
                if len(found_ids) >= 3 and run_len >= 3:
                    best_runs.append((run_start, run_len, found_ids))
                i = j
            else:
                i += 1

        if best_runs:
            best_runs.sort(key=lambda x: len(x[2]), reverse=True)
            total = len(zone_ids)
            print(f"\n  {zone_name} (u8 runs, top 5):")
            shown = 0
            seen = set()
            for start, length, found in best_runs:
                region = start // 4096
                if region in seen:
                    continue
                seen.add(region)
                pct = len(found) / total * 100
                print(f"    0x{start:08X} len={length}: {len(found)}/{total} IDs ({pct:.0f}%) {sorted(found)}")
                print(hexdump(data, max(0, start - 8), min(length + 16, 96), "      "))
                shown += 1
                if shown >= 5:
                    break


# ===========================================================================
# PHASE 4: Sequential ID patterns and high-density regions
# ===========================================================================

def find_master_monster_table(data):
    print("\n" + "=" * 80)
    print("PHASE 4: SEARCHING FOR MASTER MONSTER TABLE / ORDERED SEQUENCES")
    print("=" * 80)

    file_size = len(data)
    u16arr = build_u16_array(data)
    n_u16 = len(u16arr)

    # Look for 0,1,2,3,... sequences with various strides
    print("\n--- 4a: Looking for sequential ID patterns (0,1,2,3,...) ---")
    STRIDES_U16 = [1, 2, 4, 8, 16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40,
                   44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92, 96,
                   100, 104, 108, 112, 116, 120, 124, 128, 140, 152, 160]

    for stride_u16 in STRIDES_U16:
        stride_bytes = stride_u16 * 2
        for start_idx in range(0, n_u16 - stride_u16 * 3):
            if u16arr[start_idx] != 0:
                continue
            if start_idx + stride_u16 >= n_u16:
                continue
            if u16arr[start_idx + stride_u16] != 1:
                continue
            if start_idx + stride_u16 * 2 >= n_u16:
                continue
            if u16arr[start_idx + stride_u16 * 2] != 2:
                continue
            # Count run
            count = 0
            for k in range(min(124, (n_u16 - start_idx) // stride_u16)):
                idx = start_idx + k * stride_u16
                if idx < n_u16 and u16arr[idx] == k:
                    count += 1
                else:
                    break
            if count >= 10:
                byte_off = start_idx * 2
                print(f"  Sequential 0..{count-1} at 0x{byte_off:08X} stride={stride_bytes} bytes ({stride_u16} u16)")
                print(hexdump(data, byte_off, min(stride_bytes * 6, 256)))

    # Find high-density regions of ANY monster IDs
    print("\n\n--- 4b: High-density monster ID regions (1024-byte window, 64-byte step) ---")
    WINDOW_U16 = 512  # 1024 bytes
    STEP_U16 = 32     # 64 bytes

    best_windows = []
    for start_idx in range(0, n_u16 - WINDOW_U16, STEP_U16):
        found = set()
        for idx in range(start_idx, start_idx + WINDOW_U16):
            val = u16arr[idx]
            if val in ALL_MONSTER_IDS:
                found.add(val)
        if len(found) >= 15:
            best_windows.append((start_idx * 2, len(found), found))

    if best_windows:
        best_windows.sort(key=lambda x: x[1], reverse=True)
        print(f"  Found {len(best_windows)} windows with 15+ unique monster IDs")
        seen = set()
        shown = 0
        for start, count, found in best_windows:
            region = start // 4096
            if region in seen:
                continue
            seen.add(region)
            zone_counts = defaultdict(int)
            for mid in found:
                for zn, zd in ZONES.items():
                    if mid in zd["ids"]:
                        zone_counts[zn] += 1
            print(f"\n  0x{start:08X}: {count} unique monster IDs")
            print(f"    Zone breakdown: {dict(zone_counts)}")
            print(hexdump(data, start, 128))
            shown += 1
            if shown >= 15:
                break
    else:
        print("  No 1024-byte windows with 15+ unique monster IDs found")


# ===========================================================================
# PHASE 5: Stride search - monster IDs in record structures
# ===========================================================================

def search_strided_patterns(data):
    print("\n" + "=" * 80)
    print("PHASE 5: STRIDE SEARCH - MONSTER IDs IN RECORD STRUCTURES")
    print("=" * 80)

    file_size = len(data)
    u16arr = build_u16_array(data)
    n_u16 = len(u16arr)

    # For each zone, build index of positions, then check pairs for stride patterns
    for zone_name, zone_data in ZONES.items():
        zone_ids = set(zone_data["ids"])
        total = len(zone_ids)
        if total < 5:
            continue

        print(f"\n  --- {zone_name} ({total} monsters) ---")

        # Build position index for this zone
        positions = []
        for idx in range(n_u16):
            if u16arr[idx] in zone_ids:
                positions.append(idx)

        if len(positions) < 5:
            print(f"  Too few occurrences ({len(positions)})")
            continue

        # For a sample of positions, check strides
        stride_scores = defaultdict(list)  # stride -> [(start_idx, n_found, ids_found)]

        # Sample first 3000 positions to keep it manageable
        sample = positions[:3000]
        for i in range(len(sample)):
            idx_i = sample[i]
            for j in range(i + 1, min(i + 30, len(sample))):
                idx_j = sample[j]
                stride = idx_j - idx_i
                if stride < 2 or stride > 128:
                    continue

                # Verify: how many zone IDs at this stride from idx_i?
                found = set()
                for k in range(min(total + 5, 40)):
                    test_idx = idx_i + k * stride
                    if test_idx >= n_u16:
                        break
                    if u16arr[test_idx] in zone_ids:
                        found.add(u16arr[test_idx])

                if len(found) >= min(5, total - 1):
                    stride_scores[stride].append((idx_i, len(found), found))

        # Show best strides
        if stride_scores:
            best_strides = []
            for stride, results in stride_scores.items():
                results.sort(key=lambda x: x[1], reverse=True)
                best = results[0]
                best_strides.append((stride, best[0], best[1], best[2]))

            best_strides.sort(key=lambda x: x[2], reverse=True)
            print(f"  Top stride patterns:")
            seen = set()
            shown = 0
            for stride, start_idx, n_found, found_ids in best_strides:
                if n_found < min(5, total - 1):
                    continue
                byte_off = start_idx * 2
                stride_bytes = stride * 2
                region = byte_off // 4096
                if region in seen:
                    continue
                seen.add(region)

                pct = n_found / total * 100
                print(f"\n    Stride={stride_bytes} bytes: {n_found}/{total} IDs ({pct:.0f}%) "
                      f"starting at 0x{byte_off:08X}")
                print(f"    Found IDs: {sorted(found_ids)}")
                # Show records
                for k in range(min(n_found + 3, 25)):
                    rec_idx = start_idx + k * stride
                    if rec_idx + stride > n_u16:
                        break
                    rec_off = rec_idx * 2
                    rec_bytes = data[rec_off:rec_off + stride_bytes]
                    hex_str = " ".join(f"{b:02X}" for b in rec_bytes[:min(stride_bytes, 32)])
                    val = u16arr[rec_idx]
                    marker = " <-- ZONE" if val in zone_ids else ""
                    if val in ALL_MONSTER_IDS and val not in zone_ids:
                        marker = f" <-- other zone"
                    print(f"      [{k:2d}] 0x{rec_off:08X}: {hex_str}{marker}")

                shown += 1
                if shown >= 5:
                    break
        else:
            print(f"  No stride patterns found")


# ===========================================================================
# PHASE 6: Record-index hypothesis for source offsets
# ===========================================================================

def deep_sector_search(data):
    print("\n" + "=" * 80)
    print("PHASE 6: SOURCE OFFSETS AS RECORD INDICES")
    print("=" * 80)

    file_size = len(data)
    u16arr = build_u16_array(data)

    # Focus on small offsets only (exclude Cavern's 0xF86 which is different)
    small_src = {}
    for zn, zd in ZONES.items():
        for s in zd["source"]:
            if s < 0x400:
                small_src[s] = (zn, set(zd["ids"]))

    print(f"\n  Small source offsets: {sorted(f'0x{o:X}' for o in small_src.keys())}")

    # For each record size, compute base=0, offset = src * rec_size,
    # and check if data there contains zone monster IDs
    print("\n--- Testing record_size * source_offset from base=0 ---")

    best_results = []
    for rec_size in range(2, 513, 2):
        total_hits = 0
        zone_results = {}
        for src_off, (zone_name, zone_ids) in small_src.items():
            byte_off = src_off * rec_size
            if byte_off + 64 > file_size:
                continue
            found = set()
            # Check uint16 values at this offset and nearby
            for i in range(0, min(64, rec_size + 16), 2):
                if byte_off + i + 2 <= file_size:
                    val = read_u16_le(data, byte_off + i)
                    if val in zone_ids:
                        found.add(val)
            # Also check as uint8
            for i in range(min(32, rec_size + 8)):
                if byte_off + i < file_size:
                    val = data[byte_off + i]
                    if val in zone_ids:
                        found.add(val)
            if found:
                total_hits += len(found)
                zone_results[src_off] = (zone_name, found)

        if total_hits >= 8:
            n_zones = len(set(zn for zn, _ in zone_results.values()))
            best_results.append((rec_size, total_hits, n_zones, zone_results))

    best_results.sort(key=lambda x: (x[2], x[1]), reverse=True)
    for rec_size, total_hits, n_zones, zone_results in best_results[:15]:
        print(f"\n  rec_size={rec_size} (0x{rec_size:X}): {total_hits} hits across {n_zones} zones")
        for src_off, (zone_name, found) in sorted(zone_results.items()):
            byte_off = src_off * rec_size
            print(f"    0x{src_off:X} ({zone_name}): @ 0x{byte_off:08X} found={sorted(found)}")
            print(hexdump(data, byte_off, min(64, rec_size + 16), "      "))

    # Also try with a base offset (maybe there's a header before the table)
    print("\n\n--- Testing base_offset + record_size * source_offset ---")
    # Try common base offsets
    for base in [0x10, 0x14, 0x20, 0x800, 0x1000, 0x2000, 0x4000, 0x8000,
                 0x10000, 0x20000, 0x40000, 0x80000, 0x100000]:
        for rec_size in [2, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48,
                         52, 56, 60, 64, 128, 256]:
            total_hits = 0
            n_zone_hits = 0
            for src_off, (zone_name, zone_ids) in small_src.items():
                byte_off = base + src_off * rec_size
                if byte_off + 32 > file_size:
                    continue
                found = set()
                for i in range(0, min(32, rec_size + 8), 2):
                    if byte_off + i + 2 <= file_size:
                        val = read_u16_le(data, byte_off + i)
                        if val in zone_ids:
                            found.add(val)
                if found:
                    total_hits += len(found)
                    n_zone_hits += 1

            if total_hits >= 8 and n_zone_hits >= 3:
                print(f"  base=0x{base:X} rec_size={rec_size}: {total_hits} hits in {n_zone_hits} zones")
                # Show details for best matches
                for src_off in [0x102, 0x148, 0x196, 0x1DE, 0x240, 0x2BE]:
                    if src_off in small_src:
                        zone_name, zone_ids = small_src[src_off]
                        byte_off = base + src_off * rec_size
                        if byte_off + 32 <= file_size:
                            vals = [read_u16_le(data, byte_off + i) for i in range(0, 32, 2)]
                            matches = [v for v in vals if v in zone_ids]
                            if matches:
                                print(f"    0x{src_off:X} ({zone_name}) @ 0x{byte_off:08X}: "
                                      f"matches={matches} vals={vals}")


# ===========================================================================
# PHASE 7: Search using specific known patterns
# ===========================================================================

def search_known_patterns(data):
    """
    Search for specific byte sequences that we know should exist.
    For Forest, the IDs [24, 79, 88, 61, 59] should appear somehow near each other.
    Try all possible encodings.
    """
    print("\n" + "=" * 80)
    print("PHASE 7: SEARCHING FOR KNOWN ID SEQUENCES")
    print("=" * 80)

    file_size = len(data)

    # Search for specific uint16 LE byte sequences
    # Forest: ID 24 (0x18,0x00) followed somewhere by 79 (0x4F,0x00)
    # Let's search for 2-3 consecutive zone IDs as uint16 LE

    for zone_name, zone_data in ZONES.items():
        zone_ids = zone_data["ids"]
        total = len(zone_ids)
        if total < 3:
            continue

        print(f"\n  --- {zone_name} ---")

        # Build all 2-byte representations of each ID
        id_bytes = {}
        for mid in zone_ids:
            id_bytes[mid] = struct.pack("<H", mid)

        # Search for pairs of consecutive uint16 IDs from this zone
        pair_hits = defaultdict(list)  # (id1, id2) -> [offsets]
        for off in range(0, file_size - 3, 2):
            v1 = struct.unpack_from("<H", data, off)[0]
            v2 = struct.unpack_from("<H", data, off + 2)[0]
            if v1 in set(zone_ids) and v2 in set(zone_ids) and v1 != v2:
                pair_hits[(v1, v2)].append(off)

        if pair_hits:
            # Count total pair hits per region
            region_pairs = defaultdict(lambda: defaultdict(int))
            for (id1, id2), offsets in pair_hits.items():
                for off in offsets:
                    region = off // 1024
                    region_pairs[region][(id1, id2)] += 1

            # Find regions with most distinct pairs
            region_scores = []
            for region, pairs in region_pairs.items():
                all_ids = set()
                for (id1, id2) in pairs.keys():
                    all_ids.add(id1)
                    all_ids.add(id2)
                region_scores.append((region, len(pairs), all_ids))

            region_scores.sort(key=lambda x: x[1], reverse=True)
            print(f"  Regions with most consecutive ID pairs (top 5):")
            seen = set()
            shown = 0
            for region, n_pairs, ids_found in region_scores:
                if region // 4 in seen:
                    continue
                seen.add(region // 4)
                pct = len(ids_found) / total * 100
                byte_off = region * 1024
                print(f"    Region 0x{byte_off:08X}: {n_pairs} pairs, "
                      f"{len(ids_found)}/{total} unique IDs ({pct:.0f}%)")
                if len(ids_found) >= 3:
                    print(hexdump(data, byte_off, 128, "      "))
                shown += 1
                if shown >= 5:
                    break

        # Search for 3+ consecutive uint16 zone IDs
        triple_hits = []
        for off in range(0, file_size - 5, 2):
            v1 = struct.unpack_from("<H", data, off)[0]
            if v1 not in set(zone_ids):
                continue
            v2 = struct.unpack_from("<H", data, off + 2)[0]
            if v2 not in set(zone_ids) or v2 == v1:
                continue
            v3 = struct.unpack_from("<H", data, off + 4)[0]
            if v3 not in set(zone_ids) and v3 == v1:
                continue
            if v3 in set(zone_ids) and v3 != v1 and v3 != v2:
                # Count how many consecutive zone IDs
                count = 3
                found = {v1, v2, v3}
                pos = off + 6
                while pos + 2 <= file_size:
                    v = struct.unpack_from("<H", data, pos)[0]
                    if v in set(zone_ids):
                        found.add(v)
                        count += 1
                        pos += 2
                    else:
                        break
                triple_hits.append((off, count, found))

        if triple_hits:
            triple_hits.sort(key=lambda x: len(x[2]), reverse=True)
            print(f"  Runs of 3+ consecutive uint16 zone IDs (top 5):")
            for off, count, found in triple_hits[:5]:
                pct = len(found) / total * 100
                vals = [struct.unpack_from("<H", data, off + i*2)[0] for i in range(count)]
                print(f"    0x{off:08X}: {count} consecutive, {len(found)}/{total} unique ({pct:.0f}%)")
                print(f"      Values: {vals}")
                print(hexdump(data, max(0, off - 16), min(count * 2 + 32, 128), "      "))


# ===========================================================================
# PHASE 8: Unaligned search and broader patterns
# ===========================================================================

def search_unaligned(data):
    """Search for monster IDs at odd byte boundaries too."""
    print("\n" + "=" * 80)
    print("PHASE 8: UNALIGNED UINT16 SEARCH + BYTE-LEVEL ID SCAN")
    print("=" * 80)

    file_size = len(data)

    # For each zone, find regions where zone IDs appear as single bytes
    # with gaps of 1-4 non-zone bytes between them (structured records)
    for zone_name, zone_data in [("Forest", ZONES["Forest"]),
                                  ("Tower", ZONES["Tower"]),
                                  ("Hall of Demons", ZONES["Hall of Demons"])]:
        zone_ids = set(zone_data["ids"])
        total = len(zone_ids)
        print(f"\n  --- {zone_name} (byte-level gaps) ---")

        # Find all byte positions of zone IDs
        byte_positions = []
        for off in range(file_size):
            if data[off] in zone_ids:
                byte_positions.append(off)

        # Look for regions where many zone IDs cluster with regular gaps
        # Try gap sizes 1-8
        for gap in range(1, 9):
            record_size = gap + 1  # ID byte + gap bytes
            best = []
            for i in range(len(byte_positions)):
                pos = byte_positions[i]
                found = {data[pos]}
                count = 1
                for k in range(1, 40):
                    next_pos = pos + k * record_size
                    if next_pos >= file_size:
                        break
                    if data[next_pos] in zone_ids:
                        found.add(data[next_pos])
                        count += 1
                    else:
                        break
                if count >= 5 and len(found) >= min(4, total - 1):
                    best.append((pos, count, found))

            if best:
                best.sort(key=lambda x: len(x[2]), reverse=True)
                top = best[0]
                if len(top[2]) >= min(5, total // 2):
                    pct = len(top[2]) / total * 100
                    print(f"    gap={gap} (rec_size={record_size}): {len(top[2])}/{total} IDs ({pct:.0f}%) "
                          f"@ 0x{top[0]:08X}, {top[1]} consecutive")
                    print(f"    IDs found: {sorted(top[2])}")
                    print(hexdump(data, max(0, top[0] - 8),
                                  min(top[1] * record_size + 16, 192), "      "))


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    data, path = load_blaze()

    print(f"\nFile: {path}")
    print(f"Size: {len(data):,} bytes")
    print(f"Total unique monster IDs: {len(ALL_MONSTER_IDS)}")
    print(f"Monster ID range: {min(ALL_MONSTER_IDS)} - {max(ALL_MONSTER_IDS)}")
    print(f"Zones: {list(ZONES.keys())}")

    investigate_source_offsets(data)
    find_monster_clusters(data)
    search_byte_patterns(data)
    find_master_monster_table(data)
    search_strided_patterns(data)
    deep_sector_search(data)
    search_known_patterns(data)
    search_unaligned(data)

    print("\n\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
