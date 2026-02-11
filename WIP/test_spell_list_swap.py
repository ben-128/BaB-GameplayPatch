#!/usr/bin/env python3
"""
Test: Patch spell_list_index writes in BLAZE.ALL

Found 2 writes to entity+0x2B5 (spell_list_index):
- 0x4df93e
- 0x4e02e2

These offsets contain "A0 02 B5 02" pattern (sb $v0, 0x2B5($base))

Hypothesis: The byte BEFORE the pattern is the value written to spell_list_index.
Let's check what values are there and try changing them.

If Shaman currently uses list 0 (Offensive=FireBullet) and we change to list 2 (Status=Sleep),
we should see the Shaman cast Sleep again like in vanilla!
"""

import struct
from pathlib import Path

BLAZE_PATH = Path("output/BLAZE.ALL")

# Offsets where entity+0x2B5 is written
OFFSETS = [
    0x4df93e,
    0x4e02e2,
]

def main():
    print("Spell List Index Patcher - TEST")
    print("=" * 50)
    print()

    if not BLAZE_PATH.exists():
        print(f"ERROR: {BLAZE_PATH} not found")
        return

    with open(BLAZE_PATH, "rb") as f:
        data = bytearray(f.read())

    print("Current values at spell_list_index write sites:")
    print()

    for offset in OFFSETS:
        # Show context around the write
        context = data[offset-8:offset+8]
        hex_str = ' '.join(f'{b:02X}' for b in context)

        # The pattern is: A0 xx B5 02
        # Where xx is the register, and the value might be loaded just before
        pattern_pos = context.index(b'\xA0')
        value_before = context[pattern_pos - 1]

        print(f"Offset {hex(offset)}:")
        print(f"  Context: {hex_str}")
        print(f"  Pattern: A0 {context[pattern_pos+1]:02X} B5 02")
        print(f"  Byte before pattern: {value_before:02X} (might be list index)")
        print()

    # Test patch: change all spell_list writes to use list 2 (Status)
    print("=" * 50)
    print("TEST PATCH: Change spell_list_index to 2 (Status spells)")
    print()

    # This is speculative - we need to find where the VALUE is loaded
    # For now, let's try a different approach: search for immediate loads

    # Pattern: li $v0, 0 (load immediate 0 into $v0)
    # li is pseudo-op, expands to: ori $v0, $zero, 0 = 0x34020000
    # li $v0, 2 = 0x34020002

    print("Searching for 'li $v0, 0' near the write sites...")
    for offset in OFFSETS:
        # Search in 100 bytes before the write
        start = max(0, offset - 100)
        chunk = data[start:offset]

        # Look for li $v0, X patterns
        for i in range(len(chunk) - 3):
            word = struct.unpack('<I', chunk[i:i+4])[0]
            # ori $v0, $zero, imm = 0x3402xxxx
            if (word & 0xFFFF0000) == 0x34020000:
                imm = word & 0xFFFF
                abs_offset = start + i
                print(f"  Found 'li $v0, {imm}' at {hex(abs_offset)} ({offset - abs_offset} bytes before write)")

    print()
    print("=" * 50)
    print("To patch: Need to find and change the value loaded into $v0")
    print("Then it gets written to entity+0x2B5 via 'sb $v0, 0x2B5($base)'")
    print()
    print("Next step: Analyze disassembly to find exact load instruction")

if __name__ == '__main__':
    main()
