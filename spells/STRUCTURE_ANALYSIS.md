# Analyse complète de la structure des sorts - Blaze & Blade

## 📊 Structure binaire identifiée

Chaque sort dans BLAZE.ALL est précédé d'une structure de **48 bytes** contenant toutes ses statistiques.

### Map mémoire (offset relatif au nom du sort)

```
Offset  | Size | Type  | Description                              | Valeurs
--------|------|-------|------------------------------------------|------------------
-48..-33| 16   | Text  | Nom du sort précédent                    | ASCII
-32     | 1    | Byte  | ID du sort / Coût MP primaire            | 1-200
-31     | 1    | Byte  | Padding                                  | 0x00
-30     | 1    | Byte  | Variante du sort                         | 0-255
-29     | 1    | Byte  | Type magique / Niveau                    | 0-255
-28     | 1    | Byte  | Coût MP secondaire / Power alt.          | 1-200
-27     | 1    | Byte  | Padding                                  | 0x00
-26     | 1    | Byte  | Élément                                  | Voir tableau
-25     | 1    | Byte  | Padding                                  | 0x00
-24     | 1    | Byte  | Puissance / Dégâts / Montant soin        | 1-200
-23     | 1    | Byte  | Padding                                  | 0x00
-22..-21| 2    | Word  | Modificateurs spéciaux                   | 0x0000-0xFFFF
-20     | 1    | Byte  | Flags effets actifs                      | 0x00-0xFF
-19     | 1    | Byte  | Flags spéciaux                           | 0x00-0xFF
-18     | 1    | Byte  | Flags attributs                          | 0x00-0xFF
-17     | 1    | Byte  | Type d'effet                             | Voir tableau
-16..-15| 2    | Word  | Flags cible (little-endian)              | Voir tableau
-14..-13| 2    | Word  | Flags portée/zone (little-endian)        | Voir tableau
-12..-1 | 12   | Data  | Paramètres additionnels                  | Variable
```

## 🔍 Détails des champs identifiés

### Coût en MP (Mana Points)
- **Position**: Byte -32 (primaire) ou Byte -28 (secondaire)
- **Range**: 1-200
- **Note**: L'ID du sort correspond souvent au coût MP

### Puissance / Dégâts
- **Position**: Byte -24
- **Range**: 1-200
- **Usage**: Dégâts pour attaques, montant de soin pour sorts de soin

### Élément (Byte -26)

| Valeur | Élément      | Description                    |
|--------|--------------|--------------------------------|
| 0x00   | Neutral      | Sans élément                   |
| 0x02   | Lightning    | Foudre / Électrique            |
| 0x05   | Ice          | Glace / Froid                  |
| 0x08   | Holy/Healing | Sacré / Soin                   |

### Type d'effet (Byte -17)

| Valeur | Type           | Description                          |
|--------|----------------|--------------------------------------|
| 0x03   | Status/Buff    | Altération d'état ou amélioration    |
| 0x04   | Direct Damage  | Dégâts directs sur une cible         |
| 0x06   | Area Damage    | Dégâts de zone (AOE)                 |
| 0x09   | Multi-Target   | Cibles multiples                     |
| 0x0C   | Special        | Effet spécial (à déterminer)         |

### Flags de cible (Word -16..-15, little-endian)

| Valeur | Cible          | Description                          |
|--------|----------------|--------------------------------------|
| 0x1040 | Single Enemy   | Un seul ennemi                       |
| 0x1020 | Enemy Group    | Groupe d'ennemis                     |
| 0x8020 | All Enemies    | Tous les ennemis                     |
| 0x2080 | Single Ally    | Un seul allié                        |
| 0x1010 | Self           | Le lanceur lui-même                  |

## 📈 Exemples concrets

### Blaze (Sort de feu basique)
```
Offset: 0x00909048
Byte -32: 0x09 (9)  → ID/MP Cost = 9
Byte -28: 0x0F (15) → Power alternative
Byte -26: 0x00      → Element = Neutral
Byte -24: 0x00      → Power = 0 (utilise -28)
Byte -17: 0x04      → Effect = Direct Damage
Word -16: 0x8020    → Target = All Enemies
```
**Stats**: MP 9, Power 15, Neutre, Dégâts directs, Tous les ennemis

### Thunderbolt (Sort de foudre puissant)
```
Offset: 0x00909258
Byte -32: 0x14 (20) → ID/MP Cost = 20
Byte -28: 0x2D (45) → Power alternative
Byte -26: 0x02      → Element = Lightning
Byte -24: 0x46 (70) → Power = 70
Byte -17: 0x09      → Effect = Multi-Target
Word -16: 0x1020    → Target = Enemy Group
```
**Stats**: MP 20, Power 70, Foudre, Multi-cibles, Groupe ennemi

### Blizzard (Sort de glace)
```
Offset: 0x009090A8
Byte -32: 0x0B (11) → ID/MP Cost = 11
Byte -28: 0x10 (16) → MP secondaire
Byte -26: 0x05      → Element = Ice
Byte -24: 0x1E (30) → Power = 30
Byte -17: 0x06      → Effect = Area Damage
Word -16: 0x8010    → Target = Area
```
**Stats**: MP 11, Power 30, Glace, Dégâts de zone

### Healing (Sort de soin)
```
Offset: 0x00909408
Byte -32: 0x1E (30) → ID/MP Cost = 30
Byte -26: 0x08      → Element = Holy/Healing
Byte -24: 0x05 (5)  → Heal Amount = 5
Byte -17: 0x03      → Effect = Status/Buff
Word -16: 0x1040    → Target = Single Target
```
**Stats**: MP 30, Heal 5, Sacré, Buff, Cible unique

## 🎯 Patterns identifiés

### Relation ID ↔ Coût MP
Dans la majorité des cas, l'ID du sort (Byte -32) correspond directement au coût en MP.

### Puissance des sorts
- **Sorts faibles**: 5-20 power
- **Sorts moyens**: 20-50 power
- **Sorts puissants**: 50-100 power
- **Sorts ultimes**: 100+ power

### Coût MP typique
- **Sorts basiques**: 5-15 MP
- **Sorts intermédiaires**: 15-40 MP
- **Sorts avancés**: 40-80 MP
- **Sorts ultimes**: 80-200 MP

## 🔬 Méthodologie d'analyse

1. **Extraction**: Lecture de 48 bytes avant chaque nom de sort
2. **Comparaison**: Analyse différentielle entre sorts similaires
3. **Validation**: Vérification avec les valeurs connues du jeu
4. **Pattern matching**: Identification des structures répétitives
5. **Interprétation**: Déduction de la signification des champs

## ⚠️ Notes et limitations

### Champs non identifiés
- **Bytes -30, -29**: Variante et type magique (signification partielle)
- **Bytes -22..-21**: Modificateurs spéciaux (usage inconnu)
- **Bytes -20, -19, -18**: Flags (usage partiel identifié)
- **Bytes -12..-1**: Paramètres additionnels (usage inconnu)

### Incertitudes
- Certains sorts ont des flags inhabituels
- La relation entre bytes -28 et -24 n'est pas toujours claire
- Les modificateurs spéciaux nécessitent plus d'analyse

### Valeurs suspectes
Certains sorts ont des valeurs qui semblent incohérentes :
- Power > 200 (possibles erreurs d'extraction)
- Target flags inconnus (nouveaux types à identifier)
- Element types au-delà de 8 (éléments cachés?)

## 📝 Utilisation pratique

### Lire les stats d'un sort

```python
import struct

# Lire la structure d'un sort
with open('BLAZE.ALL', 'rb') as f:
    data = f.read()

spell_offset = 0x00909048  # Blaze
struct_data = data[spell_offset-48:spell_offset]

# Extraire les champs
mp_cost = struct_data[16]
power = struct_data[24]
element = struct_data[22]
effect_type = struct_data[31]
target_flags = struct.unpack('<H', struct_data[32:34])[0]

print(f"MP: {mp_cost}, Power: {power}, Element: {element}")
print(f"Effect: 0x{effect_type:02X}, Target: 0x{target_flags:04X}")
```

## 📚 Ressources

- **Fichier source**: BLAZE.ALL (46,206,976 bytes)
- **Zone des sorts**: 0x00909000 - 0x0090A000
- **Nombre de sorts**: 90+ identifiés
- **Format**: PlayStation 1 (little-endian)

## 🎮 Contexte du jeu

**Blaze & Blade: Eternal Quest**
- Plateforme: Sony PlayStation (PSX)
- Année: 1998
- Développeur: T&E Soft
- Genre: Action-RPG

---

*Document créé le 3 février 2026*
*Analyse basée sur reverse engineering du fichier BLAZE.ALL*
