# -*- coding: cp1252 -*-
"""Quick verification of spell table at 0x908E68 in BLAZE.ALL."""
import struct, os

blaze_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          "output", "BLAZE.ALL")
if not os.path.exists(blaze_path):
    blaze_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              "BLAZE.ALL")

with open(blaze_path, 'rb') as f:
    data = f.read()

SPELL_TABLE = 0x908E68
ENTRY_SIZE = 48
LISTS = [
    ("Offensive", 29),
    ("Support", 24),
    ("Status", 20),
    ("Herbs", 7),
    ("Wave", 1),
    ("Arrow", 1),
    ("Stardust", 1),
    ("Monster", 30),
]

offset = SPELL_TABLE
for list_name, count in LISTS:
    print(f"\n=== List: {list_name} ({count} entries) ===")
    for i in range(min(count, 5)):  # show first 5 per list
        entry = data[offset:offset + ENTRY_SIZE]
        name = ''.join(chr(b) if 32 <= b < 127 else '' for b in entry[:16]).strip()
        spell_id = entry[0x10]
        mp_cost = entry[0x13]
        element = entry[0x16]
        damage = entry[0x18]
        target = entry[0x1C]
        cast_prob = entry[0x1D]
        print(f"  [{i:2d}] 0x{offset:08X}: '{name}' id={spell_id} mp={mp_cost} "
              f"elem={element} dmg={damage} tgt={target} prob={cast_prob}")
        offset += ENTRY_SIZE
    if count > 5:
        print(f"  ... ({count - 5} more)")
        offset += (count - 5) * ENTRY_SIZE

print(f"\nTotal bytes: {offset - SPELL_TABLE}")
