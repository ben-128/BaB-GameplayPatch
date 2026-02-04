#!/usr/bin/env python3
"""
Create In-Game Tests - Crée des versions de test avec valeurs absurdes
Pour identifier quel byte = quelle stat en testant in-game
"""

import os
import shutil

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"
GROWTH_RATES_OFFSET = 0x0002BBFE

CLASS_NAMES = ["Warrior", "Priest", "Rogue", "Sorcerer", "Hunter", "Elf", "Dwarf", "Fairy"]

def create_test_for_byte(byte_index, test_value=255):
    """
    Crée un fichier SLES de test où UN byte est mis à 255 pour TOUTES les classes

    Args:
        byte_index: 0-7 (quelle position tester)
        test_value: Valeur absurde (défaut: 255 = max uint8)
    """
    # Lire le fichier original
    with open(SLES_PATH, 'rb') as f:
        data = bytearray(f.read())

    print(f"\n{'='*80}")
    print(f"TEST BYTE[{byte_index}] - Valeur: {test_value}")
    print('='*80)
    print()

    # Modifier ce byte pour TOUTES les 8 classes
    for class_idx in range(8):
        class_name = CLASS_NAMES[class_idx]
        offset = GROWTH_RATES_OFFSET + (class_idx * 8) + byte_index

        original = data[offset]
        data[offset] = test_value

        print(f"  {class_name:<12}: byte[{byte_index}] = {original:3d} -> {test_value:3d}")

    # Créer le fichier de test
    test_filename = f"SLES_008.45_TEST_BYTE{byte_index}"
    test_path = SLES_PATH.replace("SLES_008.45", test_filename)

    with open(test_path, 'wb') as f:
        f.write(data)

    print()
    print(f"[OK] Cree: {test_filename}")
    print(f"     Toutes les classes: byte[{byte_index}] = {test_value}")

    return test_path

def create_all_test_versions():
    """Crée 8 versions de test (une par byte)"""
    print("="*80)
    print("CREATION DES VERSIONS DE TEST IN-GAME")
    print("="*80)
    print()
    print("Strategie:")
    print("  - Creer 8 fichiers SLES_008.45 de test")
    print("  - Chaque version modifie UN byte pour TOUTES les classes")
    print("  - Valeur absurde: 255 (pour identifier facilement)")
    print()
    print("Test:")
    print("  1. Remplacer SLES_008.45 par SLES_008.45_TEST_BYTEN")
    print("  2. Creer N'IMPORTE QUELLE classe")
    print("  3. Monter au niveau 2")
    print("  4. Noter quelle stat EXPLOSE (+255 ou derive)")
    print()

    # Créer backup
    backup_path = SLES_PATH + ".original_backup"
    if not os.path.exists(backup_path):
        shutil.copy2(SLES_PATH, backup_path)
        print(f"[OK] Backup cree: {backup_path}")
    else:
        print(f"[INFO] Backup existe deja: {backup_path}")

    print()

    # Créer les 8 versions de test
    test_files = []
    for byte_idx in range(8):
        test_path = create_test_for_byte(byte_idx, test_value=255)
        test_files.append((byte_idx, test_path))

    print()
    print("="*80)
    print("FICHIERS CREES")
    print("="*80)
    print()

    for byte_idx, test_path in test_files:
        filename = os.path.basename(test_path)
        print(f"  [{byte_idx}] {filename}")

    print()
    print("="*80)
    print("INSTRUCTIONS DE TEST")
    print("="*80)
    print()
    print("Pour identifier CHAQUE byte:")
    print()
    print("1. Copier SLES_008.45_TEST_BYTE0 vers SLES_008.45 sur le CD")
    print("2. Lancer le jeu")
    print("3. Creer N'IMPORTE QUELLE classe")
    print("4. Tuer un monstre pour monter niveau 2")
    print("5. Noter quelle stat a EXPLOSE")
    print()
    print("Repeter pour TEST_BYTE1, TEST_BYTE2, etc.")
    print()
    print("Stats a observer:")
    print("  - HP, MP (si l'un explose de +2000+)")
    print("  - Str, Wil, Con, Int, Agl, Pow (si l'un monte de +255)")
    print()

    # Créer fichier de résultats
    results_path = os.path.join(
        os.path.dirname(__file__),
        "TEST_RESULTS.txt"
    )

    with open(results_path, 'w', encoding='utf-8') as f:
        f.write("RESULTATS DES TESTS IN-GAME\n")
        f.write("="*80 + "\n\n")
        f.write("Instructions:\n")
        f.write("  - Pour chaque TEST_BYTEN, noter quelle stat explose\n")
        f.write("  - Remplir le tableau ci-dessous\n\n")
        f.write("-"*80 + "\n\n")
        f.write("| Byte | Fichier de test      | Stat identifiee | Valeur observee |\n")
        f.write("|------|----------------------|-----------------|------------------|\n")
        for i in range(8):
            f.write(f"| [{i}]  | SLES_008.45_TEST_BYTE{i} | ???             | ???              |\n")
        f.write("\n")
        f.write("-"*80 + "\n\n")
        f.write("Stats possibles:\n")
        f.write("  - HP (si monte de ~2000+, car derive de Con/etc)\n")
        f.write("  - MP (si monte de ~2000+, car derive de Int/Pow/etc)\n")
        f.write("  - Str (Strength)\n")
        f.write("  - Wil (Will)\n")
        f.write("  - Con (Constitution)\n")
        f.write("  - Int (Intelligence)\n")
        f.write("  - Agl (Agility)\n")
        f.write("  - Pow (Power)\n")
        f.write("\n")
        f.write("Notes:\n")
        f.write("  - Si HP/MP explosent, c'est que le byte controle leur growth direct\n")
        f.write("  - Ou bien le byte controle une stat qui influence HP/MP (Con->HP, Int->MP)\n")

    print(f"[OK] Fichier de resultats cree: TEST_RESULTS.txt")
    print()
    print("="*80)
    print("PRET A TESTER!")
    print("="*80)
    print()

if __name__ == "__main__":
    create_all_test_versions()
