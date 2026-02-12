# Formation System - Guide d'utilisation

## Vue d'ensemble

Le système de formations permet de modifier les rencontres aléatoires (formations) dans Blaze & Blade. Chaque area a un fichier JSON qui définit ses formations.

## Fichiers

### Pour chaque area
- `floor_X_area_Y.json` - Configuration des formations (éditez ce fichier)
- `floor_X_area_Y_vanilla.json` - Bytes vanilla de référence (NE PAS ÉDITER)

### Scripts
- `patch_formations.py` - Applique les modifications à BLAZE.ALL
- `extract_formations.py` - Extrait les formations du vanilla bin
- `extract_vanilla_bytes_v2.py` - Extrait les bytes vanilla exacts
- `extract_slot_types.py` - Extrait les types de monstres pour suffixes corrects
- `editor.html` - Éditeur visuel (lancer avec `edit_formations.bat`)

### Documentation
- `CUSTOM_FORMATIONS_WORKING.md` - Guide complet formations custom
- `FILLER_FIX.md` - Détails techniques fillers
- `ALL_ZONES_FIXED.md` - Corrections apportées

## Comment créer des formations custom

### 1. Éditer le JSON

Ouvrez `floor_X_area_Y.json` et modifiez la section `formations`:

```json
{
  "formations": [
    {
      "total": 7,
      "slots": [0, 0, 0, 0, 0, 1, 1],
      "composition": [
        {"count": 5, "slot": 0, "monster": "Lv20.Goblin"},
        {"count": 2, "slot": 1, "monster": "Goblin-Shaman"}
      ],
      "suffix": "00000000"
    }
  ]
}
```

**Champs importants:**
- `total` - Nombre de monstres dans cette formation
- `slots` - Liste des slot_index (0, 1, 2...) pour chaque monstre
- `composition` - Auto-calculé pour affichage (optionnel)
- `suffix` - Ignoré, calculé automatiquement par le patcher

**Slot index:**
Correspond à l'ordre dans `monsters`:
```json
"monsters": [
  "Lv20.Goblin",    // slot 0
  "Goblin-Shaman",  // slot 1
  "Giant-Bat"       // slot 2
]
```

### 2. Contraintes importantes

**NE PAS modifier:**
- `formation_count` - Doit rester au nombre vanilla (ex: 8)
- `original_total_slots` - Budget total vanilla (ex: 27)
- `formation_area_bytes` - Taille fixe de l'area (ex: 896)

**Limites:**
- Total des slots ≤ `original_total_slots - formation_count`
- Nombre de formations ≤ `formation_count`
- Augmentation du `formation_count` NON supportée

**Exemple Cavern F1 A1:**
- Budget: 27 slots max
- Formations: 8 entrées max dans offset table
- Vos 3 formations: 7+8+7 = 22 slots ✓
- 5 fillers générés automatiquement (1 record chacun)

### 3. Extraction des slot_types (IMPORTANT)

Après modification, extraire les slot_types pour suffixes corrects:

```bash
cd Data/formations
python extract_slot_types.py
```

Ceci met à jour le JSON avec:
```json
"slot_types": [
  "00000000",  // Goblin
  "02000000",  // Shaman
  "00000a00"   // Bat
]
```

### 4. Build et test

```bash
cd Data/formations
python patch_formations.py

cd ../..
build_gameplay_patch.bat
```

Le patcher:
- Détecte automatiquement compositions custom vs vanilla
- Génère bytes synthétiques corrects pour customs
- Utilise bytes vanilla exacts pour compositions identiques
- Crée fillers synthétiques pour remplir le budget

## Utilisation de l'éditeur visuel

```bash
cd Data/formations
edit_formations.bat
```

Ouvre un éditeur HTML dans le navigateur pour:
- Visualiser toutes les formations d'une area
- Modifier les compositions avec boutons +/-
- Ajouter/supprimer des formations
- Sauvegarder les modifications dans le JSON

## Vérification

### Logs du patcher
```
[INFO] F00: CUSTOM composition, using SYNTHETIC bytes
[INFO] F01: using VANILLA bytes (3 records)
```

- `CUSTOM composition` - Bytes synthétiques générés
- `using VANILLA bytes` - Copie exacte vanilla

### Validation
Le patcher vérifie automatiquement:
- ✓ Slot indices valides (< nombre de monstres)
- ✓ Budget respecté
- ✓ Taille BLAZE.ALL multiple de 2048
- ✓ Offset table mise à jour

## Exemples

### Formation vanilla (reproduction exacte)
```json
{
  "total": 3,
  "slots": [0, 0, 0]  // Même composition que vanilla F0
}
```
→ Patcher utilise bytes vanilla (0 bytes différents)

### Formation custom
```json
{
  "total": 7,
  "slots": [0, 0, 0, 0, 0, 1, 1]  // Différent de vanilla
}
```
→ Patcher génère bytes synthétiques corrects

### Réduction du nombre de formations (8→3)
```json
{
  "formation_count": 8,  // Garde 8 pour offset table
  "formations": [
    {...},  // F0 custom
    {...},  // F1 custom
    {...}   // F2 custom
  ]
}
```
→ 5 fillers générés automatiquement (duplicate offsets)

## Dépannage

### Erreur: "slot X invalid"
Le slot_index dépasse le nombre de monstres dans l'area.
**Solution:** Vérifiez que tous les slots sont < len(monsters)

### Erreur: "exceeds maximum Y slots"
Trop de monstres dans vos formations.
**Solution:** Réduisez le nombre total de slots

### Erreur: "BLAZE.ALL size not multiple of 2048"
Problème d'alignement (normalement corrigé automatiquement).
**Solution:** Vérifiez que le patcher a réussi sans erreurs

### Shamans lancent FireBullet au lieu de Sleep
Formation corrompue ou bytes incorrects.
**Solution:**
1. Vérifiez que `extract_slot_types.py` a été exécuté
2. Vérifiez les slot_types dans le JSON
3. Rebuild complet

## Références

- **CUSTOM_FORMATIONS_WORKING.md** - Guide détaillé formations custom
- **FILLER_FIX.md** - Explication technique fillers synthétiques
- **Formation record format (32 bytes):**
  - byte[0:4] = prefix (type du slot précédent)
  - byte[4:8] = FFFFFFFF (marker début formation)
  - byte[8] = slot_index (0, 1, 2...)
  - byte[9] = 0xFF (formation marker)
  - byte[24:26] = area_id (ex: dc01)
  - byte[26:32] = FFFFFFFFFFFF (terminator)
  - suffix (4 bytes) = type du dernier slot

## Support

Pour des questions ou problèmes:
1. Vérifiez les logs du patcher
2. Lisez CUSTOM_FORMATIONS_WORKING.md
3. Testez avec formations vanilla d'abord
4. Comparez avec Cavern F1 A1 (exemple fonctionnel)
