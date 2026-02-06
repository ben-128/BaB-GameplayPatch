#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
patch_formations.py
Patches formation template slot indices (byte[8]) in BLAZE.ALL.

Edit the "slots" arrays in the formation JSONs, then run this script.
Only byte[8] (monster slot index) is patched - record count stays the same.

Usage: py -3 Data/formations/patch_formations.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
FORMATIONS_DIR = SCRIPT_DIR

# Formation record: 32 bytes
# byte[8] = monster slot index (the field we patch)
# byte[9] = 0xFF (template marker)
# bytes[12:18] = coords (0,0,0 for templates)
# bytes[26:32] = FF FF FF FF FF FF (terminator)
RECORD_SIZE = 32
SLOT_BYTE_OFFSET = 8
MARKER_BYTE_OFFSET = 9
MARKER_VALUE = 0xFF


def verify_record(data, offset, expected_slot=None):
    """Verify that a valid formation template record exists at offset."""
    if offset + RECORD_SIZE > len(data):
        return False, "offset out of bounds"

    rec = data[offset:offset + RECORD_SIZE]

    # Check template marker
    if rec[MARKER_BYTE_OFFSET] != MARKER_VALUE:
        return False, "byte[9] != 0xFF (got 0x{:02X})".format(rec[MARKER_BYTE_OFFSET])

    # Check coords are (0,0,0)
    coord = struct.unpack_from('<hhh', rec, 12)
    if coord != (0, 0, 0):
        return False, "coords != (0,0,0): {}".format(coord)

    # Check terminator
    if rec[26:32] != b'\xff\xff\xff\xff\xff\xff':
        return False, "missing FF terminator"

    return True, "ok"


def patch_area_formations(data, area):
    """Patch all formations for one area. Returns (patched_count, error_count)."""
    monsters = area["monsters"]
    num_slots = len(monsters)
    patched = 0
    errors = 0

    for fidx, formation in enumerate(area["formations"]):
        base_offset = int(formation["offset"], 16)
        slots = formation["slots"]

        for ridx, slot_value in enumerate(slots):
            # Within a formation, records are contiguous (32 bytes apart)
            rec_offset = base_offset + ridx * RECORD_SIZE

            # Validate slot value
            if slot_value < 0 or slot_value >= num_slots:
                print("    [ERROR] F{:02d}[{}]: slot {} invalid (area has {} monsters: {})".format(
                    fidx, ridx, slot_value, num_slots,
                    ", ".join(monsters)))
                errors += 1
                continue

            # Verify record exists at expected location
            ok, msg = verify_record(data, rec_offset)
            if not ok:
                print("    [ERROR] F{:02d}[{}] at 0x{:X}: {}".format(
                    fidx, ridx, rec_offset, msg))
                errors += 1
                continue

            # Read current value
            old_value = data[rec_offset + SLOT_BYTE_OFFSET]

            # Patch byte[8]
            data[rec_offset + SLOT_BYTE_OFFSET] = slot_value

            if old_value != slot_value:
                old_name = monsters[old_value] if old_value < num_slots else "?{}".format(old_value)
                new_name = monsters[slot_value]
                print("    F{:02d}[{}] at 0x{:X}: slot {} ({}) -> {} ({})".format(
                    fidx, ridx, rec_offset, old_value, old_name,
                    slot_value, new_name))
                patched += 1

    return patched, errors


def main():
    print("=" * 60)
    print("  Formation Template Patcher")
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

    # Find all formation JSONs
    json_files = sorted(FORMATIONS_DIR.glob("*.json"))
    if not json_files:
        print("No formation JSON files found in {}".format(FORMATIONS_DIR))
        return 1

    print("Found {} level files".format(len(json_files)))
    print()

    total_patched = 0
    total_errors = 0
    total_formations = 0

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            level_data = json.load(f)

        level_name = level_data.get("level_name", json_file.stem)
        areas = level_data.get("areas", [])

        # Skip levels with no formations to patch
        has_formations = any(a.get("formations") for a in areas)
        if not has_formations:
            continue

        print("--- {} ---".format(level_name))

        for area in areas:
            formations = area.get("formations", [])
            if not formations:
                continue

            area_name = area["name"]
            total_formations += len(formations)

            patched, errors = patch_area_formations(data, area)
            total_patched += patched
            total_errors += errors

            if patched == 0 and errors == 0:
                print("  {}: {} formations (no changes)".format(
                    area_name, len(formations)))
            elif errors > 0:
                print("  {}: {} patched, {} ERRORS".format(
                    area_name, patched, errors))

        print()

    # Write back
    if total_errors > 0:
        print("!" * 60)
        print("  {} ERRORS detected - BLAZE.ALL NOT saved".format(total_errors))
        print("  Fix the errors above and retry")
        print("!" * 60)
        return 1

    if total_patched > 0:
        BLAZE_ALL.write_bytes(data)
        print("=" * 60)
        print("  {} slot(s) patched across {} formations".format(
            total_patched, total_formations))
        print("  BLAZE.ALL saved")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  No changes needed ({} formations verified)".format(
            total_formations))
        print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
