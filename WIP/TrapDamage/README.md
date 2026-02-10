# Trap Damage Research & Patching

## Objective
Identify and modify trap/environmental damage values in Blaze & Blade.

## Known Traps
- **Cavern of Death**: Falling rocks from ceiling
- **Tower of Illusion**: Toxic floor zones (poison/continuous damage)
- **Castle of Devil**: Crushing walls

## Key Discovery

Trap damage is applied via **overlay code** in BLAZE.ALL, calling the stat modifier function `0x8008A3E4(entity, delta1, delta2, delta3)`. Found 32 damage callers (negative args) in the Cavern overlay region.

## Files

### Research Scripts (WIP)
| File | Description |
|------|-------------|
| `dump_deep_region.py` | Phase 1.1: Deep entity region dump (dead end for traps) |
| `compare_trap_zones.py` | Phase 1.2: Overlay-to-zone mapping attempt |
| `search_exe_damage.py` | Phase 2.1: EXE/overlay damage pattern search |
| `analyze_damage_function.py` | Phase 2.2: Stat modifier function analysis |
| `test_trap_modify.py` | Phase 3.1: Test modification (NOP or multiply) |

### Production Files
| File | Description |
|------|-------------|
| `Data/trap_damage/trap_damage_config.json` | Configuration |
| `Data/trap_damage/patch_trap_damage.py` | Build patcher (step 7d) |

## Configuration

```json
{
  "enabled": true,
  "mode": "multiply",
  "damage_multiplier": 2.0
}
```

Modes:
- `"multiply"` - Scale all negative damage values by `damage_multiplier`
- `"nop"` - Disable all damage calls entirely (for testing)

## Status
- Research: COMPLETE (function identified, callers found)
- Patcher: COMPLETE (integrated in build pipeline as step 7d)
- Testing: PENDING (needs in-game validation)
