# Analyse des Données de Classe - Blaze & Blade

**Date:** 2026-02-03

---

## 📍 Noms de Classes dans BLAZE.ALL

### Positions des Noms de Classe

| Classe | Occurrences | Première Position | Positions Suivantes |
|--------|-------------|-------------------|---------------------|
| **Warrior** | 4 | 0x0090B6E8 | 0x0090B758, 0x0090D688 |
| **Wizard** | 5 | 0x0163CF0C | 0x0163CF4D, 0x0179E41C, ... |
| **Fairy** | 5 | 0x0090B74C | 0x0090B7BC, 0x0090D6D4, ... |
| **Elf** | 5 | 0x0090B734 | 0x0090B7A4, 0x0090D6C0, ... |
| **Dwarf** | 5 | 0x007EDE4B | 0x007EDE8F, 0x007EE64B, ... |
| **Priest** | 5 | 0x0090B6F8 | 0x0090B768, 0x0090D694, ... |
| **Fighter** | 1 | 0x00919984 | - |
| **Ranger** | 2 | 0x01FB854C | 0x01FB858D |
| **Thief** | 2 | 0x0152AD8C | 0x0152ADCD |

### Zone Principale des Noms

**Offset : 0x0090B6E8 - 0x0090B7BC**

Cette zone contient les noms de plusieurs classes proches les unes des autres :
- Warrior (0x0090B6E8)
- Priest (0x0090B6F8)
- Elf (0x0090B734)
- Fairy (0x0090B74C)
- Warrior (répété à 0x0090B758)
- Priest (répété à 0x0090B768)

**Structure supposée** : Chaque classe a probablement une structure de données fixe, avec le nom en ASCII suivi de statistiques.

---

## 🎯 Listes de Sorts (Zone 0x002CA424)

### Structure Identifiée

**Type** : Listes de progression de sorts (non pas par classe, mais par niveau ?)

7 listes trouvées avec des progressions similaires :

#### Liste 1 @ 0x002CA49C (13 sorts)
```
Enchant Earth → Enchant Wind → Enchant Water → Charm → Silence →
Magic → Unknown_169 → Blaze → Shield → Unknown_173 → Anti-Circle →
Silence → Unknown_175
```

**Spell IDs** : [163, 164, 165, 166, 167, 168, 169, 9, 170, 173, 174, 167, 175]

#### Liste 2 @ 0x002CA528 (13 sorts)
```
Enchant Earth → Enchant Wind → Enchant Water → Charm → Silence →
Magic → Unknown_169 → Blaze → Shield → Unknown_173 → Anti-Circle →
Silence → Unknown_175
```

**Identique à Liste 1** - Probablement une autre classe avec les mêmes sorts

#### Liste 3 @ 0x002CA5B4 (13 sorts)
```
Enchant Wind → Enchant Water → Charm → Silence → Magic →
Unknown_169 → Blaze → Shield → Unknown_173 → Anti-Circle → ...
```

**Pattern** : Commence sans Enchant Earth (progression ?)

#### Liste 4 @ 0x002CA640 (13 sorts)
```
Enchant Water → Charm → Silence → Magic → Unknown_169 →
Blaze → Shield → Unknown_173 → Anti-Circle → ...
```

**Pattern** : Commence sans Enchant Earth/Wind

#### Liste 5 @ 0x002CA6CC (13 sorts)
```
Charm → Silence → Magic → Unknown_169 → Blaze → Shield →
Unknown_173 → Anti-Circle → ...
```

**Pattern** : Commence sans les Enchant

#### Liste 6 @ 0x002CA758 (13 sorts)
```
Silence → Magic → Unknown_169 → Blaze → Shield → Unknown_173 →
Anti-Circle → Silence → Unknown_175 → ...
```

#### Liste 7 @ 0x002CA7E4 (12 sorts)
```
Magic → Unknown_169 → Blaze → Shield → Unknown_173 → Anti-Circle →
Silence → Unknown_175 → ...
```

---

## 🔍 Analyse du Pattern

### Observation Clé

Les listes se succèdent en **enlevant progressivement les premiers sorts** :

```
Liste 1: [Enchant Earth, Enchant Wind, Enchant Water, Charm, Silence, Magic, ...]
Liste 2: [Enchant Earth, Enchant Wind, Enchant Water, Charm, Silence, Magic, ...]  (identique)
Liste 3: [              Enchant Wind, Enchant Water, Charm, Silence, Magic, ...]
Liste 4: [                            Enchant Water, Charm, Silence, Magic, ...]
Liste 5: [                                           Charm, Silence, Magic, ...]
Liste 6: [                                                  Silence, Magic, ...]
Liste 7: [                                                           Magic, ...]
```

### Hypothèses

1. **Progression par Niveau** :
   - Chaque liste représente les sorts disponibles à un niveau donné
   - Les sorts de base (Enchant Earth/Wind/Water) disparaissent aux niveaux supérieurs
   - Les sorts avancés (Shield, Anti-Circle) restent disponibles

2. **Classes avec Accès Différent** :
   - Liste 1 & 2 : Classes avec accès complet (Wizard, Priest ?)
   - Liste 3-5 : Classes avec accès intermédiaire (Warrior, Fairy ?)
   - Liste 6-7 : Classes avec accès limité (Fighter, Thief ?)

3. **Arbres de Compétences** :
   - Chaque liste = une branche d'arbre de compétences
   - Progression linéaire dans l'apprentissage des sorts

---

## 📊 Sorts Identifiés

### Sorts Connus

| Spell ID | Nom | MP Cost | Présent dans |
|----------|-----|---------|--------------|
| 9 | Blaze | 16 | Toutes les listes |
| 163 | Enchant Earth | 16 | Listes 1-2 uniquement |
| 164 | Enchant Wind | 16 | Listes 1-3 |
| 165 | Enchant Water | 16 | Listes 1-4 |
| 166 | Charm | 8 | Listes 1-5 |
| 167 | Silence | 8 | Toutes les listes |
| 168 | Magic (Magic Missile) | 12 | Toutes les listes |
| 170 | Shield | 12 | Listes 1-7 |
| 174 | Anti-Circle | 80 | Listes 1-7 |

### Sorts Inconnus à Identifier

| Spell ID | Présence | Notes |
|----------|----------|-------|
| 169 | Toutes les listes | Juste après Magic |
| 173 | Listes 1-7 | Juste après Shield |
| 175 | Listes 1-7 | Après Anti-Circle |
| 182-191 | Variable | Sorts avancés ? |

---

## 🔧 Structure de Données Supposée

### Format de Liste de Sorts

Chaque liste semble suivre ce format :

```
[spell_id_1] [spell_id_2] [spell_id_3] ... [spell_id_n] [separator/padding]
```

- **Taille** : ~15-20 spell_id par liste
- **Séparation** : Les listes sont séparées par ~70 words (140 bytes)
- **Format** : int16 little-endian

### Calcul des Offsets

Pour accéder à la liste N :
```
Offset = 0x002CA424 + (N * 70 * 2)
      = 0x002CA424 + (N * 140)
```

Où N = 0, 1, 2, ... (numéro de la liste)

---

## ⚠️ Limitations

### Données Manquantes

1. **Lien Classe ↔ Liste** :
   - Aucune donnée trouvée reliant directement un nom de classe à une liste de sorts
   - Le mapping doit être fait par expérimentation in-game

2. **Sorts 169, 173, 175, 182-191** :
   - Noms inconnus
   - MP costs inconnus
   - Doivent être identifiés in-game

3. **Multiplicateurs de Coût MP** :
   - Pas de données trouvées sur les modificateurs de coût par classe
   - Les coûts MP semblent fixes par sort (pas de variation par classe)

### Zones Non Explorées

- Zone autour de 0x0090B6E8 (noms de classe) : Peut contenir des statistiques de classe
- Zones entre les listes de sorts : Peuvent contenir des données de configuration
- Autres zones dans BLAZE.ALL

---

## 📝 Prochaines Étapes

### Pour Compléter l'Analyse

1. **Identifier les Sorts Inconnus** :
   - Jouer le jeu avec différentes classes
   - Noter quels sorts ont les spell_id 169, 173, 175, etc.
   - Mesurer leurs coûts MP in-game

2. **Mapper Classe ↔ Liste** :
   - Créer un nouveau personnage de chaque classe
   - Noter quels sorts sont disponibles dès le début
   - Comparer avec les listes trouvées

3. **Analyser la Zone 0x0090B6E8** :
   - Lire les 100-200 bytes autour de chaque nom de classe
   - Chercher des patterns de statistiques (HP, MP, Force, etc.)

4. **Tester les Modifications** :
   - Modifier une liste de sorts
   - Vérifier in-game si les changements sont appliqués
   - Documenter le comportement

---

## 📚 Références

### Fichiers Liés
- `MP_COST_LOCATIONS.json` - Offsets des coûts MP
- `MP_COST_DOCUMENTATION.md` - Documentation complète des coûts MP
- `[Sort].json` - Fichiers individuels mis à jour avec infos de modification

### Zones Mémoire Importantes
- 0x0090B6E8 - 0x0090B7BC : Noms de classes
- 0x002CA424 - 0x002CA8E4 : Listes de sorts
- 0x00909000 - 0x0090A000 : Structures des sorts

---

**Fin du document**
