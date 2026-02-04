#!/usr/bin/env python3
"""
Find Level-Up Code - Cherche les patterns de boucles typiques d'un level-up
"""

import struct

SLES_PATH = r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\SLES_008.45"

CODE_START = 0x800
LOAD_ADDR = 0x80010000

def analyze_loop_patterns(data):
    """Cherche des patterns de boucles qui itèrent 6-8 fois"""

    print("Recherche de boucles qui iterent 6-8 fois...")
    print("(typique pour les 6 stats ou 8 classes)")
    print()

    candidates = []

    for i in range(0, len(data) - 100, 4):
        # Chercher des séquences typiques:
        # 1. Initialisation compteur (LI ou ADDIU avec 0)
        # 2. Comparaison avec 6, 7, ou 8
        # 3. Branch conditionnel (BLT, BNE, etc.)

        window = data[i:i+100]
        instrs = [struct.unpack('<I', window[j:j+4])[0] for j in range(0, len(window), 4)]

        # Chercher des constantes 6, 7, 8 dans les instructions
        for instr in instrs:
            opcode = (instr >> 26) & 0x3F
            imm = instr & 0xFFFF

            # ADDIU, ORI, etc. avec valeur 6, 7, ou 8
            if opcode in [0x09, 0x0D]:  # ADDIU, ORI
                if imm in [6, 7, 8]:
                    # Trouvé une constante intéressante
                    file_offset = CODE_START + i
                    mem_addr = LOAD_ADDR + i

                    # Analyser le contexte
                    context = []
                    for j in range(25):
                        if i + j*4 >= len(data):
                            break

                        ctx_instr = struct.unpack('<I', data[i+j*4:i+j*4+4])[0]
                        ctx_opcode = (ctx_instr >> 26) & 0x3F

                        # LBU = Load Byte Unsigned (pour growth rates)
                        if ctx_opcode == 0x24:
                            context.append(('LBU', j))

                        # SLL = Shift Left Logical (multiplication)
                        elif (ctx_instr & 0xFC00003F) == 0x00000000:  # Special opcode
                            funct = ctx_instr & 0x3F
                            if funct == 0x00:  # SLL
                                shamt = (ctx_instr >> 6) & 0x1F
                                if shamt in [2, 3]:  # * 4 ou * 8
                                    context.append(('SLL', j, shamt))

                    # Si on a des LBU et des SLL, c'est prometteur
                    if any(c[0] == 'LBU' for c in context) and any(c[0] == 'SLL' for c in context):
                        candidates.append({
                            'offset': file_offset,
                            'addr': mem_addr,
                            'loop_max': imm,
                            'context': context
                        })

                    break  # Passer à la prochaine fenêtre

    return candidates

def find_table_loads(data):
    """Cherche des chargements depuis des tables constantes"""

    print("Recherche de chargements depuis tables...")
    print()

    # Chercher des patterns LBU avec base address calculée
    table_refs = {}

    for i in range(0, len(data) - 40, 4):
        instr = struct.unpack('<I', data[i:i+4])[0]
        opcode = (instr >> 26) & 0x3F

        # LBU = Load Byte Unsigned
        if opcode == 0x24:
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            offset = instr & 0xFFFF

            # Si offset est petit (< 100), c'est probablement un accès table
            if offset < 100:
                # Regarder en arrière pour trouver LUI qui charge l'adresse de base
                for j in range(1, 10):
                    if i - j*4 < 0:
                        break

                    prev_instr = struct.unpack('<I', data[i-j*4:i-j*4+4])[0]
                    prev_opcode = (prev_instr >> 26) & 0x3F
                    prev_rt = (prev_instr >> 16) & 0x1F

                    # LUI qui charge dans le même registre
                    if prev_opcode == 0x0F and prev_rt == rs:
                        lui_imm = prev_instr & 0xFFFF
                        base_addr = lui_imm << 16

                        # Addresse effective approximative
                        effective_addr = base_addr + offset

                        if effective_addr not in table_refs:
                            table_refs[effective_addr] = []

                        file_offset = CODE_START + i
                        mem_addr = LOAD_ADDR + i

                        table_refs[effective_addr].append({
                            'load_offset': file_offset,
                            'load_addr': mem_addr,
                            'table_offset': offset
                        })

                        break

    return table_refs

def main():
    print("="*80)
    print("RECHERCHE DU CODE DE LEVEL-UP")
    print("="*80)
    print()

    with open(SLES_PATH, 'rb') as f:
        data = f.read()

    code_data = data[CODE_START:]

    # Chercher des boucles
    print("="*80)
    print("BOUCLES AVEC COMPTEUR 6-8")
    print("="*80)
    print()

    loop_candidates = analyze_loop_patterns(code_data)

    print(f"Trouvé {len(loop_candidates)} candidats de boucles")
    print()

    if loop_candidates:
        # Afficher les 20 premiers
        for idx, cand in enumerate(loop_candidates[:20]):
            print(f"CANDIDAT {idx+1}:")
            print(f"  Offset: 0x{cand['offset']:08X}")
            print(f"  Adresse: 0x{cand['addr']:08X}")
            print(f"  Loop max: {cand['loop_max']}")
            print(f"  Context: {cand['context']}")
            print()

    # Chercher des tables
    print()
    print("="*80)
    print("TABLES CHARGEES (LBU avec offset < 100)")
    print("="*80)
    print()

    table_refs = find_table_loads(code_data)

    # Trier par nombre de références
    sorted_tables = sorted(table_refs.items(), key=lambda x: len(x[1]), reverse=True)

    print(f"Trouvé {len(sorted_tables)} adresses de tables potentielles")
    print()

    # Afficher les 20 plus référencées
    for addr, refs in sorted_tables[:20]:
        print(f"Table @ 0x{addr:08X} - {len(refs)} références")

        # Afficher quelques exemples
        for ref in refs[:3]:
            print(f"  - Chargee a 0x{ref['load_addr']:08X} (offset {ref['table_offset']})")

        if len(refs) > 3:
            print(f"  - ... et {len(refs)-3} autres")

        print()

    print("="*80)
    print("PROCHAINES ETAPES")
    print("="*80)
    print()
    print("1. Examiner les candidats dans Ghidra")
    print("2. Chercher les fonctions qui utilisent ces boucles/tables")
    print("3. Tracer le code pour voir d'ou viennent les valeurs")
    print()

if __name__ == "__main__":
    main()
