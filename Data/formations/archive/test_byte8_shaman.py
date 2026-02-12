#!/usr/bin/env python3
"""
TEST: Changer byte[8] du Shaman pour voir l'effet sur les sorts.

Ce script modifie byte[8] des records Shaman dans Cavern F1 A1:
- Formation 0, Records 5-6 (Shamans): byte[8] = 0x01 -> 0x02 (Bat slot)

Hypothèse: Si byte[8] contrôle l'entity type, le Shaman devrait:
- Avoir visuel de Bat
- Avoir comportement de Bat
- Lancer FireBullet au lieu de Sleep

Si ça ne change que les sorts -> byte[8] ne contrôle PAS l'entity type!
"""

import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BLAZE_ALL = PROJECT_ROOT / "output" / "BLAZE.ALL"

def main():
    print("=" * 70)
    print("  TEST: Modification byte[8] Shaman -> Bat")
    print("=" * 70)
    print()

    if not BLAZE_ALL.exists():
        print(f"ERREUR: {BLAZE_ALL} n'existe pas!")
        print("Lancez d'abord build_gameplay_patch.bat")
        return 1

    # Lire BLAZE.ALL
    with open(BLAZE_ALL, 'r+b') as f:
        data = bytearray(f.read())
        print(f"BLAZE.ALL: {len(data):,} bytes")
        print()

        # Cavern F1 A1 Formation 0 starts at 0xF7AFFC
        # Record 5 (Shaman 1) = 0xF7AFFC + 5*32 = 0xF7B09C
        # Record 6 (Shaman 2) = 0xF7AFFC + 6*32 = 0xF7B0BC

        offsets = [
            0xF7B09C,  # Shaman 1
            0xF7B0BC,  # Shaman 2
        ]

        print("Shamans à modifier:")
        for i, offset in enumerate(offsets, 1):
            current_byte8 = data[offset + 8]
            print(f"  Shaman {i} @ {hex(offset)}")
            print(f"    byte[8] actuel: {current_byte8:02x} (0x01 = Shaman)")
            print()

        # Demander confirmation
        print("MODIFICATION: byte[8] = 0x01 -> 0x02 (Bat)")
        print()
        response = input("Continuer? (o/n): ").lower()

        if response != 'o':
            print("Annulé.")
            return 0

        # Appliquer les modifications
        for i, offset in enumerate(offsets, 1):
            old_val = data[offset + 8]
            new_val = 0x02  # Bat slot

            data[offset + 8] = new_val

            print(f"  Shaman {i}: byte[8] {old_val:02x} -> {new_val:02x}")

        # Écrire
        f.seek(0)
        f.write(data)
        print()
        print("BLAZE.ALL modifié!")
        print()

    print("=" * 70)
    print("  TEST PRÊT")
    print("=" * 70)
    print()
    print("Prochaines étapes:")
    print("  1. Relancer build_gameplay_patch.bat (Step 10-11 seulement)")
    print("  2. Tester en jeu: Cavern Floor 1 Area 1, Formation 0")
    print()
    print("Attendu si byte[8] contrôle entity type:")
    print("  - Shamans apparaissent comme BATS (visuel, comportement)")
    print("  - Lancent FireBullet")
    print()
    print("Attendu si byte[8] ne contrôle QUE les sorts:")
    print("  - Shamans gardent visuel/stats de Shaman")
    print("  - Mais lancent FireBullet au lieu de Sleep")
    print()

    return 0

if __name__ == '__main__':
    exit(main())
