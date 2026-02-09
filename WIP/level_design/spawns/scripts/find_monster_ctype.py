#!/usr/bin/env python3
"""
Find what creature_type value monsters actually use in the combat dispatch system.

The dispatch code at 0x80024E14:
  lbu   $a1, 693($s3)           ; entity+0x2B5 = creature_type
  lui   $v0, 0x8005
  lw    $v0, 0x490C($v0)        ; global = *(0x8005490C)
  andi  $a0, $a1, 0xFFFF
  lw    $v1, 0x9C($v0)          ; ptr_array = global+0x9C
  sll   $v0, $a0, 2             ; creature_type * 4
  addu  $v1, $v0, $v1
  lw    $s5, 0($v1)             ; action_entries_base = ptr_array[creature_type]

So $s3 is the entity base, and we need to find structs where $s3+0x2B5 contains
a creature_type byte (0-79).

Strategy:
1. The entity struct must be >693 bytes (at least 694 bytes).
2. Search for the known monster config pointers in RAM to find entity structs.
3. Read the creature_type at +0x2B5 from each found struct.
4. Also check what's at the battle slot table and entity management region.
"""

import gzip
import struct
from pathlib import Path

SAVESTATE = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\combat\SLES_008.45.000")
BLAZE_ALL = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
EXE_PATH  = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")

RAM_BASE = 0x80000000
RAM_SIZE = 0x200000

def ram_idx(addr):
    return addr - RAM_BASE

def read_u32(buf, addr):
    return struct.unpack_from('<I', buf, ram_idx(addr))[0]

def read_u16(buf, addr):
    return struct.unpack_from('<H', buf, ram_idx(addr))[0]

def read_u8(buf, addr):
    return buf[ram_idx(addr)]

def is_ram_ptr(val):
    return RAM_BASE <= val < RAM_BASE + RAM_SIZE

def decode_ascii(data, max_len=32):
    result = []
    for b in data[:max_len]:
        if b == 0:
            break
        if 32 <= b < 127:
            result.append(chr(b))
        else:
            result.append('.')
    return ''.join(result) if result else ""

def decode_name_field(data16):
    """Decode two null-separated names from 16 bytes."""
    parts = []
    current = []
    for b in data16:
        if b == 0:
            if current:
                parts.append(''.join(current))
                current = []
        elif 32 <= b < 127:
            current.append(chr(b))
        else:
            current.append('.')
    if current:
        parts.append(''.join(current))
    return parts[0] if parts else "", parts[1] if len(parts) > 1 else ""


def main():
    raw = gzip.open(str(SAVESTATE), 'rb').read()
    ram = bytearray(raw[0x1BA : 0x1BA + RAM_SIZE])
    blaze = bytearray(Path(BLAZE_ALL).read_bytes())
    exe = bytearray(Path(EXE_PATH).read_bytes())

    game_state_ptr = read_u32(ram, 0x8005490C)
    ptr_array_addr = read_u32(ram, game_state_ptr + 0x9C)

    print("=" * 95)
    print("  FINDING MONSTER creature_type VALUES")
    print("=" * 95)
    print(f"  Game state: 0x{game_state_ptr:08X}")
    print(f"  Pointer array: 0x{ptr_array_addr:08X}")

    # Read all 80 pointer array entries
    ptr_array = []
    for i in range(80):
        ptr = read_u32(ram, ptr_array_addr + i * 4)
        ptr_array.append(ptr)

    # =========================================================
    # SECTION 1: Dump entity management region
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 1: Entity Management Region (0x800B4000-0x800B5B00)")
    print("=" * 95)

    # Scan for pointers into the overlay region (0x800A0000-0x800C0000)
    # These mark entity structs
    region_start = 0x800B4000
    region_end = 0x800B5B00

    print(f"\n  Scanning for overlay data pointers (0x800Axxxx):")
    overlay_ptr_locs = []
    for addr in range(region_start, region_end, 4):
        val = read_u32(ram, addr)
        if 0x800A0000 <= val < 0x800B0000:
            overlay_ptr_locs.append((addr, val))

    # Group by proximity (consecutive pointers = same entity)
    groups = []
    current_group = []
    for addr, val in overlay_ptr_locs:
        if current_group and addr - current_group[-1][0] > 0x100:
            groups.append(current_group)
            current_group = []
        current_group.append((addr, val))
    if current_group:
        groups.append(current_group)

    for gi, group in enumerate(groups):
        first_addr = group[0][0]
        last_addr = group[-1][0]
        print(f"\n  Entity group {gi} at 0x{first_addr:08X}-0x{last_addr:08X} ({len(group)} ptrs):")
        for addr, val in group[:8]:
            print(f"    0x{addr:08X}: 0x{val:08X}")
        if len(group) > 8:
            print(f"    ... ({len(group) - 8} more)")

    # =========================================================
    # SECTION 2: Search for known monster config pointers
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 2: Search for monster config pointers in entity structs")
    print("=" * 95)

    # Known monster config data pointers from previous research
    monster_config_ptrs = [0x800AA708, 0x800AA728, 0x800AB0C8, 0x800AADBC]
    player_config_ptrs = [0x800A91E8, 0x800A9320, 0x800A93BC]

    all_config_ptrs = monster_config_ptrs + player_config_ptrs
    labels = {
        0x800AA708: "Monster-config-1",
        0x800AA728: "Monster-config-2",
        0x800AB0C8: "Monster-config-3",
        0x800AADBC: "Monster-config-4",
        0x800A91E8: "Player-config-1",
        0x800A9320: "Player-config-2",
        0x800A93BC: "Player-config-3",
    }

    # Search entire RAM for these pointers
    print(f"\n  Searching RAM 0x800A0000-0x800C0000 for config pointers:")
    config_locations = {}  # ptr_value -> list of (location, offset_in_struct)

    search_start = 0x800A0000
    search_end = 0x800C0000
    for addr in range(search_start, search_end, 4):
        val = read_u32(ram, addr)
        if val in all_config_ptrs:
            label = labels.get(val, "???")
            config_locations.setdefault(val, []).append(addr)

    for ptr_val in all_config_ptrs:
        locs = config_locations.get(ptr_val, [])
        label = labels.get(ptr_val, "???")
        if locs:
            print(f"\n  {label} (0x{ptr_val:08X}) found at {len(locs)} locations:")
            for loc in locs:
                print(f"    0x{loc:08X}")
        else:
            print(f"\n  {label} (0x{ptr_val:08X}) NOT FOUND in search range")

    # =========================================================
    # SECTION 3: For each config pointer location, try to find entity base
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 3: Find entity struct bases from config pointer locations")
    print("=" * 95)

    # The config pointer is at entity+0x70 (from docs).
    # So entity_base = config_ptr_location - 0x70.
    # Then creature_type = entity_base + 0x2B5.

    entity_bases = []
    for ptr_val, locs in config_locations.items():
        label = labels.get(ptr_val, "???")
        for loc in locs:
            # Try offset 0x70
            base_70 = loc - 0x70
            # Also try other common offsets
            for field_off, field_name in [(0x70, "+0x70"), (0x04, "+0x04"), (0x08, "+0x08"),
                                           (0x00, "+0x00"), (0x7C, "+0x7C")]:
                base = loc - field_off
                if base < RAM_BASE or base + 0x300 > RAM_BASE + RAM_SIZE:
                    continue
                # Read creature_type candidate at base+0x2B5
                ctype = read_u8(ram, base + 0x2B5)
                entity_bases.append({
                    'base': base,
                    'config_ptr': ptr_val,
                    'config_loc': loc,
                    'field_off': field_off,
                    'field_name': field_name,
                    'creature_type': ctype,
                    'label': label,
                })

    # Show results grouped by base
    seen_bases = set()
    print(f"\n  Trying entity_base = config_ptr_location - field_offset:")
    print(f"  Then reading creature_type at entity_base + 0x2B5 (offset 693):")
    print()
    for eb in entity_bases:
        if eb['base'] in seen_bases:
            continue
        seen_bases.add(eb['base'])
        base = eb['base']
        ctype = eb['creature_type']

        # Also read some context around 0x2B5
        ctx_start = base + 0x2B0
        if ctx_start + 16 <= RAM_BASE + RAM_SIZE:
            ctx = ram[ram_idx(ctx_start):ram_idx(ctx_start) + 16]
            ctx_hex = ' '.join(f'{b:02X}' for b in ctx)
        else:
            ctx_hex = "out of range"

        # Check if creature_type maps to a valid pointer array entry
        ptr_entry = ptr_array[ctype] if ctype < 80 else 0
        ptr_info = ""
        if ptr_entry != 0 and is_ram_ptr(ptr_entry):
            target = ram[ram_idx(ptr_entry):ram_idx(ptr_entry) + 16]
            name = decode_ascii(target)
            ptr_info = f"-> \"{name[:20]}\""

        print(f"  base=0x{base:08X} (config at {eb['field_name']}=0x{eb['config_loc']:08X} [{eb['label']}])")
        print(f"    creature_type(+0x2B5) = {ctype}  ptr_array[{ctype}] = 0x{ptr_entry:08X} {ptr_info}")
        print(f"    bytes at +0x2B0: [{ctx_hex}]")

    # =========================================================
    # SECTION 4: Brute-force search for creature_type in entity region
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 4: Brute-force search for entities with valid creature_type")
    print("=" * 95)

    # Search the entity management region for structs where:
    # - base+0x2B5 is a small value (0-7 for player types, or some value for monsters)
    # - base has a valid pointer at +0x70 (config pointer into overlay)

    # We need large structs. Let's search with fine granularity.
    search_region_start = 0x800B0000
    search_region_end = 0x800C0000

    print(f"\n  Searching 0x{search_region_start:08X}-0x{search_region_end:08X}")
    print(f"  Criteria: base+0x70 is overlay ptr AND base+0x2B5 < 80")
    print()

    candidates = []
    for base in range(search_region_start, search_region_end - 0x2C0, 4):
        # Check if base+0x70 contains an overlay pointer
        ptr_70 = read_u32(ram, base + 0x70)
        if not (0x800A0000 <= ptr_70 < 0x800C0000):
            continue

        # Check creature_type
        ctype = read_u8(ram, base + 0x2B5)
        if ctype >= 80:
            continue

        # Additional validation: check base+0x00 looks reasonable
        word0 = read_u32(ram, base)
        # Skip if base looks like garbage
        if word0 == 0 and read_u32(ram, base + 4) == 0 and read_u32(ram, base + 8) == 0:
            continue

        candidates.append({
            'base': base,
            'ptr_70': ptr_70,
            'creature_type': ctype,
            'word0': word0,
        })

    print(f"  Found {len(candidates)} candidates")

    # Show unique (base, creature_type) pairs, grouped by creature_type
    by_ctype = {}
    for c in candidates:
        by_ctype.setdefault(c['creature_type'], []).append(c)

    for ctype in sorted(by_ctype.keys()):
        cands = by_ctype[ctype]
        ptr_entry = ptr_array[ctype] if ctype < 80 else 0
        ptr_info = ""
        if ptr_entry != 0 and is_ram_ptr(ptr_entry):
            target = ram[ram_idx(ptr_entry):ram_idx(ptr_entry) + 16]
            name, typename = decode_name_field(target)
            ptr_info = f"-> \"{name}\""
            if typename:
                ptr_info += f" ({typename})"

        print(f"\n  creature_type={ctype} ({len(cands)} entities) ptr_array[{ctype}]=0x{ptr_entry:08X} {ptr_info}")
        for c in cands:
            # Read a few key fields for context
            base = c['base']
            # Read 16 bytes at +0x2B0 for context
            ctx = ram[ram_idx(base + 0x2B0):ram_idx(base + 0x2B0) + 16]

            # Check if this looks like a player or monster
            # Players are at 0x80054698 (stride 0x9C) - but these are small structs
            # The large struct must be elsewhere

            # Read nearby data for identification
            # Check if there's a name string nearby
            name_candidates = []
            for off in [0x00, 0x04, 0x08, 0x10, 0x20, 0x2A0, 0x2A8, 0x2B0, 0x2C0, 0x2C8]:
                if base + off + 16 <= RAM_BASE + RAM_SIZE:
                    data = ram[ram_idx(base + off):ram_idx(base + off) + 16]
                    txt = decode_ascii(data)
                    if txt and len(txt) >= 3 and all(c.isalnum() or c in ' -_.' for c in txt):
                        name_candidates.append((off, txt))

            print(f"    base=0x{base:08X}  ptr@+0x70=0x{c['ptr_70']:08X}  "
                  f"ctx@+0x2B0=[{ctx.hex()}]")
            for off, txt in name_candidates:
                print(f"      name@+0x{off:03X}: \"{txt}\"")

    # =========================================================
    # SECTION 5: Examine the dispatch code more - what sets $s3?
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 5: Trace $s3 (entity pointer) origin in dispatch code")
    print("=" * 95)

    # Look backwards from 0x80024E14 to find where $s3 is set
    # The dispatch function might be called with $s3 already set from calling code
    # Let's look at the function that calls the dispatch

    # First find the function prologue (sw $ra, ...)
    # Search backwards from 0x80024E14 for addiu $sp, $sp, -N
    exe_off_base = 0x80024E14 - 0x80010000 + 0x800

    REGS = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
             '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
             '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
             '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

    def disasm(word, addr):
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        rd = (word >> 11) & 0x1F
        shamt = (word >> 6) & 0x1F
        funct = word & 0x3F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000

        if opcode == 0:
            if funct == 0x21: return f"addu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
            if funct == 0x00: return f"sll     {REGS[rd]},{REGS[rt]},{shamt}"
            if funct == 0x25: return f"or      {REGS[rd]},{REGS[rs]},{REGS[rt]}"
            if funct == 0x09: return f"jalr    {REGS[rd]},{REGS[rs]}"
            if funct == 0x08: return f"jr      {REGS[rs]}"
            if funct == 0x2B: return f"sltu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
            if funct == 0x2A: return f"slt     {REGS[rd]},{REGS[rs]},{REGS[rt]}"
            if funct == 0x23: return f"subu    {REGS[rd]},{REGS[rs]},{REGS[rt]}"
        elif opcode == 0x23: return f"lw      {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x24: return f"lbu     {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x25: return f"lhu     {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x20: return f"lb      {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x21: return f"lh      {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x28: return f"sb      {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x29: return f"sh      {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x2B: return f"sw      {REGS[rt]},{simm}({REGS[rs]})"
        elif opcode == 0x0F: return f"lui     {REGS[rt]},0x{imm:04X}"
        elif opcode == 0x09: return f"addiu   {REGS[rt]},{REGS[rs]},{simm}"
        elif opcode == 0x0D: return f"ori     {REGS[rt]},{REGS[rs]},0x{imm:04X}"
        elif opcode == 0x0C: return f"andi    {REGS[rt]},{REGS[rs]},0x{imm:04X}"
        elif opcode == 0x0A: return f"slti    {REGS[rt]},{REGS[rs]},{simm}"
        elif opcode == 0x04:
            t = addr + 4 + (simm << 2)
            return f"beq     {REGS[rs]},{REGS[rt]},0x{t:08X}"
        elif opcode == 0x05:
            t = addr + 4 + (simm << 2)
            return f"bne     {REGS[rs]},{REGS[rt]},0x{t:08X}"
        elif opcode == 0x06:
            t = addr + 4 + (simm << 2)
            return f"blez    {REGS[rs]},0x{t:08X}"
        elif opcode == 0x07:
            t = addr + 4 + (simm << 2)
            return f"bgtz    {REGS[rs]},0x{t:08X}"
        elif opcode == 0x03:
            t = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
            return f"jal     0x{t:08X}"
        elif opcode == 0x02:
            t = (word & 0x03FFFFFF) << 2 | (addr & 0xF0000000)
            return f"j       0x{t:08X}"
        return f"0x{word:08X}"

    # Search backwards for the function prologue containing 0x80024E14
    # Look for addiu $sp, $sp, -N (opcode 0x09, rs=29, rt=29, negative imm)
    print("\n  Searching for function containing dispatch code at 0x80024E14:")
    func_start = None
    for search_addr in range(0x80024E14, 0x80024000, -4):
        off = search_addr - 0x80010000 + 0x800
        if off < 0 or off + 4 > len(exe):
            continue
        word = struct.unpack_from('<I', exe, off)[0]
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        simm = imm if imm < 0x8000 else imm - 0x10000
        # addiu $sp, $sp, -N
        if opcode == 0x09 and rs == 29 and rt == 29 and simm < 0:
            func_start = search_addr
            break

    if func_start:
        print(f"  Function starts at 0x{func_start:08X}")
        print(f"\n  Disassembly (first 60 instructions):")
        for i in range(60):
            addr = func_start + i * 4
            off = addr - 0x80010000 + 0x800
            if off < 0 or off + 4 > len(exe):
                break
            word = struct.unpack_from('<I', exe, off)[0]
            asm = disasm(word, addr)
            marker = ""
            if addr == 0x80024E14:
                marker = "  <-- dispatch creature_type read"
            # Highlight $s3 references
            if '$s3' in asm:
                marker += "  <-- $s3 ref"
            print(f"    0x{addr:08X}: {asm:44s}{marker}")
    else:
        print("  Could not find function prologue!")

    # =========================================================
    # SECTION 6: Dump battle slot table with more detail
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 6: Battle slot table at 0x800BB93C (12 entries, stride 0x9C)")
    print("=" * 95)

    battle_table = 0x800BB93C
    for slot in range(12):
        base = battle_table + slot * 0x9C
        # Read first 8 bytes to check if active
        w0 = read_u32(ram, base)
        w1 = read_u32(ram, base + 4)
        if w0 == 0 and w1 == 0:
            continue

        print(f"\n  Slot {slot} at 0x{base:08X}:")

        # Dump key fields
        for off, name in [(0x00, "word0"), (0x04, "config_ptr?"), (0x10, "render_ptr?"),
                          (0x14, "state/ID"), (0x28, "combat_flags"),
                          (0x38, "slot_index"), (0x44, "type_info"),
                          (0x48, "type_info_2"), (0x68, "color/tint"),
                          (0x70, "overlay_ptr?")]:
            if off + 4 <= 0x9C:
                val = read_u32(ram, base + off)
                extra = ""
                if is_ram_ptr(val):
                    extra = f" (RAM ptr)"
                    if val in all_config_ptrs:
                        extra = f" [{labels[val]}]"
                elif val == 0x00808080:
                    extra = " (default color)"
                print(f"    +0x{off:02X} {name:16s}: 0x{val:08X}{extra}")

        # Try reading 0x2B5 from this base (even though struct is only 0x9C)
        # This will read into the next slot, but let's see
        if base + 0x2B5 < RAM_BASE + RAM_SIZE:
            ctype_from_slot = read_u8(ram, base + 0x2B5)
            print(f"    +0x2B5 (creature_type if this were the large struct): {ctype_from_slot}")

    # =========================================================
    # SECTION 7: Examine the full region around each entity group
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 7: Detailed scan of entity management region")
    print("=" * 95)

    # The entity region 0x800B4000-0x800B5B00 is ~7KB
    # Let's find entity struct boundaries by looking for patterns

    # Scan for all config data pointers in this region
    print(f"\n  All overlay pointers (0x800Axxxx) in entity region:")
    for addr in range(0x800B4000, 0x800B5C00, 4):
        val = read_u32(ram, addr)
        if 0x800A0000 <= val < 0x800C0000:
            label = labels.get(val, "")
            # Also check what's at addr+0x2B5 - 0x70 = addr+0x245
            potential_base_if_70 = addr - 0x70
            ctype_if_70 = -1
            if potential_base_if_70 + 0x2B5 < RAM_BASE + RAM_SIZE and potential_base_if_70 >= RAM_BASE:
                ctype_if_70 = read_u8(ram, potential_base_if_70 + 0x2B5)
            print(f"    0x{addr:08X}: 0x{val:08X} {label:20s} "
                  f"(if +0x70: base=0x{potential_base_if_70:08X}, ctype@+0x2B5={ctype_if_70})")

    # =========================================================
    # SECTION 8: Alternative approach - search for $s3 value in RAM
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 8: Search for large entity structs via stride analysis")
    print("=" * 95)

    # If the combat system uses an array of large entities (>0x2B6 bytes each),
    # let's try to find them by searching for arrays of config pointers with
    # consistent stride

    # Collect all locations of any overlay data pointer
    overlay_ptr_addrs = []
    for addr in range(0x800B0000, 0x800C0000, 4):
        val = read_u32(ram, addr)
        if val in monster_config_ptrs:
            overlay_ptr_addrs.append((addr, val))

    if len(overlay_ptr_addrs) >= 2:
        print(f"\n  Monster config pointer locations ({len(overlay_ptr_addrs)} found):")
        for addr, val in overlay_ptr_addrs:
            label = labels.get(val, "???")
            print(f"    0x{addr:08X}: 0x{val:08X} ({label})")

        # Check for consistent stride between consecutive monster config ptrs
        print(f"\n  Stride analysis between consecutive pointers:")
        for i in range(1, len(overlay_ptr_addrs)):
            a1, v1 = overlay_ptr_addrs[i-1]
            a2, v2 = overlay_ptr_addrs[i]
            stride = a2 - a1
            print(f"    0x{a1:08X} -> 0x{a2:08X}: stride = 0x{stride:X} ({stride})")

    # =========================================================
    # SECTION 9: Types 4-7 detail dump + tier cross-reference
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 9: Detailed dump of types 3-7 (monster ability entries)")
    print("=" * 95)

    tier_table_ram = 0x8003C020
    for ctype in range(8):
        ptr = ptr_array[ctype]
        if ptr == 0:
            continue

        # Read tier
        tier_addr = tier_table_ram + ctype * 5
        tier = list(ram[ram_idx(tier_addr):ram_idx(tier_addr) + 5])
        max_entries = max(tier) if any(v > 0 for v in tier) else 30

        print(f"\n  --- Type {ctype}: ptr=0x{ptr:08X}, tier={tier}, max_entries={max_entries} ---")

        # Read entries
        for idx in range(min(max_entries + 2, 30)):
            entry_addr = ptr + idx * 48
            if entry_addr + 48 > RAM_BASE + RAM_SIZE:
                break
            entry = bytes(ram[ram_idx(entry_addr):ram_idx(entry_addr) + 48])
            if entry == b'\x00' * 48:
                print(f"    [{idx:2d}] (all zeros - end)")
                break

            name, typename = decode_name_field(entry[0:16])
            cat = entry[0x10]
            sub = entry[0x11]
            elem1 = entry[0x12]
            elem2 = entry[0x13]
            p1, p2, p3, p4 = entry[0x14], entry[0x15], entry[0x16], entry[0x17]
            handler = entry[0x18]
            prob = entry[0x1D]

            # Determine tier availability
            avail = []
            for t in range(5):
                if tier[t] > idx:
                    avail.append(f"tier{t}")

            avail_str = ",".join(avail) if avail else "NEVER"
            type_str = f" ({typename})" if typename else ""

            print(f"    [{idx:2d}] \"{name}\"{type_str:15s}  "
                  f"cat={cat:3d} sub={sub} elem=({elem1},{elem2}) "
                  f"power=({p1},{p2},{p3},{p4}) handler={handler:3d} prob={prob:3d}  "
                  f"avail=[{avail_str}]")

    # =========================================================
    # SECTION 10: Check what monster entries point to + handler analysis
    # =========================================================
    print()
    print("=" * 95)
    print("  SECTION 10: Cross-reference monster abilities with handler table")
    print("=" * 95)

    handler_table = 0x8003C1B0
    handlers = {}
    for i in range(55):
        handlers[i] = read_u32(ram, handler_table + i * 4)

    # For type 6 (monster abilities), show which handler each maps to
    ptr6 = ptr_array[6]
    if ptr6 and is_ram_ptr(ptr6):
        print(f"\n  Type 6 (monster ability catalog) handler mapping:")
        for idx in range(30):
            entry_addr = ptr6 + idx * 48
            if entry_addr + 48 > RAM_BASE + RAM_SIZE:
                break
            entry = bytes(ram[ram_idx(entry_addr):ram_idx(entry_addr) + 48])
            if entry == b'\x00' * 48:
                break
            name, typename = decode_name_field(entry[0:16])
            handler_ref = entry[0x18]
            type_str = f" ({typename})" if typename else ""

            # Look up handler in the 55-entry table
            handler_addr = handlers.get(handler_ref, 0) if handler_ref < 55 else 0
            handler_str = f"-> 0x{handler_addr:08X}" if handler_addr else f"(handler {handler_ref} out of range)"

            print(f"    [{idx:2d}] \"{name}\"{type_str:15s}  "
                  f"handler_ref={handler_ref:3d} {handler_str}")


if __name__ == '__main__':
    main()
