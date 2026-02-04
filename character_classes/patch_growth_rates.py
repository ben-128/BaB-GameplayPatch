#!/usr/bin/env python3
"""
Patch Growth Rates - Modifie les growth rates dans SLES_008.45
Lit les valeurs depuis les fichiers JSON et patch l'exécutable
"""

import json
import os
import shutil
from datetime import datetime

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"
GROWTH_RATES_OFFSET = 0x0002BBFE

CLASS_NAMES = ["Warrior", "Priest", "Rogue", "Sorcerer", "Hunter", "Elf", "Dwarf", "Fairy"]
STAT_NAMES = ["hp_per_level", "mp_per_level", "strength_per_level", "defense_per_level",
              "magic_per_level", "magic_defense_per_level", "speed_per_level", "luck_per_level"]

def read_growth_rates_from_json():
    """Lit les growth rates depuis les fichiers JSON"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    growth_rates = {}

    for class_name in CLASS_NAMES:
        json_path = os.path.join(script_dir, f"{class_name}.json")

        with open(json_path, 'r', encoding='utf-8') as f:
            class_data = json.load(f)

        stats = class_data.get('stat_growth', {})

        # Convertir en liste de bytes
        byte_values = []
        for stat_name in STAT_NAMES:
            value = stats.get(stat_name)
            if value is None:
                print(f"AVERTISSEMENT: {class_name}.{stat_name} est null, utilisation de 0")
                value = 0

            if not isinstance(value, int) or value < 0 or value > 255:
                print(f"ERREUR: {class_name}.{stat_name} = {value} (invalide)")
                return None

            byte_values.append(value)

        growth_rates[class_name] = byte_values

    return growth_rates

def create_backup(file_path):
    """Crée une sauvegarde du fichier"""
    backup_path = file_path + ".backup"

    if not os.path.exists(backup_path):
        shutil.copy2(file_path, backup_path)
        print(f"[OK] Backup cree: {backup_path}")
        return True
    else:
        print(f"[INFO] Backup existe deja: {backup_path}")
        return True

def patch_file(file_path, offset, growth_rates):
    """Patch le fichier avec les nouvelles valeurs"""
    # Lire le fichier
    with open(file_path, 'rb') as f:
        data = bytearray(f.read())

    # Vérifier la taille
    if offset + 64 > len(data):
        print(f"ERREUR: Offset {offset} trop grand pour le fichier")
        return False

    # Lire les valeurs actuelles
    print()
    print("VALEURS ACTUELLES vs NOUVELLES:")
    print("-" * 80)
    print(f"{'Classe':<12} | {'Stat':<8} | {'Avant':<6} | {'Apres':<6} | {'Change':<6}")
    print("-" * 80)

    changes_made = False

    for class_idx, class_name in enumerate(CLASS_NAMES):
        new_values = growth_rates[class_name]
        row_offset = offset + (class_idx * 8)

        for stat_idx, stat_name in enumerate(STAT_NAMES):
            current_value = data[row_offset + stat_idx]
            new_value = new_values[stat_idx]

            changed = "OUI" if current_value != new_value else "Non"
            if current_value != new_value:
                changes_made = True

            stat_short = stat_name.replace('_per_level', '').replace('_', '')[:6]
            print(f"{class_name:<12} | {stat_short:<8} | {current_value:<6} | {new_value:<6} | {changed:<6}")

            # Appliquer le changement
            data[row_offset + stat_idx] = new_value

    print("-" * 80)
    print()

    if not changes_made:
        print("[INFO] Aucun changement necessaire")
        return True

    # Écrire le fichier modifié
    with open(file_path, 'wb') as f:
        f.write(data)

    print(f"[OK] Fichier patche: {file_path}")
    return True

def verify_patch(file_path, offset, growth_rates):
    """Vérifie que le patch a été appliqué correctement"""
    with open(file_path, 'rb') as f:
        f.seek(offset)
        data = f.read(64)

    print()
    print("VERIFICATION DU PATCH:")
    print("-" * 80)

    all_ok = True

    for class_idx, class_name in enumerate(CLASS_NAMES):
        expected_values = growth_rates[class_name]
        row_offset = class_idx * 8

        for stat_idx in range(8):
            actual = data[row_offset + stat_idx]
            expected = expected_values[stat_idx]

            if actual != expected:
                stat_name = STAT_NAMES[stat_idx]
                print(f"ERREUR: {class_name}.{stat_name}: attendu {expected}, trouve {actual}")
                all_ok = False

    if all_ok:
        print("[OK] Toutes les valeurs verifiees avec succes!")
    else:
        print("[ERREUR] Certaines valeurs ne correspondent pas!")

    print("-" * 80)
    print()

    return all_ok

def main():
    """Fonction principale"""
    print("="*80)
    print("PATCHER DES GROWTH RATES")
    print("="*80)
    print()

    if not os.path.exists(SLES_PATH):
        print(f"ERREUR: {SLES_PATH} non trouve")
        return

    print(f"Fichier cible: {SLES_PATH}")
    print(f"Offset: 0x{GROWTH_RATES_OFFSET:08X}")
    print()

    # Lire les growth rates depuis JSON
    print("="*80)
    print("LECTURE DES FICHIERS JSON")
    print("="*80)
    print()

    growth_rates = read_growth_rates_from_json()

    if growth_rates is None:
        print()
        print("ERREUR: Impossible de lire les growth rates depuis les JSON")
        return

    print(f"[OK] Growth rates lus pour {len(growth_rates)} classes")
    print()

    # Créer backup
    print("="*80)
    print("CREATION DU BACKUP")
    print("="*80)
    print()

    if not create_backup(SLES_PATH):
        print()
        print("ERREUR: Impossible de creer le backup")
        return

    print()

    # Patcher
    print("="*80)
    print("APPLICATION DU PATCH")
    print("="*80)

    if not patch_file(SLES_PATH, GROWTH_RATES_OFFSET, growth_rates):
        print()
        print("ERREUR: Echec du patch")
        return

    print()

    # Vérifier
    print("="*80)
    print("VERIFICATION")
    print("="*80)

    if not verify_patch(SLES_PATH, GROWTH_RATES_OFFSET, growth_rates):
        print()
        print("ERREUR: La verification a echoue!")
        return

    # Succès
    print("="*80)
    print("PATCH APPLIQUE AVEC SUCCES!")
    print("="*80)
    print()
    print("Les growth rates ont ete modifies dans SLES_008.45")
    print()
    print("Pour tester:")
    print("  1. Copier le SLES_008.45 modifie sur le CD")
    print("  2. Lancer le jeu")
    print("  3. Creer un personnage et monter de niveau")
    print("  4. Verifier que les stats augmentent selon les nouvelles valeurs")
    print()
    print("Pour restaurer l'original:")
    print(f"  Copier SLES_008.45.backup vers SLES_008.45")
    print()

if __name__ == "__main__":
    main()
