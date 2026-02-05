# Résumé des Recherches - Stats et Growth des Classes

## Conclusion Principale

**Les stats de base et les tables de progression des classes ne sont PAS dans BLAZE.ALL.**

Elles sont très probablement dans l'exécutable du jeu (SLES_008.45).

---

## Ce qui a été trouvé dans BLAZE.ALL

### 1. Noms des Classes (0x0090B6E8 - 0x0090B7C8)

16 classes (8 M + 8 F) stockées consécutivement:
```
0x0090B6E8: Warrior M
0x0090B6F8: Priest M
0x0090B708: Rogue M
0x0090B718: Sorcerer M
0x0090B728: Hunter M
0x0090B738: Elf M
0x0090B748: Dwarf M
0x0090B758: Fairy M / Warrior F
0x0090B768: Priestess F
0x0090B778: Rogue F
0x0090B788: Sorceress F
0x0090B798: Hunter F
0x0090B7A8: Elf F
0x0090B7B8: Dwarf F
0x0090B7C8: Fairy F
```

**Format**: Nom ASCII + marker `0B 01 D9 00`

**Important**: Ce sont juste des labels UI, pas de données de stats adjacentes.

---

### 2. Descriptions des Stats (0x0090E0D0 - 0x0090E240)

Tooltips UI pour chaque attribut:

| Offset | Stat | Description |
|--------|------|-------------|
| 0x0090E0D0 | STR | (troncé) "Important for attacks." |
| 0x0090E0E8 | INT | "Intelligence. Necessary for effective use of sorcery." |
| 0x0090E124 | WIL | "Willpower. Important for resistance to magic." |
| 0x0090E158 | AGL | "Agility. Important for defense." |
| 0x0090E180 | CON | "Constitution. Important for health and healing." |
| 0x0090E1B8 | POW | "Magical power. Important for recovery of magical energy." |
| 0x0090E1F8 | LCK | "Luck. Luck is important in many situations." |

---

### 3. Zone de Données Potentielles (0x00203000+)

Tables numériques trouvées mais **pas** identifiées comme stats de classe:

```
0x00203070: [0, 1, 2, 3, 4, 5, 6, 1, 8, 9, 10, 11, 12, 1, 14, 15, 16, ...]
0x002030C2: [10, 11, 12, 13, 16, 17, 18, 21, 24, 27, 29, 31, 34, 36, 38, 40]
0x00203920: [27, 29, 31, 34, 36, 38, 40, 0, 1, 2, 3, 9, 10, 18, ...]
```

Ces données semblent être des tables de progression de niveau ou des formules, pas des stats de base par classe.

---

### 4. Listes de Sorts par Classe (0x002CA424)

Documenté dans `../spells/CLASS_DATA_ANALYSIS.md`:
- 7 listes de sorts progressives
- Mapping classe ↔ liste non encore établi

---

## Ce qui N'EST PAS dans BLAZE.ALL

1. **Stats de base par classe** (HP, MP, STR, INT, WIL, AGL, CON, POW, LUK)
2. **Tables de progression** (gain de stats par niveau)
3. **Tables d'XP** (expérience requise par niveau)
4. **Pointeurs vers les classes** (pas de structure de données référençant les classes)

---

## Hypothèse: Données dans SLES_008.45

Les stats sont probablement hardcodées dans l'exécutable PlayStation:

```
SLES_008.45 (exécutable du jeu)
├── Code de jeu
├── Tables de stats par classe (probablement)
├── Formules de calcul
└── Tables de progression
```

### Méthode pour trouver les stats

1. **Analyse du save game**:
   - Créer un perso de chaque classe niveau 1
   - Sauvegarder et extraire les données
   - Chercher les valeurs dans SLES_008.45

2. **Reverse engineering de l'EXE**:
   - Désassembler SLES_008.45
   - Chercher les routines de création de personnage
   - Identifier les tables de stats

3. **Test in-game**:
   - Documenter les stats de départ de chaque classe
   - Chercher ces valeurs en mémoire

---

## Stats de départ connues (de la FAQ GameFAQs)

À vérifier in-game:

| Classe | HP | MP | STR | INT | WIL | AGL | CON | POW | LUK |
|--------|----|----|-----|-----|-----|-----|-----|-----|-----|
| Warrior | ~80 | ~20 | 20 | 10 | 12 | 12 | 18 | 8 | 10 |
| Sorcerer | ~50 | ~60 | 8 | 22 | 18 | 10 | 10 | 20 | 12 |
| Priest | ~60 | ~50 | 12 | 16 | 20 | 10 | 14 | 18 | 10 |
| Dwarf | ~90 | ~15 | 22 | 8 | 10 | 8 | 20 | 10 | 12 |
| Elf | ~55 | ~40 | 14 | 18 | 14 | 18 | 10 | 14 | 12 |
| Fairy | ~45 | ~70 | 8 | 20 | 16 | 14 | 8 | 22 | 12 |
| Rogue | ~55 | ~25 | 16 | 12 | 10 | 20 | 12 | 10 | 20 |
| Hunter | ~65 | ~30 | 18 | 10 | 12 | 16 | 16 | 10 | 8 |

*Valeurs estimées - à confirmer*

---

## Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `CLASS_DATA_LOCATIONS.md` | Résumé des emplacements connus |
| `EQUIPMENT_BY_CLASS.md` | Équipements par classe |
| `TODO_RESEARCH.md` | Liste des recherches à faire |
| `CLASS_STATS_ANALYSIS.txt` | Dump de l'analyse automatique |
| `FINDINGS_SUMMARY.md` | Ce document |
| `analyze_class_stats.py` | Script d'analyse zone classe |
| `analyze_growth_zone.py` | Script d'analyse zone 0x203000 |
| `quick_search.py` | Recherche rapide patterns |
| `analyze_stat_strings.py` | Analyse des strings de stats |
| `dump_stat_tooltips.py` | Dump des tooltips |
| `search_base_stats.py` | Recherche patterns de stats |

---

## Prochaines Étapes

1. **Analyser SLES_008.45** avec un désassembleur (Ghidra, IDA)
2. **Créer des personnages test** et documenter leurs stats
3. **Comparer les saves** entre classes pour identifier les offsets
4. **Tester les modifications** de la zone 0x00203000 in-game

---

## Notes Techniques

- BLAZE.ALL est un fichier de données (~46 MB)
- Les stats de monstres utilisent une structure de 40 × uint16 (80 bytes)
- Les items utilisent une structure de 128 bytes
- Le marqueur `0B 01 D9 00` sépare les noms de classes
