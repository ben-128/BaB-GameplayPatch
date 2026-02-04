"""
patch_items.py
Patch les descriptions d'items dans BLAZE.ALL et le .bin

Structure des items dans BLAZE.ALL:
- 128 bytes (0x80) par entrée
- +0x00: Nom (max ~32 bytes, null-terminated)
- +0x40: Séparateur 0x0C
- +0x41: Description (jusqu'à la fin, null-terminated)

Usage: py -3 patch_items.py
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

# Fichier .bin (à déterminer)
BIN_DIR = SCRIPT_DIR.parent.parent
BIN_FILE = BIN_DIR / "Blaze and Blade - Eternal Quest (E).bin"
BIN_BACKUP = BIN_DIR / "Blaze and Blade - Eternal Quest (E).bin.backup"

# Offset de BLAZE.ALL dans le .bin (à déterminer par analyse)
# Pour un jeu PSX, BLAZE.ALL est généralement dans le filesystem
# On va d'abord patcher BLAZE.ALL, puis on pourra injecter dans le .bin
BLAZE_IN_BIN_OFFSET = None  # À déterminer


def patch_item_description(data, offset, new_description, max_length=63):
    """Patch la description d'un item dans les données binaires"""
    # La description commence à offset + 0x41
    desc_offset = offset + 0x41

    # Vérifier que l'offset est valide
    if desc_offset < 0 or desc_offset >= len(data):
        return False

    # Encoder la description en ASCII
    desc_bytes = new_description.encode('ascii', errors='ignore')

    # Tronquer si nécessaire
    if len(desc_bytes) > max_length:
        desc_bytes = desc_bytes[:max_length]

    # Écrire la description + null byte
    end_offset = desc_offset + len(desc_bytes)
    if end_offset >= len(data):
        return False

    # Écrire les bytes
    data[desc_offset:end_offset] = desc_bytes

    # Ajouter null byte si on a de la place
    if end_offset < len(data):
        data[end_offset] = 0

    # Remplir le reste avec des null bytes jusqu'à la fin de l'entrée (128 bytes)
    entry_end = offset + 128
    if end_offset + 1 < entry_end and entry_end <= len(data):
        for i in range(end_offset + 1, entry_end):
            data[i] = 0

    return True


def main():
    print("=" * 70)
    print("  Patch des descriptions d'items")
    print("=" * 70)
    print()

    # Charger les items
    print(f"Chargement de {ITEMS_JSON}...")
    with open(ITEMS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data['items']
    print(f"  {len(items)} items chargés")

    # Vérifier que BLAZE.ALL existe
    if not BLAZE_ALL.exists():
        print(f"\nERREUR: {BLAZE_ALL} n'existe pas!")
        return

    print(f"\nChargement de {BLAZE_ALL}...")
    blaze_data = bytearray(BLAZE_ALL.read_bytes())
    print(f"  {len(blaze_data):,} bytes")

    # Créer backup
    if not BLAZE_ALL_BACKUP.exists():
        print(f"\nCréation du backup: {BLAZE_ALL_BACKUP.name}...")
        shutil.copy2(BLAZE_ALL, BLAZE_ALL_BACKUP)
        print("  Backup créé")
    else:
        print(f"\nBackup existe déjà: {BLAZE_ALL_BACKUP.name}")

    # Patcher chaque item
    print("\nPatch des items...")
    print("-" * 70)

    patched_count = 0
    failed_count = 0

    for i, item in enumerate(items):
        offset = item.get('offset_decimal', 0)
        new_desc = item.get('new_description', '')
        name = item.get('name', f'Item_{i}')

        if offset <= 0 or not new_desc:
            continue

        # Patcher
        success = patch_item_description(blaze_data, offset, new_desc)

        if success:
            patched_count += 1
            if patched_count <= 10:  # Afficher les 10 premiers
                print(f"  [{patched_count:3}] {name:30} @ 0x{offset:08X}")
        else:
            failed_count += 1
            print(f"  [FAIL] {name} @ 0x{offset:08X}")

    if patched_count > 10:
        print(f"  ... et {patched_count - 10} autres")

    print()
    print(f"Résultat:")
    print(f"  Items patchés: {patched_count}")
    print(f"  Échecs: {failed_count}")

    # Sauvegarder BLAZE.ALL patché
    print(f"\nSauvegarde de {BLAZE_ALL}...")
    BLAZE_ALL.write_bytes(blaze_data)
    print("  Sauvegardé")

    # Optionnel: patcher le .bin si trouvé
    if BIN_FILE.exists():
        print(f"\n.bin trouvé: {BIN_FILE.name}")
        print("Pour patcher le .bin, il faut:")
        print("  1. Extraire BLAZE.ALL du .bin avec mkpsxiso ou CDMage")
        print("  2. Patcher BLAZE.ALL (fait)")
        print("  3. Réinjecter BLAZE.ALL dans le .bin")
        print("\nUtilisez mkpsxiso pour reconstruire le .bin avec le BLAZE.ALL patché")
    else:
        print(f"\n.bin non trouvé: {BIN_FILE}")

    print()
    print("=" * 70)
    print("  Patch terminé!")
    print("=" * 70)
    print()
    print("IMPORTANT:")
    print("  - Le fichier work/BLAZE.ALL a été patché")
    print("  - Un backup a été créé: work/BLAZE.ALL.backup")
    print("  - Pour appliquer au jeu, utilisez mkpsxiso pour rebuilder le .bin")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
