#!/usr/bin/env python3
"""
Extract SLES_008.45 from the BIN file by parsing ISO9660 filesystem
"""

import struct
from pathlib import Path

BIN_PATH = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin")
WORK_DIR = BIN_PATH.parent
SLES_PATH = WORK_DIR / "SLES_008.45"

SECTOR_SIZE = 2352
DATA_OFFSET = 24  # RAW format: 16 sync + 8 header
DATA_SIZE = 2048

def read_sector(f, lba):
    """Read a sector's data from RAW BIN format"""
    f.seek(lba * SECTOR_SIZE + DATA_OFFSET)
    return f.read(DATA_SIZE)

def parse_directory_record(data, offset):
    """Parse an ISO9660 directory record"""
    if offset >= len(data) or data[offset] == 0:
        return None

    record_len = data[offset]
    if record_len == 0:
        return None

    extent_lba = struct.unpack('<I', data[offset+2:offset+6])[0]
    data_len = struct.unpack('<I', data[offset+10:offset+14])[0]
    name_len = data[offset+32]
    name = data[offset+33:offset+33+name_len].decode('ascii', errors='ignore')

    return {
        'record_len': record_len,
        'lba': extent_lba,
        'size': data_len,
        'name': name,
        'offset': offset
    }

def find_and_extract_sles():
    """Find and extract SLES_008.45 from the BIN"""
    print("=" * 70)
    print("  EXTRACT SLES_008.45 FROM BIN FILE")
    print("=" * 70)
    print()

    if not BIN_PATH.exists():
        print(f"[ERROR] BIN file not found: {BIN_PATH}")
        return False

    print(f"BIN: {BIN_PATH}")
    print(f"Size: {BIN_PATH.stat().st_size:,} bytes")
    print()

    with open(BIN_PATH, 'rb') as f:
        # Read Primary Volume Descriptor at sector 16
        print("[1/3] Reading ISO9660 Primary Volume Descriptor...")
        pvd = read_sector(f, 16)

        # Check signature
        if pvd[1:6] != b'CD001':
            print("[ERROR] Not a valid ISO9660 filesystem")
            return False

        print("[OK] Valid ISO9660 found")

        # Get root directory info
        root_dir_record = pvd[156:156+34]
        root_lba = struct.unpack('<I', root_dir_record[2:6])[0]
        root_size = struct.unpack('<I', root_dir_record[10:14])[0]

        print(f"[OK] Root directory at LBA {root_lba}, size {root_size} bytes")
        print()

        # Read root directory
        print("[2/3] Searching root directory for SLES_008.45...")
        sectors_needed = (root_size + DATA_SIZE - 1) // DATA_SIZE
        root_data = b''

        for i in range(sectors_needed):
            root_data += read_sector(f, root_lba + i)

        # Parse directory entries
        offset = 0
        found = False

        while offset < root_size:
            record = parse_directory_record(root_data, offset)
            if not record:
                break

            # Look for SLES_008.45 (might be named SLES_008.45;1 in ISO)
            if 'SLES_008.45' in record['name'].upper():
                print(f"[FOUND] {record['name']}")
                print(f"        LBA: {record['lba']}")
                print(f"        Size: {record['size']:,} bytes")
                print()

                # Extract the file
                print("[3/3] Extracting file...")
                file_sectors = (record['size'] + DATA_SIZE - 1) // DATA_SIZE
                file_data = b''

                for i in range(file_sectors):
                    file_data += read_sector(f, record['lba'] + i)

                # Trim to actual size
                file_data = file_data[:record['size']]

                # Write to file
                SLES_PATH.write_bytes(file_data)
                print(f"[OK] Extracted to: {SLES_PATH}")
                print(f"     Size: {len(file_data):,} bytes")

                found = True
                break

            offset += record['record_len']

        if not found:
            print("[ERROR] SLES_008.45 not found in root directory")
            print()
            print("Files found in root:")
            offset = 0
            while offset < root_size and offset < 4096:  # Limit search
                record = parse_directory_record(root_data, offset)
                if not record:
                    break
                if record['name'] and not record['name'].startswith('\x00'):
                    print(f"  - {record['name']}")
                offset += record['record_len']

            return False

    print()
    print("=" * 70)
    print("  SUCCESS!")
    print("=" * 70)
    return True

if __name__ == '__main__':
    import sys
    success = find_and_extract_sles()
    sys.exit(0 if success else 1)
