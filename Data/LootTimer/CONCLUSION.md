# Loot Chest Timer - Conclusion Finale

## État : UNSOLVED - Investigation terminée

Date : 2026-02-11
Durée : 4 jours
Tentatives : 15
Succès : 0

---

## Résumé des 15 Tentatives

| Version | Approche | Emplacements | Résultat |
|---------|----------|--------------|----------|
| v1-v9 | NOP timer decrements | BLAZE overlays (divers) | ❌ Coffres 20s |
| v10 | NOP chest_update | BLAZE overlay (2) | ❌ Coffres 20s |
| v11 | Patch init entity+0x14 | BLAZE overlay (1) | ❌ Coffres 20s |
| v12 | Patch init entity+0x12 | BLAZE overlay (12) | ❌ Coffres 20s |
| v13 | Patch SLES tables | EXE (8), x65 | ⚠️ Dégâts x65 |
| v14 | Patch SLES tables | EXE (8), x2 | ⚠️ Dégâts x2, coffres 20s |
| v15 | Patch SLES sélectif | EXE (3), x2 | ❌ Coffres 20s |

---

## Ce qui a été découvert

### ✅ Architecture du système
- Timer à `entity+0x14` décremente toutes les 20 frames
- Timer RE-INIT depuis `entity+0x0012` (master timer)
- Fonction chest_update à RAM 0x80087624

### ✅ Locations éliminées
- 12 code immediates BLAZE.ALL (entity+0x0012 init) → patches chargés mais ineffectifs
- 8 tables SLES_008.45 → affectent dégâts ennemis, PAS coffres (confirmé v15)

### ❌ Location du timer : INCONNUE
Le vrai timer des coffres n'est dans AUCUN des emplacements identifiés.

---

## Pourquoi ça ne marche pas

### Théories finales (par ordre de probabilité)

**1. Table SLES non identifiée (60%)**
- Il existe d'autres tables avec 1000 dans SLES
- Mais pas trouvées par l'analyse savestate (heap/BSS uniquement)
- Nécessite désassemblage complet de l'EXE

**2. Calcul dynamique (30%)**
- Timer calculé au runtime (formule, pas constante)
- Exemple : `timer = base_value * difficulty_modifier`
- Impossible à patcher sans modifier le code de calcul

**3. Timestamp system (10%)**
- Pas un countdown mais une comparaison
- `if (global_time - spawn_time > 1000) despawn()`
- Faudrait patcher la COMPARAISON, pas la valeur

---

## Ce qui aurait pu marcher

### Option 1 : Runtime debugging ⭐
**Seule méthode viable pour résoudre définitivement**

Outils : PCSX-Redux, no$psx avec breakpoints

Procédure :
1. Breakpoint sur `sh $reg, 0x12($base)` (write entity+0x0012)
2. Identifier quelle fonction écrit la valeur 1000
3. Trouver d'où vient cette valeur (table, calcul, constante)
4. Patcher la VRAIE source

Avantage : Identification certaine
Inconvénient : Nécessite émulateur debug + compétences

### Option 2 : Désassemblage complet EXE
Analyser TOUT le code SLES pour trouver références à 1000 liées aux coffres.

Avantage : Exhaustif
Inconvénient : 843KB de code, semaines de travail

### Option 3 : Modification RAM runtime
Code injection dynamique pour hooker la fonction d'init.

Avantage : Contourne le problème de source inconnue
Inconvénient : Nécessite cheat engine ou hack RAM

---

## Décision : Accepter la limitation

### Raisons
1. **15 tentatives exhaustives** sur 4 jours sans succès
2. **Risques élevés** de dégâts collatéraux (v13 démontre)
3. **Temps/bénéfice** : 4 jours pour +20s de timer = pas rentable
4. **Alternatives fonctionnelles** : Tous les autres mods marchent

### Recommandation
**Considérer le timer des coffres comme UNFIXABLE sans runtime debugging.**

Le temps serait mieux investi sur :
- D'autres features gameplay
- Polish des mods existants
- Documentation pour futurs reverse engineers

---

## Fichiers conservés

### Documentation (à garder)
- `RESEARCH.md` - Historique complet v1-v15
- `FAILED_SUMMARY.md` - Résumé détaillé des échecs
- `CONCLUSION.md` - Ce document

### Scripts investigation (référence)
- `analyze_savestate_timer.py` - Analyse RAM
- `find_real_timer_init.py` - Cross-ref BLAZE/RAM
- `investigate_timer_offset.py` - Analyse code
- `search_data_tables.py` - Scan tables de données

### Patcher actif
- `patch_loot_timer.py` - No-op (désactivé, permet build)

### Configs
- `loot_timer.json` - Config inutilisée (référence)

---

## Message final

Après 15 tentatives sur 4 jours, incluant :
- Analyse statique (BLAZE.ALL, SLES_008.45)
- Analyse dynamique (savestates RAM)
- Tests progressifs (sélectif, modéré, exhaustif)

**Le timer des coffres résiste à toutes les approches de patching statique.**

La seule solution serait du **runtime debugging** avec émulateur debug, ce qui sort du scope d'un mod de balance gameplay.

**Investigation close : 2026-02-11**

---

*Pour référence future : Si quelqu'un avec PCSX-Redux veut reprendre, tous les outils et la doc sont prêts.*
