#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
extract_monster_db.py
Enrich area JSONs and monster_stats files from BLAZE.ALL.

Extracts per-area:
  - Assignment entries (L/R values) for 3D model binding
  - Type-07 entries (VRAM texture offset per slot)
  - slot_types (from formation suffix patterns)

Outputs:
  - Enriches each area JSON with: slot_types, type07_entries, available_monsters
  - Adds per-floor binding data (L, R, slot_type, type07_vram) to
    Data/monster_stats/{normal_enemies,boss}/*.json files

Usage: py -3 Data/formations/extract_monster_db.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

# Always read from SOURCE (unpatched) to get original values
BLAZE_ALL = (PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)"
             / "extract" / "BLAZE.ALL")
if not BLAZE_ALL.exists():
    # Fallback to output if source doesn't exist
    BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

FORMATIONS_DIR = SCRIPT_DIR.parent.parent
MONSTER_STATS_DIR = SCRIPT_DIR.parent.parent.parent / "monster_stats"
SPAWN_GROUPS_DIR = (PROJECT_ROOT / "WIP" / "level_design" / "spawns"
                    / "data" / "spawn_groups")

# 96-byte stat field names (offset from start of 96-byte entry)
STAT_FIELDS = {
    0x10: "exp",
    0x12: "level",
    0x14: "hp",
    0x16: "magic",
    0x18: "stat_18",
    0x1A: "stat_1a",
    0x1C: "stat_1c",
    0x1E: "stat_1e",
    0x20: "stat_20",
    0x22: "drop_rate",
    0x24: "body_class",
    0x26: "armor_type",
    0x28: "elem_fire_ice",
    0x2A: "elem_poison_air",
    0x2C: "elem_light_night",
    0x2E: "elem_divine_malefic",
    0x30: "dmg",
    0x32: "armor",
}


def find_assignment_entries(data, group_offset, num_monsters):
    """Find assignment entries (L/R) by scanning backwards from group_offset.

    Looks for 8-byte entries with flag byte 0x40 at position 7 (R entries).
    Returns list of dicts with L, R values per slot, or None on failure.
    """
    # Search backwards for the block of n_mon entries with 0x40 flags
    # Allow up to 128 bytes of structural data between entries and group
    search_start = group_offset - num_monsters * 8 - 128
    search_end = group_offset

    # Find all 8-byte entries with 0x40 at byte[7]
    candidates = []
    for off in range(search_end - 8, search_start, -8):
        if off < 0:
            break
        if data[off + 7] == 0x40 and data[off + 3] == 0x00:
            candidates.insert(0, off)
        elif candidates:
            break  # Stop at first non-matching entry after finding some

    if len(candidates) != num_monsters:
        return None

    entries = []
    for i, off in enumerate(candidates):
        entry = data[off:off + 8]
        L_slot = entry[0]
        L_val = entry[1]
        R_slot = entry[4]
        R_val = entry[5]
        entries.append({
            "slot": i,
            "L": L_val,
            "R": R_val,
            "offset": "0x{:X}".format(off),
        })

    return entries


def find_animation_tables(data, group_offset, num_monsters):
    """Find animation table and 8-byte records before group_offset.

    Structure (reading backwards from group_offset):
    - group_offset: 96-byte entries start
    - group_offset - n*8: Assignment entries (L/R)
    - Before that: Zero terminator + offsets
    - Before that: 8-byte records [uint32 anim_offset][uint32 texture_ref]
    - Before that: Animation table (8 bytes per monster, animation frame indices)
    - Before that: Animation table header [00 00 00 00 04 00 00 00]

    Returns tuple (anim_table, records_8byte) or (None, None) on failure.
    """
    # Search backwards for animation table header [04 00 00 00 00 00 00 00]
    search_start = max(0, group_offset - 512)
    search_end = group_offset

    header_offset = None
    for off in range(search_end - 8, search_start, -1):
        if off < 0:
            break
        # Check for header pattern: [04 00 00 00] followed by zeros
        if data[off:off+4] == b'\x04\x00\x00\x00':
            # Verify rest is zeros
            if data[off+4:off+8] == b'\x00\x00\x00\x00':
                header_offset = off
                break

    if header_offset is None:
        return None, None

    # Animation table starts 8 bytes after header start
    anim_table_offset = header_offset + 8
    anim_table = []
    for i in range(num_monsters):
        off = anim_table_offset + i * 8
        anim_bytes = data[off:off+8]
        anim_table.append({
            "bytes": anim_bytes.hex(),
            "offset": "0x{:X}".format(off)
        })

    # 8-byte records start at fixed offset from header (0x30 = 48 bytes)
    # Structure: header (8) + animation data block (~40) = 48 bytes
    records_offset = header_offset + 0x30
    records_8byte = []
    for i in range(num_monsters):
        off = records_offset + i * 8
        if off + 8 > len(data):
            break
        anim_off = struct.unpack_from('<I', data, off)[0]
        texture_ref = struct.unpack_from('<I', data, off + 4)[0]
        records_8byte.append({
            "anim_offset": "0x{:04X}".format(anim_off),
            "texture_ref": "0x{:08X}".format(texture_ref),
            "offset": "0x{:X}".format(off)
        })

    return anim_table, records_8byte


def find_type07_entries(data, script_start, num_monsters, max_scan=2048):
    """Find Type-07 entries in the script area.

    Type-07 format: [uint32 vram_offset] [0x07, idx, slot, 0x00]
    Returns dict mapping slot -> {offset, vram_offset, idx}.
    """
    entries = {}
    for off in range(0, min(max_scan, len(data) - script_start) - 7, 4):
        abs_off = script_start + off
        if abs_off + 8 > len(data):
            break
        type_byte = data[abs_off + 4]
        last_byte = data[abs_off + 7]
        slot = data[abs_off + 6]
        idx = data[abs_off + 5]

        if type_byte == 0x07 and last_byte == 0x00 and slot < num_monsters:
            vram_off = struct.unpack_from('<I', data, abs_off)[0]
            # Sanity check: vram_offset should be reasonable (< 0x10000)
            if vram_off < 0x10000:
                entries[slot] = {
                    "vram_offset": "0x{:04X}".format(vram_off),
                    "idx": idx,
                    "offset": "0x{:X}".format(abs_off),
                }

    return entries


def extract_slot_types(data, area_json):
    """Extract slot_types from existing formation data in the binary.

    Reads the 4-byte suffix after each formation to determine per-slot types.
    The suffix equals the type value of the last monster in the formation.
    """
    formations = area_json.get("formations", [])
    monsters = area_json.get("monsters", [])
    num_slots = len(monsters)
    slot_types = {}

    for f in formations:
        slots = f.get("slots", [])
        suffix_hex = f.get("suffix", "00000000")
        if slots and suffix_hex != "00000000":
            last_slot = slots[-1]
            slot_types[last_slot] = suffix_hex

    # Build ordered list (default 00000000)
    result = []
    for i in range(num_slots):
        result.append(slot_types.get(i, "00000000"))

    return result


def read_stat_entry(data, group_offset, slot):
    """Read 96-byte stat entry as hex string and parsed name/stats."""
    off = group_offset + slot * 96
    raw = data[off:off + 96]

    # Parse name (first 16 bytes, null-terminated ASCII)
    name_bytes = raw[:16]
    name = name_bytes.split(b'\x00')[0].decode('ascii', errors='replace')

    # Parse stat values
    stats = {}
    for field_off, field_name in STAT_FIELDS.items():
        val = struct.unpack_from('<H', raw, field_off)[0]
        if val != 0:
            stats[field_name] = val

    return {
        "name": name,
        "stats_hex": raw.hex(),
        "stats": stats,
    }


def parse_floor_from_name(area_name):
    """Parse floor key from area name. 'Floor 1 - Area 2' -> 'Floor 1'."""
    parts = area_name.split(" - ")
    if len(parts) >= 2 and "Floor" in parts[0]:
        return parts[0].strip()
    return "Floor 1"


def load_all_spawn_groups():
    """Load spawn group JSONs for monster lists per area."""
    levels = {}
    for fname in sorted(SPAWN_GROUPS_DIR.iterdir()):
        if not fname.suffix == '.json':
            continue
        with open(fname, 'r') as f:
            sg_data = json.load(f)
        level_name = sg_data.get('level_name', fname.stem)
        groups = []
        for g in sg_data['groups']:
            groups.append({
                'name': g['name'],
                'offset': int(g['offset'], 16),
                'monsters': g['monsters'],
            })
        levels[fname.stem] = {
            'level_name': level_name,
            'groups': groups,
        }
    return levels


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
    print("  Monster Database Extractor")
    print("=" * 60)
    print()

    if not BLAZE_ALL.exists():
        print("ERROR: BLAZE.ALL not found at {}".format(BLAZE_ALL))
        return 1

    print("Reading BLAZE.ALL from {}...".format(BLAZE_ALL))
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print("  Size: {:,} bytes".format(len(blaze_data)))
    print()

    # Load spawn groups for reference
    spawn_groups = load_all_spawn_groups()

    # Find all area JSONs
    json_files = find_area_jsons()
    if not json_files:
        print("No area JSON files found in {}".format(FORMATIONS_DIR))
        return 1

    print("Found {} area JSON files".format(len(json_files)))
    print()

    # Build monster_db: dungeon -> floor -> monster_name -> data
    monster_db = {}
    # Track enriched areas
    enriched = 0
    current_level = None

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            area = json.load(f)

        level_name = area.get("level_name", json_file.parent.name)
        area_name = area.get("name", json_file.stem)
        monsters = area.get("monsters", [])
        group_offset_hex = area.get("group_offset")

        if not monsters or not group_offset_hex:
            continue

        group_offset = int(group_offset_hex, 16)
        num_monsters = len(monsters)
        script_start = group_offset + num_monsters * 96
        floor_key = parse_floor_from_name(area_name)

        # Print level header
        if level_name != current_level:
            if current_level is not None:
                print()
            print("--- {} ---".format(level_name))
            current_level = level_name

        # 1. Extract assignment entries (L/R)
        assign_entries = find_assignment_entries(
            blaze_data, group_offset, num_monsters)

        # 2. Extract animation tables and 8-byte records
        anim_table, records_8byte = find_animation_tables(
            blaze_data, group_offset, num_monsters)

        # 3. Extract Type-07 entries
        type07 = find_type07_entries(
            blaze_data, script_start, num_monsters)

        # 4. Extract slot_types from formation suffixes
        slot_types = extract_slot_types(blaze_data, area)

        # 5. Read 96-byte stat entries
        stat_entries = []
        for i in range(num_monsters):
            entry = read_stat_entry(blaze_data, group_offset, i)
            stat_entries.append(entry)

        # Build per-floor available_monsters list
        if level_name not in monster_db:
            monster_db[level_name] = {}
        if floor_key not in monster_db[level_name]:
            monster_db[level_name][floor_key] = {}

        floor_db = monster_db[level_name][floor_key]

        for i, m_name in enumerate(monsters):
            if m_name not in floor_db:
                entry_data = {
                    "stats_hex": stat_entries[i]["stats_hex"],
                    "stats": stat_entries[i]["stats"],
                    "slot_type": slot_types[i],
                }
                if assign_entries:
                    entry_data["L"] = assign_entries[i]["L"]
                    entry_data["R"] = assign_entries[i]["R"]
                if i in type07:
                    entry_data["type07_vram"] = type07[i]["vram_offset"]
                floor_db[m_name] = entry_data
            else:
                # Update type07_vram if missing from earlier area
                if i in type07 and "type07_vram" not in floor_db[m_name]:
                    floor_db[m_name]["type07_vram"] = type07[i]["vram_offset"]

        # 5. Compute available_monsters for this area (all on same floor)
        # Will be filled in a second pass after all areas are processed.

        # Enrich the area JSON
        area["slot_types"] = slot_types

        # Add assignment entries
        if assign_entries:
            area["assignment_entries"] = assign_entries

        # Add animation table
        if anim_table:
            area["animation_table"] = anim_table

        # Add 8-byte records
        if records_8byte:
            area["records_8byte"] = records_8byte

        type07_list = []
        for i in range(num_monsters):
            if i in type07:
                type07_list.append(type07[i])
            else:
                type07_list.append(None)
        area["type07_entries"] = type07_list

        # Write enriched JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(area, f, indent=2, ensure_ascii=False)
        enriched += 1

        # Print summary
        assign_str = ""
        if assign_entries:
            L_vals = [str(e["L"]) for e in assign_entries]
            assign_str = " L=[{}]".format(",".join(L_vals))
        else:
            assign_str = " L=?"

        anim_str = ""
        if anim_table:
            anim_str = " anim=OK"

        rec8_str = ""
        if records_8byte:
            rec8_str = " rec8=OK"

        type07_str = ""
        if type07:
            vrams = [type07[i]["vram_offset"] if i in type07 else "?"
                     for i in range(num_monsters)]
            type07_str = " vram=[{}]".format(",".join(vrams))

        st_str = ""
        if any(s != "00000000" for s in slot_types):
            st_str = " types=[{}]".format(",".join(slot_types))

        print("  {}: {}{}{}{}{}{}".format(
            area_name,
            ", ".join(monsters),
            assign_str, anim_str, rec8_str, type07_str, st_str))

    # Second pass: add available_monsters to each area JSON
    print()
    print("Adding available_monsters to area JSONs...")

    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            area = json.load(f)

        level_name = area.get("level_name", json_file.parent.name)
        area_name = area.get("name", json_file.stem)
        floor_key = parse_floor_from_name(area_name)

        floor_db = monster_db.get(level_name, {}).get(floor_key, {})
        available = sorted(floor_db.keys())

        if available:
            area["available_monsters"] = available

            # Per-slot VRAM reference from monster_db (fallback for areas
            # where type07_entries were not found in the binary)
            monsters = area.get("monsters", [])
            vram_ref = {}
            for m_name in monsters:
                entry = floor_db.get(m_name, {})
                if "type07_vram" in entry:
                    vram_ref[m_name] = entry["type07_vram"]
            if vram_ref:
                area["monster_vram_ref"] = vram_ref

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(area, f, indent=2, ensure_ascii=False)

    # Write per-floor binding data (L, R, slot_type, type07_vram) to
    # individual monster_stats files
    print()
    print("Updating monster_stats files with floor data...")
    stats_updated = 0
    stats_missing = 0

    for level_name, floors in monster_db.items():
        for floor_key, floor_monsters in floors.items():
            floor_label = "{}/{}".format(level_name, floor_key)
            for m_name, m_data in floor_monsters.items():
                # Find the monster_stats file (name.json, dots -> dashes)
                fname = m_name.replace(".", "-") + ".json"
                stat_path = MONSTER_STATS_DIR / "normal_enemies" / fname
                if not stat_path.exists():
                    stat_path = MONSTER_STATS_DIR / "boss" / fname
                if not stat_path.exists():
                    stats_missing += 1
                    continue

                with open(stat_path, 'r', encoding='utf-8') as f:
                    stat_json = json.load(f)

                # Build floor entry with only binding data
                floor_entry = {}
                if "L" in m_data:
                    floor_entry["L"] = m_data["L"]
                if "R" in m_data:
                    floor_entry["R"] = m_data["R"]
                if "slot_type" in m_data:
                    floor_entry["slot_type"] = m_data["slot_type"]
                if "type07_vram" in m_data:
                    floor_entry["type07_vram"] = m_data["type07_vram"]

                if not floor_entry:
                    continue

                # Merge into existing floors dict
                if "floors" not in stat_json:
                    stat_json["floors"] = {}
                stat_json["floors"][floor_label] = floor_entry

                with open(stat_path, 'w', encoding='utf-8') as f:
                    json.dump(stat_json, f, indent=2, ensure_ascii=False)
                stats_updated += 1

    print()
    print("=" * 60)
    print("  {} area JSONs enriched".format(enriched))
    print("  {} monster_stats files updated".format(stats_updated))
    if stats_missing:
        print("  {} monster(s) without stats file".format(stats_missing))
    print("=" * 60)
    return 0


if __name__ == '__main__':
    exit(main())
