# Level Design Data Analysis Report
**Blaze & Blade: Eternal Quest (PSX)**

Generated: 2026-02-04

---

## Executive Summary

This report documents the level design data extracted from `BLAZE.ALL` (46 MB). The file contains extensive textual data about levels, but the actual level geometry, spawn points, and placement data appear to be in compressed or encoded formats that require further investigation.

---

## 1. LEVEL/MAP NAMES FOUND

### Main Dungeons/Areas

| Level Name | Occurrences | Sample Offset | Notes |
|------------|-------------|---------------|-------|
| Castle Of Vamp | 4 | 0x240AD14 | Variations: 02, 03, 05(BOSS), 06 |
| CAVERN OF DEATH | 6 | 0xF7FB9C | Multiple references |
| The Sealed Cave | 13 | 0x907BA5 | Highly referenced |
| The Wood of Ruins | 1 | 0x907AFD | |
| The Ancient Ruins | 4 | 0x907B5D | Multiple references |
| The Ruins in the Lake | 1 | 0x907B8D | |
| The Forest | 1 | 0x149F70C | |
| The Mountain of the Fire Dragon | 1 | 0x907AD9 | |
| VALLEY OF WHITE WIND | 3 | 0x25D1AC8 | Boss area |

### Map References

- **Map03**: Found at 0x149A708
- **MAP10**: Found at 9 different offsets (0x2C07CC0, 0x2C084C0, etc.)

---

## 2. LEVEL STRUCTURE DATA

### Data Found Around Level Names

Each level name is typically followed by structured data:

#### Example: Castle Of Vamp 02 (0x240AD14)

**Before the name (64 bytes back):**
```
Hex: 3cffffffffffffff45ffff46ffffff4748ff49ffffffffff413e413e4aff4b...
Int16 values: [-196, -1, -1, -1, -187, 18175, -1, 18431, -184, -183, -1, -1, 15937, 15937, -182, -181]
```

**After the name:**
```
Hex: 000008001fd02a0c546865726520697320612062726f6e7a6520736967696c...
Text: "There is a bronze sigil on the door..."
```

**Observations:**
- Many `-1` (0xFFFF) values - likely "null" or "unused" markers
- Some sequential values (e.g., 15937, 15937) - possibly coordinates or IDs
- Followed by text strings describing level features

---

## 3. FLOOR/LEVEL HIERARCHY

The game uses multi-floor/underlevel structure:

| Term | Occurrences | Description |
|------|-------------|-------------|
| 1st Floor | 18 | First floor references |
| 2nd Floor | 10 | Second floor references |
| 3rd Floor | 7 | Third floor references |
| Floor (generic) | 80 | General floor mentions |
| Underlevel | 115 | Underground levels (1st, 2nd, 3rd Underlevel) |

**Key Finding:** The game has extensive multi-level dungeons with vertical progression (Floor 1, 2, 3, Underlevel 1, 2, 3, etc.)

---

## 4. INTERACTIVE OBJECTS

### Doors & Gates

- **Doors**: 337 references
  - Types: Magic-locked, demon-engraved, ghost-engraved
  - Keys: Various keys found (Host's Door Key, Storage Room Key, Control Room Key, etc.)

- **Gates**: 150 references
  - Special: Gate Crystals activate gates

- **Portals**: 266 references
  - Used for returning to previous underlevels
  - Example: "With this portal one can return to the 1st Underlevel"

### Chests & Treasures

- **Chest**: 13 explicit chest interactions
  - "Steel chest in the 3rd Underlevel"
  - Requires keys (Black Key, test founder's key)
  - Sealed chests requiring specific conditions

- **Treasure**: 71 references
  - Treasure chambers in ruins
  - Legendary treasure artworks

### Rooms & Chambers

- **Room**: 672 references (most common)
  - Types: Storage Room, Control Room, Guest Room, Treasure Chamber

- **Chamber**: 4 references
  - Secret chamber in 3rd underlevel of mine
  - Grave Chamber
  - Treasure Chamber

---

## 5. ENEMY/BOSS LOCATIONS

### Boss Encounters

| Boss Area | Offset | Context |
|-----------|--------|---------|
| Castle Of Vamp 05(BOSS) | 0x24189D8 | Werewolf boss fight |
| MEMORIES OF FORECIA VS-BOSS | - | Boss battle theme |
| VALLEY OF WHITE WIND VS-BOSS | - | Boss battle location |

### Enemy References

- **Enemy (generic)**: 17 references in spell descriptions
- **Monster**: 21 references
  - "These monsters are hard foes even for me!"
  - Dragon mentions
  - Griffon in Valley of White Silver

**Note:** Specific spawn data not found in text format. Likely stored in binary format or separate tables.

---

## 6. ENVIRONMENTAL FEATURES

### Natural Locations

- **Forest**: 3 references
- **Mountain**: 3 references
- **Cave**: 33 references (includes Cave-Bear, Cave-Scissors enemies)
- **Tower**: 74 references (ancient tower to the east)
- **Ruins**: 86 references (extensive ruins exploration)

### Towns & Villages

- **Town**: 9 references (return to town to sell items)
- **Village**: Limited references

---

## 7. QUEST/STORY ELEMENTS

### Key Lore Elements

1. **Arcane Civilization**
   - Ancient people who knew how to restrain evil spirits
   - Built the ancient tower
   - Highly developed culture

2. **Secrets & Mysteries**
   - Secret of immortality in palace
   - Secret chamber in 3rd underlevel of mine
   - Bewitched place in third underlevel
   - Crystal maze with portal at highest point

3. **Legendary Creatures**
   - Fire Dragon in mountain
   - Griffon in Valley of White Silver
   - Various demons throughout areas

---

## 8. TECHNICAL FINDINGS

### File Structure

- **Total Size**: 46,206,976 bytes (44.07 MB)
- **PSX TIM Images**: 2,627 image markers found
- **First TIM marker**: 0x0

### Potential Structure Zones

Multiple zones contain repeated structures:

| Zone | Offset | Structure Sizes Detected |
|------|--------|-------------------------|
| Zone 1MB-2MB | 0x100000 | 16, 20, 24, 32, 40, 48, 64 bytes |
| Zone 3MB-4MB | 0x300000 | 16, 20, 24, 32, 40, 48, 64 bytes |
| Zone 5MB-6MB | 0x500000 | 16, 20, 24, 32, 40, 48, 64 bytes |
| Zone 7MB-8MB | 0x700000 | 16, 20, 24, 32, 40, 48, 64 bytes |
| Zone 9MB-10MB | 0x900000 | 16, 20, 24, 32, 40, 48, 64 bytes |

**Hypothesis:** These zones may contain level geometry, spawn tables, or collision data in compressed/binary format.

---

## 9. DATA NOT YET FOUND

### Missing Level Design Elements

The following typical level design data has not been located in readable format:

1. **Spawn Points**
   - Enemy spawn locations (x, y, z coordinates)
   - Spawn triggers and conditions
   - Enemy counts per area

2. **Item Placement**
   - Chest locations and contents
   - Item spawn points
   - Consumable locations

3. **Level Geometry**
   - Wall/floor collision data
   - Walkable areas
   - Height maps

4. **Waypoints & Triggers**
   - Event triggers
   - Cutscene locations
   - NPC positions

5. **Camera Data**
   - Camera angles
   - Fixed camera positions
   - Camera transition zones

---

## 10. NEXT STEPS FOR RESEARCH

### Recommended Investigations

1. **Binary Structure Analysis**
   - Analyze the repeated structure zones (0x100000-0xA00000)
   - Look for coordinate triplets (x, y, z) in int16 or float format
   - Search for monster ID references (cross-reference with monster_stats data)

2. **Compression Analysis**
   - Check if level data is compressed (LZSS, RLE, or custom PSX compression)
   - Look for compression headers or signatures

3. **3D Model Formats**
   - PSX TMD (3D Model) format investigation
   - Vertex data, polygon data
   - Texture coordinates

4. **In-Game Memory Monitoring**
   - Use PS1 emulator memory viewer during gameplay
   - Watch memory regions while moving between areas
   - Identify runtime decompression of level data

5. **Cross-Reference with Known Data**
   - Compare with known monster stats offsets
   - Look for patterns similar to Fate Coin Shop structure
   - Check proximity to other identified data structures

---

## 11. TOOLS GENERATED

The following analysis tools were created:

1. **explore_level_design.py**
   - Extracts ASCII strings
   - Searches for level-related keywords
   - Analyzes coordinate patterns

2. **analyze_level_data.py**
   - Detailed level name structure analysis
   - Map data pattern search
   - Floor/level reference cataloging

3. **extract_spawn_data.py**
   - Monster spawn analysis (incomplete)
   - Chest/treasure structure search
   - Level structure zone detection

---

## 12. CONCLUSION

The `BLAZE.ALL` file contains extensive **textual** level design data (names, descriptions, dialogue) but the actual **structural** level design data (geometry, spawns, placement) appears to be:

- Stored in binary/compressed format
- Possibly embedded within the PSX TIM image data
- Located in the identified structure zones (1MB-10MB range)
- Requiring specialized PSX format knowledge to decode

**Next Priority:** Focus on binary structure analysis in the 0x100000-0xA00000 range and investigate PSX-specific 3D model formats.

---

## Appendix: File Locations

### Output Files

- `level_data_analysis.json` - Detailed level name structures
- `spawn_data_analysis.json` - Chest references and structure zones

### Known Data Locations (for reference)

- Monster stats: Various offsets (see monster_stats/ folder)
- Fate Coin Shop: 0x00B1443C (and 9 other copies)
- Auction prices: 0x002EA500
- Character classes: 0x0090B6E8 - 0x0090B7BC

---

*End of Report*
