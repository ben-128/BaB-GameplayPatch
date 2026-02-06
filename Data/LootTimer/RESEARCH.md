# Loot Chest Despawn Timer - Research

## Objectif
Modifier la duree avant disparition des coffres laches par les monstres.
Duree originale : 20 secondes (1000 frames @ 50fps PAL).

## SOLUTION TROUVEE

### Timer = entity field +0x12, valeur initiale 1000

Le timer de despawn des coffres est un compteur a rebours stocke dans le champ
+0x12 (uint16) de l'entite. Il demarre a 1000 et decremente de 1 par frame.
A 50fps PAL, 1000 frames = 20 secondes exactement.

**Confirmation par comparaison de savestates ePSXe** :
- Coffre1 (vient de spawn) : field +0x12 = 839 (161 frames = 3.2s apres spawn)
- Coffre2 (~10s apres) : field +0x12 = 403 (diff = 436 frames = 8.7s, coherent)
- Entites coffre a stride 0x9C (156 bytes) dans le tableau a 0x800B2DB4

### 12 emplacements patchables dans BLAZE.ALL

Le code est duplique par module de donjon. Chaque module contient le pattern :
```
slti $v0, $v0, 1000        ; garde de clampage
bne  $v0, $zero, +skip
...
addiu $v0, $zero, 1000     ; valeur initiale du timer
sh    $v0, 0x0012($base)   ; stocke dans entity.field_12
```

**Variante A** (10 instances, par paires $s0/$a2) :
| Offset addiu | Offset slti | Base reg |
|---|---|---|
| 0x01BA5648 | 0x01BA563C | $s0 |
| 0x01BA5780 | 0x01BA5774 | $a2 |
| 0x01BA5E48 | 0x01BA5E3C | $s0 |
| 0x01BA5F80 | 0x01BA5F74 | $a2 |
| 0x0257C018 | 0x0257C00C | $s0 |
| 0x0257C1B4 | 0x0257C1A8 | $a2 |
| 0x02B771D8 | 0x02B771CC | $s0 |
| 0x02B77374 | 0x02B77368 | $a2 |
| 0x02BC9B60 | 0x02BC9B54 | $s0 |
| 0x02BC9CFC | 0x02BC9CF0 | $a2 |

**Variante B** (2 instances, slti 1001 au lieu de 1000) :
| Offset addiu | Offset slti | Base reg |
|---|---|---|
| 0x02B78830 | 0x02B78828 | $s1 |
| 0x02BCBA84 | 0x02BCBA7C | $s1 |

Tous dans les regions de donnees patchables (> 0x01BA0000).

### Pourquoi les tentatives precedentes ont echoue

Les offsets 0x009xxxxx (region overlay code) contiennent du code MIPS valide
mais cette region n'est PAS chargee par le jeu — c'est probablement du dead data
d'un ancien build. Le vrai code est dans les modules par donjon (0x01BA+, 0x0257+,
0x02B7+, 0x02BC+) que le jeu charge dynamiquement.

## Historique des tentatives

### Tentative 1 : field 18 ori $v0, $zero, 500 (ECHEC)
- Offsets : `0x009419F4`, `0x00945534`, `0x0093FB94`
- Region overlay 0x009xxxxx = dead code, non charge par le jeu
- Valeur 500 =/= valeur reelle 1000

### Tentative 2 : slti state counter (ECHEC)
- Offsets : `0x00941A40`, `0x00945748`, `0x009457E8`
- Meme probleme : region overlay non chargee

### Tentative 3 : addiu $v0, $zero, 1000 dans modules donjon (SUCCES)
- 12 offsets dans 4 groupes de modules
- Region donnees patchable confirmee (meme zone que monster stats, formations)

## Donnees techniques

- Jeu : Blaze & Blade: Eternal Quest (Europe) PAL
- BLAZE.ALL : 46,206,976 bytes
- BIN : 736,253,616 bytes (RAW 2352-byte sectors)
- BLAZE.ALL injecte a LBA 163167 et 185765
- Framerate : 50fps (PAL)
- Timer : 1000 frames = 20s (original)
- Entity stride : 0x9C (156 bytes), array base : 0x800B2DB4
- Vtable coffre actif : 0x8014CB10, post-despawn : 0x8014AFD0
