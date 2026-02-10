#!/usr/bin/env python3
"""
Diff two ePSXe savestates to find which RAM addresses changed.

Usage:
  1. Load savestate slot 0 (standing near falling rocks)
  2. Get hit by ONE falling rock
  3. Save to slot 1
  4. Run: py -3 diff_savestates.py

This will show all RAM addresses that changed, helping identify
the HP address and the damage mechanism.
"""

import gzip
import struct
from pathlib import Path

SSTATES_DIR = Path(r"C:\Perso\BabLangue\other\ePSXe2018\sstates")
SLOT_BEFORE = SSTATES_DIR / "SLES_008.45.000"  # Before hit
SLOT_AFTER  = SSTATES_DIR / "SLES_008.45.001"  # After hit

RAM_OFFSET = 0x1BA  # Where PS1 RAM starts in ePSXe v6 savestate
RAM_SIZE = 0x200000  # 2MB


def extract_ram(savestate_path):
    data = gzip.decompress(savestate_path.read_bytes())
    return data[RAM_OFFSET:RAM_OFFSET + RAM_SIZE]


def classify_region(addr):
    """Classify a RAM address into known regions."""
    if 0x80000000 <= addr < 0x80010000:
        return "KERNEL"
    if 0x80010000 <= addr < 0x80039000:
        return "EXE (low)"
    if 0x80039000 <= addr < 0x800C0000:
        return "OVERLAY"
    if 0x800C0000 <= addr < 0x800DD800:
        return "EXE (high)"
    if 0x800DD800 <= addr < 0x80100000:
        return "EXE DATA/BSS"
    if 0x80100000 <= addr < 0x80200000:
        return "HEAP/STACK"
    return "UNKNOWN"


def main():
    if not SLOT_BEFORE.exists():
        print(f"ERROR: {SLOT_BEFORE} not found")
        return
    if not SLOT_AFTER.exists():
        print(f"ERROR: {SLOT_AFTER} not found")
        print(f"Please create a savestate in slot 1 AFTER getting hit by a rock")
        return

    print("=" * 70)
    print("  ePSXe Savestate RAM Diff Tool")
    print("=" * 70)

    ram_before = extract_ram(SLOT_BEFORE)
    ram_after = extract_ram(SLOT_AFTER)

    print(f"  Slot 0 (before): {SLOT_BEFORE.name}")
    print(f"  Slot 1 (after):  {SLOT_AFTER.name}")
    print(f"  RAM size: {len(ram_before):,} bytes")

    # Find all changed bytes
    changes = []
    for i in range(min(len(ram_before), len(ram_after))):
        if ram_before[i] != ram_after[i]:
            changes.append(i)

    print(f"\n  Total changed bytes: {len(changes)}")

    if not changes:
        print("  No changes detected! Make sure you got hit by a rock.")
        return

    # Group changes into contiguous regions
    regions = []
    region_start = changes[0]
    region_end = changes[0]
    for c in changes[1:]:
        if c <= region_end + 8:  # Allow 8-byte gaps
            region_end = c
        else:
            regions.append((region_start, region_end))
            region_start = c
            region_end = c
    regions.append((region_start, region_end))

    print(f"  Changed regions: {len(regions)}")

    # Analyze each region
    print(f"\n{'='*70}")
    print(f"  Changed Regions (looking for HP decrease)")
    print(f"{'='*70}")

    hp_candidates = []

    for reg_start, reg_end in regions:
        addr = 0x80000000 + reg_start
        size = reg_end - reg_start + 1
        region_type = classify_region(addr)

        # Skip very large regions (likely GPU/timer state, not game data)
        if size > 256:
            print(f"\n  0x{addr:08X}-0x{addr+size-1:08X} ({size} bytes) [{region_type}] - LARGE, skipping details")
            continue

        print(f"\n  0x{addr:08X}-0x{addr+size-1:08X} ({size} bytes) [{region_type}]")

        # Show the actual changes
        for off in range(reg_start, reg_end + 1):
            if ram_before[off] != ram_after[off]:
                a = 0x80000000 + off
                bv = ram_before[off]
                av = ram_after[off]
                print(f"    0x{a:08X}: 0x{bv:02X} -> 0x{av:02X} ({bv} -> {av})")

        # Check for int16 decreases (HP candidate)
        for off in range(reg_start, reg_end + 1, 2):
            if off + 2 <= len(ram_before):
                val_before = struct.unpack_from('<H', ram_before, off)[0]
                val_after = struct.unpack_from('<H', ram_after, off)[0]
                if val_before != val_after:
                    delta = val_after - val_before
                    signed_before = struct.unpack_from('<h', ram_before, off)[0]
                    signed_after = struct.unpack_from('<h', ram_after, off)[0]
                    signed_delta = signed_after - signed_before

                    if -200 < signed_delta < 0 and 10 < signed_before < 2000:
                        hp_candidates.append({
                            'addr': 0x80000000 + off,
                            'before': signed_before,
                            'after': signed_after,
                            'delta': signed_delta,
                            'region': region_type,
                        })

    # Summary: HP candidates
    print(f"\n{'='*70}")
    print(f"  HP CANDIDATES (int16 values that decreased by 1-200)")
    print(f"{'='*70}")

    if hp_candidates:
        for c in sorted(hp_candidates, key=lambda x: x['delta']):
            print(f"  0x{c['addr']:08X}: {c['before']:>5} -> {c['after']:>5} "
                  f"(delta: {c['delta']:+d}) [{c['region']}]")
    else:
        print("  No obvious HP candidates found in int16 format.")
        print("  HP might be stored as int32 or at a non-aligned offset.")
        print("  Check the full diff above for clues.")

    # Also check int32 decreases
    print(f"\n  INT32 CANDIDATES:")
    for reg_start, reg_end in regions:
        size = reg_end - reg_start + 1
        if size > 256:
            continue
        for off in range(reg_start, min(reg_end + 1, len(ram_before) - 4), 4):
            val_before = struct.unpack_from('<i', ram_before, off)[0]
            val_after = struct.unpack_from('<i', ram_after, off)[0]
            delta = val_after - val_before
            if -200 < delta < 0 and 10 < val_before < 100000:
                print(f"  0x{0x80000000+off:08X}: {val_before:>6} -> {val_after:>6} "
                      f"(delta: {delta:+d}) [{classify_region(0x80000000+off)}]")


if __name__ == "__main__":
    main()
