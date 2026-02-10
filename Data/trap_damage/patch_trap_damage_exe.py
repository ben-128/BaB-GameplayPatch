#!/usr/bin/env python3
"""
Patch the EXE damage division to globally multiply all %-based damage.

The damage function at 0x80024F90 computes:
  damage = (max_HP * param) / 100

The division by 100 uses magic multiplication ending with:
  sra  $v1, $t0, 5        (0x00081943)  <-- THIS is patched

Changing the sra shift:
  shift 5 = /100 (normal, 1x damage)
  shift 4 = /50  (2x damage)
  shift 3 = /25  (4x damage)

This affects ALL 189 callers including data-driven ones (falling rocks).
Stacks with overlay_patches: effective = overlay_value * exe_multiplier.

BIN format: raw sectors of 2352 bytes (24-byte header + 2048 user data + 280 ECC).
SLES_008.45 starts at LBA 295081.

Runs at build step 9d (patches output BIN after BLAZE.ALL injection).
"""

import struct
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "trap_damage_config.json"
BIN_PATH = SCRIPT_DIR.parent.parent / "output" / "Blaze & Blade - Patched.bin"

# BIN sector format
SECTOR_SIZE = 2352
SECTOR_HEADER = 24
SECTOR_DATA = 2048

# SLES_008.45 location in BIN
SLES_LBA = 295081

# EXE layout
EXE_HEADER_SIZE = 0x800   # PS-X EXE header
EXE_CODE_BASE = 0x80010000

# The sra instruction at RAM 0x80025004
SRA_RAM_ADDR = 0x80025004
SRA_EXE_OFFSET = EXE_HEADER_SIZE + (SRA_RAM_ADDR - EXE_CODE_BASE)  # 0x15804

# Verification: the lui instruction 4 words before (start of /100 sequence)
LUI_RAM_ADDR = 0x80024FF4
LUI_EXE_OFFSET = EXE_HEADER_SIZE + (LUI_RAM_ADDR - EXE_CODE_BASE)  # 0x157F4

# Expected instruction words for verification
EXPECTED_LUI  = 0x3C0251EB  # lui  $v0, 0x51EB
EXPECTED_ORI  = 0x3442851F  # ori  $v0, $v0, 0x851F
EXPECTED_MULT = 0x00A20018  # mult $a1, $v0
EXPECTED_MFHI = 0x00004010  # mfhi $t0

ORIGINAL_SRA  = 0x00081943  # sra  $v1, $t0, 5


def exe_offset_to_bin(exe_offset):
    """Convert an EXE file offset to a BIN file offset (raw sector format)."""
    sector_in_exe = exe_offset // SECTOR_DATA
    byte_in_sector = exe_offset % SECTOR_DATA
    return (SLES_LBA + sector_in_exe) * SECTOR_SIZE + SECTOR_HEADER + byte_in_sector


def read_exe_word(data, exe_offset):
    """Read a uint32 from the EXE at the given EXE file offset."""
    bin_off = exe_offset_to_bin(exe_offset)
    return struct.unpack_from('<I', data, bin_off)[0]


def write_exe_word(data, exe_offset, word):
    """Write a uint32 to the EXE at the given EXE file offset."""
    bin_off = exe_offset_to_bin(exe_offset)
    struct.pack_into('<I', data, bin_off, word)


def make_sra_word(shift):
    """Build sra $v1, $t0, <shift> instruction word."""
    return (8 << 16) | (3 << 11) | (shift << 6) | 3


def main():
    print("  Trap Damage EXE Patcher (global division shift)")
    print("  " + "-" * 50)

    if not CONFIG_FILE.exists():
        print(f"  [SKIP] Config not found: {CONFIG_FILE.name}")
        return

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    exe_cfg = config.get("exe_global", {})

    if not exe_cfg.get("enabled", False):
        print("  [SKIP] EXE global patch disabled in config")
        return

    shift = exe_cfg.get("shift", 5)
    if shift not in (3, 4, 5):
        print(f"  [ERROR] Invalid shift value: {shift} (must be 3, 4, or 5)")
        sys.exit(1)

    if shift == 5:
        print("  [SKIP] Shift is 5 (normal /100, no change needed)")
        return

    multiplier = {5: 1, 4: 2, 3: 4}[shift]
    print(f"  Shift: {shift} (divide by {100 // multiplier}, = x{multiplier} all damage)")
    print(f"  Target: sra at RAM 0x{SRA_RAM_ADDR:08X} (EXE offset 0x{SRA_EXE_OFFSET:05X})")

    if not BIN_PATH.exists():
        print(f"  [ERROR] BIN not found: {BIN_PATH}")
        sys.exit(1)

    data = bytearray(BIN_PATH.read_bytes())
    print(f"  BIN size: {len(data):,} bytes")

    # Verify the /100 magic sequence (4 instructions before sra)
    verify = [
        (LUI_EXE_OFFSET,      EXPECTED_LUI,  "lui  $v0, 0x51EB"),
        (LUI_EXE_OFFSET + 4,  EXPECTED_ORI,  "ori  $v0, $v0, 0x851F"),
        (LUI_EXE_OFFSET + 8,  EXPECTED_MULT, "mult $a1, $v0"),
        (LUI_EXE_OFFSET + 12, EXPECTED_MFHI, "mfhi $t0"),
    ]

    all_ok = True
    for exe_off, expected, label in verify:
        actual = read_exe_word(data, exe_off)
        ok = actual == expected
        status = "OK" if ok else f"MISMATCH (got 0x{actual:08X})"
        print(f"    EXE+0x{exe_off:05X}: 0x{expected:08X} {label} [{status}]")
        if not ok:
            all_ok = False

    if not all_ok:
        print("  [ERROR] Verification failed! EXE layout doesn't match.")
        sys.exit(1)

    # Read current sra
    current_sra = read_exe_word(data, SRA_EXE_OFFSET)
    current_shift = (current_sra >> 6) & 0x1F

    # Verify it's a sra $v1, $t0, N
    expected_mask = (8 << 16) | (3 << 11) | 3  # rs=0, rt=8, rd=3, func=sra
    if (current_sra & ~(0x1F << 6)) != expected_mask:
        print(f"  [ERROR] EXE+0x{SRA_EXE_OFFSET:05X}: not sra $v1,$t0,N "
              f"(got 0x{current_sra:08X})")
        sys.exit(1)

    print(f"    EXE+0x{SRA_EXE_OFFSET:05X}: 0x{current_sra:08X} sra $v1, $t0, {current_shift} [OK]")

    # Apply patch
    new_sra = make_sra_word(shift)
    bin_off = exe_offset_to_bin(SRA_EXE_OFFSET)
    write_exe_word(data, SRA_EXE_OFFSET, new_sra)

    print(f"\n  [PATCH] BIN+0x{bin_off:08X}: sra shift {current_shift} -> {shift} "
          f"(0x{current_sra:08X} -> 0x{new_sra:08X})")

    BIN_PATH.write_bytes(data)
    print(f"  [OK] x{multiplier} global damage multiplier applied")


if __name__ == "__main__":
    main()
