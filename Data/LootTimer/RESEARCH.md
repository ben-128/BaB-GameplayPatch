# Loot Chest Despawn Timer - Research

## Objectif
Modifier la duree avant disparition des coffres laches par les monstres.
Duree originale : 20 secondes (1000 frames @ 50fps PAL).

## Statut : RESOLU (v2 - deux patches)

Le code de decrement du timer coffre est dans le **SLES executable** (pas BLAZE.ALL).
La fonction entity update a **deux mecanismes de timer independants** :

1. **Batch timer** a entity+0x80 (48 halfword timers en boucle)
2. **Despawn timer** a entity+0x4C (countdown separe qui declenche la suppression)

Les deux sont patches (NOP) pour empecher la disparition des coffres.

---

## Solution finale

### Mecanisme #1 : Batch timer (entity+0x80)
48 timers halfword en boucle, decremente un par un :

```
SLES 0x17668: lhu  $v0, 0($a1)     ; load timer (entity+0x80+i*2)
SLES 0x1766C: nop
SLES 0x17670: beq  $v0,$zero,skip  ; if 0, skip
SLES 0x17678: lhu  $v0, 0($a1)     ; reload
SLES 0x1767C: nop
SLES 0x17680: addiu $v0,$v0,-1     ; DECREMENT ← PATCH #1 (NOP)
SLES 0x17684: sh   $v0, 0($a1)     ; store timer
```

Ou `$a1 = entity_base($s0) + 0x80` (addiu $a1,$s0,128 a 0x17654).

### Mecanisme #2 : Despawn timer (entity+0x4C) — LE VRAI DECLENCHEUR
C'est ce timer qui controle reellement la disparition :

```
SLES 0x175E4: subu $v0,$v0,$a0     ; path A: subtract computed value
SLES 0x175E8: addiu $v0,$v0,-1     ; path B: subtract 1
SLES 0x175EC: sh   $v0, 0x4C($s0)  ; STORE ← PATCH #2 (NOP)
...
SLES 0x17794: bgtz $v0, +10        ; quand +0x4C <= 0...
SLES 0x177A8: or   $v0,$v0,$v1     ; set bit 30 in flags = KILL ENTITY
```

Quand entity+0x4C atteint 0, le bit 30 de entity+0x40 est active = despawn.

### Les deux patches
**Patch #1** (batch timer) :
- `addiu $v0,$v0,-1` → `nop`
- Signature : `94A20000 00000000 2442FFFF A4A20000`
- BIN offset : 0x295FBDE8

**Patch #2** (despawn timer — CRITIQUE) :
- `sh $v0, 0x004C($s0)` → `nop`
- Signature : `08009B7B 00441023 2442FFFF A602004C`
- BIN offset : 0x295FBD54

**Note** : la v1 (patch #1 seul) ne suffisait PAS — les coffres disparaissaient
toujours apres 20s car le vrai declencheur est entity+0x4C, pas entity+0x80.

### Build
Le patch est applique au step 9b dans `build_gameplay_patch.bat`, apres
injection de BLAZE.ALL dans le BIN (step 9), car il modifie le SLES
directement dans le BIN.

---

## Pourquoi les 6 tentatives precedentes ont echoue

### Root cause : mauvais fichier + mauvais offset
1. **Mauvais fichier** : toutes les tentatives patchaient BLAZE.ALL, mais le code
   timer est dans le SLES executable. Le SLES n'est PAS un overlay - il fait
   partie de l'executable principal charge a 0x80010000.

2. **Mauvais offset de champ** : les recherches ciblaient `sh $reg, 0x0014($base)`
   ou `sh $reg, 0x0012($base)`, mais le vrai code utilise `sh $v0, 0x0000($a1)`
   ou `$a1` est un pointeur PRE-CALCULE vers `entity + 0x80`.

3. **Region 0x009xxxxx = dead data** : les instructions dans BLAZE.ALL a 0x009xxxxx
   ne sont jamais chargees par le jeu. Les 258 patches sur `addiu -1` pres de
   `sh +0x12` ont touche du code FX/anim (pas de coffre), expliquant les
   effets secondaires observes.

### Decouverte cle : l'offset 0x80 avec base pre-calculee
Le code utilise un pattern inhabituel :
```
addiu $a1, $s0, 0x80    ; $a1 = entity + 128
...
lhu $v0, 0x0000($a1)    ; load from entity+0x80 via $a1
```

Cela rend le pattern invisible aux recherches `sh/lhu $reg, 0x0080($base)`
car l'offset dans les instructions load/store est **0x0000**, pas 0x80.

---

## Chronologie de la resolution (RAM dump analysis)

### 1. Extraction RAM depuis savestates ePSXe
- Format savestate : gzip, RAM a offset 0x1BA dans les donnees decompressees
- Confirme avec 5 matches SLES text section

### 2. Comparaison de 2 savestates (Coffre1 vs Coffre2)
- Champ a entity+0x80 : 839 → 403 (436 ticks = 8.7s)
- Data pointer (PAS vtable) a entity+0x7C : 0x8014CB10

### 3. Recherche du code de decrement dans la RAM
- `find_load_modify_store.py` : trouve 5 patterns lhu-addiu(-1)-sh a offset 0
- Le pattern a **RAM 0x80026E80** = le timer coffre (avec beq-despawn)
- Les 4 autres sont des timers avec `slti -3000` (different pattern)

### 4. Recherche dans BLAZE.ALL : ECHEC
- Exact 16-byte sequence : 0 matches
- 8-byte windows : certains fragments matches, mais pas le code timer
- `lhu $v0, 0($a1)` et `sh $v0, 0($a1)` : 0 occurrences alignees
  (Note: search_chest_bytes.py avait un bug d'endianness - corrige ensuite)

### 5. Mapping instruction-par-instruction RAM → BLAZE.ALL
- `map_overlay_function.py` : 2630 instructions uniques de l'overlay ABSENTES
- Aucun chunk de 64 octets de l'overlay ne matche BLAZE.ALL
- Conclusion : l'overlay code n'est PAS stocke brut dans BLAZE.ALL

### 6. Comparaison SLES vs RAM : MATCH TOTAL
- `search_sles_direct.py` : 192 matches, 0 mismatches a 0x80026D00-0x80027000
- Le code du timer est **identique** entre SLES et RAM
- Le SLES N'EST PAS ecrase par un overlay dans cette region
- Signature exacte trouvee a SLES offset 0x17678

---

## Donnees techniques

- Jeu : Blaze & Blade: Eternal Quest (Europe) PAL
- SLES_008.45 : 843,776 bytes, load_addr=0x80010000, code_size=0x000CD800
- BLAZE.ALL : 46,206,976 bytes
- BIN : 736,253,616 bytes (RAW 2352-byte sectors)
- BLAZE.ALL injecte a LBA 163167 et 185765
- Framerate : 50fps (PAL)
- Timer original : ~1000 frames = 20s
- Timer patche : infini (2x NOP)
- SLES batch timer offset : 0x17680 (RAM 0x80026E80) → NOP addiu
- SLES despawn timer offset : 0x175EC (RAM 0x80026DEC) → NOP sh
- BIN batch timer offset : 0x295FBDE8
- BIN despawn timer offset : 0x295FBD54
- Entity batch timers : entity+0x80 (48 halfwords, countdown)
- Entity despawn timer : entity+0x4C (halfword, countdown → kill at 0)

## Scripts

- `patch_loot_timer.py` : patcheur final (patche le BIN directement, step 9b du build)
