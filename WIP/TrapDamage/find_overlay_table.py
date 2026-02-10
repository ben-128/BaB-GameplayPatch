#!/usr/bin/env python3
"""
Search the PS1 EXE (SLES_008.45) for the overlay loading table.

The EXE must have a table that maps dungeon IDs to BLAZE.ALL offsets
for overlay code loading. We search for known BLAZE.ALL offsets
(like 0x00900000 for the main code region) stored as uint32 values.

Also: verify whether 0x8008A3E4 is in the EXE or in an overlay.
"""

import struct
from pathlib import Path

BASE = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch")
BIN_FILE = BASE / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"
BLAZE_ALL = BASE / "output" / "BLAZE.ALL"

# BIN layout
SECTOR_SIZE = 2352
HEADER_SIZE = 24
USER_SIZE = 2048
SLES_LBA = 295081  # SLES_008.45 in BIN

# PS1 EXE header
EXE_TEXT_OFFSET = 0x800  # Text section starts at offset 0x800 in the file
EXE_LOAD_ADDR = 0x80010000  # Typical PS1 load address


def read_sectors(bin_data, lba, count):
    """Read raw sectors from BIN."""
    result = bytearray()
    for i in range(count):
        sector_off = (lba + i) * SECTOR_SIZE
        if sector_off + SECTOR_SIZE > len(bin_data):
            break
        result.extend(bin_data[sector_off + HEADER_SIZE: sector_off + HEADER_SIZE + USER_SIZE])
    return bytes(result)


def main():
    print("=" * 70)
    print("  Find Overlay Loading Table in EXE")
    print("=" * 70)

    # Read SLES from BIN
    bin_data = BIN_FILE.read_bytes()
    sles_size_sectors = (824 * 1024 + USER_SIZE - 1) // USER_SIZE  # ~412 sectors
    sles_data = read_sectors(bin_data, SLES_LBA, sles_size_sectors)
    print(f"  SLES_008.45: {len(sles_data):,} bytes extracted from BIN")

    # Verify 0x8008A3E4 is in EXE
    func_addr = 0x8008A3E4
    func_file_off = (func_addr - EXE_LOAD_ADDR) + EXE_TEXT_OFFSET
    print(f"\n  Function 0x{func_addr:08X}:")
    print(f"    EXE file offset: 0x{func_file_off:X}")
    print(f"    In EXE range: {0 <= func_file_off < len(sles_data)}")
    if func_file_off < len(sles_data):
        # Read first 16 bytes at that offset
        snippet = sles_data[func_file_off:func_file_off+16]
        words = [struct.unpack_from('<I', snippet, i)[0] for i in range(0, 16, 4)]
        print(f"    First 4 words: {' '.join(f'0x{w:08X}' for w in words)}")
        # Check if it looks like MIPS code (not zero/FF)
        is_code = any(w != 0 and w != 0xFFFFFFFF for w in words)
        print(f"    Looks like code: {is_code}")

    # Search EXE for known BLAZE.ALL code region offsets
    print(f"\n  Searching EXE for BLAZE.ALL overlay offset references...")

    # Known code region starts from our scan
    region_starts = [
        0x00900000, 0x009E0000, 0x00BB0000, 0x00CE0000, 0x00DE0000,
        0x01000000, 0x01080000, 0x012A0000, 0x01320000, 0x014F0000,
        0x01690000, 0x01770000, 0x01A10000, 0x01B80000, 0x01C10000,
        0x01E60000, 0x020C0000, 0x02160000, 0x024A0000, 0x02560000,
        0x02640000, 0x026D0000, 0x02770000, 0x027D0000, 0x02880000,
        0x028D0000, 0x02B60000,
    ]

    for target in region_starts:
        target_bytes = struct.pack('<I', target)
        matches = []
        pos = 0
        while True:
            idx = sles_data.find(target_bytes, pos)
            if idx == -1:
                break
            matches.append(idx)
            pos = idx + 1
        if matches:
            for m in matches[:3]:
                ram_addr = EXE_LOAD_ADDR + m - EXE_TEXT_OFFSET if m >= EXE_TEXT_OFFSET else m
                # Read context (4 words before, target, 4 words after)
                ctx_start = max(0, m - 16)
                ctx_end = min(len(sles_data), m + 20)
                ctx = sles_data[ctx_start:ctx_end]
                ctx_words = [struct.unpack_from('<I', ctx, i)[0]
                            for i in range(0, len(ctx) - 3, 4)]
                print(f"    0x{target:08X} found at EXE+0x{m:05X} (RAM 0x{ram_addr:08X})")
                print(f"      Context: {' '.join(f'{w:08X}' for w in ctx_words)}")

    # Alternative: search for sector-aligned offsets (BLAZE.ALL offsets / 2048)
    print(f"\n  Searching for sector-based offset patterns...")

    # The EXE might store offsets in sectors (2048-byte units) rather than bytes
    for target in [0x00900000, 0x009E0000, 0x00CE0000, 0x01000000]:
        sector_off = target // 2048
        target_bytes = struct.pack('<I', sector_off)
        matches = []
        pos = 0
        while True:
            idx = sles_data.find(target_bytes, pos)
            if idx == -1:
                break
            matches.append(idx)
            pos = idx + 1
        if matches:
            for m in matches[:2]:
                ram_addr = EXE_LOAD_ADDR + m - EXE_TEXT_OFFSET if m >= EXE_TEXT_OFFSET else m
                print(f"    0x{target:08X} (sector 0x{sector_off:X}) at EXE+0x{m:05X} (RAM 0x{ram_addr:08X})")

    # Search for the 4 stat_mod function addresses stored as data (table)
    print(f"\n  Searching for stat_mod function address table in EXE...")
    func_addrs = [0x8008A1C4, 0x8008A39C, 0x8008A3BC, 0x8008A3E4]
    for fa in func_addrs:
        target_bytes = struct.pack('<I', fa)
        matches = []
        pos = 0
        while True:
            idx = sles_data.find(target_bytes, pos)
            if idx == -1:
                break
            matches.append(idx)
            pos = idx + 1
        if matches:
            print(f"    0x{fa:08X}: found at {len(matches)} locations")
            for m in matches[:5]:
                ram_addr = EXE_LOAD_ADDR + m - EXE_TEXT_OFFSET if m >= EXE_TEXT_OFFSET else m
                print(f"      EXE+0x{m:05X} (RAM 0x{ram_addr:08X})")

    # Look for a table of BLAZE.ALL offsets stored consecutively
    print(f"\n  Scanning for consecutive BLAZE.ALL offset tables in EXE...")
    # Look for any pair of known region offsets within 32 bytes of each other
    known_offsets = set()
    for target in region_starts:
        target_bytes = struct.pack('<I', target)
        pos = 0
        while True:
            idx = sles_data.find(target_bytes, pos)
            if idx == -1:
                break
            known_offsets.add((idx, target))
            pos = idx + 1

    # Check for clusters
    sorted_finds = sorted(known_offsets)
    for i in range(len(sorted_finds) - 1):
        off1, val1 = sorted_finds[i]
        off2, val2 = sorted_finds[i + 1]
        if off2 - off1 <= 32:
            print(f"    Cluster at EXE+0x{off1:05X}: 0x{val1:08X}, 0x{val2:08X} (gap={off2-off1})")
            # Read surrounding data
            ctx_start = max(0, off1 - 8)
            ctx_end = min(len(sles_data), off2 + 12)
            ctx = sles_data[ctx_start:ctx_end]
            ctx_words = [struct.unpack_from('<I', ctx, i)[0]
                        for i in range(0, len(ctx) - 3, 4)]
            print(f"      Data: {' '.join(f'{w:08X}' for w in ctx_words)}")


if __name__ == "__main__":
    main()
