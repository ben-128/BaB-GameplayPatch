#!/usr/bin/env python3
"""
Patch BIN with Test SLES - Remplace SLES_008.45 dans l'image BIN
"""

import os
import shutil

BIN_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin"
SLES_TEST = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45_TEST_BYTE0"

def find_sles_in_bin(bin_path):
    """Trouve l'offset du SLES_008.45 dans le BIN"""
    print("Recherche de SLES_008.45 dans le BIN...")

    with open(bin_path, 'rb') as f:
        data = f.read()

    # Chercher la signature PS-X EXE
    signature = b'PS-X EXE'
    offset = data.find(signature)

    if offset == -1:
        print("ERREUR: Signature PS-X EXE non trouvee!")
        return None

    print(f"[OK] SLES_008.45 trouve a l'offset: 0x{offset:08X} ({offset})")
    return offset

def patch_bin(bin_path, sles_test_path, sles_offset):
    """Remplace SLES_008.45 dans le BIN par la version de test"""

    # Backup
    backup_path = bin_path + ".backup"
    if not os.path.exists(backup_path):
        print(f"Creation du backup: {os.path.basename(backup_path)}")
        shutil.copy2(bin_path, backup_path)
        print("[OK] Backup cree")
    else:
        print(f"[INFO] Backup existe deja")

    print()

    # Lire le BIN
    with open(bin_path, 'rb') as f:
        bin_data = bytearray(f.read())

    # Lire le SLES de test
    with open(sles_test_path, 'rb') as f:
        sles_data = f.read()

    sles_size = len(sles_data)

    print(f"Taille SLES: {sles_size:,} bytes ({sles_size/1024:.1f} KB)")
    print(f"Taille BIN:  {len(bin_data):,} bytes ({len(bin_data)/1024/1024:.1f} MB)")
    print()

    # Vérifier qu'on ne dépasse pas
    if sles_offset + sles_size > len(bin_data):
        print("ERREUR: SLES trop grand pour le BIN!")
        return False

    # Remplacer
    print(f"Remplacement de {sles_size} bytes a l'offset 0x{sles_offset:08X}...")
    bin_data[sles_offset:sles_offset + sles_size] = sles_data

    # Écrire
    with open(bin_path, 'wb') as f:
        f.write(bin_data)

    print("[OK] BIN patche avec succes!")
    print()

    return True

def main():
    print("="*80)
    print("PATCH BIN AVEC SLES_008.45_TEST_BYTE0")
    print("="*80)
    print()

    if not os.path.exists(BIN_PATH):
        print(f"ERREUR: {BIN_PATH} non trouve!")
        return

    if not os.path.exists(SLES_TEST):
        print(f"ERREUR: {SLES_TEST} non trouve!")
        return

    print(f"BIN:  {os.path.basename(BIN_PATH)}")
    print(f"SLES: {os.path.basename(SLES_TEST)}")
    print()

    # Trouver l'offset
    offset = find_sles_in_bin(BIN_PATH)
    if offset is None:
        return

    print()

    # Patcher
    if patch_bin(BIN_PATH, SLES_TEST, offset):
        print("="*80)
        print("SUCCES!")
        print("="*80)
        print()
        print("Le fichier BIN a ete patche avec TEST_BYTE0")
        print()
        print("Prochaines etapes:")
        print("  1. Graver/monter le BIN patche")
        print("  2. Lancer le jeu")
        print("  3. Creer N'IMPORTE QUELLE classe")
        print("  4. Monter au niveau 2")
        print("  5. Noter quelle stat EXPLOSE (+255)")
        print()
        print("Pour restaurer:")
        print(f"  Copier '{os.path.basename(BIN_PATH)}.backup'")
        print(f"  vers  '{os.path.basename(BIN_PATH)}'")
        print()

if __name__ == "__main__":
    main()
