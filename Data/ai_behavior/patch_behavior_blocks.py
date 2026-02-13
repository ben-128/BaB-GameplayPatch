#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_behavior_blocks.py
Patches monster behavior blocks in BLAZE.ALL to modify aggression, attack speed, and movement

Behavior blocks control:
- Attack cooldown (timer_04)
- AI decision frequency (timer_08)
- Aggro range (dist_0C)
- Attack range (dist_0E)
- Movement type (flags_02)

Usage:
  py -3 Data/ai_behavior/patch_behavior_blocks.py

This modifies output/BLAZE.ALL only. The BIN injection script will then copy it into the BIN.
"""

import struct
import json
from pathlib import Path

# ===========================================================================
# Configuration
# ===========================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"
CONFIG_FILE = SCRIPT_DIR / "behavior_block_config.json"

# Behavior block header field offsets (32-byte header)
FIELD_OFFSETS = {
    "unk_00": 0x00,      # uint16
    "flags_02": 0x02,    # uint16 - Movement type flags (21=flying, 0=ground)
    "timer_04": 0x04,    # uint16 - Attack cooldown (lower = faster)
    "timer_06": 0x06,    # uint16 - Special behavior timer
    "timer_08": 0x08,    # uint16 - AI decision interval (lower = more responsive)
    "timer_0A": 0x0A,    # uint16 - Unknown timer
    "dist_0C": 0x0C,     # uint16 - Aggro range (higher = aggro from farther)
    "dist_0E": 0x0E,     # uint16 - Attack range (higher = attack from farther)
    "val_10": 0x10,      # uint16
    "val_12": 0x12,      # uint16
    "val_14": 0x14,      # uint16
    "val_16": 0x16,      # uint16
    "val_18": 0x18,      # uint16
    "val_1A": 0x1A,      # uint16
    "val_1C": 0x1C,      # uint16
    "val_1E": 0x1E,      # uint16
}

# ===========================================================================
# Helper functions
# ===========================================================================

def read_uint32_le(data, offset):
    """Read uint32 little-endian"""
    return struct.unpack_from('<I', data, offset)[0]

def write_uint16_le(data, offset, value):
    """Write uint16 little-endian"""
    if value < 0 or value > 65535:
        raise ValueError(f"Value {value} out of range for uint16 (0-65535)")
    struct.pack_into('<H', data, offset, value)

def get_behavior_block_offset(blaze, script_offset, L_value):
    """
    Get absolute offset of behavior block for given L value

    Args:
        blaze: BLAZE.ALL bytearray
        script_offset: Start of script area for this zone
        L_value: AI behavior index from assignment entry

    Returns:
        Absolute offset in BLAZE.ALL, or None if NULL
    """
    # Read root offset table (array of uint32 at script area start)
    root_table_offset = script_offset
    rel_behavior_offset = read_uint32_le(blaze, root_table_offset + L_value * 4)

    if rel_behavior_offset == 0:
        return None  # NULL behavior block

    # Convert relative to absolute
    abs_behavior_offset = script_offset + rel_behavior_offset
    return abs_behavior_offset

def patch_behavior_block(blaze, abs_offset, modifications):
    """
    Patch behavior block fields at given absolute offset

    Args:
        blaze: BLAZE.ALL bytearray
        abs_offset: Absolute offset of behavior block start
        modifications: dict of field_name -> value

    Returns:
        Number of fields modified
    """
    patched_count = 0

    for field_name, value in modifications.items():
        # Skip comment fields
        if field_name.startswith('_'):
            continue

        if field_name not in FIELD_OFFSETS:
            print(f"    WARNING: Unknown field '{field_name}', skipping")
            continue

        field_offset = FIELD_OFFSETS[field_name]
        write_offset = abs_offset + field_offset

        # Read original value
        original = struct.unpack_from('<H', blaze, write_offset)[0]

        # Write new value
        write_uint16_le(blaze, write_offset, value)

        print(f"    {field_name:12s} @ 0x{write_offset:08X}: {original:5d} → {value:5d}")
        patched_count += 1

    return patched_count

# ===========================================================================
# Main
# ===========================================================================

def main():
    print("=" * 80)
    print("  Behavior Block Patcher")
    print("  Modifies monster aggression, attack speed, and movement")
    print("=" * 80)
    print()

    # Load config
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found: {CONFIG_FILE}")
        return

    print(f"Loading config: {CONFIG_FILE.name}")
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if not config.get('behavior_patches', {}).get('enabled', False):
        print("  Behavior patches DISABLED in config")
        print()
        return

    patches = config['behavior_patches']['patches']
    enabled_patches = [p for p in patches if p.get('enabled', False)]

    if not enabled_patches:
        print("  No patches enabled in config")
        print()
        return

    print(f"  Found {len(enabled_patches)} enabled patch(es)")
    print()

    # Load BLAZE.ALL
    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        print("  Run extract_blaze_all.bat first to create output/BLAZE.ALL")
        return

    print(f"Loading {BLAZE_ALL}...")
    blaze = bytearray(BLAZE_ALL.read_bytes())
    print(f"  Size: {len(blaze):,} bytes")
    print()

    # Apply patches
    total_modified = 0

    for patch in enabled_patches:
        zone = patch['zone']
        script_offset = patch['script_offset']
        L = patch['L']
        monster_name = patch['monster_name']
        modifications = patch['modifications']

        print("-" * 80)
        print(f"  Zone: {zone}")
        print(f"  Monster: {monster_name} (L={L})")
        print(f"  Script offset: 0x{script_offset:08X}")
        print()

        # Get behavior block offset
        abs_offset = get_behavior_block_offset(blaze, script_offset, L)

        if abs_offset is None:
            print(f"  ERROR: Behavior block for L={L} is NULL (no behavior block)")
            print(f"  This monster uses default/shared behavior and cannot be modified")
            print(f"  via this system.")
            print()
            continue

        print(f"  Behavior block: 0x{abs_offset:08X}")
        print()
        print("  Modifications:")

        # Patch fields
        modified = patch_behavior_block(blaze, abs_offset, modifications)
        total_modified += modified

        print()
        print(f"  ✓ Modified {modified} field(s)")
        print()

    # Save modified BLAZE.ALL
    if total_modified > 0:
        print("=" * 80)
        print(f"Writing modified BLAZE.ALL ({total_modified} total fields modified)...")
        BLAZE_ALL.write_bytes(blaze)
        print(f"  ✓ Saved to {BLAZE_ALL}")
        print()
        print("Next steps:")
        print("  1. Run build_gameplay_patch.bat (or steps 8-9) to inject into BIN")
        print("  2. Test in-game to verify behavior changes")
        print("  3. Adjust timer/distance values in config if needed")
        print()
        print("WARNINGS:")
        print("  - Timer units are UNKNOWN (frames? frames/10?). Start with small changes.")
        print("  - Distance units are UNKNOWN. 2048 = standard melee, test to confirm.")
        print("  - Extreme values (0 or 65535) may cause unexpected behavior.")
        print()
    else:
        print("=" * 80)
        print("No modifications applied (all patches disabled or NULL behaviors)")
        print()

    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
