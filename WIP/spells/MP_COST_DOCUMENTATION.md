# Documentation des Coûts MP - Blaze & Blade: Eternal Quest

**Date:** 2026-02-03
**Analysé par:** Ben Maurin & Claude Sonnet 4.5

---

## 📋 Résumé Exécutif

Les coûts MP (Mana Points) des sorts dans Blaze & Blade sont stockés dans **DEUX emplacements différents** dans BLAZE.ALL :

1. **Structure des sorts** (offset 0x00909000) : Champ `raw[10]` (byte[20]) - valeur de base
2. **Tables dispersées** : Pattern `[spell_id, mp_cost]` en int16 little-endian - **vrais coûts in-game**

---

## 🎯 Coûts MP In-Game (Confirmés)

| Sort | Spell ID | MP Cost | Occurrences trouvées |
|------|----------|---------|----------------------|
| Enchant Water/Fire/Wind/Earth | 163-165 | 16 | 25-45 |
| Charm | 166 | 8 | 20 |
| Silence | 167 | 8 | 46 |
| Magic (Magic Missile) | 168 | 12 | 50+ |
| Shield | 170 | 12 | 8 |
| Anti-Circle | 174 | 80 | 4 |
| Blaze | 9 | 16 | 50+ |
| Lightningbolt | 10 | 16 | 50+ |
| Petrifaction | 18 | 38 | 50+ |

---

## 📊 Analyse Comparative : Structure vs Tables

### Sorts où raw[10] = MP Cost (correspondance exacte)

```
Sort              | raw[10] | In-game | Status
------------------|---------|---------|--------
Enchant Earth     |   16    |   16    | ✓ MATCH
Enchant Wind      |   16    |   16    | ✓ MATCH
Enchant Water     |   16    |   16    | ✓ MATCH
Silence           |    8    |    8    | ✓ MATCH
Lightningbolt     |   16    |   16    | ✓ MATCH
```

### Sorts où raw[10] ≠ MP Cost (ajustements requis)

```
Sort              | raw[10] | In-game | Ratio   | Formule possible
------------------|---------|---------|---------|------------------
Charm             |   16    |    8    | 0.50    | raw[10] / 2
Shield            |   30    |   12    | 0.40    | raw[10] / 2.5
Magic             |    8    |   12    | 1.50    | raw[10] * 1.5
Petrifaction      |   40    |   38    | 0.95    | raw[10] - 2
Blaze             |   15    |   16    | 1.07    | raw[10] + 1
Anti-Circle       |   60    |   80    | 1.33    | raw[10] * 4/3
```

---

## 🔍 Structure du Pattern dans les Tables

### Format Découvert

Le pattern trouvé dans BLAZE.ALL est :
```
[spell_id (int16 LE), mp_cost (int16 LE), autres_données...]
```

- **Taille** : 2 bytes (spell_id) + 2 bytes (mp_cost) = 4 bytes minimum
- **Ordre** : Little-endian (LSB first)
- **Répétition** : Structure répétitive avec écarts réguliers de 18 ou 52 bytes

### Exemple : Magic (spell_id=168, mp=12)

```hex
Offset 0x00914961:
A8 00  D5 00  0C 21  20 00  00 A6  A8 00  0C 00
              ^^^^^^ ^^^^^^
              168    12

Contexte (int16): [39087, 213, 8460, 32, 42496, 168, 12, 0, ...]
```

### Exemple : Anti-Circle (spell_id=174, mp=80)

```hex
Offset 0x009B827E:
55 41  88 01  00 00  38 A4  23 08  AE 00  50 00
                                    ^^^^^^ ^^^^^^
                                    174    80

Contexte (int16): [16421, 392, 0, 42152, 2083, 174, 80, 1057, ...]
```

---

## 📍 Principales Zones de Stockage

### Zone 1 : Structures Répétitives (0x002F6854)

**Caractéristiques** :
- Pattern régulier avec écarts de 18/52 bytes
- Contient : Silence, Blaze, Lightningbolt
- Structure : `[?, ?, spell_id, mp_cost, ?, ?, ?]`

**Exemple d'extraction** :
```
Offset    | Spell_ID | MP | Sort
----------|----------|----|-------------
0x002F6870|   167    |  8 | Silence
0x002F6882|     9    | 16 | Blaze
0x002F68B6|   167    |  8 | Silence
0x002F68C8|     9    | 16 | Blaze
```

### Zone 2 : Code/Données Mixtes (0x00914961)

**Caractéristiques** :
- Occurrences multiples de Magic (168, 12)
- Espacées de ~28-60 bytes
- Probablement dans du code exécutable ou des tables de configuration

### Zone 3 : Données de Classe/Configuration (0x002CA424)

**Caractéristiques** :
- Contient Shield (170, 12)
- Entourée de séquences de spell_id consécutifs : `[166, 167, 168, 169, 9, 170, 12, ...]`
- Suggère une table de sorts par classe ou par ordre

---

## 🎮 Utilisation par le Jeu

### Hypothèse de Fonctionnement

1. **Chargement initial** : Le jeu lit la structure du sort à 0x00909000
   - Récupère les propriétés de base (élément, puissance, etc.)
   - Lit `raw[10]` comme **coût de base**

2. **Calcul du coût final** : Le jeu consulte une table séparée
   - Cherche le `spell_id` dans les tables
   - Récupère le **vrai coût MP** à utiliser in-game
   - Applique éventuellement des modificateurs de classe

3. **Affichage/Consommation** : Utilise la valeur finale des tables

### Pourquoi Deux Sources ?

Plusieurs explications possibles :
- **Équilibrage** : Les développeurs ont ajusté les coûts sans modifier les structures de base
- **Modificateurs de classe** : raw[10] = coût de base, tables = coûts par classe
- **Versions** : raw[10] = version alpha, tables = version finale
- **Système de calcul** : Formules différentes selon le contexte d'utilisation

---

## 📝 Fichiers Générés

### MP_COST_LOCATIONS.json

Contient pour chaque sort :
- `spell_id` : Identifiant du sort
- `mp_cost` : Coût MP in-game
- `total_occurrences` : Nombre d'occurrences trouvées
- `occurrences[]` : Liste des 20 premiers offsets avec contexte

**Format** :
```json
{
  "Magic": {
    "spell_id": 168,
    "mp_cost": 12,
    "total_occurrences": 50,
    "occurrences": [
      {
        "offset": "0x00914961",
        "offset_dec": 9521505,
        "context_bytes": [175, 152, 213, 0, 12, 33, 32, ...]
      }
    ]
  }
}
```

---

## 🔧 Outils de Modification

### Pour Modifier un Coût MP

**Méthode 1 : Modifier raw[10] dans la structure (si correspondance exacte)**
```
Fichier : BLAZE.ALL
Offset  : 0x00909000 + (spell_offset - 48) + 20
Format  : Byte (valeur simple)
```

**Méthode 2 : Modifier toutes les occurrences dans les tables**
```
Fichier : BLAZE.ALL
Pattern : [spell_id (2 bytes LE), mp_cost (2 bytes LE)]
Action  : Chercher et remplacer TOUTES les occurrences
```

### Script Python Exemple

```python
import struct

def change_mp_cost(data, spell_id, old_cost, new_cost):
    old_pattern = struct.pack('<HH', spell_id, old_cost)
    new_pattern = struct.pack('<HH', spell_id, new_cost)

    count = 0
    index = 0
    while True:
        index = data.find(old_pattern, index)
        if index == -1:
            break
        data = data[:index] + new_pattern + data[index+4:]
        count += 1
        index += 4

    return data, count

# Exemple : Changer Magic de 12 à 15 MP
with open('BLAZE.ALL', 'rb') as f:
    data = bytearray(f.read())

data, changed = change_mp_cost(data, 168, 12, 15)

with open('BLAZE_MODIFIED.ALL', 'wb') as f:
    f.write(data)

print(f"Changed {changed} occurrences")
```

---

## ⚠️ Notes Importantes

### Limitations Connues

1. **Enchant Fire** : Utilise une structure différente
   - raw[10] = 2 (pas 16)
   - Coût réel dans raw[17] = [16, 16]

2. **Sorts avec peu d'occurrences** :
   - Anti-Circle : Seulement 4 occurrences
   - Shield : Seulement 8 occurrences
   - Modifier TOUTES les occurrences est critique

3. **Validation nécessaire** :
   - Toujours vérifier in-game après modification
   - Sauvegarder l'original avant modifications

### Zones Non Explorées

- Fichier SLES_008.45 (exécutable) : Peut contenir du code de calcul
- Fichier .bin : Image ROM complète
- Autres sections de BLAZE.ALL non analysées

---

## 📚 Références

### Fichiers Créés
- `MP_COST_LOCATIONS.json` - Base de données des offsets
- `MP_COST_DOCUMENTATION.md` - Ce document
- `FINAL_MP_COST_ANALYSIS.txt` - Analyse initiale (obsolète)

### Méthodes Utilisées
1. Recherche de patterns binaires
2. Analyse de structures répétitives
3. Comparaison avec valeurs in-game
4. Validation croisée entre sources

---

## ✅ Validation

### Tests Recommandés

Après modification, vérifier in-game :
1. Le coût MP affiché dans le menu
2. Le MP consommé lors du lancement
3. Pas de crash ou comportement anormal
4. Cohérence avec d'autres sorts similaires

### Checklist de Modification

- [ ] Identifier le spell_id du sort
- [ ] Vérifier le coût MP actuel in-game
- [ ] Sauvegarder BLAZE.ALL original
- [ ] Modifier raw[10] si correspondance exacte
- [ ] Modifier TOUTES les occurrences du pattern [spell_id, mp_cost]
- [ ] Tester in-game
- [ ] Documenter les changements

---

**Fin du document**
