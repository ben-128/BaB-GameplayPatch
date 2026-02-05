"""
patch_items_in_bin.py
Patch les descriptions d'items directement dans BLAZE.ALL

Usage: py -3 patch_items_in_bin.py
"""

import json
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ITEMS_JSON = SCRIPT_DIR / "all_items_clean.json"
OUTPUT_DIR = SCRIPT_DIR.parent.parent / "output"
BLAZE_ALL = OUTPUT_DIR / "BLAZE.ALL"

ITEM_ENTRY_SIZE = 128


def detect_offset_type(data, offset, item_name):
    """Detecte le type de stockage a cet offset

    Returns:
        - "item_entry": Item entry with name at +0x00, desc at +0x41
        - "direct_text": "Name/Description" directly at offset
        - None: Invalid offset
    """
    if offset < 0 or offset >= len(data):
        return None

    # Check if "Name/" starts directly at offset (format 3)
    name_prefix = f"{item_name}/".encode('ascii')
    if data[offset:offset + len(name_prefix)] == name_prefix:
        return "direct_text"

    # Check if item name is at offset+0x00 (format 1 or 2)
    name_data = data[offset:offset + 32]
    null_pos = name_data.find(b'\x00')
    if null_pos > 0:
        try:
            found_name = name_data[:null_pos].decode('ascii', errors='ignore')
            if found_name == item_name:
                return "item_entry"
        except:
            pass

    return None


def detect_description_format(data, offset, item_name):
    """Detecte si la description utilise le format 'Name/Desc' ou juste 'Desc'
    (pour les item_entry seulement)
    """
    desc_offset = offset + 0x41
    if desc_offset >= len(data):
        return "desc_only"

    # Lire la description existante
    desc_data = data[desc_offset:desc_offset + 64]
    null_pos = desc_data.find(b'\x00')
    if null_pos > 0:
        try:
            existing = desc_data[:null_pos].decode('ascii', errors='ignore')
            # Check if it starts with "ItemName/"
            if existing.startswith(f"{item_name}/"):
                return "name_prefix"  # Format: "Name/Description"
            else:
                return "desc_only"    # Format: "Description"
        except:
            pass
    return "desc_only"  # Default to description only


def patch_item_description(data, offset, item_name, new_description, offset_type, max_length=63):
    """Patch la description d'un item dans les données binaires

    Three formats exist in BLAZE.ALL:
    - item_entry (aligned): "ItemName/Description" at offset+0x41
    - item_entry (unaligned): "Description" only at offset+0x41
    - direct_text: "ItemName/Description" directly at offset
    """
    if offset_type == "direct_text":
        # Format 3: "Name/Description" directly at offset
        desc_offset = offset
        full_desc = f"{item_name}/{new_description}"
    else:
        # Format 1 & 2: item_entry, description at offset+0x41
        desc_offset = offset + 0x41

        if desc_offset >= len(data):
            return False

        # Detect if it uses "Name/Desc" or just "Desc" format
        format_type = detect_description_format(data, offset, item_name)

        if format_type == "name_prefix":
            full_desc = f"{item_name}/{new_description}"
        else:
            full_desc = new_description

    desc_bytes = full_desc.encode('ascii', errors='ignore')

    if len(desc_bytes) > max_length:
        desc_bytes = desc_bytes[:max_length]

    end_offset = desc_offset + len(desc_bytes)
    if end_offset >= len(data):
        return False

    # Write the description
    data[desc_offset:end_offset] = desc_bytes

    # Add null terminator
    if end_offset < len(data):
        data[end_offset] = 0

    # Zero-fill remaining space (up to 63 chars from desc_offset)
    max_end = desc_offset + max_length
    if max_end <= len(data):
        for i in range(end_offset + 1, max_end):
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
    """Patch output/BLAZE.ALL"""
    print("=" * 70)
    print("  Patch de output/BLAZE.ALL")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERREUR: {BLAZE_ALL} n'existe pas!")
        return None

    print(f"Chargement de {BLAZE_ALL.name}...")
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  {len(blaze_data):,} bytes")

    # Patcher
    print("\nPatch des items...")
    patched_items = 0
    patched_occurrences = 0

    for item in items:
        new_desc = item.get('new_description', '')
        item_name = item.get('name', '')
        if not new_desc or not item_name:
            continue

        # Patcher TOUTES les occurrences valides de cet item
        all_offsets = item.get('all_offsets', [])
        if not all_offsets:
            # Fallback sur offset_decimal si all_offsets n'existe pas
            offset = item.get('offset_decimal', 0)
            if offset > 0:
                all_offsets = [f"0x{offset:08X}"]

        item_patched = False
        for offset_hex in all_offsets:
            try:
                offset = int(offset_hex, 16)
                if offset > 0:
                    # Detect what type of data is at this offset
                    offset_type = detect_offset_type(blaze_data, offset, item_name)
                    if offset_type is None:
                        continue
                    if patch_item_description(blaze_data, offset, item_name, new_desc, offset_type):
                        patched_occurrences += 1
                        item_patched = True
            except (ValueError, TypeError):
                continue

        if item_patched:
            patched_items += 1

    print(f"  Items patches: {patched_items}")
    print(f"  Occurrences patchees: {patched_occurrences}")

    # Sauvegarder
    print(f"\nSauvegarde de {BLAZE_ALL.name}...")
    BLAZE_ALL.write_bytes(blaze_data)

    return blaze_data


def patch_bin_file(items, blaze_data):
    """Patch output/patched.bin"""
    print()
    print("=" * 70)
    print("  Patch de output/patched.bin")
    print("=" * 70)
    print()

    if not PATCHED_BIN.exists():
        print(f"ERREUR: {PATCHED_BIN} n'existe pas!")
        print("Veuillez d'abord creer output/patched.bin")
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
    print("  Patch Items - BLAZE.ALL")
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
    print("[OK] output/BLAZE.ALL patche avec succes")

    print()
    print("=" * 70)
    print("  Patch termine!")
    print("=" * 70)
    print()
    print("FICHIERS MODIFIES:")
    print("  - output/BLAZE.ALL (patche)")

    # Ligne parsable pour le batch script
    items_with_desc = sum(1 for item in items if item.get('new_description'))
    print(f"PATCHED_COUNT={items_with_desc}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
