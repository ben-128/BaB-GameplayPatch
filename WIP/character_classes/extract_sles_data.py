"""
extract_sles_data.py - Extract class stats and level tables from SLES
"""

import struct
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SLES_FILE = SCRIPT_DIR.parent.parent / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "SLES_008.45"

# Class names (assumed order based on game)
CLASS_NAMES = ["Warrior", "Priest", "Sorcerer", "Dwarf", "Fairy", "Rogue", "Hunter", "Elf"]


def extract_level_table(data: bytes, offset: int, count: int = 100, as_uint16: bool = True):
    """Extract level progression table"""
    values = []
    step = 2 if as_uint16 else 1
    for i in range(count):
        if as_uint16:
            val = struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0]
        else:
            val = data[offset + i]
        values.append(val)
    return values


def analyze_class_stats_zone(data: bytes):
    """Analyze the zone around 0x0002BBD0 for class stats"""
    print("\n" + "=" * 70)
    print("POTENTIAL CLASS BASE STATS (8 classes x multiple stats)")
    print("=" * 70)

    # Zone 0x0002BBD0 had pattern [6, 7, 5, 8, 7, 7, 6, 8]
    # Let's see if there are multiple 8-byte stat blocks

    start = 0x0002BBA8
    print(f"\nAnalyzing from 0x{start:08X}:")

    # Try to read 7-9 stats for 8 classes (rows = stats, cols = classes)
    print("\n--- Interpretation: 8 consecutive stats, 8 classes each ---")
    print(f"{'Stat':<6}", end="")
    for name in CLASS_NAMES:
        print(f"{name:>8}", end="")
    print()
    print("-" * 70)

    for stat_idx in range(10):
        offset = start + stat_idx * 8
        values = list(data[offset:offset+8])
        stat_names = ["Grow1", "Grow2", "Grow3", "Grow4", "Grow5", "Stat1", "Stat2", "Stat3", "Stat4", "Stat5"]
        print(f"{stat_names[stat_idx]:<6}", end="")
        for v in values:
            print(f"{v:>8}", end="")
        print()


def analyze_level_tables(data: bytes):
    """Extract and display level progression tables"""
    print("\n" + "=" * 70)
    print("LEVEL PROGRESSION TABLES")
    print("=" * 70)

    # Table 1: 0x00033664 - Slow HP progression
    print("\nTable at 0x00033664 (HP progression - slow growth):")
    values = extract_level_table(data, 0x00033664, 50)
    print(f"  Levels 1-50: {values}")
    print(f"  Start: {values[0]}, End: {values[49]}, Growth: +{values[49]-values[0]} over 50 levels")

    # Table 2: 0x0002EAB6 - Linear progression
    print("\nTable at 0x0002EAB6 (HP progression - linear):")
    values = extract_level_table(data, 0x0002EAB6, 50)
    print(f"  Levels 1-50: {values}")
    print(f"  Start: {values[0]}, End: {values[49]}, Growth: +{values[49]-values[0]} over 50 levels")

    # Table 3: Check for more tables
    print("\nTable at 0x00033600 (preceding table):")
    values = extract_level_table(data, 0x00033600, 50)
    print(f"  Levels 1-50: {values}")


def analyze_c820_zone(data: bytes):
    """Analyze the 0x0002C820 zone which had interesting patterns"""
    print("\n" + "=" * 70)
    print("ZONE 0x0002C820 ANALYSIS")
    print("=" * 70)

    start = 0x0002C820
    print("\nRaw data:")
    for i in range(4):
        values = list(data[start + i*16:start + i*16 + 16])
        print(f"  +0x{i*16:02X}: {values}")

    # Interpretation as 5-value class groups
    print("\nAs 5 values per stat (5 columns = 5 something?):")
    print("  Group 1: ", list(data[start:start+5]))  # [5, 10, 15, 20, 26]
    print("  Group 2: ", list(data[start+5:start+10]))  # [5, 11, 16, 19, 22]
    print("  Group 3: ", list(data[start+10:start+15]))  # [3, 7, 9, 12, 16]


def search_for_typical_stats(data: bytes):
    """Search for typical base stat values"""
    print("\n" + "=" * 70)
    print("SEARCHING FOR TYPICAL BASE STAT PATTERNS")
    print("=" * 70)

    # Typical starting HP: 40-100
    # Typical starting MP: 10-80
    # Typical base stats: 8-25

    # Expected pattern for 8 classes:
    # Warrior: HP~80, STR~20, INT~8
    # Sorcerer: HP~50, STR~8, INT~22
    # etc.

    # Search for specific value combinations
    target_patterns = [
        # (description, values to find)
        ("Warrior-like stats (high STR ~20)", [18, 19, 20, 21, 22]),
        ("Sorcerer-like stats (high INT ~22)", [20, 21, 22, 23, 24]),
        ("Dwarf-like stats (high CON ~20)", [18, 19, 20, 21, 22]),
    ]

    print("\nSearching for 8 consecutive bytes with expected stat ranges...")

    # Look for patterns where we have 8 values that could be one stat across 8 classes
    # E.g., STR for all classes: [20, 12, 8, 22, 8, 16, 18, 14]
    found = []
    for offset in range(0, min(len(data) - 8, 0x50000)):
        values = list(data[offset:offset+8])
        if all(5 <= v <= 30 for v in values):
            # Check for variety (different classes have different stats)
            unique = len(set(values))
            if unique >= 4:
                # Check for realistic spread
                if max(values) - min(values) >= 8:
                    found.append((offset, values))

    print(f"\nFound {len(found)} potential single-stat-across-8-classes patterns")
    for offset, values in found[:30]:
        print(f"  0x{offset:08X}: {values}  (range: {min(values)}-{max(values)})")


def extract_and_save(data: bytes):
    """Extract all found data and save to JSON"""
    result = {
        "source": "SLES_008.45",
        "level_tables": {},
        "potential_class_stats": {},
        "notes": []
    }

    # Level tables
    result["level_tables"]["hp_slow_0x33664"] = extract_level_table(data, 0x00033664, 100)
    result["level_tables"]["hp_linear_0x2EAB6"] = extract_level_table(data, 0x0002EAB6, 100)
    result["level_tables"]["stat_0x33600"] = extract_level_table(data, 0x00033600, 100)

    # Potential class stats
    result["potential_class_stats"]["zone_0x2BBD0"] = {
        "classes": CLASS_NAMES,
        "rows": []
    }
    for i in range(10):
        values = list(data[0x0002BBA8 + i*8:0x0002BBA8 + i*8 + 8])
        result["potential_class_stats"]["zone_0x2BBD0"]["rows"].append(values)

    result["potential_class_stats"]["zone_0x2C820"] = list(data[0x0002C820:0x0002C820+32])

    result["notes"] = [
        "Level tables appear to be HP progression (slow and linear variants)",
        "Zone 0x2BBA8-0x2BC00 contains 8-value patterns that could be class stats",
        "Zone 0x2C820 has 5-value patterns (unknown purpose)",
        "No class name strings found in SLES - they are loaded from BLAZE.ALL"
    ]

    output_path = SCRIPT_DIR / "SLES_EXTRACTED_DATA.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\nExtracted data saved to: {output_path}")


def main():
    print("=" * 70)
    print("  SLES Data Extractor")
    print("=" * 70)

    data = SLES_FILE.read_bytes()
    print(f"File size: {len(data):,} bytes")

    analyze_class_stats_zone(data)
    analyze_level_tables(data)
    analyze_c820_zone(data)
    search_for_typical_stats(data)
    extract_and_save(data)


if __name__ == '__main__':
    main()
