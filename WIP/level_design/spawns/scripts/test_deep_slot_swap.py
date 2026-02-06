#!/usr/bin/env python3
"""
TEST: Swap slot markers in the DEEP script region (script+0x900 to +0x1DC0).

Previous tests only covered the EARLY spawn commands (script+0x080 to +0x600).
The deep region has a DIFFERENT record format with [XX FF 00 00] slot markers:
  00 FF = slot 0 (Goblin)
  01 FF = slot 1 (Shaman)
  02 FF = slot 2 (Bat)
  8X FF = slot X + 0x80 flag (behavior flag?)
  E2 FF = slot 2 + 0xE0 flags

Record format (32 bytes each):
  [FF...FF terminator] [00 00 00 00] [cmd_header 4b] [XX FF 00 00]
  [x i16] [y i16] [z i16] [00 00] [extra u32] [val u16] [FF...FF]

These look like spawn point / patrol path data. Swapping slot refs should
tell us if AI follows these markers.

Test: swap slot 0 <-> slot 2 in [XX FF 00 00] markers.
  00 FF -> 02 FF  (also 80 FF -> 82 FF, E0 FF -> E2 FF)
  02 FF -> 00 FF  (also 82 FF -> 80 FF, E2 FF -> E0 FF)
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern F1 Area1
GROUP_OFFSET = 0xF7A97C
NUM_MONSTERS = 3
SCRIPT_START = GROUP_OFFSET + NUM_MONSTERS * 96  # 0xF7AA9C

# Deep region: from script+0x900 to just before type-8 target at +0x1DC0
DEEP_START = SCRIPT_START + 0x0900  # 0xF7B39C
DEEP_END   = SCRIPT_START + 0x1DC0  # 0xF7C85C


def find_slot_markers(data, start, end):
    """Find all [XX FF 00 00] patterns where XX is a valid slot reference.

    Valid slot values: 0x00, 0x01, 0x02 (plain)
                       0x80, 0x81, 0x82 (with 0x80 flag)
                       0xE0, 0xE1, 0xE2 (with 0xE0 flags)
    """
    results = []
    for i in range(start, end - 4):
        if data[i+1] == 0xFF and data[i+2] == 0x00 and data[i+3] == 0x00:
            xx = data[i]
            slot = xx & 0x1F  # lower 5 bits = slot index
            flags = xx & 0xE0  # upper 3 bits = flags

            if slot <= 2:  # only valid slots (0, 1, 2)
                # Verify it's in a reasonable context:
                # should have 00 00 00 00 or similar before it (within 8 bytes)
                results.append({
                    'offset': i,
                    'raw': xx,
                    'slot': slot,
                    'flags': flags,
                })
    return results


def main():
    print("=" * 70)
    print("  TEST: Swap slot markers in DEEP region (script+0x900 to +0x1DC0)")
    print("  Cavern F1 Area1 - Goblin(slot 0) <-> Bat(slot 2)")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")
    print(f"  Scan region: 0x{DEEP_START:X} - 0x{DEEP_END:X} ({DEEP_END-DEEP_START} bytes)")

    # Find all slot markers
    markers = find_slot_markers(data, DEEP_START, DEEP_END)

    # Summarize by slot value
    slot_counts = {}
    for m in markers:
        key = f"slot{m['slot']}+0x{m['flags']:02X}"
        slot_counts[key] = slot_counts.get(key, 0) + 1

    print(f"\n  Found {len(markers)} [XX FF 00 00] slot markers:")
    for key, count in sorted(slot_counts.items()):
        print(f"    {key}: {count}")

    # Show first 10 of each slot value
    print(f"\n  First markers per slot:")
    shown = {}
    for m in markers:
        key = f"slot{m['slot']}+0x{m['flags']:02X}"
        if key not in shown:
            shown[key] = 0
        if shown[key] < 3:
            ctx_start = max(0, m['offset'] - 8)
            ctx_end = min(len(data), m['offset'] + 20)
            ctx = data[ctx_start:ctx_end]
            print(f"    0x{m['offset']:X}: raw=0x{m['raw']:02X} ({key}) ctx: {ctx.hex()}")
            shown[key] += 1

    # --- SWAP: slot 0 <-> slot 2 (keeping flags) ---
    print(f"\n  --- Swapping slot 0 <-> slot 2 (preserving flags) ---")
    swapped = 0
    for m in markers:
        slot = m['slot']
        flags = m['flags']

        if slot == 0:
            new_slot = 2
        elif slot == 2:
            new_slot = 0
        else:
            continue  # skip slot 1

        new_raw = flags | new_slot
        data[m['offset']] = new_raw
        swapped += 1

    print(f"  Swapped {swapped} slot markers (0 <-> 2)")

    # Verify
    markers_after = find_slot_markers(data, DEEP_START, DEEP_END)
    slot_counts_after = {}
    for m in markers_after:
        key = f"slot{m['slot']}+0x{m['flags']:02X}"
        slot_counts_after[key] = slot_counts_after.get(key, 0) + 1
    print(f"\n  After swap:")
    for key, count in sorted(slot_counts_after.items()):
        print(f"    {key}: {count}")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print(f"\n{'='*70}")
    print("  WATCH FOR:")
    print("  - Goblins with Bat behavior? (AI swap)")
    print("  - Bats with Goblin behavior? (AI swap)")
    print("  - Models unchanged but behavior different? (AI found!)")
    print("  - Crash? (records are structural)")
    print("  - No change? (these records don't control AI)")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
