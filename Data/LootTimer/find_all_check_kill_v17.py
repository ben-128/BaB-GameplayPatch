#!/usr/bin/env python3
"""
v17: Find ALL copies of check_kill function signature across entire BLAZE.ALL.

The function signature (16 bytes):
  8C840074  lw $a0, 0x0074($a0)   ; load parent entity
  00000000  nop
  8C820000  lw $v0, 0x0000($a0)   ; load parent flags
  3C030080  lui $v1, 0x0080        ; prepare bit 23 mask

Also search with different register variants (the compiler might use
different registers for different zone overlays).

ALSO: Search for ALL jal targets that contain lw $reg, 0x0074 at their
target address - this catches check_kill copies at arbitrary addresses.
"""

import struct
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent
    blaze_path = project_dir / 'Blaze  Blade - Eternal Quest (Europe)' / 'extract' / 'BLAZE.ALL'

    blaze = blaze_path.read_bytes()
    print(f"BLAZE.ALL size: {len(blaze):,} bytes")

    # =========================================================================
    # Part 1: Search for exact 16-byte signature
    # =========================================================================
    sig = bytes([0x74, 0x00, 0x84, 0x8C,  # 8C840074
                 0x00, 0x00, 0x00, 0x00,  # 00000000
                 0x00, 0x00, 0x82, 0x8C,  # 8C820000
                 0x80, 0x00, 0x03, 0x3C]) # 3C030080

    print("\n" + "=" * 80)
    print("  Part 1: Exact 16-byte signature search")
    print("  8C840074 00000000 8C820000 3C030080")
    print("=" * 80)

    pos = 0
    count = 0
    while True:
        idx = blaze.find(sig, pos)
        if idx == -1:
            break
        count += 1
        print(f"  Found at BLAZE 0x{idx:08X}")
        # Show 10 instructions
        for k in range(10):
            a = idx + k * 4
            w = struct.unpack_from('<I', blaze, a)[0]
            print(f"    0x{a:08X}: 0x{w:08X}")
        pos = idx + 4

    print(f"\n  Total exact matches: {count}")

    # =========================================================================
    # Part 2: Search for lw $ANY, 0x0074($ANY) pattern across BLAZE.ALL
    # Encoding: opcode=0x23 (bits 31-26), imm=0x0074 (bits 15-0)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 2: All lw $reg, 0x0074($reg) instructions in code regions")
    print("=" * 80)

    lw_0074_locs = []
    for i in range(0, len(blaze) - 4, 4):
        w = struct.unpack_from('<I', blaze, i)[0]
        op = (w >> 26) & 0x3F
        imm = w & 0xFFFF
        if op == 0x23 and imm == 0x0074:
            # Check if this looks like code (in code regions)
            # BLAZE code regions: 0x0091D80C+ (STUB/MAIN/overlays)
            if i >= 0x00900000:
                rs = (w >> 21) & 0x1F
                rt = (w >> 16) & 0x1F
                # Check if followed by nop + lw $reg, 0x0000($same_rt)
                if i + 12 < len(blaze):
                    w2 = struct.unpack_from('<I', blaze, i + 4)[0]
                    w3 = struct.unpack_from('<I', blaze, i + 8)[0]
                    op3 = (w3 >> 26) & 0x3F
                    rs3 = (w3 >> 21) & 0x1F
                    imm3 = w3 & 0xFFFF
                    if w2 == 0 and op3 == 0x23 and imm3 == 0 and rs3 == rt:
                        lw_0074_locs.append(i)

    print(f"  Found {len(lw_0074_locs)} lw 0x0074 + nop + lw 0x0000 sequences")
    for loc in lw_0074_locs:
        w = struct.unpack_from('<I', blaze, loc)[0]
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        regs = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']
        print(f"  BLAZE 0x{loc:08X}: lw {regs[rt]}, 0x0074({regs[rs]})")

    # =========================================================================
    # Part 3: For each JAL in BLAZE.ALL, check if target has lw 0x0074
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 3: Find ALL JAL targets that start with lw $reg, 0x0074")
    print("=" * 80)

    STUB_BLAZE = 0x0091D80C
    STUB_RAM = 0x80056F64
    MAIN_BLAZE = 0x009468A8
    MAIN_RAM = 0x80080000

    # Build RAM->BLAZE mapping for STUB region
    def ram_to_blaze_stub(ram):
        return (ram - STUB_RAM) + STUB_BLAZE

    jal_targets = {}  # target_ram -> [caller_blaze_offsets]

    for i in range(0, len(blaze) - 4, 4):
        w = struct.unpack_from('<I', blaze, i)[0]
        op = (w >> 26) & 0x3F
        if op == 0x03:  # jal
            target = (w & 0x03FFFFFF) << 2
            # Only consider targets in the STUB/MAIN RAM range
            if 0x80056F64 <= target < 0x800C0000:
                if target not in jal_targets:
                    jal_targets[target] = []
                jal_targets[target].append(i)

    # Check which targets start with lw $reg, 0x0074
    for target_ram, callers in sorted(jal_targets.items()):
        # Convert RAM to BLAZE offset (STUB only)
        blaze_off = ram_to_blaze_stub(target_ram)
        if 0 <= blaze_off < len(blaze) - 4:
            w = struct.unpack_from('<I', blaze, blaze_off)[0]
            op = (w >> 26) & 0x3F
            imm = w & 0xFFFF
            if op == 0x23 and imm == 0x0074:
                print(f"  Target RAM 0x{target_ram:08X} (BLAZE 0x{blaze_off:08X})")
                print(f"    First instr: 0x{w:08X}")
                print(f"    Called from {len(callers)} locations:")
                for c in callers[:5]:
                    print(f"      BLAZE 0x{c:08X}")
                if len(callers) > 5:
                    print(f"      ... and {len(callers) - 5} more")

    # =========================================================================
    # Part 4: Verify patch in output/BLAZE.ALL
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 4: Verify patch status in output/BLAZE.ALL")
    print("=" * 80)

    output_blaze = project_dir / 'output' / 'BLAZE.ALL'
    if output_blaze.exists():
        odata = output_blaze.read_bytes()
        off = 0x0093B908
        w1 = struct.unpack_from('<I', odata, off)[0]
        w2 = struct.unpack_from('<I', odata, off + 4)[0]
        print(f"  output/BLAZE.ALL 0x{off:08X}: 0x{w1:08X} 0x{w2:08X}")
        if w1 == 0x03E00008 and w2 == 0x00001021:
            print(f"    -> PATCHED (jr $ra + addu $v0,$zero,$zero)")
        elif w1 == 0x8C840074:
            print(f"    -> NOT PATCHED (original lw $a0, 0x0074($a0))")
        else:
            print(f"    -> UNKNOWN state")

        # Also check original
        w1o = struct.unpack_from('<I', blaze, off)[0]
        w2o = struct.unpack_from('<I', blaze, off + 4)[0]
        print(f"  original BLAZE.ALL 0x{off:08X}: 0x{w1o:08X} 0x{w2o:08X}")
    else:
        print(f"  output/BLAZE.ALL not found")

    # =========================================================================
    # Part 5: Check BIN for patch at both LBA positions
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 5: Verify patch in output BIN at both LBA positions")
    print("=" * 80)

    bin_path = project_dir / 'output' / 'Blaze & Blade - Eternal Quest (Europe).bin'
    if not bin_path.exists():
        # Try alternate names
        import glob
        bins = glob.glob(str(project_dir / 'output' / '*.bin'))
        if bins:
            bin_path = Path(bins[0])
            print(f"  Using BIN: {bin_path.name}")

    if bin_path.exists():
        # LBA positions for BLAZE.ALL in BIN
        LBA1 = 163167
        LBA2 = 185765
        SECTOR_SIZE = 2352
        HEADER_SIZE = 24
        USER_DATA = 2048

        # Calculate sector for the patch offset
        patch_blaze_off = 0x0093B908
        sector_in_blaze = patch_blaze_off // USER_DATA
        byte_in_sector = patch_blaze_off % USER_DATA

        for lba, name in [(LBA1, "LBA1"), (LBA2, "LBA2")]:
            bin_sector = lba + sector_in_blaze
            bin_offset = bin_sector * SECTOR_SIZE + HEADER_SIZE + byte_in_sector

            with open(bin_path, 'rb') as f:
                f.seek(bin_offset)
                data = f.read(8)

            if len(data) == 8:
                w1 = struct.unpack_from('<I', data, 0)[0]
                w2 = struct.unpack_from('<I', data, 4)[0]
                status = ""
                if w1 == 0x03E00008 and w2 == 0x00001021:
                    status = "PATCHED"
                elif w1 == 0x8C840074:
                    status = "NOT PATCHED"
                else:
                    status = "UNKNOWN"
                print(f"  {name} (sector {bin_sector}): 0x{w1:08X} 0x{w2:08X} -> {status}")
            else:
                print(f"  {name}: Read failed")
    else:
        print(f"  No BIN found in output/")

    # =========================================================================
    # Part 6: Check if chest_update caller of check_kill is per-zone
    # =========================================================================
    print("\n" + "=" * 80)
    print("  Part 6: chest_update jal check_kill at BLAZE 0x0094E0C0")
    print("  This is Cavern F1 only. Search for equivalent in other zones.")
    print("=" * 80)

    # The chest_update calls jal 0x80075060 at BLAZE 0x0094E0C0
    # Other zones have their own chest_update at different offsets
    # These would call... what? Let's find callers of check_kill
    # that are NOT in the STUB+CavernF1 range

    # All 17 JAL callers are at:
    jal_callers = [
        0x009406FC, 0x00942E60, 0x00943788, 0x00943CBC,
        0x009444A0, 0x00944E2C, 0x009457F8, 0x009461B4,
        0x00946E9C, 0x00948AF4, 0x0094CA78, 0x0094D348,
        0x0094E0C0, 0x0094E474, 0x0094F17C, 0x0094F3F4,
        0x0094F66C
    ]

    # Classify by region
    stub_end = 0x009468A8
    print(f"  STUB callers (shared, all zones):")
    for c in jal_callers:
        if c < stub_end:
            print(f"    BLAZE 0x{c:08X}")
    print(f"  MAIN callers (Cavern F1 only):")
    for c in jal_callers:
        if c >= stub_end:
            print(f"    BLAZE 0x{c:08X}")

    # The STUB callers should work for ALL zones since STUB is shared
    # So even if other zones don't have MAIN callers, the 8 STUB callers
    # should still trigger check_kill for those zones
    print(f"\n  If STUB callers trigger for chests in all zones,")
    print(f"  patching the function should work universally.")
    print(f"  If chests still die after patching, the STUB callers")
    print(f"  might NOT be the chest handler (they might be for")
    print(f"  other entity types like gold drops or debris).")


if __name__ == '__main__':
    main()
