"""
Find a compact table that contains multiple slot_type values together.
This would be the spell set definition table.
"""
import sys
from pathlib import Path

BLAZE_ALL = Path(__file__).parent.parent.parent / "output" / "BLAZE.ALL"

SLOT_TYPES = [
    b'\x00\x00\x00\x00',  # 00000000 Base
    b'\x02\x00\x00\x00',  # 02000000 Shaman Sleep
    b'\x03\x00\x00\x00',  # 03000000 Tower Heal
    b'\x00\x0a\x00\x00',  # 00000a00 Bat FireBullet
    b'\x00\x01\x00\x00',  # 00000100 Rare
]

def find_tables():
    if not BLAZE_ALL.exists():
        print(f"[ERROR] {BLAZE_ALL} not found")
        return 1

    data = BLAZE_ALL.read_bytes()
    print(f"[INFO] Loaded {len(data):,} bytes")
    print(f"[INFO] Looking for tables containing multiple slot_types...\n")

    # For each slot_type, find all its occurrences
    all_offsets = {}
    for st in SLOT_TYPES[1:]:  # Skip 00000000 (too common)
        offsets = []
        offset = 0
        while True:
            offset = data.find(st, offset)
            if offset == -1:
                break
            offsets.append(offset)
            offset += 1
        all_offsets[st] = offsets
        print(f"  {st.hex()}: {len(offsets)} occurrences")

    print(f"\n[INFO] Looking for regions with high concentration...\n")

    # Find regions where multiple different slot_types appear close together
    # Define "close" as within 256 bytes
    WINDOW = 256

    candidates = []

    for st1, offsets1 in all_offsets.items():
        for off1 in offsets1:
            # Count how many OTHER slot_types appear within WINDOW
            nearby = set()
            for st2, offsets2 in all_offsets.items():
                if st2 == st1:
                    continue
                for off2 in offsets2:
                    if abs(off2 - off1) <= WINDOW:
                        nearby.add(st2)

            if len(nearby) >= 2:  # At least 2 other types nearby
                candidates.append((off1, st1, nearby))

    # Deduplicate and sort by offset
    seen_regions = set()
    unique_candidates = []
    for off, st, nearby in candidates:
        region = off // 1024  # Group by 1KB regions
        if region not in seen_regions:
            seen_regions.add(region)
            unique_candidates.append((off, st, nearby))

    unique_candidates.sort()

    print(f"  Found {len(unique_candidates)} candidate table regions:\n")

    for i, (off, st, nearby) in enumerate(unique_candidates[:20]):
        print(f"  [{i+1}] Offset 0x{off:06X} ({off:,})")
        print(f"      Contains: {st.hex()} + {len(nearby)} others")

        # Show 128 bytes around this offset
        start = max(0, off - 32)
        end = min(len(data), off + 96)
        chunk = data[start:end]

        hex_lines = []
        for j in range(0, len(chunk), 16):
            line = chunk[j:j+16]
            hex_str = ' '.join(f'{b:02x}' for b in line)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
            hex_lines.append(f"      {start+j:06X}: {hex_str:48s} {ascii_str}")

        print('\n'.join(hex_lines))
        print()

    return 0

if __name__ == '__main__':
    sys.exit(find_tables())
