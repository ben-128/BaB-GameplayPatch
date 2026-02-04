# Growth Rates - TROUVES!

**Localisation:** SLES_008.45 @ 0x0002BBFE
**Adresse mémoire:** 0x8003B3FE
**Date:** 2026-02-04

---

## Growth Rates par Classe

### Warrior

- **HP/level:** 6
- **MP/level:** 6
- **Strength/level:** 4
- **Defense/level:** 2
- **Magic/level:** 4
- **Magic Defense/level:** 7
- **Speed/level:** 7
- **Luck/level:** 2

### Priest

- **HP/level:** 6
- **MP/level:** 6
- **Strength/level:** 6
- **Defense/level:** 6
- **Magic/level:** 2
- **Magic Defense/level:** 7
- **Speed/level:** 4
- **Luck/level:** 10

### Rogue

- **HP/level:** 6
- **MP/level:** 6
- **Strength/level:** 10
- **Defense/level:** 4
- **Magic/level:** 10
- **Magic Defense/level:** 4
- **Speed/level:** 4
- **Luck/level:** 6

### Sorcerer

- **HP/level:** 5
- **MP/level:** 5
- **Strength/level:** 3
- **Defense/level:** 6
- **Magic/level:** 7
- **Magic Defense/level:** 2
- **Speed/level:** 4
- **Luck/level:** 3

### Hunter

- **HP/level:** 6
- **MP/level:** 6
- **Strength/level:** 8
- **Defense/level:** 10
- **Magic/level:** 10
- **Magic Defense/level:** 6
- **Speed/level:** 6
- **Luck/level:** 6

### Elf

- **HP/level:** 6
- **MP/level:** 6
- **Strength/level:** 6
- **Defense/level:** 10
- **Magic/level:** 7
- **Magic Defense/level:** 5
- **Speed/level:** 5
- **Luck/level:** 6

### Dwarf

- **HP/level:** 6
- **MP/level:** 3
- **Strength/level:** 3
- **Defense/level:** 4
- **Magic/level:** 4
- **Magic Defense/level:** 8
- **Speed/level:** 7
- **Luck/level:** 8

### Fairy

- **HP/level:** 8
- **MP/level:** 8
- **Strength/level:** 8
- **Defense/level:** 8
- **Magic/level:** 6
- **Magic Defense/level:** 7
- **Speed/level:** 6
- **Luck/level:** 6

---

## Analyse

- **HP range:** 5-8 par niveau
- **MP range:** 3-8 par niveau
- **Classe HP max:** Fairy (8/lv)
- **Classe HP min:** Sorcerer (5/lv)
- **Classe MP max:** Fairy (8/lv)
- **Classe MP min:** Dwarf (3/lv)

---

## Modification

Pour modifier les growth rates:

```bash
py -3 patch_growth_rates.py
```

Editez les fichiers JSON des classes, puis exécutez le patcher.

