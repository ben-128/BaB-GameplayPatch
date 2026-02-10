#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Patch spell definition entries in output/BLAZE.ALL.

The REAL spell definition table is at BLAZE.ALL offset 0x908E68, with 48-byte
entries organized in 8 spell lists. This is the SINGLE copy shared by both
players and monsters.

This replaces the old patcher which targeted the spell SET table (6 copies at
0x9E8D8E etc) which only affects player spell learning, NOT monster casting.

Supports modifying individual fields: damage, mp_cost, element, cast_prob, etc.

Usage (standalone):  py -3 Data/spells/patch_spell_table.py
Usage (in build):    Called at step 7b
"""

import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "spell_config.json"
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

SPELL_TABLE_OFFSET = 0x908E68
ENTRY_SIZE = 48

# Spell counts per list (pointer_table indices 0-7)
SPELL_COUNTS = [29, 24, 20, 7, 1, 1, 1, 30]

# Field name -> (offset within 48-byte entry, size in bytes)
FIELD_MAP = {
    "spell_id":    (0x10, 1),
    "cast_time":   (0x13, 1),
    "mp_cost":     (0x14, 1),
    "element":     (0x16, 1),
    "damage":      (0x18, 1),
    "target_type": (0x1C, 1),
    "cast_prob":   (0x1D, 1),
    "param_1E":    (0x1E, 1),
    "ingredient_count": (0x1F, 1),
}


def compute_entry_offset(list_idx, spell_idx):
    """Compute absolute BLAZE.ALL offset for a spell entry."""
    if list_idx < 0 or list_idx >= len(SPELL_COUNTS):
        return None
    if spell_idx < 0 or spell_idx >= SPELL_COUNTS[list_idx]:
        return None
    # Entries are stored contiguously: list0 entries, then list1, etc.
    base = SPELL_TABLE_OFFSET
    for i in range(list_idx):
        base += SPELL_COUNTS[i] * ENTRY_SIZE
    return base + spell_idx * ENTRY_SIZE


def read_spell_name(data, offset):
    """Read 16-byte ASCII name from spell entry."""
    raw = data[offset:offset + 16]
    return ''.join(chr(b) if 32 <= b < 127 else '' for b in raw).strip()


def main():
    print("  Spell Definition Patcher (BLAZE.ALL 0x908E68)")
    print("  " + "-" * 50)

    if not CONFIG_FILE.exists():
        print("  [SKIP] Config not found: {}".format(CONFIG_FILE.name))
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    section = config.get("spell_definition_overrides", {})
    if not section.get("enabled", False):
        print("  [SKIP] spell_definition_overrides not enabled")
        return

    overrides = section.get("overrides", [])
    if not overrides:
        print("  [SKIP] No overrides defined")
        return

    if not BLAZE_ALL.exists():
        print("  [ERROR] BLAZE.ALL not found: {}".format(BLAZE_ALL))
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())
    patched = 0

    for ovr in overrides:
        if not ovr.get("enabled", False):
            continue

        list_idx = ovr.get("list", 0)
        spell_idx = ovr.get("index", 0)
        expected_name = ovr.get("name", "")
        fields = ovr.get("fields", {})

        entry_off = compute_entry_offset(list_idx, spell_idx)
        if entry_off is None:
            print("  [ERROR] Invalid list={} index={}".format(list_idx, spell_idx))
            sys.exit(1)

        if entry_off + ENTRY_SIZE > len(data):
            print("  [ERROR] Offset 0x{:X} out of range".format(entry_off))
            sys.exit(1)

        # Verify spell name matches expected
        actual_name = read_spell_name(data, entry_off)
        if expected_name and actual_name != expected_name:
            print("  [WARN] list[{}][{}]: expected '{}', found '{}' at 0x{:X}".format(
                list_idx, spell_idx, expected_name, actual_name, entry_off))

        # Apply field overrides
        changes = []
        for field_name, new_val in fields.items():
            if field_name not in FIELD_MAP:
                print("  [ERROR] Unknown field '{}' (valid: {})".format(
                    field_name, ", ".join(sorted(FIELD_MAP.keys()))))
                sys.exit(1)

            field_off, field_size = FIELD_MAP[field_name]
            abs_off = entry_off + field_off

            if field_size == 1:
                old_val = data[abs_off]
                new_byte = int(new_val) & 0xFF
                if old_val != new_byte:
                    data[abs_off] = new_byte
                    changes.append("{}:{}->{}".format(field_name, old_val, new_byte))
            elif field_size == 2:
                old_val = struct.unpack_from('<H', data, abs_off)[0]
                new_word = int(new_val) & 0xFFFF
                if old_val != new_word:
                    struct.pack_into('<H', data, abs_off, new_word)
                    changes.append("{}:{}->{}".format(field_name, old_val, new_word))

        if changes:
            print("  [PATCH] list[{}][{}] '{}' at 0x{:X}: {}".format(
                list_idx, spell_idx, actual_name or expected_name,
                entry_off, ", ".join(changes)))
            patched += 1
        else:
            print("  [OK] list[{}][{}] '{}': no changes needed".format(
                list_idx, spell_idx, actual_name or expected_name))

    if patched > 0:
        BLAZE_ALL.write_bytes(data)
        print("  [OK] {} spell definition(s) patched in BLAZE.ALL".format(patched))
    else:
        print("  [SKIP] No spell definition changes applied")


if __name__ == "__main__":
    main()
