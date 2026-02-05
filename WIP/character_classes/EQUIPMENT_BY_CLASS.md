# Équipements par Classe - Blaze & Blade

## Classes du Jeu

| ID | Classe (EN) | Classe (FR) | Archétype |
|----|-------------|-------------|-----------|
| 1 | Warrior | Guerrier | Tank/Mêlée |
| 2 | Priest | Prêtre | Support/Magie |
| 3 | Sorcerer/Wizard | Sorcier | DPS Magie |
| 4 | Dwarf | Nain | Tank/Mêlée |
| 5 | Fairy | Fée | Support/Magie |
| 6 | Rogue/Thief | Voleur | DPS Mêlée |
| 7 | Hunter/Ranger | Chasseur | DPS Distance |
| 8 | Elf | Elfe | DPS Mêlée/Hybride |

---

## Armes par Classe

| Type d'Arme | Classe(s) | Nb Items |
|-------------|-----------|----------|
| Swords (Épées) | Warrior | 23 |
| Axes (Haches) | Dwarf | 20 |
| Priest's Wand/Hammer | Priest | 17 |
| Sorcerer's Wand | Sorcerer | 16 |
| Rods (Bâtons) | Fairy | 16 |
| Rapiers (Rapières) | Elf | 16 |
| Knives (Dagues) | Rogue | 15 |
| Bows (Arcs) | Hunter | 14 |

---

## Armures par Classe

| Type d'Armure | Classe(s) | Nb Items |
|---------------|-----------|----------|
| Heavy Armors | Warrior, Dwarf | 15 |
| Light Armors | Hunter, Elf, Rogue | 14 |
| Robes | Priest, Sorcerer, Fairy | 14 |
| Shields | Warrior, Dwarf | 11 |

---

## Équipements Communs (Toutes Classes)

| Type | Nb Items | Notes |
|------|----------|-------|
| Clothings (Vêtements) | 107 | Casques, bottes, gants, anneaux |

---

## Détails par Classe

### Warrior (Guerrier)
- **Armes**: Swords (23)
- **Armures**: Heavy Armors (15)
- **Boucliers**: Shields (11)
- **Accessoires**: Clothings (107)

### Dwarf (Nain)
- **Armes**: Axes (20)
- **Armures**: Heavy Armors (15)
- **Boucliers**: Shields (11)
- **Accessoires**: Clothings (107)

### Priest (Prêtre)
- **Armes**: Priest's Wand/Hammer (17)
- **Armures**: Robes (14)
- **Accessoires**: Clothings (107)

### Sorcerer (Sorcier)
- **Armes**: Sorcerer's Wand (16)
- **Armures**: Robes (14)
- **Accessoires**: Clothings (107)

### Fairy (Fée)
- **Armes**: Rods (16)
- **Armures**: Robes (14)
- **Accessoires**: Clothings (107)

### Elf (Elfe)
- **Armes**: Rapiers (16)
- **Armures**: Light Armors (14)
- **Accessoires**: Clothings (107)

### Rogue (Voleur)
- **Armes**: Knives (15)
- **Armures**: Light Armors (14)
- **Accessoires**: Clothings (107)

### Hunter (Chasseur)
- **Armes**: Bows (14)
- **Armures**: Light Armors (14)
- **Accessoires**: Clothings (107)

---

## Armes Légendaires par Classe

### Warrior
- Answerer
- Mistortain
- Fenris
- Calvin's Blade

### Dwarf
- (à compléter)

### Priest
- Hammer of Thor

### Sorcerer
- Charmed Wand
- Baphomet

### Fairy
- Angel Rod
- Alchemist's Rod

### Rogue
- Death Sickle
- Fabnihl

### Hunter
- Bolt of Larie
- Perseus Bow

### Elf
- (à compléter)

---

## Structure Item (128 bytes)

```
+0x00 - 0x1F : Nom (32 bytes, null-terminated)
+0x10 - 0x3F : Stats binaires (uint16)
+0x40        : Séparateur (0x0C)
+0x41 - 0x7F : Description
```

### Attributs Possibles
- STR (Force)
- INT (Intelligence)
- WIL (Volonté)
- AGL (Agilité)
- CON (Constitution)
- POW (Puissance)
- LUK (Chance)
- AT (Attaque)
- MAT (Attaque Magique)
- DEF (Défense)
- MDEF (Défense Magique)

---

## Sources

- `Data/items/faq_items_reference.json` - 376 items complets
- `Data/items/all_items_clean.json` - 316 items avec offsets
- `Data/items/README.md` - Documentation complète
