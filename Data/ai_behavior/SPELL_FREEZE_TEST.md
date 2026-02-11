# Spell Offset Freeze Test

## Vue d'ensemble

Ce test permet de vérifier si l'offset identifié (`BLAZE 0x0092BF74` / `RAM 0x800656CC`) s'exécute réellement pendant les combats dans Cavern of Death.

## Problématique

La recherche précédente a identifié cet offset comme le site d'initialisation du bitfield de sorts (entity+0x160), mais les tests précédents n'ont pas confirmé son exécution. Ce test **définitif** utilise une boucle infinie pour forcer un gel du jeu si le code s'exécute.

## Méthodes de test

### Méthode 1: Test rapide (recommandé)

```batch
test_spell_freeze.bat
```

Cette méthode :
1. Copie BLAZE.ALL propre
2. Applique le patch de freeze
3. Copie le BIN propre
4. Injecte BLAZE.ALL dans le BIN

**Avantage**: Rapide, minimal, pas d'autres patches appliqués.

### Méthode 2: Build complet avec test

```batch
REM Dans build_gameplay_patch.bat, modifier :
set TEST_SPELL_FREEZE=1

REM Puis lancer :
build_gameplay_patch.bat
```

Cette méthode applique tous les patches du gameplay PLUS le freeze test.

**Avantage**: Teste le système complet.
**Inconvénient**: Plus lent, mélange les patches.

## Procédure de test in-game

1. Charger `output/Blaze & Blade - Patched.bin` dans l'émulateur
2. Démarrer une nouvelle partie OU charger une sauvegarde
3. Aller à **Cavern of Death Floor 1**
4. Marcher jusqu'à déclencher un combat
5. Observer le comportement

## Résultats attendus

### ✅ Scénario A: Le jeu GÈLE au début du combat

**Signification**: L'offset `0x0092BF74` **S'EXÉCUTE** pendant l'initialisation du combat.

**Implications**:
- Le mapping BLAZE→RAM est correct pour cette zone
- L'offset identifié est le bon site d'init du bitfield
- **On peut implémenter le patch per-monster** en remplaçant le code à cet offset

**Prochaines étapes**:
1. Activer `patch_monster_spells.py` (actuellement désactivé)
2. Configurer `Data/ai_behavior/overlay_bitfield_config.json`
3. Tester avec différents bitfields par monstre
4. Documenter le système fonctionnel

### ❌ Scénario B: Le jeu fonctionne normalement (pas de gel)

**Signification**: L'offset `0x0092BF74` **NE S'EXÉCUTE PAS** pour Cavern F1.

**Implications**:
- Le code existe dans BLAZE.ALL mais appartient à un autre donjon
- OU le code est dead/unused pour cette zone spécifique
- OU l'overlay est chargé depuis une source différente

**Prochaines étapes**:
1. Chercher d'autres patterns dans le range overlay Cavern (0x00926000-0x00966000)
2. OU patcher l'EXE dispatch loop directement (approche universelle)
3. OU utiliser uniquement les stats de sorts (limitation acceptée)

## Code technique

Le patch remplace l'instruction d'init:
```mips
0x0092BF74: ori $v0, $zero, 0x0001   ; value = 1
```

Par une boucle infinie:
```mips
0x0092BF74: beq $zero, $zero, -1     ; infinite loop (0x1000FFFF)
```

## Historique

- **2026-02-10**: Recherche initiale, freeze tests v1-v3 échouent (offsets incorrects)
- **2026-02-11**: Pattern search trouve `0x0092BF78`, analyse révèle `0x0092BF74` comme site d'init
- **2026-02-11**: Création du freeze test v2 avec offset exact

## Fichiers

- `patch_spell_freeze_test.py` - Patcher BLAZE.ALL (appelé par build)
- `test_spell_freeze.bat` - Script de test rapide standalone
- `SPELL_FREEZE_TEST.md` - Cette documentation
- `overlay_bitfield_config.json` - Config pour le patch per-monster (si test réussit)
- `patch_monster_spells.py` - Patcher per-monster (actuellement désactivé)

## Notes

- Le freeze est **intentionnel** et **attendu** si le code s'exécute
- Ne pas confondre avec un bug - c'est un **test diagnostique**
- Toujours tester avec un BIN propre pour éviter les faux positifs
- Le test affecte UNIQUEMENT Cavern of Death (overlay spécifique)
