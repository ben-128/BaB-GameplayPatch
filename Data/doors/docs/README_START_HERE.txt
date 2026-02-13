================================================================================
  BLAZE & BLADE - BASE DE DONNEES DES PORTES
================================================================================

COMMENCEZ ICI!

================================================================================
  FICHIERS IMPORTANTS (dans l'ordre de lecture)
================================================================================

1. ANALYSE_COMPLETE.md         <- TOUT CE QUI A ETE FAIT (lisez en premier!)
2. EXPLORATION_GUIDE.md         <- Guide pour explorer le jeu
3. LISTE_PORTES_PAR_ZONE.txt    <- Liste complete en francais
4. SUMMARY.md                   <- Resume visuel
5. EXAMPLE_area_with_doors.json <- Format pour remplir les JSON

================================================================================
  CE QUI A ETE ANALYSE
================================================================================

Source: BLAZE.ALL (44.1 MB, fichier binaire du jeu)

DONNEES EXTRAITES:
  - 19 cles/amulettes identifiees
  - 7 types de portes definis
  - 335 references textuelles aux portes
  - 61 portes magiques (Magical Key)
  - 3 portes demoniaques (Demon Amulet)
  - 2 portes fantomes (Ghost Amulet)
  - 131 portes a cle specifique
  - 138 portes generiques/ouvertes

STRUCTURE CREEE:
  - 10 zones
  - 41 areas
  - 41 fichiers JSON (templates vides)
  - 6 fichiers de reference
  - 1 guide d'exploration complet

================================================================================
  ETAT ACTUEL
================================================================================

✓ Structure complete creee
✓ Types de portes catalogues
✓ Cles identifiees
✓ Statistiques globales extraites
✓ Guide d'exploration pret

✗ Portes specifiques par area (a faire via exploration in-game)
✗ Positions exactes (a noter en jouant)
✗ Destinations precises (a observer en jeu)

================================================================================
  PROCHAINES ETAPES
================================================================================

OPTION 1 (Recommandee): Exploration Manuelle
  1. Lire EXPLORATION_GUIDE.md
  2. Lancer le jeu
  3. Explorer chaque zone/area
  4. Noter les portes rencontrees
  5. Remplir les fichiers JSON

OPTION 2: Utiliser un emulateur avec debugger
  - DuckStation/PCSX-Redux
  - Memory watch
  - Breakpoints sur fonctions de portes

OPTION 3: Reverse engineering avance
  - Ghidra/IDA Pro
  - Disassembler les overlays
  - Extraire les tables de portes

================================================================================
  STRUCTURE DES FICHIERS
================================================================================

Data/doors/
  ├── ANALYSE_COMPLETE.md         (CE QUI A ETE FAIT)
  ├── EXPLORATION_GUIDE.md         (GUIDE D'EXPLORATION)
  ├── LISTE_PORTES_PAR_ZONE.txt    (LISTE COMPLETE)
  ├── SUMMARY.md                   (RESUME VISUEL)
  ├── README.md                    (DOC TECHNIQUE)
  │
  ├── zone_index.json              (Index zones/areas)
  ├── door_types_reference.json    (Types de portes)
  ├── keys_reference.json          (Liste des cles)
  ├── EXAMPLE_area_with_doors.json (Exemple rempli)
  │
  └── [zone]/                      (10 dossiers)
      └── [area].json              (41 fichiers a remplir)

================================================================================
  POURQUOI L'ANALYSE BINAIRE N'A PAS TOUT TROUVE
================================================================================

Les portes dans Blaze & Blade ne sont PAS stockees comme structures binaires
simples (x, y, z, type, key, etc.) dans BLAZE.ALL.

Raisons probables:
  - Scripts/events attaches au level geometry
  - Code dans les overlays charges dynamiquement
  - Triggers de zone (polygones invisibles)
  - Donnees compilees dans le code PS1

Les donnees TEXTUELLES (descriptions, types, cles) ont ete extraites avec
succes. Les positions et details precis necessitent l'exploration in-game.

================================================================================
  CONSULTER LES DONNEES
================================================================================

Voir tous les fichiers:
  - Ouvrir Data/doors/ dans l'explorateur

Lire le guide:
  - Data/doors/EXPLORATION_GUIDE.md

Voir un exemple:
  - Data/doors/EXAMPLE_area_with_doors.json

Voir les cles:
  - Data/doors/keys_reference.json

Voir les types:
  - Data/doors/door_types_reference.json

Lire le resume complet:
  - Data/doors/ANALYSE_COMPLETE.md  <-- COMMENCEZ ICI

================================================================================
  QUESTIONS FREQUENTES
================================================================================

Q: Pourquoi les fichiers JSON sont vides?
A: L'analyse binaire a produit trop de faux positifs. Les portes ne sont pas
   stockees comme structures simples. Il faut remplir manuellement via
   l'exploration in-game.

Q: Combien de portes y a-t-il dans le jeu?
A: Environ 335 references textuelles trouvees dans BLAZE.ALL. Le nombre exact
   par area doit etre determine en jouant.

Q: Quelles cles ouvrent quelles portes?
A: Les amulettes (Magical Key, Demon Amulet, Ghost Amulet) ouvrent leurs
   portes respectives. Pour les cles specifiques, il faut tester en jeu.

Q: Peut-on patcher les portes?
A: Potentiellement oui, mais il faut d'abord les localiser precisement dans
   BLAZE.ALL ou les overlays via reverse engineering.

================================================================================

Pour plus d'informations, lisez: ANALYSE_COMPLETE.md

================================================================================
