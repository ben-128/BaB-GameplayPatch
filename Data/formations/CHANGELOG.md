# Formation System - Changelog

## 2026-02-12 - Per-Formation Spell Sets

### Major Changes

#### Spell Sets now Per-Formation (Breaking Change)
- **Before:** `slot_types` were global at area level - all monsters of same type had same spells across all formations
- **After:** Each formation can have its own `slot_types` - same monster can have different spells in different formations

**Example:**
```json
{
  "formations": [
    {
      "slots": [0, 1, 1],
      "slot_types": ["00000000", "02000000", "00000a00"]  // Shaman with Sleep
    },
    {
      "slots": [1, 1, 1],
      "slot_types": ["00000000", "00000a00", "00000a00"]  // Shaman with FireBullet!
    }
  ]
}
```

#### Editor UI Overhaul
- **Removed:** Global "Monster Spell Sets" section (top level)
- **Added:** Per-formation "Spell Sets" foldout inside each formation card
- **Added:** Tooltip button [?] showing confirmed spell set values in overlay
- **Added:** Real-time spell set name hints next to hex input fields
- **Improved:** Hex validation with auto-lowercase and auto-padding

#### Backward Compatibility
- JSONs with global `slot_types` still work (copied to all formations on load)
- JSONs without `slot_types` default to `00000000` for all slots
- Patcher checks per-formation first, then falls back to global

### Technical Changes

#### editor.html
1. **Added CSS classes:**
   - `.spell-sets-foldout` - Container for per-formation spell sets section
   - `.spell-sets-header` - Clickable header with arrow and tooltip button
   - `.spell-sets-body` - Collapsible body with slot type inputs
   - `.spell-set-row` - Individual monster spell set row
   - `.spell-tooltip-overlay` - Modal overlay for confirmed values

2. **Added HTML elements:**
   - `<div id="spellTooltip">` - Tooltip overlay with confirmed spell set values

3. **Modified JavaScript functions:**
   - `renderFormations()` - Added spell sets foldout rendering in each formation card
   - `buildOutputJSON()` - Now saves per-formation `slot_types` if present
   - Formation loading - Copies global `slot_types` to formations as initial values
   - Added `updateSpellName()` helper for real-time spell set name display

4. **Removed:**
   - Global spell sets section HTML (`#spellSetsSection`)
   - Global spell sets toggle event listener
   - `renderSpellSets()` function (no longer needed)

#### patch_formations.py
1. **Modified formation patching logic (lines 319-350):**
   - Now checks `formation.get("slot_types")` first (per-formation)
   - Falls back to `area.get("slot_types")` (global) if not present
   - Falls back to `00000000` default if neither present

2. **Preserved global slot_types for fillers:**
   - Filler formations (duplicate offsets) still use global slot_types

#### serve_editor.py
- No changes (vanilla filtering was already implemented)

### Bug Fixes
1. **Fixed:** Editor not saving per-formation slot_types (missing in `buildOutputJSON()`)
2. **Fixed:** Editor not loading per-formation slot_types (missing in formation loading)
3. **Fixed:** Missing `SPELL_SETS` constant in `updateSpellName()` function
4. **Fixed:** Removed obsolete event listeners for deleted global spell sets section
5. **Fixed:** Restored accidentally deleted `overridesSection` and `budgetBar` HTML elements

### Documentation
- Created `docs/PER_FORMATION_SPELL_SETS.md` - Complete guide with examples
- Updated `README.md` - Mentions per-formation spell sets feature
- Created `CHANGELOG.md` - This file

### Migration Guide

#### For existing JSONs (automatic):
1. Open area in editor
2. Editor automatically copies global `slot_types` to each formation
3. Modify spell sets per formation as desired
4. Save - per-formation slot_types are written to JSON
5. Rebuild with `build_gameplay_patch.bat`

#### For new areas:
- Just modify spell sets in each formation's foldout
- No need to define global `slot_types` (optional fallback only)

### Known Issues
None

### Testing
- Tested with Cavern F1 A1 (3 formations, 3 monsters)
- Verified roundtrip: load JSON → modify → save → load again
- Verified patcher respects per-formation slot_types
- Verified fallback to global slot_types works
- Verified in-game spell changes per formation

### Files Changed
- `Data/formations/editor.html` (major refactor)
- `Data/formations/Scripts/patch_formations.py` (slot_types priority logic)
- `Data/formations/README.md` (updated feature description)
- `Data/formations/docs/PER_FORMATION_SPELL_SETS.md` (new)
- `Data/formations/CHANGELOG.md` (new)
