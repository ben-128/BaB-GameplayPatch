# Monster Spell & Ability System

## Two Different Systems

Monsters use **two completely different mechanisms** for magic:

| | Offensive Spells (list 0) | Monster Abilities (list 7) |
|---|---|---|
| **Examples** | FireBullet, Blaze, Blizzard, MagicMissile | Fire Breath, Poison Touch, Drain, Paralyze Eye |
| **Users** | Goblin-Shaman, Dark-Magi, Arch-Magi, etc. | Red Dragon, Chimera, Basirisk, Salamander, etc. |
| **Controlled by** | entity+0x160 bitfield (zone-wide) | Overlay combat AI (hardcoded per monster type) |
| **Change stats?** | Yes: `spell_definition_overrides`, list=0 | Yes: `spell_definition_overrides`, list=7 |
| **Change who has what?** | Zone-wide only: `overlay_bitfield_patches` | Not yet possible (overlay AI not decoded) |
| **Per-monster assignment?** | Not yet (zone-wide limitation) | Not yet (hardcoded in overlay) |
| **MP pool** | stat4_magic (high = caster) | Probably fixed per ability |

### How offensive spells work (runtime)

1. Overlay init sets entity+0x160 = `0x01` (FireBullet only) for **ALL** monsters in zone
2. Level-up simulation runs and **adds more bits** (tiers) based on monster level
3. Final runtime bitfield = init value + level-up additions
4. Only monsters whose AI includes spell-casting behavior actually cast
5. Monsters need enough MP (stat4_magic) to pay the cost

The `overlay_bitfield_patches` replaces the init value (step 1). The level-up (step 2) can still add more on top.

### How monster abilities work (runtime)

- Monster abilities (Fire Breath, Poison Touch, etc.) are **hardcoded** in the overlay combat AI
- Each monster type has specific abilities assigned in the overlay code
- The assignment does NOT use the bitfield system at entity+0x160
- entity+0x2B5 (spell_list_index) is always 0 for all monsters, NOT 7
- The 55 combat action handlers in the EXE (`0x8003C1B0`) execute the abilities
- We cannot yet change which monster uses which ability

---

## Quick Start - Which JSON to Edit

**File: `Data/spells/spell_config.json`**

This is the only file you need to edit. It has two sections:

### Section 1: `spell_definition_overrides` - Change what spells/abilities DO

Modify stats (damage, MP cost, element). Works for **both** offensive spells AND monster abilities.

```json
{
    "spell_definition_overrides": {
        "enabled": true,
        "overrides": [
            {
                "_comment": "Make Fire Bullet stronger (affects ALL casters)",
                "enabled": true,
                "list": 0, "index": 0, "name": "FireBullet",
                "fields": { "damage": 20, "mp_cost": 2 }
            },
            {
                "_comment": "Make Fire Breath do more damage",
                "enabled": true,
                "list": 7, "index": 5, "name": "FireBreath",
                "fields": { "damage": 40 }
            }
        ]
    }
}
```

**Fields you can change:**

| Field | Offset | Description |
|-------|--------|-------------|
| `damage` | +0x18 | Damage value (u8, 0-255) |
| `mp_cost` | +0x13 | MP cost (u8) |
| `element` | +0x16 | 0=none, 1=thunder, 2=fire, 3=water, 4=earth, 5=wind, 6=light, 7=dark, 8=holy, 9=evil |
| `target_type` | +0x1C | 1=single target, other=area/self |
| `cast_prob` | +0x1D | Cast probability (higher = more likely) |

**`list` + `index`** identify which spell/ability. `name` is a safety check (patcher warns on mismatch).

### Section 2: `overlay_bitfield_patches` - Change which offensive spells monsters HAVE

**Only works for offensive spells (list 0).** Does NOT affect monster abilities.

Sets the initial spell availability bitfield (entity+0x160) for ALL monsters in a zone.

```json
{
    "overlay_bitfield_patches": {
        "enabled": true,
        "patches": [
            {
                "_comment": "Cavern of Death - give monsters 10 offensive spells",
                "enabled": true,
                "zone": "Cavern of Death",
                "bitfield_value": "0x000003FF",
                "type": "verbose",
                "offsets": { "byte0_ori": "0x0098A69C", "..." : "..." }
            }
        ]
    }
}
```

**Limitations:**
- Affects ALL monsters in the zone equally (Goblin, Shaman, Bat all get same spells)
- This is the INIT value; the level-up simulation may add more tiers on top
- Per-monster-type differentiation requires decoding the level-up code (not yet done)
- Does NOT affect monster abilities (those are hardcoded in overlay AI)

---

## Offensive Spells - Bitfield Reference (list 0)

Each bit enables one spell. Set `bitfield_value` as hex bitmask.

| Bit | Spell | Dmg | Elem | MP | Tier |
|-----|-------|-----|------|----|------|
| 0 | FireBullet | 10 | fire | 4 | 1 |
| 1 | SparkBullet | 8 | wind | 4 | 1 |
| 2 | WaterBullet | 6 | water | 4 | 1 |
| 3 | StoneBullet | 11 | earth | 4 | 1 |
| 4 | Striking | 0 | none | 20 | 1 |
| 5 | Lightbolt | 8 | light | 8 | 2 |
| 6 | DarkWave | 16 | dark | 8 | 2 |
| 7 | Smash | 24 | none | 8 | 2 |
| 8 | MagicMissile | 20 | none | 8 | 2 |
| 9 | EnchantWeapon | 0 | none | 24 | 2 |
| 10 | Blaze | 28 | fire | 12 | 3 |
| 11 | Lightningbolt | 28 | thunder | 16 | 3 |
| 12 | Blizzard | 30 | water | 16 | 3 |
| 13 | PoisonCloud | 20 | earth | 12 | 3 |
| 14 | ExtendSpell | 24 | none | 16 | 3 |
| 15 | MagicRay | 30 | light | 20 | 4 |
| 16 | Shining | 50 | light | 20 | 4 |
| 17 | DarkBreath | 30 | dark | 16 | 4 |
| 18 | DispellMagic | 0 | none | 20 | 4 |
| 19 | Petrifaction | 0 | earth | 20 | 4 |
| 20 | Explosion | 45 | fire | 24 | 5 |
| 21 | Thunderbolt | 35 | thunder | 24 | 5 |
| 22 | FreezeBeast | 38 | water | 24 | 5 |
| 23 | EarthJavelin | 32 | earth | 20 | 5 |
| 24 | DeathSpell | 0 | dark | 24 | 5 |
| 25 | Teleport | 0 | none | 28 | 5 |
| 26 | ChaosFlare | 50 | fire | 32 | 6 |
| 27 | MeteorSmash | 50 | earth | 32 | 6 |
| 28 | Fusion | 60 | none | 40 | 6 |

**Common bitfield values:**

| Value | Bits | Description |
|-------|------|-------------|
| `0x00000001` | bit 0 | Vanilla (Fire Bullet only) |
| `0x0000001F` | 0-4 | Tier 1 (5 basic spells) |
| `0x000003FF` | 0-9 | Tiers 1+2 (10 spells) |
| `0x00007FFF` | 0-14 | Tiers 1-3 (15 spells) |
| `0x000FFFFF` | 0-19 | Tiers 1-4 (20 spells) |
| `0x03FFFFFF` | 0-25 | Tiers 1-5 (26 spells) |
| `0x1FFFFFFF` | 0-28 | ALL 29 offensive spells |

---

## Monster Abilities Reference (list 7)

30 entries at BLAZE.ALL `0x909DF8`. All have spell_id = 29 (monster category).

| Index | Name | Type |
|-------|------|------|
| 0 | PoisonTouch | Contact status |
| 1 | ParalyzeTouch | Contact status |
| 2 | ParalyzeEye | Ranged status |
| 3 | ConfusionEye | Ranged status |
| 4 | SleepEye | Ranged status |
| 5 | FireBreath | Breath attack (fire) |
| 6 | ColdBreath | Breath attack (water) |
| 7 | ThunderBreath | Breath attack (thunder) |
| 8 | AcidBreath | Breath attack (earth) |
| 9 | PoisonBreath | Breath attack (poison) |
| 10 | StunBreath | Breath attack (stun) |
| 11 | MadScream | AoE confusion |
| 12 | Drain | HP drain |
| 13 | Howling | AoE fear |
| 14 | Knockback | Pushback |
| 15 | Stun | Single stun |
| 16 | SleepSong | AoE sleep |
| 17 | EvilEye | Ranged status |
| 18 | EvilHowling | AoE dark |
| 19 | EvilField | AoE dark zone |
| 20 | Invincible | Self-buff |
| 21 | Regeneration | Self-heal |
| 22 | Earthquake | AoE earth |
| 23 | FlareBreath | Breath (fire, strong) |
| 24 | DeadGate | Undead summon? |
| 25 | Destroyer | Heavy attack |
| 26 | WindSmash | AoE wind |
| 27 | Tidalwave | AoE water |
| 28 | HellHowling | AoE dark (strong) |
| 29 | DarkBlaze | Dark fire attack |

**Can modify** with `spell_definition_overrides` using `"list": 7, "index": 0-29`.

**Cannot modify** which monster uses which ability (hardcoded in overlay combat AI).

---

## What You CAN and CANNOT Modify

| What | How | Limitation |
|------|-----|------------|
| Spell/ability damage, MP, element | `spell_definition_overrides` | Shared by all users of that spell |
| Which offensive spells in a zone | `overlay_bitfield_patches` | Zone-wide (all monster types same) |
| Which offensive spells per monster type | Not yet possible | Needs level-up simulation decode |
| Which monster ability per monster type | Not yet possible | Needs overlay combat AI decode |
| Make a melee monster cast spells | Unknown | Need to test if bitfield + MP is enough |
| Spell damage formula | Not yet possible | In EXE combat code |

---

## How to Test

1. Edit `Data/spells/spell_config.json`
2. Run `build_gameplay_patch.bat` (or manually: steps below)
3. Load `output/Blaze & Blade - Patched.bin` in emulator
4. Go to **Cavern of Death Floor 1** and fight monsters
5. Watch for spell casting changes

**Manual steps (for quick iteration):**
```bat
REM Reset clean BLAZE.ALL
copy /Y "Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL" output\BLAZE.ALL

REM Apply spell definition patches (step 7b)
py -3 Data\spells\patch_spell_table.py

REM Apply overlay bitfield patches (step 7e)
py -3 Data\spells\patch_monster_spells.py

REM ... then run remaining build steps (8-9) to inject into BIN
```

---

## Build Pipeline Steps

| Step | Script | What it patches |
|------|--------|----------------|
| 7b | `patch_spell_table.py` | Spell/ability definitions (damage, MP, element) at BLAZE.ALL 0x908E68 |
| 7e | `patch_monster_spells.py` | Overlay init bitfield (entity+0x160) in BLAZE.ALL |

Both run BEFORE BIN injection (step 8-9).

---

## Technical Details

### Spell Definition Table (BLAZE.ALL 0x908E68)

8 lists stored contiguously as 48-byte entries:

| List | Count | Offset | Category |
|------|-------|--------|----------|
| 0 | 29 | 0x908E68 | Offensive spells |
| 1 | 24 | 0x9093D8 | Support/Priest spells |
| 2 | 20 | 0x909858 | Status/Enchantment spells |
| 3 | 7 | 0x909C18 | Herbs |
| 4 | 1 | 0x909D68 | Wave (Dwarf) |
| 5 | 1 | 0x909D98 | Arrow (Hunter) |
| 6 | 1 | 0x909DC8 | Stardust (Fairy) |
| 7 | 30 | 0x909DF8 | Monster abilities |

### 48-byte Entry Format

| Offset | Size | Field |
|--------|------|-------|
| +0x00 | 16 | Name (ASCII, null-padded, NO SPACES: "FireBullet" not "Fire Bullet") |
| +0x10 | u8 | Spell ID |
| +0x13 | u8 | MP cost |
| +0x16 | u8 | Element (0-9) |
| +0x18 | u8 | Damage |
| +0x1C | u8 | Target type (1=single) |
| +0x1D | u8 | Cast probability |

### Offensive Spell System (entity+0x160 bitfield)

- entity+0x2B5 = spell_list_index (always 0 = offensive list, BSS table all zeros)
- entity+0x160 = 64-bit availability bitfield (each bit = one spell)
- entity+0x2BF = current spell slot (cycles through available spells)
- Overlay init writes 0x01 at 0x0098A6xx (Cavern of Death, verbose pattern)
- Level-up simulation adds tiers via computed addresses (not fixed offsets, not yet decoded)
- Tier thresholds at EXE 0x8003C020

### Monster Ability System (overlay combat AI)

- Monster abilities are NOT controlled by entity+0x160 bitfield
- Assigned per monster type in overlay combat AI code (BLAZE.ALL)
- 55 combat action handlers in EXE at 0x8003C1B0 execute the abilities
- Assignment mechanism not yet decoded (in overlay, not EXE)

### Files

| File | Purpose |
|------|---------|
| `spell_config.json` | Configuration (the only file you edit) |
| `patch_spell_table.py` | Spell definition patcher (step 7b) |
| `patch_monster_spells.py` | Overlay bitfield patcher (step 7e) |
| `MONSTER_SPELLS.md` | This documentation |
| `scripts/add_spell_info.py` | Adds spell_info to monster JSONs |
| `WIP/spells/MONSTER_SPELL_RESEARCH.md` | Full research notes |
| `WIP/spells/verify_spell_table.py` | Dumps all spell table entries |
