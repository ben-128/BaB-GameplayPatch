#!/usr/bin/env python3
"""
Diff two ePSXe savestates to find the chest despawn timer.

Takes two savestates captured seconds apart with a chest visible.
Any halfword that decreases by exactly (elapsed_frames) is the timer.
At 50fps PAL, 5 seconds = 250 frames.

Usage: py -3 diff_savestates.py <savestate1> <savestate2> [elapsed_seconds]
"""

import gzip
import struct
import sys
from pathlib import Path

RAM_OFFSET_IN_SAVESTATE = 0x1BA
RAM_SIZE = 2 * 1024 * 1024
FPS = 50  # PAL


def extract_ram(path):
    raw = Path(path).read_bytes()
    decompressed = gzip.decompress(raw)
    return decompressed[RAM_OFFSET_IN_SAVESTATE : RAM_OFFSET_IN_SAVESTATE + RAM_SIZE]


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <savestate1> <savestate2> [elapsed_seconds]")
        print(f"  elapsed_seconds defaults to 5")
        sys.exit(1)

    ss1_path = sys.argv[1]
    ss2_path = sys.argv[2]
    elapsed_seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
    expected_frames = int(elapsed_seconds * FPS)

    print(f"Savestate 1: {ss1_path}")
    print(f"Savestate 2: {ss2_path}")
    print(f"Expected elapsed: {elapsed_seconds}s = {expected_frames} frames @ {FPS}fps")

    ram1 = extract_ram(ss1_path)
    ram2 = extract_ram(ss2_path)
    print(f"RAM extracted: {len(ram1):,} bytes each")

    # =========================================================
    # Phase 1: Find halfwords that decreased by ~expected_frames
    # =========================================================
    print(f"\n{'='*70}")
    print(f"  Phase 1: Halfwords that decreased by ~{expected_frames} (+/- 20%)")
    print(f"{'='*70}")

    min_delta = int(expected_frames * 0.8)
    max_delta = int(expected_frames * 1.2)

    countdown_candidates = []

    for off in range(0, RAM_SIZE - 2, 2):
        v1 = struct.unpack_from('<H', ram1, off)[0]
        v2 = struct.unpack_from('<H', ram2, off)[0]

        delta = v1 - v2  # positive if counting down
        if min_delta <= delta <= max_delta:
            addr = 0x80000000 + off
            countdown_candidates.append((addr, off, v1, v2, delta))

    print(f"  Found {len(countdown_candidates)} candidates (delta {min_delta}-{max_delta})")

    # Filter: value should be in plausible timer range (0-2000)
    plausible = [(a, o, v1, v2, d) for a, o, v1, v2, d in countdown_candidates
                 if 0 < v2 < 2000]
    print(f"  After filtering (v2 in 0-2000): {len(plausible)}")

    for addr, off, v1, v2, delta in plausible:
        # Classify memory region
        region = "???"
        if 0x80010000 <= addr < 0x800DD800:
            region = "SLES code"
        elif 0x80080000 <= addr < 0x800A1A5C:
            region = "OVERLAY"
        elif 0x800B4000 <= addr < 0x800BC000:
            region = "ENTITY MGR"
        elif 0x80054698 <= addr < 0x80054698 + 4 * 0x9C:
            region = "PLAYER"
        elif 0x800B9268 <= addr < 0x800B9268 + 6 * 0x28:
            region = "MONSTER META"

        # Check what this address looks like in the entity struct context
        # Try common entity strides: 0x9C, 0xA0, 0x28
        struct_info = ""
        for stride_name, stride, table_start in [
            ("9C-table", 0x9C, 0x800B4468),
            ("player", 0x9C, 0x80054698),
            ("meta", 0x28, 0x800B9268),
            ("battle", 0x9C, 0x800BB93C),
        ]:
            if table_start <= addr < table_start + 64 * stride:
                idx = (addr - table_start) // stride
                field_off = (addr - table_start) % stride
                struct_info = f" [{stride_name}[{idx}]+0x{field_off:02X}]"

        print(f"  0x{addr:08X}: {v1} -> {v2} (delta={delta}) [{region}]{struct_info}")

    # =========================================================
    # Phase 2: Find ALL changed halfwords (any delta)
    # =========================================================
    print(f"\n{'='*70}")
    print(f"  Phase 2: ALL changed halfwords in entity/data regions")
    print(f"{'='*70}")

    # Focus on likely entity memory regions
    focus_regions = [
        ("Overlay data", 0x800A0000, 0x800B0000),
        ("Entity mgr", 0x800B4000, 0x800BC000),
        ("Extended", 0x800BC000, 0x800C0000),
        ("Player", 0x80054000, 0x80056000),
        ("Monster meta", 0x800B9000, 0x800BA000),
    ]

    for region_name, rstart, rend in focus_regions:
        changes = []
        off_start = rstart - 0x80000000
        off_end = rend - 0x80000000

        for off in range(off_start, min(off_end, RAM_SIZE - 2), 2):
            v1 = struct.unpack_from('<H', ram1, off)[0]
            v2 = struct.unpack_from('<H', ram2, off)[0]
            if v1 != v2:
                addr = 0x80000000 + off
                delta = v1 - v2
                changes.append((addr, v1, v2, delta))

        if changes:
            print(f"\n  {region_name} (0x{rstart:08X}-0x{rend:08X}): {len(changes)} changes")
            for addr, v1, v2, delta in changes[:50]:
                direction = "v" if delta > 0 else "^"
                timer_marker = ""
                if min_delta <= delta <= max_delta:
                    timer_marker = " *** TIMER CANDIDATE ***"
                elif 1 <= delta <= 10:
                    timer_marker = " (slow count)"
                print(f"    0x{addr:08X}: {v1:5d} -> {v2:5d} (delta={delta:+6d}) {direction}{timer_marker}")
            if len(changes) > 50:
                print(f"    ... ({len(changes) - 50} more)")
        else:
            print(f"\n  {region_name}: no changes")

    # =========================================================
    # Phase 3: Look for timer-like patterns around candidates
    # =========================================================
    if plausible:
        print(f"\n{'='*70}")
        print(f"  Phase 3: Context around timer candidates")
        print(f"{'='*70}")

        for addr, off, v1, v2, delta in plausible[:10]:
            print(f"\n  --- 0x{addr:08X} (delta={delta}) ---")
            # Dump 64 bytes of context from ram2
            ctx_start = max(0, off - 32)
            ctx_end = min(RAM_SIZE, off + 32)
            for ci in range(ctx_start, ctx_end, 4):
                w1 = struct.unpack_from('<I', ram1, ci)[0]
                w2 = struct.unpack_from('<I', ram2, ci)[0]
                caddr = 0x80000000 + ci
                marker = " <<<" if ci == (off & ~3) else ""
                diff = "*" if w1 != w2 else " "
                print(f"    {diff} 0x{caddr:08X}: SS1={w1:08X}  SS2={w2:08X}{marker}")

    # =========================================================
    # Phase 4: Word-level changes that could be frame counters
    # =========================================================
    print(f"\n{'='*70}")
    print(f"  Phase 4: Word-level countdown candidates (delta ~{expected_frames})")
    print(f"{'='*70}")

    for off in range(0, RAM_SIZE - 4, 4):
        v1 = struct.unpack_from('<I', ram1, off)[0]
        v2 = struct.unpack_from('<I', ram2, off)[0]
        if v1 == v2:
            continue
        delta = v1 - v2
        if min_delta <= delta <= max_delta and 0 < v2 < 5000:
            addr = 0x80000000 + off
            # Skip code regions
            if 0x80010000 <= addr < 0x80080000:
                continue
            print(f"  0x{addr:08X}: {v1} -> {v2} (delta={delta})")


if __name__ == '__main__':
    main()
