#!/usr/bin/env python3
"""
Ajouter 2 monster slots SANS agrandir la middle section

Stratégie:
- Middle section reste 44 bytes (critique!)
- Monster count = 5 (dans middle section byte[2])
- Ajouter animation tables (3×8 → 5×8 = +16)
- Ajouter animation records (3×8 → 5×8 = +16)
- Ajouter assignments (3×8 → 5×8 = +16)
- Ajouter stats (3×96 → 5×96 = +192)
- Total ajouté: 240 bytes
- Enlever 240 bytes de zone_spawns pour compenser
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
CURRENT = Path("output/BLAZE.ALL")

# Restaurer backup
shutil.copy2(BACKUP, CURRENT)

with open(CURRENT, 'rb') as f:
    data = bytearray(f.read())

CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C

print("=" * 70)
print("AJOUTER SLOTS - GARDER MIDDLE SECTION 44 BYTES")
print("=" * 70)
print()

# Structure vanilla (3 monsters)
anim_header = data[CAVERN_ANIM:CAVERN_ANIM+8]
anim_tables_old = data[CAVERN_ANIM+8:CAVERN_ANIM+32]  # 3×8
anim_records_old = data[CAVERN_ANIM+32:CAVERN_ANIM+56]  # 3×8
middle_section = data[CAVERN_ANIM+56:CAVERN_STATS-24]  # 44 bytes
assignments_old = data[CAVERN_STATS-24:CAVERN_STATS]  # 3×8
stats_old = data[CAVERN_STATS:CAVERN_STATS+288]  # 3×96

# GARDER middle section 44 bytes, juste changer byte[2]
middle_section = bytearray(middle_section)
middle_section[2] = 0x05  # Monster count = 5

# Ajouter 2 nouveaux slots (copier slot 0)
slot0_anim_table = anim_tables_old[0:8]
slot0_anim_record = anim_records_old[0:8]
slot0_assignment = assignments_old[0:8]

# Stats pour nouveaux slots
def create_stats(slot_idx):
    name = f"NewSlot{slot_idx}".encode('ascii')[:16].ljust(16, b'\x00')
    stats = [0, 1, 50] + [0]*37
    return name + b''.join(struct.pack('<H', v) for v in stats)

# Reconstruire sections
new_anim_tables = anim_tables_old + slot0_anim_table + slot0_anim_table
new_anim_records = anim_records_old + slot0_anim_record + slot0_anim_record
new_assignments = assignments_old + slot0_assignment + slot0_assignment
new_stats = stats_old + create_stats(1) + create_stats(2)

# Construire nouvelle zone
new_zone = bytearray()
new_zone += anim_header  # 8
new_zone += new_anim_tables  # 40
new_zone += new_anim_records  # 40
new_zone += middle_section  # 44 (PAS 48!)
new_zone += new_assignments  # 40
new_zone += new_stats  # 480

# Ajouter script, formations, zone_spawns
script_start = 0xF7AA9C
formation_start = 0xF7AFFC
zone_spawns_start = 0xF7B37C

script_data = data[script_start:formation_start]
formation_data = data[formation_start:zone_spawns_start]
zone_spawns_data = data[zone_spawns_start:zone_spawns_start+5416]

new_zone += script_data
new_zone += formation_data
new_zone += zone_spawns_data[:5416-240]  # Réduire de 240

print(f"Zone size: {len(new_zone)} bytes")
print(f"  Middle section: 44 bytes (GARDÉE!)")
print(f"  Monster count: 5")
print()

# Écrire
zone_start = CAVERN_ANIM
data[zone_start:zone_start + len(new_zone)] = new_zone

# Mettre à jour les 4 offsets hardcodés
# Formation start décalé de +236 bytes (16+16+16+192-4 car middle pas agrandi)
old_formation = 0xF7AFFC
new_formation = old_formation + 236

REFS = [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]
for ref in REFS:
    struct.pack_into('<I', data, ref, new_formation)
    print(f"  Offset @ 0x{ref:X}: 0x{old_formation:X} -> 0x{new_formation:X}")

with open(CURRENT, 'wb') as f:
    f.write(data)

print()
print("[OK] Slots ajoutés avec middle section 44 bytes")
print()
print(f"Taille fichier: {len(data):,} bytes")
