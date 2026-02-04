"""
patch_items_in_bin.py
Patch les descriptions d'items directement dans BLAZE.ALL et patched.bin

Usage: py -3 patch_items_in_bin.py
"""

import json
import struct
from pathlib import Path
import shutil

SCRIPT_DIR = Path(__file__).parent
ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"
WORK_DIR = SCRIPT_DIR.parent / "work"
BLAZE_ALL = WORK_DIR / "BLAZE.ALL"
BLAZE_ALL_BACKUP = WORK_DIR / "BLAZE.ALL.backup"
PATCHED_BIN = WORK_DIR / "patched.bin"
PATCHED_BIN_BACKUP = WORK_DIR / "patched.bin.backup"

ITEM_ENTRY_SIZE = 128


def patch_item_description(data, offset, new_description, max_length=63):
    """Patch la description d'un item dans les données binaires"""
    desc_offset = offset + 0x41

    if desc_offset < 0 or desc_offset >= len(data):
        return False

    desc_bytes = new_description.encode('ascii', errors='ignore')

    if len(desc_bytes) > max_length:
        desc_bytes = desc_bytes[:max_length]

    end_offset = desc_offset + len(desc_bytes)
    if end_offset >= len(data):
        return False

    data[desc_offset:end_offset] = desc_bytes

    if end_offset < len(data):
        data[end_offset] = 0

    entry_end = offset + ITEM_ENTRY_SIZE
    if end_offset + 1 < entry_end and entry_end <= len(data):
        for i in range(end_offset + 1, entry_end):
            data[i] = 0

    return True


def find_blaze_all_offset_in_bin(bin_path, blaze_all_path):
    """Trouve l'offset de BLAZE.ALL dans le .bin"""
    print(f"Recherche de BLAZE.ALL dans {bin_path.name}...")

    # Lire les premiers bytes de BLAZE.ALL comme signature
    blaze_data = blaze_all_path.read_bytes()
    signature = blaze_data[:1024]  # Premiers 1KB comme signature

    # Lire le .bin
    bin_data = bin_path.read_bytes()

    # Chercher la signature
    offset = bin_data.find(signature)

    if offset != -1:
        print(f"  BLAZE.ALL trouve a l'offset: 0x{offset:08X}")
        return offset
    else:
        print("  BLAZE.ALL non trouve dans le .bin")
        return None


def patch_blaze_all(items):
    """Patch work/BLAZE.ALL"""
    print("=" * 70)
    print("  Patch de work/BLAZE.ALL")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERREUR: {BLAZE_ALL} n'existe pas!")
        return None

    print(f"Chargement de {BLAZE_ALL.name}...")
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  {len(blaze_data):,} bytes")

    # Créer backup
    if not BLAZE_ALL_BACKUP.exists():
        print(f"\nCreation du backup: {BLAZE_ALL_BACKUP.name}...")
        shutil.copy2(BLAZE_ALL, BLAZE_ALL_BACKUP)
    else:
        print(f"\nBackup existe: {BLAZE_ALL_BACKUP.name}")

    # Patcher
    print("\nPatch des items...")
    patched_count = 0

    for item in items:
        offset = item.get('offset_decimal', 0)
        new_desc = item.get('new_description', '')

        if offset <= 0 or not new_desc:
            continue

        if patch_item_description(blaze_data, offset, new_desc):
            patched_count += 1

    print(f"  Items patches: {patched_count}")

    # Sauvegarder
    print(f"\nSauvegarde de {BLAZE_ALL.name}...")
    BLAZE_ALL.write_bytes(blaze_data)

    return blaze_data


def patch_bin_file(items, blaze_data):
    """Patch work/patched.bin"""
    print()
    print("=" * 70)
    print("  Patch de work/patched.bin")
    print("=" * 70)
    print()

    if not PATCHED_BIN.exists():
        print(f"ERREUR: {PATCHED_BIN} n'existe pas!")
        print("Veuillez d'abord creer work/patched.bin")
        return False

    # Trouver l'offset de BLAZE.ALL dans le .bin
    blaze_offset = find_blaze_all_offset_in_bin(PATCHED_BIN, BLAZE_ALL_BACKUP)

    if blaze_offset is None:
        print("Impossible de trouver BLAZE.ALL dans le .bin")
        return False

    print(f"\nChargement de {PATCHED_BIN.name}...")
    bin_data = bytearray(PATCHED_BIN.read_bytes())
    print(f"  {len(bin_data):,} bytes")

    # Créer backup
    if not PATCHED_BIN_BACKUP.exists():
        print(f"\nCreation du backup: {PATCHED_BIN_BACKUP.name}...")
        shutil.copy2(PATCHED_BIN, PATCHED_BIN_BACKUP)
    else:
        print(f"\nBackup existe: {PATCHED_BIN_BACKUP.name}")

    # Patcher chaque item dans le .bin
    print("\nPatch des items dans le .bin...")
    patched_count = 0

    for item in items:
        offset = item.get('offset_decimal', 0)
        new_desc = item.get('new_description', '')

        if offset <= 0 or not new_desc:
            continue

        # Offset dans le .bin = offset BLAZE.ALL + offset dans BLAZE.ALL
        bin_offset = blaze_offset + offset

        if patch_item_description(bin_data, bin_offset, new_desc):
            patched_count += 1

    print(f"  Items patches dans le .bin: {patched_count}")

    # Sauvegarder
    print(f"\nSauvegarde de {PATCHED_BIN.name}...")
    PATCHED_BIN.write_bytes(bin_data)

    return True


def main():
    print("=" * 70)
    print("  Patch Items - BLAZE.ALL + patched.bin")
    print("=" * 70)
    print()

    # Charger items
    print(f"Chargement de {ITEMS_JSON.name}...")
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data['items']
    print(f"  {len(items)} items")
    print()

    # Patcher BLAZE.ALL
    blaze_data = patch_blaze_all(items)

    if blaze_data is None:
        return

    print()
    print("[OK] work/BLAZE.ALL patche avec succes")

    # Patcher patched.bin
    if patch_bin_file(items, blaze_data):
        print()
        print("[OK] work/patched.bin patche avec succes")
    else:
        print()
        print("[SKIP] work/patched.bin non patche")

    print()
    print("=" * 70)
    print("  Patch termine!")
    print("=" * 70)
    print()
    print("FICHIERS CREES:")
    print("  - work/BLAZE.ALL.backup (backup original)")
    print("  - work/BLAZE.ALL (patche)")
    if PATCHED_BIN_BACKUP.exists():
        print("  - work/patched.bin.backup (backup original)")
        print("  - work/patched.bin (patche)")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
