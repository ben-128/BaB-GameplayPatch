#!/usr/bin/env python3
"""
Patch SLES Test into BIN - Injecte SLES_008.45_TEST_BYTEN dans le BIN
Utilise la même méthode que patch_blaze_all.py
"""

from pathlib import Path
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent
BIN_FILE = SCRIPT_DIR.parent / "work" / "Blaze & Blade - Patched.bin"

# SLES locations
LBA_SLES = 295081  # LBA où SLES_008.45 commence
SECTOR_RAW = 2352  # RAW sector size
USER_OFF = 24      # MODE2/Form1 user data offset
USER_SIZE = 2048   # User data per sector

# SLES size in sectors (843776 bytes / 2048 = 412 sectors)
SLES_SECTORS = 412

def patch_sles_test(test_byte_num):
    """Injecte SLES_008.45_TEST_BYTEN dans le BIN"""

    sles_test_file = SCRIPT_DIR.parent.parent / f"SLES_008.45_TEST_BYTE{test_byte_num}"

    if not sles_test_file.exists():
        print(f"ERREUR: {sles_test_file.name} non trouve!")
        return False

    print("=" * 70)
    print(f"  SLES Test Patcher - TEST_BYTE{test_byte_num}")
    print("=" * 70)
    print()

    # Read test SLES
    print(f"Lecture de {sles_test_file.name}...")
    sles_data = sles_test_file.read_bytes()
    print(f"  Taille: {len(sles_data):,} bytes")

    if len(sles_data) % USER_SIZE != 0:
        print(f"ERREUR: Taille SLES ({len(sles_data)}) pas multiple de {USER_SIZE}")
        return False

    n_sectors = len(sles_data) // USER_SIZE
    print(f"  Secteurs: {n_sectors}")

    if n_sectors != SLES_SECTORS:
        print(f"WARNING: Nombre de secteurs different de l'attendu ({SLES_SECTORS})")

    # Read BIN
    print()
    print(f"Lecture de {BIN_FILE.name}...")
    bin_data = bytearray(BIN_FILE.read_bytes())
    bin_size = len(bin_data)
    print(f"  Taille: {bin_size:,} bytes")

    # Verify RAW format
    if bin_size % SECTOR_RAW != 0:
        print("ERREUR: BIN n'est pas au format RAW (2352)")
        return False

    print(f"  Format: RAW (2352)")
    print()

    # Create backup
    backup_file = BIN_FILE.with_suffix('.bin.sles_backup')
    if not backup_file.exists():
        print(f"Creation du backup...")
        backup_file.write_bytes(bin_data)
        print(f"  [OK] {backup_file.name}")
    else:
        print(f"  [INFO] Backup existe deja: {backup_file.name}")

    print()
    print(f"Injection du SLES au LBA {LBA_SLES}...")

    # Inject SLES sector by sector
    for i in range(SLES_SECTORS):
        # Source data from SLES file
        src = i * USER_SIZE
        chunk = sles_data[src:src+USER_SIZE] if src < len(sles_data) else b'\x00' * USER_SIZE

        if len(chunk) < USER_SIZE:
            chunk = chunk + b'\x00' * (USER_SIZE - len(chunk))

        # Destination in BIN (RAW format)
        dst = (LBA_SLES + i) * SECTOR_RAW + USER_OFF

        if dst + USER_SIZE > bin_size:
            print(f"ERREUR: Ecriture depasserait le fichier au secteur {i}")
            return False

        # Patch
        bin_data[dst:dst+USER_SIZE] = chunk

    # Write patched BIN
    print()
    print(f"Ecriture de {BIN_FILE.name}...")
    BIN_FILE.write_bytes(bin_data)

    print()
    print("=" * 70)
    print("  Patch complete!")
    print("=" * 70)
    print()
    print(f"Le BIN a ete patche avec TEST_BYTE{test_byte_num}")
    print()
    print("Test in-game:")
    print("  1. Monter/graver le BIN")
    print("  2. Creer n'importe quelle classe")
    print("  3. Monter au niveau 2")
    print(f"  4. Noter quelle stat explose (byte[{test_byte_num}] = 255)")
    print()
    print("Pour restaurer:")
    print(f"  Copier {backup_file.name} vers {BIN_FILE.name}")
    print()

    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: py -3 patch_sles_test.py <byte_num>")
        print()
        print("Exemple: py -3 patch_sles_test.py 0")
        print("         (injecte SLES_008.45_TEST_BYTE0)")
        print()
        return

    try:
        byte_num = int(sys.argv[1])
        if byte_num < 0 or byte_num > 7:
            print("ERREUR: byte_num doit etre entre 0 et 7")
            return

        patch_sles_test(byte_num)

    except ValueError:
        print("ERREUR: Argument invalide (doit etre un nombre 0-7)")

if __name__ == '__main__':
    main()
