# AI Behavior Modification System

**Status:** ⚠️ EXPERIMENTAL - Hypotheses based on data analysis, not yet tested in-game

---

## 📋 What This System Does

Allows modification of **monster behavior parameters** including:
- ⚔️ Attack speed (how fast monsters attack)
- 🏃 Responsiveness (how quickly monsters react)
- 👁️ Aggro range (detection distance)
- 🎯 Attack range (attack distance)

---

## 🚀 Quick Start

### 1. Edit Configuration

```bash
Data/ai_behavior/behavior_block_config.json
```

Enable a test patch:
```json
{
  "enabled": true,
  "zone": "Castle F1 Area1",
  "L": 2,
  "monster_name": "Zombie",
  "modifications": {
    "timer_04": 800,   // Faster attacks (vanilla: 1948)
    "timer_08": 800    // More responsive (vanilla: 2016)
  }
}
```

### 2. Run Patcher

```bash
py -3 Data\ai_behavior\patch_behavior_blocks.py
```

### 3. Build and Test

```bash
build_gameplay_patch.bat
```

Load `output/Blaze & Blade - Patched.bin` and test in Castle F1.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `behavior_block_config.json` | **Edit this** - Behavior modification settings |
| `patch_behavior_blocks.py` | **Run this** - Applies modifications to BLAZE.ALL |
| `BEHAVIOR_MODDING_GUIDE.md` | Complete usage guide with examples |
| `README.md` | This file |

---

## 🎯 What Can Be Modified

### ✅ Working Monsters (7 analyzed)

| Monster | Zone | Attack Type | Can Modify |
|---------|------|-------------|------------|
| Lv20.Goblin | Cavern F1 A1 | Ground melee | ✅ Yes |
| Giant-Bat | Cavern F1 A1 | Flying | ✅ Yes |
| Zombie | Castle F1 A1 | Slow heavy | ✅ Yes |
| Harpy | Castle F1 A1 | Flying melee | ✅ Yes |
| Wolf | Castle F1 A1 | Fast aggro | ✅ Yes |
| Blue-Slime | Cavern F7 A1 | Passive | ✅ Yes |
| Spirit-Ball | Cavern F7 A1 | Floating | ✅ Yes |

### ❌ NULL Behavior Blocks (Cannot Modify Yet)

| Monster | Zone | Why |
|---------|------|-----|
| Goblin-Shaman | Cavern F1 A1 | Uses default/shared behavior |
| Cave-Bear | Cavern F7 A1 | Uses default/shared behavior |
| Ogre | Cavern F7 A1 | Uses default/shared behavior |

---

## 🔧 Modifiable Fields

### High Confidence

| Field | Function | Example |
|-------|----------|---------|
| **timer_04** | Attack cooldown | Lower = faster attacks |
| **timer_08** | AI decision interval | Lower = more responsive |
| **dist_0E** | Attack range | 2048=melee, higher=longer range |

### Medium Confidence

| Field | Function | Example |
|-------|----------|---------|
| **dist_0C** | Aggro range | Higher = aggro from farther |

### Confirmed

| Field | Function | Example |
|-------|----------|---------|
| **flags_02** | Movement type | 21=flying, 0=ground |

---

## ⚠️ Important Warnings

### 🔬 Experimental Status

**ALL field functions are hypotheses** based on data pattern analysis.
**NO in-game testing has been done yet.**

### ⚡ Unknown Units

- **Timer units:** Unknown (frames? frames/10?)
- **Distance units:** Unknown (2048 = standard melee, but actual scale unclear)

**Recommendation:** Start with small changes (±20-30%) and test.

### 🚨 Limitations

1. **Cannot modify NULL behavior monsters** (Shaman, Bear, Ogre, etc.)
2. **Changes apply to ALL instances** of a monster type in a zone
3. **No per-instance differentiation** yet
4. **Extreme values may crash** (setting to 0 or 65535)

---

## 📚 Documentation

### For Users
- **BEHAVIOR_MODDING_GUIDE.md** - Complete guide with templates and examples

### For Researchers
- **WIP/behavior_analysis_report.md** - Detailed data analysis and hypotheses
- **Data/formations/Scripts/utils/dump_ai_blocks.py** - Extraction tool

---

## 🎯 Next Steps

### Immediate (Testing Phase)

1. ✅ Extract behavior blocks → **DONE**
2. ✅ Analyze patterns → **DONE**
3. ✅ Create patcher → **DONE**
4. ⏳ **YOU ARE HERE** → Test modifications in-game
5. ⏳ Measure actual effects
6. ⏳ Refine hypotheses based on results

### Future (Research Phase)

1. Determine actual timer/distance units
2. Decode remaining unknown fields (val_10-1E)
3. Find default behavior for NULL monsters
4. Implement per-instance modifications
5. Create behavior templates for common patterns

---

## 🐛 Troubleshooting

### "No visible effect"
- Try larger changes (50-80%)
- Test multiple fields
- Verify BIN injection worked

### "Game crashes"
- Use more conservative values
- Only modify proven fields
- Restore clean BLAZE.ALL

### "Monster has NULL behavior"
- Cannot modify yet
- Requires advanced overlay patching

---

## 📊 Research Data

### Analyzed Zones
- Cavern F1 Area1 (3 monsters)
- Cavern F7 Area1 (4 monsters)
- Castle F1 Area1 (3 monsters)

### Decoded Fields
- 2 CONFIRMED (flags_02, dist_0E)
- 3 HIGH confidence (timer_04, timer_08, dist_0C)
- 11 UNKNOWN (timer_06, timer_0A, val_10-1E)

---

## 🤝 Contributing

If you test modifications, please document:
- Field tested
- Vanilla value
- Modified value
- Measured effect in-game
- Conclusions

Add results to `behavior_block_config.json` under `_tested_modifications`.

---

**Created:** 2026-02-13
**Version:** 1.0 (Experimental)
**Status:** Ready for in-game testing
