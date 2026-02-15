# Guide Complet: Ajouter des Monster Slots

## 📖 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture de la Solution](#architecture-de-la-solution)
3. [Guide d'Utilisation](#guide-dutilisation)
4. [Détails Techniques](#détails-techniques)
5. [Troubleshooting](#troubleshooting)

---

## Vue d'ensemble

### Problème Initial

Les areas du jeu ont un nombre fixe de monster slots (types de monstres disponibles):
- Cavern F1 A1: **3 slots** (Goblin, Shaman, Bat)
- Castle F1 A1: **5 slots** (Vampire-Bat, Vampire, Wolf, Lesser-Vampire, Living-Sword)

**Objectif:** Ajouter de nouveaux slots pour plus de variété.

### Contraintes Découvertes

Après analyse approfondie:

1. ❌ **Monster slot definitions sont PACKED TIGHT** - 0 bytes libres
2. ✅ **Zone_spawns area a 59% d'espace libre** (3200 bytes dans Cavern F1 A1)
3. ⚠️ **Script area utilisé à 99.8%** (1373/1376 bytes)

### Solution Retenue

**Zone Reorganization** - Déplacer script+formations vers la droite dans l'espace libre de zone_spawns

```
┌─────────────────────────────────────────────────────────────┐
│ AVANT                                                       │
├─────────────────────────────────────────────────────────────┤
│ [Anim+Stats: 412b]                                         │
│ [Script: 1376b] ←─── 99.8% utilisé                        │
│ [Formations: 896b]                                         │
│ [Zone_Spawns: 5416b] ←─── 2200b utilisés, 3200b LIBRES!  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ APRÈS (ajout de 2 slots = 240 bytes)                       │
├─────────────────────────────────────────────────────────────┤
│ [Anim+Stats: 652b] ←─── +240 bytes (5 slots au lieu de 3) │
│ [Script: 1376b] ───────→ DÉPLACÉ +240 bytes               │
│ [Formations: 896b] ────→ DÉPLACÉ +240 bytes               │
│ [Zone_Spawns: 5176b] ──→ DÉPLACÉ +240, RÉDUIT -240        │
│                          (garde 2960b libres)              │
└─────────────────────────────────────────────────────────────┘

✓ TOTAL INCHANGÉ - Reste du fichier à la MÊME position!
```

**Avantages:**
- ✅ Pas de décalage global du fichier
- ✅ Seulement 4 pointeurs à mettre à jour
- ✅ Utilise l'espace libre existant
- ✅ Préserve >2900 bytes libres dans zone_spawns

---

## Architecture de la Solution

### Fichiers Créés

```
Data/formations/
├── ADD_MONSTER_SLOTS_GUIDE.md          ← Ce guide
├── SLOT_EXPANSION_GUIDE.md             ← Analyse des approches
└── Scripts/
    ├── analyze_area_structure.py      ← Analyse de la structure
    ├── reorganize_add_slots.py         ← OUTIL PRINCIPAL ⭐
    ├── replace_monster_slot.py         ← Remplacement de slots
    ├── add_slots_safe.py               ← Tentative interne (failed)
    └── expand_monster_slots.py         ← Expansion naïve (risquée)
```

### Outil Principal: `reorganize_add_slots.py`

**Ce qu'il fait:**
1. Extrait les sections actuelles (anim, stats, script, formations, zone_spawns)
2. Crée des données placeholder pour 2 nouveaux slots
3. Reconstruit la zone avec nouveau layout (shift de 240 bytes)
4. Met à jour les 4 références hardcodées à `formation_start`
5. Sauvegarde le JSON avec nouveaux slots

**Sécurité:**
- ✅ Backup automatique de BLAZE.ALL
- ✅ Backup automatique du JSON
- ✅ Mode `--dry-run` pour vérifier avant d'appliquer
- ✅ Validation des offsets

---

## Guide d'Utilisation

### Prérequis

- Python 3.x installé
- BLAZE.ALL dans `output/BLAZE.ALL`
- Backup de votre ROM (au cas où!)

### Étape 1: Dry Run (Vérification)

```bash
cd Data/formations/Scripts
python reorganize_add_slots.py --dry-run
```

**Output attendu:**
```
[PLAN]
  Add 2 monster slots (120 bytes each = 240 bytes total)
  Shift script+formations+zone_spawns RIGHT by 240 bytes
  Reduce zone_spawns allocation by 240 bytes
  Update 4 offset references

[OFFSETS]
  Stats start:      0xF7A97C -> 0xF7A944
  Script start:     0xF7AA9C -> 0xF7AADC
  Formation start:  0xF7AFFC -> 0xF7B03C
  Zone_spawns start: 0xF7B37C -> 0xF7B3BC

[DRY RUN] Not applying changes
```

### Étape 2: Application

```bash
python reorganize_add_slots.py --apply
```

**Fichiers modifiés:**
- `output/BLAZE.ALL` - Zone reorganisée
- `output/BLAZE.ALL.backup` - Backup créé
- `Data/formations/cavern_of_death/floor_1_area_1.json` - Mis à jour
- `Data/formations/cavern_of_death/floor_1_area_1.json.backup` - Backup créé

### Étape 3: Test In-Game

1. Copier `output/BLAZE.ALL` dans votre émulateur/ISO
2. Charger une sauvegarde et aller à **Cavern of Death - Floor 1**
3. Vérifier que le jeu charge sans crash
4. Essayer de déclencher un combat

**Signes de succès:**
- ✅ Pas de crash au chargement de la zone
- ✅ Combats se déclenchent normalement
- ✅ Les 3 monstres originaux apparaissent correctement

**Signes de problème:**
- ❌ Crash au chargement de Cavern F1
- ❌ Écran vert/freeze
- ❌ Monstres manquants ou glitchés

**Si problème:** Restaurer le backup `BLAZE.ALL.backup`

### Étape 4: Personnaliser les Nouveaux Slots

Les nouveaux slots sont des **placeholders** (NewSlot1, NewSlot2). Pour les remplacer par de vrais monstres:

**Option A: Copier depuis une autre area**
```bash
python replace_monster_slot.py \
  --area cavern_f1_a1 \
  --replace-slot 3 \
  --with "Wolf" \
  --from castle_f1_a1 \
  --apply
```

**Option B: Éditer manuellement**
1. Utiliser un hex editor
2. Copier les données d'un monstre d'une autre area
3. Coller dans les slots 3-4 de Cavern

### Étape 5: Utiliser les Nouveaux Slots

Mettre à jour les formations pour utiliser les nouveaux slots:

```bash
cd Data/formations
start_editor.bat  # Ouvre l'éditeur web
```

Dans l'éditeur:
1. Sélectionner **Cavern of Death - Floor 1 Area 1**
2. Les nouveaux monstres apparaissent dans la liste (slots 3-4)
3. Créer/modifier des formations pour les utiliser
4. Sauvegarder et rebuilder le patch

---

## Détails Techniques

### Structure Mémoire

#### Zone Cavern F1 A1

**Boundaries:**
- Start: `0xF7A900` (Animation header)
- End: `0xF7B37C + 5416` (Fin de zone_spawns area)
- **Limite dure:** Tout après `0xF7B37C + 5416` ne doit PAS bouger!

#### Sections

| Section | Offset | Taille | Description |
|---------|--------|--------|-------------|
| Animation Header | 0xF7A900 | 8 bytes | `[00000000 04000000]` |
| Animation Table | 0xF7A908 | 8×N bytes | Frames d'animation par slot |
| Animation Records | Variable | 8×N bytes | Pointeurs animation + texture |
| Zero Terminator | Variable | Variable | Padding structurel |
| Assignments (L/R) | Variable | 8×N bytes | AI behavior indices |
| Stats | 0xF7A97C | 96×N bytes | Nom + stats de combat |
| Script Area | 0xF7AA9C | 1376 bytes | Bytecode de scripts |
| Formations | 0xF7AFFC | 896 bytes | Random battle data |
| Zone_Spawns | 0xF7B37C | 5416 bytes | Fixed spawn positions |

### Format des Monster Slots

Chaque slot = **120 bytes total:**

```
[Animation Table]    8 bytes  - Frame indices
[Animation Record]   8 bytes  - Anim offset (4b) + Texture ref (4b)
[L Entry]            4 bytes  - [slot, L_val, 00, 00]
[R Entry]            4 bytes  - [slot, R_val, 00, 40]
[Stats]             96 bytes  - Name (16b) + Stats (80b)
```

**Exemple (Goblin - Slot 0):**
```
Anim Table:   04 04 05 05 06 06 07 07
Anim Record:  0C 00 00 00 00 03 00 00
L Entry:      00 00 00 00  (L=0, AI behavior index)
R Entry:      00 02 00 40  (R=2, purpose unknown)
Stats:        "Lv20.Goblin" + level/hp/dmg/etc.
```

### Offsets Hardcodés

**Recherche dans BLAZE.ALL:**
```python
formation_start = 0xF7AFFC  # Offset cherché
references_found = [
    0x18920CB,  # Table de pointeurs zone 1
    0x1892133,  # Table de pointeurs zone 2
    0x189234B,  # Table de pointeurs zone 3
    0x18923B3,  # Table de pointeurs zone 4
]
```

**Ces 4 références sont mises à jour automatiquement** par `reorganize_add_slots.py`.

**Note:** `script_start` et `zone_spawns_start` n'apparaissent pas en hardcodé, probablement calculés dynamiquement.

### Reorganization Algorithm

```python
def reorganize_zone(data):
    # 1. Extract current sections
    anim_section = extract(0xF7A900, 124)
    stats_section = extract(0xF7A97C, 288)  # 3 slots
    script_section = extract(0xF7AA9C, 1376)
    formation_section = extract(0xF7AFFC, 896)
    zone_spawns_section = extract(0xF7B37C, 5416)

    # 2. Create new slots (2 × 120 bytes)
    new_slots = create_placeholder_slots(2)

    # 3. Expand animation section (+40 bytes)
    new_anim = expand_animation_table(anim_section, 2)

    # 4. Rebuild zone with shift
    new_zone = (
        new_anim +              # 164 bytes (was 124)
        stats_section +         # 288 bytes (unchanged)
        new_slots[stats] +      # 192 bytes (2 × 96)
        script_section +        # 1376 bytes (shifted +240)
        formation_section +     # 896 bytes (shifted +240)
        zone_spawns[:5176]      # 5176 bytes (shifted +240, reduced)
    )

    # 5. Write back to same location
    data[0xF7A900:0xF7A900+len(new_zone)] = new_zone

    return data
```

---

## Troubleshooting

### Problème: Crash au chargement de Cavern

**Symptômes:** Écran noir, freeze, ou retour au menu

**Causes possibles:**
1. Offsets mal mis à jour
2. Animation data corrompue
3. Zone_spawns trop réduite

**Solution:**
1. Restaurer `BLAZE.ALL.backup`
2. Vérifier que les 4 offsets ont été updatés:
   ```bash
   python -c "
   import struct
   with open('output/BLAZE.ALL', 'rb') as f:
       data = f.read()
       for loc in [0x18920CB, 0x1892133, 0x189234B, 0x18923B3]:
           offset = struct.unpack('<I', data[loc:loc+4])[0]
           print(f'0x{loc:X}: 0x{offset:X}')
   "
   ```
3. Doit afficher `0xF7B03C` (nouveau formation_start)

### Problème: Monstres manquants en combat

**Symptômes:** Combat se charge mais seulement 1-2 monstres apparaissent

**Cause:** Formations JSON pas mises à jour

**Solution:**
1. Ouvrir `Data/formations/cavern_of_death/floor_1_area_1.json`
2. Vérifier `"monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat", "NewSlot1", "NewSlot2"]`
3. Rebuilder le patch: `build_gameplay_patch.bat`

### Problème: NewSlot1/2 apparaissent bizarres

**Symptômes:** Monstres invisibles, glitchés, ou crashent au contact

**Cause:** Données placeholder incompatibles

**Solution:**
Remplacer les placeholders par de vrais monstres:
```bash
python replace_monster_slot.py --area cavern_f1_a1 --replace-slot 3 --with "Wolf" --from castle_f1_a1 --apply
python replace_monster_slot.py --area cavern_f1_a1 --replace-slot 4 --with "Troll" --from tower_area_1 --apply
```

### Problème: "Cannot shrink script area"

**Symptômes:** Error pendant reorganization

**Cause:** Script area trop utilisé pour être réduit

**Solution:** C'est normal! Le script n'est PAS réduit dans la version finale. Si vous voyez cette erreur, c'est que vous utilisez le mauvais script (`add_slots_safe.py` au lieu de `reorganize_add_slots.py`).

---

## Limitations

### Nombre Maximum de Slots

**Par area:** Théoriquement jusqu'à **22 slots** (d'après l'analyse)

**Pratique:** Recommandé **5-7 slots max**
- Au-delà, risque de manquer d'espace pour zone_spawns
- Complexité de gestion des formations augmente

### Areas Compatibles

**Actuellement supporté:**
- Cavern of Death - Floor 1 Area 1 (hardcodé dans l'outil)

**Pour d'autres areas:**
1. Analyser avec `analyze_area_structure.py`
2. Trouver les boundaries et offsets
3. Adapter `reorganize_add_slots.py` avec les nouveaux offsets
4. Chercher les références hardcodées spécifiques à l'area

### Données Copiables

**Depuis quelles areas copier des monstres:**
- Castle of Vamp: Wolf, Vampire, Living-Sword
- Tower: Shamans variants, Mages
- Forest: Slimes, Bears, etc.

**Compatibilité:** Tous les monstres PSX sont techniquement copiables, mais certains peuvent avoir des bugs (animations manquantes, textures incorrectes).

---

## Références

### Documentation Connexe

- `SLOT_EXPANSION_GUIDE.md` - Analyse des 3 approches
- `FORMATIONS_PATCHER_FIX.md` - Système de formations
- `WIP/level_design/docs/SPAWN_MODDING_RESEARCH.md` - Structure complète

### Outils Relatifs

- `zone_spawn_editor.html` - Éditeur visuel de spawns
- `patch_formations.py` - Patcher de formations
- `build_gameplay_patch.bat` - Build complet

### Commits Importants

- `76b8ff1` - Research initiale sur slot expansion
- `191fa2d` - Outil de reorganization finale

---

## FAQ

**Q: Puis-je ajouter plus de 2 slots?**
A: Oui, modifier `SHIFT = 240` dans `reorganize_add_slots.py` et `num_new_slots` dans `create_new_monster_slots()`. Attention à l'espace zone_spawns!

**Q: Ça marche sur d'autres areas?**
A: Oui mais nécessite adaptation des offsets. Chaque area a sa propre structure.

**Q: Que faire si je veux retirer des slots?**
A: Inverse du processus - shift LEFT, rendre l'espace à zone_spawns. Pas d'outil créé pour ça encore.

**Q: Les nouveaux slots persistent après save/load?**
A: Oui, modifications sont dans BLAZE.ALL qui est chargé au démarrage.

**Q: Puis-je distribuer le BLAZE.ALL modifié?**
A: Seulement comme patch (diff/IPS), pas le fichier complet (copyright).

---

**Dernière mise à jour:** 2026-02-15
**Version:** 1.0
**Auteur:** Ben + Claude Sonnet 4.5
