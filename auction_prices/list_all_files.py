#!/usr/bin/env python3
"""
List all files on the PS1 disc to see what data files exist
"""

from pathlib import Path
import struct

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")

SECTOR_SIZE = 2352
DATA_OFFSET = 24
DATA_SIZE = 2048

def read_sector(f, lba):
    """Read a sector's data from RAW BIN"""
    f.seek(lba * SECTOR_SIZE + DATA_OFFSET)
    return f.read(DATA_SIZE)

def parse_directory_record(data, offset):
    """Parse ISO9660 directory record"""
    if offset >= len(data) or data[offset] == 0:
        return None

    record_len = data[offset]
    if record_len == 0:
        return None

    extent_lba = struct.unpack('<I', data[offset+2:offset+6])[0]
    data_len = struct.unpack('<I', data[offset+10:offset+14])[0]
    flags = data[offset+25]
    name_len = data[offset+32]
    name = data[offset+33:offset+33+name_len].decode('ascii', errors='ignore')

    is_directory = (flags & 0x02) != 0

    return {
        'record_len': record_len,
        'lba': extent_lba,
        'size': data_len,
        'name': name,
        'is_directory': is_directory,
    }

def list_directory(f, lba, size, path=""):
    """Recursively list directory contents"""
    sectors = (size + DATA_SIZE - 1) // DATA_SIZE
    dir_data = b''

    for i in range(sectors):
        dir_data += read_sector(f, lba + i)

    offset = 0
    files = []

    while offset < size:
        record = parse_directory_record(dir_data, offset)
        if not record:
            break

        if record['name'] and record['name'] not in ['.', '..', '\x00', '\x01']:
            full_path = f"{path}/{record['name']}" if path else record['name']

            if record['is_directory']:
                # Recurse into directory
                subfiles = list_directory(f, record['lba'], record['size'], full_path)
                files.extend(subfiles)
            else:
                files.append({
                    'path': full_path,
                    'lba': record['lba'],
                    'size': record['size']
                })

        offset += record['record_len']

    return files

def main():
    print("=" * 70)
    print("  LIST ALL FILES ON DISC")
    print("=" * 70)
    print()

    with open(BIN_PATH, 'rb') as f:
        # Read PVD
        pvd = read_sector(f, 16)

        if pvd[1:6] != b'CD001':
            print("[ERROR] Not a valid ISO9660")
            return

        # Get root directory
        root_record = pvd[156:156+34]
        root_lba = struct.unpack('<I', root_record[2:6])[0]
        root_size = struct.unpack('<I', root_record[10:14])[0]

        print(f"Scanning disc...")
        print()

        files = list_directory(f, root_lba, root_size)

        # Sort by name
        files.sort(key=lambda x: x['path'])

        print(f"Found {len(files)} file(s):")
        print()

        print(f"{'File':<50} {'Size':>12} {'LBA':>8}")
        print("-" * 70)

        for file in files:
            print(f"{file['path']:<50} {file['size']:>12,} {file['lba']:>8}")

        print()
        print("=" * 70)
        print("FILES OF INTEREST:")
        print("=" * 70)
        print()

        # Highlight interesting files
        interesting = []
        for file in files:
            name = file['path'].upper()
            if any(ext in name for ext in ['.DAT', '.BIN', '.ALL', '.TBL', 'ITEM', 'PRICE', 'SHOP']):
                interesting.append(file)

        if interesting:
            print("Data files that might contain prices:")
            for file in interesting:
                print(f"  - {file['path']} ({file['size']:,} bytes, LBA {file['lba']})")
        else:
            print("No obvious data files found.")
            print()
            print("BLAZE.ALL is probably the main data file.")
            print("Prices might be:")
            print("  - In SLES_008.45 (executable)")
            print("  - Compressed within BLAZE.ALL")
            print("  - Calculated dynamically")

if __name__ == '__main__':
    main()
