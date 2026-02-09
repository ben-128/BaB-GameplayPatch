#!/usr/bin/env python3
"""
Dump the area data as loaded in RAM from savestate.
The 96-byte stat entries are at 0x800E27E4. Look at what surrounds them
to find the FULL area data block and any additional structures.
"""

import gzip
import struct
from pathlib import Path

SAVESTATE = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\combat\SLES_008.45.000")
BLAZE_ALL = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")

RAM_BASE = 0x80000000
RAM_SIZE = 0x200000


def main():
    raw = gzip.open(str(SAVESTATE), 'rb').read()
    ram = bytearray(raw[0x1BA : 0x1BA + RAM_SIZE])
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())

    def ri(addr): return addr - RAM_BASE
    def ru32(addr): return struct.unpack_from('<I', ram, ri(addr))[0]
    def ru16(addr): return struct.unpack_from('<H', ram, ri(addr))[0]

    # Known: stat entries at 0x800E27E4, stride 96, 3 entries
    STAT_RAM = 0x800E27E4
    STAT_BLAZE = 0xF7A97C

    # Area data in BLAZE.ALL:
    # Assignment entries at 0xF7A964 (24 bytes before stats = 3*8)
    # Stat entries at 0xF7A97C (3 * 96 = 288 bytes)
    # Script area at 0xF7AA9C (right after stats)
    ASSIGN_BLAZE = 0xF7A964
    SCRIPT_BLAZE = 0xF7AA9C

    # Calculate RAM addresses by offset from stat base
    assign_ram = STAT_RAM - (STAT_BLAZE - ASSIGN_BLAZE)
    script_ram = STAT_RAM + (SCRIPT_BLAZE - STAT_BLAZE)

    print("=" * 100)
    print("  AREA DATA IN RAM (anchored on stat entries at 0x800E27E4)")
    print("=" * 100)
    print(f"  Expected RAM addresses:")
    print(f"    Assignment entries: 0x{assign_ram:08X} (BLAZE 0x{ASSIGN_BLAZE:08X})")
    print(f"    Stat entries:      0x{STAT_RAM:08X} (BLAZE 0x{STAT_BLAZE:08X})")
    print(f"    Script area:       0x{script_ram:08X} (BLAZE 0x{SCRIPT_BLAZE:08X})")

    # Verify assignment entries match
    print("\n  Verifying assignment entries match BLAZE.ALL:")
    for i in range(3):
        ram_off = assign_ram + i * 8
        blaze_off = ASSIGN_BLAZE + i * 8
        ram_val = ram[ri(ram_off):ri(ram_off)+8]
        blaze_val = blaze[blaze_off:blaze_off+8]
        match = "MATCH" if ram_val == blaze_val else "DIFFER"
        print(f"    Slot {i}: RAM=[{ram_val.hex()}] BLAZE=[{blaze_val.hex()}] {match}")

    # Dump area data starting 0x100 bytes before assignments through 0x400 after stat end
    DUMP_START = assign_ram - 0x100
    DUMP_END = script_ram + 0x400

    print(f"\n  Full area data dump: 0x{DUMP_START:08X} - 0x{DUMP_END:08X}")
    print(f"  (Legend: ASGN=assignment, STAT=stat entries, SCRP=script area)\n")

    for addr in range(DUMP_START, DUMP_END, 16):
        hex_data = ' '.join(f"{ram[ri(addr)+b]:02X}" for b in range(16)
                           if ri(addr)+b < RAM_SIZE)

        # Annotate regions
        marker = ""
        if assign_ram <= addr < assign_ram + 24:
            marker = " <ASGN>"
        elif STAT_RAM <= addr < STAT_RAM + 288:
            stat_idx = (addr - STAT_RAM) // 96
            marker = f" <STAT {stat_idx}>"
        elif script_ram <= addr < script_ram + 0x400:
            marker = " <SCRP>"

        # Check for pointers
        ptrs = []
        for b in range(0, 16, 4):
            if ri(addr) + b + 4 > RAM_SIZE:
                continue
            val = struct.unpack_from('<I', ram, ri(addr) + b)[0]
            if 0x800A0000 <= val < 0x800B0000:
                ptrs.append(f"overlay:0x{val:08X}")
            elif 0x80010000 <= val < 0x80060000:
                ptrs.append(f"exe:0x{val:08X}")
        if ptrs:
            marker += " " + " ".join(ptrs)

        print(f"  0x{addr:08X}: {hex_data}{marker}")

    # Also check the NAME occurrences in the 0x800B1xxx-0x800B5xxx region
    print("\n\n" + "=" * 100)
    print("  NAME OCCURRENCES IN RAM (entity structs?)")
    print("=" * 100)

    names = [b"Lv20.Goblin", b"Goblin-Shaman", b"Giant-Bat"]
    for name in names:
        pos = 0
        hits = []
        while pos < RAM_SIZE:
            idx = ram.find(name, pos)
            if idx < 0:
                break
            hits.append(RAM_BASE + idx)
            pos = idx + 1

        print(f"\n  \"{name.decode()}\" ({len(hits)} occurrences):")
        for addr in hits:
            # Dump 0x80 bytes around the name (0x20 before, 0x60 after)
            dump_start = addr - 0x20
            dump_end = addr + 0x80
            print(f"\n    At 0x{addr:08X}:")
            for row_addr in range(dump_start, dump_end, 16):
                if ri(row_addr) < 0 or ri(row_addr) + 16 > RAM_SIZE:
                    continue
                rel = row_addr - addr
                hex_data = ' '.join(f"{ram[ri(row_addr)+b]:02X}" for b in range(16))
                marker = " <NAME>" if 0 <= rel < len(name) else ""
                # Check for pointers
                ptrs = []
                for b in range(0, 16, 4):
                    val = struct.unpack_from('<I', ram, ri(row_addr) + b)[0]
                    if 0x800A0000 <= val < 0x800D0000:
                        ptrs.append(f"ptr:0x{val:08X}")
                if ptrs:
                    marker += " " + " ".join(ptrs)
                print(f"      {rel:+05d} 0x{row_addr:08X}: {hex_data}{marker}")


if __name__ == '__main__':
    main()
