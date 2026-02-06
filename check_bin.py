"""Quick script to compare formation data in BLAZE.ALL vs BIN."""
import sys

SECTOR_RAW = 2352
USER_OFF = 24
USER_SIZE = 2048

blaze_offset = 0xF7AFFC
check_len = 896

blaze = open(r'output\BLAZE.ALL', 'rb').read()
blaze_data = blaze[blaze_offset:blaze_offset+check_len]

bin_path = r'output\Blaze & Blade - Patched.bin'
with open(bin_path, 'rb') as f:
    bin_bytes = f.read()

for copy_idx, lba_base in enumerate([163167, 185765]):
    extracted = bytearray()
    remaining = check_len
    cur = blaze_offset
    while remaining > 0:
        sec = cur // USER_SIZE
        off_in_sec = cur % USER_SIZE
        to_read = min(remaining, USER_SIZE - off_in_sec)
        bin_off = (lba_base + sec) * SECTOR_RAW + USER_OFF + off_in_sec
        extracted.extend(bin_bytes[bin_off:bin_off+to_read])
        remaining -= to_read
        cur += to_read

    match = (bytes(extracted) == blaze_data)
    print('BIN copy {} (LBA {}): {}'.format(
        copy_idx+1, lba_base,
        'MATCHES BLAZE.ALL' if match else 'DIFFERS from BLAZE.ALL!'))
    if not match:
        for i in range(min(len(extracted), len(blaze_data))):
            if extracted[i] != blaze_data[i]:
                print('  First diff at byte {}: BIN=0x{:02X} vs BLAZE=0x{:02X}'.format(
                    i, extracted[i], blaze_data[i]))
                break
        print('  BIN first 96 bytes:')
        for j in range(0, 96, 32):
            row = extracted[j:j+32]
            print('    +{:3d}: {}'.format(j, ' '.join('{:02X}'.format(b) for b in row)))
        print('  BLAZE first 96 bytes:')
        for j in range(0, 96, 32):
            row = blaze_data[j:j+32]
            print('    +{:3d}: {}'.format(j, ' '.join('{:02X}'.format(b) for b in row)))
