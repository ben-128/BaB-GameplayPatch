# Loot Chest Despawn Timer - Research

## Objectif
Modifier la duree avant disparition des coffres laches par les monstres.
Duree originale : 20 secondes (1000 frames @ 50fps PAL).

## Statut : EN TEST

Le patch actuel gele le compteur de despawn (41 emplacements).
**Il n'a pas encore ete teste correctement** — voir section "Test a faire".

---

## Test a faire

### IMPORTANT : ne pas charger de savestate ePSXe

Les savestates ePSXe restaurent la RAM complete (y compris le code overlay
deja charge). Le BIN patche n'est pas relu. Le patch n'a donc aucun effet
si on charge une savestate.

### Procedure de test

1. Lancer ePSXe avec le BIN patche :
   `output/Blaze & Blade - Patched.bin`

2. **Demarrer une partie normalement** (nouveau jeu ou charger une
   sauvegarde IN-GAME via le menu du jeu, PAS une savestate ePSXe)

3. Entrer dans un donjon (ex: Cavern of Death Floor 1)

4. Tuer un monstre et attendre que le coffre apparaisse

5. Observer : **est-ce que le coffre reste indefiniment ?**
   - Si OUI → le patch fonctionne, le mecanisme est confirme.
     On pourra ensuite rendre le timer configurable.
   - Si NON (coffre disparait toujours en ~20s) → le patch de code
     overlay ne fonctionne pas (probablement compresse). Il faudra
     chercher une approche DATA (voir section Hypotheses).

---

## Patch actuel (build courant)

### Ce qui est patche : NOP du decrement a entity+0x14

Pattern cible dans BLAZE.ALL (41 instances, une par overlay de donjon) :
```
lhu   $v0, 0x0014($base)   ; charge le timer
nop                          ; delay slot
addiu $v0, $v0, -1          ; decremente   ← PATCHE en addiu $v0,$v0,0
sh    $v0, 0x0014($base)   ; stocke
```

Le `addiu $v0, $v0, -1` est remplace par `addiu $v0, $v0, 0` (gel du timer).
Si le patch fonctionne, les coffres ne disparaissent plus du tout.

### Offsets patches (41 emplacements)
```
0x00927F28  0x00928264  0x0093FCB0  0x0093FD68  0x0093FE54
0x0094E09C  0x00957658  0x00960238  0x0096047C  0x0096067C
0x00960A08  0x00BCC180  0x00BD6000  0x00D1151C  0x00DE99F4
0x00DEB060  0x00DF85D4  0x00DF91F0  0x010152BC  0x0108F230
0x01092DB4  0x01509F5C  0x01516FB0  0x01A24AAC  0x01C1DE98
0x01C25C1C  0x01E8A3A0  0x020E0B18  0x02191A10  0x024B18E0
0x0257BE6C  0x02707E60  0x02709530  0x027F367C  0x02895BF0
0x028FB6F4  0x028FD5C8  0x0295F4C0  0x02964F68  0x029658F0
0x029675A0
```

---

## Historique des tentatives

### Tentative 1 : ori $v0, $zero, 500 → sh +0x12 (ECHEC)
- Offsets : `0x009419F4`, `0x00945534`, `0x0093FB94`
- Region overlay 0x009xxxxx
- **Resultat** : aucun changement (teste avec BIN frais, pas savestate)

### Tentative 2 : slti state counter threshold (ECHEC)
- Offsets : `0x00941A40`, `0x00945748`, `0x009457E8`
- Seuils 60→180, 40→120
- **Resultat** : aucun changement

### Tentative 3 : addiu $v0, $zero, 1000 → sh +0x12 (ECHEC)
- 12 offsets dans 4 groupes (0x01BA+, 0x0257+, 0x02B7+, 0x02BC+)
- Valeur 1000→3000, avec slti guards
- **Resultat** : non teste correctement (user a charge une savestate)
- **Aussi** : crash quand applique avec tentative 4 en meme temps

### Tentative 4 : NOP decrement addiu $v0,$v0,-1 → sh +0x14 (EN TEST)
- 41 offsets repartis dans tout BLAZE.ALL
- **Resultat** : PAS ENCORE TESTE CORRECTEMENT
- Le test precedent utilisait une savestate ePSXe → invalide

---

## Analyse RAM (savestates ePSXe)

### Methode
Comparaison de 2 savestates :
- Coffre1 : coffre vient de spawn
- Coffre2 : ~10s apres, coffre encore present

### Resultats
- Entity array base : `0x800B2DB4`, stride : `0x9C` (156 bytes)
- Champ +0x12 : 839 → 403 (diff = 436 frames = 8.7s @ 50fps)
- Vtable coffre actif : `0x8014CB10`
- Vtable post-despawn : `0x8014AFD0`

### Analyse du code en RAM
- Fonction timer a RAM `0x80025F44` - `0x800261CC`
- Machine a etats via field +0x10 : 1=apparition, 2=visible, 3=disparition
- Etat 2 : decremente +0x14 chaque frame, passe a etat 3 quand < 0
- Etat 1 : +0x28/+0x2A grandit de 90/frame jusqu'a 1000 (scale)
- Etat 3 : +0x28/+0x2A diminue de 60/frame jusqu'a 0, puis desactive entite
- La valeur 1000 a +0x28 est le cap de SCALE, pas le timer

### Observation critique
- `addiu $reg, $zero, 1000` n'existe PAS dans la RAM chargee
- Les 12 offsets patches (tentative 3) ne sont pas charges en memoire
  pour le donjon teste (Cavern of Death)
- Le code overlay est probablement COMPRESSE dans BLAZE.ALL

---

## Hypotheses si le test echoue

### H1 : Overlays compresses
Les overlays de code dans BLAZE.ALL sont compresses. Le jeu les decompresse
en RAM au chargement. Nos patches sur les copies non-compressees sont ignorees.
Les patches DATA (prix, stats) fonctionnent car les donnees sont lues directement.

**Si confirme** : il faudrait soit :
- Trouver et modifier les overlays COMPRESSES
- Trouver une valeur DATA (pas code) qui controle le timer
- Patcher le SLES executable (si le timer y est initialise)
- Utiliser des codes GameShark pour modifier la RAM en temps reel

### H2 : Timer initialise par DATA
La valeur initiale du timer (+0x14) pourrait venir d'une table de donnees
par type d'entite, stockee dans les data patchables de BLAZE.ALL.
A chercher : valeurs proches de 1000 dans les structures d'entites.

### H3 : Timer dans le SLES
Le SLES (0x80010000-0x800DD800) contient peut-etre l'initialisation du timer.
L'analyse montre que le code de la fonction timer ECRASE le SLES en RAM
(overlay charge a 0x80025xxx). Le SLES pourrait contenir la valeur initiale
dans une table avant que l'overlay ne soit charge.

---

## Donnees techniques

- Jeu : Blaze & Blade: Eternal Quest (Europe) PAL
- SLES_008.45 : 843,776 bytes, text_addr=0x80010000, text_size=0x000CD800
- BLAZE.ALL : 46,206,976 bytes
- BIN : 736,253,616 bytes (RAW 2352-byte sectors)
- BLAZE.ALL injecte a LBA 163167 et 185765
- Framerate : 50fps (PAL)
- Timer original : ~1000 frames = 20s
- Entity stride : 0x9C (156 bytes), array base : 0x800B2DB4
