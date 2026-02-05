# Analyse SLES_008.45 - Stats et Progression

## Résumé

L'exécutable SLES_008.45 (824 KB) contient les tables de progression de niveau et potentiellement les modificateurs de stats par classe.

**Note**: Les noms de classes ne sont PAS dans SLES - ils sont chargés depuis BLAZE.ALL.

---

## Tables de Progression de Niveau

### Table 1: HP Progression Lente (0x00033664)

```
Niveaux 1-50: 40 → 71 (+31 total, ~0.6/niveau)

Lv  1-10: [40, 40, 41, 42, 42, 43, 43, 44, 45, 45]
Lv 11-20: [46, 47, 47, 48, 49, 49, 50, 50, 51, 52]
Lv 21-30: [52, 53, 54, 54, 55, 55, 56, 57, 57, 58]
Lv 31-40: [59, 59, 60, 61, 61, 62, 62, 63, 64, 64]
Lv 41-50: [65, 66, 66, 67, 67, 68, 69, 69, 70, 71]
```

**Usage probable**: Base HP ou stat de classe faible.

### Table 2: HP Progression Linéaire (0x0002EAB6)

```
Niveaux 1-50: 6 → 314 (+308 total, ~6.3/niveau)

Lv  1-10: [6, 13, 19, 25, 31, 38, 44, 50, 57, 63]
Lv 11-20: [69, 75, 82, 88, 94, 101, 107, 113, 119, 126]
Lv 21-30: [132, 138, 144, 151, 157, 163, 170, 176, 182, 188]
Lv 31-40: [195, 201, 207, 214, 220, 226, 232, 239, 245, 251]
Lv 41-50: [257, 264, 270, 276, 283, 289, 295, 301, 308, 314]
```

**Usage probable**: Bonus HP par niveau ou HP total.

### Table 3: Stat Progression (0x00033600)

```
Niveaux 1-50: 8 → 39 (+31 total, ~0.6/niveau)

Lv  1-10: [8, 9, 9, 10, 10, 11, 12, 12, 13, 14]
...
```

**Usage probable**: Progression d'attribut (STR, INT, etc).

---

## Potentielles Stats de Classes (0x0002BBA8)

Zone contenant des patterns de 8 valeurs (8 classes):

| Stat | Warrior | Priest | Sorcerer | Dwarf | Fairy | Rogue | Hunter | Elf |
|------|---------|--------|----------|-------|-------|-------|--------|-----|
| Row1 | 2 | 4 | 8 | 6 | 10 | 8 | 2 | 4 |
| Row2 | 4 | 6 | 6 | 2 | 4 | 2 | 4 | 6 |
| Row3 | 4 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| Row4 | 6 | 2 | 2 | 4 | 6 | 4 | 6 | 6 |
| Row5 | 6 | 6 | 6 | 5 | 5 | 7 | 6 | 2 |
| Row6 | 6 | 7 | 5 | 8 | 7 | 7 | 6 | 8 |
| Row7 | 6 | 6 | 6 | 6 | 7 | 8 | 6 | 6 |
| Row8 | 7 | 3 | 4 | 3 | 6 | 8 | 5 | 5 |
| Row9 | 5 | 5 | 5 | 4 | 5 | 5 | 2 | 3 |
| Row10| 6 | 2 | 8 | 5 | 6 | 5 | 5 | 4 |

**Interprétation possible**:
- Ces valeurs sont petites (2-10), donc probablement des **multiplicateurs de growth** plutôt que des stats de base
- Row1 pourrait être un modificateur de croissance pour une stat
- Les 8 colonnes correspondent aux 8 classes

---

## Zone 0x0002C820 - Données Inconnues

```
[5, 10, 15, 20, 26]   - Progression par 5 (seuils de niveau?)
[5, 11, 16, 19, 22]   - Progression variable
[3, 7, 9, 12, 16]     - Autre progression
```

**Hypothèse**: Pourrait être des seuils pour débloquer des sorts ou compétences.

---

## Patterns de Stats Typiques Trouvés

Plusieurs zones avec des patterns 8-valeurs dans la range 5-30:

| Offset | Pattern | Interprétation |
|--------|---------|----------------|
| 0x0002C820 | [5, 10, 15, 20, 26, 5, 11, 16] | Seuils? |
| 0x0002EC54 | [5, 5, 11, 5, 17, 5, 23, 5] | Alternance? |
| 0x0002ED61 | [8, 9, 8, 14, 8, 20, 8, 25] | Progression? |

---

## Structure Probable

```
SLES_008.45
├── Code exécutable PlayStation
├── Tables de progression (0x0002EA00 - 0x00034000)
│   ├── HP par niveau (plusieurs variantes)
│   ├── Stats par niveau
│   └── Modificateurs par classe
├── Données de jeu diverses
└── Pointeurs vers BLAZE.ALL
```

---

## Prochaines Étapes

1. **Tester les hypothèses in-game**:
   - Créer des personnages et noter les HP/stats à chaque niveau
   - Comparer avec les tables extraites

2. **Modifier les valeurs**:
   - Patcher une table et vérifier l'effet

3. **Désassembler le code**:
   - Utiliser Ghidra pour comprendre comment les tables sont utilisées
   - Identifier les formules de calcul

---

## Fichiers Générés

- `SLES_EXTRACTED_DATA.json` - Données extraites en JSON
- `analyze_sles.py` - Script d'analyse initial
- `analyze_sles_zone.py` - Analyse détaillée des zones
- `extract_sles_data.py` - Extraction des tables
