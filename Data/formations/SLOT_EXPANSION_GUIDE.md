# Guide: Ajouter des Monster Slots aux Areas

## 🎯 Objectif

Ajouter de nouveaux types de monstres aux areas pour plus de variété.

## 📊 Analyse Technique

### Espace Disponible

**Monster Slot Definitions:**
- Section: Assignments + Stats (120 bytes par slot)
- **Espace libre: 0 bytes** (packed tight!)
- Certaines areas ont même un espace NÉGATIF (overlap)

**Zone_Spawns Area:**
- Section: Positions x,y,z des monstres
- **Espace libre: 59% (3208 bytes dans Cavern F1 A1)**
- Peut stocker 100+ positions supplémentaires
- Mais utilise seulement les slots EXISTANTS

---

## 🛠️ Trois Approches Possibles

### Option 1: REMPLACEMENT de Slot ✅ RECOMMANDÉ

**Principe:** Remplacer un monstre existant par un autre (Wolf remplace Goblin)

**Avantages:**
- ✅ **100% SAFE** - Aucune modification de la structure
- ✅ Aucun offset cassé
- ✅ Taille de fichier inchangée
- ✅ Facile à tester

**Inconvénients:**
- ⚠️ Perd le monstre original (Goblin disparaît)
- ⚠️ Même nombre total de slots

**Outil:** `replace_monster_slot.py` (à finaliser)

**Exemple:**
```bash
python replace_monster_slot.py \
  --area cavern_f1_a1 \
  --replace-slot 0 \
  --with "Wolf" \
  --from castle_f1_a1 \
  --apply
```

**Résultat:**
- Cavern F1 A1: **Wolf**, Shaman, Bat (au lieu de Goblin, Shaman, Bat)

---

### Option 2: DÉPLACEMENT de Zone_Spawns ⚠️ MODÉRÉ

**Principe:** Déplacer zone_spawns +240 bytes, utiliser espace libéré pour nouveaux slots

**Avantages:**
- ✅ Ajoute vraiment de nouveaux slots (garde les anciens)
- ✅ Utilise l'espace libre de zone_spawns

**Risques:**
- ⚠️ **Insertion de bytes = décale tout le fichier**
- ⚠️ Casse TOUS les offsets hardcodés après l'insertion
- ⚠️ Nécessite de patcher LE CODE DU JEU
- ⚠️ Très difficile à débugger

**Outil:** `expand_monster_slots.py` (créé mais RISQUÉ)

**Problème critique:**
```
Fichier AVANT:  [Monster Slots][Script][Zone_Spawns][Autres Areas]...
Fichier APRÈS:  [Monster Slots][NOUVEAUX][Zone_Spawns déplacée][Autres Areas décalées]...
                                ^^^^^^^   ^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^
                                INSERT    MOVE                TOUS DÉCALÉS!
```

**Tous les pointeurs vers "Autres Areas" sont maintenant FAUX!**

---

### Option 3: RELOCATION à la Fin du Fichier 🔧 COMPLEXE

**Principe:** Mettre les nouveaux slots à la FIN de BLAZE.ALL, patcher le code pour les chercher là

**Avantages:**
- ✅ Pas d'insertion au milieu (offsets préservés)
- ✅ Vraiment de nouveaux slots

**Risques:**
- ⚠️ Nécessite de patcher le code assembleur du jeu
- ⚠️ Doit trouver où le code charge les monster slots
- ⚠️ Modifier la logique de chargement

**Étapes:**
1. Reverse engineer le code de chargement des monsters
2. Trouver les fonctions qui lisent assignments/stats
3. Modifier pour lire depuis deux locations (originale + extension)
4. Ajouter nouveaux slots à la fin du fichier
5. Patcher le code avec les nouveaux pointeurs

**Outil:** Nécessite analyse assembleur PSX (pas encore créé)

---

## 💡 Recommandation ACTUELLE

### Solution Immédiate: **Utiliser les Slots Existants**

Au lieu d'ajouter des slots, **utiliser l'espace zone_spawns disponible:**

**Cavern F1 A1:**
- 3 types de monstres: Goblin, Shaman, Bat
- Espace zone_spawns: 59% libre = **100 positions disponibles!**

**Créer de la variété avec 3 types:**
```json
Formation 1: 5 Goblins
Formation 2: 3 Shamans
Formation 3: 8 Bats
Formation 4: 2 Goblins + 3 Shamans
Formation 5: 1 Shaman + 5 Bats
Formation 6: 10 Bats (horde!)
etc.
```

**Avantages:**
- ✅ Utilise l'espace disponible (100 positions!)
- ✅ Aucun risque
- ✅ Fonctionne avec l'éditeur existant
- ✅ Peut créer des rencontres très variées

---

## 🚀 Solutions Futures

### Si Vraiment Besoin de Nouveaux Types

**Phase 1: Remplacement Simple**
1. Implémenter `replace_monster_slot.py` correctement
2. Tester en remplaçant Goblin par Wolf
3. Vérifier que ça fonctionne in-game

**Phase 2: Extension (si Phase 1 réussie)**
1. Reverse engineer le code de chargement des monsters
2. Identifier où les offsets sont hardcodés
3. Créer un système de "monster slot extensions" à la fin du fichier
4. Patcher le code pour supporter les extensions

**Phase 3: Outil Complet**
1. Interface pour choisir source/target
2. Auto-patch du code
3. Validation in-game automatique

---

## 📝 État Actuel

**Créé:**
- ✅ `analyze_area_structure.py` - Analyse complète des structures
- ✅ `expand_monster_slots.py` - Outil d'expansion (RISQUÉ, pas recommandé)
- ✅ `replace_monster_slot.py` - Outil de remplacement (à finaliser)
- ✅ `zone_spawn_editor.html` - Éditeur avec dropdowns

**À Faire:**
- [ ] Finaliser `replace_monster_slot.py` avec bons offsets
- [ ] Tester remplacement in-game
- [ ] Documenter quels monstres peuvent être copiés depuis quelles areas
- [ ] Créer une "monster database" avec tous les monstres disponibles

---

## 🎮 Utilisation Recommandée

**Pour l'instant:**
1. Utiliser `zone_spawn_editor.html` pour éditer les positions
2. Créer des formations variées avec les 3 types existants
3. Maximiser l'utilisation de l'espace libre (100 positions!)

**Plus tard:**
1. Tester le remplacement de slots (Wolf over Goblin)
2. Si ça marche, remplacer d'autres slots selon besoin
3. Conserver une "vanilla backup" pour chaque modification

---

## ⚠️ Avertissements

1. **NE PAS** utiliser `expand_monster_slots.py` sans comprendre les risques
2. **TOUJOURS** créer des backups avant toute modification binaire
3. **TESTER** in-game après chaque changement
4. **DOCUMENTER** tous les changements effectués

---

## 📚 Ressources

- `WIP/level_design/docs/SPAWN_MODDING_RESEARCH.md` - Structure complète des monsters
- `Data/formations/FORMATIONS_PATCHER_FIX.md` - Système de formations
- `memory/MEMORY.md` - Notes du projet

---

**Conclusion:** L'ajout de nouveaux slots est TECHNIQUEMENT POSSIBLE mais TRÈS RISQUÉ.
Le remplacement de slots est SAFE et suffisant pour la plupart des besoins.
