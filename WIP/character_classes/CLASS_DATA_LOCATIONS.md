# Character Class Data Locations in BLAZE.ALL

## Overview

This document maps where character class information is stored in the BLAZE.ALL file for Blaze & Blade modding.

---

## 1. CLASS NAME STORAGE

**Memory Zone**: `0x0090B6E8 - 0x0090B7BC`

| Class | Offset | Notes |
|-------|--------|-------|
| Warrior | 0x0090B6E8 | First class entry |
| Priest | 0x0090B6F8 | |
| Elf | 0x0090B734 | |
| Fairy | 0x0090B74C | |
| Wizard/Sorcerer | 0x0163CF0C | Different zone |
| Dwarf | 0x007EDE4B | Different zone |
| Thief/Rogue | 0x0152AD8C | Different zone |
| Ranger/Hunter | 0x01FB854C | Different zone |

**Structure Pattern**: Each class name is followed by pattern `0B 01 D9 00` as separator/marker

---

## 2. SPELL LISTS BY CLASS

**Memory Zone**: `0x002CA424 - 0x002CA8E4`

7 different spell lists found, showing progressive pattern where early spells are removed at higher levels:

| List | Starting Spells | Likely Class |
|------|-----------------|--------------|
| 1 | Enchant Earth → Enchant Wind → Enchant Water → ... | Wizard/Priest (full list) |
| 2 | Same as List 1 | Second variant or gender |
| 3 | Enchant Wind → Enchant Water → Charm → ... | Missing Enchant Earth |
| 4 | Enchant Water → Charm → Silence → ... | Missing first two Enchants |
| 5 | Charm → Silence → ... | Missing all Enchants |
| 6 | Silence → Magic → ... | Further progression |
| 7 | Magic → ... | Minimal spell list |

**Format**: int16 little-endian spell IDs per entry

---

## 3. SPELL DATABASE

**Total Spells Mapped**: 69+ spells (IDs 0-191)

**Entry Size**: 48 bytes per spell structure

**Key Spell IDs**:
| ID | Spell | MP Cost |
|----|-------|---------|
| 9 | Blaze | 16 |
| 10 | Lightningbolt | 16 |
| 31 | Healing | Unknown |
| 163-166 | Enchant spells | 16-8 |
| 167-175 | Buff/Utility spells | 8-80 |
| 176-179 | Summon spells | - |

**Source Files**:
- `Data/monster_stats/spell_table.json`
- `WIP/spells/*.json` (90 individual spell files)

---

## 4. STATS STRUCTURE (Based on Monster Template)

The monster stats structure uses **40 different stat fields** at +0x10 offset, likely similar for player classes:

| Index | Stat Name | Offset | Size |
|-------|-----------|--------|------|
| 0 | exp_reward | +0x10 | uint16 |
| 1 | stat2 | +0x12 | uint16 |
| 2 | hp | +0x14 | uint16 |
| 3 | stat4_magic (Mana/Power) | +0x16 | uint16 |
| 4 | stat5_randomness | +0x18 | uint16 |
| 5 | stat6_collider_type | +0x1A | uint16 |
| 17 | stat17_dmg (Damage) | +0x30 | uint16 |
| 18 | stat18_armor (Defense) | +0x32 | uint16 |
| 22 | stat22_magic_atk | +0x3A | uint16 |

---

## 5. EQUIPMENT PROFICIENCIES

### Weapon Categories by Class

| Weapon Type | Classes |
|-------------|---------|
| Swords | Warrior |
| Knives | Rogue |
| Bows | Hunter |
| Rapiers | Elf |
| Axes | Dwarf |
| Rods | Fairy |
| Priest's Wand/Hammer | Priest |
| Sorcerer's Wand | Sorcerer |

### Armor Categories by Class

| Armor Type | Classes |
|------------|---------|
| Heavy Armors | Warrior, Dwarf |
| Light Armors | Hunter, Elf, Rogue |
| Robes | Priest, Sorcerer, Fairy |
| Shields | Warrior, Dwarf |
| Clothings | All (helmets, boots, gloves, rings) |

---

## 6. ITEM DATABASE STRUCTURE

**Files**:
- `Data/items/all_items_clean.json` (316+ items)
- `Data/items/faq_items_reference.json` (376 items)

**Item Entry Format** (128 bytes each in BLAZE.ALL):
```
+0x00: Name (null-terminated, max 32 bytes)
+0x10-0x3F: Binary stats (uint16 values)
+0x41: Description
```

**Stat Attributes**:
- str, int, wil, agl, con, pow, luk
- at (Attack), mat (Magic Attack)
- def (Defense), mdef (Magic Defense)

---

## 7. FATE COIN SHOP - CLASS ITEMS

**Locations in BLAZE.ALL** (10 copies):
- 0x00B1443C, 0x00B14C3C, 0x00B1EC24, 0x00B1F424, 0x00B29344
- 0x00B34C38, 0x00B35438, 0x00B402E8, 0x00B4C41C, 0x00B4CC1C

**Class-specific item indices**: 10, 16, 20, 22

---

## 8. OFFSET SUMMARY TABLE

| Data Type | Offset Range | Entry Size | Format |
|-----------|--------------|------------|--------|
| Class Names | 0x0090B6E8 - 0x0090B7BC | Variable | ASCII null-terminated |
| Spell Lists | 0x002CA424 - 0x002CA8E4 | ~460 bytes | int16 LE spell IDs |
| Spell Structures | 0x00908E68 - 0x0090A200+ | 48 bytes each | Binary |
| Monster Attacks | 0x909DF0 - 0x90A1E0 | 48 bytes each | Monster spell data |
| Items Database | 0x006C6800+ | 128 bytes each | Name + stats + desc |
| Auction Prices | 0x002EA500+ | 2 bytes each | uint16 LE prices |
| Fate Coin Shop | 0x00B1443C+ | 23+ bytes | Class item prices |

---

## 9. TODO - DATA TO DISCOVER

- [ ] Base stats by class (HP, MP, attribute growth tables)
- [ ] Level progression tables (XP required per level)
- [ ] Class ↔ Spell List exact mapping
- [ ] Armor/Weapon proficiency flag encoding
- [ ] Stat modifier formulas

---

## 10. RECOMMENDED RESEARCH

1. **Analyze 0x0090B6E8 area** - Read 200-500 bytes around each class name for stat blocks
2. **Test spell lists in-game** with different classes to map spell_list_offset → class_name
3. **Extract XP tables** by finding progressive growth patterns near class definitions
4. **Document equipment restrictions** by analyzing item structure flags
5. **Create class stat templates** based on monster stat structure
