"""
patch_monster_spells.py
Patches monster spell assignments in BLAZE.ALL at ALL occurrences

Usage: py -3 patch_monster_spells.py
"""

import json
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
MONSTER_STATS_DIR = SCRIPT_DIR.parent
BLAZE_ALL = MONSTER_STATS_DIR.parent.parent / "output" / "BLAZE.ALL"
SPELL_PATCH_FILE = MONSTER_STATS_DIR / "General" / "monster_spells_patch.json"

# Spell table location (primary)
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


def find_all_occurrences(data: bytes, pattern: bytes) -> list:
    """Find all occurrences of a pattern in data."""
    occurrences = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        occurrences.append(pos)
        pos += 1
    return occurrences


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
    total_patches = 0
    for entry in entries:
        if not entry.get("enabled", True):
            continue

        index = entry.get("index")
        name = entry.get("name", f"Entry {index}")

        # Get the original bytes from the primary location
        if index is not None:
            primary_offset = SPELL_TABLE_START + (index * SPELL_ENTRY_SIZE)
        else:
            offset_hex = entry.get("offset_hex")
            if offset_hex:
                primary_offset = int(offset_hex, 16)
            else:
                print(f"  WARNING: {name} - no index or offset specified, skipping")
                continue

        # Get original bytes - either from config or from file
        if "original_bytes" in entry:
            original_entry = bytes(entry["original_bytes"])
        else:
            original_entry = bytes(blaze_data[primary_offset:primary_offset+16])

        # Build the new entry
        new_entry = build_spell_entry(entry)

        # Skip if already patched
        if original_entry == new_entry:
            print(f"  {name}: Already patched at primary location")
            # Still search for other occurrences of original pattern
            # in case there are unpatched copies elsewhere

        old_hex = ' '.join(f'{b:02X}' for b in original_entry)
        new_hex = ' '.join(f'{b:02X}' for b in new_entry)

        print(f"  {name} (entry {index}):")
        print(f"    Original: {old_hex}")
        print(f"    New:      {new_hex}")

        # Find ALL occurrences of the original entry in the entire file
        occurrences = find_all_occurrences(bytes(blaze_data), original_entry)

        if not occurrences:
            # Maybe already patched - check for new_entry pattern
            already_patched = find_all_occurrences(bytes(blaze_data), new_entry)
            if already_patched:
                print(f"    -> Already patched at {len(already_patched)} location(s)")
                continue
            else:
                print(f"    -> WARNING: Original pattern not found!")
                continue

        print(f"    -> Found {len(occurrences)} occurrence(s) to patch:")

        # Patch ALL occurrences
        for offset in occurrences:
            print(f"       0x{offset:X}")
            blaze_data[offset:offset+16] = new_entry
            total_patches += 1

    print()
    print(f"Total patches applied: {total_patches}")
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
