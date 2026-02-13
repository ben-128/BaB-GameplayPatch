"""
test_triggers_system.py
Système de test pour identifier les triggers de portes dans LEVELS.DAT

Stratégie:
1. Extraire tous les triggers candidats
2. Créer des versions patchées qui désactivent différents groupes
3. Tester en jeu pour voir quelles portes disparaissent
4. Identifier les triggers de portes par élimination

Usage: py -3 test_triggers_system.py [command]

Commands:
  extract   - Extraire tous les triggers et créer la base de données
  patch N   - Créer un patch test qui désactive le groupe N (1-5)
  disable ID - Désactiver un trigger spécifique
  info      - Afficher infos sur les triggers
"""

from pathlib import Path
import struct
import json
import sys
import shutil

LEVELS_DAT = Path("../../Blaze  Blade - Eternal Quest (Europe)/extract/LEVELS.DAT")
OUTPUT_DIR = Path("trigger_tests")
TRIGGERS_DB = OUTPUT_DIR / "triggers_database.json"

def extract_all_triggers(data):
    """Extrait TOUS les triggers candidats de LEVELS.DAT"""
    print("=" * 70)
    print("  EXTRACTION DES TRIGGERS")
    print("=" * 70)

    triggers = []

    print("\nScanning LEVELS.DAT pour triggers potentiels...")

    # Scanner tout le fichier, pas juste 1MB
    for offset in range(0, len(data) - 12, 4):
        if offset % 1000000 == 0:
            print(f"  Progression: {offset/len(data)*100:.1f}%", end='\r')

        try:
            # Structure hypothétique: x, y, z, type, dest, flags
            x = struct.unpack_from('<h', data, offset)[0]
            y = struct.unpack_from('<h', data, offset + 2)[0]
            z = struct.unpack_from('<h', data, offset + 4)[0]
            event_type = struct.unpack_from('<H', data, offset + 6)[0]
            dest_id = struct.unpack_from('<H', data, offset + 8)[0]
            flags = struct.unpack_from('<H', data, offset + 10)[0]

            # Filtres pour triggers probables
            if not all(-2048 <= coord <= 2048 for coord in [x, y, z]):
                continue

            if event_type > 100:
                continue

            if dest_id > 100:
                continue

            # Skip patterns de padding
            if x == 0 and y == 0 and z == 0 and event_type == 0:
                continue

            # Skip patterns répétés suspects
            if x == y == z:
                continue

            triggers.append({
                'id': len(triggers) + 1,
                'offset': offset,
                'x': x, 'y': y, 'z': z,
                'type': event_type,
                'dest': dest_id,
                'flags': flags,
                'raw': data[offset:offset+12].hex()
            })

            if len(triggers) >= 500:  # Limite
                break

        except:
            pass

    print(f"\n\nTrouvé {len(triggers)} triggers candidats")
    return triggers

def save_triggers_database(triggers):
    """Sauvegarde la base de données des triggers"""
    OUTPUT_DIR.mkdir(exist_ok=True)

    db = {
        'total_triggers': len(triggers),
        'triggers': triggers,
        'groups': {
            'group_1': list(range(1, 21)),      # Triggers 1-20
            'group_2': list(range(21, 41)),     # Triggers 21-40
            'group_3': list(range(41, 61)),     # Triggers 41-60
            'group_4': list(range(61, 81)),     # Triggers 61-80
            'group_5': list(range(81, 101)),    # Triggers 81-100
        },
        'notes': {
            'strategy': 'Test each group by disabling triggers. Observe which doors disappear in-game.',
            'disable_method': 'Move trigger to (9999, 9999, 9999) - unreachable position'
        }
    }

    with open(TRIGGERS_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"\nBase de données sauvegardée: {TRIGGERS_DB}")
    return db

def create_test_patch(group_num):
    """Crée un patch test qui désactive un groupe de triggers"""
    print("=" * 70)
    print(f"  CRÉATION PATCH TEST - GROUPE {group_num}")
    print("=" * 70)

    if not TRIGGERS_DB.exists():
        print("\nERREUR: Base de données manquante. Exécutez d'abord 'extract'")
        return

    # Charger la DB
    with open(TRIGGERS_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    triggers = db['triggers']
    group_key = f'group_{group_num}'

    if group_key not in db['groups']:
        print(f"\nERREUR: Groupe {group_num} invalide (1-5)")
        return

    trigger_ids = db['groups'][group_key]

    print(f"\nGroupe {group_num}: Triggers {trigger_ids[0]}-{trigger_ids[-1]}")
    print(f"Nombre de triggers à désactiver: {len(trigger_ids)}")

    # Lire LEVELS.DAT
    data = bytearray(LEVELS_DAT.read_bytes())

    # Patcher les triggers du groupe
    disabled_count = 0
    for trigger in triggers:
        if trigger['id'] in trigger_ids:
            offset = trigger['offset']

            # Méthode 1: Déplacer à position inaccessible
            struct.pack_into('<h', data, offset, 9999)      # X
            struct.pack_into('<h', data, offset + 2, 9999)  # Y
            struct.pack_into('<h', data, offset + 4, 9999)  # Z

            print(f"  Désactivé trigger #{trigger['id']} @ 0x{offset:X}")
            disabled_count += 1

    print(f"\nTotal désactivé: {disabled_count} triggers")

    # Sauvegarder le fichier patché
    output_file = OUTPUT_DIR / f"LEVELS_TEST_GROUP{group_num}.DAT"
    with open(output_file, 'wb') as f:
        f.write(data)

    print(f"\nFichier patché créé: {output_file.name}")
    print(f"Taille: {len(data):,} bytes")

    # Créer un fichier de notes
    notes_file = OUTPUT_DIR / f"test_group{group_num}_notes.txt"
    with open(notes_file, 'w', encoding='utf-8') as f:
        f.write(f"PATCH TEST - GROUPE {group_num}\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Triggers désactivés: {trigger_ids[0]}-{trigger_ids[-1]}\n")
        f.write(f"Total: {disabled_count} triggers\n\n")
        f.write("INSTRUCTIONS:\n")
        f.write("1. Remplacer LEVELS.DAT dans le BIN par ce fichier\n")
        f.write("2. Lancer le jeu\n")
        f.write("3. Explorer les niveaux\n")
        f.write("4. Noter quelles PORTES ont disparu ou sont inaccessibles\n")
        f.write("5. Comparer avec les autres groupes\n\n")
        f.write("TRIGGERS DÉSACTIVÉS:\n")
        f.write("-" * 70 + "\n")
        for trigger in triggers:
            if trigger['id'] in trigger_ids:
                f.write(f"#{trigger['id']:3d} @ 0x{trigger['offset']:08X} | "
                       f"Pos: ({trigger['x']:5d},{trigger['y']:5d},{trigger['z']:5d}) | "
                       f"Type:{trigger['type']:3d} Dest:{trigger['dest']:3d}\n")

    print(f"Notes sauvegardées: {notes_file.name}")

    return output_file

def disable_specific_trigger(trigger_id):
    """Désactive un trigger spécifique"""
    print("=" * 70)
    print(f"  DÉSACTIVATION TRIGGER #{trigger_id}")
    print("=" * 70)

    if not TRIGGERS_DB.exists():
        print("\nERREUR: Base de données manquante. Exécutez d'abord 'extract'")
        return

    with open(TRIGGERS_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    triggers = db['triggers']

    # Trouver le trigger
    trigger = None
    for t in triggers:
        if t['id'] == trigger_id:
            trigger = t
            break

    if not trigger:
        print(f"\nERREUR: Trigger #{trigger_id} introuvable")
        return

    print(f"\nTrigger #{trigger_id}:")
    print(f"  Offset: 0x{trigger['offset']:X}")
    print(f"  Position: ({trigger['x']}, {trigger['y']}, {trigger['z']})")
    print(f"  Type: {trigger['type']}, Dest: {trigger['dest']}, Flags: 0x{trigger['flags']:04X}")

    # Patcher
    data = bytearray(LEVELS_DAT.read_bytes())

    offset = trigger['offset']
    struct.pack_into('<h', data, offset, 9999)
    struct.pack_into('<h', data, offset + 2, 9999)
    struct.pack_into('<h', data, offset + 4, 9999)

    output_file = OUTPUT_DIR / f"LEVELS_DISABLE_T{trigger_id}.DAT"
    with open(output_file, 'wb') as f:
        f.write(data)

    print(f"\nFichier patché créé: {output_file.name}")

def show_info():
    """Affiche les infos sur les triggers"""
    if not TRIGGERS_DB.exists():
        print("Base de données manquante. Exécutez d'abord 'extract'")
        return

    with open(TRIGGERS_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    print("=" * 70)
    print("  INFORMATIONS TRIGGERS")
    print("=" * 70)

    print(f"\nTotal triggers: {db['total_triggers']}")

    print(f"\nGroupes de test:")
    for group_key, trigger_ids in db['groups'].items():
        print(f"  {group_key}: Triggers {trigger_ids[0]}-{trigger_ids[-1]} ({len(trigger_ids)} triggers)")

    print(f"\nPremiers 20 triggers:")
    print("ID  | Offset     | Position (X, Y, Z)     | Type | Dest | Flags")
    print("----|------------|------------------------|------|------|-------")
    for t in db['triggers'][:20]:
        print(f"{t['id']:3d} | 0x{t['offset']:08X} | ({t['x']:5d},{t['y']:5d},{t['z']:5d}) | {t['type']:4d} | {t['dest']:4d} | 0x{t['flags']:04X}")

def main():
    if len(sys.argv) < 2:
        print("Usage: py -3 test_triggers_system.py [command]")
        print("\nCommands:")
        print("  extract        - Extraire tous les triggers")
        print("  patch N        - Créer patch test groupe N (1-5)")
        print("  disable ID     - Désactiver trigger spécifique")
        print("  info           - Afficher infos")
        print("\nExemple:")
        print("  py -3 test_triggers_system.py extract")
        print("  py -3 test_triggers_system.py patch 1")
        return

    command = sys.argv[1]

    if command == 'extract':
        if not LEVELS_DAT.exists():
            print(f"ERREUR: {LEVELS_DAT} introuvable!")
            return

        data = LEVELS_DAT.read_bytes()
        triggers = extract_all_triggers(data)
        save_triggers_database(triggers)

        print("\n" + "=" * 70)
        print("EXTRACTION TERMINÉE")
        print("=" * 70)
        print(f"Triggers extraits: {len(triggers)}")
        print(f"Base de données: {TRIGGERS_DB}")
        print("\nProchaine étape:")
        print("  py -3 test_triggers_system.py patch 1")

    elif command == 'patch':
        if len(sys.argv) < 3:
            print("Usage: py -3 test_triggers_system.py patch N (N=1-5)")
            return

        group_num = int(sys.argv[2])
        create_test_patch(group_num)

        print("\n" + "=" * 70)
        print("PATCH CRÉÉ")
        print("=" * 70)
        print("\nPROCHAINES ÉTAPES:")
        print("1. Copier le fichier .DAT créé dans le jeu")
        print("2. Tester en jeu")
        print("3. Noter quelles portes ont disparu")
        print("4. Répéter pour les autres groupes")

    elif command == 'disable':
        if len(sys.argv) < 3:
            print("Usage: py -3 test_triggers_system.py disable ID")
            return

        trigger_id = int(sys.argv[2])
        disable_specific_trigger(trigger_id)

    elif command == 'info':
        show_info()

    else:
        print(f"Commande inconnue: {command}")

if __name__ == '__main__':
    main()
