#!/usr/bin/env python3
"""
Patch monster spell assignments in the game BIN.

Reads config from monster_spells_config.json and patches the SLES_008.45
executable inside the output BIN to change which spell table entries
monsters use when casting spells.

This modifies the initialization code that maps spell-casting bytecode
opcodes to spell table entries loaded from BLAZE.ALL.

Usage (standalone):  py -3 patch_monster_spells.py
Usage (in build):    Called as step 9c from build_gameplay_patch.bat
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "monster_spells_config.json"
BIN_PATH = SCRIPT_DIR.parent.parent / "output" / "Blaze & Blade - Patched.bin"

# Stable search patterns (bytes AFTER the spell index byte)
# We search for the 11 stable bytes, then patch the byte right before them.
#
# Type 0x18 (Goblin-Shaman) at RAM 0x8002B638:
#   [INDEX] 00 06 34  00 00 46 A4  18 00 05 34
#   ori $a2,$zero,INDEX / sh $a2,0($v0) / ori $a1,$zero,0x18
#
# Type 0x12 at RAM 0x8002A790:
#   [INDEX] 00 05 34  00 00 45 A4  12 00 04 34
#   ori $a1,$zero,INDEX / sh $a1,0($v0) / ori $a0,$zero,0x12

PATCHES = {
    "goblin_shaman": {
        "stable_suffix": bytes([0x00, 0x06, 0x34,
                                0x00, 0x00, 0x46, 0xA4,
                                0x18, 0x00, 0x05, 0x34]),
        "default_index": 6,
        "label": "Goblin-Shaman (opcode 0x18)",
    },
    "type_0x12_caster": {
        "stable_suffix": bytes([0x00, 0x05, 0x34,
                                0x00, 0x00, 0x45, 0xA4,
                                0x12, 0x00, 0x04, 0x34]),
        "default_index": 4,
        "label": "Type 0x12 caster",
    },
}


def main():
    print("  Monster Spell Assignment Patcher")
    print("  " + "-" * 40)

    # Load config
    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Check if anything is enabled
    any_enabled = False
    for key in PATCHES:
        entry = config.get(key, {})
        if entry.get("enabled", False):
            any_enabled = True

    if not any_enabled:
        print("  [SKIP] No spell patches enabled in config")
        print("  Edit monster_spells_config.json to enable patches")
        return

    # Check BIN exists
    if not BIN_PATH.exists():
        print(f"  [ERROR] BIN not found: {BIN_PATH}")
        sys.exit(1)

    # Read BIN
    data = bytearray(BIN_PATH.read_bytes())
    patched_count = 0

    for key, patch_info in PATCHES.items():
        entry = config.get(key, {})
        if not entry.get("enabled", False):
            continue

        new_index = entry.get("spell_index", patch_info["default_index"])
        label = patch_info["label"]
        suffix = patch_info["stable_suffix"]

        if new_index < 0 or new_index > 15:
            print(f"  [ERROR] {label}: index {new_index} out of range (0-15)")
            sys.exit(1)

        # Search for the stable suffix in the BIN
        hits = []
        pos = 0
        while True:
            found = data.find(suffix, pos)
            if found == -1:
                break
            # The spell index byte is at found-1
            if found >= 1:
                hits.append(found - 1)
            pos = found + 1

        if not hits:
            print(f"  [ERROR] {label}: pattern not found in BIN!")
            sys.exit(1)

        for hit in hits:
            old_val = data[hit]
            data[hit] = new_index
            print(f"  [PATCH] {label}: index {old_val} -> {new_index} at BIN offset 0x{hit:08X}")
            patched_count += 1

    if patched_count > 0:
        BIN_PATH.write_bytes(data)
        print(f"  [OK] {patched_count} spell patch(es) applied to BIN")
    else:
        print("  [SKIP] No patches applied")


if __name__ == "__main__":
    main()
