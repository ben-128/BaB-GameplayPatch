#!/usr/bin/env python3
"""
Search BLAZE.ALL for growth rates
Cherche des patterns de 8 classes avec variance
"""

BLAZE_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\BLAZE.ALL"

CLASS_NAMES = ["Warrior", "Priest", "Rogue", "Sorcerer", "Hunter", "Elf", "Dwarf", "Fairy"]

def search_patterns(data, pattern_size):
    """Cherche des patterns de 8 classes × pattern_size bytes"""

    total_size = 8 * pattern_size
    candidates = []

    print(f"Recherche de patterns 8×{pattern_size} ({total_size} bytes)...")
    print()

    for offset in range(len(data) - total_size):
        block = data[offset:offset+total_size]

        # Vérifier que les valeurs sont plausibles (0-20 pour growth rates)
        valid = all(0 <= b <= 20 for b in block)
        if not valid:
            continue

        # Vérifier qu'il y a de la variance entre les classes
        classes = [block[i*pattern_size:(i+1)*pattern_size] for i in range(8)]

        # Calculer la variance sur le premier byte de chaque classe
        first_bytes = [c[0] for c in classes]
        variance = max(first_bytes) - min(first_bytes)

        if variance < 2:  # Au moins 2 points de différence
            continue

        # Vérifier qu'il n'y a pas trop de zéros
        zero_count = sum(1 for b in block if b == 0)
        if zero_count > total_size * 0.3:  # Plus de 30% de zéros = suspect
            continue

        candidates.append((offset, block))

    print(f"Trouvé {len(candidates)} candidats")
    return candidates

def analyze_candidate(offset, data, pattern_size):
    """Analyse un candidat"""

    print(f"\nOffset: 0x{offset:08X} ({offset:,})")
    print("-" * 80)

    # Afficher par classe
    for i in range(8):
        class_offset = i * pattern_size
        stats = data[class_offset:class_offset+pattern_size]

        stats_str = " ".join(f"{s:2d}" for s in stats)
        print(f"  {CLASS_NAMES[i]:<12}: [{stats_str}]")

    # Stats d'analyse
    print()

    # Variance par colonne
    for col in range(pattern_size):
        values = [data[i*pattern_size + col] for i in range(8)]
        variance = max(values) - min(values)
        avg = sum(values) / len(values)
        print(f"  Byte[{col}]: range {min(values):2d}-{max(values):2d}, variance={variance:2d}, avg={avg:4.1f}")

def main():
    print("="*80)
    print("RECHERCHE GROWTH RATES DANS BLAZE.ALL")
    print("="*80)
    print()

    with open(BLAZE_PATH, 'rb') as f:
        data = f.read()

    print(f"Taille BLAZE.ALL: {len(data):,} bytes")
    print()

    # Chercher différentes tailles de patterns
    for pattern_size in [6, 7, 8, 10]:
        print("="*80)
        print(f"PATTERN: 8 classes × {pattern_size} bytes")
        print("="*80)
        print()

        candidates = search_patterns(data, pattern_size)

        if candidates:
            # Afficher les 10 premiers
            for idx, (offset, block) in enumerate(candidates[:10]):
                analyze_candidate(offset, block, pattern_size)

                if idx < len(candidates) - 1:
                    print()

        print()

    print("="*80)
    print("RECHERCHE TERMINEE")
    print("="*80)

if __name__ == "__main__":
    main()
