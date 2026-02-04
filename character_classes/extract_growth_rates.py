#!/usr/bin/env python3
"""
Extract Growth Rates from SLES_008.45
Extrait et sauvegarde les growth rates dans les fichiers JSON
"""

import json
import os

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"
GROWTH_RATES_OFFSET = 0x0002BBFE  # File offset
GROWTH_RATES_MEM_ADDR = 0x8003B3FE  # Memory address when loaded

CLASS_NAMES = ["Warrior", "Priest", "Rogue", "Sorcerer", "Hunter", "Elf", "Dwarf", "Fairy"]
STAT_NAMES = ["hp_per_level", "mp_per_level", "strength_per_level", "defense_per_level",
              "magic_per_level", "magic_defense_per_level", "speed_per_level", "luck_per_level"]

def extract_growth_rates(file_path, offset):
    """Extrait les growth rates"""
    with open(file_path, 'rb') as f:
        f.seek(offset)
        data = f.read(64)  # 8 classes x 8 stats

    growth_rates = {}

    for class_idx, class_name in enumerate(CLASS_NAMES):
        row_offset = class_idx * 8
        stats = {}

        for stat_idx, stat_name in enumerate(STAT_NAMES):
            value = data[row_offset + stat_idx]
            stats[stat_name] = value

        growth_rates[class_name] = stats

    return growth_rates

def update_json_files(growth_rates):
    """Met à jour les fichiers JSON des classes"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    for class_name in CLASS_NAMES:
        json_path = os.path.join(script_dir, f"{class_name}.json")

        # Lire le JSON existant
        with open(json_path, 'r', encoding='utf-8') as f:
            class_data = json.load(f)

        # Mettre à jour les growth rates
        stats = growth_rates[class_name]
        class_data['stat_growth'] = {
            **stats,
            "notes": f"Extracted from SLES_008.45 @ 0x{GROWTH_RATES_OFFSET:08X}"
        }

        # Mettre à jour le statut de recherche
        class_data['research_status']['growth_rates_found'] = True
        class_data['research_status']['last_updated'] = "2026-02-04"

        # Sauvegarder
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(class_data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Mis a jour: {class_name}.json")

def create_summary_file(growth_rates):
    """Crée un fichier résumé"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    summary_path = os.path.join(script_dir, "GROWTH_RATES_FOUND.md")

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# Growth Rates - TROUVES!\n\n")
        f.write(f"**Localisation:** SLES_008.45 @ 0x{GROWTH_RATES_OFFSET:08X}\n")
        f.write(f"**Adresse mémoire:** 0x{GROWTH_RATES_MEM_ADDR:08X}\n")
        f.write(f"**Date:** 2026-02-04\n\n")
        f.write("---\n\n")
        f.write("## Growth Rates par Classe\n\n")

        for class_name in CLASS_NAMES:
            stats = growth_rates[class_name]
            f.write(f"### {class_name}\n\n")
            f.write(f"- **HP/level:** {stats['hp_per_level']}\n")
            f.write(f"- **MP/level:** {stats['mp_per_level']}\n")
            f.write(f"- **Strength/level:** {stats['strength_per_level']}\n")
            f.write(f"- **Defense/level:** {stats['defense_per_level']}\n")
            f.write(f"- **Magic/level:** {stats['magic_per_level']}\n")
            f.write(f"- **Magic Defense/level:** {stats['magic_defense_per_level']}\n")
            f.write(f"- **Speed/level:** {stats['speed_per_level']}\n")
            f.write(f"- **Luck/level:** {stats['luck_per_level']}\n\n")

        f.write("---\n\n")
        f.write("## Analyse\n\n")

        # Calculer des stats
        hp_vals = [growth_rates[c]['hp_per_level'] for c in CLASS_NAMES]
        mp_vals = [growth_rates[c]['mp_per_level'] for c in CLASS_NAMES]

        f.write(f"- **HP range:** {min(hp_vals)}-{max(hp_vals)} par niveau\n")
        f.write(f"- **MP range:** {min(mp_vals)}-{max(mp_vals)} par niveau\n")
        f.write(f"- **Classe HP max:** {CLASS_NAMES[hp_vals.index(max(hp_vals))]} ({max(hp_vals)}/lv)\n")
        f.write(f"- **Classe HP min:** {CLASS_NAMES[hp_vals.index(min(hp_vals))]} ({min(hp_vals)}/lv)\n")
        f.write(f"- **Classe MP max:** {CLASS_NAMES[mp_vals.index(max(mp_vals))]} ({max(mp_vals)}/lv)\n")
        f.write(f"- **Classe MP min:** {CLASS_NAMES[mp_vals.index(min(mp_vals))]} ({min(mp_vals)}/lv)\n\n")

        f.write("---\n\n")
        f.write("## Modification\n\n")
        f.write("Pour modifier les growth rates:\n\n")
        f.write("```bash\n")
        f.write("py -3 patch_growth_rates.py\n")
        f.write("```\n\n")
        f.write("Editez les fichiers JSON des classes, puis exécutez le patcher.\n\n")

    print(f"[OK] Cree: GROWTH_RATES_FOUND.md")

def main():
    """Fonction principale"""
    print("="*80)
    print("EXTRACTION DES GROWTH RATES")
    print("="*80)
    print()

    if not os.path.exists(SLES_PATH):
        print(f"ERREUR: {SLES_PATH} non trouve")
        return

    print(f"Source: {SLES_PATH}")
    print(f"Offset: 0x{GROWTH_RATES_OFFSET:08X}")
    print()

    # Extraire
    growth_rates = extract_growth_rates(SLES_PATH, GROWTH_RATES_OFFSET)

    # Afficher
    print("GROWTH RATES EXTRAITS:")
    print("-" * 80)
    print(f"{'Classe':<12} | {'HP':<4} {'MP':<4} {'STR':<4} {'DEF':<4} {'MAG':<4} {'MDEF':<4} {'SPD':<4} {'LUK':<4}")
    print("-" * 80)

    for class_name in CLASS_NAMES:
        stats = growth_rates[class_name]
        print(f"{class_name:<12} | "
              f"{stats['hp_per_level']:<4} "
              f"{stats['mp_per_level']:<4} "
              f"{stats['strength_per_level']:<4} "
              f"{stats['defense_per_level']:<4} "
              f"{stats['magic_per_level']:<4} "
              f"{stats['magic_defense_per_level']:<4} "
              f"{stats['speed_per_level']:<4} "
              f"{stats['luck_per_level']:<4}")

    print()
    print("="*80)
    print("MISE A JOUR DES FICHIERS JSON")
    print("="*80)
    print()

    update_json_files(growth_rates)

    print()
    print("="*80)
    print("CREATION DU RESUME")
    print("="*80)
    print()

    create_summary_file(growth_rates)

    print()
    print("="*80)
    print("TERMINE!")
    print("="*80)
    print()
    print("Fichiers mis a jour:")
    print("  - Warrior.json, Priest.json, Rogue.json, etc.")
    print("  - GROWTH_RATES_FOUND.md")
    print()
    print("Prochaine etape:")
    print("  - Creer patch_growth_rates.py pour modifier les valeurs")
    print()

if __name__ == "__main__":
    main()
