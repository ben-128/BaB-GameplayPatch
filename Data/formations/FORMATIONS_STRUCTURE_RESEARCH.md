# Formation Structure Research - Shaman FireBullet Bug

## Problème
Les Goblin-Shamans lancent **FireBullet** (spell de Bat) au lieu de **Sleep** après patch des formations.

## Tests effectués

### Test 1: byte[8] = slot_index
- **Hypothèse:** Le jeu lit `byte[8]` pour déterminer quel monstre spawner
- **Patch:** Records 5-6 ont `byte[8]=0x01` (Shaman)
- **Résultat:** ❌ Toujours FireBullet

### Test 2: byte[16:18] = XXff pattern
- **Hypothèse:** Le jeu lit `byte[16:18]` (format `XXff` où XX=slot)
- **Patch:** Records 5-6 ont `byte[16:18]=01ff` (Shaman)
- **Résultat:** ❌ Toujours FireBullet

## Hypothèse actuelle: Description complète vs Référence

### Modèle "Référence" (ce qu'on croyait)
```
Formation Record (32 bytes) = {
    slot_index: byte[X],  // Pointeur vers monsters[slot_index]
    coords: ...,
    flags: ...,
}

Quand monstre spawn:
    monster_data = area.monsters[record.slot_index]  // Lit depuis le slot
    spawn(monster_data)
```

### Modèle "Description complète" (hypothèse nouvelle)
```
Formation Record (32 bytes) = {
    model_id: ...,        // Quel mesh 3D
    ai_type: ...,         // Quel comportement AI
    spell_set: ...,       // Quels sorts disponibles
    stat_ref: ...,        // Référence aux stats (HP, dmg, etc.)
    texture_variant: ..., // Couleur/skin
    ... (tous les params nécessaires inline)
}

Quand monstre spawn:
    spawn(record)  // Toutes les données sont dans le record lui-même
```

## Analyse des bytes vanilla

### Formation 1 - Comparaison des records

#### Records 0-2 (Goblins - même monstre)
```
R0: 00000000ffffffff00ff0000000000000000000000000000dc01ffffffffffff
R1: 000000000000000000ff0000000000000000000000000000dc01ffffffffffff
R2: 000000000000000000ff0000000000000000000000000000dc01ffffffffffff
```

**Observation:** Records 1-2 sont IDENTIQUES. Record 0 diffère seulement par `byte[4:8]=ffffffff` (marqueur de début).

**Conclusion:** Pour le même monstre, les bytes sont identiques (sauf marqueurs structurels).

#### Record 6 (celui qui devrait être Shaman selon JSON)
```
R6: ffffffff0200000000000000ffffffff01ff0000000000000000000000000000
```

**Différences clés avec Goblin records:**
- `byte[0:4] = ffffffff` (au lieu de 00000000)
- `byte[4:8] = 02000000` (au lieu de 00000000 ou ffffffff)
- `byte[8] = 00` (pareil que Goblin)
- `byte[9] = 00` (au lieu de 0xFF)
- `byte[12:16] = ffffffff` (au lieu de 00000000)
- `byte[16:18] = 01ff` (unique!)

### Décomposition du Record 6 vanilla

```
Offset | Bytes            | Valeur (LE)  | Hypothèse
-------|------------------|--------------|---------------------------
0-3    | ffffffff         | -1           | Prefix/marker
4-7    | 02000000         | 0x00000002   | Type? Slot_type? MODEL_ID?
8      | 00               | 0            | ???
9      | 00               | 0            | Marker (00=formation, 0B=spawn, FF=???)
10-11  | 0000             | 0            | ???
12-15  | ffffffff         | -1           | Marker/separator?
16-17  | 01ff             | 0xFF01       | SPELL_SET_ID? AI_TYPE?
18-23  | 000000000000     | 0            | Coords/params
24-25  | 0000             | 0            | Area ID (normally dc01)
26-31  | 000000           | 0            | Terminator (normally ffffff)
```

### Formation 2 vanilla - Tous des Bats (slot 2)

```
R0: ffffffff020000000000000001ff0000000000000000000000000000dc01ffff
R1: ffffffff0200000000000000ffffffff02ff0000000000000000000000000000
R2: dc01ffffffffffff00000a000000000002ff0000000000000000000000000000
R3: dc01ffffffffffff00000a000000000002ff0000000000000000000000000000
R4: dc01ffffffffffff00000a000000000002ff0000000000000000000000000000
```

**Pattern byte[16:18]:**
- R0: `01ff` (devrait être Bat mais a pattern de Shaman?!)
- R1-4: `02ff` (Bat - cohérent)

**Pattern byte[4:8]:**
- R0-1: `02000000` (valeur 2)
- R2-4: `ffffffff` puis `dc01ffff` (marqueurs)

## Hypothèse affinée: Structure hybride

Les formation records semblent être une **structure hybride**:

1. **Certains bytes sont des marqueurs structurels** (FFFFFFFF, dc01, etc.)
2. **byte[4:8] pourrait encoder le TYPE/MODEL** quand != FFFFFFFF
3. **byte[16:18] pourrait encoder l'AI/SPELL_SET** (pattern XXff)
4. **Les records ne sont PAS tous des monstres individuels!**

### Structure possible de Formation 1 vanilla

```
Record 0: HEADER (byte[4:8]=FFFFFFFF)
Record 1-2: 2x Goblin (byte[16:18]=0000)
Record 3: SEPARATOR (byte[8]=FF)
Record 4-5: 2x ??? (byte[16:18]=0000, byte[9]=00)
Record 6: 1x QUELQUE CHOSE (byte[4:8]=02, byte[16:18]=01ff)
Suffix: dc01ffff
```

**Peut-être que ce n'est PAS "7 monstres"** mais une structure plus complexe avec:
- Headers/separators
- Groupes de monstres
- Descripteurs

## Extraction vanilla: ce que le jeu spawn VRAIMENT

L'utilisateur confirme: vanilla (sans patch) = **Shamans lancent Sleep**.

Donc il y a DÉFINITIVEMENT des Shamans qui spawnent. Mais notre analyse des bytes suggère:
- Formation 1 vanilla Record 6: byte[4:8]=0x02 (Bat?) byte[16:18]=01ff
- Formation 2 vanilla: plein de byte[16:18]=02ff (Bat)

**Questions non résolues:**
1. Où est encodé "Goblin-Shaman" dans les bytes vanilla?
2. Est-ce que byte[16:18]=01ff signifie "Shaman spell set" même si byte[4:8]=02 (Bat model)?
3. Est-ce que les formations ne sont PAS une liste plate de monstres mais une structure hiérarchique?

## Comparaison Spawn Points vs Formations

### Spawn Points (fonctionnent correctement)
```
Goblin: byte[8]=00 byte[9]=0B
Shaman: byte[8]=01 byte[9]=0B
```
→ Structure claire: byte[8]=slot_index, byte[9]=0x0B marker

### Formation Templates
```
Records avec byte[9]=0xFF: ???
Records avec byte[9]=0x00: ???
Suffix dc01ffff vs 00000000: ???
```
→ Structure COMPLÈTEMENT différente des spawn points!

## Action requise

1. **Test in-game vanilla extraction:** Spawner Formation 1 vanilla et noter:
   - Combien de monstres apparaissent?
   - Quels types (Goblin / Shaman / Bat)?
   - Quels sorts ils lancent?

2. **Reverse engineering complet:**
   - Trouver le code PSX qui LIT les formation records
   - Comprendre la vraie structure (peut-être pas 32 bytes fixes?)
   - Identifier tous les champs et leur signification

3. **Extracteur:** Le JSON extrait est peut-être complètement faux
   - `slots: [0,0,0,0,0,1,1]` ne correspond PAS aux bytes vanilla
   - Il faut réécrire l'extracteur en comprenant d'abord la structure

## Conclusion temporaire

Le patcher génère des bytes synthétiques qui ne correspondent PAS au format vanilla.
Le jeu ne comprend pas ces bytes → comportement aléatoire/incorrect (Shaman → FireBullet).

**La seule solution fiable est de PRÉSERVER les bytes vanilla exactement**,
et de ne modifier QUE les formations qu'on comprend parfaitement.
