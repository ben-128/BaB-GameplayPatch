"""
debug_price_extraction.py
Debug l'extraction des prix pour comprendre le format correct
"""

import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BIN_ORIGINAL = SCRIPT_DIR.parent.parent / "Blaze and Blade - Eternal Quest (E).bin"
BLAZE_ALL_LBA = 185765
SECTOR_SIZE = 2048
PRICE_TABLE_OFFSET_IN_BLAZE = 0x002EA49A

# Prix connus selon auction_prices/README.md
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

def hex_dump(data, offset, length=64):
    """Affiche un hex dump des données"""
    print(f"\nHex dump @ 0x{offset:08X}:")
    for i in range(0, length, 16):
        hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {offset+i:08X}: {hex_str:48s} {ascii_str}")

def extract_and_test(bin_path):
    """Extrait et teste différents formats de prix"""

    print("="*70)
    print("  DEBUG - Extraction des prix")
    print("="*70)

    # Calculer l'offset dans le BIN
    offset_in_bin = (BLAZE_ALL_LBA * SECTOR_SIZE) + PRICE_TABLE_OFFSET_IN_BLAZE

    print(f"\nFichier: {bin_path.name}")
    print(f"Offset calculé: 0x{offset_in_bin:08X} ({offset_in_bin:,} bytes)")
    print(f"  = LBA {BLAZE_ALL_LBA} * {SECTOR_SIZE} + 0x{PRICE_TABLE_OFFSET_IN_BLAZE:08X}")

    with open(bin_path, 'rb') as f:
        f.seek(offset_in_bin)
        raw_data = f.read(64)  # 32 words = 64 bytes

    # Afficher le hex dump
    hex_dump(raw_data, offset_in_bin)

    # Tester différents formats
    print("\n" + "="*70)
    print("  Test 1: 16-bit little-endian (format supposé)")
    print("="*70)

    for idx in [0, 2, 7, 9, 11, 13, 15, 18]:
        offset = idx * 2
        if offset + 2 <= len(raw_data):
            value = struct.unpack_from('<H', raw_data, offset)[0]
            expected = KNOWN_PRICES.get(idx, "?")
            match = "[OK]" if value == expected else "[X]"
            print(f"  Word[{idx:2d}] @ +{offset:2d}: {value:5d} (attendu: {expected:3}) {match}")

    print("\n" + "="*70)
    print("  Test 2: 8-bit values (chaque byte = prix)")
    print("="*70)

    for idx in [0, 2, 7, 9, 11, 13, 15, 18]:
        if idx < len(raw_data):
            value = raw_data[idx]
            expected = KNOWN_PRICES.get(idx, "?")
            match = "[OK]" if value == expected else "[X]"
            print(f"  Byte[{idx:2d}]: {value:3d} (attendu: {expected:3}) {match}")

    # Chercher les valeurs connues dans les données
    print("\n" + "="*70)
    print("  Recherche des valeurs connues dans les 64 bytes")
    print("="*70)

    for price in sorted(set(KNOWN_PRICES.values())):
        # Chercher comme byte
        if price < 256:
            positions = [i for i, b in enumerate(raw_data) if b == price]
            if positions:
                print(f"  Prix {price:2d} trouvé comme byte aux positions: {positions}")

        # Chercher comme word little-endian
        price_bytes = struct.pack('<H', price)
        pos = 0
        word_positions = []
        while pos < len(raw_data) - 1:
            if raw_data[pos:pos+2] == price_bytes:
                word_positions.append(pos)
            pos += 1
        if word_positions:
            print(f"  Prix {price:2d} trouvé comme word LE aux offsets: {word_positions}")

    # Essayer de trouver automatiquement le bon offset
    print("\n" + "="*70)
    print("  Recherche du bon offset dans une zone élargie")
    print("="*70)

    with open(bin_path, 'rb') as f:
        # Chercher dans ±4KB autour de l'offset supposé
        search_start = max(0, offset_in_bin - 2048)
        f.seek(search_start)
        search_data = f.read(8192)

    best_match_score = 0
    best_match_offset = None

    # Tester tous les offsets alignés sur 2 bytes
    for test_offset in range(0, len(search_data) - 64, 2):
        score = 0
        for idx, expected_price in KNOWN_PRICES.items():
            data_offset = idx * 2
            if data_offset + 2 <= 64:
                try:
                    value = struct.unpack_from('<H', search_data, test_offset + data_offset)[0]
                    if value == expected_price:
                        score += 1
                except:
                    pass

        if score > best_match_score:
            best_match_score = score
            best_match_offset = search_start + test_offset

    if best_match_score > 0:
        print(f"\n  Meilleur match: {best_match_score}/8 prix corrects")
        print(f"  Offset trouvé: 0x{best_match_offset:08X}")
        print(f"  Différence: {best_match_offset - offset_in_bin:+d} bytes vs calculé")

        # Afficher les valeurs à cet offset
        with open(bin_path, 'rb') as f:
            f.seek(best_match_offset)
            correct_data = f.read(64)

        print("\n  Valeurs aux indices connus:")
        for idx in sorted(KNOWN_PRICES.keys()):
            offset = idx * 2
            if offset + 2 <= len(correct_data):
                value = struct.unpack_from('<H', correct_data, offset)[0]
                expected = KNOWN_PRICES[idx]
                match = "[OK]" if value == expected else "[X]"
                print(f"    Word[{idx:2d}]: {value:3d} (attendu: {expected:3d}) {match}")

        # Afficher tous les 32 prix à ce bon offset
        if best_match_score >= 5:  # Si au moins 5 prix correspondent
            print("\n  TABLE COMPLÈTE aux 32 indices:")
            for i in range(32):
                offset = i * 2
                if offset + 2 <= len(correct_data):
                    value = struct.unpack_from('<H', correct_data, offset)[0]
                    known = f" ({KNOWN_PRICES[i]})" if i in KNOWN_PRICES else ""
                    print(f"    Word[{i:2d}]: {value:3d}{known}")
    else:
        print("\n  Aucun match trouvé dans la zone de recherche")

if __name__ == '__main__':
    try:
        extract_and_test(BIN_ORIGINAL)
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
