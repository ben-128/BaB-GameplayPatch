#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
expand_formation_budget.py - Expand formation budget by relocating gap+ZS data
into free zone spawn space.

All offsets in the script area offset tables are RELATIVE to script_start.
By shifting the gap+ZS data N bytes to the right (into free ZS space), we
extend formation_area_bytes by N bytes without changing the file size.

Before:  [SCRIPT][SP][FM         ][gap][ZS_used ... ZS_free    ]
After:   [SCRIPT'][SP][FM ... +N  ][gap shifted][ZS_used ...] (N bytes less free)

SCRIPT' = same data but all table offsets >= FM_end (relative) incremented by N.

Structure discovered:
  - Root offset table at script_start: ~12 entries (uint32 LE, < 0x10000)
  - Root[0..4]: point to config/bytecode blocks (NOT offset sub-tables)
  - Root[5..N]: point to per-type offset sub-tables (~17-53 entries each)
  - Sub-tables share entries (overlapping views into a large offset array)
  - Sub-tables contain ALL offsets that reference gap/ZS data
  - Bytecode blocks contain small constants that look like offsets but ARE NOT

Usage: py -3 Data/formations/Scripts/expand_formation_budget.py [--apply]
       Default is dry-run mode (no changes written).
       --verbose: show detailed offset scan info
"""

import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
FORMATIONS_DIR = SCRIPT_DIR.parent
SPAWN_GROUPS_DIR = PROJECT_ROOT / "WIP" / "level_design" / "spawns" / "data" / "spawn_groups"

RECORD_SIZE = 32
SUFFIX_SIZE = 4

# ---------------------------------------------------------------------------
# Configuration: per-area expansion in bytes (must be multiple of 4)
# ---------------------------------------------------------------------------
# Map of "level_dir/area_name" -> desired expansion in bytes
# e.g. "cavern_of_death/floor_1_area_1": 360
AREA_EXPANSIONS = {}

# Default expansion: use all available free space (minus safety margin)
DEFAULT_EXPANSION = None  # None = max available
SAFETY_MARGIN = 256       # keep at least this many free bytes in ZS region

# Areas with FM/ZS overlap - skip in phase 1
OVERLAP_AREAS = {
    "sealed_cave/area_8",
    "hall_of_demons/area_1",
    "sealed_cave/area_6",
    "hall_of_demons/area_7",
    "sealed_cave/area_7",
    "sealed_cave/area_2",
    "castle_of_vamp/floor_5_area_1",
    "cavern_of_death/floor_7_area_3",
    "tower/area_8",
    "forest/floor_2_area_1",
}


# ---------------------------------------------------------------------------
# Area boundary computation
# ---------------------------------------------------------------------------

def build_area_end_map():
    """Build a map of group_offset -> area_end from spawn_groups JSONs.

    area_end = the next area's group_offset WITHIN THE SAME DUNGEON.
    Areas from different dungeons can be far apart in the file; we must
    only pair areas within each dungeon to avoid mega-expansions.
    The last area in each dungeon has no natural boundary; we skip it.
    """
    end_map = {}
    for sg_file in sorted(SPAWN_GROUPS_DIR.glob("*.json")):
        with open(sg_file, 'r', encoding='utf-8') as f:
            sg = json.load(f)
        dungeon_offsets = []
        for group in sg.get("groups", []):
            off = int(group["offset"], 16)
            dungeon_offsets.append(off)

        dungeon_offsets.sort()

        # Map each offset to the next one within this dungeon
        for i in range(len(dungeon_offsets) - 1):
            end_map[dungeon_offsets[i]] = dungeon_offsets[i + 1]

    return end_map


# ---------------------------------------------------------------------------
# Offset scanning
# ---------------------------------------------------------------------------

def read_root_table(data, script_start, script_size):
    """Read root offset table from start of script area.

    The root table contains uint32 LE entries (< 0x10000, relative to
    script_start). Stops after two consecutive zero entries.
    Returns list of (index, value) pairs.
    """
    entries = []
    max_entries = min(script_size // 4, 64)
    consecutive_zeros = 0

    for i in range(max_entries):
        val = struct.unpack_from('<I', data, script_start + i * 4)[0]
        if val >= 0x10000:
            break
        if val == 0:
            consecutive_zeros += 1
            entries.append((i, val))
            if consecutive_zeros >= 2:
                break
        else:
            consecutive_zeros = 0
            entries.append((i, val))

    return entries


def read_sub_table(data, abs_offset, max_entries=256):
    """Read an offset sub-table at an absolute file position.

    Sub-tables contain uint32 LE offsets relative to script_start.
    They may contain single zero entries (null slots).
    Stops at two consecutive zeros or value >= 0x10000.
    Returns list of (byte_offset_in_file, value) pairs.
    """
    entries = []
    consecutive_zeros = 0

    for i in range(max_entries):
        off = abs_offset + i * 4
        if off + 4 > len(data):
            break
        val = struct.unpack_from('<I', data, off)[0]
        if val >= 0x10000:
            break
        if val == 0:
            consecutive_zeros += 1
            entries.append((off, val))
            if consecutive_zeros >= 2:
                break
        else:
            consecutive_zeros = 0
            entries.append((off, val))

    return entries


def try_read_subtable(data, abs_offset, max_entries=256):
    """Attempt to read a sub-table at abs_offset.

    Returns a list of (file_offset, value) entries if the data looks like
    a sub-table (at least 1 non-zero entry before a large value).
    Returns empty list if the first entry is already large (bytecode block).

    Key insight: bytecode/config blocks start with values >= 0x10000 or 0xFFFFFFFF.
    Sub-tables start with small values (< 0x10000) even if they only have 1-2 entries.
    """
    # Quick check: if first entry is large, this is not a sub-table
    first_val = struct.unpack_from('<I', data, abs_offset)[0]
    if first_val >= 0x10000:
        return []

    # Read the sub-table normally
    return read_sub_table(data, abs_offset, max_entries)


def scan_structured_offsets(data, script_start, script_size, verbose=False):
    """Find all offsets in root table + sub-tables (structured scan).

    Returns dict: file_offset -> value (relative to script_start).
    Only patches offsets found in structured offset tables.
    """
    offsets = {}  # file_offset -> value

    # Root table
    root_entries = read_root_table(data, script_start, script_size)

    if verbose:
        print("    Root table: {} entries".format(len(root_entries)))

    for idx, val in root_entries:
        file_off = script_start + idx * 4
        if val > 0:
            offsets[file_off] = val

    # Follow ALL non-zero root entries to potential sub-tables
    sub_table_offsets_found = 0
    for idx, val in root_entries:
        if val == 0:
            continue
        # val is relative to script_start
        sub_abs = script_start + val
        if sub_abs + 4 > len(data):
            continue

        # Try to read as sub-table (returns empty if it's a bytecode block)
        sub_entries = try_read_subtable(data, sub_abs)
        sub_count = sum(1 for _, v in sub_entries if v > 0)

        if sub_count == 0:
            if verbose:
                print("    Root[{}] = {} -> 0x{:08X}: "
                      "not a sub-table (config/bytecode block)".format(
                          idx, val, sub_abs))
            continue

        sub_table_offsets_found += sub_count

        if verbose:
            print("    Root[{}] = {} -> 0x{:08X}: "
                  "sub-table with {} entries ({} non-zero)".format(
                      idx, val, sub_abs, len(sub_entries), sub_count))

        for sub_off, sub_val in sub_entries:
            if sub_val > 0:
                offsets[sub_off] = sub_val

    if verbose:
        print("    Total structured offsets: {} (root: {}, sub-tables: {})".format(
            len(offsets), len([v for _, v in root_entries if v > 0]),
            sub_table_offsets_found))

    return offsets


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def find_script_start(data, group_offset, fm_start):
    """Find the actual script_start by scanning for the root table pattern.

    The root table consists of small uint32 values (< 0x10000). Monster stat
    entries start with 16-byte ASCII names (high bytes in ASCII range).
    We scan forward from group_offset, checking each 96-byte boundary for
    the start of the root table pattern.

    Some areas have "hidden" stat entries not listed in the JSON, so
    computing script_start from len(monsters) * 96 can be wrong.
    """
    # Start scanning from group_offset, step 96 bytes (stat entry size)
    pos = group_offset
    while pos < fm_start:
        # Check if this position looks like a root table start:
        # First uint32 should be a small value (< 0x10000) or 0
        val0 = struct.unpack_from('<I', data, pos)[0]

        if val0 < 0x10000:
            # Additional check: should have multiple small values
            # in the first 8 entries (not all zeros, not all large)
            small_count = 0
            for i in range(min(8, (fm_start - pos) // 4)):
                v = struct.unpack_from('<I', data, pos + i * 4)[0]
                if 0 < v < 0x10000:
                    small_count += 1
            if small_count >= 2:
                return pos

        pos += 96  # next stat entry boundary

    return None  # couldn't find it


def compute_area_layout(area, area_end_map, data=None):
    """Compute layout info for an area. Returns dict or None if not expandable."""
    group_offset = int(area["group_offset"], 16)
    n_monsters = len(area["monsters"])

    fm_start = int(area["formation_area_start"], 16)
    fm_bytes = area["formation_area_bytes"]
    fm_end = fm_start + fm_bytes

    # Find actual script_start by scanning for root table
    if data is not None:
        script_start = find_script_start(data, group_offset, fm_start)
        if script_start is None:
            script_start = group_offset + n_monsters * 96  # fallback
    else:
        script_start = group_offset + n_monsters * 96

    zs_start_str = area.get("zone_spawns_area_start")
    if not zs_start_str or zs_start_str == "null":
        return None  # no zone spawns
    zs_start = int(zs_start_str, 16)
    zs_bytes = area.get("zone_spawns_area_bytes", 0)
    if zs_bytes == 0:
        return None
    zs_used_end = zs_start + zs_bytes

    area_end = area_end_map.get(group_offset)
    if area_end is None:
        return None  # last area in file, can't determine boundary

    free_space = area_end - zs_used_end
    if free_space < 0:
        return None  # something wrong

    # Check for FM/ZS overlap
    if fm_end > zs_start:
        return None  # overlap area

    return {
        "group_offset": group_offset,
        "script_start": script_start,
        "fm_start": fm_start,
        "fm_bytes": fm_bytes,
        "fm_end": fm_end,
        "zs_start": zs_start,
        "zs_bytes": zs_bytes,
        "zs_used_end": zs_used_end,
        "area_end": area_end,
        "free_space": free_space,
        "n_monsters": n_monsters,
    }


def find_offsets_to_patch(data, layout, verbose=False):
    """Find all structured table offsets that need patching.

    Returns dict of file_offset -> current_value for offsets >= shift_point.
    """
    script_start = layout["script_start"]
    fm_end = layout["fm_end"]

    # Script region extends from script_start up to fm_end
    script_size = fm_end - script_start
    if script_size <= 0:
        return {}

    # shift_point: relative offset from script_start to FM_end
    # Offsets >= this value point into gap/ZS region and need +N
    shift_point = fm_end - script_start

    # Scan structured offset tables
    structured = scan_structured_offsets(
        data, script_start, script_size, verbose=verbose)

    # Collect all offsets >= shift_point
    offsets_to_patch = {}
    for file_off, val in structured.items():
        if val >= shift_point:
            offsets_to_patch[file_off] = val

    if verbose:
        print("    shift_point = {} (0x{:X}), {} offsets >= shift_point".format(
            shift_point, shift_point, len(offsets_to_patch)))

    return offsets_to_patch


def apply_expansion(data, layout, N, offsets_to_patch):
    """Apply the expansion: shift data and patch offsets.

    1. Move block [FM_end, ZS_used_end) forward by N bytes
    2. Zero-fill the freed space [FM_end, FM_end+N)
    3. Increment all offsets >= shift_point by N
    """
    fm_end = layout["fm_end"]
    zs_used_end = layout["zs_used_end"]

    # Step 1: Shift gap+ZS data forward by N
    # Copy from end to start to handle overlapping regions safely
    block = bytes(data[fm_end:zs_used_end])
    data[fm_end + N:zs_used_end + N] = block

    # Step 2: Zero-fill freed space
    data[fm_end:fm_end + N] = b'\x00' * N

    # Step 3: Patch offsets
    patched_count = 0
    for file_off, old_val in offsets_to_patch.items():
        new_val = old_val + N
        struct.pack_into('<I', data, file_off, new_val)
        patched_count += 1

    return patched_count


def update_area_json(json_file, area, layout, N):
    """Update the area JSON with new offsets after expansion."""
    fm_end = layout["fm_end"]

    # Update formation_area_bytes
    area["formation_area_bytes"] = layout["fm_bytes"] + N

    # Update original_total_slots (recalculate from new budget)
    new_budget = area["formation_area_bytes"]
    num_formations = area.get("formation_count", len(area.get("formations", [])))
    if num_formations > 0:
        new_total_slots = (new_budget - SUFFIX_SIZE * num_formations) // RECORD_SIZE
        area["original_total_slots"] = new_total_slots

    # Update zone_spawns_area_start
    old_zs_start = int(area["zone_spawns_area_start"], 16)
    area["zone_spawns_area_start"] = "0x{:x}".format(old_zs_start + N)

    # Update zone spawn record offsets
    for zs_group in area.get("zone_spawns", []):
        if "offset" in zs_group:
            old = int(zs_group["offset"], 16)
            zs_group["offset"] = "0x{:x}".format(old + N)
        for rec in zs_group.get("records", []):
            if "offset" in rec:
                old = int(rec["offset"], 16)
                rec["offset"] = "0x{:x}".format(old + N)

    # Update spawn_points record offsets (only those located past FM_end)
    for sp_group in area.get("spawn_points", []):
        if "offset" in sp_group:
            old = int(sp_group["offset"], 16)
            if old >= fm_end:
                sp_group["offset"] = "0x{:x}".format(old + N)
        for rec in sp_group.get("records", []):
            if "offset" in rec:
                old = int(rec["offset"], 16)
                if old >= fm_end:
                    rec["offset"] = "0x{:x}".format(old + N)

    # Write back (remove internal keys)
    save_area = {k: v for k, v in area.items() if not k.startswith('_')}
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(save_area, f, indent=2, ensure_ascii=False)
        f.write('\n')


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_post_expansion(data, layout, N, verbose=False):
    """Re-scan structured offsets after expansion to verify consistency.

    After shifting by N, all offsets that were >= shift_point should now
    be >= shift_point + N. This confirms the patch was applied correctly.
    """
    script_start = layout["script_start"]
    fm_end = layout["fm_end"]

    old_shift_point = fm_end - script_start
    new_shift_point = old_shift_point + N

    # The script region now extends up to fm_end + N (new FM boundary)
    new_script_size = fm_end + N - script_start

    structured = scan_structured_offsets(data, script_start, new_script_size)

    # Check: no offset should fall in [old_shift_point, new_shift_point)
    # (that's the freed space, which should be zeros now)
    stale = {off: val for off, val in structured.items()
             if old_shift_point <= val < new_shift_point and val != 0}

    if stale:
        if verbose:
            print("    VALIDATION: {} stale offsets in freed range:".format(
                len(stale)))
            for off, val in sorted(stale.items())[:5]:
                print("      0x{:08X} = {}".format(off, val))
        return False

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def find_area_jsons():
    """Find all area JSONs (excluding _vanilla.json and _user_backup.json)."""
    results = []
    for level_dir in sorted(FORMATIONS_DIR.iterdir()):
        if not level_dir.is_dir() or level_dir.name == "Scripts" or level_dir.name == "docs":
            continue
        for json_file in sorted(level_dir.glob("*.json")):
            if json_file.stem.endswith('_vanilla') or json_file.stem.endswith('_user_backup'):
                continue
            results.append(json_file)
    return results


def main():
    apply_mode = "--apply" in sys.argv
    verbose = "--verbose" in sys.argv

    print("=" * 60)
    print("  Formation Budget Expander")
    print("  Mode: {}".format("APPLY" if apply_mode else "DRY-RUN"))
    print("=" * 60)
    print()

    if not BLAZE_ALL.exists():
        print("ERROR: {} not found!".format(BLAZE_ALL))
        print("Run build_gameplay_patch.bat step 1 first to copy clean BLAZE.ALL")
        return 1

    print("Reading {}...".format(BLAZE_ALL))
    data = bytearray(BLAZE_ALL.read_bytes())
    print("  Size: {:,} bytes".format(len(data)))
    print()

    # Build area boundary map
    area_end_map = build_area_end_map()
    print("Loaded {} area boundaries from spawn_groups".format(len(area_end_map)))
    print()

    json_files = find_area_jsons()
    if not json_files:
        print("No area JSON files found in {}".format(FORMATIONS_DIR))
        return 1

    print("Found {} area files".format(len(json_files)))
    print()

    total_expanded = 0
    total_skipped = 0
    total_errors = 0
    total_bytes_gained = 0
    current_level = None

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            area = json.load(f)

        area_key = "{}/{}".format(json_file.parent.name, json_file.stem)
        level_name = area.get("level_name", json_file.parent.name)
        area_name = area.get("name", json_file.stem)

        # Skip areas without formations or zone spawns
        if (not area.get("formation_area_start")
                or area.get("formation_area_bytes", 0) == 0):
            continue
        zs_start = area.get("zone_spawns_area_start")
        if not zs_start or zs_start == "null" or area.get("zone_spawns_area_bytes", 0) == 0:
            continue

        # Skip overlap areas
        if area_key in OVERLAP_AREAS:
            total_skipped += 1
            continue

        # Print level header
        if level_name != current_level:
            if current_level is not None:
                print()
            print("--- {} ---".format(level_name))
            current_level = level_name

        # Compute layout
        layout = compute_area_layout(area, area_end_map, data)
        if layout is None:
            print("  {}: SKIP (no boundary or overlap)".format(area_name))
            total_skipped += 1
            continue

        free_space = layout["free_space"]
        if free_space < SAFETY_MARGIN + 4:
            print("  {}: SKIP (only {} bytes free)".format(
                area_name, free_space))
            total_skipped += 1
            continue

        # Determine expansion amount
        if area_key in AREA_EXPANSIONS:
            desired_N = AREA_EXPANSIONS[area_key]
        elif DEFAULT_EXPANSION is not None:
            desired_N = DEFAULT_EXPANSION
        else:
            desired_N = free_space - SAFETY_MARGIN

        # Align to 4 bytes
        N = (min(desired_N, free_space - SAFETY_MARGIN) // 4) * 4
        if N <= 0:
            print("  {}: SKIP (expansion too small: {} desired, {} free)".format(
                area_name, desired_N, free_space))
            total_skipped += 1
            continue

        # Find offsets to patch (structured tables only)
        offsets_to_patch = find_offsets_to_patch(data, layout, verbose=verbose)

        # Calculate new budget stats
        num_formations = area.get("formation_count", len(area.get("formations", [])))
        old_budget = layout["fm_bytes"]
        new_budget = old_budget + N
        old_max_slots = (old_budget - SUFFIX_SIZE * num_formations) // RECORD_SIZE
        new_max_slots = (new_budget - SUFFIX_SIZE * num_formations) // RECORD_SIZE
        gained_slots = new_max_slots - old_max_slots

        print("  {}: +{} bytes ({} -> {} budget), +{} slots ({} -> {}), "
              "{} offsets to patch".format(
                  area_name, N, old_budget, new_budget,
                  gained_slots, old_max_slots, new_max_slots,
                  len(offsets_to_patch)))

        if apply_mode:
            # Apply expansion
            patched = apply_expansion(data, layout, N, offsets_to_patch)

            # Validate
            if not validate_post_expansion(data, layout, N, verbose=verbose):
                print("    ERROR: post-expansion validation failed!")
                total_errors += 1
                continue

            # Update JSON
            update_area_json(json_file, area, layout, N)
            print("    Applied: {} offsets patched, JSON updated".format(patched))

        total_expanded += 1
        total_bytes_gained += N

    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print("  Expanded: {} areas (+{:,} bytes total)".format(
        total_expanded, total_bytes_gained))
    print("  Skipped: {} areas".format(total_skipped))
    if total_errors > 0:
        print("  Errors: {} areas".format(total_errors))
    print()

    if apply_mode:
        if total_errors > 0:
            print("  ERRORS detected - BLAZE.ALL NOT saved")
            return 1
        if total_expanded > 0:
            BLAZE_ALL.write_bytes(data)
            print("  BLAZE.ALL saved ({:,} bytes)".format(len(data)))

            # Verify file size is still sector-aligned
            if len(data) % 2048 != 0:
                print("  WARNING: file size not sector-aligned!")
        else:
            print("  No changes to save")
    else:
        print("  (dry-run mode - no changes written)")
        print("  Run with --apply to apply changes")

    return 0


if __name__ == '__main__':
    exit(main())
