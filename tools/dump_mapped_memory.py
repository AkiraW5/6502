import sys
from src.mappers import NROMMapper
from src.Bus import Bus

if len(sys.argv) < 2:
    print('Uso: python tools/dump_mapped_memory.py <rom.nes>')
    sys.exit(1)

rom = sys.argv[1]
with open(rom, 'rb') as f:
    data = f.read()

if len(data) >= 16 and data[:4] == b'NES\x1A':
    prg_units = data[4]
    trainer = (data[6] & 0x04) != 0
    prg_start = 16 + (512 if trainer else 0)
    prg_size = prg_units * 16384
    prg = data[prg_start: prg_start + min(prg_size, 32768)]
else:
    prg = data

b = Bus()
m = NROMMapper(prg)
b.install_mapper(m)

# generate lines from 0x8000 to 0xFFFF
start_addr = 0x8000
addr = start_addr
lines = []
while addr <= 0xFFFF:
    chunk = []
    hexbytes = []
    for i in range(16):
        curr = addr + i
        if curr > 0xFFFF:
            break
        offset = curr - start_addr
        if 0 <= offset < len(prg):
            bval = prg[offset]
        else:
            bval = 0xFF
        hexbytes.append(f"{bval:02X}")
        chunk.append(bval)
    # print only last few lines near FF00..FFFF
    if addr >= 0xFFB0:
        print(f"${addr:04X}: {' '.join(hexbytes)}")
    addr += 16
