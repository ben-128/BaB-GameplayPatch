#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
patch_formations.py
Rewrites formation templates and spawn points in BLAZE.ALL from edited JSONs.

Supports:
  - Changing slot indices (monster types)
  - Merging formations (combine slots, remove the absorbed formation)
  - Resizing formations (redistribute records between formations)
  - In-place patching of spawn point records (slot, coords, byte0, etc.)

Formation templates: area-rewrite approach (total bytes must not exceed budget).
Spawn points: in-place per-record patching (safe for interleaved areas).

Edit the "slots" arrays or spawn point records, then run this script.

Usage: py -3 Data/formations/patch_formations.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
FORMATIONS_DIR = SCRIPT_DIR

RECORD_SIZE = 32
SUFFIX_SIZE = 4


# ---------------------------------------------------------------------------
# Offset table patching
# ---------------------------------------------------------------------------
# The script area (between 96-byte monster entries and formation templates)
# starts with a uint32 LE offset table. This table contains offsets (from an
# implied base deeper in the script area) to each spawn point group AND each
# formation template. Structure:
#
#   [entry0, 0, SP_offset_0, ..., FM_offset_0, FM_offset_1, ..., 0, 0]
#
# When formation sizes change, these FM offsets must be updated or the engine
# jumps to stale offsets and reads garbled data -> invisible monsters.
# ---------------------------------------------------------------------------


def parse_original_formation_sizes(data, formation_start, formation_bytes):
    """Parse formation record counts from raw binary.

    Scans the formation area for FFFFFFFF markers at byte[4:8] which
    indicate formation start records. Counts records per formation
    using the gaps between starts.

    Returns list of record counts (one per formation), e.g. [3, 3, 2, 4].
    """
    # Find all formation-start positions by scanning for the combined
    # signature: byte[4:8]=FFFFFFFF, byte[9]=0xFF, byte[26:32]=FF*6
    starts = []
    end = formation_start + formation_bytes
    for pos in range(formation_start, end - 31):
        if (data[pos + 4:pos + 8] == b'\xff\xff\xff\xff'
                and data[pos + 9] == 0xFF
                and data[pos + 26:pos + 32] == b'\xff\xff\xff\xff\xff\xff'):
            starts.append(pos)

    if not starts:
        return []

    # Derive sizes from gaps between consecutive starts
    sizes = []
    for i in range(len(starts)):
        if i + 1 < len(starts):
            gap = starts[i + 1] - starts[i]
        else:
            gap = (formation_start + formation_bytes) - starts[i]
        # gap = num_records * 32 + 4 (suffix)
        if (gap - SUFFIX_SIZE) % RECORD_SIZE != 0:
            return []  # alignment error
        sizes.append((gap - SUFFIX_SIZE) // RECORD_SIZE)

    return sizes


def read_offset_table(data, script_start, script_size):
    """Read uint32 LE offset table from start of script area.

    Reads entries while value < 0x10000 (reasonable offset range).
    Stops after two consecutive zero entries.
    Returns list of values.
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
            entries.append(val)
            if consecutive_zeros >= 2:
                break
        else:
            consecutive_zeros = 0
            entries.append(val)

    return entries


def find_fm_entries_in_table(table_entries, original_byte_sizes,
                             script_start=0, formation_start=0):
    """Find contiguous sub-sequence whose diffs match formation byte sizes.

    The sub-sequence has N entries (one per formation) and N-1 diffs
    matching the first N-1 formation byte sizes.

    For single-formation areas (N=1), uses offset calibration: finds a
    table entry whose implied absolute position matches formation_start.

    Returns (start_index, end_index) or None.
    """
    n = len(original_byte_sizes)

    if n == 1 and script_start > 0 and formation_start > 0:
        # Single formation: can't match diffs, so find entry by offset.
        # SP entries give us calibration: the implied base is
        # script_start + entry_value -> some absolute position.
        # FM entry value should point to formation_start relative to
        # the same implied base. We find the base from the first SP
        # entry (non-zero entry after the initial [entry0, 0] header),
        # then look for an entry whose base+value == formation_start.
        #
        # Alternative: the last non-zero entry before terminal zeros
        # is likely the single FM entry.
        for idx in range(len(table_entries) - 1, -1, -1):
            val = table_entries[idx]
            if val != 0:
                # Check if this is the last non-zero before terminal zeros
                # (all entries after it should be zero)
                all_zero_after = all(
                    v == 0 for v in table_entries[idx + 1:])
                if all_zero_after:
                    return (idx, idx)
                break
        return None

    if n < 2:
        return None

    expected_diffs = original_byte_sizes[:-1]

    for start_idx in range(len(table_entries) - n + 1):
        sub = table_entries[start_idx:start_idx + n]
        if 0 in sub:
            continue
        diffs = [sub[i + 1] - sub[i] for i in range(n - 1)]
        if diffs == expected_diffs:
            return (start_idx, start_idx + n - 1)

    return None


def update_offset_table(data, area, user_byte_sizes, filler_sources=None):
    """Update formation offsets in the script area offset table.

    Must be called BEFORE writing new formation data (needs original binary).
    user_byte_sizes: byte sizes for user formations.
    filler_sources: optional list of user formation indices that each filler
                    entry duplicates. Filler binary data stays in the area
                    (as FFFFFFFF termination barriers) but the offset table
                    entries point back to user formations.

    Returns (updated: bool, message: str).
    """
    group_offset_hex = area.get("group_offset")
    formation_start_hex = area.get("formation_area_start")
    formation_bytes = area.get("formation_area_bytes", 0)
    monsters = area.get("monsters", [])

    if not group_offset_hex or not formation_start_hex:
        return False, "missing offsets"

    group_offset = int(group_offset_hex, 16)
    formation_start = int(formation_start_hex, 16)
    num_monsters = len(monsters)
    script_start = group_offset + num_monsters * 96
    script_size = formation_start - script_start

    if script_size <= 0:
        return False, "no script area"

    # The original table FM entry count comes from the JSON metadata
    # (set by the extractor from the unmodified binary).
    filler_count = len(filler_sources) if filler_sources else 0
    original_count = area.get("formation_count",
                              len(user_byte_sizes) + filler_count)

    if len(user_byte_sizes) + filler_count != original_count:
        return False, ("entry count {} != table entries {}".format(
            len(user_byte_sizes) + filler_count, original_count))

    # Read offset table
    table = read_offset_table(data, script_start, script_size)
    if not table:
        return False, "no offset table found"

    # Find FM start index in the offset table.
    # Method 1: match consecutive diffs against parsed binary sizes.
    fm_start_idx = None
    original_sizes = parse_original_formation_sizes(
        data, formation_start, formation_bytes)
    if original_sizes:
        original_byte_sizes = [s * RECORD_SIZE + SUFFIX_SIZE
                               for s in original_sizes]
        fm_range = find_fm_entries_in_table(
            table, original_byte_sizes, script_start, formation_start)
        if fm_range is not None:
            fm_start_idx = fm_range[0]

    # Method 2: use spawn_point_count from JSON to locate FM start.
    if fm_start_idx is None:
        sp_count = area.get("spawn_point_count", 0)
        fm_idx = 2 + sp_count
        if (fm_idx < len(table)
                and fm_idx + original_count <= len(table)
                and table[fm_idx] != 0):
            fm_start_idx = fm_idx

    if fm_start_idx is None:
        return False, "could not locate formation entries in offset table"

    # Compute new entry values
    base_value = table[fm_start_idx]
    user_values = [base_value]
    for i in range(len(user_byte_sizes) - 1):
        user_values.append(user_values[-1] + user_byte_sizes[i])

    if filler_sources:
        # Filler entries duplicate user formation offsets
        filler_values = [user_values[src] for src in filler_sources]
        new_values = user_values + filler_values
    else:
        new_values = user_values

    # Check if values actually changed
    current_values = []
    for i in range(len(new_values)):
        idx = fm_start_idx + i
        if idx < len(table):
            current_values.append(table[idx])
        else:
            current_values.append(None)
    if current_values == new_values:
        return False, "sizes unchanged"

    # Write new values back to binary
    for i, val in enumerate(new_values):
        offset = script_start + (fm_start_idx + i) * 4
        struct.pack_into('<I', data, offset, val)

    msg = "entries [{}..{}] updated ({} formations".format(
        fm_start_idx, fm_start_idx + len(new_values) - 1,
        len(user_byte_sizes))
    if filler_count > 0:
        msg += ", {} duplicate offsets".format(filler_count)
    msg += ")"
    return True, msg


def build_record(slot_index, is_formation_start, area_id_bytes,
                  prefix=b'\x00\x00\x00\x00'):
    """Build a 32-byte formation template record.

    prefix: byte[0:4] — type value of the PREVIOUS monster slot.
            Always 00000000 for the first record in a formation.
    """
    rec = bytearray(RECORD_SIZE)
    # byte[0:4] = type value of previous monster (00000000 for first record)
    rec[0:4] = prefix
    # byte[4:8] = FFFFFFFF for formation start, 00000000 for continuation
    if is_formation_start:
        rec[4:8] = b'\xff\xff\xff\xff'
    # byte[8] = slot index
    rec[8] = slot_index
    # byte[9] = 0xFF (template marker)
    rec[9] = 0xFF
    # byte[10:12] = padding (zeros)
    # byte[12:18] = coords (0,0,0)
    # byte[18:24] = additional params (zeros)
    # byte[24:26] = area identifier
    rec[24:26] = area_id_bytes
    # byte[26:32] = terminator
    rec[26:32] = b'\xff\xff\xff\xff\xff\xff'
    return bytes(rec)


def build_formation_area(area):
    """Build the complete binary for a formation area from JSON."""
    monsters = area["monsters"]
    num_slots = len(monsters)
    area_id = bytes.fromhex(area["area_id"])
    formations = area["formations"]

    # slot_types: per-slot type value used in byte[0:4] and suffix.
    # Each entry is a 4-byte hex string (e.g. "00000a00" for flying).
    # If not provided, all slots default to "00000000".
    slot_types_hex = area.get("slot_types", [])
    slot_types = {}
    for si, st in enumerate(slot_types_hex):
        slot_types[si] = bytes.fromhex(st)
    default_type = b'\x00\x00\x00\x00'

    binary = bytearray()

    for fidx, formation in enumerate(formations):
        slots = formation["slots"]

        if not slots:
            print("    [ERROR] F{:02d}: empty formation (0 slots)".format(fidx))
            return None

        # Validate all slot indices
        for ridx, slot in enumerate(slots):
            if slot < 0 or slot >= num_slots:
                print("    [ERROR] F{:02d}[{}]: slot {} invalid "
                      "(area has {} monsters: {})".format(
                          fidx, ridx, slot, num_slots,
                          ", ".join(monsters)))
                return None

        # Build records for this formation
        for ridx, slot in enumerate(slots):
            is_first = (ridx == 0)
            # byte[0:4] = type of PREVIOUS slot (00000000 for first record)
            if is_first:
                prefix = default_type
            else:
                prev_slot = slots[ridx - 1]
                prefix = slot_types.get(prev_slot, default_type)
            rec = build_record(slot, is_first, area_id, prefix)
            binary.extend(rec)

        # Suffix = type value of the LAST monster in the formation
        last_slot = slots[-1]
        suffix_bytes = slot_types.get(last_slot, default_type)
        binary.extend(suffix_bytes)

    return bytes(binary)


def build_filler_formations(area, remaining_bytes, filler_count):
    """Build filler formations to fill remaining bytes in the budget.

    Each filler has at least 1 record (a single valid monster from slot 0).
    Extra remaining bytes are distributed as additional records among fillers.

    Returns (binary_data, byte_sizes_list) or (None, []) on error.
    """
    if filler_count <= 0 or remaining_bytes <= 0:
        return b'', []

    min_bytes = filler_count * (RECORD_SIZE + SUFFIX_SIZE)
    if remaining_bytes < min_bytes:
        return None, []

    extra_bytes = remaining_bytes - min_bytes
    if extra_bytes % RECORD_SIZE != 0:
        return None, []

    extra_records = extra_bytes // RECORD_SIZE

    # Distribute extra records evenly among fillers
    records_per_filler = []
    for i in range(filler_count):
        base = 1
        extra = extra_records // filler_count
        if i < extra_records % filler_count:
            extra += 1
        records_per_filler.append(base + extra)

    area_id = bytes.fromhex(area["area_id"])
    slot_types_hex = area.get("slot_types", [])
    slot_type_0 = (bytes.fromhex(slot_types_hex[0])
                   if slot_types_hex else b'\x00\x00\x00\x00')

    binary = bytearray()
    byte_sizes = []

    for num_records in records_per_filler:
        for ridx in range(num_records):
            is_first = (ridx == 0)
            prefix = b'\x00\x00\x00\x00' if is_first else slot_type_0
            rec = build_record(0, is_first, area_id, prefix)
            binary.extend(rec)
        binary.extend(slot_type_0)
        byte_sizes.append(num_records * RECORD_SIZE + SUFFIX_SIZE)

    return bytes(binary), byte_sizes


def patch_placed_records(data, area, section_key="spawn_points"):
    """In-place patch placed records (spawn_points or zone_spawns).

    Returns (changed_count, error).
    """
    spawn_points = area.get(section_key, [])
    if not spawn_points:
        return 0, False

    monsters = area["monsters"]
    num_slots = len(monsters)
    changed = 0

    for spidx, sp_group in enumerate(spawn_points):
        records = sp_group.get("records", [])
        for ridx, rec in enumerate(records):
            offset_hex = rec.get("offset")
            if not offset_hex:
                print("    [ERROR] SP{:02d}[{}]: missing offset".format(
                    spidx, ridx))
                return changed, True

            offset = int(offset_hex, 16)
            slot = rec["slot"]

            if slot < 0 or slot >= num_slots:
                print("    [ERROR] SP{:02d}[{}]: slot {} invalid "
                      "(area has {} monsters)".format(
                          spidx, ridx, slot, num_slots))
                return changed, True

            # Build the expected record bytes for comparison
            old_byte8 = data[offset + 8]
            old_coord = struct.unpack_from('<hhh', data, offset + 12)
            old_byte0 = data[offset]
            old_byte10_11 = data[offset + 10:offset + 12]
            old_area_id = data[offset + 24:offset + 26]

            new_x = rec["x"]
            new_y = rec["y"]
            new_z = rec["z"]
            new_byte0 = rec["byte0"]
            new_byte10_11 = bytes.fromhex(rec["byte10_11"])
            new_area_id = bytes.fromhex(rec["area_id"])

            rec_changed = False

            if old_byte8 != slot:
                data[offset + 8] = slot
                rec_changed = True
            if old_coord != (new_x, new_y, new_z):
                struct.pack_into('<hhh', data, offset + 12,
                                 new_x, new_y, new_z)
                rec_changed = True
            if old_byte0 != new_byte0:
                data[offset] = new_byte0
                rec_changed = True
            if old_byte10_11 != new_byte10_11:
                data[offset + 10:offset + 12] = new_byte10_11
                rec_changed = True
            if old_area_id != new_area_id:
                data[offset + 24:offset + 26] = new_area_id
                rec_changed = True

            if rec_changed:
                changed += 1

    return changed, False


def patch_area(data, area):
    """Rewrite the formation area for one area. Returns (changed, error)."""
    formations = area.get("formations", [])
    area_start_hex = area.get("formation_area_start")
    area_bytes = area.get("formation_area_bytes", 0)

    if not formations or not area_start_hex or area_bytes == 0:
        return False, False

    area_start = int(area_start_hex, 16)
    orig_count = area.get("formation_count", len(formations))
    new_num_formations = len(formations)

    if new_num_formations > orig_count:
        print("    [ERROR] {} formations exceeds table capacity {} "
              "(increasing count not supported)".format(
                  new_num_formations, orig_count))
        return False, True

    # Max user slots: each filler formation costs 1 slot (1 record + suffix).
    orig_total = area.get("original_total_slots",
                          (area_bytes - orig_count * SUFFIX_SIZE) // RECORD_SIZE)
    max_user_slots = new_num_formations + orig_total - orig_count

    new_total_slots = sum(len(f["slots"]) for f in formations)

    if new_total_slots > max_user_slots:
        print("    [ERROR] {} slots exceeds maximum {} for {} formations "
              "({} bytes, {} table entries)".format(
                  new_total_slots, max_user_slots, new_num_formations,
                  area_bytes, orig_count))
        return False, True

    # Build the new binary (user's formations only)
    new_binary = build_formation_area(area)
    if new_binary is None:
        return False, True

    # Build filler formations for the remaining budget.
    # Each filler has at least 1 real monster record so the engine
    # gets valid data (0-record formations cause a green screen crash).
    remaining = area_bytes - len(new_binary)
    filler_count = orig_count - new_num_formations

    if remaining > 0 and filler_count > 0:
        filler_binary, filler_byte_sizes = build_filler_formations(
            area, remaining, filler_count)
        if filler_binary is None:
            print("    [ERROR] Cannot build {} filler formations in "
                  "{} remaining bytes (need {} minimum)".format(
                      filler_count, remaining,
                      filler_count * (RECORD_SIZE + SUFFIX_SIZE)))
            return False, True
        new_binary_padded = new_binary + filler_binary
    elif remaining > 0:
        # Same count but underfill — shouldn't happen with correct slots
        print("    [ERROR] {} remaining bytes with same formation count "
              "({})".format(remaining, orig_count))
        return False, True
    elif remaining < 0:
        print("    [ERROR] Formations need {} bytes but area budget "
              "is {} bytes".format(len(new_binary), area_bytes))
        return False, True
    else:
        filler_count = 0
        filler_byte_sizes = []
        new_binary_padded = new_binary

    # Compare with existing data
    old_data = bytes(data[area_start:area_start + area_bytes])
    if new_binary_padded == old_data:
        return False, False

    # Compute byte sizes for user formations
    user_byte_sizes = [len(f["slots"]) * RECORD_SIZE + SUFFIX_SIZE
                       for f in formations]

    # Filler sources: each filler entry duplicates a user formation (round-robin).
    # The filler binary data stays in the area as FFFFFFFF termination barriers,
    # but the offset table entries point back to user formations so the engine
    # never picks a 1-monster filler encounter.
    if filler_count > 0:
        filler_sources = [i % new_num_formations for i in range(filler_count)]
    else:
        filler_sources = None

    # Update the offset table in the script area BEFORE writing formations
    tbl_updated, tbl_msg = update_offset_table(
        data, area, user_byte_sizes, filler_sources)
    if tbl_updated:
        print("    offset table: {}".format(tbl_msg))
    elif tbl_msg not in ("sizes unchanged", "missing offsets"):
        print("    [WARN] offset table not updated: {}".format(tbl_msg))

    # Write the new data
    data[area_start:area_start + area_bytes] = new_binary_padded
    return True, False


def find_area_jsons():
    """Find all area JSONs in level subdirectories."""
    results = []
    for level_dir in sorted(FORMATIONS_DIR.iterdir()):
        if not level_dir.is_dir():
            continue
        for json_file in sorted(level_dir.glob("*.json")):
            results.append(json_file)
    return results


def main():
    print("=" * 60)
    print("  Formation & Spawn Point Patcher")
    print("=" * 60)
    print()

    if not BLAZE_ALL.exists():
        print("ERROR: {} not found!".format(BLAZE_ALL))
        print("Run build_gameplay_patch.bat first to copy clean BLAZE.ALL")
        return 1

    print("Reading {}...".format(BLAZE_ALL))
    data = bytearray(BLAZE_ALL.read_bytes())
    print("  Size: {:,} bytes".format(len(data)))
    print()

    json_files = find_area_jsons()
    if not json_files:
        print("No area JSON files found in {}".format(FORMATIONS_DIR))
        return 1

    print("Found {} area files".format(len(json_files)))
    print()

    total_formation_changed = 0
    total_sp_records_changed = 0
    total_sp_areas_changed = 0
    total_errors = 0
    total_areas = 0
    current_level = None

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            area = json.load(f)

        formations = area.get("formations", [])
        spawn_points = area.get("spawn_points", [])
        zone_spawns = area.get("zone_spawns", [])
        has_formations = (formations
                          and area.get("formation_area_start")
                          and area.get("formation_area_bytes", 0) > 0)
        has_spawn_points = bool(spawn_points)
        has_zone_spawns = bool(zone_spawns)

        if not has_formations and not has_spawn_points and not has_zone_spawns:
            continue

        total_areas += 1
        level_name = area.get("level_name", json_file.parent.name)

        # Print level header when it changes
        if level_name != current_level:
            if current_level is not None:
                print()
            print("--- {} ---".format(level_name))
            current_level = level_name

        area_name = area["name"]
        status_parts = []

        # Patch formations (area-rewrite)
        if has_formations:
            new_total = sum(len(f["slots"]) for f in formations)
            orig_total = area.get("original_total_slots", new_total)
            num_f = len(formations)
            orig_count = area.get("formation_count", num_f)

            f_changed, f_error = patch_area(data, area)

            if f_error:
                total_errors += 1
                status_parts.append("formations:ERROR")
            elif f_changed:
                total_formation_changed += 1
                detail = ""
                if num_f != orig_count:
                    detail += " {}->{}F".format(orig_count, num_f)
                if new_total != orig_total:
                    detail += " {}->{}slots".format(orig_total, new_total)
                status_parts.append("formations:REWRITTEN{}".format(detail))
                monsters = area["monsters"]
                for fidx, f in enumerate(formations):
                    parts = []
                    slot_counts = {}
                    for s in f["slots"]:
                        slot_counts[s] = slot_counts.get(s, 0) + 1
                    for s in sorted(slot_counts.keys()):
                        name = monsters[s] if s < len(monsters) else "?{}".format(s)
                        parts.append("{}x{}".format(slot_counts[s], name))
                    status_parts.append("    F{:02d}: [{}] {}".format(
                        fidx, len(f["slots"]), " + ".join(parts)))
            else:
                status_parts.append("formations:ok({})".format(
                    len(formations)))

        # Patch spawn points (in-place per-record)
        if has_spawn_points:
            sp_changed, sp_error = patch_placed_records(
                data, area, "spawn_points")

            if sp_error:
                total_errors += 1
                status_parts.append("spawn_points:ERROR")
            elif sp_changed > 0:
                total_sp_records_changed += sp_changed
                total_sp_areas_changed += 1
                status_parts.append(
                    "spawn_points:{} records patched".format(sp_changed))
            else:
                total_recs = sum(len(sp.get("records", []))
                                 for sp in spawn_points)
                status_parts.append("spawn_points:ok({} recs)".format(
                    total_recs))

        # Patch zone spawns (in-place per-record)
        if has_zone_spawns:
            zs_changed, zs_error = patch_placed_records(
                data, area, "zone_spawns")

            if zs_error:
                total_errors += 1
                status_parts.append("zone_spawns:ERROR")
            elif zs_changed > 0:
                total_sp_records_changed += zs_changed
                total_sp_areas_changed += 1
                status_parts.append(
                    "zone_spawns:{} records patched".format(zs_changed))
            else:
                total_recs = sum(len(zs.get("records", []))
                                 for zs in zone_spawns)
                status_parts.append("zone_spawns:ok({} recs)".format(
                    total_recs))

        # Print status
        first = True
        for part in status_parts:
            if first:
                print("  {}: {}".format(area_name, part))
                first = False
            else:
                if part.startswith("    "):
                    print(part)
                else:
                    print("    {}".format(part))

    print()

    # Write back
    if total_errors > 0:
        print("!" * 60)
        print("  {} ERRORS detected - BLAZE.ALL NOT saved".format(total_errors))
        print("  Fix the errors above and retry")
        print("!" * 60)
        return 1

    total_changed = total_formation_changed + total_sp_areas_changed
    if total_changed > 0:
        BLAZE_ALL.write_bytes(data)
        print("=" * 60)
        parts = []
        if total_formation_changed > 0:
            parts.append("{} formation area(s) rewritten".format(
                total_formation_changed))
        if total_sp_areas_changed > 0:
            parts.append("{} spawn point records patched in {} area(s)".format(
                total_sp_records_changed, total_sp_areas_changed))
        print("  {}".format(", ".join(parts)))
        print("  ({} areas total)".format(total_areas))
        print("  BLAZE.ALL saved")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  No changes needed ({} areas verified)".format(total_areas))
        print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
