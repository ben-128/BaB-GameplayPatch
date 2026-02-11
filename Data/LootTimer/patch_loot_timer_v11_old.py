#!/usr/bin/env python3
"""
Patch chest despawn timer INIT value in BLAZE.ALL (v11).

Previous versions (v1-v10) tried to NOP the timer decrement, but failed.

v11: Instead of NOPing the decrement, we CHANGE THE INIT VALUE.
     The timer is initialized at exactly ONE place in BLAZE.ALL:

     0x01C216CC: addiu $v0, $zero, 0x3E8   ; load 1000
     0x01C216D0: sh $v0, 0x14($s2)         ; store to entity+0x14 (timer init)

     By changing 0x3E8 (1000 = 20 seconds at 50fps PAL) to a larger value,
     chests will stay longer before despawning.

     Config: loot_timer.json - chest_despawn_seconds
     - 0 = infinite (0xFFFF = 65535 frames, ~22 minutes)
     - >0 = custom duration in seconds

Runs at build step 7 (patches output/BLAZE.ALL before BIN injection).
"""

import json
import struct
import sys
from pathlib import Path

OLD_VALUE = 0x03E8  # 1000 (original 20 seconds)

# Pattern: addiu $v0, $zero, OLD_VALUE followed by sh $v0, 0x14($s2)
OLD_ADDIU = 0x240203E8  # addiu $v0, $zero, 0x3E8
SH_TO_14 = 0xA6420014  # sh $v0, 0x14($s2)


def find_timer_init(data: bytes) -> list[int]:
    """Find the chest timer init pattern in BLAZE.ALL.

    Pattern: addiu $v0, $zero, 0x3E8 followed immediately by sh $v0, 0x14($s2)
    """
    matches = []

    for i in range(0, len(data) - 8, 4):
        word1 = struct.unpack_from('<I', data, i)[0]
        word2 = struct.unpack_from('<I', data, i + 4)[0]

        if word1 == OLD_ADDIU and word2 == SH_TO_14:
            matches.append(i)

    return matches


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'output' / 'BLAZE.ALL'
    config_path = script_dir / 'loot_timer.json'

    # Load config
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    chest_despawn_seconds = config.get('chest_despawn_seconds', 0)

    # Calculate new timer value
    # Timer decrements every 20th frame at 50fps PAL
    # So: frames = seconds * 50fps / 20 = seconds * 2.5
    # But empirically, 1000 frames = 20 seconds, so 1 second = 50 frames
    if chest_despawn_seconds == 0:
        # Infinite: use max halfword value
        new_value = 0xFFFF  # 65535 frames (~22 minutes)
        duration_desc = "infinite (~22 minutes)"
    else:
        # Convert seconds to frames (50 fps PAL)
        new_value = int(chest_despawn_seconds * 50)
        if new_value > 0xFFFF:
            new_value = 0xFFFF
        duration_desc = f"{chest_despawn_seconds} seconds"

    print("Loot Timer v11: Patch chest timer INIT value (not decrement)")
    print(f"  Config: {config_path}")
    print(f"  Desired duration: {duration_desc}")
    print(f"  Target: {blaze_path}")
    print(f"  Old value: {OLD_VALUE} frames (~20 seconds)")
    print(f"  New value: {new_value} frames ({duration_desc})")
    print()

    if not blaze_path.exists():
        print(f"[ERROR] BLAZE.ALL not found: {blaze_path}")
        sys.exit(1)

    data = bytearray(blaze_path.read_bytes())
    print(f"  BLAZE.ALL size: {len(data):,} bytes")

    matches = find_timer_init(data)
    print(f"  Timer INIT patterns found: {len(matches)}")

    if not matches:
        print("[ERROR] No chest timer INIT pattern found!")
        print("Expected pattern: addiu $v0,$zero,0x3E8 / sh $v0,0x14($s2)")
        sys.exit(1)

    new_addiu = 0x24020000 | new_value  # addiu $v0, $zero, new_value

    patched = 0
    for offset in matches:
        current = struct.unpack_from('<I', data, offset)[0]
        ram = (offset - 0x009468A8) + 0x80080000 if offset >= 0x009468A8 else 0

        if current == new_addiu:
            print(f"  0x{offset:08X} (RAM ~0x{ram:08X}): already patched")
            continue

        if current != OLD_ADDIU:
            print(f"  0x{offset:08X}: UNEXPECTED 0x{current:08X}, skipping")
            continue

        data[offset:offset+4] = struct.pack('<I', new_addiu)
        patched += 1
        print(f"  PATCH 0x{offset:08X} (RAM ~0x{ram:08X}): 0x3E8 -> 0x{new_value:04X}")

    if patched == 0:
        print()
        print(f"{'='*60}")
        print(f"  All {len(matches)} timer init values already patched")
        print(f"{'='*60}")
    else:
        blaze_path.write_bytes(data)
        print()
        print(f"{'='*60}")
        print(f"  Patched {patched}/{len(matches)} timer init values")
        if chest_despawn_seconds == 0:
            print(f"  Chests will now stay for ~22 minutes (infinite)")
        else:
            print(f"  Chests will now stay for {chest_despawn_seconds} seconds")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()
