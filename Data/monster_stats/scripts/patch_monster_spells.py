"""
patch_monster_spells.py
Patches monster spell assignments in BLAZE.ALL

Usage: py -3 patch_monster_spells.py
"""

import json
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
MONSTER_STATS_DIR = SCRIPT_DIR.parent
BLAZE_ALL = MONSTER_STATS_DIR.parent.parent / "output" / "BLAZE.ALL"
SPELL_PATCH_FILE = MONSTER_STATS_DIR / "General" / "monster_spells_patch.json"

# Spell table location
SPELL_TABLE_START = 0x9E8D8E
SPELL_ENTRY_SIZE = 16


def build_spell_entry(entry: dict) -> bytes:
    """Build a 16-byte spell entry from JSON config."""
    result = bytearray(16)

    # Bytes 0-1: flags1
    flags1 = entry.get("flags1", [0, 0])
    result[0] = flags1[0]
    result[1] = flags1[1]

    # Bytes 2-4: attack spells (3 slots)
    attack_spells = entry.get("attack_spells", [0, 0, 0])
    for i, spell_id in enumerate(attack_spells[:3]):
        result[2 + i] = spell_id

    # Bytes 5-9: weighted spell repeated
    weighted_spell = entry.get("weighted_spell", 0)
    weighted_count = entry.get("weighted_count", 5)
    for i in range(min(weighted_count, 5)):
        result[5 + i] = weighted_spell

    # Bytes 10-11: flags2
    flags2 = entry.get("flags2", [0, 0])
    result[10] = flags2[0]
    result[11] = flags2[1]

    # Bytes 12-14: utility spells (3 slots)
    utility_spells = entry.get("utility_spells", [0, 0, 0])
    for i, spell_id in enumerate(utility_spells[:3]):
        result[12 + i] = spell_id

    # Byte 15: support spell
    result[15] = entry.get("support_spell", 0)

    return bytes(result)


def main():
    print("=" * 60)
    print("  Monster Spell Assignment Patcher")
    print("=" * 60)
    print()

    # Check files exist
    if not BLAZE_ALL.exists():
        print(f"ERROR: {BLAZE_ALL} not found!")
        return 1

    if not SPELL_PATCH_FILE.exists():
        print(f"ERROR: {SPELL_PATCH_FILE} not found!")
        return 1

    # Read BLAZE.ALL
    print(f"Reading {BLAZE_ALL}...")
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  Size: {len(blaze_data)} bytes")
    print()

    # Read spell patch config
    print(f"Reading {SPELL_PATCH_FILE}...")
    with open(SPELL_PATCH_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    entries = config.get("entries", [])
    print(f"  Found {len(entries)} spell entries to patch")
    print()

    # Patch each enabled entry
    patched_count = 0
    for entry in entries:
        if not entry.get("enabled", True):
            continue

        index = entry.get("index")
        name = entry.get("name", f"Entry {index}")
        offset_hex = entry.get("offset_hex")

        if offset_hex:
            # Use explicit offset
            offset = int(offset_hex, 16)
        elif index is not None:
            # Calculate from index
            offset = SPELL_TABLE_START + (index * SPELL_ENTRY_SIZE)
        else:
            print(f"  WARNING: {name} - no index or offset specified, skipping")
            continue

        # Build the entry bytes
        new_entry = build_spell_entry(entry)

        # Show what we're patching
        old_entry = blaze_data[offset:offset+16]
        old_hex = ' '.join(f'{b:02X}' for b in old_entry)
        new_hex = ' '.join(f'{b:02X}' for b in new_entry)

        print(f"  {name} (entry {index}) at 0x{offset:X}:")
        print(f"    OLD: {old_hex}")
        print(f"    NEW: {new_hex}")

        # Apply patch
        blaze_data[offset:offset+16] = new_entry
        patched_count += 1

    print()
    print(f"Patched {patched_count} spell entries")
    print()

    # Write output
    print(f"Writing {BLAZE_ALL}...")
    BLAZE_ALL.write_bytes(blaze_data)

    print()
    print("=" * 60)
    print("  Spell assignments patched successfully!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
