#!/usr/bin/env python3
"""
diagnose_script_pointers.py - Scan Area 1 script section for self-referential
absolute pointers that become stale after the N=3->N=4 expansion.

Theory: The script area starts with a "root offset table" (~50 uint32 entries,
as noted in spawn_research.md). Each non-null entry is an absolute BLAZE.ALL
file offset pointing to a per-type behavior block within the script area.

After the expansion (middle +44 bytes, stats +96 bytes = +140 bytes total),
the script area shifts by +0x8C. If the root table values still point to the
VANILLA positions (before the shift), the engine will crash when it dereferences
a stale pointer.

What we scan:
  - Source region: [VANILLA_SCRIPT_START, AREA_END) = the entire post-stats section
  - Looking for: uint32 LE values in [VANILLA_SCRIPT_START, AREA_END) (self-refs)
  - These are pointers into the script/spawn/formation/zone_spawns section that
    would need +0x8C after the expansion.

Also checks: values in [VANILLA_GROUP_OFFSET, VANILLA_SCRIPT_START) = stats refs,
  these would need +0x2C (middle expansion only).

Usage: py -3 Data/formations/Scripts/diagnose_script_pointers.py
"""

import struct
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
VANILLA_BLAZE = PROJECT_ROOT / "Blaze  Blade - Eternal Quest (Europe)" / "extract" / "BLAZE.ALL"
OUTPUT_BLAZE  = PROJECT_ROOT / "output" / "BLAZE.ALL"

# Area boundaries
AREA_START             = 0xF7A900
AREA_END               = 0xF7CA48
AREA_SIZE              = AREA_END - AREA_START  # 8520

# Vanilla layout
VANILLA_MIDDLE_SIZE    = 124
VANILLA_STATS_SIZE     = 3 * 96  # 288
VANILLA_GROUP_OFFSET   = AREA_START + VANILLA_MIDDLE_SIZE          # 0xF7A97C (stats start)
VANILLA_SCRIPT_START   = AREA_START + VANILLA_MIDDLE_SIZE + VANILLA_STATS_SIZE  # 0xF7AA9C
VANILLA_SPAWN_POINTS   = 0xF7AEB4
VANILLA_FORMATION_START= 0xF7AFFC
VANILLA_ZONE_SPAWNS    = 0xF7B520
VANILLA_ZONE_SPAWNS_MID= 0xF7B8FC

# Expansion constants
MIDDLE_EXPANSION       = 44   # 168 - 124
TOTAL_EXPANSION        = 140  # MIDDLE_EXPANSION + 96


def scan_self_refs(data, src_start, src_end, target_lo, target_hi, label):
    """Find all 4-byte-aligned uint32 LE values in [target_lo, target_hi)
    stored within [src_start, src_end) of the binary."""
    found = []
    for off in range(src_start, src_end - 3, 4):
        val = struct.unpack_from('<I', data, off)[0]
        if target_lo <= val < target_hi:
            found.append((off, val))
    return found


def scan_nonaligned_refs(data, src_start, src_end, target_lo, target_hi):
    """Non-aligned scan for completeness."""
    found = []
    for off in range(src_start, src_end - 3):
        val = struct.unpack_from('<I', data, off)[0]
        if target_lo <= val < target_hi:
            found.append((off, val, off % 4))
    return found


def dump_root_table(data, script_start, n_entries=64):
    """Dump first n_entries of the root offset table at script area start."""
    print(f"  Root table at 0x{script_start:08X} (first {n_entries} entries):")
    non_null = 0
    last_nonnull = -1
    for i in range(n_entries):
        off = script_start + i * 4
        if off + 4 > len(data):
            break
        val = struct.unpack_from('<I', data, off)[0]
        if val != 0:
            non_null += 1
            last_nonnull = i
            in_area = AREA_START <= val < AREA_END
            in_script = VANILLA_SCRIPT_START <= val < AREA_END
            flag = ""
            if in_script:
                flag = f"  -> script+0x{val - VANILLA_SCRIPT_START:04X}"
            elif in_area:
                flag = f"  -> area+0x{val - AREA_START:04X}"
            else:
                flag = f"  (OUTSIDE area: 0x{val:08X})"
            print(f"    root[{i:2d}] = 0x{val:08X}{flag}")
        elif i <= last_nonnull + 4:
            print(f"    root[{i:2d}] = 0x00000000  (null)")

    print(f"\n  Total non-null entries in first {n_entries}: {non_null}")
    print(f"  Last non-null index: {last_nonnull}")
    return last_nonnull


def analyze_per_type_block(data, block_addr, label):
    """Dump the first 64 bytes of a per-type behavior block."""
    print(f"\n  Block '{label}' at 0x{block_addr:08X} (first 64 bytes):")
    for row in range(0, 64, 16):
        off = block_addr + row
        chunk = data[off:off+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        # Check for self-refs
        refs = []
        for i in range(0, 16, 4):
            if off + i + 4 <= len(data):
                v = struct.unpack_from('<I', data, off + i)[0]
                if VANILLA_SCRIPT_START <= v < AREA_END:
                    refs.append(f"+{row+i:02X}->script+0x{v-VANILLA_SCRIPT_START:04X}")
        ref_str = '  ' + ', '.join(refs) if refs else ''
        print(f"    {off:08X}: {hex_str:<48}{ref_str}")


def main():
    vanilla_data = VANILLA_BLAZE.read_bytes()
    print(f"[OK] Loaded vanilla BLAZE.ALL ({len(vanilla_data):,} bytes)")
    print()

    # Load expanded output too (for comparison)
    if OUTPUT_BLAZE.exists():
        output_data = OUTPUT_BLAZE.read_bytes()
        print(f"[OK] Loaded output BLAZE.ALL ({len(output_data):,} bytes)")
        # Check if it's expanded
        new_script = AREA_START + 168 + 384  # 0xF7AB28
        is_expanded = output_data[new_script:new_script+4] != b'\x00\x00\x00\x00'
        print(f"     Output state: {'EXPANDED (script at 0xF7AB28)' if is_expanded else 'VANILLA'}")
    else:
        output_data = None
    print()

    # ── 1. Root table analysis ────────────────────────────────────────────────
    print("=" * 70)
    print("  1. ROOT OFFSET TABLE (vanilla script area start = 0xF7AA9C)")
    print("=" * 70)
    print()
    last_nonnull = dump_root_table(vanilla_data, VANILLA_SCRIPT_START)
    print()

    # ── 2. Scan entire post-stats area for self-referential pointers ──────────
    print("=" * 70)
    print("  2. SELF-REFERENTIAL POINTER SCAN (4-byte aligned)")
    print(f"  Source: [0x{VANILLA_SCRIPT_START:08X}, 0x{AREA_END:08X}) = script+spawn+form+zonespawn")
    print(f"  Looking for values in [0x{VANILLA_SCRIPT_START:08X}, 0x{AREA_END:08X})")
    print(f"  These pointers need +0x{TOTAL_EXPANSION:02X} correction after expansion")
    print("=" * 70)
    print()

    script_self_refs = scan_self_refs(vanilla_data,
                                      VANILLA_SCRIPT_START, AREA_END,
                                      VANILLA_SCRIPT_START, AREA_END,
                                      "script->script")
    print(f"  Found {len(script_self_refs)} pointers from script area into script area (+0x{TOTAL_EXPANSION:02X} needed):")
    for off, val in script_self_refs[:40]:
        section = ""
        if off < VANILLA_SPAWN_POINTS:
            section = "script"
        elif off < VANILLA_FORMATION_START:
            section = "spawn_pts"
        elif off < VANILLA_ZONE_SPAWNS:
            section = "formations"
        else:
            section = "zone_spawn"
        print(f"    [in {section:10s}] 0x{off:08X} = 0x{val:08X}  -> script+0x{val-VANILLA_SCRIPT_START:04X}")
    if len(script_self_refs) > 40:
        print(f"    ... and {len(script_self_refs)-40} more")
    print()

    # ── 3. Scan for stats-section refs (need +0x2C, less critical) ───────────
    stats_refs = scan_self_refs(vanilla_data,
                                VANILLA_SCRIPT_START, AREA_END,
                                VANILLA_GROUP_OFFSET, VANILLA_SCRIPT_START,
                                "script->stats")
    print(f"  Found {len(stats_refs)} pointers from script area into stats [+0x{MIDDLE_EXPANSION:02X} needed]:")
    for off, val in stats_refs[:10]:
        print(f"    0x{off:08X} = 0x{val:08X}  -> stats+0x{val-VANILLA_GROUP_OFFSET:04X}")
    print()

    # ── 4. Root table deep dive ───────────────────────────────────────────────
    print("=" * 70)
    print("  3. PER-TYPE BLOCK CONTENT (first 64 bytes each)")
    print("=" * 70)
    for i in range(min(last_nonnull + 1, 16)):
        off = VANILLA_SCRIPT_START + i * 4
        val = struct.unpack_from('<I', vanilla_data, off)[0]
        if val != 0 and VANILLA_SCRIPT_START <= val < AREA_END:
            analyze_per_type_block(vanilla_data, val, f"root[{i}]")

    # ── 5. Compare vanilla vs expanded root table ─────────────────────────────
    if output_data is not None:
        print()
        print("=" * 70)
        print("  4. VANILLA vs EXPANDED: root table comparison")
        print(f"  Vanilla script: 0x{VANILLA_SCRIPT_START:08X}")
        new_script_start = AREA_START + 168 + 384  # 0xF7AB28
        print(f"  Expanded script: 0x{new_script_start:08X}")
        print("=" * 70)
        print()
        for i in range(20):
            v_off = VANILLA_SCRIPT_START + i * 4
            e_off = new_script_start + i * 4
            v_val = struct.unpack_from('<I', vanilla_data, v_off)[0]
            e_val = struct.unpack_from('<I', output_data, e_off)[0]
            should_be = v_val + TOTAL_EXPANSION if (VANILLA_SCRIPT_START <= v_val < AREA_END) else v_val
            ok = "OK " if (e_val == should_be or v_val == 0) else "BAD"
            if v_val != 0 or e_val != 0:
                print(f"  root[{i:2d}]: vanilla=0x{v_val:08X} expanded=0x{e_val:08X} "
                      f"should=0x{should_be:08X} [{ok}]")
        print()

    # ── 6. Summary ────────────────────────────────────────────────────────────
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    total_stale = len(script_self_refs) + len(stats_refs)
    print(f"  Total stale absolute pointers after expansion: {total_stale}")
    print(f"    - Script->script (+0x{TOTAL_EXPANSION:02X}): {len(script_self_refs)}")
    print(f"    - Script->stats  (+0x{MIDDLE_EXPANSION:02X}): {len(stats_refs)}")
    if total_stale > 0:
        print()
        print("  *** CRASH CAUSE CONFIRMED: stale absolute pointers in script area ***")
        print(f"  Fix: increment each of the {total_stale} pointer values by the appropriate amount")
    else:
        print()
        print("  No self-referential pointers found - script area uses only relative offsets")
        print("  Crash cause is elsewhere")

    return 0


if __name__ == '__main__':
    exit(main())
