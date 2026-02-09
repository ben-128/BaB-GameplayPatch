# Monster Spell Assignments

## How it works

Certain monsters can cast spells. The game uses a **bytecode scripting system**
where each spell-casting monster type has an opcode that references a **spell table
entry** in BLAZE.ALL. The mapping between opcode and spell table entry is set in
the PSX executable (SLES_008.45) at game startup.

By patching the executable, we can change which spell table entry a monster type
uses, effectively changing which spells that monster casts.

## Configuration

Edit `Data/monster_stats/monster_spells_config.json`:

```json
{
    "goblin_shaman": {
        "enabled": true,
        "spell_index": 8
    }
}
```

- **enabled**: Set to `true` to apply the patch. When `false`, the original value is kept.
- **spell_index**: Which spell table entry to use (0-15). See table below.

The patch runs automatically as part of `build_gameplay_patch.bat` (step 9c).
It patches the SLES_008.45 code directly inside the output BIN.

## Spell Table Entries

16-byte entries at `0x9E8D8E` in BLAZE.ALL.
Spell names from the in-game spell name table at `0x908E68` (48-byte stride).

### Entry structure

| Bytes | Role | Encoding |
|-------|------|----------|
| 0-1 | Support spell pair | bit7=flag, spell_id = byte & 0x7F |
| 2-5 | Offensive spells (4 distinct) | Direct spell ID (0x00-0x15) |
| 6-9 | Filler offensive spell (repeated) | Direct spell ID |
| 10-15 | Support spell pairs (3 pairs) | bit7=flag, spell_id = byte & 0x7F |

Odd entries (1,3,5,7) are reversed versions of even entries (0,2,4,6).

### Offensive spells (bytes 2-9)

| Index | Offensive Spells | Tier |
|-------|-----------------|------|
| 0 | Fire Bullet, Spark Bullet, Water Bullet, Stone Bullet | Low |
| 1 | (reversed of 0) | Low |
| 2 | Striking, Lightbolt, Stone Bullet, Water Bullet | Low |
| 3 | (reversed of 2) | Low |
| 4 | Dark Wave, Smash, Stone Bullet, Spark Bullet | Low |
| 5 | (reversed of 4) | Low |
| **6** | **Magic Missile, Enchant Weapon, Stone Bullet** | **Low (ORIGINAL)** |
| 7 | (reversed of 6) | Low |
| 8 | Blaze, Lightningbolt, Blizzard, Poison Cloud | Mid |
| 9 | Blizzard, Extend Spell, Magic Ray, Poison Cloud | Mid |
| 10 | Poison Cloud, Magic Ray, Shining, Dark Breath | High |
| 11 | Extend Spell, Magic Ray, Shining, Dispell Magic | High |
| 12 | Blizzard, Extend Spell, Petrifaction, Dispell Magic | High |
| 13 | Lightningbolt, Blizzard, Explosion, Petrifaction | High |
| 14 | Blaze, Lightningbolt, Thunderbolt, Explosion | High |
| 15 | Blaze, Poison Cloud, Dark Breath, Thunderbolt | High |

### Support spells (bytes 0-1, 10-15)

Uses an **unknown encoding** - bytes are NOT standard spell name table IDs.
Known mappings (confirmed in-game for entry 6 / Goblin-Shaman):

- `0xA0` = **Sleep** (confirmed)
- `0x1F` = **Healing** (likely, from original research)

Values vary by tier:

| Tier | Support byte values |
|------|-------------------|
| Low (0-7) | 0x00, 0x1F, 0xA0, 0xAF, 0xB0, 0xBF |
| Mid (8-9) | 0x20, 0x2F, 0xB0, 0xC0, 0xDF |
| High (10-15) | 0x20, 0x30, 0x3F, 0xC0, 0xDF |

Needs in-game testing to fully decode what each support byte does per tier.

## Monster Types

Two spell-casting monster types have been identified:

| Config Key | Opcode | Default Index | Known Monster |
|-----------|--------|---------------|---------------|
| `goblin_shaman` | 0x18 | 6 | Goblin-Shaman |
| `type_0x12_caster` | 0x12 | 4 | Unknown (to identify) |

## Testing

After building with a modified spell index:

1. Run `build_gameplay_patch.bat`
2. Load the patched BIN in emulator
3. Go to **Cavern of Death F1** (Goblin-Shamans spawn there)
4. Wait for a Goblin-Shaman to cast a spell
5. The spell visual/effect should be different from the original

## Technical Details

The patch modifies two `ori` instructions in the SLES_008.45 initialization code:

- **Goblin-Shaman (0x18)**: RAM `0x8002B638`, instruction `ori $a2, $zero, INDEX`
- **Type 0x12**: RAM `0x8002A790`, instruction `ori $a1, $zero, INDEX`

These instructions run once at game startup to fill runtime buffers that the
bytecode interpreter reads when executing spell-cast opcodes.

### Spell Name Table

Located at `0x908E68` in BLAZE.ALL, entries every 48 (0x30) bytes.
Spell IDs 0x00-0x15 correspond to the offensive spells used in the table above.

## Files

- `monster_spells_config.json` - Configuration (spell indices)
- `patch_monster_spells.py` - Patcher script (called by build step 9c)
