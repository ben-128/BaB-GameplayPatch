#!/usr/bin/env python3
"""
Test: Agrandir SEULEMENT la middle section sans ajouter de slots
Pour isoler si le problème vient de la middle section ou des nouveaux slots
"""

import struct
from pathlib import Path

BLAZE_ALL = Path("output/BLAZE.ALL")
BACKUP = Path("output/BLAZE.ALL.backup")

# Copier le backup
import shutil
shutil.copy2(BACKUP, BLAZE_ALL)

with open(BLAZE_ALL, 'rb') as f:
    data = bytearray(f.read())

# Cavern F1 A1 vanilla (3 monsters)
CAVERN_ANIM = 0xF7A900
CAVERN_STATS = 0xF7A97C

# Structure vanilla (3 monsters)
anim_header_start = CAVERN_ANIM
anim_tables_start = CAVERN_ANIM + 8
anim_records_start = CAVERN_ANIM + 32  # 8 + 24
middle_start = CAVERN_ANIM + 56  # 8 + 24 + 24
assignments_start = CAVERN_STATS - 24  # 3×8

# Extraire sections vanilla
middle_vanilla = data[middle_start:assignments_start]

print("=== TEST: Middle section seulement ===")
print()
print(f"Middle vanilla size: {len(middle_vanilla)} bytes")
print()

# OPTION 1: Juste changer byte[2] de 3 à 5 SANS agrandir
print("Option A: Changer monster count SANS agrandir middle section")
data[middle_start + 2] = 0x05

with open(BLAZE_ALL, 'wb') as f:
    f.write(data)

print(f"  [DONE] Byte[2]: 3 -> 5 (taille reste 44 bytes)")
print()
print("Teste cette version en jeu.")
print("Si ça crash: le problème est le monster count lui-même")
print("Si ça marche: le problème était l'agrandissement de la middle section")
