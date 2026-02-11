# EXE Damage Patch: 10% → 50%

## Vue d'ensemble

Patch appliqué directement dans l'exécutable PS1 (SLES_008.45) pour remplacer tous les dégâts de 10% par 50%.

## Pourquoi ce patch ?

Les **rochers tombants** (falling rocks) du Cavern of Death font 10% des PV max en dégâts. Après investigation exhaustive, cette valeur de 10% n'a **pas pu être localisée** dans BLAZE.ALL :

- ❌ Pas dans le descripteur d'entité (0x009ECFEC)
- ❌ Pas codé en dur dans le code overlay
- ❌ Pas dans les arguments stack
- ❌ Pas dans les tables de données entité

La seule solution viable est de **modifier la fonction de dégâts dans l'EXE** pour intercepter et remplacer 10→50.

## Implémentation technique

### Fonction ciblée

**RAM:** `0x80024F90` (damage calculation function)
**EXE offset:** `0x00015790` (file offset avec header 0x800)
**BIN offset:** `0x295F6858` (LBA 295081 × 2352 + 24 + offset)

### Code MIPS injecté

Au début de la fonction de dégâts, insertion de :

```mips
addiu $v0, $zero, 10       ; 0x3402000A - Load 10 into $v0
bne   $a3, $v0, skip       ; 0x14E20002 - If damage% != 10, skip
nop                        ; 0x00000000 - Branch delay slot
addiu $a3, $zero, 50       ; 0x34070032 - Replace damage% with 50
skip:
(original first instruction moved here)
```

**Registres utilisés:**
- `$a3` (reg 7) : contient le `damage_param%` en entrée de fonction
- `$v0` (reg 2) : registre temporaire pour la comparaison

### Patch binaire

Remplace les 5 premiers mots (20 bytes) de la fonction :

| Offset | Original | Patched   | Description |
|--------|----------|-----------|-------------|
| +0x00  | 00000000 | 3402000A  | addiu $v0, $zero, 10 |
| +0x04  | 26310001 | 14E20002  | bne $a3, $v0, skip |
| +0x08  | 2A22000A | 00000000  | nop (delay slot) |
| +0x0C  | 1440FFCA | 34070032  | addiu $a3, $zero, 50 |
| +0x10  | 00111080 | 00000000  | Original 1st instr moved |

## Effets du patch

### ✓ Affectés (damage passe de 10% → 50%)

1. **Rochers tombants** (falling rocks) dans Cavern of Death
2. **Tous les autres pièges à 10%** dans le jeu (3 sites identifiés)
3. **Dégâts environnementaux à 10%** (si existants)

### ✗ Non affectés

- Pièges à 2%, 5%, 20% : non modifiés (patchés séparément via BLAZE.ALL)
- Dégâts de combat : ne passent pas par cette fonction
- Dégâts de sorts : système séparé

## Intégration au build

**Étape:** 9d (après injection BLAZE.ALL dans le BIN)
**Script:** `Data/trap_damage/patch_damage_10_to_50_exe.py`
**Config:** Aucune (patch hardcodé)
**Statut:** **ACTIVÉ par défaut**

### Ordre d'exécution

```
Step 8:  Copier BIN clean → output/Blaze & Blade - Patched.bin
Step 9:  Injecter BLAZE.ALL dans le BIN
Step 9d: Patcher EXE damage function (10% → 50%)  ← CE PATCH
Step 10: Update docs
```

## Limitations

1. **Granularité limitée** : Affecte TOUS les dégâts à 10%, pas seulement les rochers
2. **Pas de config** : La valeur 50% est hardcodée dans le patch
3. **Fragile** : Si la fonction de dégâts change d'adresse, le patch casse

## Comment désactiver

Commenter la section dans `build_gameplay_patch.bat` :

```batch
REM ========================================================================
REM Step 9d: Patch EXE damage function (10% -> 50%)
REM ========================================================================
REM call :log "[9d/10] Patching EXE damage function (10%% -^> 50%%)..."
REM call :log ""
REM
REM py -3 Data\trap_damage\patch_damage_10_to_50_exe.py >> "%LOGFILE%" 2>&1
REM ...
```

## Tests recommandés

1. **Falling rocks** : Se faire toucher dans Cavern of Death → ~50% HP
2. **Autres pièges 10%** : Vérifier dans d'autres donjons
3. **Pièges 2%/5%** : Vérifier qu'ils sont toujours à 10%/22% (patch BLAZE.ALL)
4. **Combat** : Vérifier que les dégâts de combat normaux sont inchangés

## Historique

- **2026-02-11** : Création du patch EXE (solution après échec de localisation dans BLAZE.ALL)
- **Investigation** : 3 jours de recherche dans BLAZE.ALL, descripteurs, overlays, stack args
- **Conclusion** : Valeur 10% probablement hardcodée dans EXE ou calculée dynamiquement

## Voir aussi

- `RESEARCH.md` : Investigation complète des dégâts de pièges
- `patch_trap_damage.py` : Patch BLAZE.ALL pour 2%, 5%, 20%
- `trap_damage_config.json` : Config des patches BLAZE.ALL
