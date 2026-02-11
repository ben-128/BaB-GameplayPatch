# Loot Chest Timer - Résumé des Échecs

## État : UNSOLVED / DANGEROUS (2026-02-11)

Après **13 tentatives** sur 4 jours d'investigation, **aucune** n'a fonctionné. La tentative v13 a causé des **dégâts collatéraux graves**.

---

## Chronologie des Tentatives

### v1-v9 : NOP timer decrements (2026-02-10)
- **Approche** : NOP l'instruction `addiu $v0,$v0,-1` qui décremente le timer
- **Emplacements** : Divers (batch timer, overlay timer, handler stubs, etc.)
- **Résultat** : ❌ Coffres disparaissent toujours en 20s
- **Problème** : Code jamais appelé pour les coffres (Function A = dead code)

### v10 : NOP chest_update timer (2026-02-10)
- **Approche** : NOP le decrement dans chest_update (RAM 0x80087624)
- **Emplacements** : 2 patterns trouvés (BLAZE 0x0093FCB0, 0x0094E09C)
- **Résultat** : ❌ Coffres disparaissent toujours en 20s
- **Problème** : Inconnu - le code semble correct mais ineffectif

### v11 : Patch init entity+0x0014 (2026-02-11)
- **Approche** : Modifier la valeur INIT du timer (1000 → 150000)
- **Emplacements** : 1 pattern (BLAZE 0x01C216CC)
- **Recherche** : Seul endroit où 1000 est chargé puis stocké vers +0x14
- **Résultat** : ❌ Coffres disparaissent toujours en 20s
- **Problème** : Timer RE-INIT depuis entity+0x0012 après chaque decrement

### v12 : Patch init entity+0x0012 (master timer) (2026-02-11)
- **Approche** : Patcher le MASTER timer qui reinit entity+0x0014
- **Emplacements** : 12 patterns (un par overlay/donjon) dans BLAZE.ALL
- **Recherche** : Tous les endroits où 1000 est chargé puis stocké vers +0x0012
- **Config** : Lit depuis loot_timer.json (3000s → 0xFFFF)
- **Vérification** : Patches confirmés présents dans BIN final (2 copies LBA)
- **Résultat** : ❌ Coffres disparaissent TOUJOURS en 20s
- **Problème** : Patches chargés en RAM (vérifié par savestate), mais timer pas affecté

### v13 : Patch SLES_008.45 data tables — ⚠️ DANGEREUX (2026-02-11)
- **Approche** : Patcher les tables de données dans l'EXE principal
- **Découverte** : Savestate analysis révèle 8 occurrences de 1000 dans SLES_008.45
- **Emplacements** : 0x014594, 0x014858, 0x014860, 0x014BE4, 0x014BEC, 0x0154A0, 0x023D6C, 0x02CAE0
- **Cross-reference** : 8 offsets SLES matchent exactement 8 adresses RAM du savestate
- **Patch** : Change 1000 → 65535 dans les 8 tables SLES
- **Résultat** : ⚠️ **DÉGÂTS COLLATÉRAUX GRAVES**
  - Ennemis infligent des dégâts démentiels (~65535 au lieu de valeurs normales)
  - Les 8 tables ne sont PAS chest-specific (paramètres gameplay mixtes)
  - Combat devenu impossible, jeu injouable
- **Problème** : Les tables de 1000 sont multi-usage (coffres + dégâts + autres systèmes)
- **Action** : Patcher DÉSACTIVÉ immédiatement (`.bak`), rebuild nécessaire

---

## Observations Communes

### ✅ Ce qui fonctionne
- Build pipeline : tous les patches s'appliquent correctement
- BIN final : patches confirmés présents aux 2 emplacements LBA
- Jeu : démarre sans crash, les autres patches fonctionnent (monsters, spells, traps)
- Coffres : apparaissent normalement après kill monster

### ❌ Ce qui ne change jamais
- Timer : **EXACTEMENT 20 secondes**, jamais plus, jamais moins
- Comportement : identique avec 0, 1, ou 12 emplacements patchés
- Despawn : toujours au même moment, comme si non-patché

---

## Théories sur le Problème

### Théorie #1 : Overlay Reload System (★★★★★ très probable)

**Evidence :**
- Les patches de monsters/spells/traps fonctionnent car ils modifient des TABLES/DATA
- Nos patches modifient du CODE avec des immediates (`addiu $v0, $zero, 0x3E8`)
- Le moteur pourrait recharger le code overlay depuis le CD périodiquement
- Ou avoir un cache overlay qui ignore nos modifications

**Test possible :**
- Debugger runtime (PCSX-Redux) avec breakpoint sur `sh $v0, 0x12($base)`
- Vérifier si l'overlay patché est chargé en RAM
- Voir d'où vient VRAIMENT la valeur 1000

### Théorie #2 : Timer dans Table de Données (★★★★☆ probable)

**Evidence :**
- Les 12 emplacements patchés pourraient être du code mort
- Le vrai timer pourrait être chargé depuis une table :
  ```mips
  lui $v0, 0x800X
  lhu $v1, offset($v0)     ; load 1000 depuis table
  sh $v1, 0x12($s1)        ; init timer
  ```

**Test possible :**
- Scanner BLAZE.ALL pour séquences de halfwords contenant 1000
- Chercher dans les DATA sections (pas CODE)
- Patcher les tables au lieu des immediates

### Théorie #3 : Timestamp Absolu (★★★☆☆ possible)

**Evidence :**
- Au lieu de countdown, pourrait être timestamp :
  ```mips
  entity+0x12 = global_frame_counter    ; timestamp spawn
  if (global_frame_counter - entity+0x12 > 1000) despawn()
  ```
- Dans ce cas, patching 1000 dans l'init ne suffit pas
- Faut trouver la COMPARAISON et patcher la constante là

**Test possible :**
- Chercher `addiu $v0, $zero, 1000` suivi de comparaison (slt, bne, etc.)
- Ou chercher `global_frame_counter` loading pattern

### Théorie #4 : Vérification d'Intégrité (★★☆☆☆ peu probable)

**Evidence :**
- Le jeu pourrait vérifier CRC/checksum des overlays
- Recharger depuis copie "propre" si modifié

**Contre-evidence :**
- Les autres patches overlay fonctionnent
- Pas de comportement erratique ou crash

### Théorie #5 : Mauvais Code Patché (★☆☆☆☆ improbable)

**Evidence :**
- Les 12 emplacements seraient pour un autre type d'entité
- Les coffres monde utilisent un système différent

**Contre-evidence :**
- Le pattern `load 1000 + store +0x12` est très spécifique
- 12 occurrences = probablement per-dungeon (cohérent)
- Le code montre clairement la logique de REINIT depuis +0x12

---

## Prochaines Étapes Recommandées

### Option 1 : Runtime Debugging (RECOMMANDÉ ⭐)

**Outils :**
- PCSX-Redux avec debugger intégré
- Ou no$psx avec breakpoints

**Procédure :**
1. Lancer le jeu dans l'émulateur debugger
2. Aller dans un donjon, tuer un monstre
3. Breakpoint sur `sh $reg, 0x12($base)` (write to entity+0x0012)
4. Voir d'où vient la valeur 1000 (registre source, call stack)
5. Vérifier si l'overlay patché est en RAM ou si c'est un reload

**Avantage :** Verra EXACTEMENT ce qui se passe au runtime

### Option 2 : Chercher Tables de Constantes

**Procédure :**
1. Scanner BLAZE.ALL pour séquences de halfwords : `03 E8 XX XX YY YY ...`
2. Ignorer les CODE sections (instructions MIPS)
3. Chercher dans DATA/BSS regions des overlays
4. Patcher les tables au lieu des immediates

**Avantage :** Si le timer vient d'une table, ça marchera

### Option 3 : Chercher Timestamp Comparison

**Procédure :**
1. Chercher pattern : load global_counter, substract entity+0x12, compare avec 1000
2. Patcher la CONSTANTE de comparaison (1000 → valeur élevée)
3. Ou chercher `slti $reg, $reg, 1000` dans le code

**Avantage :** Si c'est un timestamp system, ça marchera

### Option 4 : Accepter la Limitation

**Considérations :**
- 12 tentatives sur 3+ jours
- Tous les angles explorés (decrement, init, master timer)
- Peut-être système trop enfoui/protégé
- Temps mieux investi sur d'autres features

**Alternatives :**
- Autres améliorations gameplay (already working: monster stats, spells, traps)
- Documenter l'échec comme référence pour futur reverse engineering

---

## Fichiers Créés

### Patchers (tous ineffectifs)
- `patch_loot_timer.py` - v12 actif (12 emplacements +0x0012)
- `patch_loot_timer_v11_old.py` - v11 (1 emplacement +0x0014)
- `patch_loot_timer_v10_old.py` - v10 (NOP decrement)

### Investigation
- `investigate_timer_offset.py` - analyse code (découverte RE-INIT +0x12)
- `RESEARCH.md` - historique complet v1-v12
- `FAILED_SUMMARY.md` - ce document

### Configuration
- `loot_timer.json` - config (actuellement: 3000s, mais ignoré)

---

## Conclusion

Le système de timer des coffres résiste à toutes les approches statiques (patching de binaire).
Une approche runtime (debugging, code injection dynamique) ou une investigation plus profonde
(tables de données, timestamp system) sera nécessaire pour résoudre ce problème.

**Recommandation :** Passer à Option 1 (runtime debugging) ou Option 4 (accepter limitation).
