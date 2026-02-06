"""
deep_search_sles.py - Deep binary search for character base stats in SLES_008.45

Strategy:
1. Dump wide area around known growth modifiers (0x2BBA8)
2. Search for specific value sequences matching FAQ estimates
3. Search for 8-column tables with stat-like values
4. Try multiple data formats (uint8, uint16, int8, int16)
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SLES_FILE = SCRIPT_DIR.parent.parent / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"

# Class order as found in growth zone
CLASS_NAMES = ["Warrior", "Priest", "Sorcerer", "Dwarf", "Fairy", "Rogue", "Hunter", "Elf"]
STAT_NAMES = ["HP", "MP", "STR", "INT", "WIL", "AGL", "CON", "POW", "LUK"]

# FAQ estimated base stats (class order: War, Pri, Sor, Dwa, Fai, Rog, Hun, Elf)
FAQ_STATS = {
    "HP":  [80, 60, 50, 90, 45, 55, 65, 55],
    "MP":  [20, 50, 60, 15, 70, 25, 30, 40],
    "STR": [20, 12,  8, 22,  8, 16, 18, 14],
    "INT": [10, 16, 22,  8, 20, 12, 10, 18],
    "WIL": [12, 20, 18, 10, 16, 10, 12, 14],
    "AGL": [12, 10, 10,  8, 14, 20, 16, 18],
    "CON": [18, 14, 10, 20,  8, 12, 16, 10],
    "POW": [ 8, 18, 20, 10, 22, 10, 10, 14],
    "LUK": [10, 10, 12, 12, 12, 20,  8, 12],
}


def hexdump(data: bytes, start_offset: int, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start_offset + i:08X}: {hex_part:<{width*3}}  {ascii_part}")
    return '\n'.join(lines)


def dump_wide_zone(data: bytes, center: int, radius: int = 512):
    """Dump a wide zone around a known offset"""
    start = max(0, center - radius)
    end = min(len(data), center + radius)
    print(f"\n{'='*80}")
    print(f"ZONE DUMP: 0x{start:08X} - 0x{end:08X} (center=0x{center:08X})")
    print(f"{'='*80}")
    print(hexdump(data[start:end], start))


def interpret_as_8col_table(data: bytes, offset: int, num_rows: int, fmt: str = "uint8"):
    """Interpret data as an 8-column table"""
    rows = []
    pos = offset
    for r in range(num_rows):
        row = []
        for c in range(8):
            if fmt == "uint8":
                if pos < len(data):
                    row.append(data[pos])
                    pos += 1
            elif fmt == "uint16":
                if pos + 2 <= len(data):
                    row.append(struct.unpack('<H', data[pos:pos+2])[0])
                    pos += 2
            elif fmt == "int16":
                if pos + 2 <= len(data):
                    row.append(struct.unpack('<h', data[pos:pos+2])[0])
                    pos += 2
        rows.append(row)
    return rows


def print_class_table(rows, label="", stat_labels=None):
    """Pretty-print a class table"""
    if label:
        print(f"\n--- {label} ---")
    header = f"{'':>8}"
    for name in CLASS_NAMES:
        header += f"{name:>8}"
    print(header)
    print("-" * (8 + 8 * 8))
    for i, row in enumerate(rows):
        stat = stat_labels[i] if stat_labels and i < len(stat_labels) else f"Row{i}"
        line = f"{stat:>8}"
        for v in row:
            line += f"{v:>8}"
        print(line)


def search_exact_sequence(data: bytes, values: list, fmt: str = "uint8") -> list:
    """Search for an exact sequence of values"""
    results = []
    step = 1 if fmt == "uint8" else 2
    max_offset = len(data) - len(values) * step

    for offset in range(0, max_offset, 1):
        match = True
        for i, expected in enumerate(values):
            pos = offset + i * step
            if fmt == "uint8":
                actual = data[pos]
            elif fmt == "uint16":
                actual = struct.unpack('<H', data[pos:pos+2])[0]
            else:
                actual = data[pos]

            if actual != expected:
                match = False
                break

        if match:
            results.append(offset)
    return results


def search_approximate_sequence(data: bytes, values: list, tolerance: int = 3, fmt: str = "uint8") -> list:
    """Search for an approximate sequence (within tolerance)"""
    results = []
    step = 1 if fmt == "uint8" else 2
    max_offset = len(data) - len(values) * step

    for offset in range(0, max_offset, 1):
        match = True
        total_diff = 0
        for i, expected in enumerate(values):
            pos = offset + i * step
            if fmt == "uint8":
                actual = data[pos]
            elif fmt == "uint16":
                if pos + 2 > len(data):
                    match = False
                    break
                actual = struct.unpack('<H', data[pos:pos+2])[0]
            else:
                actual = data[pos]

            diff = abs(actual - expected)
            if diff > tolerance:
                match = False
                break
            total_diff += diff

        if match:
            results.append((offset, total_diff))

    # Sort by total difference
    results.sort(key=lambda x: x[1])
    return results


def search_stat_by_stat(data: bytes):
    """Search for each stat's 8-class values individually"""
    print(f"\n{'='*80}")
    print("SEARCHING FOR INDIVIDUAL STAT SEQUENCES (per-stat, 8 classes)")
    print(f"{'='*80}")

    for stat_name, values in FAQ_STATS.items():
        print(f"\n--- {stat_name}: {values} ---")

        # Exact search (uint8)
        exact = search_exact_sequence(data, values, "uint8")
        if exact:
            print(f"  EXACT uint8 matches: {[f'0x{o:08X}' for o in exact[:10]]}")
            for o in exact[:3]:
                print(hexdump(data[o:o+32], o))

        # Exact search (uint16)
        exact16 = search_exact_sequence(data, values, "uint16")
        if exact16:
            print(f"  EXACT uint16 matches: {[f'0x{o:08X}' for o in exact16[:10]]}")

        # Approximate search (tolerance=2, uint8)
        approx = search_approximate_sequence(data, values, tolerance=2, fmt="uint8")
        if approx:
            print(f"  Approximate uint8 (tol=2): {len(approx)} matches")
            for o, diff in approx[:5]:
                actual = list(data[o:o+8])
                print(f"    0x{o:08X}: {actual} (diff={diff})")

        # Approximate search (tolerance=2, uint16)
        approx16 = search_approximate_sequence(data, values, tolerance=2, fmt="uint16")
        if approx16:
            print(f"  Approximate uint16 (tol=2): {len(approx16)} matches")
            for o, diff in approx16[:5]:
                actual = [struct.unpack('<H', data[o+i*2:o+i*2+2])[0] for i in range(8)]
                print(f"    0x{o:08X}: {actual} (diff={diff})")


def search_class_by_class(data: bytes):
    """Search for each class's stats as a contiguous block"""
    print(f"\n{'='*80}")
    print("SEARCHING FOR PER-CLASS STAT BLOCKS")
    print(f"{'='*80}")

    # Reconstruct per-class data from FAQ
    for cls_idx, cls_name in enumerate(CLASS_NAMES):
        stats = [FAQ_STATS[s][cls_idx] for s in STAT_NAMES]
        print(f"\n--- {cls_name}: {stats} ---")

        # Search for these 9 values as consecutive bytes
        approx = search_approximate_sequence(data, stats, tolerance=3, fmt="uint8")
        if approx:
            print(f"  Approximate uint8 (tol=3): {len(approx)} matches")
            for o, diff in approx[:5]:
                actual = list(data[o:o+9])
                print(f"    0x{o:08X}: {actual} (diff={diff})")

        # Also try uint16
        approx16 = search_approximate_sequence(data, stats, tolerance=3, fmt="uint16")
        if approx16:
            print(f"  Approximate uint16 (tol=3): {len(approx16)} matches")
            for o, diff in approx16[:3]:
                actual = [struct.unpack('<H', data[o+i*2:o+i*2+2])[0] for i in range(9)]
                print(f"    0x{o:08X}: {actual} (diff={diff})")


def analyze_growth_zone_deep(data: bytes):
    """Deep analysis of the known growth zone and surrounding area"""
    print(f"\n{'='*80}")
    print("DEEP ANALYSIS OF GROWTH ZONE (0x2BB00 - 0x2BD00)")
    print(f"{'='*80}")

    # The known growth modifiers are at 0x2BBA8
    # Let's look at the wide area before and after

    # First, dump as raw hex
    dump_wide_zone(data, 0x0002BBA8, 256)

    # Interpret as 8-column uint8 table (before growth zone)
    for base_offset in range(0x0002BA00, 0x0002BC80, 8):
        rows = interpret_as_8col_table(data, base_offset, 1, "uint8")
        vals = rows[0]
        # Check if all values are in a stat-like range
        if all(5 <= v <= 100 for v in vals) and len(set(vals)) >= 3:
            print(f"  uint8 @ 0x{base_offset:08X}: {vals}")

    # Try uint16 interpretation
    print("\n--- uint16 interpretation around growth zone ---")
    for base_offset in range(0x0002BA00, 0x0002BC80, 16):
        rows = interpret_as_8col_table(data, base_offset, 1, "uint16")
        vals = rows[0]
        if all(5 <= v <= 200 for v in vals) and len(set(vals)) >= 3:
            print(f"  uint16 @ 0x{base_offset:08X}: {vals}")

    # Full 8-col table starting at 0x2BBA8
    print("\n--- Growth table at 0x2BBA8 (uint8, 8 cols) ---")
    rows = interpret_as_8col_table(data, 0x0002BBA8, 15, "uint8")
    print_class_table(rows, "Growth modifiers + surrounding data")

    # Check what's BEFORE the growth table
    print("\n--- 256 bytes BEFORE growth table (0x2BAA8) as 8-col uint8 ---")
    rows = interpret_as_8col_table(data, 0x0002BAA8, 32, "uint8")
    print_class_table(rows, "Before growth table")

    # Check what's AFTER the growth table
    print("\n--- 256 bytes AFTER growth table (0x2BC18) as 8-col uint8 ---")
    rows = interpret_as_8col_table(data, 0x0002BC18, 32, "uint8")
    print_class_table(rows, "After growth table")


def search_all_8col_tables(data: bytes, max_offset: int = 0):
    """Search entire SLES for 8-column tables with stat-like values"""
    print(f"\n{'='*80}")
    print("SEARCHING ENTIRE SLES FOR 8-COLUMN STAT TABLES")
    print(f"{'='*80}")

    if max_offset == 0:
        max_offset = len(data)

    # Search for 8 consecutive bytes where values match stat ranges
    # HP-like (40-120) followed by MP-like (10-80)
    print("\n--- HP+MP pattern: 8x HP-like then 8x MP-like (uint8) ---")
    for offset in range(0, max_offset - 16):
        hp_vals = list(data[offset:offset+8])
        mp_vals = list(data[offset+8:offset+16])

        if (all(30 <= v <= 120 for v in hp_vals) and
            all(10 <= v <= 100 for v in mp_vals) and
            len(set(hp_vals)) >= 4 and
            len(set(mp_vals)) >= 4):
            # Check if max HP > max MP (typical RPG)
            if max(hp_vals) > max(mp_vals) or min(hp_vals) > min(mp_vals):
                print(f"  0x{offset:08X}: HP={hp_vals} MP={mp_vals}")

    # Same for uint16
    print("\n--- HP+MP pattern: 8x HP-like then 8x MP-like (uint16) ---")
    for offset in range(0, max_offset - 32, 2):
        hp_vals = [struct.unpack('<H', data[offset+i*2:offset+i*2+2])[0] for i in range(8)]
        mp_vals = [struct.unpack('<H', data[offset+16+i*2:offset+16+i*2+2])[0] for i in range(8)]

        if (all(30 <= v <= 200 for v in hp_vals) and
            all(10 <= v <= 150 for v in mp_vals) and
            len(set(hp_vals)) >= 4 and
            len(set(mp_vals)) >= 4):
            print(f"  0x{offset:08X}: HP={hp_vals} MP={mp_vals}")

    # Search for blocks of 9 rows × 8 cols where ALL values are in stat range
    print("\n--- Complete 9x8 stat tables (uint8, all values 5-30) ---")
    for offset in range(0, max_offset - 72):
        valid = True
        rows = []
        for r in range(9):
            row = list(data[offset + r*8:offset + r*8 + 8])
            if not all(5 <= v <= 30 for v in row):
                valid = False
                break
            if len(set(row)) < 3:
                valid = False
                break
            rows.append(row)
        if valid:
            print(f"\n  0x{offset:08X}:")
            for i, row in enumerate(rows):
                print(f"    {STAT_NAMES[i] if i < 9 else f'Row{i}'}: {row}")


def search_interleaved_patterns(data: bytes):
    """Search for stats stored in interleaved format
    (e.g., class0_stat0, class0_stat1, ..., class1_stat0, class1_stat1, ...)"""
    print(f"\n{'='*80}")
    print("SEARCHING FOR INTERLEAVED (PER-CLASS) STAT BLOCKS")
    print(f"{'='*80}")

    # Each class block: 9 consecutive uint8 values (HP,MP,STR,INT,WIL,AGL,CON,POW,LUK)
    # 8 classes × 9 stats = 72 bytes total

    for offset in range(0, min(len(data) - 72, 0x50000)):
        classes_data = []
        valid = True
        for c in range(8):
            base = offset + c * 9
            stats = list(data[base:base+9])
            # HP should be 30-120
            if not (30 <= stats[0] <= 120):
                valid = False
                break
            # MP should be 10-100
            if not (10 <= stats[1] <= 100):
                valid = False
                break
            # Other stats should be 5-30
            if not all(5 <= s <= 30 for s in stats[2:]):
                valid = False
                break
            classes_data.append(stats)

        if valid:
            print(f"\n  0x{offset:08X} (9 stats per class, uint8):")
            for i, (name, stats) in enumerate(zip(CLASS_NAMES, classes_data)):
                print(f"    {name:>10}: HP={stats[0]:3} MP={stats[1]:3} | {stats[2:]}")

    # Try with uint16
    print("\n--- Same search with uint16 (18 bytes per class, 144 total) ---")
    for offset in range(0, min(len(data) - 144, 0x50000), 2):
        classes_data = []
        valid = True
        for c in range(8):
            base = offset + c * 18
            stats = [struct.unpack('<H', data[base+i*2:base+i*2+2])[0] for i in range(9)]
            if not (30 <= stats[0] <= 200):
                valid = False
                break
            if not (10 <= stats[1] <= 150):
                valid = False
                break
            if not all(5 <= s <= 50 for s in stats[2:]):
                valid = False
                break
            classes_data.append(stats)

        if valid:
            print(f"\n  0x{offset:08X} (9 stats per class, uint16):")
            for i, (name, stats) in enumerate(zip(CLASS_NAMES, classes_data)):
                print(f"    {name:>10}: HP={stats[0]:3} MP={stats[1]:3} | {stats[2:]}")


def search_hp_mp_separately(data: bytes):
    """HP and MP might be stored separately from other stats (wider range)"""
    print(f"\n{'='*80}")
    print("SEARCHING FOR HP/MP SEPARATELY (wider ranges)")
    print(f"{'='*80}")

    # HP for 8 classes as uint16
    hp_target = FAQ_STATS["HP"]  # [80, 60, 50, 90, 45, 55, 65, 55]

    print(f"\nSearching for HP pattern {hp_target} (tolerance=10, uint16):")
    results = search_approximate_sequence(data, hp_target, tolerance=10, fmt="uint16")
    for o, diff in results[:10]:
        actual = [struct.unpack('<H', data[o+i*2:o+i*2+2])[0] for i in range(8)]
        print(f"  0x{o:08X}: {actual} (diff={diff})")

    print(f"\nSearching for HP pattern (tolerance=10, uint8):")
    results = search_approximate_sequence(data, hp_target, tolerance=10, fmt="uint8")
    for o, diff in results[:10]:
        actual = list(data[o:o+8])
        print(f"  0x{o:08X}: {actual} (diff={diff})")


def search_with_different_class_orders(data: bytes):
    """The class order might be different than assumed. Try common orderings."""
    print(f"\n{'='*80}")
    print("TRYING DIFFERENT CLASS ORDERINGS FOR STR")
    print(f"{'='*80}")

    # Original FAQ STR values
    str_vals = FAQ_STATS["STR"]  # [20, 12, 8, 22, 8, 16, 18, 14]

    # Try different orderings
    orderings = {
        "War,Pri,Sor,Dwa,Fai,Rog,Hun,Elf": [20, 12, 8, 22, 8, 16, 18, 14],
        "War,Pri,Rog,Sor,Hun,Elf,Dwa,Fai": [20, 12, 16, 8, 18, 14, 22, 8],
        "War,Rog,Pri,Sor,Hun,Elf,Dwa,Fai": [20, 16, 12, 8, 18, 14, 22, 8],
        "War,Pri,Elf,Sor,Rog,Dwa,Hun,Fai": [20, 12, 14, 8, 16, 22, 18, 8],
        "Fai,Elf,Dwa,Hun,Rog,Sor,Pri,War": [8, 14, 22, 18, 16, 8, 12, 20],
    }

    for order_name, values in orderings.items():
        approx = search_approximate_sequence(data, values, tolerance=3, fmt="uint8")
        if approx:
            print(f"\n  Order [{order_name}]: STR={values}")
            print(f"    Found {len(approx)} matches (uint8, tol=3)")
            for o, diff in approx[:5]:
                actual = list(data[o:o+8])
                # Also show next 64 bytes for context
                print(f"    0x{o:08X}: {actual} (diff={diff})")
                if diff <= 2:
                    # Show wider context
                    print(f"      Context: {list(data[o:o+72])}")

        approx16 = search_approximate_sequence(data, values, tolerance=3, fmt="uint16")
        if approx16:
            print(f"    Found {len(approx16)} matches (uint16, tol=3)")
            for o, diff in approx16[:3]:
                actual = [struct.unpack('<H', data[o+i*2:o+i*2+2])[0] for i in range(8)]
                print(f"    0x{o:08X}: {actual} (diff={diff})")


def check_computed_stats(data: bytes):
    """Maybe stats are computed: base_stat = growth_modifier * some_factor + offset
    Check if growth zone values multiplied by constants give FAQ values"""
    print(f"\n{'='*80}")
    print("CHECKING IF STATS = GROWTH_MODIFIER * FACTOR")
    print(f"{'='*80}")

    # Read growth modifiers
    growth_rows = interpret_as_8col_table(data, 0x0002BBA8, 10, "uint8")

    # For each row, check if multiplying by a constant gives a stat
    for row_idx, row in enumerate(growth_rows):
        for stat_name, faq_values in FAQ_STATS.items():
            # Try to find a multiplier that converts growth values to FAQ values
            if row[0] == 0:
                continue
            factor = faq_values[0] / row[0] if row[0] != 0 else 0
            if factor <= 0 or factor > 20:
                continue

            # Check if this factor works for all classes
            predicted = [round(v * factor) for v in row]
            max_err = max(abs(p - f) for p, f in zip(predicted, faq_values))
            if max_err <= 3:
                print(f"  Growth Row{row_idx} × {factor:.1f} ≈ {stat_name}")
                print(f"    Growth:    {row}")
                print(f"    Predicted: {predicted}")
                print(f"    FAQ:       {faq_values}")
                print(f"    Max error: {max_err}")


def main():
    print("=" * 80)
    print("  DEEP SLES_008.45 BASE STATS SEARCH")
    print("=" * 80)

    if not SLES_FILE.exists():
        print(f"ERROR: {SLES_FILE} not found!")
        return

    data = SLES_FILE.read_bytes()
    print(f"File: {SLES_FILE}")
    print(f"Size: {len(data):,} bytes ({len(data)/1024:.1f} KB)")

    # 1. Deep analysis of known growth zone
    analyze_growth_zone_deep(data)

    # 2. Check if stats = growth * factor
    check_computed_stats(data)

    # 3. Search for individual stat sequences
    search_stat_by_stat(data)

    # 4. Search per-class blocks
    search_class_by_class(data)

    # 5. Search interleaved patterns
    search_interleaved_patterns(data)

    # 6. Try different class orderings
    search_with_different_class_orders(data)

    # 7. Search HP/MP separately with wider tolerance
    search_hp_mp_separately(data)

    # 8. Search all 8-col tables in the whole file
    search_all_8col_tables(data)

    print(f"\n{'='*80}")
    print("  SEARCH COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
