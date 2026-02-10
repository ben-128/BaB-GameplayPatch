#!/usr/bin/env python3
"""
Scan ALL overlay regions in BLAZE.ALL for damage-like patterns.

Goal: Find trap damage code in ALL dungeons, not just Cavern.

Strategy:
1. Detect code regions (high JAL density)
2. For each region, find ALL JAL calls with negative immediate args
3. Focus on the stat_mod function family AND any other damage-like functions
4. Report per-region findings

The stat_mod functions (all in main EXE at 0x8008xxxx):
  0x8008A1C4, 0x8008A39C, 0x8008A3BC, 0x8008A3E4
"""

import struct
from pathlib import Path
from collections import defaultdict

BLAZE_ALL = Path(__file__).parent.parent.parent / "output" / "BLAZE.ALL"
if not BLAZE_ALL.exists():
    BLAZE_ALL = (Path(__file__).parent.parent.parent
                 / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL")

OVERLAY_START = 0x00900000
OVERLAY_END   = 0x02D00000

# Known stat modifier functions (in main EXE)
STAT_MOD_FUNCS = {
    0x8008A1C4: "stat_mod_A1C4",
    0x8008A39C: "stat_mod_A39C",
    0x8008A3BC: "stat_mod_A3BC",
    0x8008A3E4: "stat_mod_A3E4",
}

# JAL encoding: opcode 0x03, target = addr >> 2
def ram_to_jal(addr):
    return (0x03 << 26) | ((addr >> 2) & 0x3FFFFFF)

def jal_to_ram(word):
    # PS1: top 4 bits from PC = 0x8 (kseg0)
    return ((word & 0x3FFFFFF) << 2) | 0x80000000

def is_jal(word):
    return (word >> 26) == 0x03

def extract_args_before_jal(data, jal_off, start):
    """Extract immediate args ($a1-$a3) from instructions before JAL."""
    args = {}
    # Check 12 instructions before
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

        # addiu $aX, $zero, imm  (li $aX, imm)
        if op == 0x09 and rs == 0 and 5 <= rt <= 7:
            idx = rt  # $a1=5, $a2=6, $a3=7
            if idx not in args:
                args[idx] = imms
        # ori $aX, $zero, imm
        elif op == 0x0D and rs == 0 and 5 <= rt <= 7:
            idx = rt
            if idx not in args:
                args[idx] = imm
        # Stop if we hit another JAL (different call site)
        elif is_jal(w):
            break

    # Check delay slot
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


def detect_code_regions(data, start, end, block_size=0x10000):
    """Detect regions with high JAL density (= code)."""
    regions = []
    for off in range(start, min(end, len(data)), block_size):
        jal_count = 0
        block_end = min(off + block_size, end, len(data))
        for i in range(off, block_end - 4, 4):
            w = struct.unpack_from('<I', data, i)[0]
            if is_jal(w):
                target = jal_to_ram(w)
                # Valid RAM target (0x80000000-0x80FFFFFF)
                if 0x80000000 <= target <= 0x80FFFFFF:
                    jal_count += 1
        if jal_count >= 5:  # At least 5 JALs per 64KB = code region
            regions.append((off, block_end, jal_count))
    return regions


def merge_regions(regions, gap=0x10000):
    """Merge adjacent code regions into contiguous blocks."""
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
    print("  Find ALL Damage Patterns Across ALL Overlay Regions")
    print("=" * 70)

    data = BLAZE_ALL.read_bytes()
    print(f"  BLAZE.ALL: {len(data):,} bytes from {BLAZE_ALL}")

    end = min(OVERLAY_END, len(data))

    # Step 1: Detect code regions
    print(f"\n  Scanning 0x{OVERLAY_START:08X} - 0x{end:08X} for code regions...")
    raw_regions = detect_code_regions(data, OVERLAY_START, end)
    regions = merge_regions(raw_regions)

    print(f"\n  Found {len(regions)} code regions:")
    print(f"  {'Region':>12}  {'Start':>12}  {'End':>12}  {'Size':>10}  {'JALs':>6}")
    print(f"  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*10}  {'-'*6}")
    for i, (s, e, c) in enumerate(regions):
        print(f"  Region_{i:02d}    0x{s:08X}  0x{e:08X}  {e-s:>8,}  {c:>6}")

    # Step 2: For each region, find stat_mod callers
    print(f"\n{'='*70}")
    print(f"  Stat Modifier Function Calls Per Region")
    print(f"{'='*70}")

    stat_mod_jals = {}
    for addr, name in STAT_MOD_FUNCS.items():
        stat_mod_jals[ram_to_jal(addr)] = (addr, name)

    for ri, (reg_start, reg_end, _) in enumerate(regions):
        region_callers = defaultdict(list)

        for i in range(reg_start, min(reg_end, len(data) - 4), 4):
            w = struct.unpack_from('<I', data, i)[0]
            if w in stat_mod_jals:
                addr, name = stat_mod_jals[w]
                args = extract_args_before_jal(data, i, reg_start)
                has_neg = any(v < 0 for v in args.values())
                region_callers[name].append({
                    'offset': i,
                    'args': args,
                    'has_neg': has_neg,
                })

        if region_callers:
            total = sum(len(v) for v in region_callers.values())
            neg_total = sum(1 for calls in region_callers.values()
                          for c in calls if c['has_neg'])
            print(f"\n  Region_{ri:02d} (0x{reg_start:08X}-0x{reg_end:08X}): "
                  f"{total} calls ({neg_total} with negative args)")

            for fname, calls in sorted(region_callers.items()):
                neg_calls = [c for c in calls if c['has_neg']]
                print(f"    {fname}: {len(calls)} total, {len(neg_calls)} damage")
                for c in neg_calls[:5]:  # Show first 5
                    args_str = ', '.join(f"$a{r-4}={v}" for r, v in sorted(c['args'].items()))
                    print(f"      0x{c['offset']:08X}: {args_str}")
                if len(neg_calls) > 5:
                    print(f"      ... and {len(neg_calls)-5} more")

    # Step 3: Search for ANY function called with negative args (broader search)
    print(f"\n{'='*70}")
    print(f"  ALL JAL Calls With Negative Small Integer Args (any function)")
    print(f"{'='*70}")

    for ri, (reg_start, reg_end, _) in enumerate(regions):
        func_damage = defaultdict(list)  # target_addr -> list of callers

        for i in range(reg_start, min(reg_end, len(data) - 4), 4):
            w = struct.unpack_from('<I', data, i)[0]
            if not is_jal(w):
                continue
            target = jal_to_ram(w)
            if not (0x80000000 <= target <= 0x80FFFFFF):
                continue

            args = extract_args_before_jal(data, i, reg_start)
            if not args:
                continue

            # Check: at least one arg is negative AND small (damage-like: -1 to -200)
            has_damage_arg = any(-200 <= v < 0 for v in args.values())
            if has_damage_arg:
                func_damage[target].append({
                    'offset': i,
                    'args': args,
                })

        if func_damage:
            total_callers = sum(len(v) for v in func_damage.values())
            print(f"\n  Region_{ri:02d} (0x{reg_start:08X}-0x{reg_end:08X}): "
                  f"{total_callers} damage-like calls to {len(func_damage)} functions")

            # Sort by number of callers
            for target, calls in sorted(func_damage.items(),
                                       key=lambda x: -len(x[1])):
                label = STAT_MOD_FUNCS.get(target, "")
                if label:
                    label = f" [{label}]"
                print(f"    0x{target:08X}{label}: {len(calls)} damage calls")
                for c in calls[:3]:
                    args_str = ', '.join(f"$a{r-4}={v}" for r, v in sorted(c['args'].items()))
                    print(f"      0x{c['offset']:08X}: {args_str}")
                if len(calls) > 3:
                    print(f"      ... and {len(calls)-3} more")

    # Step 4: Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY: Damage Coverage by Region")
    print(f"{'='*70}")
    print(f"\n  Stat mod function 0x8008A3E4 is in the MAIN EXE (0x80010000+0x7A3E4)")
    print(f"  Any overlay can call it. If a region has 0 callers, that dungeon")
    print(f"  uses a DIFFERENT damage mechanism (or has no traps).")


if __name__ == "__main__":
    main()
