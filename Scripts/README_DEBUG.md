# Scripts de Debugging - Index

Ce dossier contient tous les outils et guides pour debugger Blaze & Blade sur émulateur PSX.

---

## 🎯 Par où commencer?

**→ `DEBUG_START_HERE.md`** ← COMMENCER ICI!

Guide de démarrage complet avec checklist, workflows rapides et progression.

---

## 📚 Guides de Référence

### Guides Principaux
| Fichier | Description | Quand l'utiliser |
|---------|-------------|------------------|
| **`DEBUGGING_GUIDE.md`** | Guide complet: setup, breakpoints, watchpoints, techniques | Configuration initiale + référence complète |
| **`DEBUG_CHEAT_SHEET.md`** | Commandes rapides, workflows ultra-courts | Usage quotidien, référence rapide |
| **`console_commands_reference.md`** | Référence exhaustive commandes DuckStation/PCSX-Redux | Quand vous cherchez une commande spécifique |
| **`CODE_PATTERNS.md`** | Reconnaissance de patterns MIPS, reverse engineering | Analyse de disassembly, recherche de fonctions |

### Workflows Détaillés
| Fichier | Description | Durée |
|---------|-------------|-------|
| **`debug_spells_workflow.md`** | Workflow complet pour recherche spell system | 30-60 min |

---

## 🛠️ Outils

### `breakpoint_helper.py`
Générateur automatique de commandes de breakpoints pour DuckStation.

**Usage:**
```bash
# Tous les breakpoints
python Scripts/breakpoint_helper.py

# Mode spécifique
python Scripts/breakpoint_helper.py --mode spells
python Scripts/breakpoint_helper.py --mode combat
python Scripts/breakpoint_helper.py --mode trap

# Watchpoints entity (après avoir trouvé l'adresse base)
python Scripts/breakpoint_helper.py \
  --entity-base 0x800B2100 \
  --entity-fields bitmask timer level

# Watchpoints player
python Scripts/breakpoint_helper.py \
  --player 0 \
  --player-fields cur_hp max_hp level
```

**Modes disponibles:**
- `all` - Tous les breakpoints (défaut)
- `combat` - Combat system (damage, spells)
- `entity` - Entity system (init, array)
- `player` - Player data (HP, level)
- `cavern` - Cavern F1 A1 spécifique
- `spells` - Spell system
- `trap` - Trap damage

---

## 📁 Sessions Pré-Configurées

Dossier: **`debug_sessions/`**

Fichiers texte prêts à copier/coller dans la console DuckStation.

| Fichier | Objectif |
|---------|----------|
| **`spell_research.txt`** | Recherche spell system (suffix → spell_list) |
| **`trap_damage.txt`** | Trouver trap damage values (falling rock 10%) |
| **`chest_timer.txt`** | Observer chest despawn timer |

**Usage:**
1. Ouvrir le fichier `.txt`
2. Copier les commandes `break` et `watch`
3. Coller dans DuckStation console (Ctrl+`)
4. Suivre les instructions dans le fichier

---

## 🗂️ Structure Complète

```
Scripts/
├── DEBUG_START_HERE.md              ← COMMENCER ICI
├── README_DEBUG.md                  ← Ce fichier (index)
│
├── DEBUGGING_GUIDE.md               Guide complet (setup + référence)
├── DEBUG_CHEAT_SHEET.md            Commandes rapides
├── console_commands_reference.md    Référence exhaustive commandes
├── CODE_PATTERNS.md                 Patterns MIPS + reverse engineering
│
├── debug_spells_workflow.md         Workflow détaillé spell research
│
├── breakpoint_helper.py             Générateur de breakpoints
│
└── debug_sessions/                  Sessions pré-configurées
    ├── spell_research.txt           Spell system
    ├── trap_damage.txt              Trap damage
    └── chest_timer.txt              Chest timer
```

---

## 📖 Guide de Lecture Recommandé

### Débutant (Jour 1)
1. ✅ `DEBUG_START_HERE.md` (10 min)
2. ✅ `DEBUGGING_GUIDE.md` sections 1-2 (15 min)
3. ✅ Essayer Workflow 1 in-game (30 min)
4. ✅ Référer à `DEBUG_CHEAT_SHEET.md` quand besoin

### Intermédiaire (Semaine 1)
1. ✅ `debug_spells_workflow.md` complet (1h)
2. ✅ `console_commands_reference.md` sections pertinentes
3. ✅ Utiliser `breakpoint_helper.py` pour différents modes
4. ✅ Essayer les 3 sessions pré-configurées

### Avancé (Semaine 2+)
1. ✅ `CODE_PATTERNS.md` complet
2. ✅ Créer vos propres sessions de debug
3. ✅ Backtracing et pattern recognition
4. ✅ Conditional breakpoints (PCSX-Redux)

---

## 🎯 Cas d'Usage Rapide

### "Je veux debugger le spell system"
```bash
# 1. Lire
Scripts/debug_spells_workflow.md

# 2. Utiliser
python Scripts/breakpoint_helper.py --mode spells
# Ou copier/coller:
Scripts/debug_sessions/spell_research.txt
```

### "Je veux tracer un entity field"
```bash
# 1. Trouver l'entity base address avec un breakpoint
break 0x80024494
# → noter $a0 ou $s1

# 2. Générer watchpoints
python Scripts/breakpoint_helper.py \
  --entity-base <ADDR_TROUVÉE> \
  --entity-fields bitmask timer level
```

### "Je veux chercher un pattern de code"
```bash
# 1. Lire
Scripts/CODE_PATTERNS.md

# 2. Utiliser les patterns pour identifier le code
# 3. Poser breakpoints aux endroits clés
```

### "Je ne sais pas par où commencer"
```bash
# 1. LIRE
Scripts/DEBUG_START_HERE.md

# 2. Suivre la checklist de démarrage
```

---

## 🔗 Liens Externes

### Émulateurs
- [DuckStation](https://github.com/stenzek/duckstation) - Recommandé pour debugging actif
- [PCSX-Redux](https://github.com/grumpycoders/pcsx-redux) - Pour debugging avancé

### Documentation PSX
- [PSX-SPX](https://psx-spx.consoledev.net/) - Référence complète hardware PSX
- [MIPS Reference](https://www.mips.com/products/architectures/mips32-2/) - Architecture MIPS

---

## 📝 Notes

### Addresses Importantes (Mémoire)
Voir `C:\Users\Ben\.claude\projects\D--projets-Bab-Gameplay-Patch\memory\MEMORY.md` pour:
- Toutes les adresses confirmées in-game
- Entity struct layout
- Player struct layout
- Formation record format

### Recherches en Cours
- `WIP/spell_sets_and_ai/` - Spell sets per-formation
- `Data/formations/SPELL_SYSTEM_CONFIRMED.md` - Découvertes spell system
- `Data/trap_damage/RESEARCH.md` - Trap damage research (falling rock 10% UNSOLVED)

---

## 🆘 Besoin d'Aide?

### Problème Technique
1. Consulter `console_commands_reference.md` section "Troubleshooting"
2. Relire `DEBUGGING_GUIDE.md` section pertinente
3. Vérifier les addresses dans `memory/MEMORY.md`

### Recherche Bloquée
1. Consulter `CODE_PATTERNS.md` pour identifier le pattern
2. Essayer une approche différente (breakpoint vs watchpoint)
3. Comparer vanilla vs modded (voir `DEBUG_CHEAT_SHEET.md` Workflow W5)

### Commande Inconnue
1. Chercher dans `console_commands_reference.md`
2. Ou dans `DEBUG_CHEAT_SHEET.md` section "Commandes Essentielles"

---

*Dernière mise à jour: 2026-02-12*
