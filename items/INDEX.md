# Items Module - File Index

## 📁 Fichiers du module (version nettoyée)

### 📊 Données finales
- **`all_items_clean.json`** (296 KB) - Base de données complète des 424 items
  - Format structuré avec métadonnées
  - Items catégorisés (Weapons, Armor, Consumables, etc.)
  - Offsets, descriptions, stats pour chaque item

### 📖 Documentation
- **`README.md`** - Guide d'utilisation du module
  - Vue d'ensemble des items
  - Exemples de code Python
  - Structure des données

- **`EXTRACTION_SUMMARY.md`** - Rapport détaillé de l'extraction
  - Méthodologie complète
  - Structure binaire découverte
  - Statistiques et découvertes
  - Limites et prochaines étapes

- **`INDEX.md`** - Ce fichier

### 🔧 Scripts d'extraction

- **`extract_complete_database.py`** (8.6 KB) - Extracteur principal
  - Scanne tout BLAZE.ALL avec stride de 128 bytes
  - Détecte automatiquement les items valides
  - Usage : `py -3 extract_complete_database.py`
  - Génère : données brutes (nettoyées ensuite)

- **`clean_and_finalize.py`** (8.9 KB) - Nettoyeur et finaliseur
  - Filtre les faux positifs (garbage data)
  - Catégorise les items par type
  - Génère `all_items_clean.json` (final)
  - Crée README.md automatiquement
  - Usage : `py -3 clean_and_finalize.py`

---

## 🚀 Workflow d'extraction

### Extraction complète
```bash
cd items
py -3 extract_complete_database.py  # Scan complet de BLAZE.ALL
py -3 clean_and_finalize.py         # Génère all_items_clean.json + README
```

**Note** : Les données brutes intermédiaires sont automatiquement nettoyées.

---

## 📊 Tailles des fichiers (après nettoyage)

| Fichier | Taille | Type |
|---------|--------|------|
| all_items_clean.json | 296 KB | Données finales |
| extract_complete_database.py | 8.6 KB | Script |
| clean_and_finalize.py | 8.9 KB | Script |
| EXTRACTION_SUMMARY.md | 7.4 KB | Documentation |
| INDEX.md | 5.2 KB | Documentation |
| README.md | 3.4 KB | Documentation |

**Total du module** : ~340 KB (vs 1.3 MB avant nettoyage)

---

## 📚 Utilisation des données

### Python
```python
import json

# Charger les items
with open('items/all_items_clean.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    items = data['items']

# Filtrer par catégorie
weapons = [i for i in items if i['category'] == 'Weapons']
consumables = [i for i in items if i['category'] == 'Consumables']

# Rechercher un item spécifique
healing_potion = next(i for i in items if i['name'] == 'Healing Potion')
print(f"Offset: {healing_potion['offset']}")
print(f"Description: {healing_potion['description']}")
```

---

## 🔗 Liens connexes

### Modules similaires
- `../monster_stats/` - Base de données des 124 monstres
- `../spells/` - Base de données des 90 sorts
- `../fate_coin_shop/` - Items de la boutique Fate Coin

### Documentation projet
- `../README.md` - Documentation principale du projet
- `../build_gameplay_patch.bat` - Script de build

---

## 📝 Notes

- **Nettoyage effectué** : Fichiers temporaires et scripts obsolètes supprimés
- Le workflow standard est : `extract_complete_database.py` → `clean_and_finalize.py`
- Les données brutes (all_items.json) sont automatiquement nettoyées après traitement
- Pour modifier un item : éditer `all_items_clean.json` puis créer un patcher (à venir)

---

*Module créé le 2026-02-04*
*Total : 424 items extraits de BLAZE.ALL*
