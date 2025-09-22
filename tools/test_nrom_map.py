import os, sys
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo not in sys.path:
    sys.path.insert(0, repo)
from src.Bus import Bus
from src.mappers import NROMMapper

path = os.path.join(repo, 'Super Mario Bros. (Europe) (Rev A).nes')
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

print('prg len', len(prg))
print('prg last 16:', [hex(b) for b in prg[-16:]])

bus = Bus()
mapper = NROMMapper(prg)
mapper.map(bus)

print('\nBus read of $FFF0..$FFFF:')
for a in range(0xFFF0, 0x10000):
    print(f"${a:04X}: {bus.read(a):02X}")

lo = bus.read(0xFFFC)
hi = bus.read(0xFFFD)
print('\nreset lo/hi:', hex(lo), hex(hi))
print('reset vector:', hex((hi<<8)|lo))

print('Done')
