"""
Find spell list data referenced by monster AI handlers.

From the disassembly:
- Goblin-Shaman (0x18): lui a0, 0x8005 / addiu a0, a0, 0x4670 -> 0x80054670
- Type 0x17:            lui a0, 0x8005 / addiu a0, a0, 0xC4D0 -> 0x8004C4D0 (negative offset)
- Type 0x19:            lui a0, 0x8005 / addiu a0, a0, 0xC4D0 -> 0x8004C4D0
- Type 0x1A:            lui a0, 0x8005 / addiu a0, a0, 0x4670 -> 0x80054670 (same as Goblin-Shaman!)
"""

import struct

EXE_PATH = r"D:\projets\Bab_Gameplay_Patch\ghidra_work\SLES_008.45"
HEADER_SIZE = 0x800

SPELL_IDS = {
    0x00: "None",
    0x01: "Fire Ball",
    0x02: "Ice Ball",
    0x03: "Stone Bullet",
    0x04: "Thunder Ball",
    0x05: "Burning",
    0x06: "Freeze",
    0x07: "Blast",
    0x08: "Magic Missile",
    0x09: "Fire Storm",
    0x0A: "Ice Storm",
    0x0B: "Earth Quake",
    0x0C: "Thunder Storm",
    0x0D: "Inferno",
    0x0E: "Diamond Dust",
    0x0F: "Volcano",
    0x10: "Sonic Boom",
    0x11: "Flame Wave",
    0x12: "Icicle",
    0x13: "Land Slide",
    0x14: "Hurricane",
    0x15: "Explosion",
    0x16: "Shatter",
    0x17: "Mud Flow",
    0x18: "Wild Wind",
    0x19: "Crimson Flare",
    0x1A: "Absolute Zero",
    0x1B: "Meteor Swarm",
    0x1C: "Indignation",
    0x1D: "Fire Breath",
    0x1E: "Blizzard Breath",
    0x1F: "Healing",
    0x20: "Recover",
    0x21: "Multi Heal",
    0x22: "Full Recover",
    0x23: "Resurrect",
    0xA0: "Sleep",
    0xA1: "Silence",
    0xA2: "Confusion",
    0xA3: "Paralysis",
    0xA4: "Stone",
    0xA5: "Poison",
}

def ram_to_file(ram_addr):
    """Convert RAM address to file offset."""
    return ram_addr - 0x80010000 + HEADER_SIZE

def analyze_data_region(data, ram_addr, name, size=64):
    """Analyze a data region that might contain spell lists."""
    file_offset = ram_to_file(ram_addr)

    print(f"\n{'='*70}")
    print(f"{name} Data at RAM 0x{ram_addr:08X} (file 0x{file_offset:06X})")
    print(f"{'='*70}")

    # Dump as bytes
    print("\nRaw bytes:")
    for i in range(0, min(size, len(data) - file_offset), 16):
        offset = file_offset + i
        hex_str = ' '.join(f'{data[offset+j]:02X}' for j in range(16) if offset+j < len(data))
        ascii_str = ''.join(chr(data[offset+j]) if 32 <= data[offset+j] < 127 else '.' for j in range(16) if offset+j < len(data))
        print(f"  0x{ram_addr + i:08X}: {hex_str:48} |{ascii_str}|")

    # Look for spell IDs in the data
    print("\nPotential spell IDs found:")
    for i in range(min(size, len(data) - file_offset)):
        byte = data[file_offset + i]
        if byte in SPELL_IDS:
            print(f"  Offset +{i}: 0x{byte:02X} = {SPELL_IDS[byte]}")

def search_all_spell_list_refs(data):
    """Search the entire executable for potential spell list patterns."""
    print("\n" + "#"*70)
    print("Searching for Goblin-Shaman spell pattern (0x03, 0x08, 0x1F, 0xA0)...")
    print("#"*70)

    # Goblin-Shaman spells: Stone Bullet (0x03), Magic Missile (0x08), Healing (0x1F), Sleep (0xA0)
    pattern_spells = [0x03, 0x08, 0x1F, 0xA0]

    # Search for any region containing all 4 spells within 32 bytes
    results = []
    for i in range(len(data) - 32):
        found = []
        for j in range(32):
            if data[i + j] in pattern_spells:
                found.append((j, data[i + j]))

        spell_ids_found = set(f[1] for f in found)
        if len(spell_ids_found) >= 3:  # At least 3 of the 4 spells
            # Check if they're close together (within 16 bytes of each other)
            positions = [f[0] for f in found]
            if max(positions) - min(positions) <= 16:
                results.append((i, found, spell_ids_found))

    # Deduplicate overlapping results
    filtered = []
    last_offset = -100
    for offset, found, spell_ids in results:
        if offset - last_offset > 16:
            filtered.append((offset, found, spell_ids))
            last_offset = offset

    print(f"\nFound {len(filtered)} potential spell list locations:")
    for offset, found, spell_ids in filtered[:30]:
        ram_addr = 0x80010000 + offset - HEADER_SIZE
        spells = [SPELL_IDS.get(s, f'0x{s:02X}') for s in spell_ids]
        print(f"\n  File 0x{offset:06X} (RAM ~0x{ram_addr:08X})")
        print(f"    Spells: {spells}")
        # Show context
        ctx = data[offset:offset+20]
        print(f"    Bytes: {ctx.hex()}")

def main():
    with open(EXE_PATH, 'rb') as f:
        data = f.read()

    # Check the addresses referenced by monster AI handlers
    # addiu with negative immediate: lui 0x8005 + addiu 0xC4D0 = 0x8005_0000 + 0xFFFF_C4D0 = 0x8004_C4D0
    # (because addiu sign-extends the immediate)

    # Goblin-Shaman: lui 0x8005 / addiu 0x4670 -> 0x80054670
    analyze_data_region(data, 0x80054670, "Goblin-Shaman Spell Data")

    # Type 0x17/0x19: lui 0x8005 / addiu 0xC4D0 (which is -0x3B30) -> 0x8004C4D0
    analyze_data_region(data, 0x8004C4D0, "Type 0x17/0x19 Spell Data")

    # Search for spell patterns
    search_all_spell_list_refs(data)

if __name__ == "__main__":
    main()
