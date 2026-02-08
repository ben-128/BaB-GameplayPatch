#!/usr/bin/env python3
"""
Patch the chest despawn timer in the game BIN.

The entity update function in SLES has a batch timer loop processing
48 halfword timers at entity+0x80 through entity+0xDE. Each timer is
associated with a flag bitmask in a handler table at RAM 0x8003C030.
When a timer reaches 0, the corresponding flag is CLEARED from
entity+0x40 via: entity+0x40 AND= ~handler_table[timer_index].

Timer[0] (entity+0x80) controls bit 27 (0x08000000) of entity+0x40.
Chests use timer[0] with initial value ~1000 (20s at 50fps PAL).
When bit 27 is cleared, the chest despawns.

Strategy:
1. NOP the batch timer decrement (freeze all 48 timers)
2. Zero handler table entry[0] so timer[0] expiry clears NO flag
   (belt-and-suspenders: even if overlay code decrements entity+0x80,
   the flag won't be cleared when it reaches 0)

IMPORTANT: entity+0x4C is for combat HP/damage - do NOT touch it.
The bgtz at 0x017794 is the general entity death mechanism.

Must run AFTER the BIN has been created (after BLAZE.ALL injection).
"""

import struct
import sys
from pathlib import Path


PATCHES = [
    {
        'name': 'entity+0x80 batch timer decrement',
        'desc': 'addiu $v0,$v0,-1 -> nop (freeze all batch timers)',
        # lhu $v0,0($a1) + nop + addiu $v0,$v0,-1 + sh $v0,0($a1)
        'signature': [0x94A20000, 0x00000000, 0x2442FFFF, 0xA4A20000],
        'patch_index': 2,
        'verify': 0x2442FFFF,
        'replacement': 0x00000000,  # nop
    },
    {
        'name': 'timer[0] handler table entry (bit 27 mask)',
        'desc': 'table[0] = 0 (timer[0] expiry clears no flag)',
        # Handler table: entry[0]=0x08000000, entry[1]=0x02000000,
        # entry[2]=0x04000000, entry[3]=0x00000000
        'signature': [0x08000000, 0x02000000, 0x04000000, 0x00000000],
        'patch_index': 0,
        'verify': 0x08000000,
        'replacement': 0x00000000,  # no bits = no flag cleared
    },
]


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    bin_path = project_dir / 'output' / 'Blaze & Blade - Patched.bin'

    print("Loot Timer: patch chest despawn in SLES executable")
    print(f"  Target: {bin_path}")

    if not bin_path.exists():
        print(f"[ERROR] BIN not found: {bin_path}")
        sys.exit(1)

    data = bytearray(bin_path.read_bytes())
    print(f"  BIN size: {len(data):,} bytes")

    total_patched = 0

    for patch in PATCHES:
        print(f"\n  --- {patch['name']} ---")

        # Build signature bytes
        sig = b''.join(struct.pack('<I', w) for w in patch['signature'])

        # Search
        positions = []
        pos = 0
        while True:
            pos = data.find(sig, pos)
            if pos == -1:
                break
            positions.append(pos)
            pos += 4

        if len(positions) == 0:
            # Signature might already be patched - check with replacement
            patched_sig = list(patch['signature'])
            patched_sig[patch['patch_index']] = patch['replacement']
            sig_patched = b''.join(struct.pack('<I', w) for w in patched_sig)
            pos2 = data.find(sig_patched)
            if pos2 >= 0:
                print(f"  Already patched at BIN 0x{pos2:08X}")
                total_patched += 1
                continue
            print(f"  [ERROR] Signature not found!")
            print(f"  Expected: {' '.join(f'{w:08X}' for w in patch['signature'])}")
            sys.exit(1)

        if len(positions) > 1:
            print(f"  [WARNING] {len(positions)} occurrences found!")
            # For data patches, only patch in the SLES region (high BIN offsets)
            # SLES is near end of disc, BLAZE.ALL is near beginning
            sles_region = [p for p in positions if p > 0x29000000]
            if sles_region:
                print(f"  Using SLES-region match(es): {len(sles_region)}")
                positions = sles_region
            else:
                print(f"  [ERROR] No matches in SLES region!")
                sys.exit(1)

        for sig_pos in positions:
            target_pos = sig_pos + patch['patch_index'] * 4
            old_word = struct.unpack_from('<I', data, target_pos)[0]

            if old_word != patch['verify']:
                print(f"  [SKIP] 0x{target_pos:08X}: unexpected 0x{old_word:08X}")
                continue

            data[target_pos:target_pos + 4] = struct.pack('<I', patch['replacement'])
            print(f"  PATCH BIN 0x{target_pos:08X}: {patch['desc']}")
            total_patched += 1

    if total_patched == 0:
        print("\n[ERROR] No patches applied!")
        sys.exit(1)

    bin_path.write_bytes(data)

    print(f"\n{'='*60}")
    print(f"  {total_patched} patch(es) applied - chests will no longer despawn")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
