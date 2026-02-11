#!/usr/bin/env python3
"""
Analyze ePSXe savestate to find chest timer in RAM and verify patches.

This script helps answer:
1. Where is the timer stored in RAM? (entity+0x10, +0x12, or +0x14?)
2. What value does it have? (1000, or patched value 65535?)
3. Are our overlay patches loaded in RAM or ignored?

ePSXe savestate format: gzip compressed, RAM at offset 0x1BA (2MB).
"""

import gzip
import struct
from pathlib import Path


def decompress_savestate(savestate_path):
    """Decompress ePSXe savestate and extract RAM."""
    with gzip.open(savestate_path, 'rb') as f:
        data = f.read()

    # RAM starts at offset 0x1BA in decompressed data
    ram_offset = 0x1BA
    ram_size = 2 * 1024 * 1024  # 2MB

    if len(data) < ram_offset + ram_size:
        raise ValueError(f"Savestate too small: {len(data)} bytes")

    ram = data[ram_offset:ram_offset + ram_size]
    print(f"Savestate: {savestate_path.name}")
    print(f"  Decompressed: {len(data):,} bytes")
    print(f"  RAM extracted: {len(ram):,} bytes (2MB)")
    return ram


def search_timer_values(ram, target_values):
    """Search RAM for timer values (as halfwords)."""
    matches = {}

    for value in target_values:
        value_name = f"{value} (0x{value:04X})"
        matches[value_name] = []

        for i in range(0, len(ram) - 2, 2):
            hw = struct.unpack_from('<H', ram, i)[0]
            if hw == value:
                ram_addr = 0x80000000 + i
                matches[value_name].append(ram_addr)

    return matches


def check_overlay_patches(ram):
    """Check if overlay code patches (entity+0x0012 init) are present in RAM."""
    print("\nChecking if v12 patches are loaded in RAM:")
    print("  Searching for: addiu $v0, $zero, 0xFFFF (patched)")
    print("  vs original:   addiu $v0, $zero, 0x03E8 (vanilla)")
    print()

    # Pattern: addiu $v0, $zero, immediate
    # 0x240203E8 = addiu $v0, $zero, 0x3E8 (original)
    # 0x2402FFFF = addiu $v0, $zero, 0xFFFF (patched for infinite)

    original = 0x240203E8
    patched = 0x2402FFFF

    original_count = 0
    patched_count = 0

    for i in range(0, len(ram) - 4, 4):
        word = struct.unpack_from('<I', ram, i)[0]

        if word == original:
            ram_addr = 0x80000000 + i
            original_count += 1
            if original_count <= 5:
                print(f"  ORIGINAL found at RAM 0x{ram_addr:08X}")

        elif word == patched:
            ram_addr = 0x80000000 + i
            patched_count += 1
            if patched_count <= 5:
                print(f"  PATCHED found at RAM 0x{ram_addr:08X}")

    print()
    print(f"  Total ORIGINAL instructions: {original_count}")
    print(f"  Total PATCHED instructions: {patched_count}")
    print()

    if patched_count == 0:
        print("  ⚠️  NO PATCHED CODE IN RAM!")
        print("  → Overlay patches NOT loaded, or reloaded from vanilla source")
    else:
        print("  ✓ Patched code IS present in RAM")


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.parent

    print("="*70)
    print("Chest Timer Savestate Analysis")
    print("="*70)
    print()

    # Ask user for savestate path
    print("Place your ePSXe savestate (*.gpz) in Data/LootTimer/")
    print("The savestate should be taken RIGHT AFTER killing a monster,")
    print("when a chest appears (timer should be ~1000 or near max).")
    print()

    savestate_files = list(script_dir.glob("*.gpz"))

    if not savestate_files:
        print("No .gpz files found in Data/LootTimer/")
        print("Please copy your ePSXe savestate here and run again.")
        return

    print(f"Found {len(savestate_files)} savestate(s):")
    for i, f in enumerate(savestate_files):
        print(f"  [{i+1}] {f.name}")

    if len(savestate_files) == 1:
        savestate_path = savestate_files[0]
    else:
        choice = int(input("\nSelect savestate number: ")) - 1
        savestate_path = savestate_files[choice]

    print()
    print("="*70)

    # Decompress and extract RAM
    ram = decompress_savestate(savestate_path)
    print()

    # Search for common timer values
    print("Searching for timer values in RAM:")
    print("  1000 (0x03E8) - vanilla timer")
    print("  65535 (0xFFFF) - patched timer (infinite)")
    print("  500-999 - partially decremented timer")
    print()

    target_values = [1000, 65535, 999, 950, 900, 850, 800, 750, 700, 650, 600, 550, 500]
    matches = search_timer_values(ram, target_values)

    for value_name, addrs in matches.items():
        if addrs:
            print(f"\n{value_name}: {len(addrs)} occurrences")
            for addr in addrs[:10]:  # Show first 10
                print(f"  RAM 0x{addr:08X}")
            if len(addrs) > 10:
                print(f"  ... and {len(addrs) - 10} more")

    # Check if overlay patches are in RAM
    check_overlay_patches(ram)

    print("="*70)
    print("Analysis complete!")
    print()
    print("Interpretation:")
    print("  • If patched values (0xFFFF) are NOT in RAM → overlay reload confirmed")
    print("  • If timer values are at expected offsets → can verify entity structure")
    print("  • If timer values are scattered → might be in data tables")
    print("="*70)


if __name__ == '__main__':
    main()
