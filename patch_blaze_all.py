"""
patch_blaze_all.py
Patches BLAZE.ALL into the game BIN file

Usage: py -3 patch_blaze_all.py
"""

from pathlib import Path

# Configuration
BIN_IN      = Path(r"work\Blaze & Blade - Patched.bin")
BIN_OUT     = Path(r"work\Blaze & Blade - Patched.bin")  # Overwrite in place
BLAZE_ALL   = Path(r"work\BLAZE.ALL")

LBA_START   = 163167      # LBA where BLAZE.ALL starts in the BIN
SECTOR_RAW  = 2352        # RAW sector size
USER_OFF    = 24          # MODE2/Form1 user data offset
USER_SIZE   = 2048        # User data per sector

# Number of sectors for BLAZE.ALL (46206976 / 2048 = 22566)
ORIG_SECTORS = 22566

def main():
    print("=" * 50)
    print("  BLAZE.ALL Patcher")
    print("=" * 50)
    print()

    # Read modified BLAZE.ALL
    print(f"Reading {BLAZE_ALL}...")
    data = BLAZE_ALL.read_bytes()

    if len(data) % USER_SIZE != 0:
        raise SystemExit(f"ERROR: BLAZE.ALL size ({len(data)}) not multiple of {USER_SIZE}")

    n_sectors_new = len(data) // USER_SIZE
    print(f"  Size: {len(data)} bytes ({n_sectors_new} sectors)")

    if n_sectors_new > ORIG_SECTORS:
        raise SystemExit(f"ERROR: BLAZE.ALL is larger ({n_sectors_new}) than original ({ORIG_SECTORS})")

    # Read BIN file
    print(f"\nReading {BIN_IN}...")
    bin_bytes = bytearray(BIN_IN.read_bytes())
    bin_size = len(bin_bytes)
    print(f"  Size: {bin_size} bytes")

    # Verify format
    is_raw = (bin_size % SECTOR_RAW == 0)
    is_iso = (bin_size % USER_SIZE == 0) and not is_raw

    if not (is_raw or is_iso):
        raise SystemExit("ERROR: Unknown BIN format (neither 2352 nor 2048 sector size)")

    print(f"  Format: {'RAW (2352)' if is_raw else 'ISO (2048)'}")

    # Inject BLAZE.ALL sectors
    print(f"\nPatching {ORIG_SECTORS} sectors starting at LBA {LBA_START}...")

    for i in range(ORIG_SECTORS):
        src = i * USER_SIZE
        chunk = data[src:src+USER_SIZE] if src < len(data) else b'\x00' * USER_SIZE

        if len(chunk) < USER_SIZE:
            chunk = chunk + b'\x00' * (USER_SIZE - len(chunk))

        if is_raw:
            dst = (LBA_START + i) * SECTOR_RAW + USER_OFF
        else:
            dst = (LBA_START + i) * USER_SIZE

        if dst + USER_SIZE > bin_size:
            raise SystemExit(f"ERROR: Write would exceed file bounds at sector {i}")

        bin_bytes[dst:dst+USER_SIZE] = chunk

    # Write output
    print(f"\nWriting {BIN_OUT}...")
    BIN_OUT.write_bytes(bin_bytes)

    print()
    print("=" * 50)
    print("  Patch complete!")
    print("=" * 50)


if __name__ == '__main__':
    main()
