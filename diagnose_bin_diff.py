#!/usr/bin/env python3
"""
diagnose_bin_diff.py
Compare le BIN original avec le BIN patche (vanilla BLAZE.ALL) pour trouver
exactement quels secteurs different et pourquoi.

Usage: py -3 diagnose_bin_diff.py
"""

from pathlib import Path
import struct

SCRIPT_DIR = Path(__file__).parent

ORIG_BIN  = SCRIPT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"
PATCH_BIN = SCRIPT_DIR / "output" / "Blaze & Blade - Patched.bin"

SECTOR_RAW  = 2352
USER_OFF    = 24
USER_SIZE   = 2048

LBA_LOCATIONS = [163167, 185765]
ORIG_SECTORS  = 22566

def main():
    print("=" * 60)
    print("  BIN Diff Diagnostic")
    print("=" * 60)
    print()

    if not ORIG_BIN.exists():
        print(f"[ERROR] BIN original introuvable: {ORIG_BIN}")
        return

    if not PATCH_BIN.exists():
        print(f"[ERROR] BIN patche introuvable: {PATCH_BIN}")
        return

    orig  = ORIG_BIN.read_bytes()
    patch = PATCH_BIN.read_bytes()

    print(f"Original : {len(orig):,} bytes")
    print(f"Patche   : {len(patch):,} bytes")
    print()

    if len(orig) != len(patch):
        print(f"[WARN] Tailles differentes! orig={len(orig)} patch={len(patch)}")
    else:
        print("[OK] Tailles identiques")
    print()

    # Detect format
    is_raw = (len(orig) % SECTOR_RAW == 0)
    total_sectors = len(orig) // SECTOR_RAW if is_raw else len(orig) // USER_SIZE
    print(f"Format: {'RAW 2352' if is_raw else 'ISO 2048'}")
    print(f"Total secteurs: {total_sectors:,}")
    print()

    # Find first differing sector
    print("Recherche des secteurs differents...")
    diff_sectors = []
    max_report = 20

    userdata_diff_sectors = []

    for lba in range(total_sectors):
        if is_raw:
            off = lba * SECTOR_RAW
            o_user = orig [off + USER_OFF : off + USER_OFF + USER_SIZE]
            p_user = patch[off + USER_OFF : off + USER_OFF + USER_SIZE]
            o_ecc  = orig [off + USER_OFF + USER_SIZE : off + SECTOR_RAW]
            p_ecc  = patch[off + USER_OFF + USER_SIZE : off + SECTOR_RAW]
            ecc_only_diff = (o_user == p_user) and (o_ecc != p_ecc)
        else:
            off = lba * USER_SIZE
            o_user = orig [off : off + USER_SIZE]
            p_user = patch[off : off + USER_SIZE]
            ecc_only_diff = False

        if o_user != p_user:
            diff_sectors.append(lba)
            userdata_diff_sectors.append(lba)
            if len(diff_sectors) <= max_report:
                region = "HORS BLAZE.ALL"
                for lba_start in LBA_LOCATIONS:
                    if lba_start <= lba < lba_start + ORIG_SECTORS:
                        blaze_sector = lba - lba_start
                        blaze_offset = blaze_sector * USER_SIZE
                        region = f"BLAZE.ALL copie@{lba_start} secteur {blaze_sector} (offset 0x{blaze_offset:X})"
                        break
                first_byte = next((i for i in range(len(o_user)) if o_user[i] != p_user[i]), -1)
                print(f"  LBA {lba:6d} | {region}")
                if first_byte >= 0:
                    print(f"             -> 1er octet USER DATA different: +0x{first_byte:04X} "
                          f"orig=0x{o_user[first_byte]:02X} patch=0x{p_user[first_byte]:02X}")

    print()
    print(f"Total secteurs USER DATA differents: {len(diff_sectors)}")

    if diff_sectors:
        print()
        print("Plages continues:")
        start = diff_sectors[0]
        prev  = diff_sectors[0]
        for lba in diff_sectors[1:]:
            if lba != prev + 1:
                print(f"  LBA {start} - {prev}  ({prev - start + 1} secteurs)")
                start = lba
            prev = lba
        print(f"  LBA {start} - {prev}  ({prev - start + 1} secteurs)")

        print()
        print("Verification vs LBAs attendus:")
        for lba_start in LBA_LOCATIONS:
            lba_end = lba_start + ORIG_SECTORS - 1
            overlap = [l for l in diff_sectors if lba_start <= l <= lba_end]
            outside = [l for l in diff_sectors if l < lba_start or l > lba_end]
            print(f"  Copie @LBA {lba_start}: {len(overlap)} secteurs diff dans la plage")
        outside_all = [l for l in diff_sectors
                       if all(not (s <= l < s + ORIG_SECTORS) for s in LBA_LOCATIONS)]
        if outside_all:
            print(f"  [!!] {len(outside_all)} secteurs differents HORS des plages BLAZE.ALL!")
            print(f"       Premiers: {outside_all[:5]}")
    else:
        print("[OK] BINs identiques - le probleme est ailleurs (emulateur, save, etc.)")


if __name__ == '__main__':
    main()
