#!/usr/bin/env python3
"""
extract_blaze_from_bin.py
Extrait le vrai BLAZE.ALL vanilla depuis le BIN original.
Remplace l'extract/BLAZE.ALL existant.

Usage: py -3 extract_blaze_from_bin.py
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

ORIG_BIN  = SCRIPT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"
OUT_BLAZE = SCRIPT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"

LBA_START    = 185765   # Vrai LBA de BLAZE.ALL (verifie via ISO 9660)
ORIG_SECTORS = 22562    # Taille reelle (46206976 / 2048, depuis filesystem)
SECTOR_RAW   = 2352
USER_OFF      = 24
USER_SIZE     = 2048

def main():
    print("=" * 50)
    print("  BLAZE.ALL Extractor (depuis BIN original)")
    print("=" * 50)
    print()

    if not ORIG_BIN.exists():
        print(f"[ERROR] BIN original introuvable: {ORIG_BIN}")
        return 1

    print(f"Lecture de {ORIG_BIN}...")
    data = ORIG_BIN.read_bytes()
    print(f"  Taille: {len(data):,} bytes")

    is_raw = (len(data) % SECTOR_RAW == 0)
    print(f"  Format: {'RAW 2352' if is_raw else 'ISO 2048'}")
    print()

    print(f"Extraction LBA {LBA_START} -> {LBA_START + ORIG_SECTORS - 1} ({ORIG_SECTORS} secteurs)...")
    blaze = bytearray()

    for i in range(ORIG_SECTORS):
        lba = LBA_START + i
        if is_raw:
            off = lba * SECTOR_RAW + USER_OFF
        else:
            off = lba * USER_SIZE
        blaze.extend(data[off : off + USER_SIZE])

    print(f"  Extrait: {len(blaze):,} bytes ({len(blaze) // USER_SIZE} secteurs)")

    # Backup si existant
    if OUT_BLAZE.exists():
        backup = OUT_BLAZE.with_suffix('.ALL.bak')
        backup.write_bytes(OUT_BLAZE.read_bytes())
        print(f"  Backup: {backup.name}")

    OUT_BLAZE.write_bytes(blaze)
    print(f"[OK] {OUT_BLAZE}")
    print()
    print("BLAZE.ALL vanilla extrait. Lance le build pour tester.")
    return 0

if __name__ == '__main__':
    exit(main())
