"""Re-extract original formations from clean BLAZE.ALL using the extractor's
scan approach (pattern matching on FF FF FF FF FF FF terminators)."""
import struct
from collections import Counter

clean = open(r'Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL', 'rb').read()

group_offset = 0xF7A97C
num_monsters = 3
monsters = ['Lv20.Goblin', 'Goblin-Shaman', 'Giant-Bat']
script_start = group_offset + num_monsters * 96

# Scan area: script_start to +8KB
scan_end = script_start + 8192
data = clean[script_start:scan_end]

# Find all 6-byte FF blocks
ff6_positions = []
i = 0
while i < len(data) - 5:
    if data[i:i+6] == b'\xff\xff\xff\xff\xff\xff':
        ff6_positions.append(i)
        i += 6
    else:
        i += 1

# Extract formation template records
formations_recs = []
for ff_pos in ff6_positions:
    rec_start = ff_pos - 26
    if rec_start < 0:
        continue
    rec = data[rec_start:ff_pos + 6]
    if len(rec) != 32:
        continue
    byte8 = rec[8]
    byte9 = rec[9]
    if byte8 >= num_monsters:
        continue
    byte10_11 = rec[10:12]
    if 0xFF in byte10_11:
        continue
    coord = struct.unpack_from('<hhh', rec, 12)
    if any(abs(c) > 15000 for c in coord):
        continue
    if byte9 == 0xFF and coord == (0, 0, 0):
        abs_offset = script_start + rec_start
        has_inner_ff = (rec[4:8] == b'\xff\xff\xff\xff')
        formations_recs.append({
            'abs_offset': abs_offset,
            'slot': byte8,
            'is_start': has_inner_ff,
        })

# Group by start delimiter + contiguity
groups = []
current = []
for rec in formations_recs:
    if rec['is_start'] and current:
        groups.append(current)
        current = []
    elif current:
        if rec['abs_offset'] != current[-1]['abs_offset'] + 32:
            groups.append(current)
            current = []
    current.append(rec)
if current:
    groups.append(current)

print("=== Original formations (clean BLAZE.ALL, scanner method) ===")
print()
for fidx, formation in enumerate(groups):
    slots = [r['slot'] for r in formation]
    c = Counter(slots)
    comp = ' + '.join('{}x{}'.format(c[s], monsters[s]) for s in sorted(c))
    first_off = formation[0]['abs_offset']
    last_off = formation[-1]['abs_offset']
    suffix_off = last_off + 32
    suffix = clean[suffix_off:suffix_off + 4]
    print("  F{:02d}: {} slots [{}]".format(fidx, len(slots), comp))
    print("        offset=0x{:X}  end=0x{:X}  suffix={}".format(
        first_off, last_off + 32, suffix.hex()))

# Show contiguity
print()
print("=== Contiguity check ===")
if groups:
    first_abs = groups[0][0]['abs_offset']
    print("First formation starts at: 0x{:X}".format(first_abs))
    for fidx, formation in enumerate(groups):
        f_start = formation[0]['abs_offset']
        f_end = formation[-1]['abs_offset'] + 32 + 4  # records + suffix
        if fidx > 0:
            prev_end = groups[fidx-1][-1]['abs_offset'] + 32 + 4
            gap = f_start - prev_end
            if gap != 0:
                print("  !!! GAP of {} bytes between F{:02d} and F{:02d}".format(
                    gap, fidx-1, fidx))
        print("  F{:02d}: 0x{:X} - 0x{:X} ({} bytes)".format(
            fidx, f_start, f_end, f_end - f_start))

    total_end = groups[-1][-1]['abs_offset'] + 32 + 4
    total_span = total_end - first_abs
    total_slots = sum(len(g) for g in groups)
    print()
    print("Total: {} formations, {} slots".format(len(groups), total_slots))
    print("Span: 0x{:X} to 0x{:X} = {} bytes".format(first_abs, total_end, total_span))
    print("Expected: {} * 32 + {} * 4 = {}".format(
        total_slots, len(groups), total_slots * 32 + len(groups) * 4))
