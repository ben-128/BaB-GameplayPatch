"""
patch_class_stats.py
Patches character class growth modifiers and level curves in the game BIN.

These values are stored in SLES_008.45 (the PS1 executable), NOT in BLAZE.ALL.
This script finds SLES in the BIN and patches it directly, with proper
EDC/ECC recalculation for Mode 2 Form 1 sectors.

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

# PS1 disc constants
SECTOR_RAW = 2352
SYNC_SIZE = 12
HEADER_SIZE = 4
SUBHEADER_SIZE = 8
USER_OFF = SYNC_SIZE + HEADER_SIZE + SUBHEADER_SIZE  # 24
USER_SIZE = 2048
EDC_OFF = USER_OFF + USER_SIZE      # 2072
EDC_SIZE = 4
ECC_OFF = EDC_OFF + EDC_SIZE        # 2076
ECC_SIZE = 276

# SLES offsets for class data
GROWTH_TABLE_OFFSET = 0x0002BBA8
SECONDARY_TABLE_OFFSET = 0x0002BBF8
STAT_CURVE_OFFSET = 0x00033600
HP_CURVE_OFFSET = 0x00033664
LINEAR_CURVE_OFFSET = 0x0002EAB6

PSX_HEADER = b"PS-X EXE"

GROWTH_STAT_ORDER = [
    "POW", "INT", "WIL", "STR", "row4_unknown",
    "CON", "AGL", "LUK", "row8_unknown", "row9_unknown"
]

CLASS_NAMES = ["Warrior", "Priest", "Sorcerer", "Dwarf", "Fairy", "Rogue", "Hunter", "Elf"]


# ============================================================
# EDC/ECC calculation for Mode 2 Form 1 sectors
# ============================================================

def _build_edc_table():
    """Build EDC lookup table (CRC-32 with polynomial 0xD8018001)."""
    table = []
    for i in range(256):
        edc = i
        for _ in range(8):
            if edc & 1:
                edc = (edc >> 1) ^ 0xD8018001
            else:
                edc >>= 1
        table.append(edc)
    return table

EDC_TABLE = _build_edc_table()


def compute_edc(data: bytes) -> int:
    """Compute EDC (Error Detection Code) for Mode 2 Form 1."""
    edc = 0
    for b in data:
        edc = EDC_TABLE[(edc ^ b) & 0xFF] ^ (edc >> 8)
    return edc & 0xFFFFFFFF


def _build_ecc_tables():
    """Build ECC F-lookup tables."""
    f_table = bytearray(256)
    b_table = bytearray(256)
    for i in range(256):
        val = i
        val2 = (val << 1) ^ (0x11D if val & 0x80 else 0)
        f_table[i] = val2 & 0xFF
        b_table[i ^ val2] = i
    return f_table, b_table

ECC_F_TABLE, ECC_B_TABLE = _build_ecc_tables()


def compute_ecc_block(data: bytes, major_count: int, minor_count: int, major_step: int, minor_step: int) -> bytearray:
    """Compute one ECC block (P or Q)."""
    result = bytearray(major_count * 2)
    for major in range(major_count):
        idx = major * major_step
        coeff0 = 0
        coeff1 = 0
        for minor in range(minor_count):
            byte_val = data[idx]
            idx = (idx + minor_step) % (minor_count * major_step)  # wrap
            if idx >= len(data):
                byte_val = 0
            coeff0 ^= byte_val
            coeff1 ^= byte_val
            coeff0 = ECC_F_TABLE[coeff0]
        coeff0 = ECC_B_TABLE[coeff0 ^ coeff1]
        result[major * 2] = coeff0
        result[major * 2 + 1] = coeff0 ^ coeff1
    return result


def compute_ecc(sector_data: bytes) -> bytes:
    """Compute ECC (Error Correction Code) for Mode 2 Form 1.
    Input: header(4) + user_data(2048) = 2052 bytes starting at offset 12."""
    # We need to work on: header (4 bytes at offset 12) + user data (2048 bytes at offset 24)
    # But the ECC source is actually: zeroized header + subheader + user data
    # For Mode 2 Form 1: compute over 0x00,0x00,0x00,0x00 (zeroized header) + user data (2048)
    # Actually the standard is: address(4, zeroed) + user_data(2048) = 2052 bytes
    ecc_source = b'\x00' * 4 + sector_data[USER_OFF:USER_OFF + USER_SIZE]

    # P parity: 86 vectors of 24 bytes, step 86
    p_parity = bytearray(172)  # 86 * 2
    for i in range(86):
        coeff0 = 0
        coeff1 = 0
        for j in range(24):
            idx = i + j * 86
            byte_val = ecc_source[idx] if idx < len(ecc_source) else 0
            coeff0 ^= byte_val
            coeff1 ^= byte_val
            coeff0 = ECC_F_TABLE[coeff0]
        coeff0 = ECC_B_TABLE[coeff0 ^ coeff1]
        p_parity[i * 2] = coeff0
        p_parity[i * 2 + 1] = coeff0 ^ coeff1

    # Q parity: 52 vectors of 43 bytes, step 88
    # Source for Q includes: ecc_source (2052) + P parity (172) = 2224 bytes
    q_source = ecc_source + bytes(p_parity)
    q_parity = bytearray(104)  # 52 * 2
    for i in range(52):
        coeff0 = 0
        coeff1 = 0
        for j in range(43):
            idx = (i + j * 88) % 2236
            byte_val = q_source[idx] if idx < len(q_source) else 0
            coeff0 ^= byte_val
            coeff1 ^= byte_val
            coeff0 = ECC_F_TABLE[coeff0]
        coeff0 = ECC_B_TABLE[coeff0 ^ coeff1]
        q_parity[i * 2] = coeff0
        q_parity[i * 2 + 1] = coeff0 ^ coeff1

    return bytes(p_parity) + bytes(q_parity)


def fix_sector_edc_ecc(bin_data: bytearray, sector_lba: int):
    """Recalculate and write EDC and ECC for a Mode 2 Form 1 sector."""
    sector_off = sector_lba * SECTOR_RAW

    # EDC covers: subheader (8 bytes) + user data (2048 bytes) = 2056 bytes
    edc_source = bin_data[sector_off + SYNC_SIZE + HEADER_SIZE:sector_off + EDC_OFF]
    edc = compute_edc(edc_source)
    struct.pack_into('<I', bin_data, sector_off + EDC_OFF, edc)

    # ECC covers the sector
    ecc = compute_ecc(bin_data[sector_off:sector_off + SECTOR_RAW])
    bin_data[sector_off + ECC_OFF:sector_off + ECC_OFF + ECC_SIZE] = ecc


# ============================================================
# SLES patching functions
# ============================================================

def find_sles_in_bin(bin_data: bytes) -> list:
    """Find SLES executable in BIN. Returns list of (lba, byte_offset)."""
    locations = []
    total_sectors = len(bin_data) // SECTOR_RAW
    for lba in range(total_sectors):
        sector_start = lba * SECTOR_RAW + USER_OFF
        if sector_start + 8 > len(bin_data):
            break
        if bin_data[sector_start:sector_start + 8] == PSX_HEADER:
            # Verify growth table area
            growth_sec = lba + (GROWTH_TABLE_OFFSET // USER_SIZE)
            growth_off_in_sec = GROWTH_TABLE_OFFSET % USER_SIZE
            bin_off = growth_sec * SECTOR_RAW + USER_OFF + growth_off_in_sec
            if bin_off + 80 <= len(bin_data):
                growth = bin_data[bin_off:bin_off + 80]
                if all(0 <= b <= 200 for b in growth):
                    locations.append((lba, sector_start))
    return locations


def read_sles_bytes(bin_data: bytes, sles_lba: int, sles_offset: int, length: int) -> bytes:
    """Read bytes from SLES within the BIN, handling sector boundaries."""
    result = bytearray()
    remaining = length
    cur = sles_offset
    while remaining > 0:
        sec = cur // USER_SIZE
        off = cur % USER_SIZE
        n = min(remaining, USER_SIZE - off)
        bin_off = (sles_lba + sec) * SECTOR_RAW + USER_OFF + off
        result.extend(bin_data[bin_off:bin_off + n])
        remaining -= n
        cur += n
    return bytes(result)


def write_sles_bytes(bin_data: bytearray, sles_lba: int, sles_offset: int, data: bytes) -> set:
    """Write bytes to SLES within BIN. Returns set of modified sector LBAs."""
    modified_sectors = set()
    remaining = len(data)
    cur = sles_offset
    pos = 0
    while remaining > 0:
        sec = cur // USER_SIZE
        off = cur % USER_SIZE
        n = min(remaining, USER_SIZE - off)
        sector_lba = sles_lba + sec
        bin_off = sector_lba * SECTOR_RAW + USER_OFF + off
        bin_data[bin_off:bin_off + n] = data[pos:pos + n]
        modified_sectors.add(sector_lba)
        remaining -= n
        cur += n
        pos += n
    return modified_sectors


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
    print("  (with EDC/ECC sector recalculation)")
    print("=" * 60)
    print()

    if not CONFIG_FILE.exists():
        print(f"ERROR: {CONFIG_FILE} not found!")
        return False

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    display_growth_table(config)

    if not BIN_FILE.exists():
        print(f"\nERROR: {BIN_FILE} not found!")
        return False

    print(f"\nReading {BIN_FILE.name}...")
    bin_data = bytearray(BIN_FILE.read_bytes())
    print(f"  Size: {len(bin_data):,} bytes")

    print("\nSearching for SLES_008.45 in BIN...")
    locations = find_sles_in_bin(bytes(bin_data))
    if not locations:
        print("ERROR: Could not find SLES in BIN!")
        return False

    for lba, byte_off in locations:
        print(f"  Found SLES at LBA {lba} (byte offset 0x{byte_off:08X})")

    sles_lba = locations[0][0]
    display_diff(bytes(bin_data), sles_lba, config)

    # Track all modified sectors for EDC/ECC fix
    all_modified_sectors = set()
    total_patched = 0

    for loc_idx, (lba, byte_off) in enumerate(locations):
        print(f"\nPatching SLES copy {loc_idx + 1}/{len(locations)} at LBA {lba}...")

        # 1. Growth modifiers
        growth = config.get("growth_modifiers", {})
        for row_idx, stat_name in enumerate(GROWTH_STAT_ORDER):
            if stat_name in growth:
                values = growth[stat_name]
                if len(values) != 8:
                    continue
                row_bytes = bytes(max(0, min(255, v)) for v in values)
                sles_off = GROWTH_TABLE_OFFSET + row_idx * 8
                modified = write_sles_bytes(bin_data, lba, sles_off, row_bytes)
                all_modified_sectors.update(modified)
                total_patched += 8
        print(f"  Growth modifiers: 80 bytes")

        # 2. Secondary growth
        secondary = config.get("secondary_growth", {})
        rows = secondary.get("rows", [])
        for row_idx, values in enumerate(rows):
            if len(values) != 8:
                continue
            row_bytes = bytes(max(0, min(255, v)) for v in values)
            sles_off = SECONDARY_TABLE_OFFSET + row_idx * 8
            modified = write_sles_bytes(bin_data, lba, sles_off, row_bytes)
            all_modified_sectors.update(modified)
            total_patched += 8
        print(f"  Secondary growth: {len(rows) * 8} bytes")

        # 3. Level curves
        curves = config.get("level_curves", {})
        for curve_name, curve_offset in [("stat_curve", STAT_CURVE_OFFSET),
                                          ("hp_curve", HP_CURVE_OFFSET),
                                          ("linear_curve", LINEAR_CURVE_OFFSET)]:
            if curve_name in curves:
                values = curves[curve_name]["values"]
                curve_bytes = bytearray()
                for v in values:
                    curve_bytes.extend(struct.pack('<H', max(0, min(65535, v))))
                modified = write_sles_bytes(bin_data, lba, curve_offset, bytes(curve_bytes))
                all_modified_sectors.update(modified)
                total_patched += len(curve_bytes)
                print(f"  {curve_name}: {len(curve_bytes)} bytes ({len(values)} levels)")

    # 4. Recalculate EDC/ECC for all modified sectors
    print(f"\nRecalculating EDC/ECC for {len(all_modified_sectors)} modified sectors...")
    for sector_lba in sorted(all_modified_sectors):
        fix_sector_edc_ecc(bin_data, sector_lba)
    print(f"  Done")

    # Write output
    print(f"\nWriting {BIN_FILE.name}...")
    BIN_FILE.write_bytes(bin_data)

    print()
    print("=" * 60)
    print(f"  Patched {total_patched} bytes, fixed {len(all_modified_sectors)} sectors")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = main()
    if not success:
        exit(1)
