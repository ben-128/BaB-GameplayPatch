# Auction Price Research - Blaze & Blade

## Objective
Find and modify auction prices in Blaze & Blade (PS1)

## Known Auction Prices
- Healing Potion: 10 gold
- Shortsword: 22 gold
- Wooden Wand/Normal Sword: 24 gold
- Tomahawk: 26 gold
- Dagger: 28 gold
- Leather Armor: 36 gold
- Leather Shield: 46 gold
- Robe: 72 gold

## Discoveries

### ✅ Price Table Found
**Location:** `0x002EA49A` in both BLAZE.ALL and LEVELS.DAT

Pattern found (16-bit little-endian words):
```
Word  0: 10  (Healing Potion)
Word  2: 22  (Shortsword)
Word  7: 24  (Wooden Wand/Normal Sword)
Word  9: 26  (Tomahawk)
Word 11: 28  (Dagger)
Word 13: 36  (Leather Armor)
Word 15: 46  (Leather Shield)
```

**All 7 known prices match perfectly** - this cannot be coincidence.

### 📁 Files Containing the Table

1. **BLAZE.ALL** (LBA 185765)
   - Offset: 0x002EA49A
   - Contains exact price pattern

2. **LEVELS.DAT** (LBA 163167)
   - Offset: 0x002EA49A
   - Contains exact price pattern

**Total copies found:** 2 (exhaustive BIN search completed)

### ❌ Modification Attempts - ALL FAILED

#### Test 1: Modified specific prices (10→99, 22→88, 36→77)
- ✅ BLAZE.ALL patched successfully
- ✅ LEVELS.DAT patched successfully
- ✅ BIN file verified with correct values
- ❌ **In-game: No change** (still 10/22/36)

#### Test 2: Set ALL 32 words to 999
- ✅ Both files patched with 999
- ✅ BIN verified with 999 everywhere
- ❌ **In-game: No 999 seen anywhere**
  - Not in Auction House
  - Not in shops
  - Not in inventory
  - Not when selling
  - Nowhere

#### Test 3: Tested with new character
- ❌ No change

#### Test 4: Tested with existing character
- ❌ No change

### 🔍 Areas Searched

#### ✅ BLAZE.ALL
- Found price table at 0x002EA49A
- Patched successfully
- No effect in-game

#### ✅ LEVELS.DAT
- Found price table at 0x002EA49A
- Patched successfully
- No effect in-game

#### ✅ SLES_008.45 (Executable)
- Searched for price sequences
- **NOT FOUND** in executable

#### ✅ Save Files (epsxe000.mcr)
- Searched for price table pattern
- **NOT FOUND** in save files
- Individual prices appear but not as a table

#### ✅ Full BIN Scan
- Exhaustive search of entire 700MB disc image
- Only 2 copies found (already patched)
- No additional copies exist

### 🤔 Why Doesn't It Work?

The price table at 0x002EA49A is **definitely** the auction prices:
- Perfect match for 7 different items
- Probability of coincidence: ~0%

But modifications have **zero effect** in-game. Possible explanations:

1. **Checksum/Integrity Check**
   - Game detects modifications
   - Falls back to hardcoded defaults

2. **Cached at Boot**
   - Game loads all data to RAM at startup
   - Never re-reads from disc

3. **Compression/Encryption**
   - Data is decompressed in unknown format
   - We're modifying compressed data that's never read

4. **Code-based Calculation**
   - Prices calculated dynamically by game logic
   - Table we found is unused or for different purpose

5. **Unknown Protection**
   - PS1-specific disc protection
   - Data overlay system we don't understand

### 📊 Files Analyzed

**Disc Contents (17 files):**
- BLAZE.ALL (46MB) - Main data
- LEVELS.DAT (46MB) - Level data
- SLES_008.45 (843KB) - Executable
- Music files (XA format)
- Video files (STR format)
- Other assets

**No other data files** contain price information.

## Conclusion

**Status: FAILED** ❌

Despite finding the exact price table and successfully patching it:
- The table is NOT used by the game for auction prices
- OR there is protection preventing modifications
- OR auction prices are determined by other means

The search has been exhaustive. Without:
- Memory debugging during gameplay
- Reverse engineering the executable
- Understanding PS1 protection schemes

...further progress is not possible with file patching alone.

## Files Created

### Tools
- `test_modify_16bit_prices.py` - Modify prices in BLAZE.ALL
- `test_modify_correct_location.py` - Patch correct offset
- `patch_all_prices.py` - Set all prices to 999
- `verify_bin_patch.py` - Verify BIN contains patches
- `find_all_price_tables.py` - Find all table copies in BLAZE.ALL
- `search_original_bin.py` - Search entire BIN for patterns

### Analysis
- `analyze_save_file.py` - Check if prices in save
- `search_executable.py` - Search SLES for prices
- `extract_and_check_levels.py` - Extract LEVELS.DAT
- `list_all_files.py` - List all disc files
- `deep_search_sles.py` - Deep search in executable

### Verification
- `check_current_blaze.py` - Compare two offsets
- `verify_correct_location.py` - Verify correct location
- `verify_999.py` - Verify 999 pattern
- `final_check_bin.py` - Final BIN verification

### Batch Scripts
- `test_auction_prices.bat` - Full test workflow (with fixes for paths with ampersands)
- `restore_original.bat` - Restore from backup

## Next Steps (If Continuing)

1. **Memory Debugging**
   - Use PS1 emulator debugger
   - Find where prices are loaded in RAM
   - Modify RAM directly

2. **Reverse Engineering**
   - Disassemble SLES_008.45
   - Find auction price loading code
   - Patch executable directly

3. **Alternative Approach**
   - Modify different game values (HP, damage, etc.)
   - See if ANY modifications work
   - Determine if there's global protection

## Date
2026-02-04
