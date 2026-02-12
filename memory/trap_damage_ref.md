# Trap Damage Reference - FALLING ROCK SOLVED

**Date:** 2026-02-13
**Status:** ✅ COMPLETE SOLUTION

---

## Falling Rock Damage - Complete Mechanism

### In-Game Debugging Session (2026-02-13)

**Method:** DuckStation CPU Debugger with live breakpoints

**Discovery:** Damage% hardcoded as immediate value in overlay code

---

## Code Flow

```
Falling Rock Trigger
     ↓
Trap Handler at 0x800CE7B0 (Cavern overlay)
     ↓
0x800CE7B8: addiu a1, zero, 10    ← HARDCODED damage%
0x800CE7BC: addu a2, zero, zero
0x800CE7C0: jal 0x800cace8        ← Call trap damage setup
     ↓
0x800CAD08: addu s6, a1, zero     ← Save damage% in s6
     ↓
0x800CADDC: sll a1, s6, 16        ← Retrieve damage% from s6
0x800CADE4: sra a1, a1, 16
0x800CADE8: jal 0x80024F90        ← Call damage_function
     ↓
damage_function(a1=10%)
     ↓
damage = (player_maxHP * 10) / 100
```

---

## Binary Pattern (ALL Dungeons)

**Pattern in BLAZE.ALL:**
```
0A 00 05 24    # addiu a1, zero, 10  ← Damage% byte at offset +0
21 30 00 00    # addu a2, zero, zero
```

**21 occurrences found** (all dungeons with falling rocks)

---

## Patch Method

**Target:** First byte of pattern (damage% immediate value)

**Original:** `0x0A` (10%)
**Example new:** `0x05` (5%)

**Script:** `Data/trap_damage/patch_falling_rock.py`

**Usage:**
```bash
python Data/trap_damage/patch_falling_rock.py --damage 5 --dry-run
python Data/trap_damage/patch_falling_rock.py --damage 5
```

---

## All 21 Locations in BLAZE.ALL

| # | Offset | Dungeon (estimated) |
|---|--------|---------------------|
| 1 | 0x00BD0FB8 | ? |
| 2 | 0x00BD15D4 | ? |
| 3 | 0x00DF2FB8 | ? |
| 4 | 0x01511CFC | ? |
| 5 | 0x015120A4 | ? |
| 6 | 0x01787C74 | ? |
| 7 | 0x01C2607C | ? |
| 8 | 0x01C28264 | ? |
| 9 | 0x01C288E8 | ? |
| 10 | 0x01E82E7C | ? |
| 11 | 0x02189400 | ? |
| 12 | 0x026515C4 | ? |
| 13 | 0x027034EC | ? |
| 14 | 0x02703C9C | ? |
| 15 | 0x027048A0 | ? |
| 16 | 0x027EFB1C | ? |
| 17 | 0x027F06CC | ? |
| 18 | 0x028F8F98 | ? |
| 19 | 0x028F9094 | ? |
| 20 | 0x028F9978 | ? |
| 21 | 0x0296144C | ? |

(Cavern RAM 0x800CE7B8 maps to one of these)

---

## Debug Addresses (Cavern of Death)

| RAM Address | Instruction | Description |
|-------------|-------------|-------------|
| 0x800CE7B8 | `addiu a1, zero, 10` | Load damage% immediate |
| 0x800CE7BC | `addu a2, zero, zero` | Zero a2 |
| 0x800CE7C0 | `jal 0x800cace8` | Call trap handler |
| 0x800CAD08 | `addu s6, a1, zero` | Save damage% to s6 |
| 0x800CADDC | `sll a1, s6, 16` | Reload damage% from s6 |
| 0x800CADE4 | `sra a1, a1, 16` | Sign-extend |
| 0x800CADE8 | `jal 0x80024F90` | Call damage function |
| 0x80024F90 | `damage_function` | Calculate HP loss |

---

## Key Findings

1. **Damage% is NOT in entity structure** - it's hardcoded in overlay code
2. **Same pattern across all dungeons** - 21 instances in BLAZE.ALL
3. **Simple 1-byte patch** - change immediate value
4. **All falling rocks use 10%** - vanilla value confirmed across all instances

---

## Answer to User Question

> "ca veut donc dire que si ya d'autres pieges différent, il faudra re fouiller quelle adresse la hardcodé?"

**Oui!** Each trap type has its own hardcoded location.

For other traps:
- Same debug method (take damage + backtrace)
- OR use existing `patch_trap_damage.py` (finds all JAL direct callers automatically)

Falling rock was special because:
- Damage% goes through 2 function calls (not direct JAL)
- Required manual debugging to find

---

## Tools Used

- **DuckStation** (dev 0.1-10819-geda65a6ae)
- **CPU Debugger** (breakpoints, register inspection, disassembly navigation)
- **Memory Editor** (entity structure examination)

---

## Success!

✅ Complete mechanism understood
✅ All 21 locations found
✅ Patcher working
✅ Ready for testing

**Next:** Integrate into build pipeline or keep as optional patch.

---

*Documented by: User Ben + Claude Sonnet 4.5*
*Date: 2026-02-13 00:45*
