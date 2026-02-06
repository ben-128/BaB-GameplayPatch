#!/usr/bin/env python3
"""
TEST: Swap COMMAND HEADERS in deep script region while keeping slot markers intact.

Previous test: swapping [XX FF 00 00] slot markers -> created dark entities, no AI change.
This test: swap the 4-byte command header BEFORE each slot marker.

Record format in deep region:
  ... [00 00 00 00] [header 4b] [slot FF 00 00] [x y z] ... [val] [FFFFFFFFFFFF]

The header varies by slot:
  Slot 0 (Goblin): 00 2B 07 00, 06 00 01 00, etc.
  Slot 2 (Bat):    00 00 04 00, 16 00 08 00, 1C 1C 09 00, etc.

Test: for each [header][slot FF 00 00], replace the header with a header
from the OTHER slot. Slot markers stay intact (no dark entities).

Start from CLEAN BLAZE.ALL.
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

DEEP_START = SCRIPT_START + 0x0900
DEEP_END   = SCRIPT_START + 0x1DC0


def find_records(data, start, end):
    """Find all [header 4b][XX FF 00 00] patterns in the deep region."""
    results = []
    for i in range(start, end - 8):
        if data[i+5] == 0xFF and data[i+6] == 0x00 and data[i+7] == 0x00:
            xx = data[i+4]
            slot = xx & 0x1F
            flags = xx & 0xE0

            if slot <= 2:
                header = bytes(data[i:i+4])
                # Sanity: header shouldn't be FFFFFFFF or 00000000 only
                if header != b'\xff\xff\xff\xff':
                    results.append({
                        'header_offset': i,
                        'slot_offset': i + 4,
                        'header': header,
                        'slot': slot,
                        'flags': flags,
                        'raw_slot': xx,
                    })
    return results


def main():
    print("=" * 70)
    print("  TEST: Swap command HEADERS in deep region")
    print("  Keep slot markers intact, swap only the 4-byte headers")
    print("  Cavern F1 Area1 - from CLEAN source")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    records = find_records(data, DEEP_START, DEEP_END)

    # Collect headers per slot
    headers_by_slot = {}
    for r in records:
        s = r['slot']
        h = r['header']
        if s not in headers_by_slot:
            headers_by_slot[s] = {}
        h_hex = h.hex()
        headers_by_slot[s][h_hex] = headers_by_slot[s].get(h_hex, 0) + 1

    print(f"\n  Found {len(records)} records total")
    for slot in sorted(headers_by_slot.keys()):
        print(f"\n  Slot {slot} headers:")
        for h_hex, count in sorted(headers_by_slot[slot].items(), key=lambda x: -x[1]):
            print(f"    {h_hex}: {count} occurrences")

    # Build the swap mapping: most common slot 0 header <-> most common slot 2 header
    # But actually, let's swap ALL headers between slots
    # Strategy: collect ordered list of headers for slot 0 and slot 2
    slot0_records = [r for r in records if r['slot'] == 0]
    slot2_records = [r for r in records if r['slot'] == 2]

    print(f"\n  Slot 0 records: {len(slot0_records)}")
    print(f"  Slot 2 records: {len(slot2_records)}")

    # Save original headers
    slot0_headers = [bytes(r['header']) for r in slot0_records]
    slot2_headers = [bytes(r['header']) for r in slot2_records]

    # For each slot 0 record, assign a slot 2 header (cycling if needed)
    # For each slot 2 record, assign a slot 0 header (cycling if needed)
    print(f"\n  --- Swapping headers ---")
    swapped = 0

    if slot0_headers and slot2_headers:
        # Pick the most common header from each slot as the replacement
        most_common_0 = max(set(h.hex() for h in slot0_headers),
                           key=lambda x: sum(1 for h in slot0_headers if h.hex() == x))
        most_common_2 = max(set(h.hex() for h in slot2_headers),
                           key=lambda x: sum(1 for h in slot2_headers if h.hex() == x))

        hdr0 = bytes.fromhex(most_common_0)
        hdr2 = bytes.fromhex(most_common_2)

        print(f"  Most common slot 0 header: {most_common_0}")
        print(f"  Most common slot 2 header: {most_common_2}")
        print(f"  Swap: slot 0 records get header {most_common_2}")
        print(f"         slot 2 records get header {most_common_0}")

        for r in slot0_records:
            off = r['header_offset']
            old = data[off:off+4].hex()
            data[off:off+4] = hdr2
            swapped += 1

        for r in slot2_records:
            off = r['header_offset']
            old = data[off:off+4].hex()
            data[off:off+4] = hdr0
            swapped += 1

    print(f"\n  Swapped {swapped} headers total")

    # Show some examples after swap
    print(f"\n  --- After swap (first 5 per slot) ---")
    records_after = find_records(data, DEEP_START, DEEP_END)
    shown = {0: 0, 1: 0, 2: 0}
    for r in records_after:
        s = r['slot']
        if shown.get(s, 0) < 3:
            print(f"    0x{r['header_offset']:X}: header={r['header'].hex()} slot={s} flags=0x{r['flags']:02X}")
            shown[s] = shown.get(s, 0) + 1

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print(f"\n{'='*70}")
    print("  Slot markers are UNCHANGED (no dark entities expected)")
    print("  Only the 4-byte command headers are swapped between slots")
    print()
    print("  WATCH FOR:")
    print("  - Goblins with Bat behavior? -> HEADERS CONTROL AI")
    print("  - Normal behavior? -> headers don't control AI")
    print("  - Crash? -> headers are structural")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
