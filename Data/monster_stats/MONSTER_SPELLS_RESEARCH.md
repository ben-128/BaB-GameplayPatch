# Monster Spells Research - FAILED

Status: **NOT WORKING** - Unable to modify monster spells

## Goal

Change which spells monsters cast (e.g., make Goblin-Shaman cast Blaze instead of Stone Bullet)

## Test Subject

**Goblin-Shaman** casts:
- Magic Missile (0x08)
- Stone Bullet (0x03)
- Sleep (0xA0 / 160)
- Healing (0x1F / 31)

## What We Tried

### 1. Spell Table at 0x9E8D8E in BLAZE.ALL

- Found a table with 16-byte entries containing spell IDs
- Entry 6 matched Goblin-Shaman's spells: `AF 00 00 08 09 03 03 03 03 03 B0 00 A0 00 A0 1F`
- Monster stats have index 13 = 6, pointing to this entry
- **6 copies** of this table exist in BLAZE.ALL at:
  - 0x009E8DEE
  - 0x00A175BE
  - 0x00A355BE
  - 0x00A515BE
  - 0x00A7BDC6
  - 0x00A9B5BE
- Patched all 6 copies (= 12 in BIN with 2 BLAZE.ALL copies)
- **Result: NO EFFECT** - Goblin-Shaman still casts same spells
- Note: Setting all entries to 0xFF causes a crash, proving the table IS read

### 2. LEVELS.DAT Monster Data

- Found Goblin entries with `08 00 03 00` (Magic Missile, Stone Bullet as int16)
- Locations near "Goblin" at:
  - 0x149A1C8
  - 0x2BFF260
- Patched these patterns
- **Result: NO EFFECT**

### 3. AI Script Area Before Monster Names

- Area -2048 to -200 bytes before each "Goblin-Shaman" name
- Contains bytes 0x03, 0x08 that look like spell IDs
- Patched all 7 instances
- **Result: NO EFFECT**

### 4. Direct Monster Stats

- Goblin-Shaman stats structure (80 bytes after 16-byte name)
- Index 13 = 6 (spell table reference)
- Found 0x03 and 0x08 bytes in nearby data
- Patched these values
- **Result: NO EFFECT**

## Hypothesis: Hardcoded in Executable

The monster AI might determine spells based on **monster type ID**, with the actual spell selection logic hardcoded in the executable (SLES_008.45).

Evidence:
- Goblin-Shaman has monster type ID 24 (0x18) in stats index 0
- The spell table crash suggests it's read but possibly not for spell casting
- No spell patterns found in executable that match the table format

## Spell IDs Reference

| ID (hex) | ID (dec) | Spell |
|----------|----------|-------|
| 0x00 | 0 | Fire Bullet |
| 0x03 | 3 | Stone Bullet |
| 0x08 | 8 | Magic Missile |
| 0x09 | 9 | Enchant Weapon |
| 0x0A | 10 | Blaze |
| 0x0B | 11 | Lightningbolt |
| 0x0C | 12 | Blizzard |
| 0x1F | 31 | Healing |
| 0xA0 | 160 | Sleep |

## Files Cleaned

Removed experimental scripts:
- patch_monster_spells.py
- break_spells.py
- analyze_ai_script.py
- search_exe_spells.py
- (and 12 others)

Removed from build_gameplay_patch.bat:
- Step 5b (monster spell patching)

## Executable Analysis Results (2026-02-05)

### What We Found

1. **Monster Type Jump Table at 0x02BDE0** (file offset in SLES_008.45)
   - Maps monster type ID to AI handler function
   - Entry for Goblin-Shaman (type 0x18): jumps to `0x8001C218`

2. **Per-Monster AI Handlers**
   ```
   Type 0x16 -> 0x8001C0C0
   Type 0x17 -> 0x8001C1D0
   Type 0x18 (Goblin-Shaman) -> 0x8001C218
   Type 0x19 (Orc-Shaman?) -> 0x8001C2F4
   Type 0x1A -> 0x8001C33C
   ```

3. **Handlers Reference Runtime Buffers**
   - Goblin-Shaman handler loads `0x80054670` (lui 0x8005 / addiu 0x4670)
   - This address contains **zeros** in the executable = runtime buffer
   - Spell data is loaded from BLAZE.ALL at runtime, not stored in EXE

4. **13 References to Type 0x18 Near Spell IDs**
   - Found at offsets: 0x009BA8, 0x018C74, 0x029E24, etc.
   - Confirms monster type is checked when determining spell behavior

### Conclusion

Spells are **dynamically loaded** - the executable contains:
- AI logic per monster type
- Jump tables to select the right handler
- BUT the actual spell lists come from BLAZE.ALL at runtime

This explains why patching the spell table crashes when corrupted (it's read) but doesn't change spells (AI logic determines which spells to actually use).

### Possible Approach

To change monster spells, we would need to:
1. **Patch the executable** - Modify the AI handler for the target monster type
2. OR **Find the dynamic spell loading code** - Where BLAZE.ALL spell data is loaded into the runtime buffers
3. OR **Use memory hacking** - Modify RAM at runtime via emulator cheats

### Analysis Scripts Created

- `analyze_exe_spells.py` - Searches for spell patterns in executable
- `analyze_exe_deep.py` - Disassembles specific code regions
- `analyze_goblin_shaman_ai.py` - Analyzes the type 0x18 handler
- `find_spell_lists.py` - Searches for spell list data

## Next Steps to Investigate

1. **Trace the jal calls** - Functions called by AI handlers (e.g., `0x8001C16C`)
2. **Memory debugging** - Use emulator with debugger to see what gets loaded into `0x80054670`
3. **Patch the executable** - Modify AI handlers to change spell behavior
