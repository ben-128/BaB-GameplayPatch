================================================================================
  BLAZE & BLADE - AUCTION PRICE MODIFICATION GUIDE
================================================================================

QUICK START:
------------

1. Double-click: test_auction_prices.bat
2. Test the patched BIN in your emulator
3. Check if auction prices changed!


FILES:
------

BATCH FILES (Windows):
  test_auction_prices.bat   - Test auction price modifications
  restore_original.bat      - Restore BLAZE.ALL from backup

PYTHON SCRIPTS:
  test_modify_16bit_prices.py - Modify auction prices (auto-backup)
  patch_blaze_all.py          - Inject BLAZE.ALL into BIN file

DOCUMENTATION:
  AUCTION_PRICE_SOLUTION.md   - Complete technical documentation
  auction_price_research.txt  - Previous research (what didn't work)


WHAT WAS FOUND:
---------------

Auction prices are stored at 0x002EA500 in BLAZE.ALL as 16-bit words:

  Word[0]  = 10  (Healing Potion)
  Word[2]  = 22  (Shortsword)
  Word[7]  = 24  (Wooden Wand / Normal Sword)
  Word[9]  = 26  (Tomahawk)
  Word[11] = 28  (Dagger)
  Word[13] = 36  (Leather Armor)
  Word[15] = 46  (Leather Shield)

This is a DIFFERENT location than what was tried before (item structure +0x88).


TEST MODIFICATIONS:
-------------------

Running test_auction_prices.bat will change:
  - Healing Potion: 10 --> 99
  - Shortsword:     22 --> 88
  - Leather Armor:  36 --> 77

These are easy to verify in-game at the auction!


NEXT STEPS IF IT WORKS:
------------------------

1. Map all item IDs to their word indices
2. Create a complete price table JSON
3. Build a full price editor tool


TROUBLESHOOTING:
----------------

Q: Script says "work\BLAZE.ALL not found"
A: Make sure BLAZE.ALL is in the work\ subdirectory

Q: Script says "BIN not found"
A: Make sure work\Blaze & Blade - Patched.bin exists

Q: No work directory exists
A: Create the work\ subdirectory and copy BLAZE.ALL and the BIN file into it

Q: Prices didn't change in-game
A: This location might not be the auction table (could be shop/sell prices)
   Need to search for other 16-bit tables

Q: How to restore original?
A: Run restore_original.bat OR manually copy the backup file


BACKUP SYSTEM:
--------------

test_modify_16bit_prices.py automatically creates timestamped backups:
  work\BLAZE.ALL.backup_YYYYMMDD_HHMMSS

To restore manually:
  copy work\BLAZE.ALL.backup_XXXXXXXX_XXXXXX work\BLAZE.ALL


================================================================================
