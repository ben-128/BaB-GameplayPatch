#!/usr/bin/env python3
"""
Compare vanilla vs patched BLAZE.ALL to find differences.

Specifically looking for changes around:
- Cavern F1 assignment entries (0xF7A964-0xF7A97C)
- Cavern overlay code (if loaded differently)
- Any data that could affect spell_list_index

Usage:
1. Extract vanilla BLAZE.ALL from source BIN:
   - LBA 163167, size ~46MB
2. Run: py -3 compare_vanilla_patched.py vanilla_BLAZE.ALL output/BLAZE.ALL
"""

import sys
from pathlib import Path

def compare_files(vanilla_path, patched_path):
    print("BLAZE.ALL Comparison Tool")
    print("=" * 70)
    print()

    vanilla = Path(vanilla_path)
    patched = Path(patched_path)

    if not vanilla.exists():
        print(f"ERROR: {vanilla} not found")
        print()
        print("To extract vanilla BLAZE.ALL from source BIN:")
        print("  LBA: 163167")
        print("  Size: ~46MB")
        print("  Or use: extract_blaze_from_bin.py")
        return

    if not patched.exists():
        print(f"ERROR: {patched} not found")
        return

    with open(vanilla, 'rb') as f:
        vanilla_data = f.read()

    with open(patched, 'rb') as f:
        patched_data = f.read()

    print(f"Vanilla size: {len(vanilla_data):,} bytes")
    print(f"Patched size: {len(patched_data):,} bytes")
    print()

    if len(vanilla_data) != len(patched_data):
        print("WARNING: Files have different sizes!")
        print()

    # Find all differences
    min_len = min(len(vanilla_data), len(patched_data))
    diffs = []

    print("Scanning for differences...")
    for i in range(min_len):
        if vanilla_data[i] != patched_data[i]:
            diffs.append(i)

    print(f"Found {len(diffs):,} different bytes ({100*len(diffs)/min_len:.2f}%)")
    print()

    # Check specific areas of interest
    print("=" * 70)
    print("AREAS OF INTEREST")
    print("=" * 70)
    print()

    # Cavern F1 assignment entries
    print("1. Cavern F1 Assignment Entries (0xF7A964-0xF7A97C)")
    print("   Goblin (slot 0): 0xF7A964")
    print("   Shaman (slot 1): 0xF7A96C")
    print("   Bat    (slot 2): 0xF7A974")
    print()

    for name, offset in [("Goblin", 0xF7A964), ("Shaman", 0xF7A96C), ("Bat", 0xF7A974)]:
        v_entry = vanilla_data[offset:offset+8]
        p_entry = patched_data[offset:offset+8]

        v_hex = ' '.join(f'{b:02X}' for b in v_entry)
        p_hex = ' '.join(f'{b:02X}' for b in p_entry)

        print(f"   {name:8} vanilla:  {v_hex}")
        print(f"   {name:8} patched:  {p_hex}")

        if v_entry[1] != p_entry[1] or v_entry[5] != p_entry[5]:
            print(f"   {name:8} DIFF:     L={v_entry[1]}->{p_entry[1]}, R={v_entry[5]}->{p_entry[5]}")
        else:
            print(f"   {name:8} L={v_entry[1]}, R={v_entry[5]} (unchanged)")
        print()

    # Show first 20 diffs
    if diffs:
        print("=" * 70)
        print("FIRST 20 DIFFERENCES")
        print("=" * 70)
        print()

        for i, offset in enumerate(diffs[:20]):
            v_byte = vanilla_data[offset]
            p_byte = patched_data[offset]
            print(f"  {hex(offset):>10}: {v_byte:02X} → {p_byte:02X}")

        if len(diffs) > 20:
            print(f"  ... and {len(diffs)-20:,} more differences")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: py -3 compare_vanilla_patched.py <vanilla_BLAZE.ALL> <patched_BLAZE.ALL>")
        print()
        print("Example:")
        print("  py -3 compare_vanilla_patched.py vanilla_BLAZE.ALL output/BLAZE.ALL")
        sys.exit(1)

    compare_files(sys.argv[1], sys.argv[2])
