#!/usr/bin/env python3
"""
Compare script areas between Area 1 and Area 2 (both have Goblin as slot 0).

If Goblin has the same AI in both areas, the AI-related data should match.
Area-specific data (spawn positions) will differ.

By finding what's IDENTICAL for the same monster across areas, we can
identify potential AI data.

Also: dump the first 128 bytes of script area (right after 96-byte entries)
which haven't been analyzed yet.
"""

import struct
from pathlib import Path

BLAZE = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
data = bytearray(BLAZE.read_bytes())

AREAS = {
    'Area1': {
        'group_offset': 0xF7A97C,
        'num': 3,
        'monsters': ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
    },
    'Area2': {
        'group_offset': 0xF7E1A8,
        'num': 4,
        'monsters': ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "Goblin-Leader"],
    },
}

print("=" * 80)
print("  COMPARE SCRIPT AREAS: Area 1 vs Area 2")
print("=" * 80)

for name, area in AREAS.items():
    goff = area['group_offset']
    num = area['num']
    script_start = goff + num * 96

    print(f"\n  {name}: group=0x{goff:X}, script=0x{script_start:X}, {num} monsters")

    # Dump first 128 bytes of script area (uint32 pairs)
    print(f"\n  First 128 bytes of script area:")
    for i in range(0, 128, 8):
        chunk = data[script_start+i:script_start+i+8]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        v1 = struct.unpack_from('<I', chunk, 0)[0]
        v2 = struct.unpack_from('<I', chunk, 4)[0]
        abs_addr = script_start + i
        print(f"    0x{abs_addr:X} (+{i:03X}): {hex_str}  = ({v1:#010x}, {v2:#010x})")

    # Find all type entries
    print(f"\n  Type entries:")
    script_data = data[script_start:script_start + 0x300]
    for i in range(0, len(script_data) - 8, 4):
        val_off = struct.unpack_from('<I', script_data, i)[0]
        type_byte = script_data[i+4]
        idx_byte = script_data[i+5]
        slot_byte = script_data[i+6]
        zero_byte = script_data[i+7]
        if type_byte in (4, 5, 6, 7, 8, 12, 14) and zero_byte == 0 and 0 < val_off < 0x8000:
            abs_off = script_start + i
            monster = ""
            if type_byte == 7 and slot_byte < num:
                monster = f"  <- {area['monsters'][slot_byte]}"
            print(f"    0x{abs_off:X} (+{i:03X}): off=0x{val_off:04X} "
                  f"type={type_byte:2d} idx=0x{idx_byte:02X} slot={slot_byte}{monster}")

    # Extract data at type-7 targets for each monster
    print(f"\n  Type-7 target data per monster:")
    for i in range(0, len(script_data) - 8, 4):
        val_off = struct.unpack_from('<I', script_data, i)[0]
        type_byte = script_data[i+4]
        slot_byte = script_data[i+6]
        zero_byte = script_data[i+7]
        if type_byte == 7 and zero_byte == 0 and slot_byte < num and 0 < val_off < 0x8000:
            target_abs = script_start + val_off
            target_data = data[target_abs:target_abs+32]
            hex_str = ' '.join(f'{b:02X}' for b in target_data)
            print(f"    {area['monsters'][slot_byte]} (slot {slot_byte}): "
                  f"target=0x{target_abs:X} (+{val_off:04X})")
            print(f"      {hex_str}")

# Now compare the INITIAL SPAWN RECORDS (blocks 0-3)
# These contain per-slot initial data
print(f"\n{'='*80}")
print("  COMPARE: Initial spawn records (blocks 0-3)")
print(f"{'='*80}")

for name, area in AREAS.items():
    goff = area['group_offset']
    num = area['num']
    script_start = goff + num * 96

    print(f"\n  {name}:")

    # Blocks 0-3 start around script+0x080
    # Find them by scanning for FFFFFFFFFFFF + slot_byte
    region = data[script_start + 0x040:script_start + 0x180]
    base = script_start + 0x040

    for i in range(len(region) - 8):
        if region[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
            slot = struct.unpack_from('<H', region, i+6)[0]
            if slot < num + 2:
                # Show the record (go back ~28 bytes to show full record)
                rec_start = max(0, i - 28)
                rec = region[rec_start:i+8]
                abs_addr = base + rec_start
                hex_str = ' '.join(f'{b:02X}' for b in rec)
                print(f"    Slot {slot} at 0x{abs_addr:X}: {hex_str}")

# Compare type-7 target data for SAME monsters
print(f"\n{'='*80}")
print("  COMPARE: Type-7 target data for same monsters across areas")
print(f"{'='*80}")

shared_monsters = ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]
for monster in shared_monsters:
    print(f"\n  {monster}:")
    for name, area in AREAS.items():
        goff = area['group_offset']
        num = area['num']
        script_start = goff + num * 96

        # Find type-7 entry for this monster
        slot = area['monsters'].index(monster) if monster in area['monsters'] else -1
        if slot < 0:
            continue

        script_data = data[script_start:script_start + 0x300]
        for i in range(0, len(script_data) - 8, 4):
            val_off = struct.unpack_from('<I', script_data, i)[0]
            type_byte = script_data[i+4]
            slot_byte = script_data[i+6]
            zero_byte = script_data[i+7]
            if type_byte == 7 and zero_byte == 0 and slot_byte == slot and 0 < val_off < 0x8000:
                target_abs = script_start + val_off
                # Show 64 bytes at target
                target_data = data[target_abs:target_abs+64]
                hex_lines = []
                for j in range(0, 64, 16):
                    line = ' '.join(f'{b:02X}' for b in target_data[j:j+16])
                    hex_lines.append(line)
                print(f"    {name} (slot {slot}, target=0x{target_abs:X}):")
                for line in hex_lines:
                    print(f"      {line}")
                break

# Look at what's BETWEEN group entries and script start
# The script area starts with some header data
print(f"\n{'='*80}")
print("  FIRST 48 BYTES of each script area (the mystery header)")
print(f"{'='*80}")

for name, area in AREAS.items():
    goff = area['group_offset']
    num = area['num']
    script_start = goff + num * 96

    header = data[script_start:script_start+48]
    print(f"\n  {name} (script at 0x{script_start:X}):")
    for i in range(0, 48, 8):
        chunk = header[i:i+8]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        u32_1 = struct.unpack_from('<I', chunk, 0)[0]
        u32_2 = struct.unpack_from('<I', chunk, 4)[0]
        print(f"    +{i:03X}: {hex_str}  = ({u32_1:#010x}, {u32_2:#010x})")

# Compare the config blocks (around script+0x8F0)
print(f"\n{'='*80}")
print("  COMPARE: Config blocks (near script+0x8F0)")
print(f"{'='*80}")

for name, area in AREAS.items():
    goff = area['group_offset']
    num = area['num']
    script_start = goff + num * 96

    print(f"\n  {name}:")
    # Search for the pattern 08 00 FF 05 (config block marker)
    region = data[script_start + 0x800:script_start + 0xA00]
    for i in range(len(region) - 8):
        if region[i] == 0x08 and region[i+2] == 0xFF and region[i+3] == 0x05:
            abs_addr = script_start + 0x800 + i
            ctx = region[max(0,i-16):min(len(region),i+32)]
            hex_str = ' '.join(f'{b:02X}' for b in ctx)
            print(f"    Config at 0x{abs_addr:X}: {hex_str}")
            break
    else:
        # Try wider search
        region = data[script_start + 0x600:script_start + 0x1200]
        for i in range(len(region) - 8):
            if region[i] == 0x08 and region[i+2] == 0xFF and region[i+3] == 0x05:
                abs_addr = script_start + 0x600 + i
                ctx = region[max(0,i-16):min(len(region),i+48)]
                hex_str = ' '.join(f'{b:02X}' for b in ctx)
                print(f"    Config at 0x{abs_addr:X}: {hex_str}")
                break

print(f"\n{'='*80}")
print("  DONE")
print(f"{'='*80}")
