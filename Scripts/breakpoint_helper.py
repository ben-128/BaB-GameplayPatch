#!/usr/bin/env python3
"""Helper pour générer des commandes de breakpoints DuckStation/PCSX-Redux."""

import argparse
from typing import Dict

# Addresses importantes (Blaze & Blade)
ADDRESSES = {
    # EXE (fixed addresses - never change)
    "damage_function": 0x80024F90,
    "action_dispatch": 0x80024494,
    "level_sim_loop": 0x800244F4,
    "entity_init": 0x80021E68,

    # Entity runtime (base addresses - examples)
    "entity_array": 0x800B1E80,
    "player_0_block": 0x800F0000,
    "player_1_block": 0x800F2000,

    # Tables (BLAZE.ALL offsets)
    "spell_table_type0": 0x908E68,
    "falling_rock_desc": 0x009ECFEC,

    # Cavern F1 Area 1 (per-area addresses)
    "cav_f1a1_assignments": 0xF7A964,
    "cav_f1a1_stats": 0xF7A97C,
    "cav_f1a1_script": 0xF7AA9C,
    "cav_f1a1_chest_timer": 0x800877F4,
}

# Entity struct offsets
ENTITY_OFFSETS = {
    "name": 0x00,           # char[16]
    "timer": 0x14,          # u16
    "stat_b": 0x10,         # ?
    "defenses": 0x30,       # ?
    "stats": 0x44,          # ?
    "descriptor_ptr": 0x3C, # u32
    "level": 0x144,         # u16
    "flags": 0x150,         # u32
    "bitmask": 0x160,       # u32 (spell availability)
    "creature_type": 0x2B5, # u8
}

# Player struct offsets
PLAYER_OFFSETS = {
    "name": 0x100,          # ASCII
    "level": 0x144,         # u16
    "max_hp": 0x148,        # u16
    "cur_hp": 0x14C,        # u16
}


def generate_duckstation_script(research_mode: str = "all"):
    """Génère un script de breakpoints pour DuckStation."""
    print("# ========================================")
    print("# DuckStation Breakpoint Script")
    print("# Copier/coller dans la console (Ctrl+`)")
    print("# ========================================\n")

    if research_mode in ["all", "combat"]:
        print("# === Combat System ===")
        print(f"break {ADDRESSES['damage_function']:#010x}  # Damage calculation")
        print(f"break {ADDRESSES['action_dispatch']:#010x}  # Spell/action dispatch")
        print(f"break {ADDRESSES['level_sim_loop']:#010x}  # Level-up sim (bitmask)")
        print()

    if research_mode in ["all", "entity"]:
        print("# === Entity System ===")
        print(f"break {ADDRESSES['entity_init']:#010x}  # Entity descriptor init")
        print(f"watch {ADDRESSES['entity_array']:#010x} rw  # Entity array access")
        print()

    if research_mode in ["all", "player"]:
        print("# === Player Data ===")
        p0_hp = ADDRESSES['player_0_block'] + PLAYER_OFFSETS['cur_hp']
        print(f"watch {p0_hp:#010x} w  # Player 0 HP write")
        print()

    if research_mode in ["all", "cavern"]:
        print("# === Cavern F1 Area 1 ===")
        print(f"break {ADDRESSES['cav_f1a1_script']:#010x}  # Script area")
        print(f"break {ADDRESSES['cav_f1a1_chest_timer']:#010x}  # Chest timer decrement")
        print()

    if research_mode in ["all", "spells"]:
        print("# === Spell System ===")
        print(f"break {ADDRESSES['action_dispatch']:#010x}  # Spell dispatch")
        print(f"break {ADDRESSES['level_sim_loop']:#010x}  # Bitmask accumulation")
        print("# NOTE: Pour watchpoints entity+0x160, utiliser 'entity-field' command")
        print()

    if research_mode in ["all", "trap"]:
        print("# === Trap Damage (Research) ===")
        print(f"break {ADDRESSES['damage_function']:#010x}  # Catch all damage")
        print(f"break {ADDRESSES['entity_init']:#010x}  # Entity init (descriptor)")
        print("# NOTE: Step through pour trouver caller avec $a3=10")
        print()


def entity_field_address(base: int, field: str) -> int:
    """Calcule adresse absolue pour un champ d'entité."""
    if field not in ENTITY_OFFSETS:
        raise ValueError(f"Unknown entity field: {field}")
    return base + ENTITY_OFFSETS[field]


def player_field_address(player_id: int, field: str) -> int:
    """Calcule adresse absolue pour un champ de joueur."""
    if field not in PLAYER_OFFSETS:
        raise ValueError(f"Unknown player field: {field}")
    base = ADDRESSES['player_0_block'] + (player_id * 0x2000)
    return base + PLAYER_OFFSETS[field]


def generate_entity_watchpoints(entity_base: int, fields: list):
    """Génère watchpoints pour des champs d'entité spécifiques."""
    print(f"\n# === Entity Watchpoints (base = {entity_base:#010x}) ===")
    for field in fields:
        addr = entity_field_address(entity_base, field)
        print(f"watch {addr:#010x} rw  # entity+{ENTITY_OFFSETS[field]:#04x} ({field})")


def generate_player_watchpoints(player_id: int, fields: list):
    """Génère watchpoints pour des champs de joueur spécifiques."""
    print(f"\n# === Player {player_id} Watchpoints ===")
    for field in fields:
        addr = player_field_address(player_id, field)
        print(f"watch {addr:#010x} w  # player+{PLAYER_OFFSETS[field]:#04x} ({field})")


def main():
    parser = argparse.ArgumentParser(
        description="Génère des commandes de breakpoints pour debugging PSX"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "combat", "entity", "player", "cavern", "spells", "trap"],
        default="all",
        help="Type de recherche (défaut: all)"
    )
    parser.add_argument(
        "--entity-base",
        type=lambda x: int(x, 0),
        help="Adresse de base d'une entité (ex: 0x800B2000)"
    )
    parser.add_argument(
        "--entity-fields",
        nargs="+",
        choices=list(ENTITY_OFFSETS.keys()),
        help="Champs d'entité à watchpoint"
    )
    parser.add_argument(
        "--player",
        type=int,
        choices=[0, 1, 2, 3],
        help="ID du joueur pour watchpoints"
    )
    parser.add_argument(
        "--player-fields",
        nargs="+",
        choices=list(PLAYER_OFFSETS.keys()),
        help="Champs de joueur à watchpoint"
    )

    args = parser.parse_args()

    # Générer script principal
    generate_duckstation_script(args.mode)

    # Générer watchpoints entity si demandé
    if args.entity_base and args.entity_fields:
        generate_entity_watchpoints(args.entity_base, args.entity_fields)

    # Générer watchpoints player si demandé
    if args.player is not None and args.player_fields:
        generate_player_watchpoints(args.player, args.player_fields)

    # Footer avec exemples
    print("\n# ========================================")
    print("# Exemples d'Usage")
    print("# ========================================")
    print("#")
    print("# 1. Tout inclure:")
    print("#    python breakpoint_helper.py")
    print("#")
    print("# 2. Seulement spells:")
    print("#    python breakpoint_helper.py --mode spells")
    print("#")
    print("# 3. Watchpoints pour une entité spécifique:")
    print("#    python breakpoint_helper.py --entity-base 0x800B2000 --entity-fields timer bitmask level")
    print("#")
    print("# 4. Watchpoints pour Player 0:")
    print("#    python breakpoint_helper.py --player 0 --player-fields cur_hp max_hp level")
    print("#")
    print("# ========================================")
    print("# Workflow")
    print("# ========================================")
    print("#")
    print("# 1. Charger le jeu + patch dans DuckStation")
    print("# 2. Ouvrir console (Ctrl+`)")
    print("# 3. Copier/coller les commandes 'break' et 'watch'")
    print("# 4. Sauvegarder un savestate AVANT l'événement")
    print("# 5. Trigger l'événement")
    print("# 6. Quand ça break:")
    print("#    - Taper 'regs' pour voir les registres")
    print("#    - Taper 'dump <addr> <len>' pour voir la mémoire")
    print("#    - Taper 'step' ou 'next' pour avancer")
    print("#    - Taper 'continue' pour reprendre")
    print("# 7. Recharger savestate et réessayer si besoin")
    print("#")
    print("# ========================================")
    print("# Commandes DuckStation Console")
    print("# ========================================")
    print("#")
    print("# regs                    # Afficher tous les registres")
    print("# dump <addr> <len>       # Dump mémoire (hex)")
    print("# step                    # Execute 1 instruction")
    print("# next                    # Step over (skip JAL)")
    print("# continue                # Reprend l'exécution")
    print("# breakpoints             # Liste les breakpoints")
    print("# delete <id>             # Supprime un breakpoint")
    print("# clear                   # Supprime tous les breakpoints")
    print("#")


if __name__ == "__main__":
    main()
