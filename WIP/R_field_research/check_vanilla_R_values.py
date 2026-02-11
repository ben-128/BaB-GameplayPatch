#!/usr/bin/env python3
"""
Check R values in vanilla BLAZE.ALL across multiple zones.

Compares assignment entries for:
- Cavern F1 (already tested)
- Forest F1
- Castle F1
- Valley F1

To determine if R=0 is universal in vanilla or zone-specific.
"""

from pathlib import Path

VANILLA_BLAZE = Path("vanilla_BLAZE.ALL")

# Assignment entry offsets from JSON files
ZONES = {
    "Cavern F1": {
        "offsets": [0xF7A964, 0xF7A96C, 0xF7A974],  # Goblin, Shaman, Bat
        "monsters": ["Goblin", "Shaman", "Bat"]
    },
    "Forest F1": {
        "offsets": [0x148C154, 0x148C15C, 0x148C164],  # Kobold, Giant-Beetle, Giant-Ant
        "monsters": ["Kobold", "Giant-Beetle", "Giant-Ant"]
    },
    "Castle F1": {
        "offsets": [0x23FF19C, 0x23FF1A4, 0x23FF1AC],  # Zombie, Harpy, Wolf
        "monsters": ["Zombie", "Harpy", "Wolf"]
    },
    "Valley F1": {
        "offsets": [0x25D0954, 0x25D095C, 0x25D0964],  # Snow-Bear, Winter-Wolf, Hippogriff
        "monsters": ["Snow-Bear", "Winter-Wolf", "Hippogriff"]
    }
}

def main():
    print("Vanilla R Value Checker")
    print("=" * 70)
    print()

    if not VANILLA_BLAZE.exists():
        print(f"ERROR: {VANILLA_BLAZE} not found")
        print()
        print("Run: py -3 extract_vanilla_blaze.py")
        return

    with open(VANILLA_BLAZE, 'rb') as f:
        vanilla_data = f.read()

    print(f"Loaded vanilla BLAZE.ALL: {len(vanilla_data):,} bytes")
    print()

    # Check each zone
    for zone_name, zone_info in ZONES.items():
        print(f"{zone_name}")
        print("-" * 50)

        for i, offset in enumerate(zone_info["offsets"]):
            monster = zone_info["monsters"][i]

            # Read 8-byte assignment entry
            entry = vanilla_data[offset:offset+8]

            # Parse entry structure
            # [0]=model_slot, [1]=L, [2]=tex_variant, [3]=0x00,
            # [4]=unique_slot, [5]=R, [6]=0x00, [7]=flag
            model_slot = entry[0]
            L = entry[1]
            tex_variant = entry[2]
            unique_slot = entry[4]
            R = entry[5]
            flag = entry[7]

            hex_entry = ' '.join(f'{b:02X}' for b in entry)

            print(f"  {monster:15} offset={hex(offset)}")
            print(f"    Raw: {hex_entry}")
            print(f"    L={L:3}, R={R:3}, flag=0x{flag:02X}")

            # Check if this looks like a valid assignment entry
            if flag == 0x40:
                print(f"    -> Has 0x40 flag (valid entry)")
            elif all(b == 0 for b in entry):
                print(f"    -> All zeros (no entry)")
            else:
                print(f"    -> Non-standard (partial data?)")

            print()

        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    all_R_values = []
    has_0x40_flags = []

    for zone_name, zone_info in ZONES.items():
        zone_R_values = []
        zone_has_flags = []

        for offset in zone_info["offsets"]:
            entry = vanilla_data[offset:offset+8]
            R = entry[5]
            flag = entry[7]

            zone_R_values.append(R)
            zone_has_flags.append(flag == 0x40)

        all_R_values.extend(zone_R_values)
        has_0x40_flags.extend(zone_has_flags)

        R_str = ','.join(f'{r:2}' for r in zone_R_values)
        flags_str = "YES" if any(zone_has_flags) else "NO"

        print(f"{zone_name:15} R=[{R_str}]  0x40 flags: {flags_str}")

    print()

    # Check if R=0 is universal
    all_zero = all(r == 0 for r in all_R_values)
    any_flags = any(has_0x40_flags)

    print("CONCLUSION:")
    if all_zero and not any_flags:
        print("  - All R values = 0 in vanilla")
        print("  - No 0x40 flags found")
        print("  -> R=0 is UNIVERSAL in vanilla (no assignment entries exist)")
    elif all_zero and any_flags:
        print("  - All R values = 0")
        print("  - BUT some 0x40 flags found")
        print("  -> Unexpected! Flags exist but R=0")
    elif not all_zero:
        print(f"  - R values vary: min={min(all_R_values)}, max={max(all_R_values)}")
        print(f"  - 0x40 flags: {'YES' if any_flags else 'NO'}")
        print("  -> R is NOT always 0 in vanilla")
    else:
        print("  - Unknown pattern")

if __name__ == '__main__':
    main()
