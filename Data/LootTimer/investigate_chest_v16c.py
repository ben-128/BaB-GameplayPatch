#!/usr/bin/env python3
"""
v16c: Read the type descriptor table from ePSXe savestate RAM.

The table at RAM 0x800B1E80 is zero in the EXE (filled at runtime).
We need to read the actual runtime values from a savestate.

ePSXe savestate format: gzip compressed, RAM at offset 0x1BA (2MB).
RAM base: 0x80000000 (PS1 main memory).
"""

import struct
import gzip
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    savestate_path = script_dir / 'coffre_avec_argent.gpz'

    print("=" * 80)
    print("  v16c: Read runtime type descriptor table from savestate")
    print("=" * 80)

    # Decompress savestate
    with open(savestate_path, 'rb') as f:
        compressed = f.read()

    print(f"Savestate size: {len(compressed):,} bytes")

    # ePSXe savestates: gzip compressed, RAM at offset 0x1BA
    try:
        decompressed = gzip.decompress(compressed)
        print(f"Decompressed size: {len(decompressed):,} bytes")
    except Exception as e:
        print(f"Gzip decompress failed: {e}")
        # Try raw read
        decompressed = compressed
        print(f"Using raw data: {len(decompressed):,} bytes")

    RAM_OFFSET = 0x1BA  # RAM starts at this offset in the savestate
    RAM_BASE = 0x80000000
    RAM_SIZE = 2 * 1024 * 1024  # 2MB

    # Check if we have enough data
    if len(decompressed) < RAM_OFFSET + RAM_SIZE:
        print(f"WARNING: Decompressed data ({len(decompressed):,}) < expected ({RAM_OFFSET + RAM_SIZE:,})")
        print("Trying without offset...")
        RAM_OFFSET = 0
        if len(decompressed) < RAM_SIZE:
            print(f"Still too small. Available: {len(decompressed):,}")

    def read_ram_byte(addr):
        offset = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= offset < len(decompressed):
            return decompressed[offset]
        return 0

    def read_ram_halfword(addr):
        offset = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= offset + 1 < len(decompressed):
            return struct.unpack_from('<H', decompressed, offset)[0]
        return 0

    def read_ram_word(addr):
        offset = (addr - RAM_BASE) + RAM_OFFSET
        if 0 <= offset + 3 < len(decompressed):
            return struct.unpack_from('<I', decompressed, offset)[0]
        return 0

    # =========================================================================
    # Read the type descriptor table
    # =========================================================================
    table_base = 0x800B1E80
    record_size = 288  # 0x120
    timer_field = 0xB2

    print(f"\nTable base: 0x{table_base:08X}")
    print(f"Record size: {record_size} (0x{record_size:X})")
    print(f"Timer field: +0x{timer_field:02X}")

    print(f"\n{'='*80}")
    print(f"  All records with timer field at +0x{timer_field:02X}")
    print(f"{'='*80}")

    interesting_records = []
    for idx in range(64):
        rec_addr = table_base + idx * record_size
        timer_val = read_ram_halfword(rec_addr + timer_field)

        # Also read some identifying fields
        field_00 = read_ram_word(rec_addr + 0x00)
        field_04 = read_ram_word(rec_addr + 0x04)
        field_08 = read_ram_halfword(rec_addr + 0x08)
        field_0A = read_ram_halfword(rec_addr + 0x0A)

        if timer_val > 0 or field_00 != 0:
            time_sec = timer_val * 20 / 50 if timer_val > 0 else 0
            marker = ""
            if 18 <= time_sec <= 22:
                marker = " *** 20 SECONDS - CHEST TIMER! ***"
                interesting_records.append(idx)
            elif timer_val == 50:
                marker = " *** 50 decrements = 20s! ***"
                interesting_records.append(idx)
            elif timer_val == 1000:
                marker = " (1000 = old assumption)"
            elif time_sec > 0:
                marker = f""

            if timer_val > 0 or idx < 20:
                print(f"  Type {idx:3d}: timer=0x{timer_val:04X} ({timer_val:5d})"
                      f" = {time_sec:7.1f}s  "
                      f"[0x00]=0x{field_00:08X} [0x04]=0x{field_04:08X} "
                      f"[0x08]=0x{field_08:04X} [0x0A]=0x{field_0A:04X}{marker}")

    # =========================================================================
    # For interesting records, dump full 288 bytes
    # =========================================================================
    if interesting_records:
        print(f"\n{'='*80}")
        print(f"  Detailed dump of ~20s timer records")
        print(f"{'='*80}")
        for idx in interesting_records:
            rec_addr = table_base + idx * record_size
            print(f"\n  Type {idx} at 0x{rec_addr:08X}:")
            for off in range(0, record_size, 16):
                hex_str = ""
                ascii_str = ""
                for b in range(16):
                    if off + b < record_size:
                        byte = read_ram_byte(rec_addr + off + b)
                        hex_str += f"{byte:02X} "
                        ascii_str += chr(byte) if 32 <= byte < 127 else '.'
                    else:
                        hex_str += "   "
                print(f"    +0x{off:03X}: {hex_str} {ascii_str}")

    # =========================================================================
    # Also check: what's the actual entity+0x14 value for the visible chest?
    # =========================================================================
    print(f"\n{'='*80}")
    print(f"  Search for chest entities in RAM")
    print(f"{'='*80}")

    # Chest entities should have the dead flag check pattern
    # Look for entity structures with plausible timer values at +0x14
    # Entity flags word has 0x02000000 bit as dead flag
    # A live chest should have some non-zero value at +0x14

    # Search in typical entity pool regions (BSS/heap)
    # Entity pool is usually in high RAM
    entity_candidates = []
    for addr in range(0x800A0000, 0x800E0000, 4):
        # Look for entities with:
        # - flags at +0x00 that DON'T have dead bit (0x02000000)
        # - non-zero halfword at +0x14
        # - non-zero halfword at +0x10
        flags = read_ram_word(addr)
        if flags == 0:
            continue
        if flags & 0x02000000:
            continue  # Dead

        # Check for valid entity signature
        timer = read_ram_halfword(addr + 0x14)
        state = read_ram_halfword(addr + 0x10)

        if timer > 0 and timer <= 1000 and state > 0:
            # Check +0x12 too
            field_12 = read_ram_halfword(addr + 0x12)
            # This might be a chest or other entity
            if 10 <= timer <= 100:  # Plausible chest timer range
                entity_candidates.append((addr, flags, state, field_12, timer))

    print(f"  Found {len(entity_candidates)} candidate entities with timer 10-100")
    for addr, flags, state, f12, timer in entity_candidates[:20]:
        time_sec = timer * 20 / 50
        print(f"    0x{addr:08X}: flags=0x{flags:08X} state={state:5d} "
              f"+0x12=0x{f12:04X} timer={timer:5d} ({time_sec:.1f}s remaining)")

    # =========================================================================
    # Let's also check the global frame counter
    # =========================================================================
    frame_counter_addr = 0x800A42E0
    fc = read_ram_word(frame_counter_addr)
    print(f"\n  Global frame counter (0x{frame_counter_addr:08X}): {fc} (0x{fc:08X})")
    print(f"  Time elapsed: ~{fc/50:.1f}s at 50fps")

    # =========================================================================
    # Direct search: find ALL halfwords with value 50 (0x32) in the table area
    # =========================================================================
    print(f"\n{'='*80}")
    print(f"  Search for value 50 (0x0032) in table area 0x800B1E80-0x800C0000")
    print(f"{'='*80}")
    for addr in range(0x800B1E80, 0x800C0000, 2):
        val = read_ram_halfword(addr)
        if val == 50:
            table_off = addr - table_base
            rec_idx = table_off // record_size
            field_off = table_off % record_size
            print(f"  0x{addr:08X}: value=50  (record {rec_idx}, field +0x{field_off:03X})")

    # =========================================================================
    # Search for value 1000 (0x03E8) in table area
    # =========================================================================
    print(f"\n{'='*80}")
    print(f"  Search for value 1000 (0x03E8) in table area")
    print(f"{'='*80}")
    for addr in range(0x800B1E80, 0x800C0000, 2):
        val = read_ram_halfword(addr)
        if val == 1000:
            table_off = addr - table_base
            rec_idx = table_off // record_size
            field_off = table_off % record_size
            print(f"  0x{addr:08X}: value=1000  (record {rec_idx}, field +0x{field_off:03X})")


if __name__ == '__main__':
    main()
