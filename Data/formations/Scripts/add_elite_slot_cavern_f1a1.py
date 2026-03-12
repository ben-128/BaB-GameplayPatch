#!/usr/bin/env python3
"""
add_elite_slot_cavern_f1a1.py v2 — In-place binary expansion

Adds a 4th monster slot (E-Shaman) to Cavern F1 Area 1 by rewriting
the area data in-place (no file size change):

1. Builds 168-byte middle section (was 124), matching Area 2's N=4 structure
2. Inserts 96-byte E-Shaman stat block after existing stats
3. Shifts script/spawn/formation/zone_spawns data forward by 140 bytes
4. Truncates zone_spawns by 140 bytes from the end (2.6% loss, ~4 records)

Total file size: unchanged (in-place rewrite within area boundaries).
No overlay patching needed — engine navigates structurally via relative offsets.

Must run AFTER copying clean BLAZE.ALL and BEFORE patch_formations.py.
Usage: py -3 Data/formations/Scripts/add_elite_slot_cavern_f1a1.py
"""

import struct
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
AREA_JSON = SCRIPT_DIR.parent / "cavern_of_death" / "floor_1_area_1.json"
SPAWN_GROUPS_JSON = PROJECT_ROOT / "WIP" / "level_design" / "spawns" / "data" / "spawn_groups" / "cavern_of_death.json"

# === Vanilla Cavern F1 Area 1 layout ========================================
AREA_START        = 0xF7A900  # Middle section start (= area base)
AREA_END          = 0xF7CA48  # End of zone_spawns (= area end)
AREA_SIZE         = AREA_END - AREA_START   # 8520 bytes (fixed)

VANILLA_MIDDLE_SIZE  = 124    # 3 monsters
VANILLA_N_MONSTERS   = 3
VANILLA_GROUP_OFFSET = 0xF7A97C  # AREA_START + 124
VANILLA_STATS_SIZE   = 3 * 96    # 288 bytes
VANILLA_STATS_END    = 0xF7AA9C  # script_area_start

VANILLA_FORMATION_START    = 0xF7AFFC
VANILLA_SPAWN_POINTS_START = 0xF7AEB4
VANILLA_ZONE_SPAWNS_START  = 0xF7B520
VANILLA_ZONE_SPAWNS_BYTES  = 5416

# === New layout (4 monsters) =================================================
NEW_N_MONSTERS   = 4
NEW_MIDDLE_SIZE  = 168       # Matches real N=4 areas (verified vs Area 2)
MIDDLE_EXPANSION = NEW_MIDDLE_SIZE - VANILLA_MIDDLE_SIZE   # 44 bytes
STATS_EXPANSION  = 96        # One more 96-byte stat block
TOTAL_EXPANSION  = MIDDLE_EXPANSION + STATS_EXPANSION      # 140 = 0x8C

NEW_GROUP_OFFSET         = AREA_START + NEW_MIDDLE_SIZE                  # 0xF7A9A8
NEW_STATS_END            = NEW_GROUP_OFFSET + 4 * 96                    # 0xF7AB28
NEW_FORMATION_START      = VANILLA_FORMATION_START + TOTAL_EXPANSION    # 0xF7B088
NEW_SPAWN_POINTS_START   = VANILLA_SPAWN_POINTS_START + TOTAL_EXPANSION # 0xF7AF40
NEW_ZONE_SPAWNS_START    = VANILLA_ZONE_SPAWNS_START + TOTAL_EXPANSION  # 0xF7B5AC
NEW_ZONE_SPAWNS_BYTES    = VANILLA_ZONE_SPAWNS_BYTES - TOTAL_EXPANSION  # 5276

# === Middle section layout (168 bytes for N=4) ===============================
# Verified against real N=4 area (Cavern F1 Area 2):
#
#   +0x00  header           12 bytes  (copy vanilla)
#   +0x0C  anim_table       4x8=32    (3 vanilla + E-Shaman=copy Shaman)
#   +0x2C  pointed_entries  4x8=32    (animation data, one per slot)
#   +0x4C  unpointed_entries 4x8=32   (anim_offset + texture_ref pairs)
#   +0x6C  pointer_table    7x4=28    ([0, 0, 0x2C, 0x34, 0x3C, 0x44, 0])
#   +0x88  assignments      4x8=32    (3 vanilla + E-Shaman)
#   +0xA8  END


def build_new_middle_section(area_data):
    """Build 168-byte middle section for 4 monsters from vanilla 3-monster data."""
    middle = bytearray(NEW_MIDDLE_SIZE)

    # -- Header (12 bytes) --
    middle[0x00:0x0C] = area_data[0x00:0x0C]

    # -- Anim table (4x8 = 32 bytes) --
    middle[0x0C:0x14] = area_data[0x0C:0x14]  # Slot 0 (Goblin)
    middle[0x14:0x1C] = area_data[0x14:0x1C]  # Slot 1 (Shaman)
    middle[0x1C:0x24] = area_data[0x1C:0x24]  # Slot 2 (Bat)
    middle[0x24:0x2C] = area_data[0x14:0x1C]  # Slot 3 (E-Shaman = copy Shaman)

    # -- Pointed entries (4x8 = 32 bytes) --
    # Second set of animation data, one per slot. Pointer table points here.
    # Vanilla has 3 pointed entries at area offsets 0x24, 0x2C, 0x34
    middle[0x2C:0x34] = area_data[0x24:0x2C]  # Slot 0
    middle[0x34:0x3C] = area_data[0x2C:0x34]  # Slot 1 (Shaman)
    middle[0x3C:0x44] = area_data[0x34:0x3C]  # Slot 2 (Bat)
    middle[0x44:0x4C] = area_data[0x2C:0x34]  # Slot 3 (E-Shaman = copy Shaman)

    # -- Unpointed entries (4x8 = 32 bytes) --
    # anim_offset + texture_ref pairs. Vanilla has 2 at offsets 0x3C, 0x44.
    # Need 4 entries for N=4 (one per slot).
    # Slot 0 (Goblin): anim_offset=0x0C, texture_ref=0x00030000
    #   (not in vanilla Area 1, value from Area 2 which has same Goblin)
    struct.pack_into('<I', middle, 0x4C, 0x0000000C)  # anim_offset
    struct.pack_into('<I', middle, 0x50, 0x00030000)   # texture_ref
    # Slot 1 (Shaman): from vanilla at area offset 0x3C
    middle[0x54:0x5C] = area_data[0x3C:0x44]
    # Slot 2 (Bat): from vanilla at area offset 0x44
    middle[0x5C:0x64] = area_data[0x44:0x4C]
    # Slot 3 (E-Shaman): anim_offset=0x24, texture_ref=0x0006C000
    # texref pattern: i*0x14000 + 0x30000 where i=3 → 0x3C000+0x30000 = 0x6C000
    struct.pack_into('<I', middle, 0x64, 0x00000024)   # anim_offset
    struct.pack_into('<I', middle, 0x68, 0x0006C000)   # texture_ref (was 0x00044000)

    # -- Pointer table (7x4 = 28 bytes) --
    # Points to the 4 pointed entries (at +0x2C, +0x34, +0x3C, +0x44)
    pointers = [0x00000000, 0x00000000,
                0x0000002C, 0x00000034, 0x0000003C, 0x00000044,
                0x00000000]
    for i, ptr in enumerate(pointers):
        struct.pack_into('<I', middle, 0x6C + i * 4, ptr)

    # -- Assignments (4x8 = 32 bytes) --
    # Vanilla assignments at area offsets 0x64, 0x6C, 0x74
    middle[0x88:0x90] = area_data[0x64:0x6C]  # Slot 0 (Goblin)
    middle[0x90:0x98] = area_data[0x6C:0x74]  # Slot 1 (Shaman)
    middle[0x98:0xA0] = area_data[0x74:0x7C]  # Slot 2 (Bat)
    # Slot 3 (E-Shaman): slot_id=3, L=1 (Shaman model), tex=1, R=5, flag=0x40
    middle[0xA0:0xA8] = b'\x03\x01\x01\x00\x03\x05\x00\x40'

    return bytes(middle)


def build_elite_stats(area_data):
    """Build 96-byte stat block for E-Shaman from vanilla Shaman stats."""
    # Vanilla stats start at area offset 0x7C (= VANILLA_MIDDLE_SIZE)
    # Slot 1 (Shaman) is the 2nd 96-byte block
    shaman_offset = VANILLA_MIDDLE_SIZE + 96
    new_stats = bytearray(area_data[shaman_offset:shaman_offset + 96])

    # Name
    name = b'E-Shaman'
    new_stats[0:len(name)] = name
    new_stats[len(name):16] = b'\x00' * (16 - len(name))

    # Elite multipliers
    hp    = struct.unpack_from('<H', new_stats, 0x14)[0]
    magic = struct.unpack_from('<H', new_stats, 0x16)[0]
    dmg   = struct.unpack_from('<H', new_stats, 0x30)[0]
    armor = struct.unpack_from('<H', new_stats, 0x32)[0]

    struct.pack_into('<H', new_stats, 0x14, min(int(hp * 2), 65535))
    struct.pack_into('<H', new_stats, 0x16, min(int(magic * 2), 65535))
    struct.pack_into('<H', new_stats, 0x30, min(int(dmg * 1.5), 65535))
    struct.pack_into('<H', new_stats, 0x32, min(int(armor * 2), 65535))

    # Boss flag
    struct.pack_into('<H', new_stats, 0x26, 32768)

    return bytes(new_stats)


def _patch_script_offsets(new_area):
    """
    Fix stale area-relative offset fields in script command entries after N=3->N=4 expansion.

    Background: The script area contains 8-byte command entries with format
    [uint32 area-relative-offset][type][idx][slot][flag].  After the +0x8C shift,
    the pointed-to data moved but the stored offset values did not.  The engine
    then reads from zone_spawn data instead of texture/VRAM descriptors, causing a crash.

    Also adds the missing 4th type07 entry (E-Shaman slot 3) and updates the type0E
    terminator idx from 19 to 20.  Finally copies Shaman's VRAM descriptor to the new
    E-Shaman data slot so the model uses correct texture parameters.

    All area_offset values below are indices into new_area (= AREA_START-relative).
    """
    # 33 entries whose first uint32 needs +TOTAL_EXPANSION (area-relative pointer correction).
    # Each tuple: (area_offset_in_new_area, expected_stale_value).
    #
    # "Batch 1" (offset_value in [0x019C, 0x05B4)): script entries pointing into the
    #   script area itself — root table sub-blocks, VRAM descriptors, etc.
    # "Batch 2" (offset_value in [0x05B4, 0x1F48)): script entries pointing into the
    #   spawn_points, formation, and zone_spawn sections that also shifted by +0x8C.
    OFFSET_FIX_ENTRIES = [
        # -- Batch 1: script -> script area --
        # NOTE: entries at 0x0240/0x0248 (values 0x0380/0x027C) are root table
        # configuration values that repeat in groups of 3 (indices 4,5,6 / 7,8,9 / 10,11,12).
        # They are NOT area-relative pointers — do NOT shift them.
        # Same for 0x0250 (value 0x0198) — see special case removed below.
        (0x02A8, 0x0518),   # type 0x01
        (0x02B0, 0x0520),   # type 0x02
        # -- Batch 2a: script -> beyond-script areas (offsets 0x0800, 0x0C00) --
        (0x0308, 0x0800),   # script+0x00E0 -> data at 0x0800
        (0x0328, 0x0C00),   # script+0x0100 -> data at 0x0C00
        # -- Batch 1 continued --
        (0x0340, 0x0540),   # type 0x00 (null type)
        (0x0348, 0x0558),   # type 0x60
        (0x0358, 0x0568),   # type 0x04
        (0x0360, 0x0570),   # type 0x05 (light/shadow)
        (0x0368, 0x0578),   # type 0x06 (light/shadow)
        (0x0370, 0x0580),   # type 0x07 slot 0 (Goblin VRAM)
        (0x0378, 0x0588),   # type 0x07 slot 1 (Shaman VRAM)
        (0x0380, 0x0590),   # type 0x07 slot 2 (Bat VRAM)
        # 0x0388 = type0E terminator -> replaced below with type07[3]
        (0x0398, 0x05A0),   # null-type data entry
        (0x03A0, 0x05A8),   # 0x40-flag entry
        (0x03B0, 0x05B0),   # 0x40-flag entry
        # -- Batch 2b: script -> spawn_points area (offsets 0x05B8 .. 0x05DC) --
        (0x03B8, 0x05B8),   # script+0x0190 -> spawn_points+0x04
        (0x03C0, 0x05C0),   # script+0x0198 -> spawn_points+0x0C
        (0x03C8, 0x05C8),   # script+0x01A0 -> spawn_points+0x14
        (0x03F0, 0x05D0),   # script+0x01C8 -> spawn_points+0x1C
        (0x0408, 0x05DC),   # script+0x01E0 -> spawn_points+0x28
        # -- Batch 2c: script -> zone_spawn area (offsets 0x1DC0 .. 0x210C) --
        (0x0440, 0x1DC0),   # script+0x0218 -> zone_spawn data
        (0x0448, 0x1EC8),   # script+0x0220
        (0x0450, 0x1F18),   # script+0x0228
        (0x0458, 0x1F44),   # script+0x0230
        (0x0460, 0x1F8C),   # script+0x0238
        (0x0468, 0x2008),   # script+0x0240
        (0x0470, 0x2094),   # script+0x0248
        (0x0478, 0x210C),   # script+0x0250 (pointed-to data near zone_spawn tail)
        # -- Batch 2d: late script entries pointing into formation/zone_spawn --
        (0x0618, 0x1184),   # script+0x03F0 -> formation/zone area data
        (0x0630, 0x1500),   # script+0x0408
    ]
    for area_off, expected in OFFSET_FIX_ENTRIES:
        cur = struct.unpack_from('<I', new_area, area_off)[0]
        if cur != expected:
            raise ValueError(
                "Script offset fix: area+0x{:04X}: expected 0x{:04X}, got 0x{:04X}".format(
                    area_off, expected, cur))
        struct.pack_into('<I', new_area, area_off, expected + TOTAL_EXPANSION)

    # NOTE: the value 0x0198 at area+0x0250 (root table index 10) was previously
    # treated as a stats-area pointer needing +MIDDLE_EXPANSION shift. Analysis via
    # diagnose_script_pointers.py shows this is a fixed root table configuration value
    # (same value repeats at root[4], root[7], root[10]) — must NOT be shifted.

    # -- Add type07[3] for E-Shaman at area+0x0388 (was vanilla type0E terminator) --
    # offset = 0x0598 + TOTAL_EXPANSION = 0x0624 (E-Shaman VRAM data block)
    struct.pack_into('<I', new_area, 0x0388, 0x0598 + TOTAL_EXPANSION)
    new_area[0x038C] = 0x07   # type 0x07
    new_area[0x038D] = 0x13   # idx = 19
    new_area[0x038E] = 0x03   # slot = 3
    new_area[0x038F] = 0x00

    # -- Write new type0E terminator at area+0x0390 (was null) --
    # offset = 0x05A0 + TOTAL_EXPANSION = 0x062C
    # idx 0x14 = 20 = (last type07 idx 19) + 1
    struct.pack_into('<I', new_area, 0x0390, 0x05A0 + TOTAL_EXPANSION)
    new_area[0x0394] = 0x0E   # type 0x0E (terminator)
    new_area[0x0395] = 0x14   # idx = 20
    new_area[0x0396] = 0x00
    new_area[0x0397] = 0x00

    # -- Copy Shaman VRAM descriptor to E-Shaman's data block at area+0x0624 --
    # Shaman data block: area+0x0614 (= 0x0588 + TOTAL_EXPANSION)
    # E-Shaman data block: area+0x0624 (= 0x0598 + TOTAL_EXPANSION)
    # E-Shaman uses the same 3D model as Shaman, so VRAM params must match.
    new_area[0x0624:0x062C] = bytes(new_area[0x0614:0x061C])


def rewrite_area_inplace(blaze_data):
    """Rewrite area data in-place: expand middle+stats, shift rest, truncate zone_spawns."""
    # Read vanilla area data
    area_data = bytes(blaze_data[AREA_START:AREA_END])

    new_middle = build_new_middle_section(area_data)
    elite_stats = build_elite_stats(area_data)

    # Vanilla section boundaries (relative to area start)
    vanilla_middle_end = VANILLA_MIDDLE_SIZE               # 124
    vanilla_stats_end  = vanilla_middle_end + VANILLA_STATS_SIZE  # 412

    # How much "rest" data we can keep (script + spawns + formations + zone_spawns)
    rest_budget = AREA_SIZE - NEW_MIDDLE_SIZE - (4 * 96)  # 8520 - 168 - 384 = 7968

    # Build new area data
    new_area = bytearray(
        new_middle                                               # 168 bytes
        + area_data[vanilla_middle_end:vanilla_stats_end]        # 288 bytes (stats 0,1,2)
        + elite_stats                                            # 96 bytes
        + area_data[vanilla_stats_end:vanilla_stats_end + rest_budget]  # 7968 bytes
    )

    assert len(new_area) == AREA_SIZE, \
        "Area size mismatch: {} != {}".format(len(new_area), AREA_SIZE)

    # Fix stale offset fields in script command entries + add 4th type07 entry
    _patch_script_offsets(new_area)

    # Write back in-place (no file size change)
    blaze_data[AREA_START:AREA_END] = new_area

    return new_middle, elite_stats


def verify_vanilla_state(blaze_data):
    """Check if binary is in vanilla (unexpanded) state."""
    # Vanilla: stats start at VANILLA_GROUP_OFFSET with "Lv20"
    if blaze_data[VANILLA_GROUP_OFFSET:VANILLA_GROUP_OFFSET + 4] == b'Lv20':
        return True
    # Already expanded: stats at NEW_GROUP_OFFSET
    if blaze_data[NEW_GROUP_OFFSET:NEW_GROUP_OFFSET + 4] == b'Lv20':
        return None  # Already expanded
    return False


def update_json():
    """Update area JSON with correct 4-monster offsets."""
    with open(AREA_JSON, 'r', encoding='utf-8') as f:
        area = json.load(f)

    # Skip if already correct (check group_offset matches expected)
    current_group = area.get("group_offset", "")
    if current_group.lower() == hex(NEW_GROUP_OFFSET).lower():
        return False  # Already correct

    # -- Determine correction needed --
    # If JSON still has vanilla offsets (3 monsters), apply full shift from vanilla.
    # If JSON has old-script offsets (4 monsters, shifted by +0x84), apply +0x08 correction.
    n_monsters = len(area.get("monsters", []))

    if n_monsters == 3:
        # Fresh vanilla JSON: apply full shifts from vanilla
        GROUP_SHIFT = MIDDLE_EXPANSION  # 44 = 0x2C
        FULL_SHIFT = TOTAL_EXPANSION    # 140 = 0x8C
    elif n_monsters == 4:
        # Old script already shifted by +0x84 (132). Need +0x8C (140). Delta = +8.
        GROUP_SHIFT = 0x08
        FULL_SHIFT = 0x08
    else:
        print("  [ERROR] Unexpected monster count: {}".format(n_monsters))
        return False

    def shift_hex(hex_str, delta):
        return hex(int(hex_str, 16) + delta)

    # -- Monsters and slot_types --
    area["monsters"] = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "E-Shaman"]
    area["slot_types"] = ["00000000", "02000000", "00000a00", "03000000"]

    # -- Group offset --
    if n_monsters == 3:
        area["group_offset"] = hex(NEW_GROUP_OFFSET)
    else:
        area["group_offset"] = shift_hex(area["group_offset"], GROUP_SHIFT)

    # -- Post-stats area offsets --
    for key in ["formation_area_start", "spawn_points_area_start",
                "zone_spawns_area_start"]:
        if key in area:
            area[key] = shift_hex(area[key], FULL_SHIFT)

    area["zone_spawns_area_bytes"] = NEW_ZONE_SPAWNS_BYTES

    # -- Animation table (absolute offsets within middle section) --
    shaman_bytes = area["animation_table"][1]["bytes"] if len(area["animation_table"]) > 1 else "0606070708090a0b"
    area["animation_table"] = [
        {"bytes": area["animation_table"][0]["bytes"], "offset": hex(AREA_START + 0x0C)},
        {"bytes": area["animation_table"][1]["bytes"], "offset": hex(AREA_START + 0x14)},
        {"bytes": area["animation_table"][2]["bytes"], "offset": hex(AREA_START + 0x1C)},
        {"bytes": shaman_bytes, "offset": hex(AREA_START + 0x24)},
    ]

    # -- Records 8byte (unpointed entries, absolute offsets) --
    # Slot 3 (E-Shaman) texref = 0x0006C000 (pattern: i*0x14000+0x30000, i=3)
    area["records_8byte"] = [
        {"anim_offset": "0x000C", "texture_ref": "0x00030000", "offset": hex(AREA_START + 0x4C)},
        {"anim_offset": "0x0014", "texture_ref": "0x00044000", "offset": hex(AREA_START + 0x54)},
        {"anim_offset": "0x001C", "texture_ref": "0x00058000", "offset": hex(AREA_START + 0x5C)},
        {"anim_offset": "0x0024", "texture_ref": "0x0006C000", "offset": hex(AREA_START + 0x64)},
    ]

    # -- Assignment entries (absolute offsets within middle section) --
    # R values read from vanilla binary: slot0=2, slot1=3, slot2=4
    area["assignment_entries"] = [
        {"slot": 0, "L": 0, "R": 2, "offset": hex(AREA_START + 0x88)},
        {"slot": 1, "L": 1, "R": 3, "offset": hex(AREA_START + 0x90)},
        {"slot": 2, "L": 3, "R": 4, "offset": hex(AREA_START + 0x98)},
        {"slot": 3, "L": 1, "R": 5, "offset": hex(AREA_START + 0xA0)},
    ]

    # -- Type07 entries (in script area, apply FULL_SHIFT from vanilla) --
    # Also update vram_offset (the stored offset value within each entry).
    # Vanilla vram_offsets 0x0580/0x0588/0x0590 pointed into the script area;
    # after +0x8C expansion those data blocks shifted, so vram_offsets need +0x8C too.
    vanilla_type07_abs = [0xF7ABE4, 0xF7ABEC, 0xF7ABF4]
    vanilla_vram_offsets = [0x0580, 0x0588, 0x0590]
    entries = area.get("type07_entries", [])
    for i in range(min(len(entries), len(vanilla_type07_abs))):
        entries[i]["offset"] = hex(vanilla_type07_abs[i] + TOTAL_EXPANSION)
        entries[i]["vram_offset"] = hex(vanilla_vram_offsets[i] + TOTAL_EXPANSION)
    # Add 4th type07 entry for E-Shaman (slot 3)
    new_entry = {
        "vram_offset": hex(0x0598 + TOTAL_EXPANSION),  # 0x0624
        "idx": 19,
        "offset": hex(0xF7ABF4 + TOTAL_EXPANSION + 8),  # 0xF7AC88
    }
    if len(entries) < 4:
        entries.append(new_entry)
    else:
        entries[3] = new_entry
    area["type07_entries"] = entries
    # Update monster_vram_ref for display in editor
    area["monster_vram_ref"] = {
        "Lv20.Goblin":   hex(0x0580 + TOTAL_EXPANSION),
        "Goblin-Shaman": hex(0x0588 + TOTAL_EXPANSION),
        "Giant-Bat":     hex(0x0590 + TOTAL_EXPANSION),
        "E-Shaman":      hex(0x0598 + TOTAL_EXPANSION),
    }

    # -- Spawn points (record offsets shifted by FULL_SHIFT) --
    for sp in area.get("spawn_points", []):
        if "offset" in sp:
            sp["offset"] = shift_hex(sp["offset"], FULL_SHIFT)
        for rec in sp.get("records", []):
            if "offset" in rec:
                rec["offset"] = shift_hex(rec["offset"], FULL_SHIFT)

    # -- Zone spawns (record offsets shifted by FULL_SHIFT) --
    for zs in area.get("zone_spawns", []):
        if "offset" in zs:
            zs["offset"] = shift_hex(zs["offset"], FULL_SHIFT)
        for rec in zs.get("records", []):
            if "offset" in rec:
                rec["offset"] = shift_hex(rec["offset"], FULL_SHIFT)

    # -- Save floor_1_area_1.json --
    with open(AREA_JSON, 'w', encoding='utf-8') as f:
        json.dump(area, f, indent=2)

    # -- Also update cavern_of_death.json (used by patch_spawn_groups.py) --
    if SPAWN_GROUPS_JSON.exists():
        with open(SPAWN_GROUPS_JSON, 'r', encoding='utf-8') as f:
            sg = json.load(f)
        for grp in sg.get("groups", []):
            if grp.get("name") == "Floor 1 - Area 1":
                grp["offset"] = hex(NEW_GROUP_OFFSET)
                grp["monsters"] = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "E-Shaman"]
                break
        with open(SPAWN_GROUPS_JSON, 'w', encoding='utf-8') as f:
            json.dump(sg, f, indent=2)

    return True


def revert_json_to_n3():
    """Revert area JSONs to vanilla N=3 layout (no expansion).

    Keeps formation compositions unchanged (all use slots 0,1,2 — no slot 3).
    Reverts all offsets to vanilla values so other patchers work correctly.
    Always reverts BOTH floor_1_area_1.json AND cavern_of_death.json.
    """
    def shift_hex(hex_str, delta):
        return hex(int(hex_str, 16) + delta)

    # ---- Always revert cavern_of_death.json (patch_spawn_groups.py reads this) ----
    # With vanilla BLAZE.ALL (N=3, middle=124 bytes), stats are at 0xF7A97C.
    # offset=0xF7A9A8 + 4 monsters would write 384 bytes into the script area → crash.
    sg_changed = False
    if SPAWN_GROUPS_JSON.exists():
        with open(SPAWN_GROUPS_JSON, 'r', encoding='utf-8') as f:
            sg = json.load(f)
        for grp in sg.get("groups", []):
            if grp.get("name") == "Floor 1 - Area 1":
                if (grp.get("offset", "").lower() != hex(VANILLA_GROUP_OFFSET).lower()
                        or len(grp.get("monsters", [])) != 3):
                    grp["offset"] = hex(VANILLA_GROUP_OFFSET)
                    grp["monsters"] = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]
                    sg_changed = True
                break
        if sg_changed:
            with open(SPAWN_GROUPS_JSON, 'w', encoding='utf-8') as f:
                json.dump(sg, f, indent=2)
            print("  [OK] cavern_of_death.json reverted to N=3")
        else:
            print("  [SKIP] cavern_of_death.json already N=3")

    # ---- Revert floor_1_area_1.json if needed ----
    with open(AREA_JSON, 'r', encoding='utf-8') as f:
        area = json.load(f)

    if (len(area.get("monsters", [])) == 3 and
            area.get("group_offset", "").lower() == hex(VANILLA_GROUP_OFFSET).lower()):
        print("  [SKIP] floor_1_area_1.json already N=3")
        return sg_changed  # cavern_of_death.json may still have been updated above

    # -- Monsters and slot_types (N=3) --
    area["monsters"] = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]
    area["slot_types"] = ["00000000", "02000000", "00000a00"]

    # -- Group offset --
    area["group_offset"] = hex(VANILLA_GROUP_OFFSET)

    # -- Post-stats area offsets --
    area["formation_area_start"]    = hex(VANILLA_FORMATION_START)
    area["spawn_points_area_start"] = hex(VANILLA_SPAWN_POINTS_START)
    area["zone_spawns_area_start"]  = hex(VANILLA_ZONE_SPAWNS_START)
    area["zone_spawns_area_bytes"]  = VANILLA_ZONE_SPAWNS_BYTES

    # -- Remove expansion-only flags --
    area.pop("skip_formation_rewrite", None)
    # Keep skip_offset_table_update: True in vanilla mode.
    # update_offset_table() uses Method 2 (fm_idx = 2 + spawn_point_count = 4)
    # which lands in the ROOT TABLE (indices 5-11 hold config values 0x027C etc.).
    # Writing formation offsets there corrupts the root table → crash.
    # The vanilla offset table already points correctly to formation_area_start
    # (0xF7AFFC), so no update is needed when formation_start hasn't moved.
    area["skip_offset_table_update"] = True

    # -- Animation table (N=3: 3 entries at vanilla absolute offsets) --
    current_anim = area.get("animation_table", [])
    if len(current_anim) >= 3:
        area["animation_table"] = [
            {"bytes": current_anim[0]["bytes"], "offset": hex(AREA_START + 0x0C)},
            {"bytes": current_anim[1]["bytes"], "offset": hex(AREA_START + 0x14)},
            {"bytes": current_anim[2]["bytes"], "offset": hex(AREA_START + 0x1C)},
        ]

    # -- Records 8byte (N=3: 2 unpointed entries at +0x3C, +0x44) --
    current_rec = area.get("records_8byte", [])
    if len(current_rec) >= 2:
        area["records_8byte"] = [
            {"anim_offset": current_rec[0].get("anim_offset", "0x000c"),
             "texture_ref": current_rec[0].get("texture_ref", "0x00030000"),
             "offset": hex(AREA_START + 0x3C)},
            {"anim_offset": current_rec[1].get("anim_offset", "0x0014"),
             "texture_ref": current_rec[1].get("texture_ref", "0x00044000"),
             "offset": hex(AREA_START + 0x44)},
        ]

    # -- Assignment entries (N=3: 3 entries at +0x64) --
    area["assignment_entries"] = [
        {"slot": 0, "L": 0, "R": 2, "offset": hex(AREA_START + 0x64)},
        {"slot": 1, "L": 1, "R": 3, "offset": hex(AREA_START + 0x6C)},
        {"slot": 2, "L": 3, "R": 4, "offset": hex(AREA_START + 0x74)},
    ]

    # -- Type07 entries (revert to vanilla absolute offsets, 3 entries) --
    vanilla_type07_abs   = [0xF7ABE4, 0xF7ABEC, 0xF7ABF4]
    vanilla_vram_offsets = [0x0580,   0x0588,   0x0590]
    current_type07 = area.get("type07_entries", [])
    area["type07_entries"] = [
        {
            "vram_offset": hex(vanilla_vram_offsets[i]),
            "idx": current_type07[i]["idx"] if i < len(current_type07) else 19,
            "offset": hex(vanilla_type07_abs[i]),
        }
        for i in range(3)
    ]
    area["monster_vram_ref"] = {
        "Lv20.Goblin":   hex(0x0580),
        "Goblin-Shaman": hex(0x0588),
        "Giant-Bat":     hex(0x0590),
    }

    # -- Spawn points records (shift back by -TOTAL_EXPANSION) --
    for sp in area.get("spawn_points", []):
        if "offset" in sp:
            sp["offset"] = shift_hex(sp["offset"], -TOTAL_EXPANSION)
        for rec in sp.get("records", []):
            if "offset" in rec:
                rec["offset"] = shift_hex(rec["offset"], -TOTAL_EXPANSION)

    # -- Zone spawns records (shift back by -TOTAL_EXPANSION) --
    for zs in area.get("zone_spawns", []):
        if "offset" in zs:
            zs["offset"] = shift_hex(zs["offset"], -TOTAL_EXPANSION)
        for rec in zs.get("records", []):
            if "offset" in rec:
                rec["offset"] = shift_hex(rec["offset"], -TOTAL_EXPANSION)

    # -- Save floor_1_area_1.json --
    with open(AREA_JSON, 'w', encoding='utf-8') as f:
        json.dump(area, f, indent=2)

    return True


def main():
    print("=" * 60)
    print("  Add Elite Shaman Slot - Cavern F1 Area 1 (v2 in-place)")
    print("=" * 60)
    print()

    # -- Handle --no-expand: revert JSONs to N=3, skip binary changes --
    if '--no-expand' in sys.argv:
        print("[--no-expand] Skipping binary expansion, reverting JSONs to N=3...")
        revert_json_to_n3()
        print("[OK] Done")
        print()
        return 0

    if not BLAZE_ALL.exists():
        print("[ERROR] BLAZE.ALL not found: {}".format(BLAZE_ALL))
        return 1

    data = bytearray(BLAZE_ALL.read_bytes())
    original_size = len(data)
    print("[OK] Loaded BLAZE.ALL ({:,} bytes)".format(original_size))

    # -- Verify vanilla state --
    state = verify_vanilla_state(data)
    if state is None:
        print("[SKIP] Already expanded (stats found at expanded position)")
        return 0
    if state is False:
        print("[ERROR] Unexpected binary state - neither vanilla nor expanded")
        return 1

    print("[OK] Vanilla state confirmed")
    print()

    # -- Step 1: Rewrite area in-place --
    print("[1/2] Rewriting area in-place (+{} bytes shift, {} total)...".format(
        TOTAL_EXPANSION, AREA_SIZE))
    new_middle, elite_stats = rewrite_area_inplace(data)

    # Verify file size unchanged
    assert len(data) == original_size, \
        "File size changed: {} != {}".format(len(data), original_size)
    print("  Middle section: {} -> {} bytes".format(VANILLA_MIDDLE_SIZE, NEW_MIDDLE_SIZE))
    print("  Stats: {} -> {} bytes".format(VANILLA_STATS_SIZE, 4 * 96))
    print("  Zone spawns: {} -> {} bytes (-{} truncated)".format(
        VANILLA_ZONE_SPAWNS_BYTES, NEW_ZONE_SPAWNS_BYTES, TOTAL_EXPANSION))

    # Print E-Shaman stats
    name = elite_stats[0:16].rstrip(b'\x00').decode('ascii', errors='replace')
    hp = struct.unpack_from('<H', elite_stats, 0x14)[0]
    magic = struct.unpack_from('<H', elite_stats, 0x16)[0]
    dmg = struct.unpack_from('<H', elite_stats, 0x30)[0]
    armor = struct.unpack_from('<H', elite_stats, 0x32)[0]
    print("  E-Shaman: HP={} Magic={} Dmg={} Armor={}".format(hp, magic, dmg, armor))
    print()

    # -- Verify stats are at new position --
    if data[NEW_GROUP_OFFSET:NEW_GROUP_OFFSET + 4] != b'Lv20':
        print("[ERROR] Stats not found at expected new position 0x{:X}".format(NEW_GROUP_OFFSET))
        return 1
    print("[OK] Stats verified at new group_offset 0x{:X}".format(NEW_GROUP_OFFSET))

    # -- Step 1b: Patch overlay data table refs --
    # These are non-aligned uint32 LE entries in the Cavern overlay data table.
    # NOT code — verified: surrounding "instructions" decode to invalid MIPS opcodes
    # (0x0000F7AF, 0xFCB8EE89) confirming these are data, not GTE instructions.
    print("[1b/2] Patching overlay data table refs...")
    overlay_refs = [
        # (offset_in_blaze, old_value, new_value, description)
        (0x18920CB, 0x00F7AFFC, NEW_FORMATION_START,    "formation_start"),
        (0x1892133, 0x00F7AFFC, NEW_FORMATION_START,    "formation_start"),
        (0x189234B, 0x00F7AFFC, NEW_FORMATION_START,    "formation_start"),
        (0x18923B3, 0x00F7AFFC, NEW_FORMATION_START,    "formation_start"),
        (0x18920DB, 0x00F7B8FC, 0x00F7B8FC + TOTAL_EXPANSION, "zone_spawns"),
        (0x189235B, 0x00F7B8FC, 0x00F7B8FC + TOTAL_EXPANSION, "zone_spawns"),
    ]
    patched_refs = 0
    for off, old_val, new_val, desc in overlay_refs:
        current = struct.unpack_from('<I', data, off)[0]
        if current != old_val:
            print("  [WARN] 0x{:08X} ({}): expected 0x{:08X}, found 0x{:08X}".format(
                off, desc, old_val, current))
            continue
        struct.pack_into('<I', data, off, new_val)
        patched_refs += 1
    print("  Patched {}/{} overlay refs".format(patched_refs, len(overlay_refs)))
    print()

    # -- Save binary --
    BLAZE_ALL.write_bytes(data)
    print("[OK] Saved BLAZE.ALL ({:,} bytes, size unchanged)".format(len(data)))
    print()

    # -- Step 2: Update JSON --
    print("[2/2] Updating area JSON...")
    if update_json():
        print("  [OK] JSON updated with 4-monster offsets")
    else:
        print("  [SKIP] JSON already has correct offsets")

    print()
    print("=" * 60)
    print("  In-place expansion complete!")
    print("  Layout:")
    print("    Middle:     0x{:X} ({} bytes)".format(AREA_START, NEW_MIDDLE_SIZE))
    print("    Stats:      0x{:X} ({} bytes)".format(NEW_GROUP_OFFSET, 4 * 96))
    print("    Script:     0x{:X}".format(NEW_STATS_END))
    print("    Spawns:     0x{:X}".format(NEW_SPAWN_POINTS_START))
    print("    Formations: 0x{:X}".format(NEW_FORMATION_START))
    print("    Zone spawns:0x{:X} ({} bytes)".format(NEW_ZONE_SPAWNS_START, NEW_ZONE_SPAWNS_BYTES))
    print("    Area end:   0x{:X} (unchanged)".format(AREA_END))
    print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
