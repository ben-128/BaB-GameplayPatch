# Analysis: Infinite Loading Loop Structure

## Assembly Code at PC=0x80030A9C

```assembly
0x80030A0C: addiu v0, v1, 1      # v0 = v1 + 1 (increment counter?)
...
0x80030A1C: slt v0, v0, v1       # v0 = (v0 < v1) ? 1 : 0
0x80030A20: beq v0, zero, 0x80030a9c  # if v0==0 (counter >= limit), branch to exit
...
0x80030A28: lui a0, 0x8004       # Load upper immediate
0x80030A2C: addiu a0, a0, 19236  # a0 = address (probably pointer to data)
...
0x80030A94: j 0x80030aa0         # Jump forward (exit path)
0x80030A98: addiu v0, zero, -1   # Delay slot: v0 = -1
0x80030A9C: addu v0, zero, zero  # PC STUCK HERE: v0 = 0
```

## Loop Structure

This is a **for loop counting animation tables**:

```c
for (i = 0; i < header_count; i++) {
    load_animation_table(i);
    if (!success) {
        return 0;  // STUCK HERE
    }
}
```

**Key instructions:**
- `0x80030A1C: slt v0, v0, v1` - Compare counter to limit
- `0x80030A20: beq v0, zero, 0x80030a9c` - Exit loop if counter >= limit

**Problem:**
- v1 = 5 (header_count)
- Loop tries to load 5 animation tables (indices 0-4)
- Tables 3-4 don't exist
- Load fails, code branches to 0x80030A9C
- Sets v0=0 (failure) and gets stuck

## Solution Options

### Option 1: Patch the Limit (BEST)
Change the comparison limit from 5 to 3:
- Find where v1 is loaded with value 5
- Change it to 3
- Loop will only try to load 3 tables (which exist)

### Option 2: Patch the Branch
Make the branch at 0x80030A20 always exit:
- Change `beq v0, zero, 0x80030a9c` to `beq v0, v0, 0x80030a9c` (always true)
- But this makes loop never execute - BAD

### Option 3: NOP the Failure Path
At 0x80030A9C, instead of setting v0=0, keep it as success:
- Change `addu v0, zero, zero` to `addiu v0, zero, 1`
- But this won't help because we're already stuck at 0x80030A9C

## Recommended Fix

**Find where v1 gets value 5 and change to 3**

Need to look BEFORE 0x80030A1C to find:
```assembly
li v1, 5           # Load immediate 5
# OR
lw v1, offset(reg) # Load from memory (header_count @ 0xF7A851)
```

Then patch that instruction to use value 3 instead.
