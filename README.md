# Blaze & Blade - Gameplay Patch & Analysis

## 📖 Description

Ce repository contient une analyse complète des données de gameplay extraites du jeu **Blaze & Blade: Eternal Quest** (PlayStation, 1998).

## 📊 Contenu

### 📁 Dossier `spells/`

Base de données complète de **90 sorts** extraits et analysés du fichier BLAZE.ALL :

- **90 fichiers JSON** - Un fichier par sort avec toutes ses statistiques
- **INDEX.json** - Vue d'ensemble de tous les sorts
- **README.md** - Documentation utilisateur
- **STRUCTURE_ANALYSIS.md** - Analyse technique détaillée de la structure binaire

## 🎮 À propos du jeu

**Blaze & Blade: Eternal Quest**
- **Plateforme** : Sony PlayStation (PSX)
- **Année** : 1998
- **Développeur** : T&E Soft
- **Genre** : Action-RPG

## 📋 Caractéristiques de l'analyse

### Stats identifiées pour chaque sort

- ⚡ **Coût en MP** (Mana Points)
- 💥 **Puissance/Dégâts**
- 🔮 **Élément** (Neutre, Feu, Glace, Foudre, Sacré)
- 🎯 **Type d'effet** (Damage, AOE, Multi-target, Buff)
- 👥 **Cible** (Single, Group, All enemies, Ally)
- 🏷️ **ID du sort**
- 🎚️ **Niveau magique**
- 🚩 **Flags spéciaux**

### Exemples de sorts

| Sort | MP | Power | Élément | Type | Cible |
|------|----|----|---------|------|-------|
| Blaze | 9 | 15 | Neutre | Direct Damage | All Enemies |
| Thunderbolt | 20 | 70 | Foudre | Multi-Target | Enemy Group |
| Blizzard | 11 | 30 | Glace | Area Damage | Area |
| Healing | 30 | 5 | Sacré | Status/Buff | Single Target |

## 🔬 Méthodologie

### Extraction des données

Les données ont été extraites par **reverse engineering** du fichier binaire `BLAZE.ALL` (46 MB) :

1. **Analyse de la structure binaire** (48 bytes par sort)
2. **Identification des patterns** répétitifs
3. **Validation** avec les valeurs connues du jeu
4. **Interprétation** des champs et flags
5. **Documentation** complète de la structure

### Structure identifiée

Chaque sort est précédé d'une structure de 48 bytes contenant :
- Position -32 : ID/Coût MP
- Position -26 : Élément (0=Neutre, 2=Foudre, 5=Glace, 8=Sacré)
- Position -24 : Puissance/Dégâts
- Position -17 : Type d'effet
- Position -16 : Flags de cible
- Voir `spells/STRUCTURE_ANALYSIS.md` pour les détails complets

## 📈 Statistiques

- **Total sorts** : 90
- **Éléments** : 5 types identifiés
- **Types d'effets** : 4+ types identifiés
- **Types de cibles** : 5+ types identifiés

## 🛠️ Utilisation

### Charger les données d'un sort

```python
import json

# Charger un sort spécifique
with open('spells/Blaze.json', 'r', encoding='utf-8') as f:
    blaze = json.load(f)

print(f"Nom: {blaze['name']}")
print(f"MP Cost: {blaze['detailed_stats']['mp_cost']}")
print(f"Power: {blaze['detailed_stats']['power_damage']}")
print(f"Element: {blaze['interpretations']['element']}")
print(f"Target: {blaze['interpretations']['target']}")
```

### Charger l'index complet

```python
import json

with open('spells/INDEX.json', 'r', encoding='utf-8') as f:
    index = json.load(f)

print(f"Total spells: {index['total_spells']}")
print("By type:")
for spell_type, count in index['by_type'].items():
    print(f"  {spell_type}: {count}")
```

## 📝 Structure des fichiers JSON

Chaque sort contient :

```json
{
  "name": "Nom du sort",
  "type": "Type général",
  "offset": "Position dans BLAZE.ALL",
  "stats": { /* Stats de base */ },
  "detailed_stats": {
    "spell_id": 9,
    "mp_cost": 9,
    "power_damage": 15,
    "magic_level": 24,
    "element": 0,
    "effect_type_byte": 4,
    "target_flags": 32800,
    "range_flags": 4160,
    "special_flags": { /* Flags */ }
  },
  "interpretations": {
    "element": "Neutral",
    "effect_type": "Direct Damage",
    "target": "All Enemies"
  },
  "raw_data": { /* Données brutes */ }
}
```

## 🎯 Applications possibles

- **Modding** : Modification des stats de sorts
- **Balance patches** : Rééquilibrage du gameplay
- **Documentation** : Guide complet des sorts
- **Traduction** : Base pour localisation
- **Analyse** : Étude du game design

## ⚠️ Notes

- Le fichier `BLAZE.ALL` n'est pas inclus (46 MB, propriété de T&E Soft)
- Cette analyse est fournie à des fins éducatives et de préservation
- Certains champs restent à identifier (voir STRUCTURE_ANALYSIS.md)

## 📅 Historique

- **2026-02-03** : Analyse initiale et extraction complète des sorts
- **2026-02-03** : Identification de la structure binaire
- **2026-02-03** : Documentation complète

## 📧 Contact

Repository maintenu par Ben Maurin (ben.maurin@gmail.com)

## 📜 Licence

Cette analyse est fournie "as-is" à des fins de recherche et de préservation du patrimoine vidéoludique.

---

*Blaze & Blade: Eternal Quest © 1998 T&E Soft*
