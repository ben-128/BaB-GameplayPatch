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
- Total = 7 + 7x1 = 14 formations (meme budget, formations supplementaires)
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

## Recherches dans BLAZE.ALL (8 methodes, toutes negatives)

| # | Methode | Pattern cherche | Resultat |
|---|---------|-----------------|----------|
| 1 | Bytes bruts | `[03,03,02,04,04,03,04,04]` | 0 match |
| 2 | 16-bit / 32-bit LE | Memes valeurs en uint16/uint32 | 0 match |
| 3 | Stride (2/4/8/32 bytes) | Valeurs espacees | Matches aleatoires |
| 4 | Offsets cumulatifs | `[0,100,200,268,400,532,632,764]` | 0 match |
| 5 | Offsets absolus | `0xF7AFFC` etc. en 32-bit | Faux positifs (coordonnees 3D) |
| 6 | Compteurs | 8 (formations) et 27 (slots) pres de 0xF7AFFC | Non trouves |
| 7 | Sommes cumulatives | `[3,6,8,12,16,19,23,27]` | 0 match |
| 8 | Gap 420 bytes | Region entre formations et zone_spawns | Pas de metadata de taille |

**Conclusion** : les tailles de formation ne sont stockees nulle part dans BLAZE.ALL comme table de donnees.

---

## Trouvailles dans l'executable SLES_008.45

Executable: `Blaze  Blade - Eternal Quest (Europe)/extract/SLES_008.45`
- Taille: 843,776 bytes (824 KB)
- Entry point: PC=0x8002E550
- Text segment charge a: 0x80010000
- Conversion: `file_offset = RAM_address - 0x80010000 + 0x800`

### 1. Table de comptage d'encounters (186 bytes)

**RAM: `0x8003B3A8`** | **File: `0x2BBA8`**

Un byte par zone. Valeurs 2-10 (jamais 9). Distribution : 6 domine (81 zones, 43%).

C'est le nombre de **formations possibles par zone** utilise par le decodeur de bitmap d'encounters (pas les tailles individuelles). Le code a `0x80017604` l'utilise comme compteur de boucle pour extraire des bits d'un mot de 24 bits.

**Mapping area_id -> table_index** : NON RESOLU.
L'area_id de nos JSON (bytes[24:26] des records) n'est PAS le meme identifiant que celui utilise par l'exe. Formule testee : 3% de match = echec.

### 2. Decodeur de bitmap d'encounters (0x800175E0-0x800178A0)

Ce n'est **PAS** le parseur de formation templates. C'est un decodeur de bitmap :

```
Boucle externe: 15 iterations
  Lit 3 bytes depuis buffer RAM 0x801AD8F0 -> mot 24 bits
  Boucle interne: `count` iterations (table 186 bytes)
    Extrait 1 bit, ecrit nibble dans buffer 0x8005BF00
  Avance +40 bytes source, +128 bytes sortie
```

Determine OU chaque formation peut apparaitre sur la carte (encounter probability map).

### 3. Interpreteur de bytecode (0x80017D64)

Systeme de scripting separe, **PAS** le parseur de formations :

```
loop: opcode = read_byte(stream++) -> dispatch_table[opcode](stream, context)
```

32 opcodes, 23 handlers uniques. Table dispatch a `0x8003B468` (file `0x2BC68`).
Opcodes 9, 14, 15 terminent l'execution. Opcode 0 = pop/return.

### 4. Table de secteurs CD (193 entries)

**RAM: `0x8003CB50`** | **File: `0x2C350`**

Entries 16-bit (numero de secteur). Secteur x 2048 = byte offset dans BLAZE.ALL.
Formation area de Cavern F1 entre entries [182] et [183].

### 5. Adresses cles

| RAM | File | Description |
|-----|------|-------------|
| `0x80017530` | `0x07D30` | Cas speciaux area ID |
| `0x80017594` | `0x07D94` | Mapping area ID -> table index |
| `0x80017604` | `0x07E04` | Lecture table encounter count |
| `0x80017634` | `0x07E34` | Division par 31 (magic 0x84210843) |
| `0x80017698` | `0x07E98` | Base buffer RAM 0x801AD8F0 |
| `0x800176CC` | `0x07ECC` | Decodage bitfield 3 bytes -> 24 bits |
| `0x80017D5C` | `0x0855C` | Setup table dispatch bytecode |
| `0x80017D64` | `0x08564` | Boucle interpreteur bytecode |
| `0x8002E3B8` | `0x14BB8` | Lecture table secteurs CD |
| `0x80029F60` | `0x10760` | Init buffer formations |
| `0x8003B3A8` | `0x2BBA8` | Table encounter count (186 bytes) |
| `0x8003B468` | `0x2BC68` | Table dispatch bytecode (32 ptrs) |
| `0x8003CB50` | `0x2C350` | Table secteurs CD (193 entries) |
| `0x801AD8F0` | N/A (RAM) | Buffer encounter bitmap runtime |
| `0x8005BF00` | N/A (RAM) | Buffer sortie decodage encounter |

---

## Investigation PCSX-Redux (emulateur avec debugger)

Version: pcsx-redux-nightly-23069.20251118.1-x64

### Script Lua : recherche formations en RAM
Les formations de Forest F1 Area1 sont chargees a `0x800E2E58` en RAM (6 records, area_id 8e02).
90 autres records avec area_id FFFF trouves (donnees generiques/templates).

### Breakpoint Read (GUI) -> NE FONCTIONNE PAS
- Breakpoint Read:4 pose sur 0x800E2E5C (byte[4:8] du premier record)
- Active, type "Read:4 GUI Always 0"
- **Ne se declenche jamais**, meme en changeant de zone et revenant
- Probablement un bug/limitation de PCSX-Redux pour les data read breakpoints

### Breakpoint Read (Lua API) -> API INCOMPATIBLE
- `PCSX.addBreakpoint(addr, 4, "Read")` -> erreur "needs a valid breakpoint type"
- `PCSX.addBreakpoint(addr)` -> OK mais cree un breakpoint Execute uniquement
- L'API Lua ne supporte que les breakpoints Execute, pas Read/Write

### Breakpoints Execute sur code connu -> NE SE DECLENCHENT PAS
3 breakpoints poses sur :
- `0x80029F60` (formation buffer init)
- `0x80017604` (encounter count table read)
- `0x800176CC` (packed bitfield decode)

**Aucun ne se declenche.** Les breakpoints disparaissent rapidement (one-shot ?).
Cela confirme que ces fonctions ne sont PAS appelees pendant le gameplay normal a Forest F1.

### Polling Lua (surveillance memoire) -> PAS DE CHANGEMENT
Script avec `PCSX.Events.createEventListener("GPU::Vsync", callback)` qui verifie toutes les 10 frames si les donnees a 0x800E2E58 ont change.
**Les donnees ne changent PAS** quand on sort et revient dans la zone.
-> Les formations sont chargees une seule fois et restent en RAM.

### RAM dumps (avant/apres entree dans Forest F1)
Deux dumps de 2 Mo crees : `output/ram_before.bin` et `output/ram_after.bin`.
**Diff pas encore analyse** - potentiellement utile pour trouver toutes les structures
modifiees lors du chargement de zone.

---

## Ce qui reste a trouver

### 1. Le parseur de formation templates
Le code MIPS qui lit les records de 32 bytes n'a PAS ete identifie. Les 2 fonctions desassemblees
(encounter bitmap decoder + bytecode interpreter) ne sont pas le parseur.

**Approche suggeree** : analyse statique de l'exe, chercher des clusters d'instructions MIPS qui :
- Lisent un word a offset +4 (delimiteur FFFFFFFF)
- Comparent avec -1 (`addiu $reg, $zero, -1`)
- Lisent un byte a offset +8 (slot index)
- Avancent de 32 bytes (taille record)

### 2. Le diff des RAM dumps
Comparer ram_before.bin et ram_after.bin pour trouver :
- Ou exactement les formations sont ecrites
- S'il y a des tables d'offsets ou de metadata creees en meme temps
- Des pointeurs vers 0x800E2E58 (adresse RAM des formations)

### 3. Le mapping area -> table index
Identifier quel identifiant de zone le jeu utilise (pas celui de nos JSON).

---

## Fichiers de reference

| Fichier | Description |
|---------|-------------|
| `Data/formations/patch_formations.py` | Patcher actuel (contenu uniquement) |
| `Data/formations/cavern_of_death/floor_1_area_1.json` | Zone de test Cavern |
| `Data/formations/forest/floor_1_area_1.json` | Zone de test Forest |
| `Blaze  Blade - Eternal Quest (Europe)/extract/SLES_008.45` | Executable PSX |
| `tools/dump_ram.lua` | Script Lua pour dumper la RAM PSX |
| `output/ram_before.bin` | RAM dump avant Forest F1 |
| `output/ram_after.bin` | RAM dump apres Forest F1 |
