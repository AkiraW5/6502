import os, sys
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo not in sys.path:
    sys.path.insert(0, repo)
from src.Bus import Bus
from src.mappers import NROMMapper

rom_name = 'Super Mario Bros. (Europe) (Rev A).nes'
path = os.path.join(repo, rom_name)
if not os.path.exists(path):
    print('ROM not found:', path)
    sys.exit(1)

with open(path, 'rb') as f:
    data = f.read()

prg_units = data[4]
trainer = (data[6] & 0x04) != 0
prg_start = 16 + (512 if trainer else 0)
prg_size = prg_units * 16384
prg = data[prg_start:prg_start+prg_size]

bus = Bus()
mapper = NROMMapper(prg)
mapper.map(bus)

lo = bus.read(0xFFFC)
hi = bus.read(0xFFFD)
reset = (hi<<8)|lo
print('Reset via bus: {:04X}'.format(reset))

pc = reset
print('Bytes via bus at PC:')
for i in range(16):
    a = (pc + i) & 0xFFFF
    print(f"{a:04X}: {bus.read(a):02X}")

print('\nCorresponding PRG offsets:')
for i in range(16):
    a = (pc + i) & 0xFFFF
    offset = a - 0x8000
    if 0 <= offset < len(prg):
        print(f"PRG[{offset}] = {prg[offset]:02X}")
    else:
        print(f"PRG[{offset}] = out of range")

print('PRG last 16 bytes:')
print(' '.join(f"{b:02X}" for b in prg[-16:]))
