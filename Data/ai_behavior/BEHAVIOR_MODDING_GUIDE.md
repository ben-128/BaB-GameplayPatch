# Behavior Block Modding Guide
**Version:** 1.0
**Date:** 2026-02-13
**Status:** EXPERIMENTAL - All hypotheses untested in-game

---

## 🎯 What You Can Modify

This system allows you to change:
- ⚔️ **Attack Speed** - How fast monsters attack
- 🏃 **Responsiveness** - How quickly monsters react to players
- 👁️ **Aggro Range** - How far monsters detect and chase players
- 🎯 **Attack Range** - How far monsters can attack from
- 🦅 **Movement Type** - Ground vs flying (experimental)

---

## 🚀 Quick Start

### 1. Enable a Test Patch

Edit `Data/ai_behavior/behavior_block_config.json`:

```json
{
  "behavior_patches": {
    "enabled": true,
    "patches": [
      {
        "_comment": "Speed up Zombie (test)",
        "enabled": true,  // ← Change this to true
        "zone": "Castle F1 Area1",
        "script_offset": 37745364,
        "L": 2,
        "monster_name": "Zombie",
        "modifications": {
          "timer_04": 800,   // Attack cooldown (vanilla: 1948)
          "timer_08": 800    // AI decision interval (vanilla: 2016)
        }
      }
    ]
  }
}
```

### 2. Run the Patcher

```bash
py -3 Data\ai_behavior\patch_behavior_blocks.py
```

### 3. Build and Test

```bash
build_gameplay_patch.bat
```

Load `output/Blaze & Blade - Patched.bin` in your emulator and test in **Castle F1** against Zombies.

**Expected result:** Zombies attack ~2.4x faster and react more quickly.

---

## 📖 Field Reference

### Confirmed Fields

| Field | Function | Confidence | Example Values |
|-------|----------|------------|----------------|
| **flags_02** | Movement type | ✅ CONFIRMED | 0=ground, 21=flying |
| **dist_0E** | Attack range | ✅ HIGH | 2048=standard melee, 0=default, 65535=unlimited |

### High Confidence Fields

| Field | Function | Confidence | Pattern |
|-------|----------|------------|---------|
| **timer_04** | Attack cooldown | ⚠️ HIGH | Lower = faster attacks. Zombie=1948, Wolf=0, Goblin=468 |
| **timer_08** | AI decision interval | ⚠️ HIGH | Lower = more responsive. Bat=102, Zombie=2016, Goblin=420 |
| **dist_0C** | Aggro range | ⚠️ MEDIUM | Zombie=2084, Bat=3072, 0=default, 65535=unlimited |

### Unknown Fields

| Field | Status |
|-------|--------|
| timer_06 | Unknown (flight altitude for Bat?) |
| timer_0A | Unknown timer |
| val_10-1E | Unknown parameters |

---

## 🎨 Modification Templates

### Make Monster Faster

**Effect:** Increased attack frequency and responsiveness

```json
{
  "L": 2,
  "monster_name": "Zombie",
  "modifications": {
    "timer_04": 600,    // vanilla: 1948 (3x faster attacks)
    "timer_08": 800     // vanilla: 2016 (2.5x more responsive)
  }
}
```

**Recommendation:** Decrease by 50-70% for noticeable effect.

### Make Monster More Aggressive

**Effect:** Aggros from farther, attacks from longer range

```json
{
  "L": 0,
  "monster_name": "Lv20.Goblin",
  "modifications": {
    "dist_0C": 3000,    // vanilla: 0 (aggro from far away)
    "dist_0E": 2500,    // vanilla: 2048 (extended attack range)
    "timer_04": 300     // vanilla: 468 (faster attacks once engaged)
  }
}
```

**Recommendation:** Set dist_0C to 2000-5000 for long-range aggro.

### Make Monster Passive

**Effect:** Shorter aggro range, slower reactions

```json
{
  "L": 4,
  "monster_name": "Wolf",
  "modifications": {
    "dist_0C": 800,     // vanilla: 65535 (short aggro)
    "timer_04": 1200,   // vanilla: 0 (slower attacks)
    "timer_08": 800     // vanilla: 506 (less responsive)
  }
}
```

**Recommendation:** Lower dist_0C to 500-1500, increase timers by 2-3x.

---

## 📊 Analyzed Monsters

### Available for Modification

| Monster | Zone | L | Behavior Type |
|---------|------|---|---------------|
| **Lv20.Goblin** | Cavern F1 A1 | 0 | Standard ground melee |
| **Giant-Bat** | Cavern F1 A1 | 3 | Flying (flags_02=21) |
| **Zombie** | Castle F1 A1 | 2 | Slow heavy |
| **Harpy** | Castle F1 A1 | 3 | Flying melee |
| **Wolf** | Castle F1 A1 | 4 | Fast aggressive |
| **Blue-Slime** | Cavern F7 A1 | 7 | Passive floating |
| **Spirit-Ball** | Cavern F7 A1 | 8 | Passive floating |

### NULL Behavior Blocks (Cannot Modify)

| Monster | Zone | L | Why |
|---------|------|---|-----|
| **Goblin-Shaman** | Cavern F1 A1 | 1 | NULL behavior block |
| **Cave-Bear** | Cavern F7 A1 | 11 | NULL behavior block |
| **Ogre** | Cavern F7 A1 | 14 | NULL behavior block |

**Explanation:** These monsters use default/shared behavior hardcoded in the overlay, not stored in the script area.

**Workaround:** Would require creating new behavior blocks and patching the root table (advanced, not yet implemented).

---

## ⚠️ Important Warnings

### 1. Timer Units are UNKNOWN

**Problem:** We don't know if timers are in frames, frames/10, or some other unit.

**Solution:** Start with small changes (±20-30%) and test in-game.

**Example:**
- Vanilla Zombie timer_04 = 1948
- Try: 1500 (23% decrease) first
- If no noticeable effect, try: 1000 (49% decrease)
- If still nothing, try: 600 (69% decrease)

### 2. Distance Units are UNKNOWN

**Known values:**
- 2048 = standard melee attack range
- 3072 = Giant-Bat flying aggro range
- 65535 = unlimited/no limit

**Testing needed** to determine actual units (game units vs pixels).

### 3. Extreme Values May Crash

**Dangerous:**
- Setting timers to 0 (instant actions?)
- Setting distances to 65535 on wrong fields
- Changing flags_02 on non-flying monsters

**Safe approach:**
- Modify values by ±50% max on first test
- Only use proven vanilla values when possible
- Save clean BLAZE.ALL before testing

### 4. Behavior Changes Apply to ALL Instances

**Example:** If you modify Goblin L=0 behavior, ALL Lv20.Goblins in Cavern F1 will use the new behavior.

**Workaround:** None yet. Per-instance modification requires deeper system understanding.

---

## 🔬 Testing Protocol

### Step 1: Baseline Measurement

1. Load **vanilla** game
2. Go to test zone (e.g., Castle F1 for Zombie)
3. Record baseline:
   - Attacks per 10 seconds
   - Aggro distance (character pixels from monster when it aggros)
   - Attack range (max distance where monster still hits)

### Step 2: Modify and Test

1. Enable ONE patch in config
2. Run patcher + build
3. Load patched game
4. Go to same zone
5. Record new values

### Step 3: Calculate Actual Effect

```
Actual speedup = (vanilla_attacks_per_10s) / (modded_attacks_per_10s)
Timer scaling = (vanilla_timer - modded_timer) / actual_speedup

Example:
Vanilla Zombie: timer_04=1948, attacks=2 per 10s
Modded Zombie:  timer_04=974, attacks=4 per 10s
Actual speedup: 4/2 = 2x faster
Timer scaling: (1948-974) / 2 = 487 units per 1x speedup
```

### Step 4: Document Results

Add to `behavior_block_config.json`:

```json
{
  "_tested_modifications": [
    {
      "monster": "Zombie",
      "field": "timer_04",
      "vanilla": 1948,
      "modified": 974,
      "measured_effect": "2x faster attacks",
      "conclusion": "timer_04 controls attack speed, ~487 units = 1x speedup"
    }
  ]
}
```

---

## 🛠️ Advanced: Adding New Monsters

### Finding Script Offset and L Value

1. **Run dump_ai_blocks.py** on your target zone
2. **Locate monster** in assignment entries output
3. **Note script_offset** (script area starts at)
4. **Note L value** from assignment entry

**Example output:**
```
Script area starts at: 0xF7AA9C
Assignment entries:
  Slot 0 (Lv20.Goblin): L=0 R=2
  Slot 1 (Goblin-Shaman): L=1 R=3
```

### Add to Config

```json
{
  "enabled": true,
  "zone": "Cavern F1 Area1",
  "script_offset": 16231068,  // 0xF7AA9C decimal
  "L": 0,
  "monster_name": "Lv20.Goblin",
  "modifications": {
    "timer_04": 300
  }
}
```

---

## 📚 Reference Files

### Documentation
- `BEHAVIOR_MODDING_GUIDE.md` - This file
- `WIP/behavior_analysis_report.md` - Detailed analysis and hypotheses
- `Data/formations/Scripts/utils/dump_ai_blocks.py` - Extraction tool

### Code
- `patch_behavior_blocks.py` - Patcher script (run this)
- `behavior_block_config.json` - Configuration file (edit this)

### Data
- `Data/formations/Scripts/utils/ai_blocks_dump.json` - Raw extracted data

---

## 🐛 Troubleshooting

### "Behavior block for L=X is NULL"

**Cause:** Monster uses default/shared behavior, not a custom behavior block.

**Solution:** Cannot modify via this system. Needs advanced overlay patching.

**Affected:** Goblin-Shaman, Cave-Bear, Ogre (and likely many others)

### "No visible effect in-game"

**Possible causes:**
1. Timer scaling is different than expected (units unknown)
2. Modified wrong field (hypothesis incorrect)
3. BLAZE.ALL not injected correctly into BIN
4. Testing wrong monster/zone

**Solutions:**
1. Try larger changes (50-80% instead of 20%)
2. Test multiple fields simultaneously
3. Verify BIN injection (check file size/date)
4. Double-check zone and monster name in config

### "Game crashes when monster spawns"

**Cause:** Invalid value in behavior block (likely extreme value or wrong field type)

**Solution:**
1. Restore clean BLAZE.ALL
2. Use more conservative values
3. Only modify proven fields (timer_04, timer_08, dist_0C, dist_0E)
4. Avoid setting flags_02=21 on non-flying monsters

---

## 🎓 Learning More

### Next Steps for Research

1. **Measure timer units** - Test various timer values and measure in-game timing
2. **Test distance units** - Modify dist_0C/0E and measure aggro/attack range in pixels
3. **Decode NULL behaviors** - Find default behavior in overlay code
4. **Map val_10-1E fields** - Test modifications to unknown fields

### Contribute Findings

If you test modifications and discover:
- Actual timer/distance units
- Function of unknown fields
- New behavioral patterns

Please document in `behavior_block_config.json` under `_tested_modifications`.

---

## 📝 Version History

**v1.0 (2026-02-13)**
- Initial release
- 7 monsters analyzed (3 zones)
- 5 fields decoded (2 confirmed, 3 high confidence)
- Patcher script created
- All hypotheses UNTESTED in-game

---

**Status:** EXPERIMENTAL - This is a research tool. All field functions are hypotheses based on data patterns. In-game testing is required to confirm/refine hypotheses.
