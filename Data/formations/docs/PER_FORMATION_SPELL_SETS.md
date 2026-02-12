# Per-Formation Spell Sets - Documentation

## Changement majeur (2026-02-12)

Les **spell sets** (slot_types) sont maintenant gérés **PAR FORMATION** au lieu de globalement par area.

## Avant vs Après

### Avant (structure globale)
```json
{
  "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
  "slot_types": [
    "00000000",  // Tous les Goblins dans toutes les formations
    "02000000",  // Tous les Shamans dans toutes les formations
    "00000a00"   // Toutes les Bats dans toutes les formations
  ],
  "formations": [
    {"slots": [0, 0, 1, 1]},
    {"slots": [1, 1, 1]},
    {"slots": [2, 2, 2]}
  ]
}
```

**Problème:** Impossible d'avoir un Shaman avec Sleep dans Formation 0 et un Shaman avec FireBullet dans Formation 1.

### Après (structure par formation)
```json
{
  "monsters": ["Lv20.Goblin", "Goblin-Shaman", "Giant-Bat"],
  "formations": [
    {
      "slots": [0, 0, 1, 1],
      "slot_types": ["00000000", "02000000", "00000a00"]  // Sleep Shaman
    },
    {
      "slots": [1, 1, 1],
      "slot_types": ["00000000", "00000a00", "00000a00"]  // FireBullet Shaman!
    },
    {
      "slots": [2, 2, 2],
      "slot_types": ["00000000", "02000000", "00000a00"]  // Default
    }
  ]
}
```

**Avantage:** Chaque formation peut avoir des spell sets différents pour les mêmes monstres!

## Rétrocompatibilité

Les anciennes structures sont toujours supportées:

1. **slot_types global**: Si présent au niveau area, utilisé comme fallback
2. **Pas de slot_types**: Défaut à `00000000` pour tous les slots

```json
// Ancien format - toujours valide
{
  "slot_types": ["00000000", "02000000", "00000a00"],
  "formations": [
    {"slots": [0, 1, 2]}  // Pas de slot_types → utilise global
  ]
}

// Nouveau format - override par formation
{
  "slot_types": ["00000000", "02000000", "00000a00"],  // Fallback
  "formations": [
    {
      "slots": [0, 1, 2],
      "slot_types": ["00000000", "00000a00", "00000a00"]  // Override!
    }
  ]
}
```

## Interface Éditeur

### Foldout par formation

Chaque formation card a maintenant un foldout "Spell Sets":

```
┌─ Formation F00 ─────────────────┐
│ ☑ F00  7 slots  suffix:00000000 │
│ ◉ 5x Lv20.Goblin  ◉ 2x Shaman   │
│ [+/-] Controls...                │
│ ────────────────────────────────│
│ ▶ Spell Sets              [?]   │ ← Foldout + Tooltip
│ ────────────────────────────────│
│ [↑][↓][Duplicate][Delete]       │
└──────────────────────────────────┘
```

Cliquer sur "▶ Spell Sets" pour voir/éditer:

```
▼ Spell Sets              [?]
┌────────────────────────────────┐
│ Lv20.Goblin   [00000000] Base  │
│ Goblin-Shaman [02000000] Vanilla│
│ Giant-Bat     [00000a00] Flying │
└────────────────────────────────┘
```

### Bouton tooltip "?"

Cliquer sur **[?]** affiche une overlay avec toutes les valeurs confirmées:

```
╔═══════════════════════════════════╗
║ Valeurs de Spell Sets Confirmées ║
╠═══════════════════════════════════╣
║ 02000000 = Vanilla Shaman         ║
║   (Sleep / MM / Stone Bullet)     ║
║                                   ║
║ 03000000 = Tower Variant          ║
║   (Sleep / MM / Heal)             ║
║                                   ║
║ 00000a00 = Bat/Flying             ║
║   (FireBullet / MM / Stone Bullet)║
║                                   ║
║ 00000000 = Base/Goblin (varies)   ║
║                                   ║
║ 00000100 = Rare Variant (untested)║
║                                   ║
║        [Fermer]                   ║
╚═══════════════════════════════════╝
```

## Workflow d'édition

### 1. Éditer une formation spécifique

```bash
# 1. Lancer l'éditeur
cd Data/formations
edit_formations.bat

# 2. Sélectionner une area
# 3. Cliquer sur la formation à modifier
# 4. Ouvrir le foldout "Spell Sets"
# 5. Modifier les valeurs hex (validation automatique)
# 6. Sauvegarder le JSON
```

### 2. Copier des spell sets à toutes les formations

Si vous voulez que TOUTES les formations aient les mêmes spell sets, deux options:

**Option A - Global (recommandé si identique partout):**
```json
{
  "slot_types": ["00000000", "02000000", "00000a00"],
  "formations": [
    {"slots": [0, 1]},  // Pas de slot_types → utilise global
    {"slots": [1, 2]}   // Pas de slot_types → utilise global
  ]
}
```

**Option B - Per-formation (si variations futures prévues):**
Utiliser "Duplicate" dans l'éditeur pour copier les spell sets.

## Exemples pratiques

### Exemple 1: Shamans progressifs

Rendre les Shamans plus dangereux au fil des formations:

```json
{
  "monsters": ["Goblin", "Shaman", "Bat"],
  "formations": [
    {
      "slots": [0, 0, 1],
      "slot_types": ["00000000", "02000000", "00000000"]  // F0: Sleep
    },
    {
      "slots": [0, 1, 1],
      "slot_types": ["00000000", "03000000", "00000000"]  // F1: Heal support
    },
    {
      "slots": [1, 1, 1],
      "slot_types": ["00000000", "00000a00", "00000000"]  // F2: FireBullet!
    }
  ]
}
```

### Exemple 2: Formation boss

Formation finale avec sorts spéciaux:

```json
{
  "formations": [
    // ... formations normales ...
    {
      "slots": [1, 1, 1, 1, 1],  // 5 Shamans
      "slot_types": ["00000000", "00000a00", "00000a00"]  // Tous FireBullet!
    }
  ]
}
```

## Patcher (patch_formations.py)

Le patcher vérifie dans cet ordre:

1. **Formation a `slot_types`?** → Utilise ceux-là
2. **Area a `slot_types`?** → Utilise ceux-là (fallback)
3. **Rien?** → Utilise `00000000` (default)

Log du patcher:

```
[PATCH] Cavern of Death - Floor 1 - Area 1
    [INFO] F00: using formation slot_types (per-formation override)
    [INFO] F01: using global slot_types (fallback)
    [INFO] F02: using default slot_types (no override, no global)
```

## Validation

Le patcher vérifie:

- ✓ `slot_types` a la bonne longueur (= nombre de monsters)
- ✓ Chaque valeur est un hex string de 8 caractères
- ✓ Formation avec vanilla bytes → ignore slot_types (utilise bytes exacts)

## Notes importantes

1. **Vanilla bytes prioritaires**: Si une formation utilise `vanilla_records`, les `slot_types` sont ignorés (bytes vanilla déjà corrects)

2. **Fillers utilisent global**: Les formations filler (duplicate offsets) utilisent toujours les `slot_types` globaux

3. **Pas de migration automatique**: Les anciens JSONs gardent leur structure. Pour passer à per-formation, éditez manuellement.

4. **Backup**: L'éditeur crée des backups automatiques avant sauvegarde

## Références

- **SPELL_SYSTEM_CONFIRMED.md** - Liste complète des spell sets testés
- **README.md** - Guide d'utilisation général
- **editor.html** - Interface modifiée (lignes ~350-450)
- **patch_formations.py** - Logic de patching (lignes 319-350)
