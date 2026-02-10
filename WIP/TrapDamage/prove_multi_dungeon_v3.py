#!/usr/bin/env python3
"""
Function-agnostic search for damage callers across ALL dungeon overlays.

Instead of looking for a specific JAL target, we search for the CALLER PATTERN:
  addiu $a1, $zero, <negative>
  addiu $a2, $zero, <negative>
  jal <any_function>
  addiu $a3, $zero, <negative>   (delay slot)

This finds damage calls regardless of overlay base address or function address.

We filter for:
1. At least 2 of $a1/$a2/$a3 set to negative values (-1 to -200)
2. Within 10 instructions before the JAL (and 1 after for delay slot)
3. Grouped by overlay region
"""

import struct
from pathlib import Path
from collections import defaultdict

BLAZE_ALL = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377"
                 r"\GameplayPatch\output\BLAZE.ALL")

OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000

# Known Region_00 function signature for verification
SIG_WORDS = None  # Will be loaded


def is_jal(word):
    return (word >> 26) == 0x03

def jal_target(word):
    return ((word & 0x3FFFFFF) << 2) | 0x80000000


def find_damage_callers(data, start, end):
    """Find ALL JAL calls with 2+ negative small integer args in $a1-$a3."""
    callers = []

    for i in range(start, min(end, len(data) - 4), 4):
        w = struct.unpack_from('<I', data, i)[0]
        if not is_jal(w):
            continue

        target = jal_target(w)
        # Only consider calls to RAM functions (0x80xxxxxx)
        if not (0x80000000 <= target <= 0x80FFFFFF):
            continue

        # Extract $a1, $a2, $a3 immediate values
        args = {}

        # Check 10 instructions before
        for j in range(1, 11):
            off = i - j * 4
            if off < start:
                break
            cw = struct.unpack_from('<I', data, off)[0]
            op = (cw >> 26) & 0x3F
            rs = (cw >> 21) & 0x1F
            rt = (cw >> 16) & 0x1F
            imm = cw & 0xFFFF
            imms = imm if imm < 0x8000 else imm - 0x10000

            # addiu $aX, $zero, imm
            if op == 0x09 and rs == 0 and 5 <= rt <= 7:
                if rt not in args:
                    args[rt] = imms
            # ori $aX, $zero, imm
            elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
                if rt not in args:
                    args[rt] = imm
            # Stop at another JAL
            elif is_jal(cw):
                break

        # Check delay slot
        ds_off = i + 4
        if ds_off + 4 <= len(data):
            cw = struct.unpack_from('<I', data, ds_off)[0]
            op = (cw >> 26) & 0x3F
            rs = (cw >> 21) & 0x1F
            rt = (cw >> 16) & 0x1F
            imm = cw & 0xFFFF
            imms = imm if imm < 0x8000 else imm - 0x10000
            if op == 0x09 and rs == 0 and 5 <= rt <= 7:
                if rt not in args:
                    args[rt] = imms
            elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
                if rt not in args:
                    args[rt] = imm

        # Filter: at least 2 of $a1/$a2/$a3 are negative and in range -200 to -1
        neg_args = {r: v for r, v in args.items() if r in (5, 6, 7) and -200 <= v <= -2}
        if len(neg_args) >= 2:
            callers.append({
                'offset': i,
                'target': target,
                'args': args,
                'neg_args': neg_args,
            })

    return callers


def detect_code_regions(data, start, end, block_size=0x10000, threshold=5):
    """Detect code regions by JAL density."""
    regions = []
    for off in range(start, min(end, len(data)), block_size):
        jal_count = 0
        block_end = min(off + block_size, end, len(data))
        for i in range(off, block_end - 4, 4):
            w = struct.unpack_from('<I', data, i)[0]
            if is_jal(w) and 0x80000000 <= jal_target(w) <= 0x80FFFFFF:
                jal_count += 1
        if jal_count >= threshold:
            regions.append((off, block_end, jal_count))
    return regions


def merge_regions(regions, gap=0x10000):
    if not regions:
        return []
    merged = [list(regions[0])]
    for start, end, count in regions[1:]:
        if start <= merged[-1][1] + gap:
            merged[-1][1] = end
            merged[-1][2] += count
        else:
            merged.append([start, end, count])
    return [(s, e, c) for s, e, c in merged]


def main():
    print("=" * 70)
    print("  Function-Agnostic Damage Caller Search")
    print("  (Finds negative stat modifications in ALL dungeon overlays)")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()
    end = min(OVERLAY_END, len(data))

    # Step 1: Detect code regions
    print(f"\n  Detecting code regions...")
    raw = detect_code_regions(data, OVERLAY_START, end)
    regions = merge_regions(raw)
    print(f"  Found {len(regions)} code regions")

    # Step 2: Search each region for damage callers
    print(f"\n{'='*70}")
    print(f"  Searching ALL code regions for damage callers")
    print(f"  (Pattern: 2+ of $a1/$a2/$a3 set to -2..-200 before JAL)")
    print(f"{'='*70}")

    total_damage = 0
    regions_with_damage = 0

    for ri, (reg_start, reg_end, jal_count) in enumerate(regions):
        callers = find_damage_callers(data, reg_start, reg_end)

        if callers:
            regions_with_damage += 1
            total_damage += len(callers)

            # Group by target function
            by_target = defaultdict(list)
            for c in callers:
                by_target[c['target']].append(c)

            # Summarize unique damage values
            unique_triplets = set()
            for c in callers:
                vals = tuple(c['neg_args'].get(r, 0) for r in (5, 6, 7))
                unique_triplets.add(vals)

            print(f"\n  Region_{ri:02d} (0x{reg_start:08X}-0x{reg_end:08X}, "
                  f"{jal_count} JALs):")
            print(f"    {len(callers)} damage callers to "
                  f"{len(by_target)} function(s)")

            for target, tcallers in sorted(by_target.items(), key=lambda x: -len(x[1])):
                print(f"    -> 0x{target:08X}: {len(tcallers)} damage calls")
                for c in tcallers[:5]:
                    args_str = ', '.join(
                        f"$a{r-4}={v}" for r, v in sorted(c['args'].items())
                        if r in (5, 6, 7) and isinstance(v, int)
                    )
                    print(f"       0x{c['offset']:08X}: {args_str}")
                if len(tcallers) > 5:
                    print(f"       ... and {len(tcallers)-5} more")

            print(f"    Unique damage triplets ($a1,$a2,$a3):")
            for t in sorted(unique_triplets):
                print(f"      ({t[0]:>4}, {t[1]:>4}, {t[2]:>4})")

    # Final summary
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"  Total code regions: {len(regions)}")
    print(f"  Regions with damage callers: {regions_with_damage}")
    print(f"  Total damage callers: {total_damage}")

    if regions_with_damage > 1:
        print(f"\n  PROVEN: Damage code exists in {regions_with_damage} overlay regions!")
        print(f"  The patcher should cover ALL of these regions.")
    elif regions_with_damage == 1:
        print(f"\n  Only 1 region has damage callers.")
        print(f"  Other dungeons may use different damage mechanisms.")
    else:
        print(f"\n  No damage callers found!")


if __name__ == "__main__":
    main()
