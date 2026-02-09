#!/usr/bin/env python3
"""
Patch spell table entries in output/BLAZE.ALL.

Reads config from monster_spells_config.json and overwrites spell table
entries in BLAZE.ALL directly. This is complementary to patch_monster_spells.py
which patches the EXE's spell_index pointer.

The spell table is at offset 0x9E8D8E in BLAZE.ALL, with 16 entries of 16 bytes each.
Each entry defines offensive spells (bytes 2-9) and support spells (bytes 0-1, 10-15).

Usage (standalone):  py -3 patch_spell_table.py
Usage (in build):    Called before BLAZE.ALL injection into BIN
"""

import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "monster_spells_config.json"
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"

# There are 6 identical copies of the spell table in BLAZE.ALL.
# All must be patched, as the game may load any of them depending on context.
SPELL_TABLE_OFFSETS = [
    0x009E8D8E,  # Copy 1 (originally identified)
    0x00A1755E,  # Copy 2
    0x00A3555E,  # Copy 3
    0x00A5155E,  # Copy 4
    0x00A7BD66,  # Copy 5
    0x00A9B55E,  # Copy 6
]
ENTRY_SIZE = 16
NUM_ENTRIES = 16


def main():
    print("  Spell Table Patcher (BLAZE.ALL)")
    print("  " + "-" * 40)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    overrides = config.get("spell_table_overrides", {})
    if not overrides:
        print("  [SKIP] No spell_table_overrides in config")
        return

    if not BLAZE_ALL.exists():
        print(f"  [ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())
    patched = 0

    for entry_key, override in overrides.items():
        if not override.get("enabled", False):
            continue

        target_idx = int(entry_key)
        if target_idx < 0 or target_idx >= NUM_ENTRIES:
            print(f"  [ERROR] Entry index {target_idx} out of range (0-{NUM_ENTRIES-1})")
            sys.exit(1)

        source_idx = override.get("copy_from")
        custom_bytes = override.get("bytes")

        if source_idx is not None:
            if source_idx < 0 or source_idx >= NUM_ENTRIES:
                print(f"  [ERROR] Source index {source_idx} out of range")
                sys.exit(1)
            # Read source from first copy (clean reference)
            source_off = SPELL_TABLE_OFFSETS[0] + source_idx * ENTRY_SIZE
            new_data = bytes(data[source_off:source_off + ENTRY_SIZE])
            desc = f"copied from entry #{source_idx}"

        elif custom_bytes is not None:
            new_data = bytes.fromhex(custom_bytes.replace(" ", ""))
            if len(new_data) != ENTRY_SIZE:
                print(f"  [ERROR] Entry #{target_idx}: expected {ENTRY_SIZE} bytes, got {len(new_data)}")
                sys.exit(1)
            desc = "custom bytes"

        else:
            continue

        # Patch ALL 6 copies of the spell table
        old_data = data[SPELL_TABLE_OFFSETS[0] + target_idx * ENTRY_SIZE:
                        SPELL_TABLE_OFFSETS[0] + target_idx * ENTRY_SIZE + ENTRY_SIZE]
        print(f"  [PATCH] Entry #{target_idx}: {desc} (x{len(SPELL_TABLE_OFFSETS)} copies)")
        print(f"    Old: {old_data.hex(' ')}")
        print(f"    New: {new_data.hex(' ')}")

        for table_off in SPELL_TABLE_OFFSETS:
            target_off = table_off + target_idx * ENTRY_SIZE
            data[target_off:target_off + ENTRY_SIZE] = new_data

        patched += 1

    if patched > 0:
        BLAZE_ALL.write_bytes(data)
        print(f"  [OK] {patched} spell table patch(es) applied to BLAZE.ALL")
    else:
        print("  [SKIP] No spell table patches applied")


if __name__ == "__main__":
    main()
