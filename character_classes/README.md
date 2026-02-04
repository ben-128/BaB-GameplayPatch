# Character Classes - Stats par Niveau

## 📋 Vue d'ensemble

Ce dossier contient l'analyse des statistiques des classes de personnages dans Blaze & Blade: Eternal Quest.

---

## 🎭 Classes Identifiées

| Classe | Nom dans BLAZE.ALL | Offset | Statut |
|--------|-------------------|--------|--------|
| Warrior | "Warrior" | 0x0090B6E8 | 🔍 En recherche |
| Priest | "Priest" | 0x0090B6F8 | 🔍 En recherche |
| Elf | "Elf" | 0x0090B734 | 🔍 En recherche |
| Fairy | "Fairy" | 0x0090B74C | 🔍 En recherche |
| Wizard | "Wizard" | 0x0163CF0C | 🔍 En recherche |
| Dwarf | "Dwarf" | 0x007EDE4B | 🔍 En recherche |
| Fighter | "Fighter" | 0x00919984 | 🔍 En recherche |
| Ranger | "Ranger" | 0x01FB854C | 🔍 En recherche |
| Thief | "Thief" | 0x0152AD8C | 🔍 En recherche |

---

## 📊 Structure des Stats (Hypothèse)

D'après l'analyse des monstres (40 stats par monstre), les personnages pourraient avoir une structure similaire:

### Stats de Base (Level 1)
- **HP** (Hit Points)
- **MP** (Magic Points)
- **Strength** (Force physique)
- **Defense** (Défense physique)
- **Magic** (Puissance magique)
- **Magic Defense** (Résistance magique)
- **Speed** (Vitesse/Agilité)
- **Luck** (Chance)

### Stats par Niveau
- **HP Gain** : Points de vie gagnés par niveau
- **MP Gain** : Points de magie gagnés par niveau
- **Strength Gain** : Force gagnée par niveau
- **Defense Gain** : Défense gagnée par niveau
- **Magic Gain** : Magie gagnée par niveau
- **Magic Defense Gain** : Résistance magique gagnée par niveau
- **Speed Gain** : Vitesse gagnée par niveau

### Autres Données Possibles
- **Starting Equipment** : Équipement de départ
- **Spell List ID** : Référence à la liste de sorts (0-6)
- **Base EXP** : Expérience requise pour level-up
- **EXP Multiplier** : Multiplicateur d'expérience par niveau

---

## 🔍 Zone Mémoire Principale

**Offset : 0x0090B6E8 - 0x0090B7BC** (212 bytes)

Cette zone contient:
```
0x0090B6E8 : "Warrior\0"  (8 bytes)
0x0090B6F0 : [??? stats ???]
0x0090B6F8 : "Priest\0"   (8 bytes)
0x0090B700 : [??? stats ???]
...
0x0090B734 : "Elf\0"      (4 bytes)
0x0090B738 : [??? stats ???]
0x0090B74C : "Fairy\0"    (6 bytes)
0x0090B752 : [??? stats ???]
```

**Hypothèse**: Chaque classe a une structure fixe avec:
- Nom en ASCII (variable, terminé par \0)
- Padding jusqu'à l'alignement
- Stats en int16/uint16 (2 bytes chacune)
- Total estimé: 20-40 bytes par classe

---

## 📁 Structure des Fichiers

### Fichiers de Classe
Chaque classe aura son propre fichier JSON:
- `Warrior.json`
- `Priest.json`
- `Elf.json`
- `Fairy.json`
- `Wizard.json`
- `Dwarf.json`
- `Fighter.json`
- `Ranger.json`
- `Thief.json`

### Format JSON
```json
{
  "class_name": "Warrior",
  "offset_in_blaze_all": "0x0090B6E8",
  "base_stats": {
    "level_1": {
      "hp": 100,
      "mp": 20,
      "strength": 12,
      "defense": 10,
      "magic": 5,
      "magic_defense": 5,
      "speed": 8,
      "luck": 5
    }
  },
  "stat_growth": {
    "hp_per_level": 8,
    "mp_per_level": 2,
    "strength_per_level": 1.2,
    "defense_per_level": 0.8,
    "magic_per_level": 0.3,
    "magic_defense_per_level": 0.4,
    "speed_per_level": 0.5,
    "luck_per_level": 0.2
  },
  "spell_list_id": 0,
  "starting_equipment": {
    "weapon": "Shortsword",
    "armor": "Leather Armor",
    "accessory": null
  },
  "notes": "Physical damage dealer with high HP and strength"
}
```

---

## 🛠️ Scripts Disponibles

### 1. `explore_class_stats.py`
Script pour explorer la zone mémoire 0x0090B6E8 et extraire les données brutes.

**Usage:**
```bash
py -3 explore_class_stats.py
```

**Output:**
- Affiche les bytes autour de chaque nom de classe
- Tente d'identifier les patterns de stats
- Génère un rapport d'analyse

### 2. `create_class_template.py`
Génère les fichiers JSON template pour chaque classe.

**Usage:**
```bash
py -3 create_class_template.py
```

### 3. `patch_class_stats.py` (À venir)
Script pour modifier les stats des classes dans BLAZE.ALL.

---

## 📝 Méthodologie de Recherche

### Étape 1: Analyse de la Zone Mémoire ✅ À FAIRE
1. Extraire les 100 bytes autour de chaque nom de classe
2. Chercher des patterns de int16 (2 bytes)
3. Comparer avec les valeurs connues in-game
4. Identifier les stats communes entre classes

### Étape 2: Tests In-Game 🎮 REQUIS
1. Créer un nouveau personnage de chaque classe
2. Noter les stats de niveau 1
3. Monter de niveau et noter les gains
4. Comparer avec les données extraites

### Étape 3: Validation 🔬 À FAIRE
1. Modifier une stat dans BLAZE.ALL
2. Tester in-game
3. Confirmer que la modification fonctionne
4. Documenter l'offset exact

### Étape 4: Documentation Complète 📚 À FAIRE
1. Créer les fichiers JSON pour chaque classe
2. Remplir avec les données validées
3. Créer un index général
4. Ajouter des exemples de modification

---

## 🎯 Liens avec Autres Modules

### Spell Lists
Les listes de sorts trouvées à **0x002CA424** sont probablement liées aux classes:
- Liste 1-2: Classes magiques (Wizard, Priest?)
- Liste 3-5: Classes hybrides (Elf, Fairy?)
- Liste 6-7: Classes physiques (Warrior, Fighter?)

Voir `spells/CLASS_DATA_ANALYSIS.md` pour détails.

### Fate Coin Shop
Les équipements spécifiques par classe sont documentés dans:
`fate_coin_shop/fate_coin_shop.json`

Classes utilisées:
- Warrior
- Priest/ess
- Rogue
- Sorcerer/ess
- Hunter
- Elf
- Dwarf
- Fairy

**Note**: Légère différence de nomenclature (Rogue vs Thief, Sorcerer vs Wizard)

---

## ⚠️ Limitations Actuelles

### Données Manquantes
1. **Stats de base**: Aucune donnée confirmée
2. **Progression par niveau**: Format inconnu
3. **Level cap**: Maximum level inconnu
4. **EXP requirements**: Table d'expérience non trouvée
5. **Class-specific abilities**: Capacités spéciales non documentées

### Questions Ouvertes
- Les stats augmentent-elles linéairement ou avec une formule?
- Y a-t-il des stats cachées (Crit Rate, Evasion, etc.)?
- Les classes ont-elles des modificateurs de dégâts élémentaires?
- Existe-t-il des soft caps ou hard caps pour les stats?

---

## 📅 Prochaines Étapes

1. ✅ Créer la structure de dossier
2. ✅ Documenter la méthodologie
3. 🔄 Créer le script `explore_class_stats.py`
4. 🔄 Exécuter l'exploration mémoire
5. ⏳ Tests in-game requis
6. ⏳ Validation et documentation

---

## 📚 Références

### Fichiers Liés
- `spells/CLASS_DATA_ANALYSIS.md` - Analyse des listes de sorts
- `fate_coin_shop/fate_coin_shop.json` - Équipements par classe
- `monster_stats/_index.json` - Structure des stats de monstre (référence)

### Zones Mémoire
- **0x0090B6E8 - 0x0090B7BC** : Noms de classes (zone principale)
- **0x002CA424 - 0x002CA8E4** : Listes de sorts
- **0x007EDE4B** : Dwarf (occurrence secondaire)
- **0x00919984** : Fighter
- **0x0152AD8C** : Thief
- **0x0163CF0C** : Wizard
- **0x01FB854C** : Ranger

---

**Dernière mise à jour:** 2026-02-04
**Statut:** 🔍 Recherche en cours
**Contribution:** Tests in-game requis pour validation
