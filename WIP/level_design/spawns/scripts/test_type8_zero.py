#!/usr/bin/env python3
"""
TEST: Zero out type-8 target data to see what breaks.

Type-8 target 1: script+0x1DC0 (abs 0xF7C85C) - 512 bytes of room bytecode
Type-8 target 2: script+0x1FC4 (abs 0xF7CA60) - contains dialogue text

Test: zero out 256 bytes at type-8 target 1 only (the safer one without text).

If monsters lose AI -> AI is in the bytecode here.
If crash -> bytecode is critical for room loading.
If no change -> this section is not AI-related.

Start from CLEAN BLAZE.ALL.
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent

BLAZE_SRC = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
BLAZE_OUT = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Cavern F1 Area1
GROUP_OFFSET = 0xF7A97C
NUM_MONSTERS = 3
SCRIPT_START = GROUP_OFFSET + NUM_MONSTERS * 96  # 0xF7AA9C

# Type-8 target 1
TARGET_OFFSET = SCRIPT_START + 0x1DC0  # 0xF7C85C
ZERO_SIZE = 256  # zero 256 bytes


def main():
    print("=" * 70)
    print("  TEST: Zero out type-8 target 1 data (256 bytes)")
    print("  Cavern F1 Area1 - from CLEAN source")
    print("=" * 70)

    data = bytearray(BLAZE_SRC.read_bytes())

    # Show what we're zeroing
    original = data[TARGET_OFFSET:TARGET_OFFSET + ZERO_SIZE]
    nonzero = sum(1 for b in original if b != 0)
    print(f"\n  Target: 0x{TARGET_OFFSET:X} (script+0x1DC0)")
    print(f"  Zeroing {ZERO_SIZE} bytes ({nonzero} non-zero bytes)")
    print(f"  First 32 bytes: {original[:32].hex()}")

    # Zero it out
    data[TARGET_OFFSET:TARGET_OFFSET + ZERO_SIZE] = b'\x00' * ZERO_SIZE

    # Save
    BLAZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLAZE_OUT.write_bytes(data)
    print(f"\n[SAVED] {BLAZE_OUT}")

    print(f"\n{'='*70}")
    print("  WATCH FOR:")
    print("  - Monsters passive/no AI? -> AI WAS HERE")
    print("  - Fewer monsters spawning? -> spawn data was here")
    print("  - Crash? -> critical bytecode")
    print("  - No change? -> this data is not used for AI")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
