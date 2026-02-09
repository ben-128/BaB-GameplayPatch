#!/usr/bin/env python3
"""
Patch AI behavior blocks in output/BLAZE.ALL.

Reads config from ai_behavior_config.json and overwrites specific uint16 fields
in monster behavior blocks. Each patch targets a single field for isolated testing.

Usage (standalone):  py -3 Data/ai_behavior/patch_ai_behavior.py
Usage (in build):    Called before BLAZE.ALL injection into BIN
"""

import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "ai_behavior_config.json"
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"


def main():
    print("  AI Behavior Patcher (BLAZE.ALL)")
    print("  " + "-" * 40)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    patches = config.get("patches", [])
    if not patches:
        print("  [SKIP] No patches in config")
        return

    if not BLAZE_ALL.exists():
        print(f"  [ERROR] BLAZE.ALL not found: {BLAZE_ALL}")
        sys.exit(1)

    data = bytearray(BLAZE_ALL.read_bytes())
    applied = 0

    for patch in patches:
        pid = patch.get("id", "?")
        if not patch.get("enabled", False):
            continue

        blaze_off = int(patch["blaze_offset"], 16)
        field_off = int(patch["field_offset"], 16)
        field_size = patch["field_size"]
        original = patch["original"]
        new_val = patch["value"]

        abs_off = blaze_off + field_off

        if abs_off + field_size > len(data):
            print(f"  [ERROR] {pid}: offset 0x{abs_off:X} out of range")
            sys.exit(1)

        # Read current value
        if field_size == 2:
            cur_val = struct.unpack_from("<H", data, abs_off)[0]
        elif field_size == 4:
            cur_val = struct.unpack_from("<I", data, abs_off)[0]
        else:
            print(f"  [ERROR] {pid}: unsupported field_size {field_size}")
            sys.exit(1)

        # Safety check: verify original matches (catch config errors)
        if cur_val != original:
            print(f"  [WARN] {pid}: expected original={original}, found={cur_val} at 0x{abs_off:X}")
            print(f"         (BLAZE.ALL may already be patched or config is wrong)")

        # Apply patch
        if field_size == 2:
            struct.pack_into("<H", data, abs_off, new_val)
        elif field_size == 4:
            struct.pack_into("<I", data, abs_off, new_val)

        hyp = patch.get("_hypothesis", "")
        # Truncate hypothesis for display
        if len(hyp) > 80:
            hyp = hyp[:77] + "..."
        print(f"  [PATCH] {pid}")
        print(f"    offset 0x{abs_off:X}, field +0x{field_off:02X}: {original} -> {new_val}")
        if hyp:
            print(f"    hypothesis: {hyp}")
        applied += 1

    if applied > 0:
        BLAZE_ALL.write_bytes(data)
        print(f"  [OK] {applied} AI behavior patch(es) applied to BLAZE.ALL")
    else:
        print("  [SKIP] No AI behavior patches enabled")


if __name__ == "__main__":
    main()
