"""
quick_search.py - Fast targeted search for class stats
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BLAZE_ALL = SCRIPT_DIR.parent.parent / "output" / "BLAZE.ALL"


def main():
    data = BLAZE_ALL.read_bytes()
    print(f"File size: {len(data):,} bytes")

    # 1. Search for stat-related strings first
    print("\n=== STAT STRINGS ===")
    for s in [b'STR', b'INT', b'WIL', b'AGL', b'CON', b'POW', b'LUK']:
        pos = data.find(s)
        if pos != -1:
            print(f"  {s.decode()}: 0x{pos:08X}")

    # 2. Check zone after class names (0x0090B7C8+)
    print("\n=== ZONE AFTER CLASS NAMES ===")
    start = 0x0090B7C8
    print(f"Hex at 0x{start:08X}:")
    for i in range(0, 256, 16):
        chunk = data[start+i:start+i+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {start+i:08X}: {hex_str}  {ascii_str}")

    # 3. Search for 0x0090B6E8 references (pointer to Warrior)
    print("\n=== POINTERS TO CLASS NAMES ===")
    warrior_offset = 0x0090B6E8
    warrior_bytes = struct.pack('<I', warrior_offset)
    pos = 0
    count = 0
    while count < 20:
        pos = data.find(warrior_bytes, pos)
        if pos == -1:
            break
        print(f"  Pointer to Warrior at 0x{pos:08X}")
        # Show context
        ctx_start = max(0, pos - 8)
        ctx = data[ctx_start:pos+24]
        print(f"    Context: {ctx.hex()}")
        pos += 1
        count += 1

    # 4. Look at zone 0x00203000 in more detail
    print("\n=== LEVEL TABLE ZONE 0x00203000 ===")
    start = 0x00203000
    # Show first 64 uint16 values
    print("First 64 uint16 values:")
    values = [struct.unpack('<H', data[start + i*2:start + i*2 + 2])[0] for i in range(64)]
    for i in range(0, 64, 8):
        print(f"  +{i*2:03X}: {values[i:i+8]}")

    # 5. Check zone 0x00203920+ which had interesting patterns
    print("\n=== INTERESTING ZONE 0x00203920 ===")
    start = 0x00203920
    print("uint16 values at 0x203920:")
    values = [struct.unpack('<H', data[start + i*2:start + i*2 + 2])[0] for i in range(80)]
    for i in range(0, 80, 8):
        print(f"  +{i*2:03X}: {values[i:i+8]}")

    # 6. Search for the marker 0x0B01D900 that follows class names
    # and look at structures that might reference it
    print("\n=== CLASS MARKER ANALYSIS ===")
    marker = bytes([0x0B, 0x01, 0xD9, 0x00])
    pos = 0x0090B6E0
    count = 0
    while count < 20 and pos < 0x0090B900:
        pos = data.find(marker, pos)
        if pos == -1 or pos >= 0x0090B900:
            break
        # Read preceding text
        text_start = pos - 16
        text = data[text_start:pos]
        # Find null terminator
        null_pos = text.find(b'\x00')
        if null_pos != -1:
            text = text[null_pos+1:]
        try:
            name = text.split(b'\x00')[0].decode('ascii', errors='ignore')
            if name:
                print(f"  0x{pos:08X}: marker after '{name}'")
        except:
            pass
        pos += 1
        count += 1


if __name__ == '__main__':
    main()
