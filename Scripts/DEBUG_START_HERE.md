# 🎯 Debugging PSX - START HERE

Bienvenue dans le système de debugging pour Blaze & Blade!

## 📋 Checklist de Démarrage Rapide

- [ ] 1. Télécharger **DuckStation** (dev build avec debugger)
- [ ] 2. Activer la console: Settings → Console → Enable Dev Console
- [ ] 3. Charger le patch: `output/BLAZE.ALL.cue`
- [ ] 4. Ouvrir console: **Ctrl+`**
- [ ] 5. Générer breakpoints: `python Scripts/breakpoint_helper.py`
- [ ] 6. Copier/coller dans la console
- [ ] 7. Sauvegarder un savestate AVANT l'événement à tester
- [ ] 8. Tester et observer!

---

## 📂 Fichiers à Connaître

### Guides Principaux
1. **`DEBUGGING_GUIDE.md`** ← LIRE EN PREMIER
   - Configuration complète DuckStation/PCSX-Redux
   - Breakpoints, watchpoints, techniques
   - Addresses importantes

2. **`DEBUG_CHEAT_SHEET.md`** ← RÉFÉRENCE RAPIDE
   - Commandes les plus courantes
   - Workflows ultra-rapides
   - Calculateurs d'adresses

3. **`console_commands_reference.md`** ← RÉFÉRENCE COMPLÈTE
   - Toutes les commandes console
   - Syntax détaillée
   - Exemples avancés

4. **`CODE_PATTERNS.md`** ← POUR REVERSE ENGINEERING
   - Reconnaissance de patterns MIPS
   - Comment chercher dans le disassembly
   - Patterns spécifiques Blaze & Blade

### Workflows Détaillés
- **`debug_spells_workflow.md`** - Debugger le spell system (complet)
- **`debug_sessions/spell_research.txt`** - Session prête à l'emploi
- **`debug_sessions/trap_damage.txt`** - Session pour trap damage
- **`debug_sessions/chest_timer.txt`** - Session pour chest timer

### Outils
- **`breakpoint_helper.py`** - Générateur de commandes de breakpoints
  ```bash
  python Scripts/breakpoint_helper.py --mode spells
  ```

---

## 🚀 3 Workflows pour Démarrer

### Workflow 1: "Je veux voir quand un Shaman cast"
```bash
# 1. Générer les breakpoints
python Scripts/breakpoint_helper.py --mode spells

# 2. Dans DuckStation:
#    - Charger output/BLAZE.ALL.cue
#    - Ctrl+` (ouvrir console)
#    - Copier/coller: break 0x80024494
#    - Aller à Cavern F1 A1
#    - F2 (sauvegarder "shaman_test")
#    - Entrer en combat
#    - Quand ça break: taper 'regs'
#    - Noter $a0 (entity), $a1 (spell_id?)
```

### Workflow 2: "Je veux tracer le bitmask spell"
```bash
# 1. Suivre Workflow 1 pour trouver l'entity pointer (ex: 0x800B2100)

# 2. Générer watchpoints
python Scripts/breakpoint_helper.py \
  --entity-base 0x800B2100 \
  --entity-fields bitmask

# 3. Dans DuckStation:
#    - Copier/coller: watch 0x800B2260 rw
#    - F1 (recharger "shaman_test")
#    - Continue
#    - Observer chaque accès au bitmask!
```

### Workflow 3: "Je veux comparer vanilla vs modded"
```bash
# 1. Test vanilla
#    - Charger vanilla BLAZE.ALL
#    - break 0x80024494
#    - F2 "vanilla"
#    - Trigger → noter les valeurs
#    - Screenshot des registres

# 2. Test modded
#    - Charger patched BLAZE.ALL
#    - break 0x80024494
#    - F2 "modded"
#    - Trigger → noter les valeurs
#    - Screenshot des registres

# 3. Comparer les screenshots
```

---

## 🎓 Progression d'Apprentissage

### Niveau 1: Débutant
✅ Poser un breakpoint simple
✅ Voir les registres avec `regs`
✅ Continuer l'exécution avec `continue`
✅ Sauvegarder/charger savestates

**Lire:** `DEBUGGING_GUIDE.md` sections 1-2

### Niveau 2: Intermédiaire
✅ Watchpoints sur la mémoire
✅ Step through avec `step` et `next`
✅ Dump mémoire avec `dump`
✅ Calculer des adresses entity+offset

**Lire:** `DEBUG_CHEAT_SHEET.md` + `debug_spells_workflow.md`

### Niveau 3: Avancé
✅ Backtracer des appels de fonctions
✅ Reconnaître les patterns de code
✅ Tracer des structures complexes
✅ Conditional breakpoints (PCSX-Redux)

**Lire:** `CODE_PATTERNS.md` + `console_commands_reference.md`

---

## 🛠️ Aide-Mémoire Ultra-Rapide

### Commandes Essentielles (Top 10)
```bash
break <addr>        # Breakpoint d'exécution
watch <addr> rw     # Watchpoint lecture/écriture
regs                # Afficher registres
dump <addr> <len>   # Dump mémoire
step                # 1 instruction (step into)
next                # 1 instruction (step over)
continue            # Reprendre
breakpoints         # Lister les BPs
delete <id>         # Supprimer un BP
clear               # Supprimer tous les BPs
```

### Addresses Top 5 (à retenir)
```
0x80024F90    damage_function (EXE)
0x80024494    spell_dispatch (EXE)
0x800244F4    level_sim_loop (EXE)
0x800B1E80    entity_array (runtime)
0x800F014C    player_0_hp (runtime)
```

### Registres Top 5 (à surveiller)
```
$a0-$a3       Arguments de fonction
$v0-$v1       Return values
$s1           Entity pointer (TRÈS COURANT!)
$ra           Return address (backtracing)
$pc           Program counter (où on est)
```

---

## 🎯 Cas d'Usage Courants

| Objectif | Breakpoint | Registres Clés | Voir Aussi |
|----------|------------|----------------|------------|
| Spell casting | `0x80024494` | `$a0`=entity, `$a1`=spell_id? | `debug_spells_workflow.md` |
| Damage calc | `0x80024F90` | `$a3`=damage%, `$a1`=max_hp | `debug_sessions/trap_damage.txt` |
| Bitmask spell | `0x800244F4` | `$s1`=entity, voir entity+0x160 | `debug_spells_workflow.md` |
| Entity init | `0x80021E68` | `$a0`=entity, voir entity+0x3C | `CODE_PATTERNS.md` section 2 |
| Chest timer | `0x800877F4` | `$s1`=entity, voir entity+0x14 | `debug_sessions/chest_timer.txt` |

---

## 🚨 Troubleshooting

### "Breakpoint ne s'active jamais"
- ✅ Vérifier l'adresse (EXE vs overlay)
- ✅ Vérifier que l'événement est bien triggeré in-game
- ✅ Essayer un watchpoint large: `watch 0x800B0000 rw`

### "Trop de breaks (watchpoint trop actif)"
- ✅ Affiner l'adresse (watchpoint sur field précis)
- ✅ Poser le watchpoint APRÈS l'init (pas au startup)
- ✅ Utiliser conditional breakpoint (PCSX-Redux)

### "Je ne sais pas quelle entity surveiller"
- ✅ Poser BP sur l'action (ex: spell_dispatch)
- ✅ Regarder `$a0` ou `$s1` pour trouver l'entity pointer
- ✅ Calculer les offsets depuis ce pointer

### "Les registres changent trop vite"
- ✅ F2 (savestate) juste avant l'événement
- ✅ Recharger et réessayer autant de fois que nécessaire
- ✅ Noter les valeurs importantes au fur et à mesure

---

## 📞 Support

### Documentation Complète
1. `DEBUGGING_GUIDE.md` - Setup et configuration
2. `console_commands_reference.md` - Référence commandes
3. `CODE_PATTERNS.md` - Patterns MIPS
4. `DEBUG_CHEAT_SHEET.md` - Commandes rapides

### Exemples Pratiques
1. `debug_spells_workflow.md` - Workflow complet spell research
2. `debug_sessions/*.txt` - Sessions prêtes à l'emploi

### Outils
1. `breakpoint_helper.py` - Générateur de breakpoints
   ```bash
   python Scripts/breakpoint_helper.py --help
   ```

### Mémoire du Projet
- `memory/MEMORY.md` - Toutes les adresses confirmées in-game
- `Data/formations/SPELL_SYSTEM_CONFIRMED.md` - Spell system découvertes
- `Data/LootTimer/RESEARCH.md` - Chest timer research
- `Data/trap_damage/RESEARCH.md` - Trap damage research

---

## 🎉 Prêt à Démarrer!

### Next Steps
1. ✅ Lire `DEBUGGING_GUIDE.md` (15 minutes)
2. ✅ Télécharger DuckStation dev build
3. ✅ Essayer Workflow 1 (voir un Shaman cast)
4. ✅ Référer à `DEBUG_CHEAT_SHEET.md` quand besoin

**Bonne chance avec votre recherche! 🚀**

---

*Dernière mise à jour: 2026-02-12*
