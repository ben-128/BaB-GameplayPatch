# Items Extraction Summary - Blaze & Blade: Eternal Quest

## 📊 Résumé de l'extraction

**Date** : 2026-02-04
**Source** : `BLAZE.ALL` (46.2 MB)
**Méthode** : Analyse binaire et scan structurel

---

## 🎯 Résultats

### Items extraits
- **Total brut** : 1,244 entrées détectées
- **Items valides** : 424 items uniques
- **Items avec descriptions** : 45 items
- **Taux de réussite** : 34% (après nettoyage)

### Répartition par catégorie

| Catégorie | Nombre | Pourcentage |
|-----------|--------|-------------|
| Miscellaneous | 318 | 75.0% |
| Helmets | 38 | 9.0% |
| Weapons | 17 | 4.0% |
| Consumables | 11 | 2.6% |
| Accessories | 10 | 2.4% |
| Materials | 8 | 1.9% |
| Quest Items | 8 | 1.9% |
| Armor | 5 | 1.2% |
| Shields | 5 | 1.2% |
| Other | 4 | 0.9% |

---

## 🔍 Structure découverte

### Format d'entrée item (128 bytes / 0x80)

```
+0x00: Nom de l'item (null-terminated, max ~32 bytes)
+0x10: Zone de statistiques (valeurs uint16)
  +0x10: Valeur 1
  +0x12: Valeur 2
  +0x30: Valeur 3
  +0x32: Valeur 4
  +0x36: Valeur 5
+0x40: Séparateur (0x0C)
+0x41: Description complète (format: "Nom/Description détaillée")
```

### Exemple concret: Healing Potion

```
Offset: 0x006C6F80

+0x00: "Healing Potion" (0x48 65 61 6C 69 6E 67 20 50 6F 74 69 6F 6E 00)
+0x10: 0x0005 (5)
+0x12: 0x90FF (37119)
+0x40: 0x0C (séparateur)
+0x41: "Healing Potion/Common potion.(Restores HP to single unit)"
```

---

## 📍 Zones mémoire identifiées

### Table principale
- **Offset** : `0x006C6000` - `0x006D6000`
- **Taille** : ~64 KB
- **Contenu** : Items de base (armes, armures, potions)
- **Structure** : Entrées fixes de 128 bytes

### Tables secondaires
- `0x00AAA000` - `0x00AAE000` : Items spéciaux avec descriptions
- `0x00BE0000` - `0x00BE4000` : Variantes d'items
- Multiples occurrences dans tout BLAZE.ALL (pour différentes classes/shops)

---

## 🛠️ Scripts créés

### 1. `extract_complete_database.py`
Scanner complet de BLAZE.ALL avec stride de 128 bytes
- Scanne ~360,000 positions
- Détecte automatiquement les noms d'items valides
- Extrait stats et descriptions
- Comptabilise les occurrences

### 2. `clean_and_finalize.py`
Nettoyage et catégorisation des items
- Filtre les faux positifs (garbage data)
- Catégorise par type (Weapons, Armor, etc.)
- Génère la documentation
- Crée le JSON final propre

### 3. Scripts d'analyse (utilisés pour la recherche)
- `find_item_locations.py` : Localise les items connus
- `analyze_item_structure.py` : Analyse la structure binaire
- `extract_items.py` / `extract_items_v2.py` : Versions préliminaires

---

## 📦 Fichiers générés

### `all_items_clean.json`
```json
{
  "metadata": {
    "source": "BLAZE.ALL",
    "game": "Blaze & Blade: Eternal Quest",
    "total_items": 424,
    "extraction_date": "2026-02-04"
  },
  "items": [
    {
      "name": "Healing Potion",
      "offset": "0x006C6F80",
      "description": "Common potion.(Restores HP to single unit)",
      "category": "Consumables",
      "stats": {
        "0x10": 5,
        "0x12": 37119
      },
      "occurrences_count": 1
    }
  ]
}
```

---

## 🎓 Exemples d'items extraits

### Armes
- Normal Sword, Shortsword, Broad Sword
- Dagger, Mist Dagger
- Bow, Shortbow, Artemis
- Club, Hammer, Rapier
- Wand, Wooden Wand, Rod

### Armures & Protection
- Leather Armor, Crusader Cloak, Shadow Robe
- Leather Shield, Wooden Shield
- Various Helmets (38 types)

### Consommables
- Healing Potion, Mind Potion, Cure Potion
- Elixir, Ambrosia
- Berserk Drug, Blood Extract
- Miracle Powder

### Accessoires
- Blessed Ring, Jewel Ring, Merlin's Ring
- Amulet, Misty Pendant
- Strong Gloves, Quick Boots

### Matériaux
- Material Magic, Material Flame, Material Water
- Material Earth, Material Wind
- Material Light, Material Dark
- Material Holiness, Material Evil

### Items spéciaux
- Fate Coin
- Cross, Holy Orb, Dark Orb, Crystal Orb
- Judge Scale, Knights Banner
- Rope of Return

---

## 💡 Découvertes importantes

### 1. Duplication des items
Chaque item apparaît multiple fois dans BLAZE.ALL :
- Pour chaque classe de personnage (8 classes)
- Pour différents shops/vendors
- Pour différents donjons/niveaux

**Exemple** : "Healing Potion" apparaît 78 fois

### 2. Format uniforme
Tous les items suivent la même structure de 128 bytes, ce qui facilite :
- L'extraction automatisée
- La modification (modding)
- La création de nouveaux items

### 3. Descriptions partielles
Seulement ~10% des items ont des descriptions complètes dans les données extraites. Les autres descriptions sont probablement :
- Stockées ailleurs dans BLAZE.ALL
- Dans le code exécutable (SLES_008.45)
- Générées dynamiquement en jeu

---

## 🔬 Méthodologie utilisée

1. **Identification manuelle** : Recherche d'items connus (Healing Potion, Shortsword, etc.)
2. **Analyse des patterns** : Étude des bytes autour des noms trouvés
3. **Détermination de la structure** : Identification du format 128-byte
4. **Scan complet** : Parcours de tout BLAZE.ALL avec stride fixe
5. **Validation** : Filtrage des faux positifs
6. **Catégorisation** : Classification par type d'item
7. **Documentation** : Génération des fichiers JSON et README

---

## 📈 Statistiques du projet

- **Lignes de code** : ~55,000 (scripts + JSON)
- **Temps d'extraction** : ~2 minutes (pour scanner 46 MB)
- **Taille des données** :
  - `all_items.json` (brut) : 890 KB
  - `all_items_clean.json` : 296 KB
  - Total module : ~1.3 MB

---

## 🚀 Utilisations possibles

### 1. Modding
- Modifier les stats d'items existants
- Créer de nouveaux items
- Rééquilibrer l'économie du jeu

### 2. Documentation
- Guides complets des items
- Wikis du jeu
- Calculateurs de builds

### 3. Traduction
- Base pour localisation FR complète
- Correction de descriptions

### 4. Analyse
- Étude du game design
- Balance analysis
- Item progression curves

---

## 🎯 Prochaines étapes

### À court terme
1. ✅ Extraction complète : **TERMINÉ**
2. ✅ Nettoyage des données : **TERMINÉ**
3. ✅ Documentation : **TERMINÉ**

### À moyen terme
- [ ] Tests in-game pour valider les stats extraites
- [ ] Identification précise de chaque valeur dans les stats
- [ ] Création d'un patcher pour modifier les items
- [ ] Extraction des descriptions manquantes

### À long terme
- [ ] Interface graphique pour éditer les items
- [ ] Générateur d'items procéduraux
- [ ] Base de données en ligne interactive

---

## ⚠️ Limites connues

1. **Descriptions incomplètes** : Seulement 45 items ont des descriptions
2. **Catégorisation imparfaite** : 318 items dans "Miscellaneous"
3. **Stats non décodées** : Les valeurs uint16 nécessitent des tests in-game
4. **Noms tronqués** : Certains noms semblent coupés (max 32 chars)

---

## 📚 Ressources

### Fichiers principaux
- `all_items_clean.json` : Base de données finale
- `README.md` : Guide d'utilisation
- Scripts Python : Outils d'extraction et analyse

### Documentation connexe
- `../README.md` : Documentation du projet complet
- `../monster_stats/` : Système similaire pour les monstres
- `../spells/` : Base de données des sorts

---

**Extraction réalisée par reverse engineering de BLAZE.ALL**
*Blaze & Blade: Eternal Quest © 1998 T&E Soft*
