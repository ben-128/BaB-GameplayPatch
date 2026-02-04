"""
extract_blaze_from_bin.py
Extrait BLAZE.ALL depuis le BIN original (format RAW)

Le BIN est en format RAW (2352 bytes/sector)
BLAZE.ALL se trouve à LBA 185765

Usage: py -3 extract_blaze_from_bin.py
"""

from pathlib import Path
import struct

SCRIPT_DIR = Path(__file__).parent
BIN_ORIGINAL = SCRIPT_DIR.parent.parent / "Blaze and Blade - Eternal Quest (E).bin"
OUTPUT_FILE = SCRIPT_DIR / "BLAZE_ORIGINAL.ALL"

# Configuration
BLAZE_ALL_LBA = 185765
BLAZE_ALL_SIZE = 46206976  # bytes
SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048
NUM_SECTORS = BLAZE_ALL_SIZE // USER_SIZE  # 22566 sectors

def extract_blaze_all(bin_path, output_path):
    """Extrait BLAZE.ALL depuis le BIN RAW"""

    print("="*70)
    print("  Extraction de BLAZE.ALL depuis le BIN original")
    print("="*70)
    print()

    print(f"BIN source: {bin_path.name}")
    print(f"Output: {output_path.name}")
    print()

    # Vérifier le format du BIN
    bin_size = bin_path.stat().st_size
    is_raw = (bin_size % SECTOR_RAW == 0)
    is_iso = (bin_size % USER_SIZE == 0) and not is_raw

    print(f"Taille BIN: {bin_size:,} bytes")
    print(f"Format: {'RAW (2352)' if is_raw else 'ISO (2048)' if is_iso else 'INCONNU'}")

    if not is_raw and not is_iso:
        print("ERREUR: Format BIN inconnu")
        return False

    print()
    print(f"Extraction depuis LBA {BLAZE_ALL_LBA}...")
    print(f"Nombre de secteurs: {NUM_SECTORS}")

    # Extraire
    with open(bin_path, 'rb') as bin_f, open(output_path, 'wb') as out_f:
        for sector_idx in range(NUM_SECTORS):
            if sector_idx % 5000 == 0:
                print(f"  Secteur {sector_idx}/{NUM_SECTORS} ({sector_idx*100//NUM_SECTORS}%)")

            if is_raw:
                # Format RAW: sauter les headers/footers
                offset = (BLAZE_ALL_LBA + sector_idx) * SECTOR_RAW + USER_OFF
                bin_f.seek(offset)
                sector_data = bin_f.read(USER_SIZE)
            else:
                # Format ISO: données directes
                offset = (BLAZE_ALL_LBA + sector_idx) * USER_SIZE
                bin_f.seek(offset)
                sector_data = bin_f.read(USER_SIZE)

            if len(sector_data) != USER_SIZE:
                print(f"ERREUR: Lecture incomplète au secteur {sector_idx}")
                return False

            out_f.write(sector_data)

    output_size = output_path.stat().st_size
    print()
    print(f"Extraction terminée: {output_size:,} bytes")

    if output_size == BLAZE_ALL_SIZE:
        print("[OK] Taille correcte")
    else:
        print(f"[ATTENTION] Taille attendue: {BLAZE_ALL_SIZE:,} bytes")

    return True


def verify_prices(blaze_path):
    """Vérifie les prix d'enchères dans BLAZE.ALL extrait"""

    PRICE_TABLE_OFFSET = 0x002EA49A
    KNOWN_PRICES = {
        0: 10,   # Healing Potion
        2: 22,   # Shortsword
        7: 24,   # Normal Sword / Wooden Wand
        9: 26,   # Tomahawk
        11: 28,  # Dagger
        13: 36,  # Leather Armor
        15: 46,  # Leather Shield
        18: 72   # Robe
    }

    print()
    print("="*70)
    print("  Vérification des prix d'enchères")
    print("="*70)
    print()

    data = blaze_path.read_bytes()

    print(f"Offset de la table: 0x{PRICE_TABLE_OFFSET:08X}")
    print()
    print("Prix extraits:")

    all_match = True
    for idx in sorted(KNOWN_PRICES.keys()):
        offset = PRICE_TABLE_OFFSET + (idx * 2)
        if offset + 2 <= len(data):
            price = struct.unpack_from('<H', data, offset)[0]
            expected = KNOWN_PRICES[idx]
            match = "[OK]" if price == expected else "[X]"
            if price != expected:
                all_match = False
            print(f"  Word[{idx:2d}]: {price:3d} (attendu: {expected:3d}) {match}")

    print()
    if all_match:
        print("[OK] Tous les prix connus correspondent!")
    else:
        print("[X] Certains prix ne correspondent pas")

    # Afficher tous les 32 prix
    print()
    print("Table complète (32 entrées):")
    for i in range(32):
        offset = PRICE_TABLE_OFFSET + (i * 2)
        if offset + 2 <= len(data):
            price = struct.unpack_from('<H', data, offset)[0]
            known = f" (connu)" if i in KNOWN_PRICES else ""
            print(f"  Word[{i:2d}]: {price:3d}{known}")

    return all_match


def main():
    if not BIN_ORIGINAL.exists():
        print(f"ERREUR: {BIN_ORIGINAL} n'existe pas")
        return 1

    # Extraire BLAZE.ALL
    if extract_blaze_all(BIN_ORIGINAL, OUTPUT_FILE):
        # Vérifier les prix
        verify_prices(OUTPUT_FILE)

        print()
        print("="*70)
        print("  Terminé!")
        print("="*70)
        print()
        print(f"BLAZE.ALL original extrait dans: {OUTPUT_FILE}")
        print()

        return 0
    else:
        return 1


if __name__ == '__main__':
    try:
        import sys
        sys.exit(main())
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
