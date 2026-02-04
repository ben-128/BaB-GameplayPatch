#!/usr/bin/env python3
"""
Filter growth rate candidates based on known class characteristics
"""

BLAZE_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\work\BLAZE.ALL"

CLASS_NAMES = ["Warrior", "Priest", "Rogue", "Sorcerer", "Hunter", "Elf", "Dwarf", "Fairy"]

# Indices de classes
WARRIOR = 0
DWARF = 6
SORCERER = 3
PRIEST = 1

def search_with_criteria(data, pattern_size):
    """Cherche avec critères spécifiques basés sur les classes"""

    total_size = 8 * pattern_size
    candidates = []

    for offset in range(len(data) - total_size):
        block = data[offset:offset+total_size]

        # Toutes valeurs entre 0 et 20
        if not all(0 <= b <= 20 for b in block):
            continue

        # Extraire les stats par classe
        classes = [block[i*pattern_size:(i+1)*pattern_size] for i in range(8)]

        warrior_stats = list(classes[WARRIOR])
        dwarf_stats = list(classes[DWARF])
        sorcerer_stats = list(classes[SORCERER])
        priest_stats = list(classes[PRIEST])

        # CRITÈRE 1: Dwarf doit avoir au moins une stat TRÈS BASSE (≤3)
        # (MP/Int car classe physique)
        if min(dwarf_stats) > 3:
            continue

        # CRITÈRE 2: Warrior et Dwarf doivent avoir au moins une stat ÉLEVÉE (≥8)
        # (Str probablement)
        if max(warrior_stats) < 8 or max(dwarf_stats) < 8:
            continue

        # CRITÈRE 3: Sorcerer doit avoir au moins une stat ÉLEVÉE (≥7)
        # (Int/Magie)
        if max(sorcerer_stats) < 7:
            continue

        # CRITÈRE 4: Bonne variance globale
        for col in range(pattern_size):
            values = [classes[i][col] for i in range(8)]
            variance = max(values) - min(values)
            if variance >= 5:  # Au moins une colonne avec grande variance
                candidates.append((offset, block))
                break

    return candidates

def analyze_candidate(offset, data, pattern_size):
    """Analyse détaillée d'un candidat"""

    print(f"\n{'='*80}")
    print(f"Offset: 0x{offset:08X} ({offset:,})")
    print('='*80)

    # Afficher par classe
    for i in range(8):
        class_offset = i * pattern_size
        stats = data[class_offset:class_offset+pattern_size]

        stats_str = " ".join(f"{s:2d}" for s in stats)

        # Marquer les valeurs extrêmes
        min_val = min(stats)
        max_val = max(stats)

        markers = []
        if i == WARRIOR and max_val >= 8:
            markers.append("STR haute?")
        if i == DWARF and min_val <= 3:
            markers.append("MP/INT basse?")
        if i == DWARF and max_val >= 8:
            markers.append("STR haute?")
        if i == SORCERER and max_val >= 7:
            markers.append("INT/MAG haute?")

        marker_str = "  <- " + ", ".join(markers) if markers else ""

        print(f"  {CLASS_NAMES[i]:<12}: [{stats_str}]{marker_str}")

    # Analyse par colonne
    print()
    print("  Analyse des colonnes:")

    for col in range(pattern_size):
        values = [data[i*pattern_size + col] for i in range(8)]
        variance = max(values) - min(values)
        avg = sum(values) / len(values)

        # Identifier le pattern
        pattern_desc = ""

        # Si Dwarf/Warrior ont des valeurs basses -> probablement MP/Int
        if values[DWARF] <= 3 and values[WARRIOR] <= 6:
            pattern_desc = " <- MP/INT? (bas pour Dwarf/Warrior)"

        # Si Dwarf/Warrior ont des valeurs hautes -> probablement Str/Con
        elif values[DWARF] >= 8 and values[WARRIOR] >= 8:
            pattern_desc = " <- STR/CON? (haut pour Dwarf/Warrior)"

        # Si Sorcerer a la valeur la plus haute -> probablement Int
        elif values[SORCERER] == max(values) and values[SORCERER] >= 9:
            pattern_desc = " <- INT? (max pour Sorcerer)"

        print(f"    [{col}] range {min(values):2d}-{max(values):2d}, var={variance:2d}, avg={avg:4.1f}{pattern_desc}")

def main():
    print("="*80)
    print("FILTRAGE INTELLIGENT DES CANDIDATS")
    print("="*80)
    print()
    print("Criteres:")
    print("  - Dwarf: au moins une stat <=3 (MP/Int bas)")
    print("  - Warrior/Dwarf: au moins une stat >=8 (Str haute)")
    print("  - Sorcerer: au moins une stat >=7 (Int/Mag haute)")
    print("  - Variance significative (>=5) dans au moins une colonne")
    print()

    with open(BLAZE_PATH, 'rb') as f:
        data = f.read()

    print(f"Taille BLAZE.ALL: {len(data):,} bytes")
    print()

    # Tester différentes tailles
    for pattern_size in [6, 8]:
        print("="*80)
        print(f"PATTERN: 8 classes × {pattern_size} bytes")
        print("="*80)

        candidates = search_with_criteria(data, pattern_size)

        print(f"\nTrouvé {len(candidates)} candidats prometteurs")

        if candidates:
            # Limiter à 20 pour ne pas spammer
            for offset, block in candidates[:20]:
                analyze_candidate(offset, block, pattern_size)

        print()

if __name__ == "__main__":
    main()
