#!/usr/bin/env python3
"""Find damage% value in BLAZE.ALL by searching for known code patterns."""

import struct
import sys

def search_sll_sra_pattern(data, start=0):
    """
    Search for the pattern:
      sll a1, s0, 10  (MIPS opcode)
      ...
      sra a1, a1, 16  (MIPS opcode)

    Returns list of (offset, context) tuples.
    """
    results = []

    # MIPS opcodes (little-endian):
    # sll a1, s0, 10  = 0x00102A80 (approximately, need exact encoding)
    # sra a1, a1, 16  = 0x00052C03 (approximately)

    # Let's search for the bit patterns
    # sll: opcode=0, rs=s0=16, rt=a1=5, rd=a1=5, shamt=10, funct=0
    # Encoding: 000000 10000 00101 00101 01010 000000
    #           = 0x00102A80 in hex (little endian: 80 2A 10 00)

    # sra: opcode=0, rs=0, rt=a1=5, rd=a1=5, shamt=16, funct=3
    # Encoding: 000000 00000 00101 00101 10000 000011
    #           = 0x00052C03 in hex (little endian: 03 2C 05 00)

    # Search for sll instruction
    sll_pattern = bytes([0x80, 0x2A, 0x10, 0x00])  # sll a1, s0, 10
    sra_pattern = bytes([0x03, 0x2C, 0x05, 0x00])  # sra a1, a1, 16

    i = start
    while i < len(data) - 4:
        if data[i:i+4] == sll_pattern:
            # Found sll, search for sra nearby (within 20 bytes)
            for j in range(i+4, min(i+24, len(data)-4), 4):
                if data[j:j+4] == sra_pattern:
                    # Found the pattern!
                    context = data[i-16:j+20]
                    results.append((i, j, context))
                    break
        i += 4

    return results

def search_damage_value(data, value=10):
    """
    Search for encoded damage value.
    If damage% is extracted as (s0 << 10) >> 16 = 10,
    then s0 = 40 (0x28).

    Search for 0x28 in context of other game data.
    """
    results = []

    # Search for value 40 (0x28) as different encodings
    patterns = [
        bytes([0x28, 0x00, 0x00, 0x00]),  # u32 little endian
        bytes([0x28, 0x00]),               # u16 little endian
        bytes([0x28]),                     # u8
    ]

    for pattern in patterns:
        i = 0
        while i < len(data) - len(pattern):
            if data[i:i+len(pattern)] == pattern:
                # Found the value, get context
                context = data[max(0, i-32):i+32]
                results.append((i, len(pattern), context))
            i += 1

    return results

def analyze_blaze_all():
    """Analyze BLAZE.ALL for falling rock damage mechanism."""

    blaze_path = "Blaze  Blade - Eternal Quest (Europe)/extract/BLAZE.ALL"

    try:
        with open(blaze_path, "rb") as f:
            data = f.read()

        print(f"BLAZE.ALL loaded: {len(data)} bytes")
        print()

        # Search for the code pattern
        print("=== Searching for sll/sra pattern ===")
        code_results = search_sll_sra_pattern(data)

        if code_results:
            print(f"Found {len(code_results)} occurrence(s) of code pattern:")
            for i, (sll_offset, sra_offset, context) in enumerate(code_results):
                print(f"\n[{i+1}] sll at offset 0x{sll_offset:08X}, sra at 0x{sra_offset:08X}")
                print(f"    Context (32 bytes):")
                for j in range(0, len(context), 16):
                    hex_part = ' '.join(f'{b:02X}' for b in context[j:j+16])
                    print(f"      {hex_part}")
        else:
            print("No exact code pattern found (might need to adjust opcodes)")

        print()

        # Search for the damage value (40 = 0x28)
        print("=== Searching for damage value 40 (0x28) ===")
        value_results = search_damage_value(data, 10)

        print(f"Found {len(value_results)} occurrence(s)")
        if len(value_results) > 100:
            print("(showing first 20 only)")
            value_results = value_results[:20]

        for i, (offset, size, context) in enumerate(value_results):
            print(f"\n[{i+1}] at offset 0x{offset:08X} (size {size} bytes)")
            print(f"    Context:")
            for j in range(0, len(context), 16):
                hex_part = ' '.join(f'{b:02X}' for b in context[j:j+16])
                addr = offset - 32 + j
                print(f"      0x{addr:08X}: {hex_part}")

        print()
        print("=== Summary ===")
        print(f"To modify falling rock damage from 10% to 5%:")
        print(f"  Current: s0 = 40 (0x28) → damage = 10%")
        print(f"  Target:  s0 = 20 (0x14) → damage = 5%")
        print(f"  Action:  Find where s0=40 is stored and change to 20")

    except FileNotFoundError:
        print(f"Error: {blaze_path} not found")
        print("Make sure you're in the project root directory")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(analyze_blaze_all())
