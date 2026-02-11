#!/usr/bin/env python3
"""
Patch chest timer in SLES with SELECTIVE offsets (v15).

v14 patched ALL 8 offsets, causing x2 damage increase.

v15: Patch only SOME offsets to isolate which affect chests vs combat.
     Use config to enable/disable each offset group.

8 offsets grouped by memory region:
  Group A (close region 1): 0x014594, 0x014858, 0x014860
  Group B (close region 2): 0x014BE4, 0x014BEC
  Group C (isolated 1):     0x0154A0
  Group D (isolated 2):     0x023D6C
  Group E (isolated 3):     0x02CAE0

Strategy:
1. Test Group A only (most likely chest timers, close addresses)
2. If no effect, try Group B, then C, etc.
3. Find which group affects chests without breaking combat
"""

import json
import struct
import sys
from pathlib import Path

OLD_VALUE = 1000  # Original value to find

# Grouped offsets
OFFSET_GROUPS = {
    'A': [0x014594, 0x014858, 0x014860],  # Close region 1
    'B': [0x014BE4, 0x014BEC],             # Close region 2
    'C': [0x0154A0],                       # Isolated 1
    'D': [0x023D6C],                       # Isolated 2
    'E': [0x02CAE0],                       # Isolated 3
}


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    bin_path = project_dir / 'output' / 'Blaze & Blade - Patched.bin'
    config_path = script_dir / 'loot_timer_v15_config.json'

    # Load config
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        print(f"Create {config_path.name} with enabled_groups and new_value")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    enabled_groups = config.get('enabled_groups', ['A'])
    new_value = config.get('new_value', 2000)

    # Build list of offsets to patch
    offsets_to_patch = []
    for group in enabled_groups:
        if group in OFFSET_GROUPS:
            offsets_to_patch.extend(OFFSET_GROUPS[group])

    if not offsets_to_patch:
        print("[ERROR] No groups enabled in config!")
        sys.exit(1)

    multiplier = new_value / 1000.0

    print("="*60)
    print("Loot Timer v15: Selective offset patching")
    print("="*60)
    print(f"  Config: {config_path}")
    print(f"  Enabled groups: {', '.join(enabled_groups)}")
    print(f"  Offsets to patch: {len(offsets_to_patch)}")
    print(f"  Old value: {OLD_VALUE}")
    print(f"  New value: {new_value} (x{multiplier:.1f} multiplier)")
    print()

    if not bin_path.exists():
        print(f"[ERROR] BIN not found: {bin_path}")
        sys.exit(1)

    # SLES_008.45 at LBA 295081
    SECTOR_SIZE = 2352
    DATA_OFFSET_IN_SECTOR = 24
    DATA_SIZE_IN_SECTOR = 2048
    SLES_LBA = 295081

    data = bytearray(bin_path.read_bytes())
    print(f"  BIN size: {len(data):,} bytes")
    print()

    patched = 0
    skipped = 0

    for sles_offset in offsets_to_patch:
        # Calculate BIN offset
        sectors_from_start = sles_offset // DATA_SIZE_IN_SECTOR
        offset_in_sector = sles_offset % DATA_SIZE_IN_SECTOR
        lba = SLES_LBA + sectors_from_start
        bin_offset = (lba * SECTOR_SIZE) + DATA_OFFSET_IN_SECTOR + offset_in_sector
        ram_addr = (sles_offset - 0x800) + 0x80010000

        # Read current value
        current = struct.unpack_from('<H', data, bin_offset)[0]

        if current == new_value:
            print(f"  SLES 0x{sles_offset:06X} (RAM 0x{ram_addr:08X}): already patched")
            skipped += 1
            continue

        if current != OLD_VALUE:
            print(f"  SLES 0x{sles_offset:06X}: current=0x{current:04X}, patching anyway")

        # Patch
        struct.pack_into('<H', data, bin_offset, new_value)
        patched += 1
        print(f"  PATCH SLES 0x{sles_offset:06X} (RAM 0x{ram_addr:08X}): {current} -> {new_value}")

    if patched == 0:
        print()
        print(f"{'='*60}")
        print(f"  All {len(offsets_to_patch)} values already patched")
        print(f"{'='*60}")
    else:
        bin_path.write_bytes(data)
        print()
        print(f"{'='*60}")
        print(f"  Patched {patched}/{len(offsets_to_patch)} values")
        print(f"  Groups: {', '.join(enabled_groups)}")
        print(f"  Multiplier: x{multiplier:.1f}")
        print()
        print(f"  Test in-game:")
        print(f"    - Do chests stay longer?")
        print(f"    - Are enemy damages x{multiplier:.1f}?")
        print(f"  If chests unchanged, try next group!")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()
