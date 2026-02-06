"""
show_class_stats.py
Reads the current class growth data from the BIN and displays it.
Useful to verify patches or extract current values.

Usage: py -3 show_class_stats.py
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BIN_FILE = PROJECT_ROOT / "output" / "Blaze & Blade - Patched.bin"
SLES_FILE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"

SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048

CLASS_NAMES = ["Warrior", "Priest", "Sorcerer", "Dwarf", "Fairy", "Rogue", "Hunter", "Elf"]
STAT_LABELS = ["POW", "INT", "WIL", "STR", "row4?", "CON", "AGL", "LUK", "row8?", "row9?"]

# Offsets in SLES
GROWTH_OFFSET = 0x0002BBA8
SECONDARY_OFFSET = 0x0002BBF8
STAT_CURVE_OFFSET = 0x00033600
HP_CURVE_OFFSET = 0x00033664
LINEAR_CURVE_OFFSET = 0x0002EAB6


def read_sles_data(source: str = "sles"):
    """Read data from either standalone SLES or from BIN"""
    if source == "sles":
        if not SLES_FILE.exists():
            print(f"SLES not found: {SLES_FILE}")
            return None
        return SLES_FILE.read_bytes()
    else:
        if not BIN_FILE.exists():
            print(f"BIN not found: {BIN_FILE}")
            return None

        bin_data = BIN_FILE.read_bytes()
        # Find SLES in BIN
        pos = bin_data.find(b"PS-X EXE")
        if pos == -1:
            print("PS-X EXE header not found in BIN!")
            return None

        lba = (pos - USER_OFF) // SECTOR_RAW
        # Extract SLES content (reconstruct from sectors)
        sles_size = SLES_FILE.stat().st_size if SLES_FILE.exists() else 843776
        result = bytearray()
        for sector in range(sles_size // USER_SIZE + 1):
            bin_off = (lba + sector) * SECTOR_RAW + USER_OFF
            result.extend(bin_data[bin_off:bin_off + USER_SIZE])
        return bytes(result[:sles_size])


def display_growth_table(data: bytes):
    """Display growth modifier table"""
    print("\n  GROWTH MODIFIERS (SLES offset 0x{:08X})".format(GROWTH_OFFSET))
    print("  Higher value = faster stat growth per level-up")
    print()
    print(f"  {'Stat':>14}", end="")
    for name in CLASS_NAMES:
        print(f"{name:>9}", end="")
    print()
    print("  " + "-" * 86)

    for row in range(10):
        offset = GROWTH_OFFSET + row * 8
        values = list(data[offset:offset + 8])
        label = STAT_LABELS[row] if row < len(STAT_LABELS) else f"Row{row}"
        print(f"  {label:>14}", end="")
        for v in values:
            print(f"{v:>9}", end="")
        print()


def display_secondary_table(data: bytes):
    """Display secondary growth table"""
    print("\n  SECONDARY GROWTH (SLES offset 0x{:08X})".format(SECONDARY_OFFSET))
    print()
    print(f"  {'Row':>14}", end="")
    for name in CLASS_NAMES:
        print(f"{name:>9}", end="")
    print()
    print("  " + "-" * 86)

    for row in range(13):
        offset = SECONDARY_OFFSET + row * 8
        values = list(data[offset:offset + 8])
        print(f"  {'S_Row' + str(row):>14}", end="")
        for v in values:
            print(f"{v:>9}", end="")
        print()


def display_level_curves(data: bytes):
    """Display level progression curves"""
    curves = [
        ("Stat Curve", STAT_CURVE_OFFSET, "Main stat progression (STR, INT, etc.)"),
        ("HP Curve", HP_CURVE_OFFSET, "HP/slow progression"),
        ("Linear Curve", LINEAR_CURVE_OFFSET, "Linear/fast progression"),
    ]

    for name, offset, desc in curves:
        values = [struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0] for i in range(100)]
        print(f"\n  {name.upper()} (offset 0x{offset:08X})")
        print(f"  {desc}")
        print(f"  Range: {values[0]} -> {values[99]} (growth: +{values[99]-values[0]})")
        print(f"  Lv  1-10: {values[0:10]}")
        print(f"  Lv 11-20: {values[10:20]}")
        print(f"  Lv 21-30: {values[20:30]}")
        print(f"  Lv 31-40: {values[30:40]}")
        print(f"  Lv 41-50: {values[40:50]}")
        if values[50] > 0:
            print(f"  Lv 51-60: {values[50:60]}")
            print(f"  Lv 61-70: {values[60:70]}")
            print(f"  Lv 71-80: {values[70:80]}")
            print(f"  Lv 81-90: {values[80:90]}")
            print(f"  Lv 91-99: {values[90:100]}")


def compare_sles_vs_bin(sles_data: bytes, bin_sles_data: bytes):
    """Compare original SLES vs patched BIN"""
    print("\n  COMPARISON: Original SLES vs Patched BIN")
    print("  " + "=" * 60)

    has_diff = False
    for row in range(10):
        offset = GROWTH_OFFSET + row * 8
        orig = list(sles_data[offset:offset + 8])
        patched = list(bin_sles_data[offset:offset + 8])
        label = STAT_LABELS[row] if row < len(STAT_LABELS) else f"Row{row}"

        if orig != patched:
            has_diff = True
            print(f"  {label:>14}: {orig} -> {patched}")

    if not has_diff:
        print("  No differences found (BIN matches original SLES)")


def main():
    print("=" * 60)
    print("  Character Class Stats Viewer")
    print("=" * 60)

    # Read from SLES (original)
    print("\n--- ORIGINAL (from SLES_008.45) ---")
    sles_data = read_sles_data("sles")
    if sles_data:
        display_growth_table(sles_data)
        display_secondary_table(sles_data)
        display_level_curves(sles_data)

    # Read from BIN (patched)
    print("\n\n--- PATCHED (from BIN) ---")
    bin_sles_data = read_sles_data("bin")
    if bin_sles_data:
        display_growth_table(bin_sles_data)

    # Compare
    if sles_data and bin_sles_data:
        compare_sles_vs_bin(sles_data, bin_sles_data)


if __name__ == '__main__':
    main()
