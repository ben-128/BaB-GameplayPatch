# Guide d'analyse Ghidra - Trouver les Growth Rates

## Configuration initiale

### 1. Importer SLES_008.45 dans Ghidra

1. **Nouveau projet**: File > New Project
2. **Importer**: File > Import File > Sélectionner `SLES_008.45`
3. **Format**: PlayStation Executable (ou Binary si pas détecté)
4. **Language**: MIPS > R3000 (little-endian, 32-bit)
5. **Base Address**: `0x80010000` (adresse de chargement PS1)

### 2. Analyser le fichier

1. **Auto-analyze**: Analyser > Auto Analyze
2. Cocher toutes les options recommandées
3. Laisser tourner (peut prendre quelques minutes)

---

## Recherche des Growth Rates

### Méthode 1: Chercher les références à l'offset 0x0002BBFE

L'offset `0x0002BBFE` dans le fichier correspond à l'adresse mémoire `0x8003B3FE` quand chargé.

**Étapes:**

1. **Go to address**: `G` ou Navigation > Go To...
2. Entrer: `0x8003B3FE` (adresse mémoire)
3. **Find references**: Click droit > Find References to Address
4. Examiner les fonctions qui lisent cette adresse

**Ce qu'on cherche:**
- Instructions `LBU` (Load Byte Unsigned) - charge un byte
- Instructions `LH` (Load Halfword) - charge 2 bytes
- Fonctions qui bouclent 8 fois (pour les 8 classes)
- Calculs avec offset (classe_id * 8 + stat_id)

### Méthode 2: Chercher des strings liées au level-up

1. **Search > For Strings**: Search > For Strings...
2. Chercher:
   - "level"
   - "Level"
   - "LEVEL"
   - "exp"
   - "EXP"

3. Pour chaque string trouvée:
   - Click droit > Find References to Address
   - Examiner les fonctions qui utilisent cette string

### Méthode 3: Chercher des patterns de boucles

Les growth rates sont probablement accédés dans une fonction qui:
1. Boucle sur les 8 classes
2. Boucle sur les 6-8 stats
3. Lit depuis une table

**Pattern typique en MIPS:**

```mips
# Pseudo-code de ce qu'on cherche:
loop_classes:
    li   $t0, 0              # i = 0 (classe)
    li   $t1, 8              # max = 8 classes
    la   $t2, growth_table   # adresse de la table

loop:
    sll  $t3, $t0, 3         # offset = i * 8 (8 stats par classe)
    add  $t4, $t2, $t3       # adresse = table + offset
    lbu  $t5, 0($t4)         # charger byte (stat)

    # ... utiliser $t5 ...

    addi $t0, $t0, 1         # i++
    blt  $t0, $t1, loop      # si i < 8, continuer
```

**Comment chercher:**

1. **Search > For Instruction Patterns**: Search > For Instruction Patterns...
2. Chercher:
   - `LBU` avec offset entre 0-64
   - `SLL` par 3 (multiplication par 8)
   - Boucles avec compteur jusqu'à 8

### Méthode 4: Analyser la fonction de level-up

**Si on trouve une fonction "LevelUp" ou similaire:**

1. Examiner le **Control Flow Graph** (fenêtre > Display Function Graph)
2. Chercher les **Load** depuis des adresses constantes
3. Suivre les **data references** (Xrefs)

---

## Que faire quand on trouve quelque chose

### Si on trouve des accès à 0x8003B3FE:

1. **Noter la fonction** qui lit cette adresse
2. **Désassembler** le code autour
3. **Comprendre** comment les valeurs sont utilisées:
   - Sont-elles ajoutées aux stats?
   - Multipliées par quelque chose?
   - Utilisées dans un calcul de HP/MP?

### Si l'offset 0x8003B3FE n'est PAS les growth rates:

Chercher d'autres tables:
1. Regarder les **autres adresses** accédées par la même fonction
2. Chercher des **tables de taille 48 ou 64 bytes** (8 classes × 6-8 stats)
3. Vérifier si c'est dans **BLAZE.ALL** en RAM plutôt que dans SLES

---

## Adresses importantes

| Offset fichier | Adresse mémoire | Description |
|----------------|-----------------|-------------|
| 0x0002BBFE | 0x8003B3FE | Candidat growth rates (64 bytes) |
| 0x800 | 0x80010000 | Début du code exécutable |

**Note:** BLAZE.ALL est chargé dynamiquement, donc ses adresses changent. Chercher les fonctions qui lisent depuis BLAZE.ALL.

---

## Astuces Ghidra

- **F** - Créer une fonction
- **L** - Renommer un label
- **;** - Ajouter un commentaire
- **Ctrl+E** - Éditer la fonction (changer signature)
- **Ctrl+Shift+E** - Exporter vers C (pseudo-code)

---

## Prochaines étapes

Une fois la fonction de level-up trouvée et les growth rates identifiés:
1. Noter l'**adresse exacte** de la table
2. Noter le **format** (uint8, int16, etc.)
3. Noter l'**ordre des stats** (quel byte = quelle stat)
4. Créer un patcher basé sur ces informations

---

## Aide supplémentaire

Si tu trouves quelque chose d'intéressant, partage:
- L'adresse de la fonction
- Le code assembleur
- Les adresses des tables accédées

Je pourrai t'aider à interpréter le code MIPS!
