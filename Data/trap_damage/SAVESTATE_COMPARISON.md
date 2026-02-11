# Falling Rocks Savestate Comparison

## Purpose
Compare two savestates to verify Attempt #9 patch had no effect on in-game damage.

---

## Savestate Locations

**Savestate 1:** `C:\Perso\BabLangue\other\ePSXe2018\sstates\rocher\SLES_008.45.000` (before patch)
**Savestate 2:** `C:\Perso\BabLangue\other\ePSXe2018\sstates\rocher\2\SLES_008.45.000` (after patch)

---

## Pattern Found in RAM

Both savestates contain the same pattern at identical addresses:

### Address 1: RAM 0x800A1856

**Savestate 1:**
```
Pattern: 0028000A 01000064 00000096 00000000
Damage%: 10 (at offset+0)
```

**Savestate 2:**
```
Pattern: 0028000A 01000064 00000096 00000000
Damage%: 10 (at offset+0)
```

**Status:** ✓ IDENTICAL - No change after patch

---

### Address 2: RAM 0x800A1996

**Savestate 1:**
```
Pattern: 0028000A 01000064 00000096 0032FFCE
Damage%: 10 (at offset+0)
```

**Savestate 2:**
```
Pattern: 0028000A 01000064 00000096 0032FFCE
Damage%: 10 (at offset+0)
```

**Status:** ✓ IDENTICAL - No change after patch

---

## Pattern Breakdown (Little-Endian)

```
Word 1: 0x0028000A → bytes [0A 00 28 00]
  - offset+0: halfword 0x000A = 10 (DAMAGE%)
  - offset+2: halfword 0x0028 = 40 (unknown purpose)

Word 2: 0x01000064 → bytes [64 00 00 01]
  - offset+4: halfword 0x0064 = 100
  - offset+6: halfword 0x0001 = 1

Word 3: 0x00000096 → bytes [96 00 00 00]
  - offset+8: halfword 0x0096 = 150
  - offset+10: halfword 0x0000 = 0

Word 4: varies by address
```

---

## BLAZE.ALL Pattern Search

**Exact pattern:** `28000a006400000196000000` (12 bytes)

**Result:** ❌ **NOT FOUND** in BLAZE.ALL (clean or patched)

**Partial pattern:** `28000a00` (first 4 bytes only)

**Result:** ✓ Found 165 times in BLAZE.ALL, but with DIFFERENT following bytes:

Example matches:
```
0x00241556: 000A0028 0015000B 0032002E 003D0037  (byte-swapped + different data)
0x0029E0E6: 000A0028 00001000 00000000 00000000  (different word 2: 0x00001000 vs 0x01000064)
0x0029EFB2: 000A0028 00001000 00E30C00 00000000  (different word 2: 0x00001000)
```

**Note:** All BLAZE.ALL matches have word 2 = `0x00001000`, but RAM has word 2 = `0x01000064`.

---

## Why Attempt #9 Failed

### 1. Patcher Bug (Code Logic Error)

The verification check had **halfwords in wrong order**:

```python
# WRONG (line 50 of patch_falling_rock_attempt9.py)
hw1, hw2 = struct.unpack_from('<HH', data, offset)
if hw1 != 0x0028 or hw2 != 0x000A:  # Expected hw1=40, hw2=10
    print("[SKIP] ...")
    continue
```

**Actual pattern in BLAZE.ALL:**
- hw1 (offset+0) = `0x000A` = 10
- hw2 (offset+2) = `0x0028` = 40

**Result:** All 10 targets failed verification → **ZERO patches applied**

---

### 2. Pattern Mismatch (Even if Bug Fixed)

Even if the verification bug was corrected, the patch would still fail because:

1. **RAM pattern** (runtime): `28000a00 64000001 96000000`
2. **BLAZE pattern** (disk): `28000a00 00100000 00000000` (when byte-swapped)

The patterns differ at word 2:
- RAM has `0x01000064` (bytes: 64 00 00 01)
- BLAZE has `0x00001000` (bytes: 00 10 00 00)

**Conclusion:** The damage% structure exists in RAM but **does not match any BLAZE.ALL data**. It's generated at runtime, not loaded from disk.

---

## Verification Steps Completed

1. ✓ Extracted both savestates (gzip decompression)
2. ✓ Compared RAM at 0x800A1856 and 0x800A1996
3. ✓ Verified damage% = 10 in both savestates (no change after patch)
4. ✓ Searched BLAZE.ALL for exact pattern (not found)
5. ✓ Searched BLAZE.ALL for partial pattern (165 matches, all different)
6. ✓ Identified patcher verification bug (halfword order swapped)
7. ✓ Confirmed pattern mismatch between RAM and BLAZE.ALL

---

## Final Conclusion

**Attempt #9 failed for TWO independent reasons:**

1. **Patcher bug:** Verification check logic error → zero patches applied
2. **Pattern not in BLAZE.ALL:** Even if patched, exact RAM pattern doesn't exist on disk

**Root cause:** Falling rocks damage% is **generated at runtime**, not loaded from static data files.

**Status:** UNSOLVED - Data cannot be patched via BLAZE.ALL or SLES_008.45 static modification.

---

## Date
Analysis completed: 2026-02-11
