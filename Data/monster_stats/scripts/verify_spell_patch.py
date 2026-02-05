"""
Verify spell patch is applied in both BLAZE.ALL and the final BIN
"""
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent.parent.parent / "output"

BLAZE_ALL = OUTPUT_DIR / "BLAZE.ALL"
PATCHED_BIN = OUTPUT_DIR / "Blaze & Blade - Patched.bin"

# Spell entry 6 (Goblin-Shaman) location in BLAZE.ALL
SPELL_ENTRY_OFFSET = 0x9E8DEE
SPELL_ENTRY_SIZE = 16

# Expected patched value (Blaze, Lightningbolt, Blizzard)
EXPECTED_PATCHED = bytes([0xAF, 0x00, 0x0A, 0x0B, 0x0C, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0xB0, 0x00, 0xA0, 0x00, 0xA0, 0x1F])
# Original value
ORIGINAL_VALUE = bytes([0xAF, 0x00, 0x00, 0x08, 0x09, 0x03, 0x03, 0x03, 0x03, 0x03, 0xB0, 0x00, 0xA0, 0x00, 0xA0, 0x1F])

def find_all_occurrences(data: bytes, pattern: bytes) -> list:
    """Find all occurrences of a pattern in data"""
    occurrences = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        occurrences.append(pos)
        pos += 1
    return occurrences

def check_file(filepath: Path, name: str):
    """Check spell entry in a file"""
    if not filepath.exists():
        print(f"\n{name}: FILE NOT FOUND")
        return

    data = filepath.read_bytes()
    print(f"\n{name} ({len(data):,} bytes):")

    # Check at known offset
    entry_at_offset = data[SPELL_ENTRY_OFFSET:SPELL_ENTRY_OFFSET+16]
    hex_str = ' '.join(f'{b:02X}' for b in entry_at_offset)
    print(f"  At offset 0x{SPELL_ENTRY_OFFSET:X}: {hex_str}")

    if entry_at_offset == EXPECTED_PATCHED:
        print(f"  -> PATCHED (Blaze/Lightningbolt/Blizzard)")
    elif entry_at_offset == ORIGINAL_VALUE:
        print(f"  -> ORIGINAL (Stone Bullet/Magic Missile)")
    else:
        print(f"  -> UNKNOWN VALUE")

    # Find all occurrences of both patterns
    print(f"\n  Searching for all spell entry patterns...")

    patched_locs = find_all_occurrences(data, EXPECTED_PATCHED)
    original_locs = find_all_occurrences(data, ORIGINAL_VALUE)

    print(f"  PATCHED pattern found at {len(patched_locs)} location(s):")
    for loc in patched_locs[:10]:
        print(f"    0x{loc:X}")
    if len(patched_locs) > 10:
        print(f"    ... and {len(patched_locs) - 10} more")

    print(f"  ORIGINAL pattern found at {len(original_locs)} location(s):")
    for loc in original_locs[:10]:
        print(f"    0x{loc:X}")
    if len(original_locs) > 10:
        print(f"    ... and {len(original_locs) - 10} more")

def main():
    print("=" * 60)
    print("  Spell Patch Verification")
    print("=" * 60)

    check_file(BLAZE_ALL, "BLAZE.ALL")
    check_file(PATCHED_BIN, "Patched BIN")

    print("\n" + "=" * 60)
    print("  Verification complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
