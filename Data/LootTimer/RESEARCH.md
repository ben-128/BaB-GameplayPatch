# Loot Chest Despawn Timer - Research

## Objectif
Modifier la duree avant disparition des coffres laches par les monstres.
Duree originale : 20 secondes (1000 frames @ 50fps PAL).

## Statut : v12 - ECHEC (2026-02-11)

### Tentative v12 : Patcher entity+0x0012 (master timer)

**Decouverte** : Le timer a entity+0x0014 est CONSTAMMENT REINIT depuis entity+0x0012!

```mips
lhu $v0, 0x0014($s1)     ; load timer
addiu $v0, $v0, -1       ; decrement
sh $v0, 0x0014($s1)      ; store timer
...
lhu $v1, 0x0012($s1)     ; load MASTER timer
sh $v1, 0x0014($s1)      ; REINIT timer from master!
```

**12 emplacements d'init a entity+0x0012** (un par overlay/donjon) :
```
0x01BA5648, 0x01BA5780, 0x01BA5E48, 0x01BA5F80,
0x0257C018, 0x0257C1B4, 0x02B771D8, 0x02B77374,
0x02B78830, 0x02BC9B60, 0x02BC9CFC, 0x02BCBA84
```

Pattern : `addiu $v0, $zero, 0x3E8` / `sh $v0, 0x12($base)`

**Patch v12** : Change 0x3E8 (1000) en 0xFFFF (65535) pour les 12 emplacements
Config JSON : lit `chest_despawn_seconds` depuis loot_timer.json

**Resultat** : **ECHEC - Les coffres disparaissent TOUJOURS en 20s**

### Pourquoi v12 echoue - Nouvelles hypotheses

**Hypothese #1 : Overlay reload (la plus probable)**
- Les patches sont bien appliques dans output/BLAZE.ALL
- Mais le jeu charge les overlays depuis une AUTRE source
- Possibilites :
  - Cache overlay en RAM jamais rafraichi
  - Deuxieme copie de BLAZE.ALL dans le BIN (3eme emplacement LBA?)
  - Overlays comprimes/encodes ailleurs
  - CD loader qui charge depuis des offsets fixes ignores

**Hypothese #2 : Timer dans une table de donnees**
- Les 12 emplacements patches sont du code mort
- Le vrai timer est charge depuis une table :
  ```mips
  lui $v0, 0x800X
  lhu $v1, offset($v0)     ; load 1000 depuis table
  sh $v1, 0x12($s1)        ; init timer
  ```
- Besoin de chercher les tables de constantes dans les overlays

**Hypothese #3 : Timestamp absolu (pas countdown)**
- Le timer pourrait etre un TIMESTAMP de spawn :
  ```mips
  entity+0x12 = global_frame_counter  ; timestamp spawn
  if (global_frame_counter - entity+0x12 > 1000) despawn()
  ```
- Dans ce cas, patching 1000 ne suffit pas, faut trouver la COMPARAISON

**Hypothese #4 : Verification d'integrite**
- Le jeu pourrait verifier les overlays (CRC/checksum)
- Recharger depuis une copie "propre" si modifie

**Hypothese #5 : Mauvais overlays patches**
- Les 12 emplacements trouves sont pour un autre type d'entite
- Les coffres monde utilisent un systeme different
- Besoin de verifier avec savestate quel code est VRAIMENT execute

---

## v11 - ECHEC (2026-02-11)

### Tentative v11 : Modifier la valeur INIT du timer (pas le decrement)

**BLAZE 0x01C216CC : `addiu $v0, $zero, 0x3E8`** (charge 1000)
**BLAZE 0x01C216D0 : `sh $v0, 0x14($s2)`** (init timer a entity+0x14)

**Approche v11** : Au lieu de NOP le decrement (v1-v10), on change la valeur INIT
de 1000 (0x3E8) a 3000s (150000 = 0x249F0) avec config JSON.

**Resultat** : **ECHEC - Les coffres disparaissent toujours en 20s**

### Pourquoi v11 a echoue

**Hypothese #1 : Code mort (comme Function A dans v8)**
- L'init a 0x01C216CC n'est peut-etre jamais appele pour les coffres monde
- Ce pourrait etre du code pour un autre type d'entite utilisant +0x14
- Besoin de verifier les xrefs (qui appelle cette fonction?)

**Hypothese #2 : Plusieurs chemins d'init**
- Il pourrait y avoir d'autres endroits qui initent le timer
- La recherche (load 1000 + store +0x14) n'en trouve qu'UN seul
- Mais le timer pourrait etre init depuis une table/data section

**Hypothese #3 : Overlay reload**
- Meme probleme que v10 : l'overlay patche pourrait etre ecrase
- Le jeu pourrait charger l'overlay depuis BLAZE.ALL non-patche
- Ou depuis une autre source (cache, autre copie dans le BIN)

**Hypothese #4 : Timer pas a entity+0x14**
- Les savestates v10 montrent timer a entity+0x10 (PAS +0x14)
- entity+0x14 pourrait etre autre chose (sous-state, ref count)
- Besoin de re-verifier les offsets dans le code

**Hypothese #5 : Mecanisme de despawn different**
- Le timer 20s pourrait etre base sur un compteur global
- Ou un timestamp absolu (game_time - spawn_time > 1000)
- Au lieu d'un timer countdown entity+0x14

---

## v13 : Patch SLES_008.45 data tables — ECHEC DANGEREUX (2026-02-11)

### Tentative v13 : Patcher les tables dans l'EXE principal

**Découverte par savestate** : Les 105 occurrences de 1000 en RAM sont réparties :
- 23 dans l'EXE (SLES_008.45)
- 5 dans les overlays
- 77 dans heap/BSS (entités runtime)

**8 occurrences trouvées dans SLES_008.45** qui matchent la RAM :
```
0x014594, 0x014858, 0x014860, 0x014BE4, 0x014BEC, 0x0154A0, 0x023D6C, 0x02CAE0
```

**Patch v13** : Change les 8 occurrences de 1000 → 65535 dans SLES

**Résultat** : ❌ **DÉGÂTS COLLATÉRAUX GRAVES**
- Les ennemis infligent des dégâts démentiels (65535?)
- Les 8 tables patchées ne sont PAS toutes pour les coffres
- Elles contiennent des paramètres de gameplay divers (dégâts, HP, multiplicateurs?)

**Conclusion** : Patcher aveuglément TOUTES les occurrences de 1000 est **dangereux**.
Il faudrait identifier QUELLE table spécifique gère les coffres (impossible sans debugging runtime).

**Patcher désactivé** : `patch_loot_timer_v13_DANGEROUS.py.bak`

---

## v14-v15 : Tests avec valeurs moderees — ECHEC (2026-02-11)

### v14 : 8 offsets SLES avec x2 multiplier
- **Patch** : Les 8 offsets SLES (1000 → 2000)
- **Résultat** : Dégâts ennemis x2, **coffres 20s inchangés** ❌

### v15 : Patch sélectif par groupes
- **Approche** : Tester groupes d'offsets séparément pour isoler
- **Groupe A** : 0x014594, 0x014858, 0x014860 (3 offsets proches)
- **Patch** : 1000 → 2000 (x2 multiplier)
- **Résultat** : **Coffres 20s inchangés** ❌
- **Conclusion** : Les 8 offsets SLES ne contiennent PAS le timer des coffres

---

## Synthese finale v1-v15 (2026-02-11)

### 15 tentatives sur 4 jours, 0 succes

**Approches essayees :**
1. v1-v9 : NOP timer decrements (divers emplacements BLAZE) → ECHEC
2. v10 : NOP chest_update timer decrement (overlay) → ECHEC
3. v11 : Patch init entity+0x0014 (1 emplacement BLAZE) → ECHEC
4. v12 : Patch init entity+0x0012 (12 emplacements BLAZE) → ECHEC
5. v13 : Patch 8 tables SLES (EXE, x65 multiplier) → **ECHEC DANGEREUX**
6. v14 : Patch 8 tables SLES (EXE, x2 multiplier) → ECHEC (dégâts x2, coffres 20s)
7. v15 : Patch sélectif Groupe A (3 offsets SLES) → ECHEC (coffres 20s inchangés)

**Observations communes (v1-v15) :**
- Tous les patches confirmés présents dans le BIN final
- Le jeu démarre sans crash, les autres patches fonctionnent
- Les coffres apparaissent normalement
- **Mais disparaissent TOUJOURS exactement en 20 secondes**
- Les 8 offsets SLES affectent les dégâts ennemis (confirmé v13-v15)
- Mais NE contiennent PAS le timer des coffres (confirmé v15)

### Conclusion finale : Timer source inconnu

**Ce qui a été éliminé :**
- ❌ Code immediates dans BLAZE.ALL (v11-v12) : patches chargés mais ineffectifs
- ❌ Les 8 tables SLES identifiées (v13-v15) : affectent dégâts mais pas coffres
- ❌ NOP decrements overlay (v1-v10) : code mort ou rechargé

**Le timer des coffres est probablement :**
1. Dans une table SLES non identifiée (différente des 8 trouvées)
2. Calculé dynamiquement au runtime (pas de constante patchable)
3. Dans un mécanisme de timestamp (comparaison vs valeur globale)
4. Chargé depuis BSS/heap (non présent dans les fichiers)

**Sans runtime debugging impossible à résoudre.**

### Ancienne theorie : Overlay reload systeme

**Evidence :**
1. Le timing est EXACTEMENT 20s (jamais plus, jamais moins)
2. Meme avec 12 emplacements patches, comportement identique
3. Les autres patches overlays (monsters, spells, traps) fonctionnent
4. Mais ceux-la sont dans des TABLES/DATA, pas dans du CODE executable

**Hypothese :** Le moteur du jeu pourrait :
- Charger les overlays dans un buffer temporaire
- Les executer depuis RAM
- Puis les RECHARGER depuis le CD periodiquement
- Ou avoir un cache overlay qui ignore nos patches

### Pistes pour continuer

**Option 1 : Runtime debugging (RECOMMANDE)**
- PCSX-Redux avec debugger integre
- Breakpoint sur entity+0x0012 write
- Voir d'ou vient la valeur 1000 VRAIMENT
- Verifier si l'overlay patche est charge en RAM

**Option 2 : Chercher tables de constantes**
- Scanner BLAZE.ALL pour sequences de halfwords contenant 1000
- Pas dans le code, mais dans les DATA sections
- Patching tables au lieu de code immediat

**Option 3 : Chercher le timestamp system**
- Chercher comparaisons `global_counter - entity+0x12 > 1000`
- Au lieu de countdown, pourrait etre timestamp absolu
- Patching la constante de comparaison

**Option 4 : Accepter la limitation**
- Apres 12 tentatives sur 3+ jours
- Peut-etre que ce systeme est trop enfoui/protege
- Considerer d'autres ameliorations gameplay

---

## Investigation v11-v12 - Pourquoi les patches ne fonctionnent pas

### Pistes de debogage

**1. Verifier que le patch est bien applique dans le BIN final**
```bash
# Extraire BLAZE.ALL depuis le BIN patche
# Verifier offset 0x01C216CC = 0x24020000 | new_value (pas 0x240203E8)
```

**2. Chercher TOUS les stores vers entity+0x14 avec des valeurs immediates**
- Pas seulement 1000, mais aussi 50, 100, 500, etc.
- Le timer reel pourrait etre 50 (si decrement/frame) au lieu de 1000

**3. Verifier l'offset du timer dans les savestates (CRITIQUE)**
- v10 doc dit timer a entity+0x10 (PAS +0x14!) dans les savestates
- Contradiction avec le code qui lit/ecrit +0x14
- Besoin de re-verifier avec plusieurs savestates

**4. Chercher des comparaisons avec 1000 (au lieu de countdown a 0)**
```mips
lhu $v0, entity+0xNN
addiu $v1, $zero, 1000    ; ou 0x3E8
slt $v0, $v0, $v1         ; si timer > 1000 ?
```

**5. Chercher timestamp absolu (spawn_time + 1000 < game_time)**
- Le despawn pourrait etre base sur le temps global
- entity+0x14 = spawn_timestamp (word)
- Comparaison : `global_frame_counter - entity+0x14 > 1000`

**6. Disassembler la fonction qui contient 0x01C216CC**
- Identifier quelle fonction contient l'init patche
- Chercher les xrefs (qui appelle cette fonction)
- Verifier si elle est appelee pour les coffres ou autre chose

**7. Chercher "1000" dans les data sections (pas code)**
- Tables de config/params dans BLAZE.ALL
- Pourrait etre charge avec `lw` depuis une adresse fixe

---

## v10 - Timer decrement trouve mais NOP sans effet (2026-02-10)

### Le VRAI systeme de despawn coffre

**Le timer coffre est dans la fonction chest_update a RAM 0x80087624** (overlay principal,
handler index 41 dans la table d'entites monde a 0x8005A800).

Ce n'est PAS le dispatcher stubs (0x8006E044) ni Function A. C'est un **handler
d'entite monde** appele directement par le moteur chaque frame.

**Timer decrement** : `addiu $v0,$v0,-1` a **RAM 0x800877F4 = BLAZE 0x0094E09C**

```
chest_update (RAM 0x80087624, overlay principal Cavern F1):
    ...
    global_frame_counter = *(0x800A42E0)
    if global_frame_counter % 20 == 0:      // chaque 20eme frame
        timer = lhu entity+0x14             // load timer halfword
        timer -= 1                          // ← v10 NOP ICI
        sh timer, entity+0x14              // store timer
        if timer == 0:
            entity+0x00 |= 0x02000000      // set dead flag
    ...
```

**Pattern a 0x800877EC (BLAZE 0x0094E094) :**
```
96020014  lhu $v0, 0x14($s0)      load timer
00000000  nop
2442FFFF  addiu $v0,$v0,-1        ← CIBLE v10
A6020014  sh $v0, 0x14($s0)       store timer
00021400  sll $v0,$v0,16          check zero (halfword)
14400005  bne $v0,$zero, +0x14    skip si pas zero
3C030200  lui $v1, 0x0200         dead flag = 0x02000000
8E020000  lw $v0, 0x00($s0)       load entity flags
00000000  nop
00431025  or $v0,$v0,$v1          set dead flag
AE020000  sw $v0, 0x00($s0)       KILL entity
```

**Overlay est per-dungeon** : offset BLAZE 0x0094E09C = Cavern F1 uniquement.
Le patcheur v10 scanne tout BLAZE.ALL pour le pattern 16 bytes afin de couvrir tous les donjons.

### Pourquoi v1-v9 ne marchaient pas

| Version | Cible | Probleme |
|---------|-------|----------|
| v1-v8 | Function A (overlay, 0x800999D0) | Code mort : pas dans la table dispatcher |
| v9 | Handler [0] stubs (0x8006E3AC) | **Fausse piste** : c'est l'interpreteur bytecode d'ITEMS, pas le systeme coffre |

**Handler [0] a 0x8006E044** est un interpreteur de scripts bytecode pour les **items/equipement**
(slots a 0x800F0000). Il n'a RIEN a voir avec le timer de despawn des coffres monde.

Le vrai systeme coffre utilise les **entity update handlers** (table a 0x8005A800, index 41),
qui sont des fonctions de l'overlay principal appelees chaque frame par le moteur.

---

## Architecture complete des overlays

### Region NOP massive dans le SLES

Le SLES contient une **region NOP de 420 KB** : RAM 0x80056F64 - 0x800BD800.
Cette region est **vide dans le fichier SLES** (tout a zero) et remplie a
runtime depuis BLAZE.ALL par le CD loader.

Tous les stubs overlay connus sont dans cette region :
```
RAM 0x8006D61C  (stub inconnu)
RAM 0x8006E044  Entity Destroy/Handler dispatcher
RAM 0x800739D8  Play Animation
RAM 0x80073B2C  Set Anim State
RAM 0x80073F9C  Play Sound/VFX
RAM 0x80080000  Debut overlay principal (per-area)
```

### Mapping RAM → BLAZE.ALL (Cavern F1)

```
Formule STUBS  : BLAZE = (RAM - 0x80056F64) + 0x0091D80C
Formule MAIN   : BLAZE = (RAM - 0x80080000) + 0x009468A8

Exemples :
  RAM 0x8006E044 = BLAZE 0x009348EC  (stub dispatcher)
  RAM 0x80080000 = BLAZE 0x009468A8  (debut overlay principal)
  RAM 0x80099BD4 = BLAZE 0x0096047C  (Function A timer decrement)
```

### Deux regions de code overlay distinctes

1. **Region stubs** : BLAZE 0x009348EC - 0x009468A8 (73,660 bytes)
   - RAM 0x8006E044 - 0x80080000
   - Contient le **dispatcher** + les **handlers d'entites** (coffres, effets, etc.)
   - 56 self-decrements, dont **seulement 2** vrais timer halfword a +0x10
   - Table de 30 function pointers a 0x8005A458 (handler opcodes)
   - **Le patcheur v8 ne trouve AUCUN match ici** (0/31)

2. **Region principale** : BLAZE 0x009468A8+ (137,824 bytes)
   - RAM 0x80080000 - 0x800A1A5C
   - Per-area : meshes, textures, scripts, stats, Function A/B
   - 7+ copies dans BLAZE.ALL (une par groupe de donjon)
   - **Les 31 matches du patcheur v8 sont TOUS ici**

---

## Le dispatcher : stub 0x8006E044

### Architecture (BLAZE 0x009348EC, 488 bytes)

Le stub 0x8006E044 est un **dispatcher multi-handler** :

```
function entity_dispatch(entity, reason_code):
    entity_id = entity → calcul index
    handler_base = 0x800F0000 + (entity_id << 13)
    handler_slots = handler_base + 0x02B0    // 5 slots par entite

    for slot in 0..4:
        handler_type = byte_at(handler_slots + slot)
        if handler_type == 0: continue       // slot vide
        handler_data = computed_offset(handler_type)
        if handler_data+0x84 matches reason_code:
            sub_dispatch(handler_data)       // appel indirect via table
```

**Table de function pointers** a 0x8005A458 (en RAM overlay).
Chaque type d'handler (coffre, monstre, effet, etc.) a un index
qui pointe vers sa fonction handler specifique.

### Appels depuis le SLES

17 sites d'appel, tous gates par bit 23 de entity+0x00 :
```
lw $v0, entity+0x00
lui $v1, 0x0080
and $v0, $v0, $v1      ; test bit 23
beq $v0, $zero, skip    ; skip si pas set
jal 0x8006E044          ; appel dispatcher
```

Codes raison ($a1) : 0 (post-timers), 2,3,7,8,9,12,13,17,18,19,20 (combat)

---

## Fonctions handler dans la region stubs

### Function #3 : Fade-in animation (BLAZE 0x00940168, RAM 0x800798C0)

Handler d'**animation d'apparition**. Dure 16 frames puis s'auto-detruit.

```
State 0 : Init
  - Lit entity+0x12 (opacite initiale)
  - Set entity+0x28 (opacite), entity+0x2C
  - 3x jal 0x80039CB0 (RNG pour position)
  - Set entity+0x04 = 0x1D (type visuel)

State 1..15 : Animation
  - Interpolation opacite : opacity += (timer - opacity) >> 2
  - Calcul couleur : sin(state << 7) * 255 >> 12 → R=G=B → entity+0x38
  - Copie coords monde depuis config (+0x78)
  - jal 0x80023B58 (rendering)

State 16 : Kill
  - sw $zero, 0x0000($s0)  → KILL (zero le vtable ptr)
```

**Ce n'est PAS le coffre** — c'est l'entite d'animation visuelle du spawn.

### Function #4 : Coffre open + visual (BLAZE 0x009402B4, RAM 0x80079A0C)

Handler de **cycle de vie visuel du coffre**. Utilise le champ COLOR (+0x38),
PAS le timer (+0x14) comme mecanisme de despawn.

```
State 0 : Init
  - entity+0x0A = 7 (sous-etat visuel)
  - entity+0x28 = 0 (opacite)
  - entity+0x38 = 0 (couleur)
  - entity+0x2E = -20

State 1..31 : Fade-in
  - Opacite : si +0x28 < 4096, ajoute 0x01000100 (+256 par canal)
  - Couleur : si +0x38 <= 0x00D0D0CF, ajoute 0x00080808 (+8 par R/G/B)

State 32 : Ouverture
  - entity+0x12 = 0
  - entity+0x14 = 0x2000 (8192) — set MAIS JAMAIS DECREMENTE ici
  - jal 0x80073D48 (son ouverture coffre, ID 0x68)

State 33+ : Fade-out
  - Couleur -= 0x00080808 par frame (lui 0xFFF7 / ori 0xF7F8 / addu)
  - Opacite converge vers 0x2000 : opacity += (0x2000 - opacity) >> 2

Kill : quand state != 0 ET entity+0x38 == 0
  → sw $zero, 0x0000($s0)  (zero vtable ptr)
```

**Duree : ~63 frames (~1.3s)** — trop court pour etre le timer 20s.
entity+0x14 est set a 0x2000 mais n'est jamais lu/decremente dans cette fonction.

### Function #7 : Explosion/despawn (BLAZE 0x00945ADC, RAM 0x8007F234)

Effet d'**explosion au despawn**. 14 frames, genere 9 particules (3x3 boucle).

```
State 0 : Init explosion
  - entity+0x38 = 0x00F0F0F0 (blanc brillant)
  - entity+0x28 = 0x20004000 (grande opacite)
  - entity+0x14 = 0x2000
  - jal 0x80073F9C (son/VFX)

State 1..13 : Particules
  - entity+0x28 = 0x1FFC, entity+0x14 = 0
  - Boucle 3x3 : positions aleatoires, opacites aleatoires
  - jal 0x80073F9C + 0x80019D54 (sons)

State 14 : Kill
  - sw $zero, 0x0000($s0)
```

### Autres fonctions chest-related (stub region)

| # | BLAZE | RAM | Taille | Description |
|---|-------|-----|--------|-------------|
| 1 | 0x009356A4 | 0x8006EDFC | 11,532B | Handler geant (dispatcher secondaire?) |
| 2 | 0x0093CE90 | 0x800765E8 | 360B | Interpolation/fade generique |
| 5 | 0x00941A98 | 0x8007B1F0 | 284B | Effet fade/spin-out |
| 6 | 0x00944EB8 | 0x8007E610 | 484B | Setup + transition |

---

## Function A : State machine coffre — overlay principal

**BLAZE 0x00960278, RAM 0x800999D0** (Cavern F1)

La "vraie" state machine timer avec le countdown 1000→0 :

```
State 1 : Fade-in
  - +0x28 += 90/frame, +0x2A += 90/frame
  - Cap a 1000 (0x03E8)
  - Quand +0x28 >= 1001 → state = 2

State 2 : Countdown
  - +0x14 -= 1/frame               ← v8 PATCHE (NOP a BLAZE 0x0096047C)
  - Quand +0x14 < 0 → state = 3

State 3 : Fade-out
  - +0x28 -= 60/frame, +0x2A -= 60/frame
  - Quand +0x28 < 0 :
    - +0x28 = 0
    - +0x00 = +0x00 AND 0x7FFFFFFF  ← v8 PATCHE (NOP a BLAZE 0x009604E8)
    (clear bit 31 = flag "alive")
```

**Deux mecanismes de kill differents :**
- Function A (overlay principal) : `AND 0x7FFFFFFF` (clear bit 31)
- Stubs (region stubs) : `sw $zero` (zero le mot entier, clear TOUS les bits)

---

## Analyse savestate (2026-02-10) — PREUVE DEFINITIVE

### Setup savestates

Emulateur ePSXe, 4 savestates Cavern F1 :
- **Base** : pas de coffre visible
- **CoffreSolo** : 1 coffre visible
- **Coffre1** : coffre visible (1er moment)
- **Coffre2** : coffre visible (2eme moment)

Format ePSXe : fichier gzip, RAM a offset **0x1BA** dans les donnees decompressees.

### Timer coffre localise — offset +0x10 (PAS +0x14)

Recherche de valeur halfword 957 dans CoffreSolo → 5 copies identiques :

| Adresse RAM | Timer (hw) | State (hw) | Flags a -0x10 |
|-------------|-----------|------------|---------------|
| 0x800A93A0 | 957 | 1 | 0x80054698 |
| 0x800B4B9C | 957 | 1 | 0x80054698 |
| 0x800B4C38 | 957 | 1 | 0x80054698 |
| 0x800B507C | 957 | 1 | 0x80054698 |
| 0x800B5250 | 957 | 1 | 0x80054698 |

Verification multi-savestate :
| Savestate | 0x800A93A0 | 0x800B4B9C | 0x800B507C | Notes |
|-----------|-----------|-----------|-----------|-------|
| Base | 425 (autre) | 0 | 0 | Pas de coffre |
| CoffreSolo | 957 | 957 | 957 | 1 coffre, 5 copies |
| Coffre1 | 403 | 839 | 839 | 2 coffres, timers differents |
| Coffre2 | 403 | 839 | 403 | Timers en countdown |

### Structure record handler (stride 0x9C entre records 2 et 3)

```
record+0x00 : type descriptor ptr (0x80054698 quand vivant, 0 quand mort)
              bit 31 = alive flag
record+0x04 : 0x00000000
record+0x08 : 0x00000000
record+0x0C : data ptr (0x8014CDB8)
record+0x10 : TIMER (halfword low, countdown 1000→0)
              STATE (halfword high, =1 pendant countdown)
record+0x14 : sous-champ (PAS le timer contrairement a l'hypothese initiale)
record+0x18..0x24 : 0xA0000000 (position data)
record+0x28 : opacity/rendering
record+0x38 : color/state
```

### PREUVE : Function A n'est JAMAIS appelee

**Function A (RAM 0x800999D0) est chargee en RAM** (40/40 instructions verifiees,
match parfait avec BLAZE.ALL 0x00960278). L'instruction `addiu $v0,$v0,-1`
(0x2442FFFF) est bien presente a RAM 0x80099BD4.

**MAIS : la table de function pointers du dispatcher a 0x8005A458 :**
```
  [ 0] 0x8006E3AC  (BLAZE 0x00934C54) ← HANDLER TIMER (probability-gated -1 to +0x10)
  [ 1] 0x8006E4FC  (BLAZE 0x00934DA4)   Helper: lbu+sll+or→return offset
  [ 2] 0x8006E518  (BLAZE 0x00934DC0)   Helper: lw check + sw zero kill
  [ 3] 0x8006E55C  (BLAZE 0x00934E04)   Helper: jal 0x8001A3D4
  ...
  [18] 0x8006EBA0  (BLAZE 0x00935448)   Jump table dispatch (22 cases)
  [19] 0x8006EC3C  (BLAZE 0x009354E4)   Play Animation (lbu size switch)
  [20] 0x8006ECEC  (BLAZE 0x00935594)   Play Animation (lbu size switch)
  [21] 0x8006EDA0  (BLAZE 0x00935648)   Play Sound (jal 0x80019ADC)
  [22] 0x80061AE8  ...
  ...
  [29] 0x80061C3C
```

**Function A (0x800999D0) N'EST PAS dans la table (30 entrees verifiees).**
Le dispatcher 0x8006E044 ne peut pas l'appeler.
→ Les 31 patches v8 sont tous dans du **code mort** pour les coffres.

### Desassemblage handlers [18]-[21] — NE SONT PAS des timers (FAUSSE PISTE)

**ERREUR de l'analyse precedente** : les handlers [18]-[21] etaient supposes
avoir des timer decrements. Le desassemblage complet montre :

- **[18]** : Jump table dispatch (22 entries via `jr $v0`), appel indirect via
  table a 0x800A17FC. NOP/jal, PAS de timer decrement.
- **[19]** : Play Animation helper — lit 1/2/4 bytes selon state, appelle
  jal 0x800739D8 (overlay Play Animation). 44 bytes.
- **[20]** : Play Animation helper — identique a [19] mais avec `lw $a0, 0x0070($a0)`.
  44 bytes, appelle jal 0x800739D8.
- **[21]** : Play Sound helper — assemble params depuis bytecode, appelle
  jal 0x80019ADC. 32 bytes. Aucun timer.

**Aucun de ces 4 handlers ne contient de decrement timer.** Leur taille est
de 32-96 bytes chacun (pas assez pour une state machine).

### Handler [0] : LE countdown timer (BLAZE 0x00934C54, RAM 0x8006E3AC)

**C'est la seule fonction de la table qui decremente un halfword timer.**

```
function handler_0(entity_block, handler_data, bytecode_ptr):
    $s0 = entity_block
    $s1 = handler_data          // pointe vers le record
    $s2 = bytecode_ptr          // pointe vers les params

    rng = jal 0x80039CB0()      // random number
    chance = rng % 100           // modulo 100
    threshold = lbu $s2+1        // probabilite depuis bytecode

    if chance >= threshold:
        return $s2+2             // skip, avance bytecode de 2

    // Decrement timer:
    timer = lhu $s1+0x10         // load timer (halfword)
    timer -= 1
    sh timer, $s1+0x10           // store timer
    if timer != 0:
        return $s2+2             // continue

    // Timer atteint 0 → KILL :
    sb $zero, $s1+0x00           // clear handler type byte
    // Loop: iterate entity+0x2B0 handler slots (5 slots, 10 candidates)
    // Mark matching slots as 0xFF
    return $s2+2
```

**Cible v9 : NOP `addiu $v0,$v0,-1` a BLAZE 0x00934CC8 (RAM 0x8006E420)**

**Attention** : Handler [0] est generique — utilise par TOUS les types d'entite
qui ont handler_type=0 (pas seulement les coffres). Le NOP gelerait TOUS les
timers handler_type=0. Il faudra tester si ca cause des effets secondaires.

### Giant Function #1 : second timer decrement — handler de MORT (pas countdown)

**BLAZE 0x00939D58, RAM 0x800734B0** dans le Giant Function (0x8006EDFC, 11,532B) :

```
// Avant le decrement :
lw $v0, 0x0000($s0)
lui $v1, 0x7FFF
ori $v1, 0xFFFF
and $v0, $v0, $v1          // clear bit 31 (marque entite comme MORTE)
sw $v0, 0x0000($s0)

// Decrement timer mort :
lhu $v0, 0x0010($s0)
addiu $v0, $v0, -1
sh $v0, 0x0010($s0)
if timer != 0: continue     // animation de mort en cours
// timer = 0 → nettoyage final
```

**Ce n'est PAS le countdown coffre** : il clear bit 31 AVANT de decrementer.
Or dans les savestates, les coffres vivants ont bit 31 SET (0x80054698).
C'est le handler d'animation de mort APRES que le timer countdown a atteint 0.

### H2 ELIMINEE — les 3 decrements +0x14 stubs sont des compteurs debris

Les 3 patterns a BLAZE 0x0093FCB0/0x0093FD68/0x0093FE54 sont dans une SEULE
fonction de handler debris/fragments. Ils decrementent **parent+0x14** (via
$v1 = $s2+0x6C = parent pointer), PAS le timer coffre direct.

### Inventaire COMPLET des self-decrements stubs (56 total)

| Type | Nombre | Description |
|------|--------|-------------|
| Timer halfword +0x10 | **2** | Handler[0] (countdown) + Giant func (mort) |
| Timer halfword +0x14 via parent | 3 | Debris (parent ref count) |
| Timer halfword +0x16 via parent | 2 | Debris (companion counter) |
| Byte counters (+0x0A, +0x0C, +0x0E, +0x27, +0x206, +0x207) | 8 | Anim/state bytes |
| Global counters (0x800A4010, 0x80057964) | 2 | Systeme |
| Loop counters (bne-based) | 39 | Iteration, pas des timers |

---

## Pourquoi v8 ne fonctionne pas — Synthese

### CAUSE RACINE CONFIRMEE : Function A jamais appelee

1. Les 31 patches v8 sont TOUS dans l'overlay principal (0x009468A8+)
2. 0 patches dans la region stubs (0x009348EC-0x009468A8)
3. Function A (overlay principal) contient une state machine timer 1000→0
4. **MAIS** : la table de function pointers du dispatcher (0x8005A458)
   ne contient QUE des fonctions stubs (30 entrees, toutes en 0x8006xxxx/0x80061xxx)
5. Function A **n'est JAMAIS appelee** pour les entites coffre
6. → Les patches v8 ciblent du code mort

### Hypotheses historiques — toutes resolues

| Hypothese | Statut | Raison |
|-----------|--------|--------|
| H1 : Function A pas appelee | **CONFIRMEE** | Table dispatcher ne la contient pas (30 entries verifiees) |
| H2 : Timer dans les 3 decrements +0x14 stubs | **ELIMINEE** | Ce sont des compteurs debris parent+0x14 (via $s2+0x6C) |
| H3 : Handlers [20]/[21] contiennent le timer | **ELIMINEE** | Ce sont des helpers Play Animation / Play Sound (44/32 bytes) |
| H4 : Overlay recharge apres patches | Non pertinente | Cause racine trouvee |
| H5 : Timer a +0x14 | **CORRIGEE** | Timer est a **+0x10** (confirme par code ET savestate) |

### Cible v9 identifiee

**Handler [0]** (BLAZE 0x00934C54, RAM 0x8006E3AC) :
- Seul handler dans la table du dispatcher avec un decrement halfword timer
- Decremente `record+0x10` (probability-gated par bytecode)
- Quand timer atteint 0 → kill entity (sb $zero, record+0x00)
- **NOP a BLAZE 0x00934CC8** = geler le timer

**Risque** : Handler [0] est generique, utilise par d'autres types d'entites.
Le NOP gelerait TOUS les timers handler_type=0, pas seulement les coffres.
A tester in-game pour evaluer les effets secondaires.

---

## Historique des tentatives

### v1 : batch timer seul (entity+0x80)
- Patch : NOP `addiu $v0,$v0,-1` a 0x80027680 (boucle 48 timers)
- Resultat : 48 timers geles, **coffres disparaissent toujours**
- Conclusion : les 48 timers ne controlent pas le despawn des coffres

### v2 : batch timer + entity+0x4C
- Patch : NOP stores vers entity+0x4C
- Resultat : combat casse (monstres immortels), **coffres disparaissent toujours**
- Conclusion : entity+0x4C = HP combat, pas timer coffre

### v3-v7 : overlay timer region 0x80080000+
- v3 : 7 patterns (registre $s1 seul) → insuffisant
- v4 : 35 patterns (tous registres) → v5 montre qu'il manquait des variants
- v5 : 68 patterns (detection generique addiu-1) → trop de faux positifs (35 = spells)
- v6 : 35 vrais patterns mais cassait les sorts (timer animation spell patche)
- v7 : filtre par opacite (forward only), 12 patterns → manque Function B
- Toutes ces versions : **coffres disparaissent toujours en 20s**

### v8 : bidirectional opacity scan + kill NOP — SANS EFFET
- 31 timer decrements NOPes (scan bidirectionnel pour opacite +0x28/+0x2A)
- 11 kill instructions NOPes (sw entity+0x00 apres AND 0x7FFFFFFF)
- Patches confirmes presents dans BIN final (2 copies LBA)
- **Coffres disparaissent toujours en 20s**
- **CAUSE** : les 31 patches ciblent Function A (overlay principal, 0x800999D0)
  qui n'est JAMAIS appelee par le dispatcher (table a 0x8005A458 = stubs uniquement).

### v9 : Handler [0] stub region — SANS EFFET
- NOP `addiu $v0,$v0,-1` a BLAZE 0x00934CC8 (RAM 0x8006E420)
- Handler [0] = entry [0] dans la table dispatcher (0x8005A458)
- Seul handler de la table avec un decrement halfword timer a +0x10
- **Coffres disparaissent toujours**
- **CAUSE** : Handler [0] est l'interpreteur bytecode d'ITEMS (equipment slots 0x800Fxxxx),
  PAS le systeme coffre monde. La table a 0x8005A458 gere les items, pas les entites monde.

### v10 : chest_update overlay — SANS EFFET
- NOP `addiu $v0,$v0,-1` a BLAZE 0x0094E09C (RAM 0x800877F4, Cavern F1)
- Fonction chest_update (RAM 0x80087624, entity handler index 41)
- Timer a entity+0x14 (halfword), decremente chaque 20eme frame
- Pattern scan : 2 matches (1 chest + 1 debris), NOP confirme dans BIN final
- **Coffres disparaissent toujours en 20s**
- **CAUSE inconnue** : le code est correct (confirme par savestate), le NOP est dans le BIN,
  mais le timer continue de decrementer. Possible : overlay rechargee depuis une autre source,
  ou un second chemin de code non identifie

### v11 : Modification de la valeur INIT — ECHEC (2026-02-11)
- Approche differente : au lieu de NOP le decrement, **modifier la valeur d'initialisation**
- Recherche globale de la constante 1000 (0x3E8) dans BLAZE.ALL : 77 occurrences
- Recherche de `addiu $reg, $zero, 0x3E8` suivi de `sh $reg, 0x14($base)` : **1 SEUL match**
- **BLAZE 0x01C216CC** : `addiu $v0, $zero, 0x3E8` (charge 1000)
- **BLAZE 0x01C216D0** : `sh $v0, 0x14($s2)` (init timer a entity+0x14)
- **Patch** : change 0x3E8 (1000) en 0x249F0 (150000) = 3000 secondes (50 minutes)
- Config JSON : `chest_despawn_seconds: 3000` (lit depuis loot_timer.json)
- **ECHEC : Coffres disparaissent toujours en 20s**
- **Conclusion** : Le timer a +0x14 est REINIT depuis +0x0012 dans la meme fonction

### v12 : Patch entity+0x0012 (master timer) — ECHEC (2026-02-11)
- Investigation du code : le timer a +0x14 est **REINIT depuis +0x12**
- Recherche de `addiu $v0, $zero, 0x3E8` suivi de `sh $v0, 0x12($base)` : **12 matches**
- **12 emplacements** (un par overlay/donjon) :
  - 0x01BA5648, 0x01BA5780, 0x01BA5E48, 0x01BA5F80
  - 0x0257C018, 0x0257C1B4, 0x02B771D8, 0x02B77374
  - 0x02B78830, 0x02BC9B60, 0x02BC9CFC, 0x02BCBA84
- **Patch** : change 0x3E8 (1000) en 0xFFFF (65535) pour les 12 emplacements
- Config JSON : `chest_despawn_seconds: 3000` → 0xFFFF (65535 = ~22 minutes)
- Patch confirme present dans output/BLAZE.ALL et BIN final (2 copies LBA)
- **ECHEC : Coffres disparaissent toujours en 20s**
- **Conclusion** : Overlay reload, timer depuis table, ou mauvais code patche

---

## Verification build pipeline (2026-02-10)

### Ordre de build confirme correct
1. BLAZE.ALL clean copie vers output/ (step 1)
2. Patches prix/items/stats/formations (steps 2-6b)
3. **Loot timer patch** applique sur output/BLAZE.ALL (step 7)
4. Patches spells/AI/traps (steps 7b-7e)
5. BIN clean copie vers output/ (step 8)
6. BLAZE.ALL patche injecte dans BIN (step 9, 2 emplacements LBA)

### Patches confirmes dans les fichiers finaux
```
BLAZE.ALL 0x0096047C (Function A timer) : 0x00000000 = NOP confirmed
BLAZE.ALL 0x009604E8 (Function A kill)  : 0x00000000 = NOP confirmed
BLAZE.ALL 0x00960238 (Function B timer) : 0x00000000 = NOP confirmed
BIN LBA 163167 copy : NOP confirmed
BIN LBA 185765 copy : NOP confirmed
```

---

## Entity struct (champs confirmes)

```
+0x00 : flags word
         bit 23 (0x00800000) = overlay-managed entity
         bit 30 (0x40000000) = dead/inactive flag
         bit 31 (0x80000000) = alive (Function A kill = clear bit 31)
+0x04 : type byte (0x1D = coffre visual)
+0x0A : sub-state byte
+0x10 : TIMER halfword (Handler[0]: countdown 1000→0, confirme par savestate)
+0x12 : STATE halfword (=1 pendant countdown actif)
+0x14 : sous-champ (Function #4: set 0x2000, debris: parent ref count)
+0x28 : opacity word (2 halfwords packed)
+0x2A : opacity channel 2
+0x2C : opacity channel 3
+0x2E : rotation/offset param
+0x38 : color word (R/G/B packed, Function #4 kill quand == 0)
+0x40 : data flags word (entity + 0x100 offset)
+0x4C : HP halfword (combat)
+0x4E : HP2 halfword (combat)
+0x78 : config data pointer (vers region overlay)
+0x80..0xDF : 48 halfword timers (boucle SLES)
+0xE0 : counter halfword
+0xE2 : counter2 halfword
+0x2B0+ : handler type slots (5 bytes, utilises par dispatcher 0x8006E044)
```

---

## Donnees techniques

- Jeu : Blaze & Blade: Eternal Quest (Europe) PAL
- SLES_008.45 : 843,776 bytes, load_addr=0x80010000, code_size=0x000CD800
- BLAZE.ALL : 46,206,976 bytes
- Region NOP SLES : 0x80056F64-0x800BD800 (420 KB, remplie a runtime)
- Framerate : 50fps (PAL)
- Timer original : ~1000 ticks (1 tick / 20 frames = 400s a 50fps? a verifier)
- Timer patche v10 : NOP addiu a BLAZE 0x0094E09C → SANS EFFET

## Scripts

- `patch_loot_timer.py` : patcheur v12 (patche entity+0x0012 master timer, 12 emplacements)
- `patch_loot_timer_v11_old.py` : v11 (patche entity+0x0014, 1 emplacement, NE FONCTIONNE PAS)
- `patch_loot_timer_v10_old.py` : v10 (NOP decrement, NE FONCTIONNE PAS)
- `investigate_timer_offset.py` : script d'analyse du code (verifie offsets +0x10/+0x12/+0x14)
