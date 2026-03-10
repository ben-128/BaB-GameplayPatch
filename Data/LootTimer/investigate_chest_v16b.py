#!/usr/bin/env python3
"""
v16b: Read the type descriptor table at RAM 0x800B1E80 from the EXE.

DISCOVERY: The chest timer init value is loaded from:
    RAM 0x800B1E80 + (type * 288) + 0xB2

This is NOT a code immediate - it's a DATA TABLE in the EXE!
288 bytes per record, timer at offset 0xB2 (halfword).

The timer decrements every 20 frames (confirmed by 0xCCCCCCCD magic constant).
At 50fps PAL: 2.5 decrements/sec. For 20 seconds: init = 50.
"""

import struct
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    sles_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'SLES_008.45'

    sles = sles_path.read_bytes()
    print(f"SLES size: {len(sles):,} bytes (0x{len(sles):X})")

    # Read PS-X EXE header
    magic = sles[0:8]
    print(f"Magic: {magic}")

    # Standard PS-X EXE header offsets
    entry_point = struct.unpack_from('<I', sles, 0x10)[0]
    # initial_gp = struct.unpack_from('<I', sles, 0x14)[0]
    dest_addr = struct.unpack_from('<I', sles, 0x18)[0]
    file_size = struct.unpack_from('<I', sles, 0x1C)[0]
    # data_start = struct.unpack_from('<I', sles, 0x28)[0]
    # data_size = struct.unpack_from('<I', sles, 0x2C)[0]
    bss_start = struct.unpack_from('<I', sles, 0x30)[0]
    bss_size = struct.unpack_from('<I', sles, 0x34)[0]
    sp_base = struct.unpack_from('<I', sles, 0x30)[0]  # Sometimes SP init

    print(f"\nPS-X EXE Header:")
    print(f"  Entry point:  0x{entry_point:08X}")
    print(f"  Dest address: 0x{dest_addr:08X}")
    print(f"  File size:    0x{file_size:08X} ({file_size:,})")
    print(f"  BSS start:    0x{bss_start:08X}")
    print(f"  BSS size:     0x{bss_size:08X}")

    # Calculate table address in file
    # RAM 0x800B1E80 → file offset
    table_ram = 0x800B1E80
    load_addr = dest_addr  # Usually 0x80010000
    header_size = 0x800

    table_file_offset = (table_ram - load_addr) + header_size
    print(f"\n  Table RAM:    0x{table_ram:08X}")
    print(f"  Load address: 0x{load_addr:08X}")
    print(f"  Table file offset: 0x{table_file_offset:08X}")

    # Check if this is within the file
    if table_file_offset >= len(sles):
        print(f"  ERROR: Table offset 0x{table_file_offset:X} is beyond file size 0x{len(sles):X}")
        print(f"  This means the table is in BSS (uninitialized, filled at runtime)")
        print(f"  Need to check BLAZE.ALL or savestate for the actual values")

        # Let's check BSS boundaries
        payload_end = load_addr + (len(sles) - header_size)
        print(f"\n  Payload covers RAM: 0x{load_addr:08X} - 0x{payload_end:08X}")
        print(f"  Table at 0x{table_ram:08X} {'IS' if table_ram < payload_end else 'is NOT'} within payload")

        # Maybe the load address is different. Let's check.
        # Try alternative: maybe dest_addr field is at different offset
        for off in [0x18, 0x1C, 0x10]:
            addr = struct.unpack_from('<I', sles, off)[0]
            foff = (table_ram - addr) + header_size
            if 0 < foff < len(sles):
                print(f"\n  ALTERNATIVE: Using header[0x{off:02X}]=0x{addr:08X}")
                print(f"    File offset would be: 0x{foff:08X} ({'valid' if foff < len(sles) else 'invalid'})")

        # Let's also dump the first 0x40 bytes of header for reference
        print(f"\n  Raw header (first 0x40 bytes):")
        for i in range(0, 0x40, 4):
            val = struct.unpack_from('<I', sles, i)[0]
            print(f"    0x{i:02X}: 0x{val:08X}")
        return

    print(f"  Table is within file!")

    # Read the table - dump records
    record_size = 288  # 0x120
    timer_offset = 0xB2

    # How many records can we read?
    max_records = (len(sles) - table_file_offset) // record_size
    max_records = min(max_records, 64)  # Cap at 64 types

    print(f"\n{'='*80}")
    print(f"  Type Descriptor Table at 0x{table_ram:08X}")
    print(f"  Record size: {record_size} bytes (0x{record_size:X})")
    print(f"  Timer field at offset +0x{timer_offset:02X}")
    print(f"{'='*80}")

    timer_values = {}
    for idx in range(max_records):
        rec_start = table_file_offset + idx * record_size
        if rec_start + record_size > len(sles):
            break

        # Read timer value at +0xB2
        timer_val = struct.unpack_from('<H', sles, rec_start + timer_offset)[0]
        timer_values[idx] = timer_val

        # Read a few interesting fields for context
        byte0 = sles[rec_start]
        byte1 = sles[rec_start + 1]

        # Read potential name or ID fields
        first_word = struct.unpack_from('<I', sles, rec_start)[0]

        # Calculate time in seconds (decrement every 20 frames at 50fps)
        time_sec = timer_val * 20 / 50 if timer_val > 0 else 0

        marker = ""
        if 18 <= time_sec <= 22:
            marker = " <-- ~20 SECONDS! CHEST TIMER?"
        elif timer_val == 50:
            marker = " <-- 50 decrements = 20s!"
        elif timer_val == 1000:
            marker = " <-- 1000 (old assumption)"
        elif timer_val == 0:
            marker = " (zero/unused)"

        if timer_val > 0:  # Only show non-zero entries
            print(f"  Type {idx:3d}: timer=0x{timer_val:04X} ({timer_val:5d}) = {time_sec:7.1f}s{marker}")

    # Summary
    print(f"\n{'='*80}")
    print(f"  Summary: Values that give ~20 seconds")
    print(f"{'='*80}")
    for idx, val in timer_values.items():
        time_sec = val * 20 / 50 if val > 0 else 0
        if 15 <= time_sec <= 25 and val > 0:
            print(f"  Type {idx}: timer={val} → {time_sec:.1f}s")

    # Also search for the value in the wider context
    print(f"\n{'='*80}")
    print(f"  Searching BLAZE.ALL for table initialization code")
    print(f"{'='*80}")

    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'
    blaze = blaze_path.read_bytes()

    # Search for lui 0x800B + addiu 0x1E80 pattern (loads table base address)
    # lui = 0x3C00 | (rt << 16) | 0x800B = 0x3C0X800B
    # But we need to search for the LUI value 0x800B
    count = 0
    for i in range(0, len(blaze) - 8, 4):
        word = struct.unpack_from('<I', blaze, i)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x0F:  # lui
            imm = word & 0xFFFF
            if imm == 0x800B:
                # Check next few instructions for addiu with 0x1E80 (7808)
                for j in range(1, 6):
                    off2 = i + j * 4
                    if off2 + 4 > len(blaze):
                        break
                    w2 = struct.unpack_from('<I', blaze, off2)[0]
                    if (w2 >> 26) == 0x09:  # addiu
                        imm2 = w2 & 0xFFFF
                        simm2 = imm2 if imm2 < 0x8000 else imm2 - 0x10000
                        if simm2 == 7808:  # 0x1E80
                            ram_i = 0
                            if i >= 0x009468A8:
                                ram_i = (i - 0x009468A8) + 0x80080000
                            elif i >= 0x0091D80C:
                                ram_i = (i - 0x0091D80C) + 0x80056F64
                            print(f"  Found table ref at BLAZE 0x{i:08X} (RAM ~0x{ram_i:08X})")
                            count += 1

    print(f"\n  Total table references in BLAZE.ALL: {count}")

    # Also search in SLES for this pattern
    count_sles = 0
    for i in range(0x800, len(sles) - 8, 4):
        word = struct.unpack_from('<I', sles, i)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x0F:  # lui
            imm = word & 0xFFFF
            if imm == 0x800B:
                for j in range(1, 6):
                    off2 = i + j * 4
                    if off2 + 4 > len(sles):
                        break
                    w2 = struct.unpack_from('<I', sles, off2)[0]
                    if (w2 >> 26) == 0x09:  # addiu
                        imm2 = w2 & 0xFFFF
                        simm2 = imm2 if imm2 < 0x8000 else imm2 - 0x10000
                        if simm2 == 7808:
                            ram_i = (i - 0x800) + 0x80010000
                            print(f"  Found table ref at SLES 0x{i:08X} (RAM 0x{ram_i:08X})")
                            count_sles += 1

    print(f"  Total table references in SLES: {count_sles}")


if __name__ == '__main__':
    main()
