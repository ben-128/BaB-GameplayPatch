#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
patch_formations.py
Rewrites formation templates in BLAZE.ALL from edited JSONs.

Supports:
  - Changing slot indices (monster types)
  - Merging formations (combine slots, remove the absorbed formation)
  - Resizing formations (redistribute records between formations)

The patcher rewrites the entire formation area in-place. Total bytes
must not exceed formation_area_bytes. Unused space is null-padded.

Edit the "slots" arrays in the formation JSONs, then run this script.
To merge: combine slots arrays and delete the absorbed formation entry.

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


def build_record(slot_index, is_formation_start, area_id_bytes):
    """Build a 32-byte formation template record."""
    rec = bytearray(RECORD_SIZE)
    # byte[0:4] = flags (zeros)
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
            rec = build_record(slot, is_first, area_id)
            binary.extend(rec)

        # Write 4-byte suffix
        suffix_hex = formation.get("suffix", "00000000")
        suffix_bytes = bytes.fromhex(suffix_hex)
        if len(suffix_bytes) != 4:
            print("    [ERROR] F{:02d}: suffix must be 4 bytes, "
                  "got {}".format(fidx, len(suffix_bytes)))
            return None
        binary.extend(suffix_bytes)

    return bytes(binary)


def patch_area(data, area):
    """Rewrite the formation area for one area. Returns (changed, error)."""
    formations = area.get("formations", [])
    area_start_hex = area.get("formation_area_start")
    area_bytes = area.get("formation_area_bytes", 0)

    if not formations or not area_start_hex or area_bytes == 0:
        return False, False

    area_start = int(area_start_hex, 16)

    # Calculate new size
    new_total_slots = sum(len(f["slots"]) for f in formations)
    new_num_formations = len(formations)
    new_needed = new_total_slots * RECORD_SIZE + new_num_formations * 4

    if new_needed > area_bytes:
        print("    [ERROR] New formations need {} bytes but area budget "
              "is {} bytes ({} slots in {} formations)".format(
                  new_needed, area_bytes, new_total_slots, new_num_formations))
        print("    Reduce slots or formations to fit. "
              "Max slots with {} formations: {}".format(
                  new_num_formations,
                  (area_bytes - new_num_formations * 4) // RECORD_SIZE))
        return False, True

    # Build the new binary
    new_binary = build_formation_area(area)
    if new_binary is None:
        return False, True

    # Pad with null bytes to fill the area
    padding_needed = area_bytes - len(new_binary)
    new_binary_padded = new_binary + b'\x00' * padding_needed

    # Compare with existing data
    old_data = bytes(data[area_start:area_start + area_bytes])
    if new_binary_padded == old_data:
        return False, False

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
    print("  Formation Rewrite Patcher")
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
        print("No formation JSON files found in {}".format(FORMATIONS_DIR))
        return 1

    print("Found {} area files".format(len(json_files)))
    print()

    total_changed = 0
    total_errors = 0
    total_areas = 0
    current_level = None

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            area = json.load(f)

        formations = area.get("formations", [])
        if not formations:
            continue

        area_start = area.get("formation_area_start")
        area_bytes = area.get("formation_area_bytes", 0)
        if not area_start or area_bytes == 0:
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
        new_total = sum(len(f["slots"]) for f in formations)
        orig_total = area.get("original_total_slots", new_total)
        num_f = len(formations)
        orig_count = area.get("formation_count", num_f)

        changed, error = patch_area(data, area)

        if error:
            total_errors += 1
            print("  {}: ERRORS".format(area_name))
        elif changed:
            total_changed += 1
            detail = ""
            if num_f != orig_count:
                detail += " ({}->{}F)".format(orig_count, num_f)
            if new_total != orig_total:
                detail += " ({}->{}slots)".format(orig_total, new_total)
            print("  {}: REWRITTEN{}".format(area_name, detail))
            # Show new formations
            monsters = area["monsters"]
            for fidx, f in enumerate(formations):
                parts = []
                slot_counts = {}
                for s in f["slots"]:
                    slot_counts[s] = slot_counts.get(s, 0) + 1
                for s in sorted(slot_counts.keys()):
                    name = monsters[s] if s < len(monsters) else "?{}".format(s)
                    parts.append("{}x{}".format(slot_counts[s], name))
                print("    F{:02d}: [{}] {}".format(fidx, len(f["slots"]),
                                                     " + ".join(parts)))
        else:
            print("  {}: {} formations (no changes)".format(
                area_name, num_f))

    print()

    # Write back
    if total_errors > 0:
        print("!" * 60)
        print("  {} ERRORS detected - BLAZE.ALL NOT saved".format(total_errors))
        print("  Fix the errors above and retry")
        print("!" * 60)
        return 1

    if total_changed > 0:
        BLAZE_ALL.write_bytes(data)
        print("=" * 60)
        print("  {} area(s) rewritten out of {} total".format(
            total_changed, total_areas))
        print("  BLAZE.ALL saved")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  No changes needed ({} areas verified)".format(total_areas))
        print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
