#!/usr/bin/env python3
"""
Patch falling rock damage in Cavern of Death.

Modifies hardcoded immediate value at RAM 0x800CE7B8:
    addiu a1, zero, 10  →  addiu a1, zero, <new_value>

Usage:
    python patch_falling_rock.py --damage 5
"""

import sys
import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "trap_damage_config.json"


def load_config_damage():
    """Load damage% from trap_damage_config.json for falling rocks (10%)."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Get the replacement value for 10% traps
        values = config.get('overlay_patches', {}).get('values', {})
        return values.get('10', 25)  # Default to 25 if not found
    except Exception as e:
        print(f"[WARNING] Could not read config file: {e}")
        print("   Using default damage% = 25")
        return 25


def patch_falling_rock_damage(blaze_path, damage_percent, dry_run=False):
    """
    Patch falling rock damage% (Cavern of Death).

    Args:
        blaze_path: Path to BLAZE.ALL
        damage_percent: New damage% (1-100)
        dry_run: If True, only search without modifying

    Returns:
        Offset where pattern was found, or None if not found
    """

    if not 1 <= damage_percent <= 100:
        raise ValueError(f"damage_percent must be 1-100, got {damage_percent}")

    # Pattern CORRECT (vérifié in-game 2026-02-13):
    # addiu a1, zero, 10 + addu a2, zero, zero
    pattern = bytes([
        0x0A, 0x00, 0x05, 0x24,  # addiu a1, zero, 10  ← TARGET
        0x21, 0x30, 0x00, 0x00,  # addu a2, zero, zero
    ])

    # On va patcher TOUS les falling rocks (10 occurrences dans BLAZE.ALL)
    # Cela affecte tous les donjons (Cavern, Tower, Hall of Demons, etc.)

    # Lire BLAZE.ALL
    blaze_path = Path(blaze_path)
    if not blaze_path.exists():
        raise FileNotFoundError(f"BLAZE.ALL not found: {blaze_path}")

    with open(blaze_path, 'rb') as f:
        data = f.read()

    # Trouver TOUTES les occurrences
    matches = []
    offset = 0
    while True:
        pos = data.find(pattern, offset)
        if pos == -1:
            break
        matches.append(pos)
        offset = pos + 1

    if not matches:
        print("[ERROR] Pattern not found in BLAZE.ALL")
        print(f"   Searched for: {pattern.hex(' ')}")
        return None

    print(f"[OK] Found {len(matches)} falling rock trap(s):")
    for i, pos in enumerate(matches):
        old_value = data[pos]
        print(f"   [{i+1}] BLAZE 0x{pos:08X} - damage {old_value}%")

    if dry_run:
        print("\n[DRY RUN] No changes made")
        return matches

    # Appliquer le patch à TOUTES les occurrences
    data = bytearray(data)
    patched_count = 0

    for pos in matches:
        old_value = data[pos]
        data[pos] = damage_percent
        patched_count += 1

    # Écrire le fichier modifié
    with open(blaze_path, 'wb') as f:
        f.write(data)

    print(f"\n[OK] Patched {patched_count} falling rock trap(s): 10% → {damage_percent}%")
    print("   Affects ALL dungeons (Cavern, Tower, Hall of Demons, etc.)")

    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Patch falling rock damage in Blaze & Blade"
    )
    parser.add_argument(
        '--damage',
        type=int,
        default=25,
        help='New damage percentage (1-100, default: 25 to match trap_damage_config.json)'
    )
    parser.add_argument(
        '--blaze',
        type=str,
        default='output/BLAZE.ALL',
        help='Path to BLAZE.ALL (default: output/BLAZE.ALL)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Search only, do not modify file'
    )

    args = parser.parse_args()

    print("=== Falling Rock Damage Patcher ===\n")
    print(f"Target: {args.blaze}")
    print(f"New damage: {args.damage}%")
    print(f"Dry run: {args.dry_run}\n")

    try:
        offset = patch_falling_rock_damage(
            args.blaze,
            args.damage,
            dry_run=args.dry_run
        )

        if offset is None:
            return 1

        print("\n[OK] Success!")
        print("\nNext steps:")
        print("1. Run build_gameplay_patch.bat to inject into BIN")
        print("2. Test in-game (Cavern of Death, falling rocks)")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
