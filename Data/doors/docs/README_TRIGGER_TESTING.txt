================================================================================
  SYSTEME DE TEST DES TRIGGERS - IDENTIFICATION DES PORTES
================================================================================

OBJECTIF:
Identifier quels triggers dans LEVELS.DAT sont des portes en les desactivant
par groupes et en observant les changements en jeu.

================================================================================
  FICHIERS CREES
================================================================================

SCRIPTS:
  - test_triggers_system.py        Script principal de test
  - ../../apply_trigger_test.bat   Applique un test au BIN
  - ../../restore_original_levels.bat  Restaure l'original

DONNEES:
  trigger_tests/
    - triggers_database.json       500 triggers extraits
    - LEVELS_TEST_GROUP1.DAT       Groupe 1 (triggers 1-20 desactives)
    - LEVELS_TEST_GROUP2.DAT       Groupe 2 (triggers 21-40)
    - LEVELS_TEST_GROUP3.DAT       Groupe 3 (triggers 41-60)
    - LEVELS_TEST_GROUP4.DAT       Groupe 4 (triggers 61-80)
    - LEVELS_TEST_GROUP5.DAT       Groupe 5 (triggers 81-100)
    - test_groupN_notes.txt        Details de chaque groupe

DOCUMENTATION:
  - TRIGGER_TEST_GUIDE.md          Guide complet de test

================================================================================
  UTILISATION RAPIDE
================================================================================

ETAPE 1: Appliquer un test
  > cd C:\...\GameplayPatch
  > apply_trigger_test.bat 1

ETAPE 2: Tester en jeu
  - Lancer le jeu avec le BIN patche
  - Explorer Cavern of Death, Forest, Castle
  - Noter quelles PORTES ont disparu

ETAPE 3: Tester les autres groupes
  > apply_trigger_test.bat 2
  > apply_trigger_test.bat 3
  > etc.

ETAPE 4: Restaurer l'original
  > restore_original_levels.bat

================================================================================
  COMMANDES DISPONIBLES
================================================================================

# Voir les infos sur les triggers
py -3 test_triggers_system.py info

# Creer un patch de groupe (deja fait pour groupes 1-5)
py -3 test_triggers_system.py patch 3

# Desactiver un trigger specifique
py -3 test_triggers_system.py disable 42

# Appliquer un test au jeu
apply_trigger_test.bat 1

# Restaurer l'original
restore_original_levels.bat

================================================================================
  METHODOLOGIE
================================================================================

PHASE 1: Test par groupes (5 tests)
  1. Appliquer groupe 1: apply_trigger_test.bat 1
  2. Lancer le jeu
  3. Explorer les zones prioritaires
  4. Noter les portes affectees
  5. Repeter pour groupes 2-5

PHASE 2: Analyse des resultats
  - Comparer les groupes entre eux
  - Identifier les triggers de portes probables
  - Croiser avec les donnees BLAZE.ALL

PHASE 3: Tests individuels
  - Tester les triggers suspects individuellement
  - Confirmer qu'ils sont bien des portes
  - Documenter leur fonction exacte

================================================================================
  ZONES A TESTER EN PRIORITE
================================================================================

1. Cavern of Death - Floor 1 (debut du jeu, facile)
2. Forest of Despair (plusieurs portes visibles)
3. Castle of Vamp (chateau = beaucoup de portes)

Pour chaque groupe teste, verifier ces 3 zones d'abord.

================================================================================
  TEMPLATE DE NOTES
================================================================================

TEST GROUPE N
Date: [date]

ZONES TESTEES:
[ ] Cavern Floor 1
[ ] Forest
[ ] Castle

PORTES AFFECTEES:
- Porte [description] dans [zone]: DISPARUE / OK
- etc.

AUTRES EFFETS:
- [noter tout changement]

TRIGGERS PROBABLES:
- IDs: [liste]

================================================================================
  ETAT ACTUEL
================================================================================

[x] 500 triggers extraits
[x] 5 patches de groupe crees
[x] Scripts d'application crees
[x] Guide de test redige

[ ] Tests en jeu effectues
[ ] Triggers de portes identifies
[ ] Database mise a jour

================================================================================
  PROCHAINES ETAPES
================================================================================

1. Lire TRIGGER_TEST_GUIDE.md pour details complets
2. Appliquer test groupe 1: apply_trigger_test.bat 1
3. Tester en jeu
4. Noter les resultats
5. Repeter pour les autres groupes
6. Analyser et documenter

================================================================================

Pour plus d'informations: TRIGGER_TEST_GUIDE.md

================================================================================
