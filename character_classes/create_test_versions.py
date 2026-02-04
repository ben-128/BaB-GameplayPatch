#!/usr/bin/env python3
"""
Create Test Versions - Crée des versions de test avec valeurs extrêmes
Pour identifier quel byte correspond à quelle stat in-game
"""

import json
import os
import shutil

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"
GROWTH_RATES_OFFSET = 0x0002BBFE

def create_test_version(byte_index, test_value=50):
    """
    Crée une version de test où un seul byte est modifié

    Args:
        byte_index: 0-7 (quelle position tester)
        test_value: Valeur extrême à mettre (défaut: 50)
    """
    # Backup original
    backup_path = SLES_PATH + f".test_byte{byte_index}.backup"
    if not os.path.exists(backup_path):
        shutil.copy2(SLES_PATH, backup_path)

    # Lire le fichier
    with open(SLES_PATH, 'rb') as f:
        data = bytearray(f.read())

    # Modifier UNIQUEMENT le byte testé pour le Warrior (première classe)
    warrior_offset = GROWTH_RATES_OFFSET + byte_index
    original_value = data[warrior_offset]
    data[warrior_offset] = test_value

    # Écrire
    test_file = SLES_PATH.replace("SLES_008.45", f"SLES_008.45_TEST_BYTE{byte_index}")
    with open(test_file, 'wb') as f:
        f.write(data)

    print(f"[OK] Créé: {test_file}")
    print(f"     Byte[{byte_index}] Warrior: {original_value} -> {test_value}")
    print(f"     Backup: {backup_path}")
    print()

    return test_file

def create_all_tests():
    """Crée 8 versions de test (une par byte)"""
    print("="*80)
    print("CRÉATION DES VERSIONS DE TEST")
    print("="*80)
    print()
    print("Création de 8 fichiers SLES_008.45 de test:")
    print("  - Chaque version modifie UN SEUL byte du Warrior à 50")
    print("  - Créer un Warrior et monter au niveau 2")
    print("  - Noter quelle stat augmente de ~50")
    print()
    print("-"*80)
    print()

    test_files = []
    for i in range(8):
        test_file = create_test_version(i, test_value=50)
        test_files.append((i, test_file))

    print("="*80)
    print("INSTRUCTIONS DE TEST")
    print("="*80)
    print()
    print("Pour CHAQUE fichier de test:")
    print()
    print("1. Copier SLES_008.45_TEST_BYTEN sur le CD (remplacer SLES_008.45)")
    print("2. Lancer le jeu")
    print("3. Créer un WARRIOR")
    print("4. Noter ses stats au niveau 1")
    print("5. Monter au niveau 2 (tuer un monstre)")
    print("6. Noter quelle stat a augmenté BEAUCOUP (~50)")
    print()
    print("-"*80)
    print()
    print("Tableau à remplir:")
    print()
    print("| Fichier | Byte | Stat qui monte de ~50 |")
    print("|---------|------|-----------------------|")
    for i, _ in test_files:
        print(f"| TEST_BYTE{i} | [{i}] | ??? |")
    print()
    print("Exemple:")
    print("  Si TEST_BYTE2 fait monter Str de 50 -> byte[2] = Str")
    print()

    # Créer un fichier de notes
    notes_path = os.path.join(
        os.path.dirname(SLES_PATH),
        "GameplayPatch",
        "character_classes",
        "TEST_RESULTS.md"
    )

    with open(notes_path, 'w', encoding='utf-8') as f:
        f.write("# Test Results - Identification des Growth Rates\n\n")
        f.write("## Instructions\n\n")
        f.write("Pour chaque fichier TEST_BYTEN:\n")
        f.write("1. Remplacer SLES_008.45 sur le CD\n")
        f.write("2. Créer un Warrior niveau 1\n")
        f.write("3. Monter au niveau 2\n")
        f.write("4. Noter quelle stat a augmenté de ~50\n\n")
        f.write("## Résultats\n\n")
        f.write("| Byte | Stat identifiée | Notes |\n")
        f.write("|------|-----------------|-------|\n")
        for i in range(8):
            f.write(f"| [{i}] | ??? | |\n")
        f.write("\n")
        f.write("## Stats possibles\n\n")
        f.write("- HP, MP\n")
        f.write("- Str (Strength)\n")
        f.write("- Wil (Will)\n")
        f.write("- Con (Constitution)\n")
        f.write("- Int (Intelligence)\n")
        f.write("- Agl (Agility)\n")
        f.write("- Pow (Power)\n")

    print(f"[OK] Fichier de notes créé: TEST_RESULTS.md")
    print()

if __name__ == "__main__":
    create_all_tests()
