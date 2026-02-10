#!/usr/bin/env python3
"""
Step 1: Read the PS-X EXE header to get text_size, bss_addr, bss_size
Step 2: Determine if 0x8008A3E4 is in text or BSS
Step 3: Find overlay base by cross-referencing caller addresses with
        known EXE function calls

Key insight: The overlay callers make JAL to BOTH:
  - EXE functions (known RAM addresses like 0x80039CB0)
  - Overlay-internal functions (like 0x8008A3E4)
If we can find what RAM address a caller at BLAZE offset X has,
we can compute the base.

Method: Look for LUI+ORI/ADDIU pairs that load known RAM addresses
(global variable pointers) in the overlay code. These addresses
tell us about the memory layout.
"""

import struct
from pathlib import Path

BASE = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch")
BIN_FILE = BASE / "Blaze  Blade - Eternal Quest (Europe)" / "Blaze & Blade - Eternal Quest (Europe).bin"

SECTOR_SIZE = 2352
HEADER_SIZE = 24
USER_SIZE = 2048
SLES_LBA = 295081


def read_sectors(bin_data, lba, count):
    result = bytearray()
    for i in range(count):
        sector_off = (lba + i) * SECTOR_SIZE
        if sector_off + SECTOR_SIZE > len(bin_data):
            break
        result.extend(bin_data[sector_off + HEADER_SIZE: sector_off + HEADER_SIZE + USER_SIZE])
    return bytes(result)


def main():
    print("=" * 70)
    print("  PS-X EXE Header Analysis & Overlay Base Discovery")
    print("=" * 70)

    bin_data = BIN_FILE.read_bytes()
    sles_size_sectors = (824 * 1024 + USER_SIZE - 1) // USER_SIZE
    sles_data = read_sectors(bin_data, SLES_LBA, sles_size_sectors)
    print(f"  SLES_008.45: {len(sles_data):,} bytes")

    # PS-X EXE header
    magic = sles_data[0:8]
    print(f"\n  Header magic: {magic}")

    # Standard PS-X EXE header fields
    dest_addr = struct.unpack_from('<I', sles_data, 0x18)[0]  # initial_pc
    text_addr = struct.unpack_from('<I', sles_data, 0x10)[0]  # (sometimes pad)

    # Read all header fields for PS-X EXE
    print(f"\n  PS-X EXE Header fields:")
    for name, off in [
        ("initial_pc", 0x10),
        ("initial_gp", 0x14),
        ("dest_addr (text)", 0x18),
        ("text_size", 0x1C),
        ("data_addr", 0x20),
        ("data_size", 0x24),
        ("bss_addr", 0x28),
        ("bss_size", 0x2C),
        ("stack_addr", 0x30),
        ("stack_size", 0x34),
    ]:
        val = struct.unpack_from('<I', sles_data, off)[0]
        print(f"    0x{off:02X} {name:16s}: 0x{val:08X} ({val:,})")

    dest_addr = struct.unpack_from('<I', sles_data, 0x18)[0]
    text_size = struct.unpack_from('<I', sles_data, 0x1C)[0]
    bss_addr = struct.unpack_from('<I', sles_data, 0x28)[0]
    bss_size = struct.unpack_from('<I', sles_data, 0x2C)[0]

    print(f"\n  Text section: 0x{dest_addr:08X} - 0x{dest_addr + text_size:08X} "
          f"({text_size:,} bytes)")
    print(f"  BSS section:  0x{bss_addr:08X} - 0x{bss_addr + bss_size:08X} "
          f"({bss_size:,} bytes)")

    func_addr = 0x8008A3E4
    in_text = dest_addr <= func_addr < dest_addr + text_size
    in_bss = bss_addr <= func_addr < bss_addr + bss_size
    print(f"\n  0x{func_addr:08X} in text section: {in_text}")
    print(f"  0x{func_addr:08X} in BSS section: {in_bss}")

    if in_text:
        file_off = 0x800 + (func_addr - dest_addr)
        print(f"  File offset: 0x{file_off:X}")
        words = [struct.unpack_from('<I', sles_data, file_off + i*4)[0] for i in range(8)]
        print(f"  Data: {' '.join(f'{w:08X}' for w in words)}")
        is_zero = all(w == 0 for w in words)
        print(f"  All zeros: {is_zero}")

    # Now: scan the overlay code for a pattern that reveals the load base
    # Method: Find branches within the overlay that target known offsets
    # Or: look for LUI instructions that load addresses we can cross-reference

    BLAZE_ALL = BASE / "output" / "BLAZE.ALL"
    data = BLAZE_ALL.read_bytes()

    print(f"\n{'='*70}")
    print(f"  Finding overlay base via internal cross-references")
    print(f"{'='*70}")

    # If the overlay is loaded at base B, then:
    # - Code at BLAZE+X corresponds to RAM B+(X-0x00900000)
    # - A J/JAL at BLAZE+X targeting RAM Y means Y = B+(target_blaze-0x00900000)
    #   where target_blaze = 0x00900000+(Y-B)

    # Strategy: Find a pair of branch/jump instructions in the overlay that
    # target addresses we can identify. Since all internal JALs encode the
    # full target address, we just need one pair:
    #   - One JAL to a known EXE function (e.g., 0x80039CB0)
    #   - One JAL to an overlay-internal function

    # The EXE functions have known addresses. If the overlay calls 0x80039CB0,
    # that's a JAL 0x80039CB0 at some BLAZE offset. This tells us the overlay
    # CAN call EXE functions. But it doesn't help find the overlay base directly.

    # Better: Find J (jump, not JAL) instructions, which are used for intra-function
    # jumps. Or find branch instructions with computable targets.

    # Even better: Find references to global variables using LUI+ADDIU/ORI pairs.
    # If the overlay references a variable at 0x800BXXXX, that's in BSS.
    # But the key insight: if we see LUI 0x8009 in the overlay code near offset
    # 0x0095xxxx, the upper 16 bits tell us what address range the code expects
    # to be at. If 0x8009 appears, the code thinks it's at 0x8009xxxx.

    # Let's look at J (not JAL) instructions in the overlay, which are used
    # for long jumps within the same section.
    print(f"\n  J (jump) instructions in Region_00 (0x0095xxxx-0x0096xxxx):")
    j_targets = []
    for off in range(0x00951000, min(0x00961000, len(data) - 4), 4):
        w = struct.unpack_from('<I', data, off)[0]
        if (w >> 26) == 0x02:  # J instruction
            target = ((w & 0x3FFFFFF) << 2) | 0x80000000
            j_targets.append((off, target))

    # Group by target address upper 16 bits
    hi_groups = {}
    for off, target in j_targets:
        hi = target >> 16
        if hi not in hi_groups:
            hi_groups[hi] = []
        hi_groups[hi].append((off, target))

    for hi, entries in sorted(hi_groups.items()):
        print(f"    0x{hi:04X}xxxx: {len(entries)} jumps")
        for off, target in entries[:5]:
            # If the target is in the overlay, target = B + (target_blaze - 0x00900000)
            # So target_blaze = 0x00900000 + (target - B)
            print(f"      BLAZE+0x{off:08X} -> 0x{target:08X}")
        if len(entries) > 5:
            print(f"      ... and {len(entries)-5} more")

    # Compute base from J targets
    print(f"\n  Computing base from J instruction targets:")
    for off, target in j_targets[:20]:
        # If J target is within Region_00 overlay:
        # target = B + (target_blaze - 0x00900000)
        # We need target_blaze to be in the range 0x00900000-0x009C0000
        # So B = target - (target_blaze - 0x00900000)
        # But we don't know target_blaze!

        # However, if the J target is NEAR the J instruction in file terms,
        # the offset difference in file = offset difference in RAM.
        # So: target - (B + (off - 0x00900000)) = target_blaze - off
        # We can assume target_blaze is somewhere in Region_00.
        pass

    # More direct approach: for each JAL to 0x8008A3E4, the code before it
    # often has LUI instructions. These LUI values tell us about the address space.
    print(f"\n  LUI instructions near stat_mod callers:")
    jal_word = 0x0C0228F9  # jal 0x8008A3E4
    lui_stats = {}
    for off in range(0x00950000, min(0x00970000, len(data) - 4), 4):
        w = struct.unpack_from('<I', data, off)[0]
        if w == jal_word:
            # Look at 10 instructions around this JAL for LUI
            for delta in range(-40, 44, 4):
                check_off = off + delta
                if check_off < 0x00900000:
                    continue
                cw = struct.unpack_from('<I', data, check_off)[0]
                if (cw >> 26) == 0x0F:  # LUI
                    rt = (cw >> 16) & 0x1F
                    imm = cw & 0xFFFF
                    key = f"0x{imm:04X}"
                    if key not in lui_stats:
                        lui_stats[key] = 0
                    lui_stats[key] += 1

    print(f"  LUI upper halfwords near stat_mod callers:")
    for key, count in sorted(lui_stats.items(), key=lambda x: -x[1])[:20]:
        print(f"    LUI {key}: {count} times")

    # Most common LUI values tell us about the memory layout
    # If we see LUI 0x8009 or 0x800A, code is accessing those ranges

    # Finally: try to find the base by looking at B/J internal targets
    # within Region_00 and finding the most consistent base value
    print(f"\n  Analyzing internal J targets to find overlay base:")

    base_votes = {}
    for off, target in j_targets:
        # The J target must be in Region_00 in terms of BLAZE offset
        # target = B + (target_blaze - 0x00900000)
        # target_blaze = 0x00900000 + (target - B)
        # For target_blaze to be in [0x00900000, 0x009C0000]:
        # target - B must be in [0, 0xC0000]
        # B = target - offset_in_overlay
        # offset_in_overlay = target_blaze - 0x00900000

        # The J instruction at BLAZE+off is at overlay offset (off - 0x00900000)
        # Its RAM address is B + (off - 0x00900000)
        # The target is target_ram

        # For a short forward/backward jump, target should be near the J instruction.
        # So target ~= B + (off - 0x00900000)
        # B ~= target - (off - 0x00900000)
        inferred_base = target - (off - 0x00900000)
        inferred_base_aligned = (inferred_base >> 12) << 12  # Align to 4KB

        if inferred_base_aligned not in base_votes:
            base_votes[inferred_base_aligned] = 0
        base_votes[inferred_base_aligned] += 1

    top_bases = sorted(base_votes.items(), key=lambda x: -x[1])[:10]
    print(f"  Top inferred base addresses:")
    for base, count in top_bases:
        func_off = 0x00900000 + (0x8008A3E4 - base)
        if 0x00900000 <= func_off < 0x009C0000:
            status = "IN RANGE"
        else:
            status = "out of range"
        print(f"    0x{base:08X}: {count} votes "
              f"(func at BLAZE+0x{func_off:08X} {status})")


if __name__ == "__main__":
    main()
