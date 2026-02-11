#!/usr/bin/env python3
"""
Search for 1000 (0x03E8) in DATA tables (not CODE immediates).

v12 patched CODE immediates, but if the timer comes from a DATA table,
we need to find and patch the table instead.

This script scans BLAZE.ALL for sequences of halfwords containing 0x03E8,
filtering out MIPS code instructions to find real data tables.
"""

import struct
from pathlib import Path


def is_likely_mips_code(data, offset):
    """Check if a 4-byte word looks like MIPS instruction."""
    if offset % 4 != 0:
        return False

    word = struct.unpack_from('<I', data, offset)[0]
    opcode = (word >> 26) & 0x3F

    # Common MIPS opcodes
    common_opcodes = {
        0x00,  # R-type (add, sub, or, sll, etc.)
        0x02, 0x03,  # j, jal
        0x04, 0x05, 0x06, 0x07,  # beq, bne, blez, bgtz
        0x08, 0x09,  # addi, addiu
        0x0A, 0x0B,  # slti, sltiu
        0x0C, 0x0D, 0x0E, 0x0F,  # andi, ori, xori, lui
        0x10, 0x11, 0x12, 0x13,  # cop0, cop1, cop2, cop3
        0x14, 0x15,  # beql, bnel
        0x20, 0x21, 0x22, 0x23,  # lb, lh, lwl, lw
        0x24, 0x25, 0x26,  # lbu, lhu, lwr
        0x28, 0x29, 0x2A, 0x2B,  # sb, sh, swl, sw
        0x2E,  # swr
    }

    return opcode in common_opcodes


def find_data_tables_with_1000(data):
    """Find sequences of halfwords containing 0x03E8 that look like data tables."""
    matches = []

    # Search for 0x03E8 as halfword (not part of instruction)
    for i in range(0, len(data) - 2, 2):
        hw = struct.unpack_from('<H', data, i)[0]

        if hw != 0x03E8:
            continue

        # Check if this looks like code
        # Look at surrounding 4-byte words
        surrounding_is_code = False
        for offset in range(i - 12, i + 16, 4):
            if 0 <= offset < len(data) - 4:
                if is_likely_mips_code(data, offset):
                    surrounding_is_code = True
                    break

        if surrounding_is_code:
            continue  # Skip if surrounded by code

        # This looks like a data table entry
        # Get surrounding context (16 halfwords before and after)
        context_before = []
        context_after = []

        for j in range(i - 32, i, 2):
            if j >= 0:
                context_before.append(struct.unpack_from('<H', data, j)[0])

        for j in range(i + 2, i + 34, 2):
            if j < len(data):
                context_after.append(struct.unpack_from('<H', data, j)[0])

        matches.append({
            'offset': i,
            'context_before': context_before[-8:] if len(context_before) >= 8 else context_before,
            'context_after': context_after[:8] if len(context_after) >= 8 else context_after,
        })

    return matches


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    print("="*70)
    print("Search for 1000 (0x03E8) in DATA tables (not CODE)")
    print("="*70)
    print(f"Analyzing: {blaze_path}")
    print()

    data = blaze_path.read_bytes()
    print(f"BLAZE.ALL size: {len(data):,} bytes")
    print()

    matches = find_data_tables_with_1000(data)
    print(f"Found {len(matches)} potential data table entries with 0x03E8")
    print()

    if not matches:
        print("No data table entries found. Timer might use code immediates only.")
        return

    print("Showing first 20 entries:")
    print()

    for i, match in enumerate(matches[:20]):
        offset = match['offset']
        ram_stub = (offset - 0x0091D80C) + 0x80056F64 if 0x0091D80C <= offset < 0x009468A8 else 0
        ram_main = (offset - 0x009468A8) + 0x80080000 if offset >= 0x009468A8 else 0
        ram = ram_main if ram_main else ram_stub

        print(f"[{i+1}] Offset 0x{offset:08X} (RAM ~0x{ram:08X})")

        print(f"  Context before: ", end="")
        for hw in match['context_before']:
            print(f"{hw:5d} ", end="")
        print()

        print(f"  >>> 1000 (0x03E8) <<<")

        print(f"  Context after:  ", end="")
        for hw in match['context_after']:
            print(f"{hw:5d} ", end="")
        print()
        print()

    if len(matches) > 20:
        print(f"... and {len(matches) - 20} more entries")

    print("="*70)
    print("Next steps:")
    print("1. Review entries to find patterns (sequences, ranges, etc.)")
    print("2. Create patcher to modify these data table entries")
    print("3. Test if patching tables works where code immediates failed")
    print("="*70)


if __name__ == '__main__':
    main()
