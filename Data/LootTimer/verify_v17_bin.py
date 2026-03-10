#!/usr/bin/env python3
"""Verify all v17 patches in final BIN."""
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

LBA1, LBA2 = 163167, 185765
SECTOR = 2352
HDR = 24
USER = 2048

# All patches to verify
PATCHES = {
    "Layer 1: check_kill func": (0x0093B908, 0x03E00008),
    "Layer 1: func +4":         (0x0093B90C, 0x00001021),
    "Layer 2: STUB caller 1":   (0x009406FC, 0x24020000),
    "Layer 2: STUB caller 2":   (0x00942E60, 0x24020000),
    "Layer 2: STUB caller 5":   (0x009444A0, 0x24020000),
    "Layer 2: STUB caller 8":   (0x009461B4, 0x24020000),
    "Layer 2: MAIN caller 1":   (0x00946E9C, 0x24020000),
    "Layer 2: MAIN caller 5":   (0x0094E0C0, 0x24020000),
    "Layer 2: MAIN caller 9":   (0x0094F66C, 0x24020000),
    "Layer 3: timer or->nop":   (0x0094E0B8, 0x00000000),
    "Layer 3: timer sw->nop":   (0x0094E0BC, 0x00000000),
}

bin_path = PROJECT_DIR / 'output' / 'Blaze & Blade - Patched.bin'
with open(bin_path, 'rb') as f:
    for name, (blaze_off, expected) in PATCHES.items():
        sec = blaze_off // USER
        byte_in_sec = blaze_off % USER
        bin_off = (LBA1 + sec) * SECTOR + HDR + byte_in_sec
        f.seek(bin_off)
        actual = struct.unpack('<I', f.read(4))[0]
        ok = "OK" if actual == expected else "FAIL"
        print(f"  [{ok}] {name}: 0x{actual:08X} {'==' if ok == 'OK' else '!='} 0x{expected:08X}")
