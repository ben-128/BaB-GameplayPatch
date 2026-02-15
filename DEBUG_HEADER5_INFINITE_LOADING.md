# Debug: Header Count = 5 Infinite Loading

## Objectif

Trouver POURQUOI `header_count=5` cause infinite loading et le patcher pour le fixer.

## Version Actuelle

- Header count @ 0xF7A851 = **5** (changé de 3)
- Middle count @ 0xF7A93A = **5** (changé de 3)
- Animation tables = **3** (vanilla, pas changé)
- Stats = **3** (vanilla, pas changé)

**Symptôme:** Infinite loading lors de l'entrée dans Cavern F1 A1

---

## Étapes de Debug avec DuckStation

### 1. Lancer le Jeu

1. Ouvre DuckStation
2. Charge le BIN patché
3. Charge une sauvegarde juste avant Cavern F1 A1
4. **N'entre PAS encore** dans Cavern

### 2. Préparer le Debugger

1. Menu: **Debug → CPU Debugger**
2. Menu: **Debug → Memory Scanner** (optionnel mais utile)
3. Garde la fenêtre CPU Debugger visible

### 3. Déclencher l'Infinite Loading

1. Entre dans Cavern F1 A1
2. Le jeu va commencer à charger
3. **Attends 5 secondes** (pour être sûr qu'il est bloqué)
4. **Pause** (bouton Pause ou **F10**)

### 4. Analyser Où le Jeu est Bloqué

Le CPU Debugger montre:
- **PC (Program Counter):** adresse actuelle d'exécution
- **Instructions:** le code assembleur
- **Registres:** valeurs de v0, v1, a0, a1, etc.

**Regarde le PC** - c'est là que le jeu est bloqué.

### 5. Identifier le Type de Boucle

#### Cas A: Boucle d'Attente CD

Si tu vois quelque chose comme:
```
80012340: lw    v0, 0x1234(s0)   # Charge une valeur
80012344: andi  v0, v0, 0x01     # Test un bit
80012348: beqz  v0, 0x80012340   # Retour si zéro (boucle!)
8001234C: nop
```

**C'est une boucle d'attente** - le jeu attend que quelque chose devienne non-zéro (généralement une lecture CD).

**Ce qui se passe:**
- Le jeu demande au CD de lire quelque chose
- Il attend que le flag "lecture terminée" se mette à 1
- Mais la lecture ne finit jamais → infinite loading

#### Cas B: Boucle de Comptage

Si tu vois:
```
80023400: lw    v0, 0x100(s1)    # Charge compteur
80023404: addiu v0, v0, 1        # Incrémente
80023408: sw    v0, 0x100(s1)    # Sauvegarde
8002340C: slti  v1, v0, 5        # Compare à 5
80023410: bnez  v1, 0x80023400   # Continue si < 5
```

**C'est une boucle for(i=0; i<5; i++)** qui essaie de charger 5 choses.

**Ce qui se passe:**
- Le jeu essaie de charger 5 animation tables/records
- Mais il n'y en a que 3 dans le binaire
- Il attend indéfiniment les 2 manquants

---

## Informations à Rapporter

Une fois le jeu en pause, note:

### 1. Program Counter (PC)
```
PC = 0x80XXXXXX
```

### 2. Instructions Autour (±5 lignes)
```
80XXXXXX-10: instruction
80XXXXXX-08: instruction
80XXXXXX-04: instruction
80XXXXXX   : instruction  ← PC actuel
80XXXXXX+04: instruction
80XXXXXX+08: instruction
```

### 3. Registres Importants
```
v0 = 0xXXXXXXXX
v1 = 0xXXXXXXXX
a0 = 0xXXXXXXXX (souvent utilisé pour compteurs)
s0 = 0xXXXXXXXX (souvent pointeur de structure)
s1 = 0xXXXXXXXX
```

### 4. Valeurs en Mémoire

Si tu vois `lw v0, 0x100(s0)`, note:
- Valeur de s0
- Valeur à l'adresse `s0 + 0x100`

---

## Solutions Possibles Selon le Cas

### Si Cas A (Attente CD)

**Problème:** Le jeu essaie de lire des données CD qui n'existent pas.

**Solution:** Patcher le code pour sauter cette lecture:
```
Remplacer: beqz v0, 0x80012340  (boucle infinie)
Par:       nop                  (ne rien faire)
           nop
```

### Si Cas B (Boucle for)

**Problème:** Le jeu boucle de 0 à 4 (5 itérations) mais bloque.

**Solutions possibles:**

#### Option 1: Changer la limite de boucle
```
Remplacer: slti v1, v0, 5   (compare à 5)
Par:       slti v1, v0, 3   (compare à 3)
```

#### Option 2: Ajouter vraiment 5 animation tables
- Revenir au code et ajouter 2 animation tables
- Mais on sait que ça crashe (TEST D)
- Donc cette option ne marche pas

#### Option 3: Faire semblant que la boucle a fini
```
Remplacer: addiu v0, v0, 1     (i++)
Par:       li    v0, 5         (i = 5, force la sortie)
```

---

## Outils DuckStation Utiles

### Breakpoints

Tu peux mettre un breakpoint AVANT d'entrer dans Cavern:

1. Trouve l'adresse du code de chargement d'area (ex: 0x80021E68)
2. Dans CPU Debugger: clic droit → **Add Breakpoint**
3. Entre dans Cavern
4. Le jeu s'arrête au breakpoint
5. **Step Over (F11)** ligne par ligne pour voir où ça bloque

### Memory Viewer

Pour voir le header_count en mémoire:

1. Le fichier BLAZE.ALL est chargé en RAM
2. Header @ 0xF7A851 dans le fichier
3. Cherche cette valeur en RAM (ça change selon où c'est chargé)
4. Memory Viewer → Search → 03 00 00 00 (cherche l'ancien 3)
5. Tu peux modifier en RAM pour tester sans rebuilder

---

## Workflow Complet

1. **Debug** → trouve le code qui bloque
2. **Identifie** le patch nécessaire (change limite, skip boucle, etc.)
3. **Trouve** l'offset dans BLAZE.ALL qui correspond au code RAM
   - Code RAM @ 0x800XXXXX
   - Overlay loadé depuis BLAZE.ALL
   - Utilise patterns d'instructions pour trouver l'offset
4. **Patch** le binaire BLAZE.ALL à cet offset
5. **Test** si ça marche

---

## Prochaines Étapes

1. Lance DuckStation avec cette version
2. Debug selon ce guide
3. **Rapporte:**
   - PC bloqué
   - Instructions autour
   - Registres
   - Type de boucle (A ou B)
4. On créera le patch ensemble

**Bonne chance!** 🎮🔧
