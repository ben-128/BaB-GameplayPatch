"""
verify_bin_patches.py
Verify loot timer patches in the patched BIN file (RAW 2352-byte sectors).

Reads the Cavern F1 overlay from the BIN and checks for:
  - ORIGINAL pattern (should be 0 -- all patched)
  - PATCHED pattern (should be 6)
  - Any remaining addiu $v0,$v0,-1 instructions
"""

import struct
import sys
import os

# -- Config -------------------------------------------------------------------
BIN_PATH = r"D:\projets\Bab_Gameplay_Patch\output\Blaze & Blade - Patched.bin"
BLAZE_ALL_LBA = 163167          # LBA of BLAZE.ALL first copy
OVERLAY_OFFSET = 0x009468A8     # Cavern F1 overlay offset within BLAZE.ALL
OVERLAY_SIZE = 137824           # bytes to read

RAW_SECTOR = 2352               # bytes per raw sector
USER_DATA_OFFSET = 24           # user data starts at byte 24 in raw sector
USER_DATA_SIZE = 2048           # user data per sector


def read_from_bin(bin_path, blaze_lba, file_offset, size):
    """Read `size` bytes starting at `file_offset` within BLAZE.ALL,
    accounting for RAW sector layout in the BIN."""

    data = bytearray()
    remaining = size

    # Which sector (relative to BLAZE.ALL start) and byte within that sector
    sector_in_file = file_offset // USER_DATA_SIZE
    byte_in_sector = file_offset % USER_DATA_SIZE

    with open(bin_path, "rb") as f:
        while remaining > 0:
            abs_lba = blaze_lba + sector_in_file
            # Position in the BIN file
            bin_pos = abs_lba * RAW_SECTOR + USER_DATA_OFFSET + byte_in_sector

            chunk = min(remaining, USER_DATA_SIZE - byte_in_sector)
            f.seek(bin_pos)
            block = f.read(chunk)
            if len(block) != chunk:
                raise IOError(
                    f"Short read at BIN offset 0x{bin_pos:X}: "
                    f"expected {chunk}, got {len(block)}"
                )
            data.extend(block)
            remaining -= chunk
            sector_in_file += 1
            byte_in_sector = 0  # subsequent sectors start at 0

    return bytes(data)


def match_lhu(w):
    """lhu $v0, 0x14(ANY): opcode=100101, rt=$v0=2, imm=0x0014"""
    return (w & 0xFC1FFFFF) == 0x94020014


def match_sh(w):
    """sh $v0, 0x14(ANY): opcode=101001, rt=$v0=2, imm=0x0014"""
    return (w & 0xFC1FFFFF) == 0xA4020014


def match_addiu_dec(w):
    """addiu $v0, $v0, -1  =>  0x2442FFFF"""
    return w == 0x2442FFFF


NOP = 0x00000000


def main():
    print(f"BIN file : {BIN_PATH}")
    print(f"BLAZE.ALL LBA : {BLAZE_ALL_LBA}")
    print(f"Overlay offset: 0x{OVERLAY_OFFSET:08X}")
    print(f"Overlay size  : {OVERLAY_SIZE} bytes ({OVERLAY_SIZE // 4} words)")
    print()

    if not os.path.isfile(BIN_PATH):
        print(f"ERROR: BIN file not found: {BIN_PATH}")
        sys.exit(1)

    overlay = read_from_bin(BIN_PATH, BLAZE_ALL_LBA, OVERLAY_OFFSET, OVERLAY_SIZE)
    print(f"Read {len(overlay)} bytes from BIN.")
    print()

    # Parse all 32-bit words (little-endian MIPS)
    n_words = len(overlay) // 4
    words = struct.unpack(f"<{n_words}I", overlay[:n_words * 4])

    # -- Search for patterns --------------------------------------------------
    original_hits = []   # lhu + nop + addiu -1 + sh   (UNPATCHED)
    patched_hits = []    # lhu + nop + nop + sh         (PATCHED)
    addiu_hits = []      # any addiu $v0,$v0,-1

    for i in range(n_words):
        w = words[i]

        # (c) Any addiu $v0,$v0,-1
        if match_addiu_dec(w):
            addiu_hits.append(i)

        # Need at least 4-word window for pattern checks
        if i + 3 >= n_words:
            continue

        w0, w1, w2, w3 = words[i], words[i+1], words[i+2], words[i+3]

        # (a) ORIGINAL: lhu + nop + addiu $v0,$v0,-1 + sh
        if match_lhu(w0) and w1 == NOP and match_addiu_dec(w2) and match_sh(w3):
            original_hits.append(i)

        # (b) PATCHED: lhu + nop + nop + sh
        if match_lhu(w0) and w1 == NOP and w2 == NOP and match_sh(w3):
            patched_hits.append(i)

    # -- Results --------------------------------------------------------------
    def fmt_offset(word_idx):
        byte_off = word_idx * 4
        return f"overlay+0x{byte_off:05X}  (BLAZE.ALL 0x{OVERLAY_OFFSET + byte_off:08X})"

    print("=" * 72)
    print("(a) ORIGINAL pattern: lhu + nop + addiu $v0,$v0,-1 + sh")
    print(f"    Found: {len(original_hits)}  (expected: 0)")
    for idx in original_hits:
        print(f"      {fmt_offset(idx)}")
    status_a = "PASS" if len(original_hits) == 0 else "FAIL"
    print(f"    Status: {status_a}")
    print()

    print("=" * 72)
    print("(b) PATCHED pattern: lhu + nop + nop + sh")
    print(f"    Found: {len(patched_hits)}  (expected: 6)")
    for idx in patched_hits:
        byte_off = idx * 4
        # Show the 4 words for context
        w0, w1, w2, w3 = words[idx], words[idx+1], words[idx+2], words[idx+3]
        print(f"      {fmt_offset(idx)}")
        print(f"        {w0:08X} {w1:08X} {w2:08X} {w3:08X}")
    status_b = "PASS" if len(patched_hits) == 6 else "FAIL"
    print(f"    Status: {status_b}")
    print()

    print("=" * 72)
    print("(c) Any 'addiu $v0,$v0,-1' (0x2442FFFF) in overlay")
    print(f"    Found: {len(addiu_hits)}")
    for idx in addiu_hits:
        byte_off = idx * 4
        # Show surrounding context (word before and after if available)
        ctx_before = f"{words[idx-1]:08X}" if idx > 0 else "--------"
        ctx_after  = f"{words[idx+1]:08X}" if idx + 1 < n_words else "--------"
        print(f"      {fmt_offset(idx)}  "
              f"[...{ctx_before}] 2442FFFF [{ctx_after}...]")
    if len(addiu_hits) == 0:
        print("    All addiu $v0,$v0,-1 instructions have been removed.")
    print()

    # -- Summary --------------------------------------------------------------
    print("=" * 72)
    overall = "ALL CHECKS PASSED" if (status_a == "PASS" and status_b == "PASS") else "SOME CHECKS FAILED"
    print(f"RESULT: {overall}")
    print(f"  (a) Original patterns remaining: {len(original_hits)} [{status_a}]")
    print(f"  (b) Patched patterns found:      {len(patched_hits)} [{status_b}]")
    print(f"  (c) Total addiu $v0,$v0,-1:      {len(addiu_hits)}")


if __name__ == "__main__":
    main()
