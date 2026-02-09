#!/usr/bin/env python3
"""
Extract combat action data from ePSXe savestate + BLAZE.ALL + EXE.

Architecture (verified by MIPS disassembly of dispatch function at 0x80024494):

  creature_type (entity+0x2B5) -- ALWAYS 0 for all entities (player + monster)
       |
       v
  Global ptr *(0x8005490C) + 0x9C -> per-type pointer array (80 entries)
       |
       v
  ptr_array[creature_type] -> base of 48-byte ACTION ENTRIES (in BLAZE.ALL overlay)
       |                      For creature_type=0: "Fire", "Spark", "Water"... (28 Mage spells)
       v
  $s1 = entity+0x144 (level counter) determines TIER:
    <20=tier0, 20-49=tier1, 50-79=tier2, 80-109=tier3, 110+=tier4
       |
       v
  5-byte TIER TABLE at 0x8003C020 -> max_entries for this tier
    Type 0: [5, 10, 15, 20, 26] = Mage spells available per tier
       |
       v
  Loop 0..max_entries-1, stride 48 bytes:
    - entry+0x1D = probability threshold (random roll check)
    - Bitmask filter at entity+0x160+creature_type*8 gates availability
    - Selected action -> 55-entry HANDLER TABLE at 0x8003C1B0 -> jalr to handler code

KEY DISCOVERY: creature_type is NEVER written by code (no sb/sh/sw to +0x2B5 in
entire 2MB RAM). It's initialized to 0 by struct zeroing. ALL entities share
Type 0 action table. Differentiation between player classes and monsters happens
via the bitmask filter at entity+0x160 and the probability field in entries.

Types 0-2 are player class spell lists (Mage/Priest/Sorcerer).
Types 3 = consumable items, 4-5 = basic monster ability stubs.
Types 6-7 = full monster ability catalogs (30 entries each: breaths, eyes, drains, etc.)
  but tier=[0,0,0,0,0] means they're NEVER selected via the tier gate.
  Monster abilities must use a DIFFERENT selection mechanism.

ENTRY FORMAT (48 bytes, name-first):
  +0x00..0x0F: Ability name (16 bytes, two null-terminated names: display + type)
               e.g. "Fire\0Bullet\0" = name "Fire", type "Bullet"
  +0x10..0x11: Action category + sub-flags
  +0x12..0x13: Element type / target info
  +0x14..0x15: Range / power param 1
  +0x16..0x17: Range / power param 2
  +0x18..0x19: Additional params (handler_ref at +0x18)
  +0x1A..0x1B: Zeros
  +0x1C..0x1D: Flags + probability threshold
     +0x1D:    Probability threshold (0-255, compared vs random roll)
  +0x1E..0x1F: Size / range flags
  +0x20..0x2F: Targeting parameters (16 bytes)

Verified dispatch loop at 0x80024E58-0x80024EF8:
  s5 = ptr_array[creature_type]           ; action base
  lbu   v0, 0x1D(s5)                      ; probability
  addiu s5, s5, 48                        ; stride
"""

import gzip
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------
# Paths
# ---------------------------------------------------------------
SAVESTATE = Path(r"D:\VieuxJeux\BAB\ePSXe2018\sstates\combat\SLES_008.45.000")
BLAZE_ALL = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL")
EXE_PATH  = Path(r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45")

# ---------------------------------------------------------------
# Constants
# ---------------------------------------------------------------
RAM_BASE         = 0x80000000
RAM_SIZE         = 0x200000       # 2 MB
SAVESTATE_RAM_OFF = 0x1BA

GAME_STATE_PTR   = 0x8005490C
PTR_ARRAY_OFF    = 0x9C

TIER_TABLE_RAM   = 0x8003C020
NUM_CREATURE_TYPES = 80
TIER_ENTRIES     = 5

HANDLER_TABLE_RAM = 0x8003C1B0
NUM_HANDLERS     = 55

MAX_ACTIONS_PER_CREATURE = 30
ACTION_ENTRY_SIZE = 48            # 0x30 bytes

ELEMENT_NAMES = {
    0: "none",
    1: "water",
    2: "fire",
    3: "ice",
    4: "earth",
    5: "wind",
    6: "lightning",
    7: "light",
    8: "dark",
    9: "divine",
    10: "malefic",
}

TIER_LABELS = [
    "Lv<20",
    "Lv20-49",
    "Lv50-79",
    "Lv80-109",
    "Lv110+",
]


def ram_idx(addr):
    """Convert RAM address to buffer index."""
    return addr - RAM_BASE


def read_u32(buf, addr):
    """Read uint32 from RAM buffer at a RAM address."""
    return struct.unpack_from('<I', buf, ram_idx(addr))[0]


def read_u16(buf, addr):
    """Read uint16 from RAM buffer at a RAM address."""
    return struct.unpack_from('<H', buf, ram_idx(addr))[0]


def decode_name(data16):
    """Decode the 16-byte name field.
    Format: "DisplayName\\0TypeName\\0..."
    Returns (display_name, type_name).
    """
    # Find first null
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


def find_blaze_offset(ram, blaze_data, ram_addr, entry_data):
    """Find the BLAZE.ALL offset for a given RAM entry by searching."""
    pattern = entry_data[:16]  # Match first 16 bytes (spell name)
    idx = blaze_data.find(pattern)
    if idx != -1:
        # Verify full 48 bytes
        if blaze_data[idx:idx + ACTION_ENTRY_SIZE] == entry_data:
            return idx
    return None


# ===================================================================
# STEP 1: Extract RAM from savestate
# ===================================================================
def extract_ram():
    print("=" * 95)
    print("  STEP 1: Extract RAM from ePSXe savestate")
    print("=" * 95)

    raw = gzip.open(str(SAVESTATE), 'rb').read()
    print(f"  Decompressed savestate: {len(raw):,} bytes")

    ram = raw[SAVESTATE_RAM_OFF : SAVESTATE_RAM_OFF + RAM_SIZE]
    print(f"  RAM extracted: {len(ram):,} bytes (from offset 0x{SAVESTATE_RAM_OFF:X})")

    if len(ram) < RAM_SIZE:
        print(f"  WARNING: Expected {RAM_SIZE} bytes, got {len(ram)}")

    exe_data = bytearray(Path(EXE_PATH).read_bytes())

    # PSX EXE: 0x800 header, text section loads to 0x80010000
    exe_text = exe_data[0x800:0x808]
    ram_text = ram[ram_idx(0x80010000):ram_idx(0x80010000) + 8]
    match = (bytes(exe_text) == bytes(ram_text))
    print(f"  EXE text verification (0x80010000): {'MATCH' if match else 'MISMATCH'}")
    print(f"    First 8 bytes: {bytes(ram_text).hex()}")

    return bytearray(ram), exe_data


# ===================================================================
# STEP 2: Read master game state pointer
# ===================================================================
def read_game_state(ram):
    print()
    print("=" * 95)
    print("  STEP 2: Master game state pointer")
    print("=" * 95)

    game_state_ptr = read_u32(ram, GAME_STATE_PTR)
    print(f"  *(0x{GAME_STATE_PTR:08X}) = 0x{game_state_ptr:08X}  (master game state struct)")

    if game_state_ptr < RAM_BASE or game_state_ptr >= RAM_BASE + RAM_SIZE:
        print(f"  ERROR: Game state pointer out of RAM range!")
        return None, None

    ptr_array_addr = game_state_ptr + PTR_ARRAY_OFF
    ptr_array_ptr = read_u32(ram, ptr_array_addr)
    print(f"  *(game_state+0x{PTR_ARRAY_OFF:02X}) = *(0x{ptr_array_addr:08X}) = 0x{ptr_array_ptr:08X}  (per-type pointer array)")

    if ptr_array_ptr < RAM_BASE or ptr_array_ptr >= RAM_BASE + RAM_SIZE:
        print(f"  ERROR: Pointer array address out of RAM range!")
        return game_state_ptr, None

    return game_state_ptr, ptr_array_ptr


# ===================================================================
# STEP 3: Dump pointer array
# ===================================================================
def dump_pointer_array(ram, ptr_array_addr):
    print()
    print("=" * 95)
    print("  STEP 3: Per-creature-type pointer array")
    print("=" * 95)
    print(f"  Array at 0x{ptr_array_addr:08X}, reading {NUM_CREATURE_TYPES} entries")
    print()

    pointers = []
    non_zero = 0
    for i in range(NUM_CREATURE_TYPES):
        addr = ptr_array_addr + i * 4
        ptr = read_u32(ram, addr)
        pointers.append(ptr)
        if ptr != 0:
            # Peek at first bytes to see if it looks like a name
            target_data = ram[ram_idx(ptr):ram_idx(ptr) + 16]
            name, typename = decode_name(target_data)
            name_str = f'  "{name}"' if name else ""
            if typename:
                name_str += f' ({typename})'
            print(f"    [{i:3d}] 0x{ptr:08X}{name_str}")
            non_zero += 1

    print(f"\n  Total non-zero entries: {non_zero} / {NUM_CREATURE_TYPES}")
    return pointers


# ===================================================================
# STEP 4: Follow pointers, dump action entries
# ===================================================================
def dump_action_entries(ram, pointers, blaze_data, tiers):
    print()
    print("=" * 95)
    print("  STEP 4: Action entries per creature type")
    print("=" * 95)

    all_entries = {}  # creature_type -> list of action dicts
    blaze_mapping = {}  # ram_addr -> blaze_offset (to compute base mapping)

    for ctype, ptr in enumerate(pointers):
        if ptr == 0:
            continue

        if ptr < RAM_BASE or ptr >= RAM_BASE + RAM_SIZE:
            continue

        # Use the tier table to determine expected entry count
        tier = tiers.get(ctype, [0, 0, 0, 0, 0])
        max_expected = max(tier) if any(v > 0 for v in tier) else MAX_ACTIONS_PER_CREATURE

        # Validate: does ptr point to data that looks like an action entry?
        # Action entries start with ASCII name. Check if first byte is printable.
        first_byte = ram[ram_idx(ptr)]
        if not (32 <= first_byte < 127):
            # Not ASCII - probably not an action entry (might be description text ptr for types 9+)
            continue

        entries = []
        base_addr = ptr

        for idx in range(min(max_expected + 2, MAX_ACTIONS_PER_CREATURE)):
            entry_addr = base_addr + idx * ACTION_ENTRY_SIZE
            if entry_addr + ACTION_ENTRY_SIZE > RAM_BASE + RAM_SIZE:
                break

            entry_data = bytes(ram[ram_idx(entry_addr):ram_idx(entry_addr) + ACTION_ENTRY_SIZE])

            # Check for all-zeros (end of entries)
            if entry_data == b'\x00' * ACTION_ENTRY_SIZE:
                break

            # Parse the name-first format
            name, typename = decode_name(entry_data[0x00:0x10])

            # Validate: name should be printable ASCII
            if not name or not all(32 <= ord(c) < 127 for c in name):
                break

            # Parse remaining fields
            cat_byte  = entry_data[0x10]  # action category
            sub_byte  = entry_data[0x11]  # sub-category
            elem1     = entry_data[0x12]  # element / param
            elem2     = entry_data[0x13]  # secondary element / param
            param1    = entry_data[0x14]  # range/power param
            param2    = entry_data[0x15]  # range/power param
            param3    = entry_data[0x16]  # additional param
            param4    = entry_data[0x17]  # additional param
            handler_ref = entry_data[0x18]  # reference to handler
            unk_19    = entry_data[0x19]
            unk_1a    = entry_data[0x1A]
            unk_1b    = entry_data[0x1B]
            unk_1c    = entry_data[0x1C]
            prob      = entry_data[0x1D]  # probability threshold (confirmed by dispatch code)
            size_flags = struct.unpack_from('<H', entry_data, 0x1E)[0]
            params    = entry_data[0x20:0x30]

            # Find BLAZE.ALL offset
            blaze_off = find_blaze_offset(ram, blaze_data, entry_addr, entry_data)
            if blaze_off is not None:
                blaze_mapping[entry_addr] = blaze_off

            entry_dict = {
                'idx': idx,
                'addr': entry_addr,
                'name': name,
                'typename': typename,
                'cat': cat_byte,
                'sub': sub_byte,
                'elem1': elem1,
                'elem2': elem2,
                'param1': param1,
                'param2': param2,
                'param3': param3,
                'param4': param4,
                'handler_ref': handler_ref,
                'prob': prob,
                'size_flags': size_flags,
                'params': params,
                'blaze_off': blaze_off,
                'raw': entry_data,
            }
            entries.append(entry_dict)

        if entries:
            all_entries[ctype] = entries

    # Compute overall RAM->BLAZE mapping from found entries
    if blaze_mapping:
        offsets = [(ram_a, blaze_a, blaze_a - (ram_a - 0x800A0000))
                   for ram_a, blaze_a in blaze_mapping.items()]
        bases = set(o[2] for o in offsets)
        if len(bases) == 1:
            blaze_base = bases.pop()
            print(f"\n  BLAZE.ALL overlay mapping: BLAZE = (RAM - 0x800A0000) + 0x{blaze_base:08X}")
            print(f"  (RAM 0x800A0000 corresponds to BLAZE 0x{blaze_base:08X})")
        else:
            print(f"\n  WARNING: Multiple base offsets found: {[f'0x{b:08X}' for b in sorted(bases)]}")
            blaze_base = min(bases)
    else:
        blaze_base = 0x00900000  # fallback

    # Print results
    for ctype, entries in sorted(all_entries.items()):
        ptr = pointers[ctype]
        first_blaze = entries[0]['blaze_off']
        blaze_str = f" = BLAZE 0x{first_blaze:08X}" if first_blaze is not None else ""
        print(f"\n  --- Creature type {ctype} ({len(entries)} entries at RAM 0x{ptr:08X}{blaze_str}) ---")

        for e in entries:
            type_str = f" ({e['typename']})" if e['typename'] else ""
            blaze_str2 = f"  BLAZE 0x{e['blaze_off']:08X}" if e['blaze_off'] is not None else ""
            print(f"    [{e['idx']:2d}] \"{e['name']}\"{type_str:12s}  "
                  f"cat={e['cat']:2d} elem=({e['elem1']},{e['elem2']}) "
                  f"prob={e['prob']:3d} handler={e['handler_ref']:2d} "
                  f"params=({e['param1']},{e['param2']},{e['param3']},{e['param4']})"
                  f"{blaze_str2}")
            # Raw hex for reference
            print(f"         [{e['raw'][:16].hex()}|{e['raw'][16:32].hex()}|{e['raw'][32:].hex()}]")

    return all_entries, blaze_base


# ===================================================================
# STEP 5: 5-byte tier table
# ===================================================================
def read_tier_table(ram, exe_data):
    print()
    print("=" * 95)
    print("  STEP 5: 5-byte tier table (action counts per level range)")
    print("=" * 95)
    print(f"  RAM address: 0x{TIER_TABLE_RAM:08X}")

    # PSX EXE: 0x800 header, loads at 0x80010000
    exe_offset = TIER_TABLE_RAM - 0x80010000 + 0x800  # = 0x2C820
    print(f"  EXE file offset: 0x{exe_offset:X}")

    tiers = {}

    for i in range(NUM_CREATURE_TYPES):
        addr = TIER_TABLE_RAM + i * TIER_ENTRIES
        tier_data = ram[ram_idx(addr):ram_idx(addr) + TIER_ENTRIES]
        tiers[i] = list(tier_data)

    # Verify against EXE
    if exe_offset + NUM_CREATURE_TYPES * TIER_ENTRIES <= len(exe_data):
        exe_tier0 = list(exe_data[exe_offset:exe_offset + TIER_ENTRIES])
        ram_tier0 = tiers[0]
        if exe_tier0 == ram_tier0:
            print(f"  EXE verification: MATCH (offset 0x{exe_offset:X})")
        else:
            print(f"  EXE verification: MISMATCH")
            print(f"    EXE: {exe_tier0}")
            print(f"    RAM: {ram_tier0}")
    print()

    print(f"  {'Type':>4s}  {'<20':>4s}  {'20-49':>5s}  {'50-79':>5s}  {'80-109':>6s}  {'110+':>4s}  {'Max':>4s}")
    print(f"  {'----':>4s}  {'----':>4s}  {'-----':>5s}  {'-----':>5s}  {'------':>6s}  {'----':>4s}  {'----':>4s}")
    for i in range(NUM_CREATURE_TYPES):
        t = tiers[i]
        if any(v != 0 for v in t):
            print(f"  {i:4d}  {t[0]:4d}  {t[1]:5d}  {t[2]:5d}  {t[3]:6d}  {t[4]:4d}  {max(t):4d}")

    return tiers


# ===================================================================
# STEP 6: Verify BLAZE.ALL mapping
# ===================================================================
def verify_blaze_mapping(ram, blaze_data, all_entries, blaze_base):
    print()
    print("=" * 95)
    print("  STEP 6: BLAZE.ALL offset verification")
    print("=" * 95)
    print(f"  Computed mapping: BLAZE = (RAM - 0x800A0000) + 0x{blaze_base:08X}")
    print()

    total = 0
    verified = 0
    for ctype, entries in sorted(all_entries.items()):
        for e in entries:
            total += 1
            if e['blaze_off'] is not None:
                # Verify full match
                if blaze_data[e['blaze_off']:e['blaze_off'] + ACTION_ENTRY_SIZE] == e['raw']:
                    verified += 1

    print(f"  Total action entries:  {total}")
    print(f"  BLAZE.ALL verified:    {verified}")
    if verified < total:
        print(f"  Not verified:          {total - verified}")

    # Show the BLAZE.ALL region containing all entries
    if all_entries:
        all_blaze_offs = [e['blaze_off'] for elist in all_entries.values() for e in elist if e['blaze_off'] is not None]
        if all_blaze_offs:
            min_off = min(all_blaze_offs)
            max_off = max(all_blaze_offs) + ACTION_ENTRY_SIZE
            print(f"\n  Action entries span BLAZE.ALL 0x{min_off:08X} - 0x{max_off:08X} ({max_off - min_off:,} bytes)")


# ===================================================================
# STEP 7: Handler table
# ===================================================================
def dump_handler_table(ram):
    print()
    print("=" * 95)
    print("  HANDLER TABLE (55 entries at 0x{:08X})".format(HANDLER_TABLE_RAM))
    print("=" * 95)

    handlers = {}
    for i in range(NUM_HANDLERS):
        addr = HANDLER_TABLE_RAM + i * 4
        handler = read_u32(ram, addr)
        handlers[i] = handler

    by_handler = {}
    for i, h in handlers.items():
        by_handler.setdefault(h, []).append(i)

    print(f"\n  {'Idx':>3s}  {'Handler':>10s}  {'Shared with':>20s}")
    print(f"  {'---':>3s}  {'----------':>10s}  {'--------------------':>20s}")
    for i in range(NUM_HANDLERS):
        h = handlers[i]
        shared = by_handler[h]
        shared_str = ""
        if len(shared) > 1:
            others = [x for x in shared if x != i]
            shared_str = f"{others}"
        print(f"  {i:3d}  0x{h:08X}  {shared_str}")

    return handlers


# ===================================================================
# STEP 8: Build spell catalog
# ===================================================================
def build_spell_catalog(blaze_data):
    """Search BLAZE.ALL for known spell names to build a reference catalog."""
    print()
    print("=" * 95)
    print("  SPELL/ABILITY NAME CATALOG (from BLAZE.ALL)")
    print("=" * 95)

    known_names = [
        "Teleport", "Chaos Flare", "Meteor Smash", "Fusion",
        "Turn Undead", "Healing", "Haste", "Enchant Fire",
        "Enchant Earth", "Enchant Wind", "Enchant Water", "Charm",
        "Paralyze Eye", "Confusion Eye", "Sleep Eye",
        "Fire Breath", "Cold Breath", "Thunder Breath", "Stone Breath",
        "Throw Rock", "Wave", "Sonic Boom", "Gas Bullet", "Power Wave",
        "Fire", "Spark", "Water", "Stone", "Striking", "Lightbolt",
        "Arrow", "Stardust", "Poison", "Lavender", "Sage",
        "Sleep", "Slow",
    ]

    catalog = {}
    for name in known_names:
        search = name.encode('ascii') + b'\x00'
        pos = 0
        while True:
            idx = blaze_data.find(search, pos)
            if idx == -1 or idx > 0x2000000:
                break
            # Check if this is at the start of a 16-byte name field
            # (i.e., is it at a position that could be entry+0x00?)
            catalog.setdefault(name, []).append(idx)
            pos = idx + 1

    for name in known_names:
        offsets = catalog.get(name, [])
        if offsets:
            offs_str = ", ".join(f"0x{o:08X}" for o in offsets[:5])
            extra = f" (+{len(offsets)-5} more)" if len(offsets) > 5 else ""
            print(f"  {name:20s}: {offs_str}{extra}")

    return catalog


# ===================================================================
# STEP 9: Summary
# ===================================================================
def print_summary(all_entries, tiers, blaze_base, pointers):
    print()
    print("#" * 95)
    print("#  SUMMARY: Combat Action Data for Blaze & Blade")
    print("#" * 95)

    for ctype in sorted(all_entries.keys()):
        entries = all_entries[ctype]
        tier = tiers.get(ctype, [0, 0, 0, 0, 0])
        ptr = pointers[ctype]

        first_blaze = entries[0]['blaze_off']
        blaze_str = f" = BLAZE 0x{first_blaze:08X}" if first_blaze is not None else ""

        print(f"\n  === CREATURE TYPE {ctype} (entries at RAM 0x{ptr:08X}{blaze_str}) ===")
        print(f"  Tier counts: [{', '.join(f'{t:2d}' for t in tier)}]  "
              f"({', '.join(f'{TIER_LABELS[i]}={tier[i]}' for i in range(5))})")

        for i, e in enumerate(entries):
            type_str = f" ({e['typename']})" if e['typename'] else ""

            # Determine unlock tier
            unlock = "always"
            for t in range(5):
                if tier[t] > i:
                    unlock = TIER_LABELS[t]
                    break
            else:
                if tier[4] <= i:
                    unlock = "NEVER"

            blaze_str2 = f"BLAZE=0x{e['blaze_off']:08X}" if e['blaze_off'] is not None else "BLAZE=???"

            print(f"    [{i:2d}] \"{e['name']}\"{type_str:14s} "
                  f"prob={e['prob']:3d}  cat={e['cat']:2d}  elem=({e['elem1']},{e['elem2']})  "
                  f"unlock={unlock:8s}  {blaze_str2}")

    # ---------------------------------------------------------------
    # MODDING GUIDE
    # ---------------------------------------------------------------
    print()
    print("#" * 95)
    print("#  MODDING GUIDE: How to patch combat actions in BLAZE.ALL")
    print("#" * 95)
    print("""
  ENTRY FORMAT (48 bytes, starting at BLAZE offset listed above):
  ================================================================
  +0x00..0x0F  Ability names (16 bytes: "DisplayName\\0TypeName\\0padding")
  +0x10        Action category (byte)
  +0x11        Sub-category (byte)
  +0x12        Element / parameter 1 (byte)
  +0x13        Element / parameter 2 (byte)
  +0x14        Range / power 1 (byte)
  +0x15        Range / power 2 (byte)
  +0x16        Additional param 1 (byte)
  +0x17        Additional param 2 (byte)
  +0x18        Handler reference (byte)
  +0x19        Unknown flag (byte)
  +0x1A..0x1B  Zeros / reserved (2 bytes)
  +0x1C        Unknown flag (byte)
  +0x1D        PROBABILITY THRESHOLD (0-255) - key modding target
  +0x1E..0x1F  Size / range flags (2 bytes)
  +0x20..0x2F  Targeting parameters (16 bytes)

  PROBABILITY (+0x1D):
    Dispatch loop rolls random number and compares against this threshold.
    Higher = more likely to use this action.
    0 = skip (never used as a random action, may be used as default).

  TIER TABLE (in EXE at RAM 0x8003C020, file offset 0x2C820):
    5 bytes per creature type: [tier0, tier1, tier2, tier3, tier4]
    tier0=Lv<20, tier1=Lv20-49, tier2=Lv50-79, tier3=Lv80-109, tier4=Lv110+
    Value = number of actions available to the creature at that level range.
    Creature uses entries [0..count-1] from its action table.

  TO MODIFY:
    1. Change probability: modify byte at entry+0x1D in BLAZE.ALL
    2. Change spell name:  modify 16 bytes at entry+0x00
    3. Change parameters:  modify bytes at entry+0x10..0x1F
    4. Change tier counts:  modify EXE at 0x2C820 + creature_type * 5
""")

    print("  Per-creature BLAZE.ALL offsets:")
    print(f"  {'Type':>4s}  {'RAM Addr':>10s}  {'BLAZE Addr':>12s}  {'Entries':>7s}  {'BLAZE Range':>28s}")
    print(f"  {'----':>4s}  {'----------':>10s}  {'------------':>12s}  {'-------':>7s}  {'----------------------------':>28s}")

    for ctype in sorted(all_entries.keys()):
        entries = all_entries[ctype]
        if not entries:
            continue
        ptr = pointers[ctype]
        first_blaze = entries[0]['blaze_off']
        if first_blaze is not None:
            last_blaze = first_blaze + (len(entries) - 1) * ACTION_ENTRY_SIZE
            end_blaze = last_blaze + ACTION_ENTRY_SIZE
            print(f"  {ctype:4d}  0x{ptr:08X}  0x{first_blaze:08X}  {len(entries):7d}  "
                  f"0x{first_blaze:08X}-0x{end_blaze:08X}")
        else:
            print(f"  {ctype:4d}  0x{ptr:08X}  {'???':>12s}  {len(entries):7d}")

    # Tier table EXE offsets
    print()
    print("  Tier table offsets in EXE (SLES_008.45):")
    exe_base = 0x2C820
    for ctype in sorted(all_entries.keys()):
        tier = tiers.get(ctype, [0]*5)
        off = exe_base + ctype * 5
        print(f"    Type {ctype:3d}: EXE offset 0x{off:05X}  bytes={tier}")


# ===================================================================
# Main
# ===================================================================
def main():
    print("BLAZE & BLADE - Combat Action Data Extractor")
    print("=" * 95)
    print(f"  Savestate: {SAVESTATE}")
    print(f"  BLAZE.ALL: {BLAZE_ALL}")
    print(f"  EXE:       {EXE_PATH}")
    print()

    # Load files
    blaze_data = bytearray(Path(BLAZE_ALL).read_bytes())
    print(f"  BLAZE.ALL loaded: {len(blaze_data):,} bytes")

    # Step 1: Extract RAM
    ram, exe_data = extract_ram()

    # Step 2: Game state pointer
    game_state_ptr, ptr_array_addr = read_game_state(ram)
    if ptr_array_addr is None:
        print("FATAL: Cannot read pointer array. Aborting.")
        sys.exit(1)

    # Step 5 first (we need tiers to determine entry counts)
    tiers = read_tier_table(ram, exe_data)

    # Step 3: Pointer array
    pointers = dump_pointer_array(ram, ptr_array_addr)

    # Step 4: Action entries (using tiers)
    all_entries, blaze_base = dump_action_entries(ram, pointers, blaze_data, tiers)

    # Step 6: BLAZE.ALL verification
    verify_blaze_mapping(ram, blaze_data, all_entries, blaze_base)

    # Handler table
    handlers = dump_handler_table(ram)

    # Spell catalog
    catalog = build_spell_catalog(blaze_data)

    # Step 7: Summary
    print_summary(all_entries, tiers, blaze_base, pointers)

    # Final stats
    total_entries = sum(len(e) for e in all_entries.values())
    print(f"\n  TOTAL: {len(all_entries)} creature types with {total_entries} total action entries")
    print(f"  Done.")


if __name__ == '__main__':
    main()
