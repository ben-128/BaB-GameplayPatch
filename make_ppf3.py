#!/usr/bin/env python3
"""
make_ppf3.py - Generate PPF3 patch from original and patched BIN files.

Replaces PPF-Studio GUI tool with a scriptable CLI alternative.

PPF3 format:
  0x00  5B  Magic "PPF30"
  0x05  1B  Encoding method (2 = PPF3)
  0x06  50B Description (null-padded)
  0x38  1B  Image type (0 = BIN)
  0x39  1B  Block check (0=off, 1=on)
  0x3A  1B  Undo data (0=off, 1=on)
  0x3B  1B  Dummy (0)
  [if block check: 1024 bytes from start of original file]
  Patch blocks: [uint64_LE offset][uint8 length][new data bytes]
  [if undo: original data bytes after each block]

Usage:
  py -3 make_ppf3.py <original.bin> <patched.bin> <output.ppf> [--description "text"]
  py -3 make_ppf3.py  (uses default paths from build pipeline)
"""

import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Default paths (build pipeline)
DEFAULT_ORIGINAL = SCRIPT_DIR / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"
DEFAULT_PATCHED  = SCRIPT_DIR / "output" / "Blaze & Blade - Patched.bin"
DEFAULT_OUTPUT   = SCRIPT_DIR / "output" / "BaB_Plus_Patch_1.1c.ppf"
DEFAULT_DESC     = "BaB+ v1.1c Gameplay Patch (EU) by ben-128"

MAX_BLOCK_LEN = 255  # PPF3 block length is uint8


def make_ppf3(original_path, patched_path, output_path, description="", undo=True, block_check=True):
    """Generate PPF3 patch file by comparing original and patched BINs."""

    print("=" * 60)
    print("  PPF3 Patch Generator")
    print("=" * 60)
    print()

    # Read files
    print(f"Original: {original_path}")
    original = original_path.read_bytes()
    print(f"  Size: {len(original):,} bytes")

    print(f"Patched:  {patched_path}")
    patched = patched_path.read_bytes()
    print(f"  Size: {len(patched):,} bytes")

    if len(original) != len(patched):
        print(f"[ERROR] File sizes differ ({len(original)} vs {len(patched)})")
        print("PPF3 requires same-size files.")
        return False

    # Find all differences
    print(f"\nScanning for differences...")
    blocks = []
    i = 0
    file_len = len(original)

    while i < file_len:
        if original[i] != patched[i]:
            # Found a difference - collect consecutive changed bytes
            start = i
            while i < file_len and original[i] != patched[i]:
                i += 1
            diff_len = i - start

            # Split into MAX_BLOCK_LEN-sized chunks
            for chunk_start in range(start, start + diff_len, MAX_BLOCK_LEN):
                chunk_end = min(chunk_start + MAX_BLOCK_LEN, start + diff_len)
                chunk_len = chunk_end - chunk_start
                blocks.append({
                    'offset': chunk_start,
                    'length': chunk_len,
                    'new_data': patched[chunk_start:chunk_end],
                    'old_data': original[chunk_start:chunk_end],
                })
        else:
            i += 1

    total_changed = sum(b['length'] for b in blocks)
    print(f"  {len(blocks)} patch blocks, {total_changed:,} bytes changed")

    if not blocks:
        print("[WARN] Files are identical - no patch needed")
        return False

    # Build PPF3 file
    print(f"\nGenerating PPF3...")
    out = bytearray()

    # Header
    out += b'PPF30'                                          # Magic
    out += struct.pack('B', 2)                               # Encoding = PPF3
    desc_bytes = description.encode('ascii', errors='ignore')[:50]
    out += desc_bytes.ljust(50, b'\x00')                     # Description
    out += struct.pack('B', 0)                               # Image type = BIN
    out += struct.pack('B', 1 if block_check else 0)         # Block check
    out += struct.pack('B', 1 if undo else 0)                # Undo data
    out += struct.pack('B', 0)                               # Dummy

    # Block check data (first 1024 bytes of original)
    if block_check:
        out += original[:1024]

    # Patch blocks
    for block in blocks:
        out += struct.pack('<Q', block['offset'])            # 8-byte offset
        out += struct.pack('B', block['length'])             # 1-byte length
        out += block['new_data']                             # New data
        if undo:
            out += block['old_data']                         # Original data (undo)

    # Write output
    print(f"Output:   {output_path}")
    print(f"  Size: {len(out):,} bytes")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(out)

    print()
    print("=" * 60)
    print("  PPF3 patch created successfully!")
    print("=" * 60)
    print()
    print(f"Apply with: ppf-o-matic3.exe")
    print(f"  Original: {original_path.name}")
    print(f"  Patch:    {output_path.name}")

    return True


def main():
    # Parse args
    args = sys.argv[1:]
    description = DEFAULT_DESC

    # Extract --description flag
    for i, a in enumerate(args):
        if a == '--description' and i + 1 < len(args):
            description = args[i + 1]
            args = args[:i] + args[i+2:]
            break

    if len(args) >= 3:
        original_path = Path(args[0])
        patched_path = Path(args[1])
        output_path = Path(args[2])
    elif len(args) == 0:
        original_path = DEFAULT_ORIGINAL
        patched_path = DEFAULT_PATCHED
        output_path = DEFAULT_OUTPUT
    else:
        print("Usage: py -3 make_ppf3.py [original.bin patched.bin output.ppf] [--description text]")
        print("       Without args: uses default build pipeline paths")
        return 1

    if not original_path.exists():
        print(f"[ERROR] Original not found: {original_path}")
        return 1
    if not patched_path.exists():
        print(f"[ERROR] Patched not found: {patched_path}")
        return 1

    success = make_ppf3(original_path, patched_path, output_path, description)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
