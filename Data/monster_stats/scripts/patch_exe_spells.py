"""
Patch SLES_008.45 executable to change monster spell behavior.

Goblin-Shaman (Type 0x18) Handler at 0x8001C218:
  0x8001C22C: 3C048005  lui a0, 0x8005           ; Load upper address
  0x8001C230: 24844670  addiu a0, a0, 0x4670     ; a0 = 0x80054670 (spell list)
  0x8001C238: 0C00705B  jal 0x8001C16C           ; Call spell handler

To change spells, we can either:
1. Change the spell list address (0x80054670) to another monster's list
2. Modify the spell list data directly if we can find it

Type 0x17 uses: 0x8004C4D0
Type 0x1A uses: 0x80054670 (same as Goblin-Shaman)
"""

import struct
import os
import sys

# Add parent directory for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# PS1 executable header size
EXE_HEADER_SIZE = 0x800

# File offsets in SLES_008.45 (subtract 0x80010000 from RAM, add header)
# Handler for Goblin-Shaman starts at RAM 0x8001C218 = file offset 0xCA18
GOBLIN_SHAMAN_HANDLER_OFFSET = 0x8001C218 - 0x80010000 + EXE_HEADER_SIZE  # = 0xCA18

# The spell list address instructions are at:
# 0x8001C22C: lui a0, 0x8005
# 0x8001C230: addiu a0, a0, 0x4670
LUI_OFFSET = 0x8001C22C - 0x80010000 + EXE_HEADER_SIZE  # = 0xCA2C
ADDIU_OFFSET = 0x8001C230 - 0x80010000 + EXE_HEADER_SIZE  # = 0xCA30

def read_instruction(data, offset):
    """Read a 32-bit MIPS instruction."""
    return struct.unpack('<I', data[offset:offset+4])[0]

def write_instruction(data, offset, instr):
    """Write a 32-bit MIPS instruction."""
    return data[:offset] + struct.pack('<I', instr) + data[offset+4:]

def make_lui(rt, imm):
    """Create LUI instruction: lui rt, imm"""
    # lui = opcode 0x0F (001111)
    # Format: 001111 00000 rt imm
    return (0x0F << 26) | (rt << 16) | (imm & 0xFFFF)

def make_addiu(rt, rs, imm):
    """Create ADDIU instruction: addiu rt, rs, imm"""
    # addiu = opcode 0x09 (001001)
    # Format: 001001 rs rt imm
    return (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

def get_address_from_lui_addiu(lui_instr, addiu_instr):
    """Extract the full address from lui + addiu pair."""
    upper = lui_instr & 0xFFFF
    lower = addiu_instr & 0xFFFF
    # Sign extend lower
    if lower & 0x8000:
        lower = lower - 0x10000
    return (upper << 16) + lower

def set_address_lui_addiu(target_addr, reg=4):
    """Create lui + addiu instructions to load a target address into reg."""
    upper = (target_addr >> 16) & 0xFFFF
    lower = target_addr & 0xFFFF

    # If lower is negative (high bit set), we need to adjust upper
    if lower & 0x8000:
        upper = (upper + 1) & 0xFFFF
        lower = lower - 0x10000

    lui = make_lui(reg, upper)
    addiu = make_addiu(reg, reg, lower & 0xFFFF)
    return lui, addiu

def analyze_exe(exe_path):
    """Analyze the executable and show current spell list addresses."""
    print(f"Analyzing {exe_path}...")

    with open(exe_path, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Read current instructions
    lui_instr = read_instruction(data, LUI_OFFSET)
    addiu_instr = read_instruction(data, ADDIU_OFFSET)

    current_addr = get_address_from_lui_addiu(lui_instr, addiu_instr)

    print(f"\nGoblin-Shaman (Type 0x18) handler:")
    print(f"  LUI instruction at 0x{LUI_OFFSET:06X}: 0x{lui_instr:08X}")
    print(f"  ADDIU instruction at 0x{ADDIU_OFFSET:06X}: 0x{addiu_instr:08X}")
    print(f"  Current spell list address: 0x{current_addr:08X}")

    # Check Type 0x17 for comparison
    type17_lui_offset = 0x8001C1E4 - 0x80010000 + EXE_HEADER_SIZE
    type17_addiu_offset = 0x8001C1E8 - 0x80010000 + EXE_HEADER_SIZE

    type17_lui = read_instruction(data, type17_lui_offset)
    type17_addiu = read_instruction(data, type17_addiu_offset)
    type17_addr = get_address_from_lui_addiu(type17_lui, type17_addiu)

    print(f"\nType 0x17 handler for comparison:")
    print(f"  Spell list address: 0x{type17_addr:08X}")

    return data, current_addr

def patch_spell_list_address(data, new_addr):
    """Patch the Goblin-Shaman spell list address."""
    print(f"\nPatching spell list address to 0x{new_addr:08X}...")

    lui, addiu = set_address_lui_addiu(new_addr, reg=4)  # a0 = $4

    print(f"  New LUI instruction: 0x{lui:08X}")
    print(f"  New ADDIU instruction: 0x{addiu:08X}")

    # Verify the new instructions
    test_addr = get_address_from_lui_addiu(lui, addiu)
    print(f"  Verification - reconstructed address: 0x{test_addr:08X}")

    if test_addr != new_addr:
        print("  ERROR: Address mismatch!")
        return None

    data = write_instruction(data, LUI_OFFSET, lui)
    data = write_instruction(data, ADDIU_OFFSET, addiu)

    return data

def find_exe_in_bin(bin_path):
    """Find SLES_008.45 location in the BIN file."""
    # PS-X EXE signature
    signature = b'PS-X EXE'

    with open(bin_path, 'rb') as f:
        data = f.read()

    # Search for the signature
    offset = 0
    locations = []
    while True:
        pos = data.find(signature, offset)
        if pos == -1:
            break
        locations.append(pos)
        offset = pos + 1

    print(f"Found {len(locations)} PS-X EXE signature(s) in BIN:")
    for loc in locations:
        print(f"  Offset 0x{loc:08X}")

    return locations

def patch_bin_exe(bin_path, patched_exe_data, output_path=None):
    """Patch ALL occurrences of the executable instructions in the BIN file."""
    print(f"\nPatching ALL EXE occurrences in BIN file...")

    with open(bin_path, 'rb') as f:
        bin_data = bytearray(f.read())

    print(f"  BIN size: {len(bin_data):,} bytes")

    # Search for the ORIGINAL instruction pattern (before patch)
    # LUI a0, 0x8005 followed by ADDIU a0, a0, 0x4670
    original_pattern = struct.pack('<II', 0x3C048005, 0x24844670)

    # Get new instructions from patched EXE
    new_lui = struct.unpack('<I', patched_exe_data[LUI_OFFSET:LUI_OFFSET+4])[0]
    new_addiu = struct.unpack('<I', patched_exe_data[ADDIU_OFFSET:ADDIU_OFFSET+4])[0]
    new_pattern = struct.pack('<II', new_lui, new_addiu)

    print(f"  Original pattern: {original_pattern.hex()}")
    print(f"  New pattern:      {new_pattern.hex()}")

    # Find ALL occurrences
    positions = []
    offset = 0
    while True:
        pos = bin_data.find(original_pattern, offset)
        if pos == -1:
            break
        positions.append(pos)
        offset = pos + 1

    print(f"\n  Found {len(positions)} occurrence(s) of original pattern:")
    for i, pos in enumerate(positions):
        print(f"    [{i+1}] Offset 0x{pos:08X}")

    if len(positions) == 0:
        print("  ERROR: No occurrences found!")
        return False

    # Patch all occurrences
    for pos in positions:
        bin_data[pos:pos+8] = new_pattern
        print(f"  Patched at 0x{pos:08X}")

    # Save patched BIN
    if output_path is None:
        output_path = bin_path.replace('.bin', '_exe_patched.bin')

    with open(output_path, 'wb') as f:
        f.write(bin_data)

    print(f"\n  Patched {len(positions)} occurrence(s)")
    print(f"  Saved to: {output_path}")
    return True

def main():
    # Paths
    bin_path = r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\Blaze & Blade - Eternal Quest (Europe).bin"
    exe_extract_path = r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\SLES_008.45"

    print("="*60)
    print("Monster Spell Executable Patcher")
    print("="*60)

    # First analyze the extracted EXE
    if os.path.exists(exe_extract_path):
        data, current_addr = analyze_exe(exe_extract_path)

        # Option: Change Goblin-Shaman to use Type 0x17's spell list
        # Type 0x17 address: 0x8004C4D0
        new_addr = 0x8004C4D0

        print(f"\n{'='*60}")
        print("PROPOSED PATCH:")
        print(f"Change Goblin-Shaman spell list from 0x{current_addr:08X} to 0x{new_addr:08X}")
        print("(This will make Goblin-Shaman use Type 0x17's spell list)")
        print(f"{'='*60}")

        # Apply patch
        patched_data = patch_spell_list_address(data, new_addr)

        if patched_data:
            # Save patched EXE to output folder
            output_dir = r"D:\projets\Bab_Gameplay_Patch\output"
            os.makedirs(output_dir, exist_ok=True)
            output_exe_path = os.path.join(output_dir, "SLES_008.45.patched")

            with open(output_exe_path, 'wb') as f:
                f.write(patched_data)
            print(f"\nPatched EXE saved to: {output_exe_path}")

            # Now patch the BIN file
            print(f"\n{'='*60}")
            print("Patching EXE in BIN file...")
            print(f"{'='*60}")

            if os.path.exists(bin_path):
                output_bin_path = os.path.join(output_dir, "Blaze & Blade - Patched.bin")
                patch_bin_exe(bin_path, patched_data, output_bin_path)
            else:
                print(f"BIN not found at {bin_path}")
    else:
        print(f"EXE not found at {exe_extract_path}")

if __name__ == "__main__":
    main()
