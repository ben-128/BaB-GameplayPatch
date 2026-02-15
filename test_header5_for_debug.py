#!/usr/bin/env python3
"""
Create version with header_count=5 for debugging infinite loading

This version will cause infinite loading, allowing us to debug
WHERE and WHY it gets stuck.
"""

import struct
import shutil
from pathlib import Path

BACKUP = Path("output/BLAZE.ALL.backup")
OUTPUT = Path("output/BLAZE.ALL")

HEADER_COUNT = 0xF7A851
MIDDLE_COUNT = 0xF7A93A

print("=" * 70)
print("TEST: Header count = 5 (pour debug infinite loading)")
print("=" * 70)
print()

shutil.copy2(BACKUP, OUTPUT)

with open(OUTPUT, 'rb') as f:
    data = bytearray(f.read())

print("Changements:")
print(f"  Header @ 0x{HEADER_COUNT:X}: 3 -> 5")
print(f"  Middle @ 0x{MIDDLE_COUNT:X}: 3 -> 5")

# Change both counts to 5
data[HEADER_COUNT] = 0x05
data[MIDDLE_COUNT] = 0x05

with open(OUTPUT, 'wb') as f:
    f.write(data)

print()
print("Version créée pour debug!")
print()
print("=" * 70)
print("INSTRUCTIONS DEBUG DUCKSTATION")
print("=" * 70)
print()
print("1. Charge cette version dans DuckStation")
print("2. Ouvre Debug -> CPU Debugger")
print("3. Va dans Cavern F1 A1 (ça va infinite load)")
print("4. Pendant l'infinite loading, pause (F10)")
print("5. Regarde le PC (Program Counter) - c'est où le jeu est bloqué")
print("6. Trouve la boucle qui attend quelque chose")
print()
print("Informations utiles:")
print(f"  Header count @ BLAZE 0x{HEADER_COUNT:X} = 5")
print(f"  Middle count @ BLAZE 0x{MIDDLE_COUNT:X} = 5")
print(f"  Animation section @ BLAZE 0xF7A900")
print()
print("Le jeu essaie probablement de:")
print("  - Charger 5 animation tables")
print("  - Lire 5 animation records")
print("  - Allouer 5 structures en mémoire")
print()
print("CHERCHE:")
print("  - Une boucle 'for i=0; i<count; i++'")
print("  - Un compteur qui s'incrémente jusqu'à header_count")
print("  - Une attente de lecture CD qui ne finit jamais")
print()
print("Une fois trouvé, rapporte:")
print("  - L'adresse RAM du code bloqué (PC)")
print("  - Les instructions assembleur autour")
print("  - Les valeurs des registres")
