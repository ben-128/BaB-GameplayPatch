#!/usr/bin/env python3
"""
Find SLES LBA - Trouve le LBA du SLES_008.45 dans le BIN
"""

BIN_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin"

SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048

print("Recherche du LBA de SLES_008.45...")
print()

with open(BIN_PATH, 'rb') as f:
    data = f.read()

# Chercher PS-X EXE
sig = b'PS-X EXE'
offset = data.find(sig)

if offset == -1:
    print("ERREUR: PS-X EXE non trouve!")
    exit(1)

print(f"PS-X EXE trouve a l'offset: 0x{offset:08X} ({offset:,})")
print()

# Vérifier le format du BIN
bin_size = len(data)
is_raw = (bin_size % SECTOR_RAW == 0)

print(f"Taille BIN: {bin_size:,} bytes")
print(f"Format: {'RAW (2352)' if is_raw else 'ISO (2048)'}")
print()

if is_raw:
    # Le SLES devrait commencer à l'offset 24 d'un secteur
    # Donc: offset = LBA * 2352 + 24

    # Vérifier si l'offset est aligné
    if (offset - USER_OFF) % SECTOR_RAW == 0:
        lba = (offset - USER_OFF) // SECTOR_RAW
        print(f"[OK] SLES_008.45 est aligne sur un secteur")
        print(f"LBA: {lba}")
        print()
        print("Calcul:")
        print(f"  offset = {offset}")
        print(f"  LBA = (offset - {USER_OFF}) / {SECTOR_RAW}")
        print(f"  LBA = ({offset} - {USER_OFF}) / {SECTOR_RAW}")
        print(f"  LBA = {lba}")
    else:
        # Pas aligné, trouver le secteur qui contient cet offset
        sector_num = offset // SECTOR_RAW
        offset_in_sector = offset % SECTOR_RAW

        print(f"[WARNING] SLES_008.45 n'est PAS aligne sur un secteur")
        print(f"Secteur: {sector_num}")
        print(f"Offset dans le secteur: {offset_in_sector}")
        print()

        # Si offset_in_sector == 24, alors c'est le début des données utilisateur
        if offset_in_sector == USER_OFF:
            lba = sector_num
            print(f"[OK] C'est le debut des donnees utilisateur")
            print(f"LBA: {lba}")
        else:
            print(f"[ERROR] Position inattendue dans le secteur!")
            print(f"Attendu: {USER_OFF}, Trouve: {offset_in_sector}")
else:
    # Format ISO (2048)
    lba = offset // USER_SIZE
    print(f"LBA: {lba}")
    print(f"  offset = {offset}")
    print(f"  LBA = offset / {USER_SIZE}")
    print(f"  LBA = {offset} / {USER_SIZE}")
    print(f"  LBA = {lba}")

print()
print("="*80)
print(f"Utiliser ce LBA dans le script de patch: LBA_SLES = {lba}")
print("="*80)
