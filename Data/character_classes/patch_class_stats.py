"""
patch_class_stats.py
Patches character class growth modifiers and level curves in the game BIN.

These values are stored in SLES_008.45 (the PS1 executable), NOT in BLAZE.ALL.
This script finds SLES in the BIN and patches it directly.

Usage: py -3 patch_class_stats.py
"""

import json
import struct
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CONFIG_FILE = SCRIPT_DIR / "class_growth.json"
BIN_FILE = PROJECT_ROOT / "output" / "Blaze & Blade - Patched.bin"
SLES_FILE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"

# PS1 disc constants
SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048

# SLES offsets for class data
GROWTH_TABLE_OFFSET = 0x0002BBA8       # 10 rows x 8 bytes (growth modifiers)
SECONDARY_TABLE_OFFSET = 0x0002BBF8    # 13 rows x 8 bytes (secondary growth)
STAT_CURVE_OFFSET = 0x00033600         # 100 x uint16 (stat progression)
HP_CURVE_OFFSET = 0x00033664           # 100 x uint16 (HP progression)
LINEAR_CURVE_OFFSET = 0x0002EAB6       # 100 x uint16 (linear progression)

# PS-X EXE header to find SLES in BIN
PSX_HEADER = b"PS-X EXE"

# Growth modifier stat row order (must match JSON key order)
GROWTH_STAT_ORDER = [
    "POW", "INT", "WIL", "STR", "row4_unknown",
    "CON", "AGL", "LUK", "row8_unknown", "row9_unknown"
]

CLASS_NAMES = ["Warrior", "Priest", "Sorcerer", "Dwarf", "Fairy", "Rogue", "Hunter", "Elf"]


def find_sles_in_bin(bin_data: bytes) -> list:
    """Find all occurrences of the SLES executable in the BIN file.
    Returns list of (lba, byte_offset) tuples."""
    locations = []

    # Search for PS-X EXE header in raw sectors
    total_sectors = len(bin_data) // SECTOR_RAW
    for lba in range(total_sectors):
        sector_start = lba * SECTOR_RAW + USER_OFF
        if sector_start + 8 > len(bin_data):
            break
        if bin_data[sector_start:sector_start+8] == PSX_HEADER:
            locations.append((lba, sector_start))

    return locations


def sles_offset_to_bin_offset(sles_offset: int, sles_lba: int) -> int:
    """Convert an offset within SLES to its byte position in the BIN file.
    SLES is stored across consecutive sectors starting at sles_lba."""
    sector_index = sles_offset // USER_SIZE
    offset_in_sector = sles_offset % USER_SIZE
    bin_offset = (sles_lba + sector_index) * SECTOR_RAW + USER_OFF + offset_in_sector
    return bin_offset


def read_sles_bytes(bin_data: bytes, sles_lba: int, sles_offset: int, length: int) -> bytes:
    """Read bytes from SLES within the BIN, handling sector boundaries."""
    result = bytearray()
    remaining = length
    current_sles_offset = sles_offset

    while remaining > 0:
        sector_index = current_sles_offset // USER_SIZE
        offset_in_sector = current_sles_offset % USER_SIZE
        bytes_in_sector = min(remaining, USER_SIZE - offset_in_sector)

        bin_offset = (sles_lba + sector_index) * SECTOR_RAW + USER_OFF + offset_in_sector
        result.extend(bin_data[bin_offset:bin_offset + bytes_in_sector])

        remaining -= bytes_in_sector
        current_sles_offset += bytes_in_sector

    return bytes(result)


def write_sles_bytes(bin_data: bytearray, sles_lba: int, sles_offset: int, data: bytes):
    """Write bytes to SLES within the BIN, handling sector boundaries."""
    remaining = len(data)
    current_sles_offset = sles_offset
    data_pos = 0

    while remaining > 0:
        sector_index = current_sles_offset // USER_SIZE
        offset_in_sector = current_sles_offset % USER_SIZE
        bytes_in_sector = min(remaining, USER_SIZE - offset_in_sector)

        bin_offset = (sles_lba + sector_index) * SECTOR_RAW + USER_OFF + offset_in_sector
        bin_data[bin_offset:bin_offset + bytes_in_sector] = data[data_pos:data_pos + bytes_in_sector]

        remaining -= bytes_in_sector
        current_sles_offset += bytes_in_sector
        data_pos += bytes_in_sector


def verify_sles_location(bin_data: bytes, sles_lba: int) -> bool:
    """Verify this is really SLES by checking for known data patterns."""
    # Check PS-X EXE header
    header = read_sles_bytes(bin_data, sles_lba, 0, 8)
    if header != PSX_HEADER:
        return False

    # Check that growth table area has reasonable values (all bytes 0-15)
    growth_data = read_sles_bytes(bin_data, sles_lba, GROWTH_TABLE_OFFSET, 80)
    if all(0 <= b <= 15 for b in growth_data):
        return True

    return False


def patch_growth_modifiers(bin_data: bytearray, sles_lba: int, config: dict) -> int:
    """Patch growth modifier table. Returns number of bytes patched."""
    growth = config.get("growth_modifiers", {})
    patched = 0

    for row_idx, stat_name in enumerate(GROWTH_STAT_ORDER):
        if stat_name in growth:
            values = growth[stat_name]
            if len(values) != 8:
                print(f"  WARNING: {stat_name} has {len(values)} values (expected 8), skipping")
                continue

            # Clamp to uint8
            row_bytes = bytes(max(0, min(255, v)) for v in values)
            sles_offset = GROWTH_TABLE_OFFSET + row_idx * 8
            write_sles_bytes(bin_data, sles_lba, sles_offset, row_bytes)
            patched += 8

    return patched


def patch_secondary_growth(bin_data: bytearray, sles_lba: int, config: dict) -> int:
    """Patch secondary growth table. Returns number of bytes patched."""
    secondary = config.get("secondary_growth", {})
    rows = secondary.get("rows", [])
    patched = 0

    for row_idx, values in enumerate(rows):
        if len(values) != 8:
            print(f"  WARNING: secondary row {row_idx} has {len(values)} values, skipping")
            continue
        row_bytes = bytes(max(0, min(255, v)) for v in values)
        sles_offset = SECONDARY_TABLE_OFFSET + row_idx * 8
        write_sles_bytes(bin_data, sles_lba, sles_offset, row_bytes)
        patched += 8

    return patched


def patch_level_curve(bin_data: bytearray, sles_lba: int, sles_offset: int,
                      values: list, name: str) -> int:
    """Patch a level progression curve. Returns number of bytes patched."""
    curve_bytes = bytearray()
    for v in values:
        curve_bytes.extend(struct.pack('<H', max(0, min(65535, v))))

    write_sles_bytes(bin_data, sles_lba, sles_offset, bytes(curve_bytes))
    return len(curve_bytes)


def display_growth_table(config: dict):
    """Display current growth modifier configuration."""
    growth = config.get("growth_modifiers", {})

    print("\n  Growth Modifiers (higher = faster growth per level):")
    print(f"  {'Stat':>14}", end="")
    for name in CLASS_NAMES:
        print(f"{name:>9}", end="")
    print()
    print("  " + "-" * 86)

    for stat_name in GROWTH_STAT_ORDER:
        if stat_name in growth:
            values = growth[stat_name]
            print(f"  {stat_name:>14}", end="")
            for v in values:
                print(f"{v:>9}", end="")
            print()


def display_diff(bin_data: bytes, sles_lba: int, config: dict):
    """Show differences between current BIN and config."""
    growth = config.get("growth_modifiers", {})
    has_diff = False

    for row_idx, stat_name in enumerate(GROWTH_STAT_ORDER):
        if stat_name not in growth:
            continue
        new_values = growth[stat_name]
        sles_offset = GROWTH_TABLE_OFFSET + row_idx * 8
        current = list(read_sles_bytes(bin_data, sles_lba, sles_offset, 8))

        if current != new_values:
            if not has_diff:
                print("\n  Changes to apply:")
                print(f"  {'Stat':>14}  {'Current':>40}  {'New':>40}")
                print("  " + "-" * 96)
                has_diff = True
            print(f"  {stat_name:>14}  {str(current):>40}  {str(new_values):>40}")

    if not has_diff:
        print("\n  No changes to growth modifiers (config matches BIN)")


def main():
    print("=" * 60)
    print("  Character Class Stats Patcher")
    print("=" * 60)
    print()

    # Load config
    if not CONFIG_FILE.exists():
        print(f"ERROR: {CONFIG_FILE} not found!")
        return False

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    display_growth_table(config)

    # Check BIN file
    if not BIN_FILE.exists():
        print(f"\nERROR: {BIN_FILE} not found!")
        print("Run build_gameplay_patch.bat first to create the patched BIN.")
        return False

    print(f"\nReading {BIN_FILE.name}...")
    bin_data = bytearray(BIN_FILE.read_bytes())
    print(f"  Size: {len(bin_data):,} bytes")

    # Find SLES in BIN
    print("\nSearching for SLES_008.45 in BIN...")
    locations = find_sles_in_bin(bytes(bin_data))

    if not locations:
        print("ERROR: Could not find PS-X EXE header in BIN!")
        return False

    # Filter to valid SLES locations
    valid_locations = []
    for lba, byte_off in locations:
        if verify_sles_location(bytes(bin_data), lba):
            valid_locations.append((lba, byte_off))
            print(f"  Found SLES at LBA {lba} (byte offset 0x{byte_off:08X})")

    if not valid_locations:
        print("ERROR: Found PS-X EXE headers but none matched SLES data patterns!")
        return False

    print(f"\n  {len(valid_locations)} SLES location(s) found")

    # Show diff
    sles_lba = valid_locations[0][0]
    display_diff(bytes(bin_data), sles_lba, config)

    # Patch at all locations
    total_patched = 0
    for loc_idx, (lba, byte_off) in enumerate(valid_locations):
        print(f"\nPatching SLES copy {loc_idx + 1}/{len(valid_locations)} at LBA {lba}...")

        # 1. Growth modifiers
        n = patch_growth_modifiers(bin_data, lba, config)
        print(f"  Growth modifiers: {n} bytes")
        total_patched += n

        # 2. Secondary growth
        n = patch_secondary_growth(bin_data, lba, config)
        print(f"  Secondary growth: {n} bytes")
        total_patched += n

        # 3. Level curves
        curves = config.get("level_curves", {})

        if "stat_curve" in curves:
            values = curves["stat_curve"]["values"]
            n = patch_level_curve(bin_data, lba, STAT_CURVE_OFFSET, values, "stat_curve")
            print(f"  Stat curve: {n} bytes ({len(values)} levels)")
            total_patched += n

        if "hp_curve" in curves:
            values = curves["hp_curve"]["values"]
            n = patch_level_curve(bin_data, lba, HP_CURVE_OFFSET, values, "hp_curve")
            print(f"  HP curve: {n} bytes ({len(values)} levels)")
            total_patched += n

        if "linear_curve" in curves:
            values = curves["linear_curve"]["values"]
            n = patch_level_curve(bin_data, lba, LINEAR_CURVE_OFFSET, values, "linear_curve")
            print(f"  Linear curve: {n} bytes ({len(values)} levels)")
            total_patched += n

    # Write output
    print(f"\nWriting {BIN_FILE.name}...")
    BIN_FILE.write_bytes(bin_data)

    print()
    print("=" * 60)
    print(f"  Patched {total_patched} bytes across {len(valid_locations)} SLES location(s)")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = main()
    if not success:
        exit(1)
