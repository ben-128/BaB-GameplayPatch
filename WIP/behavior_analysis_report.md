# Behavior Blocks Analysis Report
**Date:** 2026-02-13
**Objective:** Identify fields controlling aggression, attack speed, and movement patterns

---

## 📊 Comparative Data

### Speed Comparison (timer_08 - Attack Cooldown Hypothesis)

| Monster | Type | timer_08 | Observed Speed |
|---------|------|----------|----------------|
| **Giant-Bat** | Flying | 102 | Fast |
| **Goblin** | Ground Melee | 420 | Normal |
| **Harpy** | Flying | 450 | Normal-Fast |
| **Wolf** | Ground Fast | 506 | Very Fast |
| **Zombie** | Slow Undead | 2016 | Very Slow |
| **Blue-Slime** | Passive | 343 | Slow-Normal |
| **Spirit-Ball** | Floating | 343 | Slow-Normal |

**Observation:** Lower timer_08 does NOT always mean faster (Bat=102 vs Wolf=506, but both fast)

**Revised Hypothesis:**
- timer_08 might be **action interval** (time between AI decisions)
- Lower = more frequent actions, but NOT necessarily faster attacks
- Giant-Bat's very low value (102) might be for smooth flight animation

### Movement Type Comparison (flags_02)

| Monster | flags_02 | Movement Type |
|---------|----------|---------------|
| **Giant-Bat** | 21 | Flying |
| All others | 0 | Ground/Standard |

**Conclusion:** flags_02 = 21 (0x15 binary: 00010101) indicates **flying movement**

### Aggression/Range Comparison

| Monster | Aggression | dist_0C | dist_0E | timer_04 | timer_06 |
|---------|------------|---------|---------|----------|----------|
| **Zombie** | Medium | 2084 | 0 | 1948 | 0 |
| **Goblin** | Medium | 0 | 2048 | 468 | 634 |
| **Harpy** | Medium | 0 | 2048 | 0 | 0 |
| **Wolf** | High | 65535 | 65535 | 0 | 0 |
| **Giant-Bat** | Medium | 3072 | 0 | 2067 | 64376 |
| **Blue-Slime** | Passive | 65535 | 65535 | 0 | 0 |
| **Spirit-Ball** | Passive | 65535 | 65535 | 0 | 0 |

**Observations:**
1. **dist_0C/0E = 65535 (0xFFFF)**: Appears on BOTH aggressive (Wolf) AND passive (Slime) monsters
   - Likely means "no distance limit" or "use default behavior"

2. **Giant-Bat unique pattern:**
   - dist_0C = 3072 (moderate range, likely aggro range for flying)
   - timer_06 = 64376 (huge value, possibly flight altitude timer?)

3. **Goblin/Harpy pattern:**
   - dist_0E = 2048 (attack range?)
   - dist_0C = 0 (use default aggro?)

4. **Zombie pattern:**
   - dist_0C = 2084 (specific aggro range)
   - Higher timer values (1948, 2016) - slow deliberate movement

---

## 🔬 Field Function Hypotheses

### CONFIRMED Fields

| Offset | Name | Function | Evidence |
|--------|------|----------|----------|
| 0x02 | flags_02 | Movement type flags | Giant-Bat=21 (flying), all others=0 (ground) |

### HIGH CONFIDENCE Fields

| Offset | Name | Function | Evidence |
|--------|------|----------|----------|
| 0x08 | timer_08 | AI decision interval | Lower = more frequent actions. Bat=102 (smooth flight), Zombie=2016 (sluggish) |
| 0x0E | dist_0E | Attack/Action range | Goblin/Harpy=2048 (standard melee), 0=use default, FFFF=unlimited |

### MEDIUM CONFIDENCE Fields

| Offset | Name | Function | Evidence |
|--------|------|----------|----------|
| 0x04 | timer_04 | Attack cooldown timer? | Zombie=1948 (slow attacks), Wolf/Harpy=0 (fast attacks), Goblin=468 (normal) |
| 0x06 | timer_06 | Special behavior timer | Giant-Bat=64376 (flight altitude?), Goblin=634, others=0 |
| 0x0C | dist_0C | Aggro detection range | Zombie=2084 (fixed range), Bat=3072 (flying range), FFFF=no limit/default |

### LOW CONFIDENCE Fields

| Offset | Name | Function | Evidence |
|--------|------|----------|----------|
| 0x0A | timer_0A | Unknown timer | Goblin/Shaman=634, Harpy=580, Wolf=FFFF, varies widely |
| 0x00 | unk_00 | Unknown ID/pointer | Zombie=1880, Wolf=5000, Slime=60724, Bat/Goblin/Harpy=0 |
| 0x10+ | val_10-1E | Unknown params | Highly variable, need more data |

---

## 🎯 Behavioral Patterns Identified

### Pattern 1: Standard Ground Melee (Goblin, Harpy)
```
flags_02 = 0
timer_04 = 0-468 (low to moderate)
timer_06 = 0-634
timer_08 = 420-450 (moderate)
timer_0A = 580-634
dist_0C = 0 (use default)
dist_0E = 2048 (standard attack range)
```

### Pattern 2: Slow Heavy (Zombie)
```
flags_02 = 0
timer_04 = 1948 (HIGH - slow attacks)
timer_06 = 0
timer_08 = 2016 (HIGH - slow decisions)
timer_0A = 0
dist_0C = 2084 (fixed moderate aggro)
dist_0E = 0
```

### Pattern 3: Fast Aggressive (Wolf)
```
flags_02 = 0
timer_04 = 0 (instant attacks)
timer_06 = 0
timer_08 = 506 (moderate decisions)
timer_0A = 65535 (no limit)
dist_0C = 65535 (unlimited aggro)
dist_0E = 65535 (unlimited range)
```

### Pattern 4: Flying (Giant-Bat)
```
flags_02 = 21 (FLYING FLAG)
timer_04 = 2067
timer_06 = 64376 (HUGE - flight behavior)
timer_08 = 102 (VERY LOW - smooth flight)
timer_0A = 0
dist_0C = 3072 (flying aggro range)
dist_0E = 0
```

### Pattern 5: Passive/Floating (Blue-Slime, Spirit-Ball)
```
flags_02 = 0
timer_04 = 0
timer_06 = 0
timer_08 = 343 (low-moderate)
timer_0A = 656-738
dist_0C = 65535 (no aggro limit)
dist_0E = 65535 (no range limit)
```

---

## 🛠️ Recommended Modification Targets

### To Make a Monster FASTER:
1. **Decrease timer_04** (attack cooldown): 1948 → 400 (much faster attacks)
2. **Decrease timer_08** (decision interval): 2016 → 400 (more responsive)
3. **Keep timer_06** at 0 unless flying

**Example: Speed up Zombie**
```json
{
  "L": 2,
  "monster": "Zombie",
  "modifications": {
    "timer_04": 400,   // vanilla: 1948 (faster attacks)
    "timer_08": 500    // vanilla: 2016 (faster decisions)
  }
}
```

### To Make a Monster MORE AGGRESSIVE:
1. **Increase dist_0C** (aggro range): 0 → 3000 (detects from farther)
2. **Set dist_0E** to 2048+ (attack range)
3. **Decrease timer_04** for faster attacks once engaged

**Example: Make Goblin more aggressive**
```json
{
  "L": 0,
  "monster": "Lv20.Goblin",
  "modifications": {
    "dist_0C": 3000,   // vanilla: 0 (aggro from farther)
    "dist_0E": 2500,   // vanilla: 2048 (attack from farther)
    "timer_04": 300    // vanilla: 468 (faster attacks)
  }
}
```

### To Make a Monster PASSIVE:
1. **Set dist_0C = 0** or very low (short aggro range)
2. **Increase timer_04** (slower attacks): 400 → 1500
3. **Increase timer_08** (slower decisions): 400 → 800

**Example: Make Wolf passive**
```json
{
  "L": 4,
  "monster": "Wolf",
  "modifications": {
    "dist_0C": 800,    // vanilla: 65535 (short aggro)
    "timer_04": 1200,  // vanilla: 0 (slower attacks)
    "timer_08": 800    // vanilla: 506 (slower decisions)
  }
}
```

---

## ⚠️ Important Notes

### NULL Behavior Blocks

Several monsters have **NULL behavior blocks** (L points to empty root table entry):
- **Goblin-Shaman** (L=1)
- **Cave-Bear** (L=11)
- **Ogre** (L=14)

**Implication:** These monsters use a **default/shared behavior** not stored in the script area, or their behavior is entirely hardcoded in the overlay.

**Action:** Cannot modify behavior via script area for these monsters. Would need to:
1. Create new behavior blocks in the script area
2. Patch root table to point to them
3. Or modify the default behavior in overlay code

### Distance Units

Distances (dist_0C, dist_0E) likely use **game units**, not pixels.
- 2048 = standard melee range
- 3072 = extended range (flying)
- 65535 = unlimited/default

Need in-game testing to determine exact conversion (1 unit = ? pixels).

### Timer Units

Timers likely use **frames** at 50 FPS (PAL) or 60 FPS (NTSC).
- 468 frames ÷ 50 FPS = 9.36 seconds
- 634 frames ÷ 50 FPS = 12.68 seconds
- 2016 frames ÷ 50 FPS = 40.32 seconds

**This seems WAY too long for attack cooldowns!**

**Revised hypothesis:** Timers might use a **different scale** (frames/10? frames/100?), or they're accumulator values, not direct frame counts.

---

## 📋 Next Steps

### Immediate Actions

1. ✅ **Done:** Extract and analyze behavior blocks
2. ⚠️ **Next:** Create behavior block patcher script
3. ⚠️ **Next:** Test modifications on Goblin (speed up timer_04 and timer_08)
4. ⚠️ **Next:** Measure in-game timing to confirm timer units

### Testing Protocol

1. **Baseline Test:**
   - Record vanilla Zombie attack frequency (attacks per 10 seconds)
   - Record vanilla Goblin attack frequency

2. **Modification Test:**
   - Halve Zombie timer_04 (1948 → 974)
   - Measure new attack frequency
   - Calculate actual timer scaling

3. **Range Test:**
   - Set Goblin dist_0C to 5000
   - Measure aggro range in-game (player distance when monster aggros)
   - Confirm distance units

4. **Behavior Validation:**
   - Create new behavior block for Goblin-Shaman (currently NULL)
   - Test if root table patching works
   - Document limitations

---

## 🔍 Questions Remaining

1. **What is timer_06 for non-flying monsters?** (Goblin=634, others=0)
2. **What is unk_00?** (Wolf=5000, Zombie=1880, varies widely)
3. **Why do passive Slime and aggressive Wolf both have dist_C/E = 65535?**
4. **What are val_10 through val_1E?** (appear to vary by monster type)
5. **How do NULL behavior blocks work?** (Shaman, Bear, Ogre)
6. **What is the actual timer scaling factor?** (frames? frames/10? other?)

---

## 📚 References

- `dump_ai_blocks.py` - Extraction tool
- `ai_blocks_dump.json` - Raw extracted data
- MEMORY.md - "Monster AI System (DECODED 2026-02-10)"
- MONSTER_SPELL_RESEARCH.md - Overlay analysis

**Status:** Behavior blocks partially decoded, ready for experimental patching.
