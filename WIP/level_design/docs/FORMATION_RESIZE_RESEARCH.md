# Formation Resize Research

## Objectif

Pouvoir changer la TAILLE des formations (nombre de slots par formation), pas seulement leur contenu.
Actuellement, changer la taille cause des monstres invisibles.

---

## Tests effectues (resultats confirmes en jeu)

### TEST 1 : Contenu modifie, taille identique -> OK
- F00 passe de `[0,0,0]` (3x Goblin) a `[0,1,2]` (Goblin+Shaman+Bat)
- Tailles : `[3, 3, 2, 4, 4, 3, 4, 4]` (inchangees)
- Resultat : **PAS de monstre invisible, tout fonctionne**

### TEST 2 : 3 formations custom + 5 originales, tailles identiques -> OK
- F00-F02 modifies (contenu change), F03-F07 originaux
- Tailles toujours `[3, 3, 2, 4, 4, 3, 4, 4]`
- Resultat : **OK**

### TEST 3 : Grosse formation 7 slots + fillers 1 slot -> FAIL
- F00 = 7 slots, F01-F07 = 1 slot chacun (filler synthetique)
- Total = 7 + 7×1 = 14 formations (meme budget, formations supplementaires)
- Resultat : **monstres invisibles**

### TEST 4 : Redistribution minimale +1/-1 -> FAIL
- F00 passe de 3 a 4 slots, F01 passe de 3 a 2 slots
- Tailles : `[4, 2, 2, 4, 4, 3, 4, 4]` (total toujours 27, toujours 8 formations)
- Resultat : **1 monstre invisible**

### TEST 5 : Formations originales exactes (verification round-trip) -> OK
- Les 8 formations avec contenu et tailles originaux
- Le patcher genere un binaire byte-pour-byte identique a l'original
- Resultat : **OK, aucun monstre invisible**

### Conclusion des tests
- **Le contenu est libre** : on peut mettre n'importe quel slot index dans n'importe quel slot
- **La taille est verrouillee** : changer le nombre de slots d'une formation, meme de 1, cause des monstres invisibles
- Le probleme n'est PAS le budget total mais la position en bytes de chaque formation dans la zone

---

## Recherches dans BLAZE.ALL (ce qui n'a PAS marche)

### Recherche 1 : Tailles comme sequence de bytes
Cherche `[03, 03, 02, 04, 04, 03, 04, 04]` dans tout le fichier (46 Mo).
**Resultat : 0 match.** Pas stocke comme tableau de bytes.

### Recherche 2 : Tailles en 16-bit ou 32-bit
Memes valeurs encodees en uint16 LE ou uint32 LE.
**Resultat : 0 match.**

### Recherche 3 : Tailles avec stride (every Nth byte)
Cherche les valeurs espacees de 2, 4, 8, 32 bytes.
**Resultat : matches aleatoires sans rapport avec les formations.**

### Recherche 4 : Offsets cumulatifs des formations
Les offsets relatifs `[0, 100, 200, 268, 400, 532, 632, 764]` en 16-bit et 32-bit.
**Resultat : 0 match pour la sequence complete.**

### Recherche 5 : Offsets absolus des formations
`[0xF7AFFC, 0xF7B060, 0xF7B0C4, ...]` en 32-bit LE.
- `0xF7AFFC` (F00) : trouve a 4 endroits (~0x01892000)
- **Mais c'est un FAUX POSITIF** : ce sont des coordonnees 3D (Y=-840, Z=-2129) dont les bytes forment accidentellement le pattern `FC AF F7 00`
- Formations F01-F07 : **aucun match** -> confirme qu'il n'y a pas de table de pointeurs par formation

### Recherche 6 : Compteurs de formations et slots
Cherche les valeurs 8 (formation_count) et 27 (total_slots) pres de 0xF7AFFC.
**Resultat : pas trouves dans la region.**

### Recherche 7 : Sommes cumulatives de slots
`[3, 6, 8, 12, 16, 19, 23, 27]` en bytes, 16-bit, 32-bit, stride.
**Resultat : 0 match.**

### Recherche 8 : Gap entre formations et zone_spawns
420 bytes entre 0xF7B37C et 0xF7B520 examines en detail.
- Region A (88 bytes) : config d'encounter, contient la valeur 8 en u16 mais dans un contexte different
- Region B (116 bytes) : table de references (indices incrementaux avec flags)
- Region C (216 bytes) : records de zone_spawn overflow
- **Aucune metadata de taille de formation trouvee dans ce gap**

---

## Trouvailles dans l'executable SLES_008.45

Executable: `Blaze  Blade - Eternal Quest (Europe)/extract/SLES_008.45`
- Taille: 843,776 bytes
- Entry point: PC=0x8002E550
- Text segment charge a: 0x80010000
- Conversion: `file_offset = RAM_address - 0x80010000 + 0x800`

### 1. Table de comptage (186 bytes)

**RAM: `0x8003B3A8`** | **File: `0x2BBA8`**

Un byte par zone de jeu. Valeurs de 2 a 10 (jamais 9). Distribution:
- 6 = 81 zones (43%), 5 = 23, 4 = 23, 8 = 15, 7 = 15, 2 = 13, 3 = 9, 10 = 7

Lue a `0x80017604` (formation count table lookup).

**Probleme** : le mapping area_id -> table_index n'est PAS resolu.
- Le `area_id` dans nos JSON (bytes[24:26] des records, ex: "dc01") n'est PAS le meme identifiant que l'area_id utilise dans l'exe
- La formule de mapping testee (plages 0x22-0xFF avec offsets) donne **1 match sur 31** (3%) = essentiellement du hasard
- L'area_id JSON est un identifiant de room/zone, l'area_id de l'exe est un index de niveau
- **On ne sait pas quel byte de cette table correspond a Cavern F1 Area1**

### 2. Mapping Area ID -> Table Index (code a 0x80017594)

Le code utilise un systeme de plages avec offsets soustraits :

| Plage Area ID | Soustraction | Table index result |
|---------------|-------------|-------------------|
| 0x22 - 0x3F   | 34          | 0 - 13            |
| 0x41 - 0x5F   | 33          | 14 - 44           |
| 0x61 - 0x9F   | 35          | 26 - 106          |
| 0xA1 - 0xBF   | 68          | 85 - 123          |
| 0xC1 - 0xDF   | 69          | 124 - 154         |
| 0xE1 - 0xFF   | 70          | 155 - 185         |

Cas speciaux (boss/villes) : `0x40, 0x80, 0x8A, 0x9A, 0xC0, 0xE0` -> redirigent vers area `0xA5`.

**Le probleme : l'area_id utilise ici (0x22-0xFF) n'est PAS celui de nos JSON.** Il faut trouver ou le jeu stocke l'identifiant de zone qui alimente cette fonction.

### 3. Ce que fait le code a 0x800175E0-0x800178A0 (desassemble)

Ce n'est PAS le parseur de templates de formation. C'est le decodeur de la **carte d'encounters** :

```
Boucle externe : 15 iterations ($s0 = 0xF -> 0)
  - Lit 3 bytes depuis le buffer RAM 0x801AD8F0 -> construit un mot de 24 bits
  - Boucle interne : `count` iterations (valeur de la table 186 bytes)
    - Extrait 1 bit a la fois (shift left de $a3)
    - Ecrit des nibbles dans un buffer a 0x8005BF00
  - Avance de 40 bytes dans la source, 128 bytes dans la sortie
```

C'est un decodeur de bitmap : chaque bit determine si une formation apparait a une position donnee sur la carte. La valeur de la table (2-10) = nombre de formations possibles par zone. Ce n'est PAS la taille des formations.

### 4. Interpreteur de bytecode (0x80017D64)

Boucle d'interpretation completement separee du parseur de formations :

```
loop:
  opcode = lbu($s1)           ; lit 1 byte du flux
  $s1 += 1                    ; avance le pointeur
  if opcode == 0: pop/return  ; opcode 0 = retour de sous-routine
  if opcode >= 32: erreur     ; opcodes valides : 1-31
  handler = dispatch_table[opcode]  ; table a 0x8003B468
  $s1 = handler($s1, context) ; le handler consomme des bytes et retourne le nouveau pointeur
  if opcode in {9, 14, 15}: exit  ; ces opcodes terminent l'execution
  goto loop
```

**Table de dispatch** (32 handlers, 23 uniques) :

| Handler         | Opcodes                  | Notes                          |
|-----------------|--------------------------|--------------------------------|
| `0x80016DF0`    | 0, 5, 8, 9, 14, 20      | Handler partage (6 opcodes)    |
| `0x80016DF8`    | 2, 3, 4, 6              | Handler partage (4 opcodes)    |
| `0x80016DE8`    | 12, 13                   | Handler partage (2 opcodes)    |
| `0x80016E00`    | 1                        | Unique                         |
| `0x80016E08`    | 10                       | Unique                         |
| `0x8001855C`    | 7                        | Unique                         |
| `0x80018794`    | 11                       | Unique                         |
| `0x80018B40+`   | 15-31                    | Chacun a son propre handler    |

**Ce bytecode n'est PAS le parseur de formation templates.** C'est un systeme de scripting separe (probablement pour la logique d'encounter/events). Les handlers 0-10 sont de petits stubs groupes a `0x80016DE0`. Les handlers 15+ sont des fonctions plus grosses.

### 5. Table de secteurs CD (193 entries)

**RAM: `0x8003CB50`** | **File: `0x2C350`**

Entries 16-bit : numero de secteur dans BLAZE.ALL (secteur × 2048 = byte offset).
L'offset 0xF7AFFC tombe entre entries [182] (secteur 0x1EDD = 0xF6E800) et [183] (secteur 0x1EFA = 0xF7D000).

### 6. Adresses cles

| RAM             | File      | Description                                |
|-----------------|-----------|--------------------------------------------|
| `0x80017530`    | `0x07D30` | Gestion cas speciaux area ID               |
| `0x80017594`    | `0x07D94` | Mapping area ID -> table index             |
| `0x80017604`    | `0x07E04` | Lecture table formation count              |
| `0x80017634`    | `0x07E34` | Division par 31 (magic 0x84210843)         |
| `0x80017698`    | `0x07E98` | Base buffer RAM 0x801AD8F0                 |
| `0x800176CC`    | `0x07ECC` | Decodage bitfield (3 bytes -> 24 bits)     |
| `0x80017D5C`    | `0x0855C` | Setup table dispatch bytecode              |
| `0x80017D64`    | `0x08564` | Boucle interpreteur bytecode               |
| `0x8002E3B8`    | `0x14BB8` | Lecture table secteurs CD                  |
| `0x80029F60`    | `0x10760` | Init buffer formations                     |
| `0x8003B3A8`    | `0x2BBA8` | Table encounter count (186 bytes)          |
| `0x8003B468`    | `0x2BC68` | Table dispatch bytecode (32 ptrs)          |
| `0x8003CB50`    | `0x2C350` | Table secteurs CD (193 entries)            |
| `0x801AD8F0`    | N/A (RAM) | Buffer encounter bitmap runtime            |
| `0x8005BF00`    | N/A (RAM) | Buffer sortie decodage encounter           |

---

## Ce qu'on n'a PAS encore trouve

### Le parseur de formation templates
Le code qui lit les records de 32 bytes avec delimiteur FFFFFFFF n'a PAS ete identifie.
Les fonctions analysees (0x80017500-0x80017E00) sont :
- Un decodeur de bitmap d'encounters (pas les templates)
- Un interpreteur de bytecode de scripting (pas les templates)

Le parseur de templates est probablement AILLEURS dans l'executable. Il doit :
1. Recevoir un pointeur vers les donnees de formation en RAM (chargees depuis BLAZE.ALL)
2. Lire des records de 32 bytes
3. Utiliser byte[4:8] == FFFFFFFF pour delimiter les formations (ou pas)
4. Construire une representation interne utilisee pour generer les groupes de monstres

### Le mapping area -> table index
On ne sait pas quel area_id du jeu correspond a quel index dans la table de 186 bytes.
L'area_id de nos JSON n'est PAS le meme systeme d'identification.

### La raison exacte des monstres invisibles
On ne sait toujours pas POURQUOI changer les tailles cause des invisibles. Hypotheses :
- A) La structure packee en RAM attend les formations a des positions fixes
- B) Un autre systeme (rendering, AI placement) utilise des offsets pre-calcules
- C) Le parseur de templates utilise des tailles hardcodees (pas les delimiteurs)

---

## Prochaines etapes suggerees

### 1. Trouver le VRAI parseur de formation templates
Chercher dans l'exe le code qui :
- Reference la constante 32 (taille record) pres d'une boucle
- Lit byte[4:8] et compare avec 0xFFFFFFFF
- Ou reference byte[8] (slot index) et byte[9] (0xFF = marker)
Le code se trouve probablement autour de `0x80016D00-0x80016E00` (zone des handlers de bytecode) ou dans une fonction appelee lors du chargement de niveau.

### 2. Utiliser un emulateur avec debugger
PCSX-Redux ou no$psx permettent de :
- Mettre un breakpoint en lecture sur la zone 0xF7AFFC-0xF7B37C dans la RAM
- Observer exactement quel code lit les formation templates
- Tracer le flux d'execution pour comprendre le parsing

### 3. Identifier le mapping area -> table
Lancer le jeu dans l'emulateur, aller a Cavern F1, et observer :
- La valeur chargee a `0x80017604` (quelle valeur la table retourne)
- L'index utilise pour acceder a la table (quel "area_id" le jeu utilise)

---

## Fichiers de reference

| Fichier | Description |
|---------|-------------|
| `Data/formations/patch_formations.py` | Patcher actuel (contenu uniquement) |
| `Data/formations/cavern_of_death/floor_1_area_1.json` | Zone de test principale |
| `Blaze  Blade - Eternal Quest (Europe)/extract/SLES_008.45` | Executable PSX original |
| `Blaze  Blade - Eternal Quest (Europe)/extract/SLES_008.45.backup` | Backup |
| `analyze_formation_table.py` | Script d'analyse de la table 186 bytes |
| `analyze_tables.py` | Script dump tables dispatch + count |
| `disasm_regions.py` | Desassembleur MIPS pour les regions cles |

---

## Scripts temporaires generes (a la racine du projet)

Ces scripts ont ete crees pendant la recherche et peuvent etre supprimes :
- `analyze_formation_refs.py` - analyse des faux positifs de 0xF7AFFC
- `analyze_formation_table.py` - dump table 186 bytes + validation JSON
- `analyze_tables.py` - dump tables dispatch + count
- `disasm_regions.py` - desassembleur MIPS custom
- `output/analysis_v2.txt` - sortie analyse coordonnees
- `output/formation_ref_analysis_final.txt` - sortie analyse references
