#!/usr/bin/env python3
"""
TEST: Swap slot references in spawn commands (Goblin slot 0 <-> Bat slot 2).

Observation from spawn command analysis:
  Each spawn command ends with: [u16 value] [FF FF FF FF FF FF] [u16 slot]
  The slot byte after the 6 FF bytes determines which monster slot spawns.

  In Area 1's spawn groups:
    Commands with XX=00 in [XX 0B YY 00] prefix -> end with slot=00 (Goblin)
    Commands with XX=01 in [XX 0B YY 00] prefix -> end with slot=02 (Bat)

This test: swap ONLY the slot bytes (00 <-> 02) at the end of spawn commands.
  Keep: L, R, anim, 96-byte entries, type-7, everything else.

  If a different monster APPEARS at the spawn point -> slot byte controls visual
  If AI CHANGES -> slot byte determines AI via the monster definition
  If NOTHING changes -> slot byte is not the spawn reference
  If CRASH -> slot byte is critical but needs other changes too

Focus: spawn command region in Area 1 (after the resource definition block).
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

# Spawn command region starts after the resource definition block
# Block 4 ends around script+0x41C, spawn commands follow
# We'll scan from script+0x420 to script+0x600 (the spawn command groups)
SCAN_START = SCRIPT_START + 0x420   # 0xF7AEBC
SCAN_END   = SCRIPT_START + 0x600   # 0xF7B09C


def find_spawn_slots(data, start, end):
    """Find all [FFFFFFFFFFFF][u16 slot] patterns in the region."""
    results = []
    i = start
    while i < end - 8:
        # Look for 6 consecutive FF bytes
        if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
            slot_off = i + 6
            slot_val = struct.unpack_from('<H', data, slot_off)[0]
            # Read the u16 value before the FFs
            val_before = struct.unpack_from('<H', data, i - 2)[0]
            results.append({
                'ff_offset': i,
                'slot_offset': slot_off,
                'slot': slot_val,
                'val_before': val_before,
            })
            i = slot_off + 2  # skip past slot bytes
        else:
            i += 1
    return results


def find_prefix_bytes(data, start, end):
    """Find all [XX 0B YY 00] patterns in the region."""
    results = []
    for i in range(start, end - 4):
        if data[i+1] == 0x0B and data[i+3] == 0x00:
            xx = data[i]
            yy = data[i+2]
            if xx <= 3 and yy < 0x20:  # reasonable values
                results.append({
                    'offset': i,
                    'xx': xx,
                    'yy': yy,
                })
    return results


def main():
    print("=" * 70)
    print("  TEST: Swap spawn command slot bytes (Goblin 0 <-> Bat 2)")
    print("  Cavern F1 Area1")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())
    print(f"  BLAZE.ALL: {len(data):,} bytes")
    print(f"  Scan region: 0x{SCAN_START:X} - 0x{SCAN_END:X}")

    # Find slot references
    slots = find_spawn_slots(data, SCAN_START, SCAN_END)
    prefixes = find_prefix_bytes(data, SCAN_START, SCAN_END)

    print(f"\n  Found {len(slots)} spawn slot references:")
    for s in slots:
        print(f"    0x{s['slot_offset']:X}: slot={s['slot']} (val_before=0x{s['val_before']:04X}={s['val_before']})")

    print(f"\n  Found {len(prefixes)} [XX 0B YY 00] prefixes:")
    for p in prefixes:
        print(f"    0x{p['offset']:X}: XX={p['xx']} YY=0x{p['yy']:02X}")

    # Show correlation between prefix XX and slot
    print(f"\n  --- Correlation analysis ---")
    for s in slots:
        # Find nearest prefix before this slot
        nearest = None
        for p in prefixes:
            if p['offset'] < s['slot_offset'] and (nearest is None or p['offset'] > nearest['offset']):
                nearest = p
        if nearest and s['slot_offset'] - nearest['offset'] < 32:
            print(f"    Prefix XX={nearest['xx']} at 0x{nearest['offset']:X} -> slot={s['slot']} at 0x{s['slot_offset']:X}")

    # --- SWAP ---
    print(f"\n  --- Swapping slot bytes: 0 <-> 2 ---")
    swapped = 0
    for s in slots:
        old_slot = s['slot']
        if old_slot == 0:
            new_slot = 2
        elif old_slot == 2:
            new_slot = 0
        else:
            continue  # skip slot 1 (Shaman) and others

        struct.pack_into('<H', data, s['slot_offset'], new_slot)
        print(f"    0x{s['slot_offset']:X}: slot {old_slot} -> {new_slot}")
        swapped += 1

    print(f"\n  Swapped {swapped} slot references")

    # Verify
    print(f"\n  --- After swap ---")
    slots_after = find_spawn_slots(data, SCAN_START, SCAN_END)
    for s in slots_after:
        print(f"    0x{s['slot_offset']:X}: slot={s['slot']}")

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print(f"\n" + "=" * 70)
    print("  EXPECTED:")
    print("  - Spawn points that were Goblin now reference Bat slot")
    print("  - Spawn points that were Bat now reference Goblin slot")
    print("")
    print("  IF model+AI change -> slot byte is the FULL reference")
    print("  IF only model changes -> slot controls visual, AI elsewhere")
    print("  IF nothing changes -> slot byte is not a spawn reference")
    print("  IF crash -> slot byte is important but something else needed")
    print("=" * 70)


if __name__ == '__main__':
    main()
