#!/usr/bin/env python3
"""
Find all PS-X EXE occurrences in BIN
"""

BIN_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\Blaze & Blade - Patched.bin"

print("Recherche de toutes les occurrences de PS-X EXE...")
print()

with open(BIN_PATH, 'rb') as f:
    data = f.read()

sig = b'PS-X EXE'
offset = 0
count = 0
occurrences = []

while True:
    pos = data.find(sig, offset)
    if pos == -1:
        break

    # Lire un peu de contexte
    context_start = max(0, pos - 16)
    context_end = min(len(data), pos + 32)
    context = data[context_start:context_end]

    occurrences.append(pos)
    count += 1

    print(f"Occurrence {count}: offset 0x{pos:08X} ({pos:,})")
    print(f"  Context: {context[:16].hex()} ...")
    print()

    offset = pos + 1

print("="*80)
print(f"Total: {count} occurrences de 'PS-X EXE' trouvees")
print("="*80)
print()

if count > 1:
    print("PROBLEME IDENTIFIE!")
    print()
    print("Il y a plusieurs copies du SLES dans le BIN.")
    print("J'ai probablement patche la MAUVAISE copie!")
    print()
    print("Le BIOS charge probablement depuis la PREMIERE occurrence,")
    print("mais j'ai peut-etre modifie une copie plus loin dans le fichier.")
    print()
    print("Solution: Modifier TOUTES les occurrences.")
elif count == 1:
    print("Une seule occurrence trouvee.")
    print("Le probleme vient d'ailleurs (EDC/ECC?).")
