#!/usr/bin/env python3
"""
Search for the chest despawn overlay code in BLAZE.ALL.

The overlay code at RAM 0x80099B50-0x80099C40 is loaded at runtime
into a region that's all zeros in the SLES file. This code manages
the chest entity lifecycle (state 1=fade-in, state 2=countdown,
state 3=fade-out/kill).

We need to find WHERE in BLAZE.ALL this code is stored, so we can
patch the countdown decrement (addiu $v0,$v0,-1 at 0x80099BD4).
"""

import gzip
import struct
from pathlib import Path

BLAZE_ALL_PATH = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
SAVESTATE_PATH = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\CoffreSolo\SLES_008.45.000")
RAM_OFFSET_IN_SAVESTATE = 0x1BA

def extract_ram(savestate_path):
    raw = savestate_path.read_bytes()
    decompressed = gzip.decompress(raw)
    return decompressed[RAM_OFFSET_IN_SAVESTATE : RAM_OFFSET_IN_SAVESTATE + 2*1024*1024]


def main():
    print("=" * 70)
    print("  Search for overlay code in BLAZE.ALL")
    print("=" * 70)

    ram = extract_ram(SAVESTATE_PATH)
    blaze = BLAZE_ALL_PATH.read_bytes()
    print(f"RAM: {len(ram):,} bytes")
    print(f"BLAZE.ALL: {len(blaze):,} bytes")

    # Extract overlay code from RAM: 0x80099B50 to 0x80099C50
    # (contains the full state machine for entity lifecycle)
    overlay_start = 0x99B50  # RAM offset (from 0x80000000)
    overlay_end = 0x99C50
    overlay_code = ram[overlay_start:overlay_end]
    print(f"\nOverlay code: {len(overlay_code)} bytes from RAM 0x{0x80000000+overlay_start:08X}-0x{0x80000000+overlay_end:08X}")

    # 1. Search for exact match of full overlay code
    print(f"\n--- Search 1: Full {len(overlay_code)}-byte overlay ---")
    pos = blaze.find(overlay_code)
    if pos >= 0:
        print(f"  FOUND at BLAZE.ALL offset 0x{pos:08X}")
    else:
        print(f"  Not found (full block)")

    # 2. Search for progressively smaller chunks
    for chunk_size in [64, 32, 16, 12, 8]:
        print(f"\n--- Search 2: {chunk_size}-byte sliding windows ---")
        found_any = False
        for off in range(0, len(overlay_code) - chunk_size + 1, 4):
            chunk = overlay_code[off:off + chunk_size]
            # Skip chunks that are all zeros
            if chunk == b'\x00' * chunk_size:
                continue
            pos = blaze.find(chunk)
            if pos >= 0:
                ram_addr = 0x80000000 + overlay_start + off
                words_hex = ' '.join(f'{struct.unpack_from("<I", chunk, i)[0]:08X}'
                                     for i in range(0, min(chunk_size, 16), 4))
                print(f"  MATCH: overlay+0x{off:02X} (RAM 0x{ram_addr:08X}) -> BLAZE.ALL 0x{pos:08X}")
                print(f"    Bytes: {words_hex}{'...' if chunk_size > 16 else ''}")
                found_any = True
        if not found_any:
            print(f"  No {chunk_size}-byte matches found")
        else:
            break  # Stop at the largest matching chunk size

    # 3. Search for the KEY instruction: the state 2 countdown
    # RAM 0x80099BCC-0x80099BDC:
    # 96220014 00000000 2442FFFF A6220014 00021400
    countdown_start = 0x99BCC - overlay_start
    countdown_bytes = overlay_code[countdown_start:countdown_start + 20]
    print(f"\n--- Search 3: Countdown instruction block (20 bytes) ---")
    words = [struct.unpack_from('<I', countdown_bytes, i)[0] for i in range(0, 20, 4)]
    print(f"  Pattern: {' '.join(f'{w:08X}' for w in words)}")
    pos = blaze.find(countdown_bytes)
    if pos >= 0:
        print(f"  FOUND at BLAZE.ALL 0x{pos:08X}")
    else:
        print(f"  Not found")

    # 4. Search for individual KEY instructions
    print(f"\n--- Search 4: Individual instructions in BLAZE.ALL ---")

    key_instrs = [
        (0x96220014, "lhu $v0, 0x14($s1)"),
        (0xA6220014, "sh $v0, 0x14($s1)"),
        (0xA6220010, "sh $v0, 0x10($s1)"),
        (0x86220028, "lh $v0, 0x28($s1)"),
        (0x96220028, "lhu $v0, 0x28($s1)"),
        (0xA6220028, "sh $v0, 0x28($s1)"),
        (0x9622002A, "lhu $v0, 0x2A($s1)"),
        (0xA622002A, "sh $v0, 0x2A($s1)"),
        (0x284203E9, "slti $v0, $v0, 1001"),
        (0x240203E8, "addiu $v0, $zero, 1000"),
    ]

    for instr_word, instr_name in key_instrs:
        instr_bytes = struct.pack('<I', instr_word)
        positions = []
        p = 0
        while True:
            p = blaze.find(instr_bytes, p)
            if p == -1:
                break
            # Only count 4-byte aligned matches
            if p % 4 == 0:
                positions.append(p)
            p += 1
        print(f"  {instr_name} (0x{instr_word:08X}): {len(positions)} aligned match(es)")
        if 0 < len(positions) <= 20:
            for pp in positions[:10]:
                print(f"    0x{pp:08X}")

    # 5. Extract a wider region of the overlay and check where RAM differs from SLES
    # This helps us understand what the overlay module covers
    print(f"\n{'='*70}")
    print(f"  Overlay coverage map: where RAM != SLES zeros")
    print(f"{'='*70}")

    sles_path = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")
    sles_data = sles_path.read_bytes()

    # Check from 0x80080000 to 0x800DD800 for overlay regions
    sles_load = 0x80010000
    sles_header = 0x800

    overlay_regions = []
    in_overlay = False
    region_start = 0

    for addr in range(0x80080000, 0x800DD800, 4):
        ram_off = addr - 0x80000000
        sles_off = sles_header + (addr - sles_load)
        ram_word = struct.unpack_from('<I', ram, ram_off)[0]
        sles_word = struct.unpack_from('<I', sles_data, sles_off)[0]

        is_diff = (ram_word != sles_word)
        if is_diff and not in_overlay:
            region_start = addr
            in_overlay = True
        elif not is_diff and in_overlay:
            overlay_regions.append((region_start, addr - 4))
            in_overlay = False

    if in_overlay:
        overlay_regions.append((region_start, 0x800DD7FC))

    # Merge nearby regions (< 64 bytes gap)
    merged = []
    for start, end in overlay_regions:
        if merged and start - merged[-1][1] < 64:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    print(f"  Found {len(merged)} overlay region(s) in 0x80080000-0x800DD800:")
    for start, end in merged:
        size = end - start + 4
        contains_target = start <= 0x80099BD4 <= end
        marker = " *** CONTAINS DESPAWN CODE ***" if contains_target else ""
        print(f"    0x{start:08X} - 0x{end:08X} ({size:,} bytes){marker}")

    # 6. For the region containing our target, extract and search in BLAZE.ALL
    for start, end in merged:
        if start <= 0x80099BD4 <= end:
            size = end - start + 4
            ram_off = start - 0x80000000
            region_data = ram[ram_off:ram_off + size]

            print(f"\n{'='*70}")
            print(f"  Target overlay region: 0x{start:08X}-0x{end:08X} ({size:,} bytes)")
            print(f"{'='*70}")

            # Search for this entire region in BLAZE.ALL
            print(f"\n  Full region search in BLAZE.ALL:")
            pos = blaze.find(region_data)
            if pos >= 0:
                print(f"    FOUND at 0x{pos:08X}!")
            else:
                print(f"    Not found (full region)")

            # Try 256-byte chunks
            print(f"\n  256-byte chunk search:")
            found_256 = 0
            for off in range(0, size - 256, 128):
                chunk = region_data[off:off + 256]
                if chunk == b'\x00' * 256:
                    continue
                pos = blaze.find(chunk)
                if pos >= 0:
                    chunk_addr = start + off
                    print(f"    overlay+0x{off:04X} (RAM 0x{chunk_addr:08X}) -> BLAZE.ALL 0x{pos:08X}")
                    found_256 += 1
                    if found_256 >= 10:
                        print(f"    ... (truncated)")
                        break
            if found_256 == 0:
                print(f"    No 256-byte matches found")

            # Try 128-byte chunks
            if found_256 == 0:
                print(f"\n  128-byte chunk search:")
                found_128 = 0
                for off in range(0, size - 128, 64):
                    chunk = region_data[off:off + 128]
                    if chunk == b'\x00' * 128:
                        continue
                    pos = blaze.find(chunk)
                    if pos >= 0:
                        chunk_addr = start + off
                        print(f"    overlay+0x{off:04X} (RAM 0x{chunk_addr:08X}) -> BLAZE.ALL 0x{pos:08X}")
                        found_128 += 1
                        if found_128 >= 10:
                            print(f"    ... (truncated)")
                            break
                if found_128 == 0:
                    print(f"    No 128-byte matches found")

            break


if __name__ == '__main__':
    main()
