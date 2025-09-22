from src.mappers import NROMMapper
from src.Bus import Bus
import sys, os

if len(sys.argv) < 2:
    print('Uso: python tools/inspect_rom_map.py <rom.nes>')
    sys.exit(1)

rom = sys.argv[1]
with open(rom, 'rb') as f:
    data = f.read()

if len(data) >= 16 and data[:4] == b'NES\x1A':
    prg_units = data[4]
    prg_size = prg_units * 16384
    trainer = (data[6] & 0x04) != 0
    prg_start = 16 + (512 if trainer else 0)
    prg = data[prg_start: prg_start + min(prg_size, 32768)]
else:
    prg = data

b = Bus()
m = NROMMapper(prg)
b.install_mapper(m)

print(f'PRG len used: {len(prg)}')
for addr in range(0xFFB0, 0x10010, 0x10):
    line = f'${addr:05X}: '
    for i in range(16):
        a = (addr + i) & 0xFFFF
        v = b.read(a)
        line += f'{v:02X} '
    print(line)
