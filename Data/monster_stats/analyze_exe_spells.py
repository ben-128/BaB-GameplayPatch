"""
Analyze SLES_008.45 executable to find monster spell assignment logic.

Key values to search for:
- Goblin-Shaman type ID: 0x18 (24)
- Spell IDs: 0x03 (Stone Bullet), 0x08 (Magic Missile), 0x1F (Healing), 0xA0 (Sleep)
- Spell table address in BLAZE.ALL: 0x9E8D8E

We're looking for:
1. A lookup table mapping monster type to spell list
2. Code that checks monster type and assigns spells
3. Multiple spell IDs in close proximity
"""

import struct
import os

EXE_PATH = r"D:\projets\Bab_Gameplay_Patch\ghidra_work\SLES_008.45"

# Also check the original location
EXE_PATH_ALT = r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45"

# Monster types known to cast spells
SPELL_CASTERS = {
    0x18: "Goblin-Shaman",
    0x25: "Necromancer",  # Probably casts spells
    0x19: "Orc-Shaman",   # Probably casts spells
}

# Spell IDs
SPELL_IDS = {
    0x03: "Stone Bullet",
    0x08: "Magic Missile",
    0x1F: "Healing",
    0xA0: "Sleep",
    0x00: "None/Physical",
}

def find_exe():
    """Find the executable file."""
    if os.path.exists(EXE_PATH):
        return EXE_PATH
    if os.path.exists(EXE_PATH_ALT):
        return EXE_PATH_ALT
    return None

def analyze_mips_instruction(data, offset):
    """Decode a MIPS instruction at the given offset."""
    if offset + 4 > len(data):
        return None
    instr = struct.unpack('<I', data[offset:offset+4])[0]
    opcode = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    imm = instr & 0xFFFF
    # Sign extend immediate
    if imm & 0x8000:
        imm_signed = imm - 0x10000
    else:
        imm_signed = imm
    return {
        'raw': instr,
        'opcode': opcode,
        'rs': rs,
        'rt': rt,
        'imm': imm,
        'imm_signed': imm_signed,
    }

def search_for_spell_clusters(data):
    """Search for areas where multiple spell IDs appear close together."""
    print("\n" + "="*60)
    print("Searching for clusters of spell IDs...")
    print("="*60)

    # Find all occurrences of spell ID bytes
    spell_bytes = [0x03, 0x08, 0x1F, 0xA0]
    occurrences = []

    for i in range(len(data)):
        if data[i] in spell_bytes:
            occurrences.append((i, data[i]))

    # Find clusters (multiple spell IDs within 32 bytes)
    clusters = []
    i = 0
    while i < len(occurrences):
        cluster_start = occurrences[i][0]
        cluster = [occurrences[i]]
        j = i + 1
        while j < len(occurrences) and occurrences[j][0] - cluster_start <= 64:
            cluster.append(occurrences[j])
            j += 1
        if len(cluster) >= 3:  # At least 3 spell IDs close together
            clusters.append(cluster)
        i = j if j > i + 1 else i + 1

    print(f"Found {len(clusters)} potential spell ID clusters")

    # Filter to unique locations (different spell IDs)
    interesting = []
    for cluster in clusters:
        spell_set = set(c[1] for c in cluster)
        if len(spell_set) >= 2:  # Multiple different spells
            interesting.append(cluster)

    print(f"Clusters with 2+ different spell IDs: {len(interesting)}")

    for cluster in interesting[:20]:  # Show first 20
        start = cluster[0][0]
        end = cluster[-1][0]
        spells = [f"{SPELL_IDS.get(c[1], f'0x{c[1]:02X}')}@{c[0]:06X}" for c in cluster]
        print(f"\n  Offset 0x{start:06X}-0x{end:06X}: {', '.join(spells)}")
        # Show context
        ctx_start = max(0, start - 8)
        ctx_end = min(len(data), end + 16)
        print(f"    Context: {data[ctx_start:ctx_end].hex()}")

def search_monster_type_refs(data):
    """Search for references to monster type IDs near spell IDs."""
    print("\n" + "="*60)
    print("Searching for monster type ID references...")
    print("="*60)

    # MIPS li/addiu with immediate value 0x18 (Goblin-Shaman)
    # addiu rt, zero, 0x18 => opcode 0x09 (001001), rs=0, imm=0x18
    # Pattern: 0x24XX0018 where XX is register

    results = []

    for i in range(0, len(data) - 4, 4):
        instr = struct.unpack('<I', data[i:i+4])[0]

        # Check for addiu/ori with immediate 0x18
        opcode = (instr >> 26) & 0x3F
        rs = (instr >> 21) & 0x1F
        imm = instr & 0xFFFF

        # addiu = 0x09, ori = 0x0D
        if opcode in [0x09, 0x0D] and imm == 0x18 and rs == 0:
            # Check surrounding area for spell IDs
            context = data[max(0, i-64):i+64]
            spell_found = []
            for spell_id in [0x03, 0x08, 0x1F, 0xA0]:
                if spell_id in context:
                    spell_found.append(spell_id)
            if spell_found:
                results.append((i, instr, spell_found))

    print(f"Found {len(results)} type-0x18 references near spell IDs")
    for offset, instr, spells in results[:20]:
        spell_names = [SPELL_IDS.get(s, f'0x{s:02X}') for s in spells]
        print(f"  0x{offset:06X}: instruction 0x{instr:08X}, nearby spells: {spell_names}")

def search_switch_table(data):
    """Search for potential switch/jump tables that might map monster type to behavior."""
    print("\n" + "="*60)
    print("Searching for potential switch tables...")
    print("="*60)

    # Look for sequences of addresses that might be jump tables
    # PS1 RAM starts at 0x80000000, so addresses would be 0x800XXXXX

    potential_tables = []

    for i in range(0, len(data) - 128, 4):
        # Check if we have a sequence of valid-looking addresses
        addrs = []
        valid = True
        for j in range(32):  # Check 32 consecutive words
            if i + j*4 + 4 > len(data):
                valid = False
                break
            addr = struct.unpack('<I', data[i + j*4:i + j*4 + 4])[0]
            # Check if it looks like a PS1 RAM address
            if not (0x80010000 <= addr <= 0x801FFFFF):
                valid = False
                break
            addrs.append(addr)

        if valid and len(addrs) == 32:
            # Check if addresses are reasonable (not all the same, some variation)
            if len(set(addrs)) > 5:  # At least 6 different addresses
                potential_tables.append((i, addrs))

    print(f"Found {len(potential_tables)} potential jump tables")
    for offset, addrs in potential_tables[:10]:
        print(f"\n  Table at 0x{offset:06X}:")
        print(f"    First 8 entries: {[f'0x{a:08X}' for a in addrs[:8]]}")
        # Check if entry 0x18 (24) points somewhere different
        if len(addrs) > 0x18:
            print(f"    Entry 0x18 (Goblin-Shaman): 0x{addrs[0x18]:08X}")

def search_spell_assignment_pattern(data):
    """Search for patterns that look like spell assignment code."""
    print("\n" + "="*60)
    print("Searching for spell assignment patterns...")
    print("="*60)

    # Look for stores of spell ID values
    # sw/sh/sb with immediate matching spell IDs

    results = []

    for i in range(0, len(data) - 4, 4):
        instr = struct.unpack('<I', data[i:i+4])[0]

        # Check for lui (load upper immediate) with values that could be spell-related
        opcode = (instr >> 26) & 0x3F

        # li followed by sb/sw pattern for spell assignment
        if opcode == 0x09:  # addiu
            imm = instr & 0xFFFF
            if imm in [0x03, 0x08, 0x1F, 0xA0]:
                # Check next few instructions for store
                for j in range(1, 5):
                    if i + j*4 + 4 > len(data):
                        break
                    next_instr = struct.unpack('<I', data[i + j*4:i + j*4 + 4])[0]
                    next_op = (next_instr >> 26) & 0x3F
                    # sb=0x28, sh=0x29, sw=0x2B
                    if next_op in [0x28, 0x29, 0x2B]:
                        results.append((i, imm, SPELL_IDS.get(imm, f'0x{imm:02X}')))
                        break

    print(f"Found {len(results)} potential spell assignment sequences")

    # Group by proximity
    if results:
        print("\nGrouped results (assignments within 256 bytes):")
        current_group = [results[0]]
        groups = []

        for r in results[1:]:
            if r[0] - current_group[-1][0] <= 256:
                current_group.append(r)
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [r]
        if len(current_group) >= 2:
            groups.append(current_group)

        for group in groups[:10]:
            start = group[0][0]
            spells = [f"{g[2]}@0x{g[0]:06X}" for g in group]
            print(f"\n  Group at 0x{start:06X}: {', '.join(spells)}")

def main():
    exe_path = find_exe()
    if not exe_path:
        print("ERROR: Cannot find SLES_008.45 executable")
        return

    print(f"Analyzing: {exe_path}")
    print(f"Size: {os.path.getsize(exe_path)} bytes")

    with open(exe_path, 'rb') as f:
        data = f.read()

    # Skip PS-X EXE header (0x800 bytes typically)
    # The actual code starts after the header
    header_size = 0x800
    code_data = data[header_size:]

    print(f"Code section size: {len(code_data)} bytes")

    search_for_spell_clusters(code_data)
    search_monster_type_refs(code_data)
    search_spell_assignment_pattern(code_data)
    search_switch_table(code_data)

    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)

if __name__ == "__main__":
    main()
