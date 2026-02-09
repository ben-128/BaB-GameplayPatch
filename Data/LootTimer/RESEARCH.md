# Loot Chest Despawn Timer - Research

## Objectif
Modifier la duree avant disparition des coffres laches par les monstres.
Duree originale : 20 secondes (1000 frames @ 50fps PAL).

## Statut : v4 - ALL REGISTERS OVERLAY PATCH

Le vrai code de despawn est dans le **dungeon overlay** charge depuis BLAZE.ALL,
PAS dans le SLES executable. Les patches SLES (v1/v2) etaient inefficaces.

---

## Solution v3 : Overlay countdown NOP

### Mecanisme reel : state machine dans l'overlay

Le cycle de vie des coffres est gere par un automate a 3 etats dans le code
overlay charge en RAM a 0x80080000+ (zone zero dans SLES) :

```
State 1 (fade-in) :
  entity+0x28 += 90/frame    ; apparence augmente
  entity+0x2A += 90/frame
  Quand entity+0x28 >= 1001 → cap a 1000, passage a State 2

State 2 (vivant - countdown) :
  entity+0x14 -= 1/frame     ; TIMER DE DESPAWN ← PATCH ICI
  Quand entity+0x14 < 0 (signe) → passage a State 3

State 3 (fade-out) :
  entity+0x28 -= 60/frame    ; disparition rapide
  entity+0x2A -= 60/frame
  Quand entity+0x28 < 0 → bit 14 de entity+0x00 = KILL
```

### Code assembleur (State 2 countdown, RAM 0x80099BCC)

```
86230010  lh   $v1, 0x10($s1)    ; load state
24020002  addiu $v0, $zero, 2
14620009  bne  $v1, $v0, +9      ; skip if state != 2
00000000  nop
96220014  lhu  $v0, 0x14($s1)    ; load timer
00000000  nop
2442FFFF  addiu $v0, $v0, -1     ; DECREMENT ← NOP THIS
A6220014  sh   $v0, 0x14($s1)    ; store timer
00021400  sll  $v0, $v0, 16      ; sign-extend pour bgez
04410002  bgez $v0, +2           ; si timer >= 0, skip
24020003  addiu $v0, $zero, 3    ; state = 3
A6220010  sh   $v0, 0x10($s1)    ; ecrire state 3
```

### Le patch

**Signature** (16 bytes) :
```
96220014 00000000 2442FFFF A6220014
lhu $v0,0x14($s1) / nop / addiu $v0,$v0,-1 / sh $v0,0x14($s1)
```

**Action** : NOP l'instruction index 2 (`addiu $v0,$v0,-1` → `00000000`)

**35 occurrences dans BLAZE.ALL** (multiples overlays, 4 registres de base) :

Le meme pattern existe avec differents registres de base :
- 7 avec **$s1** (overlay handler principal)
- 9 avec **$s0** (overlay handler secondaire)
- 16 avec **$s2** (overlay handler variant)
- 3 avec **$v1** (overlay handler misc)

La v3 initiale ne patchait que les 7 patterns $s1. L'entite coffre est
traitee par un handler utilisant un AUTRE registre ($s0 ou $s2), donc
le timer continuait de decrementer.

La v4 patche les 35 patterns avec un matching masque sur le registre :
```
w0: (w0 & 0xFC1FFFFF) == 0x94020014  → lhu $v0, 0x14(ANY)
w1: 0x00000000                        → nop
w2: 0x2442FFFF                        → addiu $v0, $v0, -1
w3: (w3 & 0xFC1FFFFF) == 0xA4020014  → sh $v0, 0x14(ANY)
+ base register of w0 == base register of w3
```

### Build

Le patch est applique au **step 7** dans `build_gameplay_patch.bat`.
Il patche `output/BLAZE.ALL` AVANT injection dans le BIN (step 9).

---

## Decouverte cle : l'overlay est stocke brut dans BLAZE.ALL

L'overlay charge en RAM a 0x80080000 est une copie **exacte** des bytes
dans BLAZE.ALL. Mapping pour Cavern F1 :

```
RAM 0x80080000 = BLAZE.ALL 0x009468A8
RAM 0x80099BD4 = BLAZE.ALL 0x0096047C  (notre cible)
Offset = RAM_addr - 0x80080000 + 0x009468A8
```

La region overlay couvre 137,824 bytes (0x80080000 - 0x800A1A5C).
Le SLES a des **zeros** dans toute cette zone (confirme par comparaison).

### Autres patterns entity+0x14 dans BLAZE.ALL

35 patterns `lhu $v0,0x14($base) / nop / addiu $v0,-1 / sh $v0,0x14($base)` trouves
avec differents registres ($s0, $s1, $s2, $v1). Tous sont patches car le coffre
peut etre traite par n'importe quel handler (confirme : $s1 seul ne suffit pas).

---

## Historique : pourquoi v1 et v2 ont echoue

### v1 : batch timer seul (entity+0x80)
- Patchait `addiu $v0,$v0,-1` dans la boucle 48 timers du SLES
- Les 48 timers a entity+0x80 etaient geles
- Mais le VRAI timer (entity+0x14 dans l'overlay) continuait de tourner
- Resultat : coffres disparaissaient toujours a 20s

### v2 : batch timer + entity+0x4C
- Ajoutait NOP sur le store a entity+0x4C
- entity+0x4C = HP combat (pas timer coffre !)
- Cassait le combat (monstres immortels)
- Coffres disparaissaient toujours

### Root cause des echecs
1. **Mauvaise cible** : le code SLES (0x80026E80) gere les batch timers et le
   combat, PAS le cycle de vie des coffres
2. **Code overlay invisible** : la region 0x80080000+ est zero dans le SLES
   mais remplie a runtime par le dungeon overlay charge depuis BLAZE.ALL
3. **Region 0x009xxxxx** : precedemment consideree comme "dead data" dans
   BLAZE.ALL, c'est en fait le code overlay des donjons

---

## Donnees techniques

- Jeu : Blaze & Blade: Eternal Quest (Europe) PAL
- SLES_008.45 : 843,776 bytes, load_addr=0x80010000, code_size=0x000CD800
- BLAZE.ALL : 46,206,976 bytes
- Framerate : 50fps (PAL)
- Timer original : ~1000 frames = 20s
- Timer patche : infini (NOP decrement)
- Entity struct (overlay fields) :
  - +0x00 : flags (bit 14 = kill)
  - +0x10 : state (1=spawn, 2=alive, 3=despawn)
  - +0x14 : countdown timer (halfword, unsigned)
  - +0x28 : appearance/opacity (halfword)
  - +0x2A : appearance2 (halfword)

## Scripts

- `patch_loot_timer.py` : patcheur v3 (patche BLAZE.ALL, step 7 du build)
- `check_overlay_vs_sles.py` : comparaison RAM overlay vs SLES file
- `find_overlay_in_blazeall.py` : localisation du code overlay dans BLAZE.ALL
- `survey_countdown_pattern.py` : inventaire de tous les patterns countdown
