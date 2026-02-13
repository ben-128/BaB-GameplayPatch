"""
analyze_trigger_format.py
Analyse détaillée du format d'un trigger

Usage: py -3 analyze_trigger_format.py
"""

from pathlib import Path
import struct
import json

LEVELS_DAT = Path("../../../Blaze  Blade - Eternal Quest (Europe)/extract/LEVELS.DAT")
TRIGGERS_DB = Path("../trigger_tests/triggers_database.json")

def analyze_trigger_bytes(data, offset, trigger_id):
    """Analyse détaillée des bytes d'un trigger"""
    print("=" * 70)
    print(f"  ANALYSE TRIGGER #{trigger_id} @ 0x{offset:X}")
    print("=" * 70)

    # Lire 32 bytes (pour voir le contexte)
    chunk = data[offset:offset+32]

    print(f"\nBytes bruts (32 bytes):")
    print(f"  Hex: {chunk.hex()}")
    print(f"  Visualisation: {' '.join([f'{b:02X}' for b in chunk])}")

    print(f"\n{'─'*70}")
    print("  STRUCTURE HYPOTHÉTIQUE (12 bytes)")
    print("─" * 70)

    # Structure hypothétique actuelle
    print(f"\nOffset | Bytes    | Type   | Valeur       | Description")
    print("─" * 70)

    # +0x00: X coordinate (int16)
    x = struct.unpack_from('<h', data, offset)[0]
    x_bytes = chunk[0:2]
    print(f"+0x00  | {x_bytes.hex():8s} | int16  | {x:13d} | Position X")

    # +0x02: Y coordinate (int16)
    y = struct.unpack_from('<h', data, offset + 2)[0]
    y_bytes = chunk[2:4]
    print(f"+0x02  | {y_bytes.hex():8s} | int16  | {y:13d} | Position Y")

    # +0x04: Z coordinate (int16)
    z = struct.unpack_from('<h', data, offset + 4)[0]
    z_bytes = chunk[4:6]
    print(f"+0x04  | {z_bytes.hex():8s} | int16  | {z:13d} | Position Z")

    # +0x06: Event type? (uint16)
    event_type = struct.unpack_from('<H', data, offset + 6)[0]
    type_bytes = chunk[6:8]
    print(f"+0x06  | {type_bytes.hex():8s} | uint16 | {event_type:13d} | Event Type?")

    # +0x08: Destination ID? (uint16)
    dest_id = struct.unpack_from('<H', data, offset + 8)[0]
    dest_bytes = chunk[8:10]
    print(f"+0x08  | {dest_bytes.hex():8s} | uint16 | {dest_id:13d} | Destination ID?")

    # +0x0A: Flags? (uint16)
    flags = struct.unpack_from('<H', data, offset + 10)[0]
    flags_bytes = chunk[10:12]
    print(f"+0x0A  | {flags_bytes.hex():8s} | uint16 | 0x{flags:04X} ({flags:5d}) | Flags?")

    print(f"\n{'─'*70}")
    print("  INTERPRÉTATIONS ALTERNATIVES")
    print("─" * 70)

    # Alternative 1: Tout en float
    try:
        f1 = struct.unpack_from('<f', data, offset)[0]
        f2 = struct.unpack_from('<f', data, offset + 4)[0]
        f3 = struct.unpack_from('<f', data, offset + 8)[0]
        print(f"\nComme floats (x3):")
        print(f"  Float[0]: {f1:.6f}")
        print(f"  Float[1]: {f2:.6f}")
        print(f"  Float[2]: {f3:.6f}")
    except:
        pass

    # Alternative 2: Tout en uint16
    uint16_values = []
    for i in range(0, 12, 2):
        val = struct.unpack_from('<H', data, offset + i)[0]
        uint16_values.append(val)

    print(f"\nComme uint16 (x6):")
    print(f"  {uint16_values}")

    # Alternative 3: Tout en uint8
    uint8_values = list(chunk[:12])
    print(f"\nComme uint8 (x12):")
    print(f"  {uint8_values}")

    # Alternative 4: 4 bytes + 4 bytes + 4 bytes
    chunk1 = struct.unpack_from('<I', data, offset)[0]
    chunk2 = struct.unpack_from('<I', data, offset + 4)[0]
    chunk3 = struct.unpack_from('<I', data, offset + 8)[0]
    print(f"\nComme uint32 (x3):")
    print(f"  0x{chunk1:08X}, 0x{chunk2:08X}, 0x{chunk3:08X}")

    # Contexte après
    print(f"\n{'─'*70}")
    print("  BYTES SUIVANTS (contexte)")
    print("─" * 70)
    next_chunk = data[offset+12:offset+32]
    print(f"  {next_chunk.hex()}")

    # Vérifier si c'est une table répétée
    if offset + 24 < len(data):
        try:
            next_x = struct.unpack_from('<h', data, offset + 12)[0]
            next_y = struct.unpack_from('<h', data, offset + 14)[0]
            next_z = struct.unpack_from('<h', data, offset + 16)[0]

            if all(-2048 <= coord <= 2048 for coord in [next_x, next_y, next_z]):
                print(f"\n⚠️ PATTERN RÉPÉTÉ DÉTECTÉ!")
                print(f"  Prochain trigger possible: ({next_x}, {next_y}, {next_z})")
        except:
            pass

def compare_multiple_triggers(data):
    """Compare plusieurs triggers pour trouver des patterns"""
    print("\n" + "=" * 70)
    print("  COMPARAISON DE PLUSIEURS TRIGGERS")
    print("=" * 70)

    if not TRIGGERS_DB.exists():
        print("Base de données manquante")
        return

    with open(TRIGGERS_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    triggers = db['triggers'][:10]  # 10 premiers

    print(f"\nComparaison des 10 premiers triggers:")
    print("\nID | Offset     | Bytes (12 premiers)")
    print("---|------------|" + "-" * 54)

    for t in triggers:
        offset = t['offset']
        chunk = data[offset:offset+12]
        hex_str = ' '.join([f'{b:02X}' for b in chunk])
        print(f"{t['id']:2d} | 0x{offset:08X} | {hex_str}")

    # Chercher des patterns communs
    print(f"\n{'─'*70}")
    print("  ANALYSE DES PATTERNS")
    print("─" * 70)

    # Byte 6-7 (type)
    types = [t['type'] for t in triggers]
    print(f"\nValeurs de 'type' (byte 6-7):")
    print(f"  Valeurs uniques: {set(types)}")
    print(f"  Fréquence de 0: {types.count(0)}/{len(types)}")

    # Byte 8-9 (dest)
    dests = [t['dest'] for t in triggers]
    print(f"\nValeurs de 'destination' (byte 8-9):")
    print(f"  Valeurs uniques: {set(dests)}")
    print(f"  Fréquence de 0: {dests.count(0)}/{len(dests)}")

    # Byte 10-11 (flags)
    flags_list = [t['flags'] for t in triggers]
    print(f"\nValeurs de 'flags' (byte 10-11):")
    print(f"  Valeurs uniques: {set(flags_list)}")

def search_for_door_markers(data):
    """Cherche des marqueurs de portes spécifiques"""
    print("\n" + "=" * 70)
    print("  RECHERCHE DE MARQUEURS DE PORTES")
    print("=" * 70)

    # Patterns qui pourraient indiquer une porte
    door_patterns = [
        (b'\x44\x4F\x4F\x52', "ASCII 'DOOR'"),
        (b'\x00\x00\x00\x00', "Null padding"),
        (b'\xFF\xFF\xFF\xFF', "0xFFFFFFFF marker"),
    ]

    print("\nRecherche de patterns spécifiques...")

    for pattern, desc in door_patterns:
        count = data.count(pattern)
        if count > 0:
            first_pos = data.find(pattern)
            print(f"  {desc:20s}: {count:5d} occurrences (1ère: 0x{first_pos:X})")

def main():
    print("=" * 70)
    print("  ANALYSE DU FORMAT DES TRIGGERS")
    print("=" * 70)

    if not LEVELS_DAT.exists():
        print(f"ERREUR: {LEVELS_DAT} introuvable!")
        return

    data = LEVELS_DAT.read_bytes()
    print(f"\nLEVELS.DAT: {len(data):,} bytes\n")

    # Analyser quelques triggers spécifiques
    if TRIGGERS_DB.exists():
        with open(TRIGGERS_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)

        # Analyser trigger #1
        trigger1 = db['triggers'][0]
        analyze_trigger_bytes(data, trigger1['offset'], 1)

        # Analyser trigger #6 (a dest_id=9)
        trigger6 = db['triggers'][5]
        print("\n\n")
        analyze_trigger_bytes(data, trigger6['offset'], 6)

        # Comparer plusieurs
        compare_multiple_triggers(data)

    # Chercher des marqueurs
    search_for_door_markers(data)

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("""
Structure hypothétique actuelle (12 bytes):
  +0x00: Position X (int16)
  +0x02: Position Y (int16)
  +0x04: Position Z (int16)
  +0x06: Event Type (uint16) - souvent 0
  +0x08: Destination ID (uint16) - variable
  +0x0A: Flags (uint16) - variable

INCERTITUDES:
- Cette structure est une HYPOTHÈSE basée sur les coordonnées
- Les champs type/dest/flags ne sont pas confirmés
- Pourrait être une structure différente (collision, spawn, etc.)
- Nécessite test en jeu pour confirmer

RECOMMANDATION:
- Tester les patches pour voir l'effet réel
- Observer si les triggers affectent les portes
- Ajuster la structure si nécessaire
    """)
    print("=" * 70)

if __name__ == '__main__':
    main()
