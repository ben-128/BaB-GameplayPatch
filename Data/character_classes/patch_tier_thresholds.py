#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""
Spell Tier Threshold Patcher - Modifies EXE tier unlock table.

The EXE dispatch loop (0x80024494) reads tier thresholds from 0x8003C020
to determine how many spells to unlock per tier. This patcher modifies
that table to give faster/complete spell progression.

**APPROACH A1**: Data modification only (no code injection).
**SUCCESS RATE**: 95% (confirmed table read by dispatch loop).

EXE Offset: 0x8003C020 (RAM)
BIN Offset: 0x2C820 (0x8003C020 - 0x80010000 + 0x800)
Size: 8 lists × 5 tiers = 40 bytes

Format: 5 bytes per list (cumulative spell counts)
  byte[0] = Tier 1 count (e.g., 5 spells)
  byte[1] = Tier 2 count (e.g., 10 spells, includes tier 1)
  byte[2] = Tier 3 count
  byte[3] = Tier 4 count
  byte[4] = Tier 5 count

Usage: Called from build_gameplay_patch.bat at step 7g (new step)
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
CONFIG_FILE = SCRIPT_DIR / "tier_thresholds_config.json"
BIN_PATH = PROJECT_DIR / "output" / "Blaze & Blade - Patched.bin"

# SLES → BIN offset conversion
# SLES_008.45 is stored in BIN at LBA 295081
# Each sector = 2352 bytes (24 byte header + 2048 data + 280 EDC/ECC)
# SLES file offset = (RAM_address - 0x80010000) + 0x800
# BIN offset = (LBA * 2352) + 24 + SLES_file_offset

EXE_RAM_OFFSET = 0x8003C020
SLES_FILE_OFFSET = (EXE_RAM_OFFSET - 0x80010000) + 0x800  # = 0x2C820

SLES_LBA = 295081
SECTOR_SIZE = 2352
SECTOR_HEADER = 24
DATA_PER_SECTOR = 2048

# Table structure
NUM_LISTS = 8
TIERS_PER_LIST = 5
TABLE_SIZE = NUM_LISTS * TIERS_PER_LIST  # = 40 bytes

LIST_NAMES = [
    "0_offensive",
    "1_support",
    "2_status",
    "3_herbs",
    "4_wave",
    "5_arrow",
    "6_stardust",
    "7_monster"
]

def load_config():
    """Load configuration from JSON."""
    if not CONFIG_FILE.exists():
        print(f"  [ERROR] Config not found: {CONFIG_FILE}")
        return None

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    section = config.get("tier_thresholds", {})
    if not section.get("enabled", False):
        print("  [SKIP] Tier threshold patching disabled in config")
        return None

    return section.get("lists", {})

def validate_thresholds(thresholds, total_spells, list_name):
    """Validate threshold array."""
    if len(thresholds) != TIERS_PER_LIST:
        print(f"  [ERROR] {list_name}: Expected {TIERS_PER_LIST} thresholds, got {len(thresholds)}")
        return False

    # Check cumulative ordering
    for i in range(1, len(thresholds)):
        if thresholds[i] < thresholds[i-1]:
            print(f"  [ERROR] {list_name}: Thresholds must be cumulative (tier {i+1} < tier {i})")
            return False

    # Check max doesn't exceed total
    if thresholds[-1] > total_spells:
        print(f"  [WARNING] {list_name}: Max threshold {thresholds[-1]} > total spells {total_spells}")

    return True

def sles_offset_to_bin(sles_offset):
    """Convert SLES file offset to BIN offset (handling CD sectors)."""
    # SLES is stored as CD-ROM sectors in BIN
    # Each sector: 24 byte header + 2048 data + 280 EDC/ECC = 2352 total
    # To read byte N from SLES:
    #   sector_num = N // 2048
    #   offset_in_sector = N % 2048
    #   bin_offset = (SLES_LBA + sector_num) * 2352 + 24 + offset_in_sector

    sector_num = sles_offset // 2048
    offset_in_sector = sles_offset % 2048

    bin_offset = (SLES_LBA + sector_num) * SECTOR_SIZE + SECTOR_HEADER + offset_in_sector
    return bin_offset

def read_from_bin_sles(bin_path, sles_offset, size):
    """Read data from SLES in BIN, handling sector boundaries."""
    data = bytearray()

    while len(data) < size:
        # Calculate current position
        current_sles_offset = sles_offset + len(data)
        bin_offset = sles_offset_to_bin(current_sles_offset)

        # How much can we read from this sector?
        offset_in_sector = current_sles_offset % 2048
        bytes_left_in_sector = 2048 - offset_in_sector
        bytes_to_read = min(bytes_left_in_sector, size - len(data))

        # Read from BIN
        with open(bin_path, 'rb') as f:
            f.seek(bin_offset)
            chunk = f.read(bytes_to_read)

        if len(chunk) != bytes_to_read:
            return None

        data.extend(chunk)

    return bytes(data)

def write_to_bin_sles(bin_path, sles_offset, data):
    """Write data to SLES in BIN, handling sector boundaries."""
    written = 0

    with open(bin_path, 'r+b') as f:
        while written < len(data):
            # Calculate current position
            current_sles_offset = sles_offset + written
            bin_offset = sles_offset_to_bin(current_sles_offset)

            # How much can we write to this sector?
            offset_in_sector = current_sles_offset % 2048
            bytes_left_in_sector = 2048 - offset_in_sector
            bytes_to_write = min(bytes_left_in_sector, len(data) - written)

            # Write to BIN
            f.seek(bin_offset)
            f.write(data[written:written + bytes_to_write])

            written += bytes_to_write

    return True

def read_current_table(bin_path):
    """Read current tier threshold table from BIN."""
    if not bin_path.exists():
        print(f"  [ERROR] BIN not found: {bin_path}")
        return None

    data = read_from_bin_sles(bin_path, SLES_FILE_OFFSET, TABLE_SIZE)

    if data is None or len(data) != TABLE_SIZE:
        print(f"  [ERROR] Failed to read {TABLE_SIZE} bytes from SLES offset 0x{SLES_FILE_OFFSET:X}")
        return None

    # Parse into 8 lists of 5 bytes each
    table = []
    for i in range(NUM_LISTS):
        offset = i * TIERS_PER_LIST
        thresholds = list(data[offset:offset + TIERS_PER_LIST])
        table.append(thresholds)

    return table

def write_table(bin_path, table):
    """Write modified tier threshold table to BIN."""
    # Flatten table into bytes
    data = bytearray()
    for thresholds in table:
        data.extend(thresholds)

    if len(data) != TABLE_SIZE:
        print(f"  [ERROR] Table size mismatch: {len(data)} != {TABLE_SIZE}")
        return False

    return write_to_bin_sles(bin_path, SLES_FILE_OFFSET, data)

def format_thresholds(thresholds):
    """Format threshold array for display."""
    return "[" + ", ".join(f"{t:2d}" for t in thresholds) + "]"

def main():
    print("  Spell Tier Threshold Patcher (EXE data table)")
    print("  " + "-" * 50)
    print()

    # Load config
    lists = load_config()
    if lists is None:
        return

    # Read current table
    print(f"  Reading tier table from SLES offset 0x{SLES_FILE_OFFSET:X}...")
    print(f"  (SLES in BIN at LBA {SLES_LBA})")
    current_table = read_current_table(BIN_PATH)
    if current_table is None:
        return

    print(f"  [OK] Read {TABLE_SIZE} bytes")
    print()

    # Build modified table
    modified_table = []
    changes = 0

    for i, list_name in enumerate(LIST_NAMES):
        list_config = lists.get(list_name, {})

        vanilla = list_config.get("vanilla_thresholds", [])
        modded = list_config.get("modded_thresholds", [])
        total = list_config.get("total_spells", 0)
        name = list_config.get("name", list_name)

        if not modded:
            # No config for this list, keep vanilla
            modified_table.append(current_table[i])
            continue

        # Validate
        if not validate_thresholds(modded, total, list_name):
            print(f"  [ERROR] Validation failed for {list_name}")
            return

        # Check if different from current
        current = current_table[i]
        if current != modded:
            print(f"  [{list_name}] {name}")
            print(f"    Current:  {format_thresholds(current)}")
            print(f"    Modified: {format_thresholds(modded)}")

            # Show what changed
            for tier in range(TIERS_PER_LIST):
                if current[tier] != modded[tier]:
                    print(f"      Tier {tier+1}: {current[tier]:2d} → {modded[tier]:2d} spells")

            print()
            changes += 1

        modified_table.append(modded)

    if changes == 0:
        print("  [OK] No changes needed (already patched)")
        return

    # Write modified table
    print(f"  Writing modified table ({changes} lists changed)...")
    if not write_table(BIN_PATH, modified_table):
        print("  [ERROR] Failed to write table")
        return

    # Verify write
    verify_table = read_current_table(BIN_PATH)
    if verify_table != modified_table:
        print("  [ERROR] Verification failed (read-back mismatch)")
        return

    print("  [OK] Tier thresholds patched successfully")
    print()
    print(f"  EXE RAM offset: 0x{EXE_RAM_OFFSET:08X}")
    print(f"  SLES file offset: 0x{SLES_FILE_OFFSET:X}")
    print(f"  SLES in BIN at LBA: {SLES_LBA}")
    print(f"  Lists modified: {changes}/{NUM_LISTS}")
    print()

if __name__ == '__main__':
    import sys
    try:
        main()
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
