#!/usr/bin/env python3
"""Convert RAM address to BLAZE.ALL offset for overlays."""

def ram_to_blaze_offset(ram_addr):
    """
    Convert RAM address to BLAZE.ALL offset.

    PSX overlays are loaded at different RAM addresses.
    For Cavern overlay: RAM 0x800CA??? → BLAZE offset 0x01??????

    This needs to be determined empirically or from overlay table.
    """

    # Common overlay base addresses (examples - need confirmation)
    overlay_mappings = {
        # Format: (ram_start, ram_end, blaze_offset_base)
        # Cavern overlay (example - needs verification)
        (0x800C0000, 0x800DFFFF, 0x01B00000),  # Hypothetical

        # Other dungeons would be here...
    }

    for ram_start, ram_end, blaze_base in overlay_mappings:
        if ram_start <= ram_addr <= ram_end:
            offset_in_overlay = ram_addr - ram_start
            blaze_offset = blaze_base + offset_in_overlay
            return blaze_offset

    # If not in overlay, might be in EXE (SLES_008.45)
    # EXE addresses 0x80010000-0x8008???? map to SLES file
    if 0x80010000 <= ram_addr <= 0x80090000:
        # EXE offset (approximate)
        exe_offset = ram_addr - 0x80010000
        print(f"  [EXE] Offset in SLES_008.45: 0x{exe_offset:08X}")
        return None  # Not in BLAZE.ALL

    return None

def find_overlay_in_blaze(code_bytes):
    """
    Search for specific code bytes in BLAZE.ALL to find overlay location.

    Args:
        code_bytes: bytes to search for (e.g., the sll/sra pattern)

    Returns:
        List of offsets where pattern is found
    """
    blaze_path = "Blaze  Blade - Eternal Quest (Europe)/extract/BLAZE.ALL"

    try:
        with open(blaze_path, "rb") as f:
            data = f.read()

        results = []
        i = 0
        while i < len(data) - len(code_bytes):
            if data[i:i+len(code_bytes)] == code_bytes:
                results.append(i)
            i += 4  # Align to 4 bytes (MIPS instructions)

        return results

    except FileNotFoundError:
        print(f"Error: {blaze_path} not found")
        return []

def main():
    print("=== RAM to BLAZE.ALL Offset Converter ===\n")

    # Known addresses from debug session
    test_addresses = {
        "sll a1, s6, 16": 0x800CADDC,
        "sra a1, a1, 16": 0x800CADE4,
        "jal damage_fn":  0x800CADE8,
    }

    print("Known addresses:")
    for name, addr in test_addresses.items():
        print(f"  {name:20} = 0x{addr:08X}")

    print("\n" + "="*60)
    print("Method 1: Direct Mapping (needs overlay table)")
    print("="*60 + "\n")

    for name, addr in test_addresses.items():
        offset = ram_to_blaze_offset(addr)
        if offset:
            print(f"{name:20} → BLAZE offset 0x{offset:08X}")
        else:
            print(f"{name:20} → Not in BLAZE.ALL or unknown overlay")

    print("\n" + "="*60)
    print("Method 2: Search by Code Pattern")
    print("="*60 + "\n")

    # Search for the sll a1, s6, 16 instruction
    # MIPS encoding: sll a1, s6, 16
    # Format: 000000 sssss ttttt ddddd shamt 000000
    #         000000 10110 00101 00101 10000 000000
    # s6=22 (s registers start at 16, s6=16+6=22)
    # a1=5
    # shamt=16
    # Result: 0x00162C00 in big endian, 0x002C1600 in little endian

    sll_pattern = bytes([0x00, 0x2C, 0x16, 0x00])  # sll a1, s6, 16 (little endian)

    print(f"Searching for pattern: {sll_pattern.hex()}")
    print(f"(sll a1, s6, 16)\n")

    results = find_overlay_in_blaze(sll_pattern)

    if results:
        print(f"Found {len(results)} occurrence(s):")
        for i, offset in enumerate(results[:5]):  # Show first 5
            ram_addr = 0x800CA000 + (offset - results[0])  # Estimate RAM addr
            print(f"  [{i+1}] BLAZE offset: 0x{offset:08X}")
            print(f"      (Estimated RAM: 0x{ram_addr:08X})")
    else:
        print("Pattern not found. Opcode might be different.")
        print("\nTry searching manually:")
        print("  1. Open BLAZE.ALL in hex editor")
        print("  2. Search for pattern: 00 2C 16 00")
        print("  3. Note the offset")

    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("1. Find exact BLAZE offset using Method 2")
    print("2. Create patch to modify instruction or data")
    print("3. Test with modified BLAZE.ALL")

if __name__ == "__main__":
    main()
