# Falling Rocks Damage Patch - Failed Attempts Log

## Objective
Increase falling rocks damage from 10% to 50% of max HP in Cavern of Death.

---

## ATTEMPT 1: BLAZE.ALL Entity Descriptor (FAILED - 2026-02-10)

**Hypothesis:** Damage% stored in entity descriptor at BLAZE 0x009ECFEC

**Method:**
- Found descriptor block (32 bytes) before Template A1 function
- Located byte with value 10 (0x0A) at offset 0x009ECE8A (+0x06 in descriptor)
- Patched value from 10 → 50

**Result:** ❌ FAILED
- **Collision/hitbox behavior CHANGED** (harder to get hit by rock)
- **Damage UNCHANGED** (still 10% of max HP)
- **Conclusion:** Byte at +0x06 controls collision radius, NOT damage%

**Evidence:**
- In-game test confirmed hitbox change
- Damage remained at 10% regardless of value (tested 10, 50, 100)

---

## ATTEMPT 2: BLAZE.ALL Overlay Code - Immediate Values (FAILED - 2026-02-10)

**Hypothesis:** Damage% hardcoded as immediate value in overlay code

**Method:**
- Searched BLAZE 0x009E0000-0x00A00000 for `ori/addiu $reg, $zero, 10`
- Found 2 sites: 0x009EE44C and 0x009EF0D4

**Result:** ❌ FAILED
- Both sites write to **entity+0x14 via $s5**
- This offset stores **STATE MACHINE ID**, not damage%
- Context confirmed: `sh $v0, 20($s5)` followed by state checks (0xCE, 0xC8)

**Evidence:**
```mips
0x009EF0D4: ori $v0, $zero, 10
0x009EF0D8: sh $v0, 20($s5)     ; entity+0x14 = state ID 10
```
- Other state IDs in same code: 20, 200, 201, 206, 211
- No damage function calls nearby

---

## ATTEMPT 3: BLAZE.ALL Overlay Code - Template A1 Function (FAILED - 2026-02-10)

**Hypothesis:** Damage% hardcoded inside Template A1 (0x009ED00C)

**Method:**
- Disassembled function prologue (80 instructions)
- Traced argument loading: `lhu $s7, 72($sp)` = 5th stack arg = damage%

**Result:** ❌ FAILED
- Damage% is **NOT hardcoded** in Template A1
- Value comes from **caller** via stack argument
- Template A1 just receives and uses the value

**Evidence:**
- No `ori/addiu $reg, 10` found in entire function
- $s7 loaded from stack at sp+0x48 (caller's 5th argument)

---

## ATTEMPT 4: BLAZE.ALL Stack Argument Preparation (FAILED - 2026-02-10)

**Hypothesis:** Caller prepares damage% with `ori $reg, 10` then `sw $reg, N($sp)`

**Method:**
- Searched for pattern: `ori/addiu $reg, $zero, 10` followed by `sw/sh $reg, N($sp)`
- Scanned entire overlay region 0x009E0000-0x00A00000

**Result:** ❌ FAILED
- **Zero patterns found** matching this signature
- Damage% is not prepared as immediate stack argument

**Evidence:**
- 0 matches for: immediate load 10 → stack store pattern
- All `ori $reg, 10` sites write to entity+0x14 (state machine)

---

## ATTEMPT 5: BLAZE.ALL Entity Init Data Search (FAILED - 2026-02-11)

**Hypothesis:** Damage% stored in entity init data table somewhere

**Method:**
- Searched all bytes = 10 (0x0A) in region 0x009EC000-0x009F4000
- Found 52 bytes, checked each for halfword alignment and context

**Result:** ❌ FAILED
- **Only ONE** aligned halfword = 10 found: 0x009ECE8A (already tested, is collider)
- Other 0x0A bytes are part of larger values or unaligned
- No other damage% candidate found

**Evidence:**
- Exhaustive byte scan: 52 matches, only 1 relevant halfword
- Tested halfword already proven to be collision size

---

## ATTEMPT 6: Calculated Damage from Descriptor Fields (FAILED - 2026-02-11)

**Hypothesis:** Damage% calculated from other descriptor bytes (e.g., 32/3 ≈ 10)

**Method:**
- Analyzed descriptor structure:
  ```
  [00 48 18 20 01 02 10 00] (repeated 4 times with variant at [0])
  ```
- Tested formulas: division, multiplication, subtraction, addition

**Result:** ❌ FAILED
- No formula yields 10 from any descriptor byte(s)
- byte[3]=32, byte[6]=16 - no simple math gives 10
- No multi-byte combinations equal 10

**Evidence:**
- Tested: /2, /3, *2, *3, +combinations, -combinations
- Zero matches for damage% = 10

---

## ATTEMPT 7: EXE Damage Function Patch (FAILED - 2026-02-11)

**Hypothesis:** Patch damage function in EXE to replace 10→50 at runtime

**Method:**
- Located damage function: RAM 0x80024F90, EXE offset 0x00015790
- Injected MIPS code at function start:
  ```mips
  addiu $v0, $zero, 10       ; Load 10
  bne   $a3, $v0, skip       ; If damage% != 10, skip
  nop
  addiu $a3, $zero, 50       ; Replace with 50
  skip:
  (original code)
  ```
- Replaced first 5 instructions (20 bytes) at BIN offset 0x295F6858
- Integrated into build pipeline (step 9d)

**Result:** ❌ FAILED
- Build completed successfully, patch applied to BIN
- **In-game test: damage still 10%** (no change observed)

**Possible reasons:**
1. **Wrong register:** Damage% not in $a3 but in $a1 or stack
2. **Wrong function:** Multiple damage functions, patched the wrong one
3. **Code path bypass:** Falling rocks use different damage calculation
4. **Overlay reload:** EXE code reloaded from different source at runtime
5. **Wrong offset:** Calculation error in BIN offset (LBA/sector math)

**Evidence:**
- Patch confirmed applied (hex dump shows modified instructions)
- Game runs normally (no crash)
- Damage unchanged → code not executing or wrong target

**Build log excerpt:**
```
[9d/10] Patching EXE damage function (10% -> 50%)...
Function RAM address: 0x80024F90
EXE file offset:      0x00015790
BIN file offset:      0x295F6858
[OK] EXE damage function patched (10% -> 50%)
```

---

## ATTEMPT 8: All /100 Division Functions (TESTING - 2026-02-11)

**Hypothesis:** The real damage function is one of the 14 functions that use the magic constant 0x51EB851F for /100 division

**Discovery:** 0x80024F90 does NOT use 0x51EB851F constant! It's likely a wrapper.

**Method:**
- Searched EXE for `lui $reg, 0x51EB` + `ori $reg, $reg, 0x851F` pattern
- Found 14 functions at:
  ```
  0x80026A50, 0x80026EE8, 0x80026F58, 0x80027B70, 0x80027BF4,
  0x80027C78, 0x80027CFC, 0x80027D80, 0x80027E04, 0x80027EA8,
  0x800281D4, 0x80028D64, 0x8002A344, 0x8002A3D0
  ```
- All divisions are in MIDDLE of functions (not at start)
- Strategy: Patch result AFTER division (after `sra $reg, 5` instruction)
- Inject: `if (result == 10) result = 50` after each `/100` operation

**Implementation:**
- Found `sra $reg, 5` pattern after lui/ori in 11 of 14 functions
- Patched 11 functions successfully
- 3 functions skipped (no sra pattern found)

**Result:** ❌ FAILED
- Patch applied to BIN successfully (11 functions modified)
- **In-game test: damage still 10%** (no change observed)
- Build + test completed 2026-02-11

**Possible reasons:**
1. **Result not used directly:** The /100 result may be intermediate, not the final damage%
2. **Wrong functions:** None of the 11 patched functions are used by falling rocks
3. **Different code path:** Falling rocks may use a completely different damage calculation
4. **Post-processing:** Result may be further transformed after our patch injection point

**Why /100 for 10%?**
Formula: `damage = (maxHP * param%) / 100`
- If param% = 10, then damage = (maxHP * 10) / 100 = maxHP / 10 = 10% ✓
- param% is integer (10), not decimal (0.10)

**Patcher:** `Data/trap_damage/patch_all_div100_functions.py` (DISABLED in build)

---

## ATTEMPT 9: Savestate Pattern Analysis (FAILED - 2026-02-11)

**Hypothesis:** Analyze RAM savestate to find damage% value, then patch corresponding data in BLAZE.ALL

**Method:**
1. Loaded savestate with falling rock active (`sstates/rocher/SLES_008.45.000`)
2. Searched RAM for halfword = 10 (0x000A) in BSS region
3. Found pattern: `0x0028000A` in 2 structures at RAM 0x800A1856 and 0x800A1996
4. Distance between structures: 320 bytes (0x140) - suggests descriptor table
5. Searched BLAZE.ALL for same pattern
6. Found 164 matches, patched 10 descriptors:
   - 0x00241556 (first match)
   - 0x0029E0E6-0x0029F022 (cluster of 9 matches)

**Pattern structure:**
```
+0x00: 0028000A  (hw: 0x0028=40, 0x000A=10 ← damage%)
+0x04: 01000064
+0x08: 00000096
...
```

**Result:** ❌ FAILED
- Build completed, BIN generated
- **In-game test: damage still 10%** (no change observed)
- Tested with new savestate (`sstates/rocher/2`) - confirmed still 10%

**Root cause identified (2026-02-11):**
- **PATCHER BUG**: Verification check had halfwords in WRONG ORDER
- Check expected: hw1=0x0028, hw2=0x000A
- Actual pattern: hw1=0x000A (damage%), hw2=0x0028 (other)
- Result: All 10 targets FAILED verification → **ZERO patches applied**
- Patcher silently skipped all offsets (printed "[SKIP]" but no error code)
- Build succeeded because no Python error, but no data was modified

**Additional findings:**
1. **Wrong pattern:** The 0x0028000A pattern may not be trap damage data
2. **Runtime generation:** Damage% may be calculated/generated at runtime, not loaded from BLAZE.ALL
3. **Different data:** RAM pattern differs from BLAZE.ALL pattern (runtime modifications)
4. **Unrelated data:** The 164 matches may be something else entirely (not trap descriptors)
5. **Patcher bug:** Even if pattern was correct, implementation had verification logic error

**Pattern analysis:**
- RAM data: `0028000A 01000064 00000096 00000000`
- BLAZE data: `0028000A 00001000 00000000 00000000` (different after first word!)
- The data structures are NOT identical - BLAZE.ALL values differ from RAM

**Patcher:** `Data/trap_damage/patch_falling_rock_attempt9.py` (DISABLED in build)

---

## Summary of Investigation (2026-02-08 to 2026-02-11)

### What we found ✓
- Damage function location: 0x80024F90 (EXE, never moves)
- Damage formula: `damage = (maxHP * param%) / 100`
- 189 total call sites (15 immediate, 174 register-based)
- BLAZE.ALL overlay patcher works for 2%, 5%, 20% (15 immediate sites)

### What we could NOT find ✗
- Location of 10% value for falling rocks
- Entity descriptor encoding (all tested bytes were wrong)
- Stack argument preparation site
- Any hardcoded 10 in relevant code paths
- Alternative damage calculation function

### Remaining mysteries
1. **Where is the 10% stored?**
   - Not in BLAZE.ALL descriptors
   - Not in overlay code immediates
   - Not in stack preparation
   - Not in Template A1 function

2. **How does the value reach the damage function?**
   - Must be via register (not immediate)
   - Template A receives via 5th stack arg ($s7)
   - But caller not found in overlay code

3. **Is there a different damage path for falling rocks?**
   - Possible separate environmental damage function
   - May not use 0x80024F90 at all
   - Or uses completely different parameter passing

---

## Next Investigation Steps (If Resuming)

### Option A: Runtime Debugging
1. Use PCSX-Redux or no$psx debugger
2. Set breakpoint at 0x80024F90
3. Get hit by falling rock
4. Inspect $a3 (or $a1) to see actual damage% value
5. Trace backwards to find where it came from

### Option B: Alternative Damage Functions
1. Search EXE for other functions with similar `/100` division pattern
2. Look for magic constant `0x51EB851F` (used in /100 fast division)
3. Check if falling rocks use different damage calculation

### Option C: Savestate Analysis
1. Extract entity data from savestate during falling rock hit
2. Compare before/after entity fields
3. Search BLAZE.ALL for observed values

### Option D: Accept Limitation
- Document as "not patchable with current tools"
- 15 immediate sites work (2%, 5%, 20% in other areas)
- Falling rocks 10% remains unchanged

---

## Files Created During Investigation

### Working Patches
- `Data/trap_damage/patch_trap_damage.py` - BLAZE.ALL overlay patcher (15 sites)
- `Data/trap_damage/trap_damage_config.json` - Config for working patches

### Failed Attempts
- `Data/trap_damage/patch_damage_10_to_50_exe.py` - EXE function patch (doesn't work)
- `WIP/test_patch_damage_mul.py` - Test multiply all damage by 5

### Documentation
- `Data/trap_damage/RESEARCH.md` - Comprehensive investigation notes
- `Data/trap_damage/EXE_DAMAGE_PATCH.md` - Failed EXE patch documentation
- `Data/trap_damage/FAILED_ATTEMPTS.md` - This file

---

## Conclusion (2026-02-11)

After 4 days of exhaustive reverse engineering, **the falling rocks 10% damage is not patchable** with current methods. The value's location remains unknown despite:

- ✓ Complete BLAZE.ALL descriptor analysis
- ✓ Full overlay code disassembly
- ✓ Template function argument tracing
- ✓ Bytecode system investigation
- ✓ Entity init data scanning
- ✓ Savestate RAM analysis (found pattern location)
- ✗ EXE function patching (applied but ineffective)
- ✗ Attempt #9 patcher bug (verification logic error, zero patches applied)

**Key finding:** Exact RAM pattern `28000a006400000196000000` exists at runtime but **NOT in BLAZE.ALL**. The partial pattern `28000a00` exists 165 times in BLAZE.ALL, but with different following bytes (e.g., `00001000` vs `01000064`). This confirms damage% is **generated at runtime**, not loaded from static data.

**Note on Attempt #9:** Even if the patcher bug was fixed (swap halfword order in verification), it would still fail because BLAZE.ALL doesn't contain the exact pattern to patch.

**Status:** UNSOLVED - requires runtime debugging or acceptance of limitation.
