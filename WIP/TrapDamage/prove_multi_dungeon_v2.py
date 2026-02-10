#!/usr/bin/env python3
"""
The stat_mod function signature exists in 173 locations across BLAZE.ALL.
Each overlay region has its own copy loaded at a different RAM base.
Different overlays use DIFFERENT JAL encodings to call their local copy.

Strategy:
1. For each region with a signature match, determine the region's overlay base
   using J instruction voting (same method that found base=0x80039000 for Region_00)
2. Calculate the function's RAM address in that overlay
3. Compute the JAL word for that address
4. Search that region for callers with negative args

This will prove stat_mod exists and is called with damage values in multiple dungeons.
"""

import struct
from pathlib import Path
from collections import defaultdict

BLAZE_ALL = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377"
                 r"\GameplayPatch\output\BLAZE.ALL")

# Region_00 known values
R0_BASE = 0x80039000
R0_START = 0x00900000
R0_FUNC_BLAZE = 0x009513E4  # stat_mod function in Region_00

# The function's offset within the overlay
FUNC_OFFSET_IN_OVERLAY = R0_FUNC_BLAZE - R0_START  # 0x513E4


def ram_to_jal(addr):
    return (0x03 << 26) | ((addr >> 2) & 0x3FFFFFF)


def jal_to_ram(word):
    return ((word & 0x3FFFFFF) << 2) | 0x80000000


def find_overlay_base_via_j(data, region_start, region_end):
    """Find overlay base using J instruction target voting."""
    base_votes = defaultdict(int)
    for off in range(region_start, min(region_end, len(data) - 4), 4):
        w = struct.unpack_from('<I', data, off)[0]
        if (w >> 26) != 0x02:  # Not a J instruction
            continue
        target = jal_to_ram(w)
        # Infer base: target = base + (off - region_start) + delta
        # For a jump, target should be within the same overlay
        # base = target - (target_blaze - region_start)
        # Since target_blaze should also be in [region_start, region_end],
        # we approximate: base = target - (off - region_start)
        inferred_base = target - (off - region_start)
        aligned = (inferred_base >> 12) << 12
        base_votes[aligned] += 1

    if not base_votes:
        return None

    # Return the base with most votes
    best_base = max(base_votes.items(), key=lambda x: x[1])
    return best_base[0], best_base[1]


def extract_args_before_jal(data, jal_off, start):
    """Extract immediate args ($a1-$a3) from instructions before JAL."""
    args = {}
    for j in range(1, 13):
        off = jal_off - j * 4
        if off < start:
            break
        w = struct.unpack_from('<I', data, off)[0]
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000
        if op == 0x09 and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imms
        elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imm
        elif (w >> 26) == 0x03:
            break
    # Delay slot
    ds_off = jal_off + 4
    if ds_off + 4 <= len(data):
        w = struct.unpack_from('<I', data, ds_off)[0]
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        imms = imm if imm < 0x8000 else imm - 0x10000
        if op == 0x09 and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imms
        elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
            if rt not in args:
                args[rt] = imm
    return args


def main():
    print("=" * 70)
    print("  Prove Stat_Mod Damage in Multiple Dungeon Overlays")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()
    print(f"  BLAZE.ALL: {len(data):,} bytes")

    # Step 1: Find function signature matches
    sig_start = R0_FUNC_BLAZE
    signature = [struct.unpack_from('<I', data, sig_start + i*4)[0] for i in range(8)]

    # Broader search: use 4 words
    sig4 = signature[:4]
    matches = []
    search_end = min(0x02D00000, len(data) - 32)
    for off in range(0x00900000, search_end, 4):
        if struct.unpack_from('<I', data, off)[0] != sig4[0]:
            continue
        match = all(struct.unpack_from('<I', data, off + i*4)[0] == sig4[i] for i in range(1, 4))
        if match:
            # Count full match
            score = 4
            for i in range(4, 8):
                if struct.unpack_from('<I', data, off + i*4)[0] == signature[i]:
                    score += 1
            if score >= 6:  # Strong match
                matches.append((off, score))

    print(f"  Found {len(matches)} strong signature matches (6+ of 8 words)")

    # Group by region (1MB blocks)
    by_region = defaultdict(list)
    for off, score in matches:
        region = off >> 20
        by_region[region].append((off, score))

    print(f"  Across {len(by_region)} distinct regions")

    # Step 2: For each region, find base and search for damage callers
    print(f"\n{'='*70}")
    print(f"  Per-Region Analysis")
    print(f"{'='*70}")

    # Zone data offset to dungeon mapping
    dungeon_regions = {
        0x009: "Cavern of Death (overlay)",
        0x00B: "Unknown-B",
        0x00D: "Unknown-D",
        0x00E: "Unknown-E",
        0x010: "Unknown-10",
        0x012: "Unknown-12",
        0x013: "Unknown-13",
        0x015: "Forest (overlay?)",
        0x016: "Unknown-16",
        0x017: "Unknown-17",
        0x01A: "Unknown-1A",
        0x01B: "Tower (overlay?)",
        0x01C: "Unknown-1C",
        0x01E: "Sealed Cave (overlay?)",
        0x020: "Unknown-20",
        0x021: "Castle (overlay?)",
        0x024: "Unknown-24",
        0x025: "Valley (overlay?)",
        0x026: "Undersea (overlay?)",
        0x027: "Unknown-27",
        0x028: "Unknown-28",
        0x029: "Unknown-29",
        0x02B: "Hall of Demons (overlay?)",
    }

    total_damage_regions = 0
    all_results = []

    for region, region_matches in sorted(by_region.items()):
        # Find region boundaries (extend to nearest code)
        region_start = min(off for off, _ in region_matches) - 0x60000
        region_start = max(region_start, 0x00900000)
        region_end = max(off for off, _ in region_matches) + 0x60000
        region_end = min(region_end, len(data))

        # Find overlay base for this region
        base_result = find_overlay_base_via_j(data, region_start, region_end)
        if not base_result:
            continue

        base, votes = base_result

        # The stat_mod function in this region
        best_func_off = region_matches[0][0]  # Best match
        func_ram = base + (best_func_off - region_start)

        # But FUNC_OFFSET_IN_OVERLAY is the offset from the overlay start
        # We need to figure out where this overlay actually starts
        # The function is at best_func_off in BLAZE, and at func_ram in RAM
        # overlay_blaze_start = best_func_off - FUNC_OFFSET_IN_OVERLAY
        # But FUNC_OFFSET_IN_OVERLAY is specific to Region_00's layout
        # Different overlays may have the function at different offsets

        # Instead, directly compute: function is at best_func_off in BLAZE
        # The JAL to call it encodes its RAM address: func_ram = base + (best_func_off - overlay_start)
        # But we don't know overlay_start for other regions...

        # Actually, from base voting: base = inferred from J instructions
        # which means for any instruction at BLAZE+off, its RAM addr = base + (off - region_start_approx)
        # We used region_start as the approximate overlay start in file

        # So: func_ram = base + (best_func_off - region_start)
        func_ram_addr = base + (best_func_off - region_start)
        jal_word = ram_to_jal(func_ram_addr)

        # Search for this JAL in the region
        jal_count = 0
        damage_callers = []
        for off in range(region_start, min(region_end, len(data) - 4), 4):
            w = struct.unpack_from('<I', data, off)[0]
            if w != jal_word:
                continue
            jal_count += 1
            args = extract_args_before_jal(data, off, region_start)
            has_neg = any(v < 0 for r, v in args.items() if r in (5, 6, 7) and -200 <= v < 0)
            if has_neg:
                damage_callers.append((off, args))

        label = dungeon_regions.get(region, f"Unknown-{region:03X}")
        status = "DAMAGE FOUND" if damage_callers else ("callers but no damage" if jal_count > 0 else "no callers")

        if damage_callers:
            total_damage_regions += 1

        all_results.append({
            'region': region,
            'label': label,
            'base': base,
            'votes': votes,
            'func_ram': func_ram_addr,
            'jal_count': jal_count,
            'damage_count': len(damage_callers),
            'callers': damage_callers,
        })

        if jal_count > 0 or damage_callers:
            print(f"\n  Region 0x{region:03X} ({label}):")
            print(f"    Base: 0x{base:08X} ({votes} votes)")
            print(f"    stat_mod RAM: 0x{func_ram_addr:08X}, JAL: 0x{jal_word:08X}")
            print(f"    Total callers: {jal_count}, Damage callers: {len(damage_callers)}")
            for off, args in damage_callers[:8]:
                args_str = ', '.join(f"$a{r-4}={v}" for r, v in sorted(args.items()) if r in (5,6,7))
                print(f"      0x{off:08X}: {args_str}")
            if len(damage_callers) > 8:
                print(f"      ... and {len(damage_callers)-8} more")

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Function signature found in {len(by_region)} overlay regions")
    print(f"  Regions with damage callers: {total_damage_regions}")
    print(f"\n  {'Region':>6}  {'Base':>12}  {'Votes':>5}  {'Callers':>7}  {'Damage':>6}  Label")
    print(f"  {'-'*6}  {'-'*12}  {'-'*5}  {'-'*7}  {'-'*6}  {'-'*25}")
    for r in sorted(all_results, key=lambda x: x['region']):
        if r['jal_count'] > 0 or r['damage_count'] > 0:
            print(f"  0x{r['region']:03X}  0x{r['base']:08X}  {r['votes']:>5}  "
                  f"{r['jal_count']:>7}  {r['damage_count']:>6}  {r['label']}")


if __name__ == "__main__":
    main()
