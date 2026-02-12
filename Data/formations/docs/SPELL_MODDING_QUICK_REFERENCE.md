# Spell Modding - Quick Reference Guide

**Date:** 2026-02-12

---

## TL;DR

Formation records use a **TWO-LAYER system** to control monsters:

1. **byte[8]** = Entity type (visual, stats, AI)
2. **byte[0:4]** = Spell modifier (changes available spells)

**You can mix and match:** Shaman entity + Bat spell modifier = Shaman with FireBullet! ✅ Confirmed in-game.

---

## Spell Modifier Values (slot_types)

| Value      | Found On              | Effect (when applied to Shaman) | Status    |
|------------|-----------------------|---------------------------------|-----------|
| 00000000   | Goblin, base monsters | ? (testing)                     | ⏳ Testing |
| 02000000   | Goblin-Shaman         | Sleep                           | ✅ Confirmed |
| 03000000   | Tower Shaman variant  | ? (testing)                     | ⏳ Testing |
| 00000a00   | Bat, Ghost, Wraith    | **FireBullet**                  | ✅ Confirmed |
| 00000100   | Arch-Magi, rare Bats  | ? (not tested)                  | 📋 Queue  |

---

## Current Tests (Awaiting Results)

**Location:** Cavern of Death, Floor 1, Area 1

### Formation 0
- **Monsters:** 3x Shaman (byte[8]=0x01)
- **Modifier:** 00000000 (Goblin base)
- **Question:** Do Shamans lose spells? Or different set?

### Formation 1
- **Monsters:** 3x Shaman (byte[8]=0x01)
- **Modifier:** 03000000 (Tower variant)
- **Question:** What spell set does this rare value give?

### Formation 2
- **Monsters:** 3x Goblin (byte[8]=0x00)
- **Modifier:** 02000000 (Shaman set)
- **Question:** **Can Goblins cast Sleep?!** 🤯

---

## How to Test In-Game

1. Load `output\Blaze & Blade - Patched.bin`
2. Go to **Cavern Floor 1 Area 1**
3. Trigger each formation (wander until encounter)
4. Enter combat
5. Check spell menu for each monster type
6. Document ALL spells (not just changes)

---

## Quick Test Script

Use `test_slot_types_comprehensive.py` to apply current tests:

```bash
cd Data/formations
py -3 test_slot_types_comprehensive.py
# Answer 'o' to confirm

# Then inject:
cd ../..
py -3 patch_blaze_all.py
```

---

## To Mod Spells Yourself

### Method 1: Edit Formation JSON

1. Open `Data/formations/<level>/<area>.json`
2. Find the `slot_types` array
3. Change the value for your desired monster slot
4. Build and test

**Example:** Give all Shamans FireBullet
```json
"slot_types": [
  "00000000",  // Slot 0: Goblin
  "00000a00",  // Slot 1: Shaman (CHANGED from 02000000)
  "00000a00"   // Slot 2: Bat
]
```

### Method 2: Quick Python Patch

```python
from pathlib import Path

BLAZE_ALL = Path("output/BLAZE.ALL")
SHAMAN_RECORD_OFFSET = 0xF7B09C  # Example offset

with open(BLAZE_ALL, 'r+b') as f:
    data = bytearray(f.read())
    # Change byte[0:4] to desired spell modifier
    data[SHAMAN_RECORD_OFFSET:SHAMAN_RECORD_OFFSET+4] = bytes.fromhex("00000a00")
    f.seek(0)
    f.write(data)
```

---

## Known Combinations (Confirmed)

| Entity (byte[8]) | Modifier (byte[0:4]) | Result                  | Tested |
|------------------|----------------------|-------------------------|--------|
| Shaman (0x01)    | 02000000             | Sleep (vanilla)         | ✅     |
| Shaman (0x01)    | 00000a00             | FireBullet (from Bat)   | ✅     |
| Shaman (0x01)    | 00000000             | ? (testing)             | ⏳     |
| Shaman (0x01)    | 03000000             | ? (testing)             | ⏳     |
| Goblin (0x00)    | 02000000             | ? (testing)             | ⏳     |

---

## Important Notes

- ✅ System works **PER-FORMATION** (not global)
- ✅ Same monster in different formations can have different spells
- ✅ Visual/stats/AI stay correct (controlled by byte[8])
- ✅ Only spell list changes (controlled by byte[0:4])
- ⚠️ Value 00000000 is NOT "no spells" (Trent/Wisp cast with this!)

---

## Full Documentation

- **Research:** `SPELL_MODIFIER_RESEARCH.md` - Complete findings and analysis
- **Discovery:** `SPELL_SYSTEM_DISCOVERY.md` - Original discovery and protocols
- **Memory:** `memory/MEMORY.md` - Formation Patcher section

---

## Next Steps

1. ⏳ Test current 3 formations in Cavern F1 A1
2. 📋 Document all spell lists for each test
3. 📋 Build complete spell modifier table
4. 📋 Test rare values (00000100, etc.)
5. 📋 Test on other entity types (Bat, Ghost, Trent)
6. 📋 Create spell set database for modding

---

**Status:** 1/3 tests confirmed, 2/3 awaiting in-game results
**Updated:** 2026-02-12
