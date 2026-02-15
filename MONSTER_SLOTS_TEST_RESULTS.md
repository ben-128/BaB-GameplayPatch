# Monster Slots Addition - Test Results

**Date:** 2026-02-15
**Objective:** Add 2 monster slots to Cavern F1 A1 (3 → 5 monsters)

## Key Discoveries

### Critical Offsets

1. **Header Monster Count @ 0xF7A851**
   - Located 175 bytes BEFORE animation section
   - Value: 0x03 (3 monsters)
   - **CRITICAL: Cannot be changed!** Changing to 5 causes infinite loading

2. **Middle Section Count @ 0xF7A93A** (CAVERN_ANIM + 56 + 2)
   - Inside animation section, middle section byte[2]
   - Value: 0x03 (3 monsters)
   - **CAN be changed to 5** without issues

### Structure Layout (Cavern F1 A1)

```
[Header Section @ 0xF7A851]
  - Contains monster count (MUST stay 3)

[Animation Section @ 0xF7A900]
  - Header (8 bytes)
  - Animation Tables (3×8 = 24 bytes)
  - Animation Records (3×8 = 24 bytes)
  - Middle Section (44 bytes)
    - byte[2] = monster count (CAN be 5)
  - Assignments (3×8 = 24 bytes)

[Stats Section @ 0xF7A97C]
  - Stats (3×96 = 288 bytes)
```

## Test Results

### Phase 1: Isolate Monster Count Locations

| Test | Changes | Result | Notes |
|------|---------|--------|-------|
| TEST 1 | Header=5, Middle=5 | ❌ Infinite Loading | Both counts changed |
| TEST 7 | Header=5, Middle=3 | ❌ Infinite Loading | Header count alone |
| TEST A | Header=3, Middle=5 | ✅ WORKS | Middle count alone |

**Conclusion:** Header count @ 0xF7A851 MUST stay at 3. Only middle count can be changed.

---

### Phase 2: Test Structure Additions (Header=3, Middle=5)

| Test | Structure Change | Shift | Result | Notes |
|------|------------------|-------|--------|-------|
| TEST A | None (baseline) | 0 | ✅ WORKS | Loads normally |
| TEST B | +Stats (3→5) | +192 | ❌ Black Level | Loads but broken rendering |
| TEST C | +Assignments (3→5) | +16 | ✅ WORKS | Loads correctly! |
| TEST D | +Anim Tables (3→5) | +16 | ❌ CRASH | Adding anim tables crashes |

**Key Findings:**
- ✅ Assignments can be safely added
- ❌ Anim tables cannot be added (header count controls this)
- ❌ Stats cause black level when added (unknown validation)

---

### Phase 3: Reuse Existing Animations (CURRENT TEST)

**Approach:** Add 2 assignment slots that reuse existing anim tables

**Changes:**
- Header count: **3** (unchanged)
- Middle count: **5** (changed)
- Anim tables: **3** (unchanged - no new tables)
- Anim records: **3** (unchanged)
- Assignments: **5** (2 added)
  - Slot 3: Points to anim 0 (Goblin)
  - Slot 4: Points to anim 1 (Shaman)
- Stats: **3** (unchanged - no new stats)

**Expected:**
- Should load correctly (no crash, no black level)
- Slots 3,4 will use Goblin/Shaman animations
- Needs testing if slots 3,4 can actually spawn monsters

---

## Assignment Structure Analysis

### Vanilla Assignments (3 slots):
```
Slot 0: 00 00 00 00 00 02 00 40  (Lv20.Goblin)
Slot 1: 01 01 00 00 01 03 00 40  (Goblin-Shaman)
Slot 2: 02 03 00 00 02 04 00 40  (Giant-Bat)
```

### Pattern Analysis:
```
Byte[0] = Anim table index (0, 1, 2)
Byte[1] = ? (matches byte[0] for slots 1,2)
Byte[2-3] = 0x0000
Byte[4] = Slot index (0, 1, 2)
Byte[5] = Monster ID? (2, 3, 4)
Byte[6] = 0x00
Byte[7] = 0x40 (flag)
```

### New Assignments (reusing anims):
```
Slot 3: 00 00 00 00 03 02 00 40  (reuses anim 0 - Goblin)
Slot 4: 01 01 00 00 04 03 00 40  (reuses anim 1 - Shaman)
```

---

## Limitations Discovered

### Cannot Change:
1. **Header count @ 0xF7A851** - Causes infinite loading
2. **Anim tables count** - Controlled by header, adding crashes
3. **Anim records count** - Presumably also controlled by header
4. **Stats count** - Causes black level (unknown validation)

### Can Change:
1. **Middle count** - Can be set to 5
2. **Assignments count** - Can add more, reusing existing anims

---

## Next Steps

1. **Test Phase 3** (reuse anims)
   - Verify it loads correctly
   - Test if formations can spawn using slots 3,4
   - Check if monsters appear correctly in-game

2. **If Phase 3 works:**
   - All 5 slots share only 3 animation sets
   - Slots 0,3 = Goblin animations
   - Slots 1,4 = Shaman animations
   - Slot 2 = Bat animations
   - This allows 5 formation slots but only 3 visual types

3. **Alternative: Investigate stats black level**
   - Find why adding stats breaks rendering
   - May be another offset/count to update
   - Could allow different stats per slot

---

## Technical Notes

### Formation Offset References
Updated for all changes (4 locations):
- 0x18920CB
- 0x1892133
- 0x189234B
- 0x18923B3

### Size Shifts
- Adding assignments: +16 bytes (2×8)
- Adding stats: +192 bytes (2×96)
- Adding anim tables: +16 bytes (2×8)

---

## Files Created

### Test Scripts
- `test_incremental_changes.py` - Phase 1 & 2 tests
- `test_add_slots_header3.py` - Phase 2 detailed tests
- `test_reuse_anims.py` - Phase 3 (current)

### Test Versions (output/test_versions/)
- `test1_counts_only.ALL` - Both counts changed
- `test7_header_count_only.ALL` - Header count only
- `testA_middle5_header3_baseline.ALL` - Middle count only
- `testB_middle5_header3_add_stats.ALL` - Middle + stats
- `testC_middle5_header3_add_assignments.ALL` - Middle + assignments
- `testD_middle5_header3_add_anim_tables.ALL` - Middle + anim tables

### Documentation
- `MONSTER_SLOTS_RESEARCH_SUMMARY.md` - Initial research
- `MONSTER_SLOTS_TEST_RESULTS.md` - This file

---

**Status:** Phase 3 in testing (reuse anims approach)
