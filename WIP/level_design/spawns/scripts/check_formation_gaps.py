#!/usr/bin/env python3
# -*- coding: cp1252 -*-
"""Check what's in the 4-byte gaps between formation groups."""
import struct
from pathlib import Path

BLAZE = Path(r"C:\Perso\BabLangue\Blaze  Blade  Eternal Quest (US)-1644762377\GameplayPatch\output\BLAZE.ALL").read_bytes()

# Cavern F1 Area 1 - well-known data
records = [
    (0xF7AFFC, "F00[0]"), (0xF7B01C, "F00[1]"), (0xF7B03C, "F00[2]"),
    (0xF7B060, "F01[0]"), (0xF7B080, "F01[1]"), (0xF7B0A0, "F01[2]"),
    (0xF7B0C4, "F02[0]"), (0xF7B0E4, "F02[1]"),
    (0xF7B108, "F03[0]"), (0xF7B128, "F03[1]"), (0xF7B148, "F03[2]"), (0xF7B168, "F03[3]"),
    (0xF7B18C, "F04[0]"), (0xF7B1AC, "F04[1]"), (0xF7B1CC, "F04[2]"), (0xF7B1EC, "F04[3]"),
    (0xF7B210, "F05[0]"), (0xF7B230, "F05[1]"), (0xF7B250, "F05[2]"),
    (0xF7B274, "F06[0]"), (0xF7B294, "F06[1]"), (0xF7B2B4, "F06[2]"), (0xF7B2D4, "F06[3]"),
    (0xF7B2F8, "F07[0]"), (0xF7B318, "F07[1]"), (0xF7B338, "F07[2]"), (0xF7B358, "F07[3]"),
]

print("=== GAPS BETWEEN FORMATION RECORDS (Cavern F1 Area 1) ===")
print()
for i in range(len(records) - 1):
    off1, name1 = records[i]
    off2, name2 = records[i + 1]
    end1 = off1 + 32
    gap = off2 - end1
    if gap > 0:
        gap_data = BLAZE[end1:off2]
        gap_hex = ' '.join('{:02X}'.format(b) for b in gap_data)
        print("{} -> {} : gap={} bytes at 0x{:X}: [{}]".format(
            name1, name2, gap, end1, gap_hex))
    elif gap == 0:
        pass  # contiguous, skip
    else:
        print("{} -> {} : OVERLAP {} bytes!".format(name1, name2, gap))

# Also check Forest F1 Area 1
print()
print("=== GAPS: Forest F1 Area 1 ===")
forest_records = [
    (0x148CCC4, "F00[0]"), (0x148CCE4, "F00[1]"), (0x148CD04, "F00[2]"),
    (0x148CD28, "F01[0]"), (0x148CD48, "F01[1]"), (0x148CD68, "F01[2]"),
    (0x148CD8C, "F02[0]"), (0x148CDAC, "F02[1]"), (0x148CDCC, "F02[2]"),
    (0x148CDF0, "F03[0]"), (0x148CE10, "F03[1]"), (0x148CE30, "F03[2]"), (0x148CE50, "F03[3]"),
    (0x148CE74, "F04[0]"), (0x148CE94, "F04[1]"), (0x148CEB4, "F04[2]"),
    (0x148CED8, "F05[0]"), (0x148CEF8, "F05[1]"), (0x148CF18, "F05[2]"),
    (0x148CF38, "F05[3]"), (0x148CF58, "F05[4]"),
]
for i in range(len(forest_records) - 1):
    off1, name1 = forest_records[i]
    off2, name2 = forest_records[i + 1]
    end1 = off1 + 32
    gap = off2 - end1
    if gap > 0:
        gap_data = BLAZE[end1:off2]
        gap_hex = ' '.join('{:02X}'.format(b) for b in gap_data)
        print("{} -> {} : gap={} bytes at 0x{:X}: [{}]".format(
            name1, name2, gap, end1, gap_hex))

# What's AFTER the last formation record?
print()
print("=== AFTER LAST FORMATION (Cavern) ===")
last_end = 0xF7B358 + 32  # F07[3] end
after = BLAZE[last_end:last_end + 64]
print("0x{:X}:".format(last_end))
for i in range(0, 64, 16):
    chunk = after[i:i+16]
    hex_str = ' '.join('{:02X}'.format(b) for b in chunk)
    print("  0x{:X}: {}".format(last_end + i, hex_str))

print()
print("=== AFTER LAST FORMATION (Forest) ===")
last_end_f = 0x148CF58 + 32  # F05[4] end
after_f = BLAZE[last_end_f:last_end_f + 64]
print("0x{:X}:".format(last_end_f))
for i in range(0, 64, 16):
    chunk = after_f[i:i+16]
    hex_str = ' '.join('{:02X}'.format(b) for b in chunk)
    print("  0x{:X}: {}".format(last_end_f + i, hex_str))
