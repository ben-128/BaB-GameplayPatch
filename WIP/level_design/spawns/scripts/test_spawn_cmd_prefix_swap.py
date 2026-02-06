#!/usr/bin/env python3
"""
TEST: Swap the XX byte in [XX 0B YY 00] spawn command prefixes.

Previous test: swapping slot bytes after FFFFFFFFFFFF had NO effect.

Observation: the [XX 0B YY 00] prefix perfectly correlates with monster type:
  XX=0 -> always Goblin (slot 0)
  XX=1 -> always Bat (slot 2)
  No XX=2 observed (no Shaman spawns in these groups?)

This test: swap XX values (0 <-> 1) in ALL [XX 0B YY 00] prefixes.
  Also swap the initial spawn blocks (blocks 0-2) which are before the
  main spawn command area.

  Goblin commands (XX=0) -> XX=1
  Bat commands (XX=1) -> XX=0

Start from CLEAN BLAZE.ALL (undo previous test).
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

# Scan the FULL spawn command region (from start of script area)
SCAN_START = SCRIPT_START + 0x080  # after initial offset table
SCAN_END   = SCRIPT_START + 0x600  # covers all spawn groups


def find_0B_prefixes(data, start, end):
    """Find all [XX 0B YY 00] patterns."""
    results = []
    for i in range(start, end - 4):
        if data[i+1] == 0x0B and data[i+3] == 0x00:
            xx = data[i]
            yy = data[i+2]
            if xx <= 3 and 0 < yy < 0x20:
                results.append({
                    'offset': i,
                    'xx': xx,
                    'yy': yy,
                })
    return results


def main():
    print("=" * 70)
    print("  TEST: Swap XX in [XX 0B YY 00] prefixes (0 <-> 1)")
    print("  Cavern F1 Area1 - from CLEAN source")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    # Find all prefixes
    prefixes = find_0B_prefixes(data, SCAN_START, SCAN_END)

    print(f"\n  Found {len(prefixes)} [XX 0B YY 00] prefixes:")
    for p in prefixes:
        # Show context (24 bytes around)
        ctx_start = max(0, p['offset'] - 4)
        ctx_end = min(len(data), p['offset'] + 20)
        ctx = data[ctx_start:ctx_end]
        print(f"    0x{p['offset']:X}: XX={p['xx']} 0B YY=0x{p['yy']:02X} 00  "
              f"context: {ctx.hex()}")

    # Also look at the INITIAL spawn blocks (blocks 0-3, around script+0x0A0)
    # These have a different format but also contain slot references
    print(f"\n  --- Initial spawn blocks (script+0x080 to script+0x110) ---")
    init_start = SCRIPT_START + 0x080
    init_end = SCRIPT_START + 0x120
    init_region = data[init_start:init_end]
    for i in range(0, len(init_region), 8):
        chunk = init_region[i:i+8]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        i16s = []
        for k in range(0, len(chunk), 2):
            if k + 2 <= len(chunk):
                i16s.append(struct.unpack_from('<h', chunk, k)[0])
        i16_str = ' '.join(f'{v:6d}' for v in i16s)
        print(f"    0x{init_start+i:X}: {hex_str:<24s} | {i16_str}")

    # --- SWAP XX values ---
    print(f"\n  --- Swapping XX: 0 <-> 1 ---")
    swapped = 0
    for p in prefixes:
        old_xx = p['xx']
        if old_xx == 0:
            new_xx = 1
        elif old_xx == 1:
            new_xx = 0
        else:
            continue

        data[p['offset']] = new_xx
        print(f"    0x{p['offset']:X}: XX={old_xx} -> XX={new_xx} (YY=0x{p['yy']:02X})")
        swapped += 1

    print(f"\n  Swapped {swapped} prefix XX bytes")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print(f"\n" + "=" * 70)
    print("  Goblin spawn commands now have XX=1 (Bat's value)")
    print("  Bat spawn commands now have XX=0 (Goblin's value)")
    print("")
    print("  WATCH FOR:")
    print("  - Do Goblins now appear as Bats? (model change)")
    print("  - Do they behave differently? (AI change)")
    print("  - Crash? (XX controls something structural)")
    print("=" * 70)


if __name__ == '__main__':
    main()
