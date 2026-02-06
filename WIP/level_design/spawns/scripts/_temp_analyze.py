import struct
from pathlib import Path

BLAZE = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
data = bytearray(BLAZE.read_bytes())

areas = [
    ("Cavern F1 Area1", 0xF7A97C, 3, ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"]),
    ("Cavern F1 Area2", 0xF7E1A8, 4, ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "Goblin-Leader"]),
    ("Cavern F3 Area1", 0xF86198, 4, ["Giant-Scorpion", "Giant-Bat", "Big-Viper", "Giant-Spider"]),
    ("Cavern F7 Area1", 0xF8C1C4, 3, ["Cave-Bear", "Blue-Slime", "Ogre"]),
]

for name, group_off, num, monsters in areas:
    script_start = group_off + num * 96
    region = data[script_start:script_start + 2048]
    
    print("=" * 100)
    print(f"  {name} | script at 0x{script_start:X}")
    print("=" * 100)
    
    # Find ALL type entries (type 1-15, pad=0, offset < 0x2000)
    type_entries = []
    for i in range(0, min(1024, len(region)) - 8, 4):
        entry = region[i:i+8]
        off_val = struct.unpack_from('<I', entry, 0)[0]
        type_val = entry[4]
        idx_val = entry[5]
        slot_val = entry[6]
        pad_val = entry[7]
        if type_val in range(1, 16) and pad_val == 0 and 0 < off_val < 0x2000 and idx_val < 0x30:
            type_entries.append((i, off_val, type_val, idx_val, slot_val))
    
    # Show type entries
    print(f"\n  All type entries found:")
    for i, off_val, type_val, idx_val, slot_val in type_entries:
        abs_addr = script_start + i
        note = ""
        if type_val in (6, 7) and slot_val < num:
            note = f"  <- {monsters[slot_val]}"
        print(f"    0x{abs_addr:X} (script+0x{i:03X}): off=0x{off_val:04X} type={type_val:2d} idx=0x{idx_val:02X} slot={slot_val}{note}")
    
    # For each monster-type entry (type 6 or 7), dump what's at the target
    print(f"\n  === DATA AT MONSTER TYPE ENTRY TARGETS ===")
    for i, off_val, type_val, idx_val, slot_val in type_entries:
        if type_val not in (6, 7):
            continue
        if slot_val >= num:
            continue
            
        target_abs = script_start + off_val
        # Dump 128 bytes at target
        target_data = data[target_abs:target_abs + 128]
        
        print(f"\n  --- {monsters[slot_val]} (slot {slot_val}, type={type_val}, idx=0x{idx_val:02X}) ---")
        print(f"  Target: script+0x{off_val:04X} = abs 0x{target_abs:X}")
        
        for j in range(0, min(128, len(target_data)), 8):
            chunk = target_data[j:j+8]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            # int16 interpretation
            i16s = []
            for k in range(0, len(chunk), 2):
                if k + 2 <= len(chunk):
                    i16s.append(struct.unpack_from('<h', chunk, k)[0])
            i16_str = ' '.join(f'{v:6d}' for v in i16s)
            print(f"    +{j:02X}: {hex_str:<24s} | i16: {i16_str}")
    
    # Also dump the spawn commands (data between type entries and first FF block)
    # Find all FF FF FF FF in first 1024 bytes
    print(f"\n  === SPAWN COMMAND BLOCKS (FF-terminated) ===")
    ff_blocks = []
    j = 0
    while j < min(1536, len(region)) - 4:
        if region[j:j+4] == b'\xff\xff\xff\xff':
            ff_blocks.append(j)
            j += 4
        else:
            j += 1
    
    # Parse blocks between consecutive FF terminators
    if ff_blocks:
        # Data before first FF
        if ff_blocks[0] > 0:
            # Find where meaningful data starts (after type entries)
            last_type_end = 0
            for ti, off_val, type_val, idx_val, slot_val in type_entries:
                last_type_end = max(last_type_end, ti + 8)
            
            pre_ff = region[last_type_end:ff_blocks[0]]
            if any(b != 0 for b in pre_ff):
                print(f"    Data between type entries and first FF (script+0x{last_type_end:03X} to +0x{ff_blocks[0]:03X}, {len(pre_ff)} bytes):")
                for k in range(0, len(pre_ff), 16):
                    chunk = pre_ff[k:k+16]
                    hex_str = ' '.join(f'{b:02X}' for b in chunk)
                    print(f"      +{last_type_end+k:03X}: {hex_str}")
        
        # Show each FF-terminated block with some context before it
        for bi in range(len(ff_blocks)):
            ff_pos = ff_blocks[bi]
            # Block start: after previous FF+8, or after type entries
            if bi > 0:
                block_start = ff_blocks[bi-1] + 8
            else:
                block_start = max(0, ff_pos - 32)  # just show 32 bytes before first FF
            
            block_data = region[block_start:ff_pos + 8]  # include FF + 4 bytes after
            
            # After FF, next 4 bytes
            after_ff = region[ff_pos:ff_pos+8] if ff_pos + 8 <= len(region) else b''
            
            print(f"\n    Block {bi} ending at script+0x{ff_pos:03X}:")
            for k in range(0, len(block_data), 8):
                chunk = block_data[k:k+8]
                abs_k = script_start + block_start + k
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                # Check for coordinates (int16 triples)
                i16s = []
                for m in range(0, len(chunk), 2):
                    if m + 2 <= len(chunk):
                        i16s.append(struct.unpack_from('<h', chunk, m)[0])
                i16_str = ' '.join(f'{v:6d}' for v in i16s)
                print(f"      0x{abs_k:X}: {hex_str:<24s} | {i16_str}")
            
            if bi >= 20:
                print(f"    ... (showing first 20 blocks of {len(ff_blocks)})")
                break
    
    print()

print("\n\n=== CROSS-AREA COMPARISON: Same monster in different areas ===")
print("Comparing Lv20.Goblin and Giant-Bat which appear in both F1-Area1 and F1-Area2\n")

# Extract type-7 target data for specific monsters
def get_type7_target(data, group_off, num, slot):
    script_start = group_off + num * 96
    region = data[script_start:script_start + 2048]
    for i in range(0, min(1024, len(region)) - 8, 4):
        entry = region[i:i+8]
        off_val = struct.unpack_from('<I', entry, 0)[0]
        type_val = entry[4]
        slot_val = entry[6]
        pad_val = entry[7]
        if type_val in (6, 7) and pad_val == 0 and slot_val == slot and 0 < off_val < 0x2000:
            target_abs = script_start + off_val
            return data[target_abs:target_abs + 128]
    return None

# Goblin is slot 0 in both Area1 and Area2
gob_a1 = get_type7_target(data, 0xF7A97C, 3, 0)
gob_a2 = get_type7_target(data, 0xF7E1A8, 4, 0)

if gob_a1 and gob_a2:
    print("  Lv20.Goblin - Area1 type-7 target:")
    print(f"    {gob_a1[:64].hex()}")
    print("  Lv20.Goblin - Area2 type-7 target:")
    print(f"    {gob_a2[:64].hex()}")
    print(f"  Same? {gob_a1[:64] == gob_a2[:64]}")

# Bat is slot 2 in Area1, slot 2 in Area2
bat_a1 = get_type7_target(data, 0xF7A97C, 3, 2)
bat_a2 = get_type7_target(data, 0xF7E1A8, 4, 2)

if bat_a1 and bat_a2:
    print("\n  Giant-Bat - Area1 type-7 target:")
    print(f"    {bat_a1[:64].hex()}")
    print("  Giant-Bat - Area2 type-7 target:")
    print(f"    {bat_a2[:64].hex()}")
    print(f"  Same? {bat_a1[:64] == bat_a2[:64]}")
