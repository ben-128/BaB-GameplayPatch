#!/usr/bin/env python3
"""
find_blaze_lba.py
Parse le filesystem ISO 9660 du BIN pour trouver le vrai LBA et la vraie
taille de BLAZE.ALL dans le disque original.

Usage: py -3 find_blaze_lba.py
"""

from pathlib import Path
import struct

SCRIPT_DIR = Path(__file__).parent
ORIG_BIN = SCRIPT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"

SECTOR_RAW = 2352
USER_OFF   = 24
USER_SIZE  = 2048


def read_sector(data, lba, is_raw):
    if is_raw:
        off = lba * SECTOR_RAW + USER_OFF
    else:
        off = lba * USER_SIZE
    return data[off : off + USER_SIZE]


def parse_dir_record(sector_data, offset):
    """Parse un directory record ISO 9660 a l'offset donne."""
    length = sector_data[offset]
    if length == 0:
        return None, 0
    ea_length     = sector_data[offset + 1]
    lba           = struct.unpack_from('<I', sector_data, offset + 2)[0]
    size          = struct.unpack_from('<I', sector_data, offset + 10)[0]
    flags         = sector_data[offset + 25]
    name_len      = sector_data[offset + 32]
    name_raw      = sector_data[offset + 33 : offset + 33 + name_len]
    try:
        name = name_raw.decode('ascii', errors='replace').rstrip(';').rstrip('\x00').rstrip('\x01')
    except Exception:
        name = repr(name_raw)
    return {
        'lba': lba, 'size': size, 'flags': flags,
        'name': name, 'is_dir': bool(flags & 0x02)
    }, length


def scan_directory(data, dir_lba, dir_size, is_raw, depth=0, path=""):
    """Scan recursivement un repertoire ISO 9660."""
    results = []
    sectors_needed = (dir_size + USER_SIZE - 1) // USER_SIZE

    for s in range(sectors_needed):
        sector = read_sector(data, dir_lba + s, is_raw)
        offset = 0
        while offset < USER_SIZE:
            rec, length = parse_dir_record(sector, offset)
            if rec is None or length == 0:
                break
            name = rec['name']
            full_path = path + "/" + name if path else name
            if name not in ('', '\x00', '\x01'):
                results.append((full_path, rec))
                if rec['is_dir'] and depth < 4 and rec['lba'] != dir_lba:
                    sub = scan_directory(data, rec['lba'], rec['size'], is_raw, depth+1, full_path)
                    results.extend(sub)
            offset += length

    return results


def main():
    print("=" * 60)
    print("  ISO 9660 BLAZE.ALL Finder")
    print("=" * 60)
    print()

    if not ORIG_BIN.exists():
        print(f"[ERROR] {ORIG_BIN}")
        return 1

    data = ORIG_BIN.read_bytes()
    is_raw = (len(data) % SECTOR_RAW == 0)
    total = len(data) // (SECTOR_RAW if is_raw else USER_SIZE)
    print(f"Format: {'RAW 2352' if is_raw else 'ISO 2048'} | {total} secteurs")
    print()

    # Primary Volume Descriptor at LBA 16
    pvd = read_sector(data, 16, is_raw)
    if pvd[0] != 1 or pvd[1:6] != b'CD001':
        print("[ERROR] PVD introuvable au LBA 16")
        return 1

    root_lba  = struct.unpack_from('<I', pvd, 156 + 2)[0]
    root_size = struct.unpack_from('<I', pvd, 156 + 10)[0]
    print(f"Root dir: LBA {root_lba}, size {root_size}")
    print()

    print("Scan du filesystem...")
    entries = scan_directory(data, root_lba, root_size, is_raw)

    # Chercher BLAZE.ALL
    print()
    print("Fichiers trouves:")
    for path, rec in entries:
        upper = path.upper()
        if 'BLAZE' in upper or 'ALL' in upper:
            sectors = (rec['size'] + USER_SIZE - 1) // USER_SIZE
            print(f"  *** {path}")
            print(f"      LBA={rec['lba']}  size={rec['size']:,} bytes  ({sectors} secteurs)")
        # Aussi afficher tous les gros fichiers
        elif rec['size'] > 1_000_000 and not rec['is_dir']:
            sectors = (rec['size'] + USER_SIZE - 1) // USER_SIZE
            print(f"  {path}: LBA={rec['lba']} size={rec['size']:,} bytes ({sectors} secteurs)")

    # Tous les fichiers pour reference
    print()
    print("Tous les fichiers (taille > 100KB):")
    for path, rec in sorted(entries, key=lambda x: x[1]['lba']):
        if not rec['is_dir'] and rec['size'] > 100_000:
            sectors = (rec['size'] + USER_SIZE - 1) // USER_SIZE
            print(f"  LBA {rec['lba']:6d} | {rec['size']:12,} bytes ({sectors:6d} secteurs) | {path}")

    return 0


if __name__ == '__main__':
    exit(main())
