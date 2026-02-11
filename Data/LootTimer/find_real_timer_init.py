#!/usr/bin/env python3
"""
Cross-reference savestate RAM with BLAZE.ALL data tables.

We found:
- 105 occurrences of 1000 in RAM
- 2918 occurrences of 1000 in BLAZE.ALL data tables
- But v12 patches (12 code immediates) don't work

This script finds which of the 2918 data table entries are loaded in RAM,
so we can patch the RIGHT data tables instead of code immediates.
"""

import gzip
import struct
from pathlib import Path


def decompress_savestate(savestate_path):
    """Decompress ePSXe savestate and extract RAM."""
    with gzip.open(savestate_path, 'rb') as f:
        data = f.read()

    ram_offset = 0x1BA
    ram_size = 2 * 1024 * 1024
    ram = data[ram_offset:ram_offset + ram_size]
    return ram


def find_timer_1000_in_ram(ram):
    """Find all RAM addresses containing 1000 as halfword."""
    matches = []
    for i in range(0, len(ram) - 2, 2):
        hw = struct.unpack_from('<H', ram, i)[0]
        if hw == 1000:
            ram_addr = 0x80000000 + i
            matches.append(ram_addr)
    return matches


def find_timer_1000_in_blaze(blaze_data):
    """Find all BLAZE.ALL offsets containing 1000 as halfword (non-code)."""
    matches = []

    # Simple heuristic: skip if surrounded by MIPS-looking code
    for i in range(0, len(blaze_data) - 2, 2):
        hw = struct.unpack_from('<H', blaze_data, i)[0]
        if hw != 1000:
            continue

        # Check if surrounded by code (aligned 4-byte instructions)
        looks_like_code = False
        for offset in range(i - 12, i + 16, 4):
            if 0 <= offset < len(blaze_data) - 4:
                word = struct.unpack_from('<I', blaze_data, offset)[0]
                opcode = (word >> 26) & 0x3F
                # Very common MIPS opcodes
                if opcode in {0x00, 0x02, 0x03, 0x04, 0x05, 0x08, 0x09, 0x0F, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B}:
                    looks_like_code = True
                    break

        if not looks_like_code:
            matches.append(i)

    return matches


def map_blaze_to_ram(blaze_offset):
    """Map BLAZE.ALL offset to potential RAM addresses (overlay mapping)."""
    # Overlay regions (from RESEARCH.md)
    # Main overlay: BLAZE 0x009468A8+ -> RAM 0x80080000+
    # Stub region: BLAZE 0x0091D80C+ -> RAM 0x80056F64+

    potential_rams = []

    # Main overlay
    if blaze_offset >= 0x009468A8:
        ram_main = (blaze_offset - 0x009468A8) + 0x80080000
        potential_rams.append(ram_main)

    # Stub region
    if 0x0091D80C <= blaze_offset < 0x009468A8:
        ram_stub = (blaze_offset - 0x0091D80C) + 0x80056F64
        potential_rams.append(ram_stub)

    return potential_rams


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent

    savestate_path = script_dir / "coffre_avec_argent.gpz"
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    print("="*70)
    print("Find REAL timer init by cross-referencing RAM with BLAZE.ALL")
    print("="*70)
    print()

    # Load savestate RAM
    print(f"Loading savestate: {savestate_path.name}")
    ram = decompress_savestate(savestate_path)
    print(f"  RAM extracted: {len(ram):,} bytes")

    # Find 1000 in RAM
    ram_matches = find_timer_1000_in_ram(ram)
    print(f"  Found {len(ram_matches)} occurrences of 1000 in RAM")
    print()

    # Load BLAZE.ALL
    print(f"Loading: {blaze_path}")
    blaze_data = blaze_path.read_bytes()
    print(f"  Size: {len(blaze_data):,} bytes")

    # Find 1000 in BLAZE data tables
    blaze_matches = find_timer_1000_in_blaze(blaze_data)
    print(f"  Found {len(blaze_matches)} occurrences of 1000 in data tables")
    print()

    # Cross-reference
    print("Cross-referencing BLAZE.ALL with RAM:")
    print("(Looking for BLAZE offsets that map to RAM addresses with 1000)")
    print()

    candidates = []

    for blaze_offset in blaze_matches:
        potential_rams = map_blaze_to_ram(blaze_offset)

        for ram_addr in potential_rams:
            if ram_addr in ram_matches:
                # MATCH! This BLAZE offset corresponds to a RAM address with 1000
                candidates.append({
                    'blaze': blaze_offset,
                    'ram': ram_addr,
                })

    print(f"Found {len(candidates)} MATCHES (BLAZE data -> RAM with 1000):")
    print()

    if not candidates:
        print("No matches found. Timer might be:")
        print("  - In a different overlay region (not main/stub)")
        print("  - Computed dynamically (not from data table)")
        print("  - In BSS/stack (not in BLAZE.ALL file)")
        return

    # Show first 30 matches
    for i, match in enumerate(candidates[:30]):
        print(f"[{i+1}] BLAZE 0x{match['blaze']:08X} -> RAM 0x{match['ram']:08X}")

        # Show context from BLAZE
        offset = match['blaze']
        context_before = []
        context_after = []

        for j in range(offset - 16, offset, 2):
            if j >= 0:
                context_before.append(struct.unpack_from('<H', blaze_data, j)[0])

        for j in range(offset + 2, offset + 18, 2):
            if j < len(blaze_data):
                context_after.append(struct.unpack_from('<H', blaze_data, j)[0])

        print(f"     Before: {' '.join(f'{hw:5d}' for hw in context_before[-4:])}")
        print(f"     >>> 1000 <<<")
        print(f"     After:  {' '.join(f'{hw:5d}' for hw in context_after[:4])}")
        print()

    if len(candidates) > 30:
        print(f"... and {len(candidates) - 30} more matches")

    print("="*70)
    print("Next steps:")
    print("1. Review matches to identify patterns")
    print("2. Create patcher v13 to modify these BLAZE data table offsets")
    print("3. Test if patching data tables works!")
    print("="*70)


if __name__ == '__main__':
    main()
