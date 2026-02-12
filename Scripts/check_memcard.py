#!/usr/bin/env python3
"""Check PSX memory card for Blaze & Blade saves."""

import sys
import re

def check_memcard(filepath):
    """Check if memory card contains Blaze & Blade saves."""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()

        print(f"\n=== Checking: {filepath} ===")
        print(f"Size: {len(data)} bytes")

        # Convert to string for text search (ignore errors)
        text = data.decode('ascii', errors='ignore')

        # Search patterns
        patterns = {
            'SLES_008.45': r'SLES.008\.45',
            'SLES_00845': r'SLES.00845',
            'SLES00845': r'SLES00845',
            'Blaze': r'[Bb]laze',
            'Blade': r'[Bb]lade',
            'Eternal': r'[Ee]ternal',
            'T&E Soft': r'T&E\s*Soft',
        }

        found = False
        for name, pattern in patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                print(f"[OK] Found '{name}': {len(matches)} occurrence(s)")
                if len(matches) <= 5:
                    for match in matches:
                        print(f"  - {repr(match)}")
                found = True

        if not found:
            print("[NO] No Blaze & Blade signatures found")

        # Check for PSX memory card header
        if data[:2] == b'MC':
            print("[OK] Valid PSX Memory Card header detected")
        else:
            print("[NO] No standard PSX Memory Card header")

        # List all game codes found
        print("\n--- All SLES codes found ---")
        sles_codes = re.findall(r'SLES[_-]?\d{3}[\._]?\d{2}', text)
        if sles_codes:
            unique_codes = sorted(set(sles_codes))
            for code in unique_codes:
                print(f"  - {code}")
        else:
            print("  (none)")

        # Show first 512 bytes as hex (first 4 save slots headers)
        print("\n--- First 512 bytes (hex) ---")
        for i in range(0, min(512, len(data)), 16):
            hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f"{i:08X}: {hex_part:<48} {ascii_part}")

        return found

    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

if __name__ == "__main__":
    memcard1 = r"D:\VieuxJeux\BAB\ePSXe2018\memcards\duck\epsxe000.mcr"
    memcard2 = r"D:\VieuxJeux\BAB\ePSXe2018\memcards\duck\epsxe001.mcr"

    found1 = check_memcard(memcard1)
    found2 = check_memcard(memcard2)

    print("\n" + "="*60)
    if found1 or found2:
        print("[OK] Blaze & Blade saves FOUND!")
        if found1:
            print(f"  -> {memcard1}")
        if found2:
            print(f"  -> {memcard2}")
    else:
        print("[NO] No Blaze & Blade saves found in either memory card")
