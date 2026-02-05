import struct
import sys

BLAZE_ALL = r'D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL'
GROUP_START = 0xF7A97C
SCAN_SIZE   = 512
SCAN_START  = GROUP_START - SCAN_SIZE

TARGET_IDS = {
    0x54: 'Lv20.Goblin',
    0x3B: 'Goblin-Shaman',
    0x31: 'Giant-Bat',
}
CONTEXT = 8

def hex_ascii_dump(data, base_offset):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        abs_off = base_offset + i
        rel_off = abs_off - GROUP_START
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        hex_part = hex_part.ljust(47)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  {abs_off:08X}  (rel {rel_off:+5d})  {hex_part}  |{ascii_part}|')
    return chr(10).join(lines)

def search_ids(data):
    for target_val, name in sorted(TARGET_IDS.items()):
        target_byte = target_val & 0xFF
        print(f'{chr(10)}' + '='*72)
        print(f'  Searching for ID 0x{target_val:02X} ({target_val}) = {name}')
        print('='*72)
        hits = 0
        for i in range(len(data)):
            if data[i] != target_byte:
                continue
            hits += 1
            abs_off = SCAN_START + i
            rel_off = i - SCAN_SIZE
            ctx_lo = max(0, i - CONTEXT)
            ctx_hi = min(len(data), i + 1 + CONTEXT)
            ctx = data[ctx_lo:ctx_hi]
            marker_pos = i - ctx_lo
            u8_val = data[i]
            u16_val = struct.unpack_from('<H', data, i)[0] if i + 1 < len(data) else None
            u16_hi_val = struct.unpack_from('<H', data, i - 1)[0] if i >= 1 else None
            ctx_hex = ''
            for j, b in enumerate(ctx):
                if j == marker_pos:
                    ctx_hex += f'[{b:02X}]'
                else:
                    ctx_hex += f' {b:02X} '
            ctx_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print(f'{chr(10)}  Hit #{hits}  absolute=0x{abs_off:08X}  relative_to_group={rel_off:+d}  (scan index {i})')
            print(f'    Context bytes:  {ctx_hex}')
            print(f'    Context ASCII:  |{ctx_ascii}|')
            print(f'    As uint8  : {u8_val} (0x{u8_val:02X})')
            if u16_val is not None:
                print(f'    As uint16 LE (this byte = low): {u16_val} (0x{u16_val:04X})')
            if u16_hi_val is not None:
                print(f'    As uint16 LE (this byte = high, prev byte = low): {u16_hi_val} (0x{u16_hi_val:04X})')
            flags = []
            if u8_val == target_val:
                flags.append('uint8 MATCH')
            if u16_val is not None and u16_val == target_val:
                flags.append('uint16-LE MATCH (low byte)')
            if u16_hi_val is not None and u16_hi_val == target_val:
                flags.append('uint16-LE MATCH (high byte of previous word)')
            if i % 4 == 0 and i + 4 <= len(data):
                u32_val = struct.unpack_from('<I', data, i)[0]
                if u32_val == target_val:
                    flags.append(f'uint32-LE MATCH (aligned) = {u32_val}')
            print(f'    Plausibility : {chr(44).join(flags) if flags else chr(45)}')
        if hits == 0:
            print('  (no occurrences found)')
        else:
            print(f'{chr(10)}  Total hits for 0x{target_val:02X}: {hits}')

def main():
    print(f'BLAZE.ALL : {BLAZE_ALL}')
    print(f'Group start offset : 0x{GROUP_START:08X}')
    print(f'Scan window        : 0x{SCAN_START:08X} .. 0x{GROUP_START:08X} ({SCAN_SIZE} bytes)')
    print()
    with open(BLAZE_ALL, 'rb') as f:
        f.seek(SCAN_START)
        data = f.read(SCAN_SIZE)
    if len(data) < SCAN_SIZE:
        print(f'WARNING: only read {len(data)} bytes (expected {SCAN_SIZE})')
    print('='*72)
    print('  HEX + ASCII DUMP of 512 bytes before group start')
    print('='*72)
    print(hex_ascii_dump(data, SCAN_START))
    print()
    with open(BLAZE_ALL, 'rb') as f:
        f.seek(GROUP_START)
        group_data = f.read(96 * 3)
    print('='*72)
    print(f'  REFERENCE: first 3 group entries (96 bytes each) at 0x{GROUP_START:08X}')
    print('='*72)
    print(hex_ascii_dump(group_data, GROUP_START))
    print()
    search_ids(data)
    print(chr(10) + '='*72)
    print('  CLUSTER ANALYSIS -- regions where multiple IDs appear within <=16 bytes')
    print('='*72)
    all_hits = []
    for target_val, name in TARGET_IDS.items():
        for i in range(len(data)):
            if data[i] == (target_val & 0xFF):
                all_hits.append((i, target_val, name))
    all_hits.sort()
    WINDOW = 16
    found_cluster = False
    visited = set()
    for idx in range(len(all_hits)):
        pos, val, name = all_hits[idx]
        if pos in visited:
            continue
        cluster = [(pos, val, name)]
        for pos2, val2, name2 in all_hits[idx+1:]:
            if pos2 - pos <= WINDOW:
                cluster.append((pos2, val2, name2))
        unique_ids = set(v for _, v, _ in cluster)
        if len(unique_ids) >= 2:
            found_cluster = True
            for p, v, n in cluster:
                visited.add(p)
            abs_start = SCAN_START + cluster[0][0]
            abs_end   = SCAN_START + cluster[-1][0]
            print(f'{chr(10)}  Cluster at absolute 0x{abs_start:08X}..0x{abs_end:08X} (rel {cluster[0][0]-SCAN_SIZE:+d}..{cluster[-1][0]-SCAN_SIZE:+d})')
            for p, v, n in cluster:
                print(f'    offset {SCAN_START+p:08X} (rel {p-SCAN_SIZE:+d}): 0x{v:02X} ({v}) = {n}')
            c_lo = max(0, cluster[0][0] - 8)
            c_hi = min(len(data), cluster[-1][0] + 9)
            print('    Context dump:')
            print(hex_ascii_dump(data[c_lo:c_hi], SCAN_START + c_lo))
    if not found_cluster:
        print(chr(10) + '  No clusters of 2+ different IDs found within 16-byte windows.')
    print(chr(10) + 'Done.')

if __name__ == "__main__":
    main()
